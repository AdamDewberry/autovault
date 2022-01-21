from generate_raw_vault.app.find_metadata_files import (
    load_template_file,
    load_metadata_file,
    find_json_metadata,
)
from generate_raw_vault.app.metadata_handler import Metadata
from string import Template

STAGING_TEMPLATE = "generate_raw_vault/app/templates/staging_model.sql"
SAT_HASHDIFF_TEMPLATE = "generate_raw_vault/app/templates/sat_hashdiff.sql"
NAME_DICTIONARY = "./name_dictionary.json"


def export_all_staging_files(metadata_file_dirs):
    for metadata_file_path in metadata_file_dirs:
        create_staging_file(metadata_file_path)


def create_staging_file(metadata_file_path):
    template = load_template_file(STAGING_TEMPLATE)
    staging_template = Template(template)

    metadata_file = load_metadata_file(metadata_file_path)
    metadata = Metadata(metadata_file)
    hubs = metadata.get_hubs_from_business_topics()
    topics = metadata.get_business_topics()
    hub_substitutions_string = get_hub_substitutions_string(metadata, hubs)
    sat_substitutions_string = get_sat_substitutions_string(metadata, topics)
    unique_link_combinations_substitutions_string = get_unique_link_combinations_substitutions_string(
        metadata, hubs, NAME_DICTIONARY
    )
    hub_alias_substitution_string = get_hub_alias_substitutions_string(topics)

    substitutions = create_staging_subsitutions(
        metadata,
        hub_substitutions_string,
        hub_alias_substitution_string,
        unique_link_combinations_substitutions_string,
        sat_substitutions_string,
    )
    staging_model = staging_template.substitute(substitutions)
    file_name = metadata.get_versioned_source_name().lower()
    with open(f"./models/raw_vault/stages/stg_{file_name}.sql", "w") as sql_export:
        sql_export.write(staging_model)


def format_derived_columns(column_list):
    return "\n  ".join(column_list)


def get_hub_substitutions_string(metadata, hubs):
    hubs_substitutions = [hashkey_substitution(metadata, hub) for hub in hubs]
    return create_substitutions_string(hubs_substitutions)


def create_substitutions_string(substitutions):
    substitutions_string = "\n  ".join(substitutions)
    return substitutions_string


def hashkey_substitution(metadata, hub):
    primary_key = metadata.get_hub_business_key(hub)
    topic = metadata.get_business_topics()
    if topic.get("alias"):
        primary_key = topic.get("alias")
    hashkey_substitution = f'{hub}_HK: "{primary_key}"'
    return hashkey_substitution


def get_sat_substitutions_string(metadata, topics):
    sats_substitutions = [
        get_sat_substitution_from_topic(metadata, hub_name) for hub_name in topics
    ]
    if sats_substitutions:
        return create_substitutions_string(sats_substitutions)


def get_sat_substitution_from_topic(metadata, hub_name):
    template = load_template_file(SAT_HASHDIFF_TEMPLATE)
    sat_hashdiff_template = Template(template)
    satellites = metadata.get_sat_from_hub(hub_name)
    sats = [
        get_sat_subs(sat_hashdiff_template, sat_name, payload)
        for sat_name, payload in satellites.items()
    ]
    if sats[0]:
        return "\n  ".join(sats)
    else:
        return ""


def get_sat_subs(sat_hashdiff_template, sat_name, payload):
    hashdiff = f"{sat_name}_HASHDIFF"
    sorted_payload_keys = sorted(payload.keys())
    formatted_sat_column_list = [f'- "{column}"' for column in sorted_payload_keys]
    formatted_sat_column_list_string = f"\n{chr(32)*6}".join(formatted_sat_column_list)
    substitutions = {
        "hashdiff_name": hashdiff,
        "columns": formatted_sat_column_list_string,
    }
    if "null" not in formatted_sat_column_list_string:
        return sat_hashdiff_template.substitute(substitutions)


def get_unique_link_combinations_substitutions_string(
    metadata, hubs, naming_dictionary_path
):
    if len(hubs) > 1:
        unique_link_combinations_substitutions = []
        naming_dictionary = load_metadata_file(naming_dictionary_path)
        for hub in hubs:
            if hub not in naming_dictionary:
                raise Exception(
                    f"Hub name missing from name dictionary, check hub name convention and existance in file {naming_dictionary_path}"
                )
        link_combination_string = "_".join([naming_dictionary[hub] for hub in hubs])
        unit_of_work = metadata.get_unit_of_work()
        link_name = f"{link_combination_string}_{unit_of_work}"
        combi_primary_keys = [metadata.get_hub_business_key(hub) for hub in hubs]
        link_keys = [f'- "{key}"' for key in combi_primary_keys]
        primarykeys_join = "\n   ".join(link_keys)
        unique_link_combinations_substitutions.append(
            f"{link_name}_HK:\n   {primarykeys_join}"
        )
        return create_substitutions_string(unique_link_combinations_substitutions)
    else:
        return ""


def get_hub_alias_substitutions_string(topics):
    hubs_alias_substitutions = [
        f'{topic_value.get("alias")}: "{"".join(list(topic_value.get("business_keys").keys()))}"'
        for topic_value in list(topics.values())
        if topic_value.get("alias") is not None
    ]
    return create_substitutions_string(hubs_alias_substitutions)


def create_staging_subsitutions(
    metadata,
    hubs_substitution,
    hub_alias_substitution_string,
    unique_link_combinations_substitution,
    sat_substitution,
):
    database_name = metadata.get_target_database()
    schema_name = metadata.get_target_schema()
    source_name = f"{database_name}_{schema_name}"
    table_name = metadata.get_versioned_source_name()

    derived_columns = [
        'EFFECTIVE_FROM: "LOAD_DATETIME"',
        'START_DATE: "LOAD_DATETIME"',
        '''END_DATE: "TO_DATE('9999-12-31')"''',
    ]
    formatted_derived_columns = format_derived_columns(derived_columns)

    substitutions = {
        "source": f'{source_name}: "{table_name}"',
        "derived_columns": formatted_derived_columns,
        "hashed_hubs_primary_key": hubs_substitution,
        "alias_columns": hub_alias_substitution_string,
        "hashed_links": unique_link_combinations_substitution,
        "hashdiff": sat_substitution,
    }
    return substitutions


if __name__ == "__main__":
    metadata_file_dirs = find_json_metadata(metadata_directory="source_metadata")
    export_all_staging_files(metadata_file_dirs)


{{ config(
  materialized='incremental',
  schema = "HUBS"
  ) }}

{%- set source_model = "stg_customer_visits_v1" -%}
{%- set src_pk = "CUSTOMER_HK" -%}
{%- set src_nk = "CUSTOMER_ID" -%}
{%- set src_ldts = "LOAD_DATETIME" -%}
{%- set src_source = "RECORD_SOURCE" -%}

{{ dbtvault.hub(src_pk=src_pk,
                src_nk=src_nk,
                src_ldts=src_ldts,
                src_source=src_source,
                source_model=source_model) }}
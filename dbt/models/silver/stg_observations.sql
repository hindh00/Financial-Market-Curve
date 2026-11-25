{#
  Typed, long-format reshape of every non-CORRA series (see stg_corra.sql
  for CORRA's group shape). Multiple pull_date rows can exist per
  (series_id, observation_date) by design — a revised value shows up as a
  later-pull_date row, and gold/fact_observation.sql decides
  is_latest_pull/is_revision from that. For backfilled rows, pull_date is
  derived from observation_date itself, since one backfill file has no
  single meaningful file-level pull_date.
#}

with exploded as (
    select
        series_id,
        pull_date,
        pull_timestamp_utc,
        resolved_as_rrb_benchmark,
        rrb_description,
        is_backfill,
        explode(
            from_json(
                observations_flat_json,
                'array<struct<observation_date:string,field_name:string,value_raw:string>>'
            )
        ) as obs
    from {{ source('bronze', 'raw_observations') }}
    where series_id != 'CORRA_METRICS'
),

parsed as (
    select
        series_id,
        cast(obs.observation_date as date) as observation_date,
        case when is_backfill then cast(obs.observation_date as date) else pull_date end as pull_date,
        pull_timestamp_utc,
        resolved_as_rrb_benchmark,
        rrb_description,
        is_backfill,
        obs.value_raw,
        try_cast(regexp_extract(obs.value_raw, '^-?[0-9]+(\\.[0-9]+)?', 0) as double) as value,
        regexp_extract(obs.value_raw, '([A-Za-z]+)$', 1) as revision_flag_raw
    from exploded
)

select
    p.series_id,
    p.observation_date,
    p.pull_date,
    p.pull_timestamp_utc,
    p.is_backfill,
    p.value,
    p.value_raw,
    nullif(p.revision_flag_raw, '') is not null as has_revision_marker,
    coalesce(p.resolved_as_rrb_benchmark, false) as is_rrb_benchmark,
    coalesce(sr.category, case when p.resolved_as_rrb_benchmark then 'rrb_benchmark' end) as category,
    coalesce(sr.tenor, case when p.resolved_as_rrb_benchmark then 'LONG' end) as tenor,
    coalesce(sr.instrument_type, case when p.resolved_as_rrb_benchmark then 'real_return_bond' end) as instrument_type,
    coalesce(sr.unit, case when p.resolved_as_rrb_benchmark then 'percent' end) as unit,
    coalesce(sr.label, p.rrb_description) as label
from parsed p
left join {{ ref('series_registry_seed') }} sr
    on p.series_id = sr.series_id

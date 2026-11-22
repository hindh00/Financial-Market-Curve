{#
  Typed, long-format reshape of every non-CORRA series (CORRA's group
  shape is handled separately in stg_corra.sql, since it has several
  named sub-fields per day rather than one value).

  Multiple pull_date rows can exist for the same (series_id, observation_date)
  — that's intentional: OBSERVATION_WINDOW re-fetches a rolling window every
  day, so a value revised after first publication shows up as a second row
  with a later pull_date and a different value. gold/fact_observation.sql
  is what decides is_latest_pull / is_revision from this.

  value_raw is split into a numeric value plus any trailing non-numeric
  suffix (revision_flag_raw) defensively, in case Valet ever marks a
  revised value with a suffix on the raw string (the Bank's CORRA *webpage*
  marks revisions with "R", but it's unconfirmed whether the raw API value
  string ever does the same — this is a no-op if it never does).

  pull_date is derived per-row for backfilled data (is_backfill=true, from
  ingestion/backfill.py): a backfill file has no single meaningful
  file-level pull_date since it spans years of observations in one call,
  so each row instead uses its own observation_date as a stand-in. This is
  also why backfilled rows can't carry revision history — there's no
  record of what was "pulled" on any day other than the day the backfill
  itself ran.
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

{#
  Human-readable revision log, built on fact_observation's is_revision
  flag: series, observation_date, which pull_date the revision showed up
  on, and the old/new values.
#}

with base as (
    select
        series_id,
        observation_date,
        pull_date,
        value,
        is_revision,
        lag(value) over (partition by series_id, observation_date order by pull_date) as old_value
    from {{ ref('fact_observation') }}
)

select
    series_id,
    observation_date,
    pull_date as revised_as_of_pull_date,
    old_value,
    value as new_value,
    (value - old_value) as delta
from base
where is_revision

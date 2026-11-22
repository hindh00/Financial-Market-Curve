{#
  Market inflation expectations = nominal benchmark yield minus the RRB
  real yield. The RRB benchmark is a fixed, aging bond (issuance ceased in
  2022, see ingestion/rrb_lookup.py) with no newer issue to replace it, so
  this metric's long-run trend is less trustworthy over time than a metric
  built on a regularly-refreshed benchmark — caveat_text carries that note
  through to any dashboard built on this table rather than hardcoding it
  in Lakeview.
#}

with nominal as (
    select observation_date, value as nominal_yield
    from {{ ref('fact_observation') }}
    where series_id = 'BD.CDN.LONG.DQ.YLD' and is_latest_pull
),

real as (
    select
        observation_date,
        value as real_yield,
        series_id as rrb_series_id,
        label as rrb_label
    from {{ ref('fact_observation') }}
    where is_rrb_benchmark and is_latest_pull
)

select
    n.observation_date,
    n.nominal_yield,
    r.real_yield,
    (n.nominal_yield - r.real_yield) as breakeven_inflation,
    r.rrb_series_id,
    r.rrb_label,
    'Breakeven inflation uses the RRB benchmark bond as the real-yield leg. The government ceased issuing new RRBs in 2022, so this benchmark bond ages indefinitely with no newer issue to replace it (see rrb_label for its issue date) — treat long-run trend comparisons with that in mind.' as caveat_text
from nominal n
join real r
    on n.observation_date = r.observation_date

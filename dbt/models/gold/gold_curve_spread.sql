{#
  10s2s spread and inversion flag, precomputed here (rather than in
  Lakeview) so the "Curve over time" page can just conditionally shade
  is_inverted without computing it in-visual.
#}

with curve as (
    select observation_date, tenor, yield
    from {{ ref('gold_daily_curve') }}
    where tenor in ('2Y', '10Y')
),

pivoted as (
    select
        observation_date,
        max(case when tenor = '2Y' then yield end) as yield_2y,
        max(case when tenor = '10Y' then yield end) as yield_10y
    from curve
    group by observation_date
)

select
    observation_date,
    yield_2y,
    yield_10y,
    (yield_10y - yield_2y) * 100 as spread_10s2s_bps,
    (yield_10y < yield_2y) as is_inverted
from pivoted

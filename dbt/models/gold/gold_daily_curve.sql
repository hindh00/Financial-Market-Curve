{#
  Long-format date x tenor yield table — feeds the "Curve over time"
  heatmap and the "Today" page's curve-vs-1mo/1yr-ago comparison.
  is_benchmark_switch_day rides along as a flag (not a filter) so the
  dashboard can annotate/shade a switch day rather than silently hide a
  real data point; jump/change calculations elsewhere are what actually
  exclude switch days (see gold_decision_day_reactions.sql).
#}

select
    observation_date,
    series_id,
    tenor,
    value as yield,
    is_benchmark_switch_day
from {{ ref('fact_observation') }}
where category in ('benchmark_bond', 'treasury_bill')
    and is_latest_pull

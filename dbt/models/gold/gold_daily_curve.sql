{#
  Long-format date x tenor yield table feeding the curve heatmap and
  "Today" comparisons. is_benchmark_switch_day rides along as a flag, not
  a filter, so the dashboard can annotate a switch day rather than hide it.
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

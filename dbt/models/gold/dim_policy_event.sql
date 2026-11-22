{#
  Sourced purely from the manually-maintained seed — NEVER derived from
  V39079 rate changes, which would silently drop every hold. See
  dbt/seeds/dim_policy_event_seed.csv for the maintenance note; the rows
  currently in that seed are placeholders and must be replaced with the
  Bank's verified published schedule before this table is trusted.
#}

select
    decision_date,
    action,
    size_bps,
    has_mpr,
    notes
from {{ ref('dim_policy_event_seed') }}

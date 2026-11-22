{#
  Sourced purely from the manually-maintained seed — NEVER derived from
  V39079 rate changes, which would silently drop every hold. 81 rows,
  2017-01-18 through 2026-10-28, compiled from the Bank's published
  "Schedule for Fixed Announcement Dates" press releases and decision
  releases (see dbt/seeds/dim_policy_event_seed.csv and docs/architecture.md
  for sourcing notes) — cross-checked by replaying size_bps/action against
  the known overnight rate path (0.50% -> 5.00% -> 2.25% -> 2.50% across
  this window). Needs a yearly top-up once the Bank publishes next year's
  schedule — see dbt/seeds/dim_policy_event_seed.csv's header.
#}

select
    decision_date,
    action,
    size_bps,
    has_mpr,
    notes
from {{ ref('dim_policy_event_seed') }}

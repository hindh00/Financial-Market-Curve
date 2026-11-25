{#
  Sourced purely from the manually-maintained seed — never derived from
  V39079 rate changes, which would silently drop every hold. Needs a
  yearly top-up once the Bank publishes next year's schedule.
#}

select
    decision_date,
    action,
    size_bps,
    has_mpr,
    notes
from {{ ref('dim_policy_event_seed') }}

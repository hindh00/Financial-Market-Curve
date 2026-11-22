{#
  Static series (from the seed) plus whichever series id has actually been
  resolved as the current RRB benchmark in the landed data — the RRB id is
  never hardcoded (see ingestion/rrb_lookup.py), so it can't live in the
  static seed; it's discovered from stg_observations instead.
#}

select series_id, category, tenor, instrument_type, unit, label
from {{ ref('series_registry_seed') }}

union all

select distinct series_id, category, tenor, instrument_type, unit, label
from {{ ref('stg_observations') }}
where is_rrb_benchmark

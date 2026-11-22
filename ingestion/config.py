"""Static registry of Valet API series/groups this project tracks.

The Real Return Bond benchmark is deliberately NOT listed here — see
rrb_lookup.py. The Bank periodically re-designates which RRB issue is the
"current" benchmark, and issuance of new RRBs ceased in 2022, so hardcoding
an id here would silently go stale.
"""

VALET_BASE_URL = "https://www.bankofcanada.ca/valet"

# How many most-recent observations to request on every daily pull. A window
# (not just "today") is pulled so that any revision to a value published in
# the last few days is captured under today's pull_date, which is what makes
# the revision log (feature 3) possible.
OBSERVATION_WINDOW = 10

# One-time backfill range (ingestion/backfill.py) — not used by the daily
# pull. Chosen as a common window most of these series should have data
# for; Valet simply returns less for a series that didn't exist yet this
# far back rather than erroring. Keep in sync with dbt's
# `backfill_start_date` var (dbt_project.yml) — dim_date's spine must start
# no later than this or backfilled fact rows before it will fail the
# referential-integrity DQ check.
BACKFILL_START_DATE = "2017-01-01"

# Single-series pulls: Valet series name -> dim_series metadata.
SERIES_REGISTRY = {
    "V39079": {"category": "policy_rate", "tenor": None, "label": "Target for the overnight rate"},
    "TB.CDN.60D.MID": {"category": "treasury_bill", "tenor": "60D", "label": "Treasury bill 60 day"},
    "TB.CDN.90D.MID": {"category": "treasury_bill", "tenor": "90D", "label": "Treasury bill 90 day"},
    "TB.CDN.180D.MID": {"category": "treasury_bill", "tenor": "180D", "label": "Treasury bill 180 day"},
    "TB.CDN.1Y.MID": {"category": "treasury_bill", "tenor": "1Y", "label": "Treasury bill 1 year"},
    "BD.CDN.2YR.DQ.YLD": {"category": "benchmark_bond", "tenor": "2Y", "label": "Benchmark bond yield 2 year"},
    "BD.CDN.3YR.DQ.YLD": {"category": "benchmark_bond", "tenor": "3Y", "label": "Benchmark bond yield 3 year"},
    "BD.CDN.5YR.DQ.YLD": {"category": "benchmark_bond", "tenor": "5Y", "label": "Benchmark bond yield 5 year"},
    "BD.CDN.7YR.DQ.YLD": {"category": "benchmark_bond", "tenor": "7Y", "label": "Benchmark bond yield 7 year"},
    "BD.CDN.10YR.DQ.YLD": {"category": "benchmark_bond", "tenor": "10Y", "label": "Benchmark bond yield 10 year"},
    "BD.CDN.LONG.DQ.YLD": {"category": "benchmark_bond", "tenor": "LONG", "label": "Benchmark bond yield long-term"},
    "FXUSDCAD": {"category": "fx", "tenor": None, "label": "USD/CAD daily exchange rate"},
}

# CORRA is published as a group (richer than a single series: the rate plus
# percentiles, volume, unique submitters, trim rate).
CORRA_GROUP_NAME = "AVG.INTWO"

# Pattern used by rrb_lookup.py to find the current Real Return Bond
# benchmark series in /lists/series/json. Matched case-insensitively against
# each series' description/label text.
RRB_DESCRIPTION_PATTERN = r"real return bond"

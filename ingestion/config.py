"""Static registry of Valet API series/groups this project tracks. The Real
Return Bond benchmark is deliberately excluded — see rrb_lookup.py, since the
Bank periodically re-designates it and new RRB issuance ceased in 2022.
"""

VALET_BASE_URL = "https://www.bankofcanada.ca/valet"

# Rolling window (not just "today") pulled daily so a value revised in the
# last few days gets captured under today's pull_date (feature 3: revisions).
OBSERVATION_WINDOW = 10

# One-time backfill start date — must stay in sync with dbt's
# `backfill_start_date` var, or backfilled rows before it fail the
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
CORRA_GROUP_NAME = "CORRA_METRICS"

# Matches the current RRB benchmark in /lists/series/json by description
# text; narrowed to require "yield" since other RRB-related series exist
# (index ratios, CPI ref dates) that aren't the benchmark yield itself.
RRB_DESCRIPTION_PATTERN = r"real return bonds? yield"

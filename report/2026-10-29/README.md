# Report snapshot, 2026-10-29

MV2 of Munim, Inc. Made by AI agents (Claude) working in MV2's name. No human has reviewed it. Text and tables CC BY 4.0. Public-health research information, not medical advice and not a forecast for any person or place.

- `index.html`: the open early-warning page for all 50 states and DC (COVID-19, influenza A, RSV). Open it in any browser; it has no scripts.
- `status.csv`: the same status, one row per state and pathogen.

Built by job `ew-report-v2` on 2026-10-29 at 14:47-14:50 UTC with `ew/report.py` 1.2 (`python -m ew.report --fetch --backtest results/ew-bt-v1/results.json --states results/ew-bt-v1/states.csv`). Data as published by CDC on the fetch date: WVAL site data up to the week ending 2026-10-17, ED data through the same week.

On this page: the wastewater rule is firing in 11 states for COVID-19, 7 for influenza and 0 for RSV; the ED-only rule in 8, 40 and 4. Thirteen series are marked stale (newest value more than 2 weeks older than the page's newest week) and are not counted as firing: wastewater for DC (all three), Montana (influenza, RSV), New Mexico (influenza, RSV), North Dakota (COVID-19, last reported 2023-09-16), Oklahoma (influenza) and Wyoming (RSV); ED data for Iowa (all three, last 2026-06-27).

The page uses the state median of site values. Study v2 ([../../results/ew-agg-results-v1-2026-10-29.md](../../results/ew-agg-results-v1-2026-10-29.md)) found that other aggregates catch more influenza and RSV surges at a cost in false alarms; the page has not been changed because of it.

Data: CDC NWSS and NSSP, US federal public data. No endorsement by CDC is implied.

# ew-backtest

An open, pre-registered back-test of one simple early-warning rule. It checks whether CDC's published wastewater viral activity (NWSS WVAL) warns of state emergency department (ED) surges for COVID-19, influenza and RSV earlier than the ED data's own rule. It also checks how often the warning is right, and whether it still helps once each source's release timing is counted.

By MV2 of Munim, Inc. (mv2@munimtech.com). The code and text were made by AI agents (Claude) working in MV2's name. No human has reviewed the results yet.

## Status

- **Pre-registration:** [prereg/ew-backtest-prereg-v1-2026-10-28.md](prereg/ew-backtest-prereg-v1-2026-10-28.md). The rules, outcomes, hypotheses (H1-H6), predictions and readings were fixed before any result existed.
- **Results (v0.2.0):** [results/ew-backtest-results-v1-2026-10-29.md](results/ew-backtest-results-v1-2026-10-29.md), graded exactly as written; job outputs in [results/ew-bt-v1/](results/ew-bt-v1/). In all 50 states and DC, the wastewater rule beat random timing for all three viruses (PPV 0.36, 0.51 and 0.44 against 0.12 to 0.15 by chance). It was not significantly earlier than the same rule on ED data for any of them, and it caught only 37% of influenza and 26% of RSV ED surges. The pre-registered reading: state wastewater gave confirmation, not lead. 11 of 16 predictions held.
- **Report (v0.2.0):** `ew/report.py` 1.1 turns the weekly series into one static HTML page that shows where the rule stands in every state now. Given the back-test's `results.json` and `states.csv`, it also shows how often each rule's alerts were right and each state's own record. It applies the pre-registered rule as written and fits nothing new.
- **Follow-up study (v0.3.0, pre-registered, results pending):** [prereg/ew-agg-prereg-v1-2026-10-29.md](prereg/ew-agg-prereg-v1-2026-10-29.md). Was v1's result a property of the state median? `ew/agg.py` runs the same rule on a population-weighted mean and on the upper quartile of the same site values, and tests whether either catches the ED surges the median missed or comes earlier than the ED-only rule.

## What it does

1. Fetches two public CDC datasets through the data.cdc.gov SODA API: NWSS WVAL by site (`atcp-73re`) and NSSP ED visit percentages by state (`rdmq-nq56`, `trend_source='State'`).
2. Builds one weekly series per state and pathogen: the median site WVAL (with the site count) and the ED percent.
3. Runs a fixed rule. It fires when a series is above its own trailing 52-week median and has risen two weeks running. The rule runs on wastewater (`ww`), on ED data alone (`ed`, the baseline) and on both together (`both`).
4. Scores the rules against ED surge onsets: sensitivity, lead time, PPV, false alarms per 52 state-weeks, a random-timing null, paired lead differences and the effect of the publication schedule.

All thresholds use past weeks only. Outputs are aggregate public data: `results.json`, `series.csv` and `states.csv`.

## The report

`python -m ew.report --fetch --out-dir out/report` (or `--series out/series.csv` to reuse a back-test's series) writes:

- `index.html`: one self-contained page with no scripts and no server. For each state and pathogen there is an inline SVG chart of the last 104 weeks, showing state wastewater and ED percent, the ED surge onsets, and the weeks each rule alerted. Under the chart, each source's newest week is explained in words: its status (rule firing, above median, at or below median, too little history, no data), the value against its trailing median, the two weeks before, the number of wastewater sites, and the last alert. A summary table counts the states where each rule is firing.
- With `--backtest results.json`: a table of how reliable each rule's alerts have been (surges caught, PPV, PPV by chance, false alarms, lead) and the pre-registered reading for each pathogen. With `--states states.csv`: each state's own back-test record under its chart.
- `status.csv`: the same status, one row per state and pathogen.

## Run

```
python -m unittest discover -v
python -m ew.run --out-dir out
python -m ew.report --series out/series.csv --backtest out/results.json --states out/states.csv --out-dir out/report
python -m ew.agg --out-dir out/agg
```

Python 3.11+, standard library only. Fetching needs network access to data.cdc.gov.

## Limits

These are state medians over very different sewersheds. Both sources are revised, and the back-test uses the data as published on the fetch date. ED percent is a share of all visits. This is research information for public-health readers. It is not medical advice and not a forecast for any person or place.

## Data and licence

Data: CDC National Wastewater Surveillance System and National Syndromic Surveillance Program (US federal public data). No endorsement by CDC is implied.

Code: Apache-2.0 (see LICENSE). Text and derived tables: CC BY 4.0.

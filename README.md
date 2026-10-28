# ew-backtest

An open, pre-registered back-test of one simple early-warning rule. It checks whether CDC's published wastewater viral activity (NWSS WVAL) warns of state emergency department (ED) surges for COVID-19, influenza and RSV earlier than the ED data's own rule. It also checks how often the warning is right, and whether it still helps once each source's release timing is counted.

By MV2 of Munim, Inc. (mv2@munimtech.com). The code and text were made by AI agents (Claude) working in MV2's name. No human has reviewed the results yet.

## Status

- **Pre-registration:** [prereg/ew-backtest-prereg-v1-2026-10-28.md](prereg/ew-backtest-prereg-v1-2026-10-28.md). The rules, outcomes, hypotheses (H1-H6), predictions and readings were fixed before any result existed.
- **Results:** pending. They will be graded exactly as written, including failures.

## What it does

1. Fetches two public CDC datasets through the data.cdc.gov SODA API: NWSS WVAL by site (`atcp-73re`) and NSSP ED visit percentages by state (`rdmq-nq56`, `trend_source='State'`).
2. Builds one weekly series per state and pathogen: the median site WVAL (with the site count) and the ED percent.
3. Runs a fixed rule. It fires when a series is above its own trailing 52-week median and has risen two weeks running. The rule runs on wastewater (`ww`), on ED data alone (`ed`, the baseline) and on both together (`both`).
4. Scores the rules against ED surge onsets: sensitivity, lead time, PPV, false alarms per 52 state-weeks, a random-timing null, paired lead differences and the effect of the publication schedule.

All thresholds use past weeks only. Outputs are aggregate public data: `results.json`, `series.csv` and `states.csv`.

## Run

```
python -m unittest discover -v
python -m ew.run --out-dir out
```

Python 3.11+, standard library only. The run needs network access to data.cdc.gov.

## Limits

These are state medians over very different sewersheds. Both sources are revised, and the back-test uses the data as published on the fetch date. ED percent is a share of all visits. This is research information for public-health readers. It is not medical advice and not a forecast for any person or place.

## Data and licence

Data: CDC National Wastewater Surveillance System and National Syndromic Surveillance Program (US federal public data). No endorsement by CDC is implied.

Code: Apache-2.0 (see LICENSE). Text and derived tables: CC BY 4.0.

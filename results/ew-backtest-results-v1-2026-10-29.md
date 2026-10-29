# Results: does a fixed wastewater alert rule warn of state ED-visit surges earlier than ED data alone? (v1, graded 2026-10-29)

MV2 of Munim, Inc. (mv2@munimtech.com). Researched, coded, run and graded by AI agents (Claude) working in MV2's name. No human has reviewed these results yet. Text and tables CC BY 4.0; code Apache-2.0. This is public-health research information, not medical advice and not a forecast for any person or place.

**Pre-registration:** [prereg/ew-backtest-prereg-v1-2026-10-28.md](../prereg/ew-backtest-prereg-v1-2026-10-28.md), fixed and published (tag v0.1.0) before the job ran. Every grade below is copied from the job's `results.json` and applies the plan exactly as written. Nothing was re-run, re-tuned or dropped.

**Job:** `ew-bt-v1`, code `ew/` 1.0 at tag v0.1.0, run 2026-10-28 21:29-21:33 UTC in a sealed container (Python 3.12.15). Offline tests 20/20 passed before the run. Data fetched from data.cdc.gov at 21:31 UTC. Outputs: [results/ew-bt-v1/](ew-bt-v1/) (`results.json`, `series.csv`, `states.csv`).

## Short answer

Across all 50 states and DC, a simple wastewater alert rule run on CDC's state-level wastewater data **was far better than chance** at flagging emergency department (ED) surges of COVID-19, influenza and RSV. **But for none of the three was it significantly earlier than the same rule run on the ED data itself**; for influenza and RSV the ED-only rule was usually the earlier one. For influenza and RSV it also missed most surges: it caught 37% and 26%, against 61% and 65% for the ED-only rule. Under the pre-registered reading, state wastewater gave **confirmation, not lead.** 11 of our 16 predictions held. The one prediction of a wastewater lead (RSV) was wrong.

## Gate

| Check | Needed | Observed | |
|---|---|---|---|
| WVAL site rows | >= 400,000 | 575,229 (0 skipped) | pass |
| ED rows | >= 10,000 | 10,863 (0 skipped) | pass |
| Places in both sources | >= 45 | 51 | pass |

Timing on the fetch date: newest wastewater week 2026-10-17 (data updated 2026-10-23); newest ED week 2026-10-24 (build 2026-10-28). Graded grid: weeks ending 2022-01-01 to 2026-10-17; 8,448 evaluable state-weeks per pathogen.

## Grades (exactly as pre-registered)

| ID | Test | COVID-19 | Influenza | RSV | Our prediction | Held? |
|---|---|---|---|---|---|---|
| H1 | Wastewater PPV beats random timing (p < 0.05, above null mean) | **pass** (0.36 vs 0.15, p = 0.0005) | **pass** (0.51 vs 0.13, p = 0.0005) | **pass** (0.44 vs 0.12, p = 0.0005) | pass x3 | 3 of 3 |
| H2 | Wastewater sensitivity >= 0.50 | **pass** (0.65) | **fail** (0.37) | **fail** (0.26) | pass x3 | 1 of 3 |
| H3 | Same cycle: wastewater earlier than ED-only rule (sign test p < 0.05) | **fail** (42 vs 37, p = 0.33) | **fail** (2 vs 26, p = 1.00) | **fail** (6 vs 12, p = 0.95) | RSV pass; flu, COVID fail | 2 of 3 |
| H4 | Wednesday cycle (wastewater one week behind) | **fail** (26 vs 78) | **fail** (1 vs 30) | **fail** (3 vs 15) | fail x3 | 3 of 3 |
| H5 | Wastewater PPV >= ED-only PPV | **fail** (0.36 vs 0.53) | **pass** (0.51 vs 0.48) | **fail** (0.44 vs 0.54) | fail x3 | 2 of 3 |
| H6 | All pathogens: sensitivity lower where the median site count is < 3 (Fisher p < 0.05) | **fail** (24 of 58 = 41% vs 204 of 443 = 46%, p = 0.30) | | | pass | 0 of 1 |

H3 and H4 counts are "wastewater earlier vs ED-only earlier" among surges both rules caught; ties dropped (COVID-19 41, influenza 4, RSV 3 on the same cycle). No grade was untestable: every pathogen had at least 86 wastewater alerts with an outcome, at least 146 surges and at least 21 surges caught by both rules. H6 left out 6 surges in the 2 series with no wastewater sites (North Dakota influenza and RSV).

**Predictions held: 11 of 16.** Missed: H2 influenza and RSV (we expected sensitivity >= 0.50), H3 RSV (we expected a wastewater lead), H5 influenza (we expected lower wastewater PPV) and H6.

## Fixed readings, applied as written

- **H1 passes and H3 fails, for all three pathogens:** "wastewater alerts are informative but no earlier than the ED data's own rule. Its value would be confirmation, not lead."
- **H3 fails, so the H3/H4 lead readings do not apply.** No lead survives on either release cycle. On the Wednesday cycle, when wastewater is a week behind, the ED-only rule was earlier in 78 of 104 untied COVID-19 pairs, 30 of 31 influenza pairs and 15 of 18 RSV pairs.
- **H5 fails for COVID-19 and RSV:** the plan's reading is "wastewater buys lead at the cost of more false alarms." Here it bought no lead: the wastewater rule raised more false alarms (1.47 vs 0.98 per state-year for COVID-19; for RSV 0.30 vs 0.50, but with a lower PPV because it caught far fewer surges). For influenza, wastewater PPV was slightly higher (0.51 vs 0.48), but it caught 58 surges against the ED rule's 97.
- **Artifact reading (stated with every result):** surges are defined on the ED series, so the ED-only rule shares its noise with the outcome. That favours it on PPV. The plan expected it to work against the ED rule on lead, yet wastewater was not significantly earlier for any pathogen. The data are as published on 2026-10-28, after revisions, which may flatter both rules relative to what a forecaster saw in real time.

## Full numbers (primary parameters: trailing median, horizon 4 weeks)

| Pathogen | Rule | Surges caught | PPV | PPV by chance | False alarms per state-year | Median lead (weeks) | Alerts during a surge already under way |
|---|---|---|---|---|---|---|---|
| COVID-19 | Wastewater | 132 of 203 (65%) | 0.36 (132/371) | 0.15 | 1.47 | 2 | 74 of 445 (17%) |
| COVID-19 | ED only | 179 of 203 (88%) | 0.53 (179/339) | 0.15 | 0.98 | 2 | 25 of 364 (7%) |
| COVID-19 | Both rising | 132 of 203 (65%) | 0.43 (132/309) | | 1.09 | 2 | 57 |
| Influenza | Wastewater | 58 of 158 (37%) | 0.51 (58/113) | 0.13 | 0.34 | 1 | 95 of 208 (46%) |
| Influenza | ED only | 97 of 158 (61%) | 0.48 (96/200) | 0.13 | 0.64 | 3 | 68 of 268 (25%) |
| Influenza | Both rising | 57 of 158 (36%) | 0.65 (57/88) | | 0.19 | 1 | 87 |
| RSV | Wastewater | 38 of 146 (26%) | 0.44 (38/86) | 0.12 | 0.30 | 1.5 | 116 of 202 (57%) |
| RSV | ED only | 95 of 146 (65%) | 0.54 (95/176) | 0.12 | 0.50 | 3 | 31 of 207 (15%) |
| RSV | Both rising | 39 of 146 (27%) | 0.67 (39/58) | | 0.12 | 1 | 79 |

"Both rising" (the wastewater rule firing in a week when the ED percent also rose) was descriptive, not graded. Surges caught by wastewater only / ED only / neither: COVID-19 12 / 59 / 12; influenza 26 / 65 / 35; RSV 17 / 74 / 34.

## What we see beyond the grades (descriptive, not pre-registered)

1. **For influenza and RSV, the wastewater rule mostly fired after the ED surge had begun.** 46% of influenza and 57% of RSV wastewater alerts came when ED visits were already above their surge threshold, against 25% and 15% for the ED-only rule. At the state level, as built here, wastewater trailed ED for these two viruses more often than it led.
2. **In many states the wastewater rule caught no RSV or influenza surge at all.** It caught none in 24 of 51 RSV series and 12 of 51 influenza series (each count includes North Dakota, which has no wastewater sites for these two), against 2 of 51 COVID-19 series (`states.csv`).
3. **Tuning does not rescue it.** In the descriptive grid (threshold quantile 0.5 or 0.75; horizon 4 or 6 weeks) wastewater sensitivity for influenza stayed at 0.30-0.39 and for RSV at 0.12-0.27. With the 0.75 threshold the ED-only rule nearly restates the surge definition (PPV 0.85-0.97), so that column says little.
4. **Combining helps precision, not reach.** "Both rising" had the highest PPV for influenza (0.65) and RSV (0.67), at about a third of surges caught.

## Why this may differ from studies that found a wastewater lead

These are hypotheses for follow-up, not findings:
- **Aggregation.** We take the median of site WVAL values in each state. One early sewershed is diluted by many others; a population-weighted or "any site rising" signal might lead where the median does not.
- **Influenza A only.** WVAL's influenza target is influenza A; ED visits count all influenza.
- **The outcome.** We score against ED-visit share, a fast clinical signal. Studies that found a lead often scored against hospital admissions or laboratory data, which come later.
- **Revisions.** WVAL baselines are recomputed. A real-time (as-first-published) test could come out differently in either direction.

## Prior art and what is new

The prior-art search (pre-registration, section 2, 2026-10-28) found single-state lead-lag studies (Wisconsin, Texas, and California, which found no consistent lead), a 50-state abstract against hospitalizations, an EWMA alert back-test against laboratory data with no clinical-only comparator, and a 281-county SARS-CoV-2 event-detection study. We found no pre-registered back-test that uses CDC's published state-level WVAL for all three pathogens in every state, compares the wastewater rule with the same rule on ED data and with random timing, reports sensitivity, PPV and false alarms, and counts release timing, with open code. This result, a pre-registered negative on lead across 50 states and DC with the ED-only comparator, is to our knowledge the first of its kind. The search was by AI agents and may have missed work.

## Limits

- State medians of site WVAL over very different sewersheds; a few sites can move a small state.
- ED percent is a share of all ED visits.
- Data as published on 2026-10-28, not as first released. Graded surges start in late 2023: about three seasons.
- One rule family and one surge definition, fixed in advance. Other rules, aggregations or outcomes may do better.
- One model family (Claude) designed, coded and graded this. No human has checked it yet.

## What changes in the tool

`ew/report.py` 1.1 now shows these numbers on the report page next to each pathogen's status, with the pre-registered reading, and gives each state's own back-test record under its chart. The page says plainly that state wastewater alerts have been confirmation, not lead.

## Data and acknowledgement

CDC National Wastewater Surveillance System (NWSS Wastewater Viral Activity Level by site, `atcp-73re`) and National Syndromic Surveillance Program (ED visit trajectories by state, `rdmq-nq56`), US federal public data. No endorsement by CDC is implied.

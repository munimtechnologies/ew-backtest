# Pre-registration: does a fixed wastewater alert rule warn of state ED-visit surges earlier than ED data alone? (v1, 2026-10-28)

MV2 of Munim, Inc. Researched, written and coded by AI agents (Claude) working in MV2's name. No human has reviewed this plan yet. Text CC BY 4.0; code Apache-2.0. This is public-health research information, not medical advice.

**Status:** fixed before any back-test result exists. Code: `ew/backtest.py`, `ew/cdc.py` and `ew/run.py` 1.0 in this repository, with offline tests. Before writing this plan we looked only at the datasets' metadata: column names, row counts per state and pathogen, first and last weeks, and the two or three newest rows of each dataset (on 2026-10-28). We have not looked at any state's time series.

## 1. Question

Public-health agencies now publish two weekly respiratory signals for every US state: wastewater viral activity (CDC NWSS) and the share of emergency department (ED) visits for each virus (CDC NSSP). Wastewater is often said to lead clinical data. We ask a narrower, practical question. Take one simple alert rule, fixed in advance and run on the published state-level data. Does it warn of an ED surge earlier than the same rule run on the ED data itself, how often is it right, and does it still help once each source's release timing is counted?

## 2. Prior art (searched 2026-10-28)

- Lead-lag and correlation studies of wastewater against ED visits, lab tests or hospital admissions exist for single states or cities: Wisconsin (MMWR 72(37), 2023), Texas (Emerging Infectious Diseases vol. 32 supplement, article 26-0141, 2026) and California (EID vol. 32 supplement, article 26-0306, 2026, which found no consistent lead). A conference abstract covers all 50 states against hospitalizations (PMC12792989).
- Alert-rule back-tests exist too. An EWMA early-warning index on WastewaterSCAN sites for RSV and influenza A, benchmarked against laboratory data, reports lead time and off-season false alerts (medRxiv 10.64898/2026.01.20.26344452). It has no clinical-only comparator, no PPV and no open code. A 281-county SARS-CoV-2 event-detection study reports true positives, false alarms and lead against hospitalizations (medRxiv 10.64898/2026.05.14.26353186).
- **What we did not find:** a pre-registered back-test that (a) uses CDC's published WVAL at state level, (b) covers all three pathogens in all states, (c) compares the wastewater rule with the same rule on ED data (an ED-only baseline) and with random timing, (d) reports sensitivity, PPV and false alarms, and (e) counts release timing, with open code. That combination is the contribution here. The question is not new; this design is, as far as our search found.

## 3. Data (US federal public data, data.cdc.gov, fetched by the job)

- **Wastewater:** NWSS Wastewater Viral Activity Level by site, `atcp-73re` (SARS-CoV-2, "Influenza A virus", RSV). As of 2026-10-28: about 575,000 rows, weeks ending 2022-01-01 (RSV 2022-03-05) to 2026-10-17, in 50 states, DC, Guam and the US Virgin Islands. **State value per week = the median over the state's sites of site_wval.** A site with two rows in one week counts once, at their mean. The number of sites is kept.
- **ED visits:** NSSP "ED Visit Trajectories by State and Sub State Regions", `rdmq-nq56`, rows with trend_source = 'State'. These are the unsmoothed percent of ED visits for COVID-19, influenza and RSV. There are 51 geographies (50 states and DC), 213 weeks each, weeks ending 2022-10-01 to 2026-10-24.
- **Grid:** weeks ending on Saturdays, from the first week in either source to the last week both have (expected 2026-10-17). Only the 51 places in both sources enter.
- Both sources are revised over time (WVAL baselines are recomputed). **This back-test uses the data as published on the fetch date, not as first released.**

## 4. Definitions (constants in `ew/backtest.py`)

- **Trailing threshold:** the q-quantile (value at sorted index floor(q*(n-1))) of the series' previous 52 weeks. It needs at least 40 known values and at least 52 weeks of grid before it. Thresholds use only past weeks.
- **ED above flag:** the ED percent is above its trailing 0.75-quantile.
- **Event (ED surge onset):** week t where the above flag is True in t and t+1, and known and False in each of the 4 weeks before t.
- **Rule R(x, q):** fires in week t if x[t] is above its trailing q-quantile and x[t] > x[t-1] > x[t-2]. It does not fire if any of these is unknown. **Alert** = a firing week with no firing in the previous 4 weeks.
  - **ww** = R(state WVAL, 0.5): the wastewater rule.
  - **ed** = R(ED percent, 0.5): the ED-only baseline. It is the same rule on the ED series, so it can fire before the 0.75 event threshold is crossed.
  - **both** = ww firing in a week when the ED percent also rose (descriptive, multi-signal).
- **Detection:** an event is detected by a rule if one of its alerts falls 0-4 weeks before the onset, or in the onset week. Lead = onset minus the earliest such alert, in weeks.
- **Alert outcome:** an alert in week t counts as **true** if an event onset falls in weeks t..t+4. It counts as **in episode** if not true and the ED was already above its threshold in week t-1. Otherwise it is a **false alarm**. It is evaluable only if the above flag is known from t-1 through t+5. **PPV = true / (true + false).** In-episode alerts are reported, not counted in PPV. False alarms are also given per 52 evaluable state-weeks.
- **Random-timing null:** for each state and pathogen, the same number of evaluable alerts goes to random evaluable weeks without replacement (refractory spacing not kept). PPV is pooled per pathogen. There are 2,000 repetitions, seed 20261029, one generator used in a fixed order. p = (1 + #null PPV >= observed) / (1 + reps).
- **Release timing:** on 2026-10-28, the newest WVAL week was 2026-10-17 (updated Friday 2026-10-23). The newest NSSP week was 2026-10-24 (build Wednesday 2026-10-28). So on a weekly cycle run after the Friday WVAL release, both sources cover the same week ("same cycle"). On a Wednesday cycle, wastewater is one week behind ED ("Wednesday cycle", 1-week penalty). The job records the fetch-date timing again.

## 5. Gate

The gate needs at least 400,000 WVAL rows, at least 10,000 ED rows and at least 45 places in both sources. If it fails, nothing is graded.

## 6. Hypotheses, predictions and fixed readings (primary parameters only)

Each of H1-H5 is graded separately for COVID-19, influenza and RSV, all states pooled. A result is **untestable** when, for that pathogen: there are fewer than 20 ww alerts with an outcome (H1, H5; also fewer than 20 ed alerts for H5); fewer than 20 events (H2); or fewer than 10 events detected by both rules (H3, H4).

| ID | Test | Pass if | Our prediction |
|---|---|---|---|
| H1 | ww PPV against the random-timing null | null p < 0.05 and PPV above the null mean | pass, all three |
| H2 | ww sensitivity | >= 0.50 | pass, all three (least sure: COVID-19) |
| H3 | Same cycle: among events detected by both rules, ww earlier than ed (d = lead_ww - lead_ed) | one-sided exact sign test p < 0.05, ties dropped | RSV pass; influenza fail; COVID-19 fail |
| H4 | Wednesday cycle: the same with d - 1 | p < 0.05 | fail, all three |
| H5 | ww PPV >= ed PPV | point estimates | fail, all three |
| H6 | All pathogens pooled: ww sensitivity lower in state-pathogen series whose median site count is < 3 than in those with >= 3 | one-sided Fisher exact p < 0.05 (untestable if either group has < 10 events) | pass (least sure: few sparse series) |

**Fixed readings:**
- **H1 fails:** the state wastewater rule's timing is no better than chance against ED surges. No early-warning claim is made for that pathogen.
- **H1 passes and H3 fails:** wastewater alerts are informative but no earlier than the ED data's own rule. Its value would be confirmation, not lead.
- **H3 passes and H4 fails:** wastewater's lead exists only on a cycle run after the Friday release. Any tool must state this.
- **H3 and H4 both pass:** the lead survives a one-week publication handicap. This is the strongest result.
- **H5 fails (ww PPV below ed):** wastewater buys lead at the cost of more false alarms. The trade-off is reported, not hidden.
- **Artifact reading:** the event is defined on the ED series. So the ed rule shares its noise with the outcome, which favours it on PPV and against it on lead. Both directions are stated with every result. Revised data may also flatter both rules relative to what a forecaster saw in real time.

Descriptive only, not graded: the "both" rule; a grid with q in {0.5, 0.75} and horizon in {4, 6} weeks (no nulls); per-state counts; the counts of events detected only by ww, only by ed, or by neither.

## 7. Outputs (aggregate public data only)

`results.json` (gate, timing, summary, grades, grid), `series.csv` (weekly state WVAL median, site count, ED percent), `states.csv` (per state and pathogen counts). The results note will grade H1-H6 exactly as written above, including any that are untestable or fail because of our own error.

## 8. Limits known now

- These are state medians of site WVAL. Large states average over very different sewersheds, and a single site can move a small state.
- ED percent is a share of all visits, so it can move when other visit types change.
- Both sources are revised, as noted in section 3. Thresholds are per state and per pathogen, so they do not compare absolute levels across states.
- 2022-23 serves mainly as threshold history. Graded events start in late 2023, which leaves about three seasons.
- One model family (Claude) designed, coded and will grade this. Nothing here is a forecast for any person or place.

## 9. Why this exists

This back-test is the evidence base for an open early-warning prototype that MV2 of Munim, Inc. plans to enter in a public innovation challenge (multi-signal population early warning). The prototype will be released as open source whatever the challenge outcome. Data: CDC National Wastewater Surveillance System and National Syndromic Surveillance Program, public domain; no endorsement by CDC is implied.

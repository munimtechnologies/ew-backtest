# Pre-registration: the 2026-27 season, scored on alerts as they were published (prospective study S1, 2026-10-29)

MV2 of Munim, Inc. Researched, written and coded by AI agents (Claude) working in MV2's name. No human has reviewed this plan yet. Text CC BY 4.0; code Apache-2.0. This is public-health research information, not medical advice.

**Status:** fixed on 2026-10-29, before any ED surge in the scoring window below can have started (the newest week in CDC's data today ends 2026-10-17). Recording code: `ew/watch.py` 1.0 with offline tests (`ew/test_watch.py`). The scoring code (`ew/season.py`) does not exist yet; section 7 says what may and may not be decided when it is written.

## 1. Why

Three retrospective studies on 2022-2026 (v1, study v2 and study v3; notes in [results/](../results/)) found that a simple wastewater rule beats random timing but never warns earlier than the same rule on ED data, and that every state aggregate that catches more ED surges than the median pays for it in false alarms, except perhaps the upper quartile (q75), which was chosen after the first study. All three scored alerts on data as revised later, and five aggregates were compared on the same history. Two things only a prospective check can settle:

1. Do the retrospective findings hold on a season none of the choices could have been fitted to?
2. How much does scoring on revised data flatter the rules? CDC's WVAL values are re-based and revised after release, and ED percentages are revised as late records arrive. A reader acting on the report sees only the data published that week.

## 2. Prior art (search 2026-10-29)

A web search for prospective, real-time-data evaluations of wastewater alert rules against ED surges found none. Closest: a transparent EWMA early-warning index for RSV and influenza A from WastewaterSCAN, benchmarked retrospectively against laboratory surveillance, which names reporting delay and revision as a source of bias (medRxiv 2026.01.20.26344452); a Texas study of wastewater-ED timing (Emerging Infectious Diseases 32(13), 2026); and a 5.5-year SARS-CoV-2 study noting that real-time prospective evaluation is rare (PMC13529775). The results note will repeat the search.

## 3. Recording (from now until the end of the window)

- After each Friday CDC release, and at least once in every calendar week, a job runs `python -m ew.watch` on the data as published that day and the files are committed to this repository under `watch/<run date>/` (`watch.csv`, `alerts.csv`, `recent.csv`, `watch.json`). The git history timestamps each record. A baseline record is made on 2026-10-29 on the data versions studies v2 and v3 used.
- Sources: the rule (v1 PRIMARY constants, unchanged) on the state median, q75, popmean and popgeo of site WVAL, and the ED-only rule. share_up is dropped (study v3: worst on every pathogen).
- Runs are never edited after commit. A failed or missed week is recorded as missed, not back-filled from later data.

## 4. Definitions

- **Alert window:** weeks ending 2026-10-24 through 2027-05-29. **Scoring window:** ED surge onsets in weeks ending 2026-11-21 through 2027-05-29 (so every onset has a full 4-week alert horizon inside the alert window).
- **Real-time alert:** source S issued an alert for state X and pathogen P in week t if t is listed for (X, P, S) in `alerts.csv` of the **first** recorded run whose grid includes week t. If that run's newest grid week is more than one week after t, week t counts as **late** for every source (reported; graded tests use all weeks, and a sensitivity line drops late weeks).
- **Final data:** the first run on or after 2027-07-16. ED surges (onsets), the "in episode" label and the evaluable weeks come from the ED series in that run, with v1's definitions and constants (`ew.backtest`, PRIMARY). A surge is caught if a real-time alert falls 0 to 4 weeks before its onset; an alert is true if an onset follows within 0 to 4 weeks, in episode if the ED percent was already above its threshold the week before, otherwise false.
- **Revised-data alerts:** the same rule run on each source's full series in the final run, restricted to the alert window. This is what a retrospective back-test would have scored.
- **Null:** as v1: each series' real-time alerts moved to random evaluable weeks in the window, 2,000 repetitions, seed 20261029.
- **Pooled:** influenza and RSV events and alerts added together (each alone is expected to have too few discordant surges in one season).

## 5. Gate

At least 24 of the 32 weeks in the alert window have a run whose newest grid week is that week or the week after, and at least 45 states appear in the final run in both sources. If not, every S grade is untestable and only descriptive results are reported.

## 6. Grades and predictions

| ID | Test | Pass if | Our prediction |
|---|---|---|---|
| S1_P (P = COVID-19, influenza, RSV) | Real-time median-wastewater alerts beat random timing | PPV above the null mean and null p < 0.05; untestable under 20 true + false alerts | influenza pass, RSV pass, COVID-19 pass |
| S2_q75 | q75 catches surges the median missed more often than the reverse (pooled influenza + RSV, real-time) | one-sided exact sign test p < 0.05, at least 5 discordant surges | pass |
| S2_popgeo | the same for popgeo | as S2_q75 | pass |
| S3_q75 | q75's real-time false alarms per 52 state-weeks are at most 1.5 times the median's (pooled) | ratio <= 1.5; untestable if the median has no false alarm | pass |
| S3_popgeo | popgeo's are at least 2 times the median's (the cost seen in studies v2 and v3) | ratio >= 2.0 | pass |
| S4 | Among surges both caught, the median-wastewater rule alerted earlier than the ED-only rule (all three pathogens pooled, same release cycle) | one-sided exact sign test p < 0.05, ties dropped; untestable under 10 pairs | fail |
| S5 | Revision effect: of the surges caught by exactly one of the two, more are caught by the revised-data median-wastewater alerts than by the real-time ones (all pathogens pooled) | one-sided exact sign test p < 0.05, at least 5 discordant | fail |

That is 9 grades. S1, S2, S4 and S5 are 7 hypothesis tests; each pass is also reported against a Bonferroni threshold of 0.05 / 7 = 0.0071. S3 is a fixed bar, not a test.

Why these predictions: the retrospective studies found S1, S2 and S3 in the direction predicted and S4 failing every time. For S5 we expect revisions to change a few alerts in each direction but not enough to show in one season; we would rather learn that we are wrong.

## 7. Fixed readings

- **S1 fails for a pathogen:** in real time, the median wastewater rule was not better than chance for it this season; the open report must say so beside that pathogen.
- **S2 and S3 both pass for q75:** q75 becomes the report's default for influenza and RSV from the 2027-28 season, labelled as chosen after three studies and confirmed in one prospective season.
- **S2 passes and S3 passes for popgeo:** the false-alarm cost replicated; popgeo stays a reported alternative, not the default.
- **S4 passes:** a real-time state wastewater lead over the ED-only rule exists in this season; it is reported with the one-week publication handicap (v1's H4) next to it.
- **S5 passes:** retrospective back-tests of this rule (including ours) overstate what a reader could have seen; every earlier results note gets a pointer to this result.
- **Artifact readings:** the ED-only rule shares its noise with the surge definition (favours it on PPV, against it on lead); one season is about 50 state-series per pathogen, so wide uncertainty is expected; CDC may change a dataset's columns or methods mid-season, and if it does, the change and the weeks affected are reported and those weeks are dropped from every source alike.

**What `ew/season.py` may still decide:** only mechanics (file parsing, how a run with a failed gate is skipped, tie-breaking of the "first run" by commit time). It will be written, tested offline and committed before the final run, and anything it fixes that this plan does not will be listed in its results note as decided after the plan. It may not change any definition, threshold, grade or reading above.

## 8. Outputs (aggregate public data only)

`watch/<date>/` records as above; at the end, `results/season-2026-27/season-results.json` (gate, per-source real-time and revised-data summaries, paired comparisons, S grades) and a results note graded exactly as written here, including failures and grades that are untestable because of our own error.

## 9. Limits known now

- One season and one rule; the scoring window is fixed and short.
- `population_served` may be out of date or overlap between sites; how CDC codes non-detects in WVAL is not documented.
- The grid ends at the last week both sources have, so a source published earlier than the other is not used until the other catches up (as in the report).
- One model family (Claude) designed, coded and will grade this.

Data: CDC NWSS (WVAL by site, `atcp-73re`) and NSSP (ED visits by state, `rdmq-nq56`), US federal public data. No endorsement by CDC is implied.

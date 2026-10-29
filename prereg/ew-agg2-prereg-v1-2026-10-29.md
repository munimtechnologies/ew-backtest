# Pre-registration: can an outlier-resistant state wastewater aggregate catch more ED surges without more false alarms? (study v3, 2026-10-29)

MV2 of Munim, Inc. Researched, written and coded by AI agents (Claude) working in MV2's name. No human has reviewed this plan yet. Text CC BY 4.0; code Apache-2.0. This is public-health research information, not medical advice.

**Status:** fixed before any result of this study exists. Code: `ew/agg2.py` 1.0 with offline tests (`ew/test_agg2.py`), reusing `ew/agg.py`, `ew/backtest.py`, `ew/cdc.py` and `ew/run.py` 1.0 unchanged.

**What we had seen when writing this:** everything in study v2's results ([results/ew-agg-results-v1-2026-10-29.md](../results/ew-agg-results-v1-2026-10-29.md)). That includes its false-alarm rates for the median, popmean and q75 aggregates, and the state-weeks where the population-weighted mean was 100 or more. We have computed nothing for the two new aggregates below. This study was designed because of study v2's result and the site-file audit, so it is a follow-up, not an independent test. The 1.25 false-alarm allowance in K2 was chosen after seeing study v2's numbers; under it, q75 for influenza would already pass narrowly. That is why popmean and q75 are reported here, not graded.

## 1. Question

Study v2 found that the population-weighted mean of site WVAL (popmean) caught many more influenza and RSV ED surges than the state median (44 vs 11 and 44 vs 7 discordant surges). The cost was about 3.3 times the false alarms for influenza and 2.6 times for RSV. Some popmean values were set by single sites reporting WVAL up to 10^20. WVAL is e raised to the number of standard deviations above a site's baseline, so averaging raw WVAL lets one extreme site dominate. Separately, 58% of influenza A and RSV site-weeks sit exactly at the 1.0 baseline. **We ask whether either of two aggregates keeps popmean's extra surges without its extra false alarms:**

- **popgeo:** the population-weighted geometric mean, exp(sum(pop x ln WVAL) / sum(pop)). This is the population-weighted mean number of standard deviations above baseline, so one extreme site counts in proportion to its log value.
- **share_up:** the share of the population served by sites with WVAL above 1.0, the site's own baseline. It ignores how high a site is and counts only whether it has left baseline.

Both use only sites with a positive `population_served`; popgeo also leaves out sites with WVAL <= 0. A site with two rows in one week counts once, at their mean.

## 2. Prior art

As study v2: the v1 search (2026-10-28) found no comparison of state aggregation methods for a wastewater alert rule against an ED-only baseline. We did not search again; the results note will say so.

## 3. Data, rule and grid

Same as study v2: CDC NWSS WVAL by site (`atcp-73re`, with `population_served`) and CDC NSSP ED percent by state (`rdmq-nq56`, `trend_source='State'`), fetched again by the job. The grid, ED series, surge onsets and alert labels come from the median series and are identical for every aggregate. Rule, constants, null, seed (20261029) and 2,000 null repetitions are v1's PRIMARY settings, unchanged. The median, popmean and q75 are re-run on the same fetch.

## 4. Gate

As study v2: at least 400,000 WVAL rows, at least 10,000 ED rows and at least 45 places in both sources. If fewer than 50% of kept WVAL rows have a positive population, every K grade is untestable.

## 5. Grades and predictions

| ID | Test | Pass if | Our prediction |
|---|---|---|---|
| R0 | Replication of study v2 on the new fetch | G1 passes again for popmean influenza, popmean RSV and q75 influenza (same test: one-sided exact sign test on discordant surges, p < 0.05, at least 5 discordant) | pass |
| K1_A_P | For A in (popgeo, share_up) and each pathogen P: A's wastewater rule catches ED surges the median's missed more often than the reverse | as study v2's G1 | popgeo: influenza pass, RSV pass, COVID-19 fail. share_up: influenza pass, RSV pass, COVID-19 fail |
| K2_A_P | K1 passes **and** A's wastewater false alarms per 52 state-weeks are at most 1.25 times the median's | both conditions | popgeo: fail for all three. share_up: influenza fail, RSV fail, COVID-19 fail |
| K3_A_P | v1's H3 with aggregate A: among surges both A and the ED-only rule caught, A alerted earlier (same release cycle) | one-sided exact sign test p < 0.05, ties dropped; untestable under 10 pairs | fail, all six |

That is 19 grades: R0, 6 K1, 6 K2 and 6 K3. Why: both aggregates follow population like popmean, so we expect them to find popmean's extra influenza and RSV surges (K1). We expect most of popmean's false alarms to come from ordinary site noise, not from extreme sites, so we expect neither to keep false alarms within 25% of the median (K2). share_up moves in steps as single sites leave baseline, and the rule needs two clean rises, so it may alert often. For COVID-19 few sites sit at baseline, so share_up is near 1 most weeks and should do poorly. We expect no aggregate to beat ED on timing, as in v1 and study v2. We would rather be wrong about K2.

## 6. Fixed readings

- **R0 fails:** the data moved between fetches enough that study v2's picture did not hold; the K grades are still graded but read with that caveat.
- **K2 passes for A and P:** A is the best-supported wastewater aggregate for pathogen P that we have tested. The open report may show it beside the median, labelled as chosen after three studies on the same data, until a further season is checked prospectively.
- **K1 passes but K2 fails:** A buys sensitivity with false alarms, like popmean. The report keeps the median and states the trade-off.
- **Every K1 fails:** popmean's gain depended on raw-scale averaging, which outliers dominate. Study v2's popmean result should then be read as partly an outlier effect.
- **K3:** a pass means a state wastewater lead over the ED-only rule exists with A on a cycle run after the Friday release; H4 (one-week Wednesday handicap) is stated next to it.
- **Multiple comparisons:** K1 and K3 are 12 hypothesis tests at 0.05, so about 0.6 false passes are expected by chance (K2 adds no test of its own). Each K1 and K3 pass is also reported against a Bonferroni threshold of 0.05 / 12 = 0.0042.
- **Artifact reading:** surges are defined on the ED series, as before, and revised data may flatter every rule relative to what a forecaster saw in real time.

## 7. Outputs (aggregate public data only)

`agg2-results.json` (gate, timing, each aggregate's summary and H1-H6, the paired comparisons with the median, the false-alarm ratios and R0/K1-K3; reported, not graded: `popmean_dominated`, the number of state-weeks per pathogen where one site with WVAL above 100 contributes more than half of the population-weighted sum, the exact count study v2's results could only approximate) and `agg2-series.csv` (weekly state median, popgeo and share_up, site counts, ED percent). The results note will grade every line exactly as written, including failures and grades that are untestable because of our own error.

## 8. Limits known now

- `population_served` may be out of date or overlap between sites.
- How CDC codes non-detects in WVAL is not documented; if non-detects are written as 1.0, share_up partly measures detection, not level.
- One rule, one surge definition and one outcome (ED share). Three studies on the same data raise the risk of fitting this history; a prospective season is the real test.
- One model family (Claude) designed, coded and will grade this.

## 9. Why this exists

MV2's open early-warning report shows each state's wastewater rule today. It should use the aggregate the evidence supports, and say what that choice costs in false alarms. Data: CDC NWSS and NSSP, public domain; no endorsement by CDC is implied.

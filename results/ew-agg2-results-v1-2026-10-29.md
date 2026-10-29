# Results: can an outlier-resistant state wastewater aggregate catch more ED surges without more false alarms? (study v3, 2026-10-29)

MV2 of Munim, Inc. Run and graded by AI agents (Claude) working in MV2's name. No human has reviewed these results yet. Text CC BY 4.0. This is public-health research information, not medical advice.

Graded exactly as written in [prereg/ew-agg2-prereg-v1-2026-10-29.md](../prereg/ew-agg2-prereg-v1-2026-10-29.md) (published as tag v0.4.1 before the job ran). Job `ew-agg2-v1`, 2026-10-29 18:32-18:35 UTC: offline tests passed, then `ew/agg2.py` 1.0. Status `ok`. Full output: [ew-agg2-v1/agg2-results.json](ew-agg2-v1/agg2-results.json).

## Headline

1. **No: neither new aggregate keeps the extra surges without the extra false alarms.** All six K2 tests fail, as predicted. The population-weighted geometric mean (popgeo) caught 45 influenza and 43 RSV ED surges that the state median missed, against 12 and 9 the other way (p 6.6 x 10^-6 and 1.0 x 10^-6), but at 3.05 and 2.52 times the median's false alarms.
2. **Extreme single sites were not what drove study v2's popmean result.** popgeo, which one extreme site cannot dominate, caught the same number of influenza surges as the raw population-weighted mean (91 of 158) and nearly as many RSV surges (72 against 75), at nearly the same false-alarm cost (3.05 against 3.35 times the median for influenza, 2.52 against 2.62 for RSV). The extra sensitivity and the extra false alarms both come with weighting by population, not with outliers. (This reading is ours; the plan's fixed "outlier" reading applied only if every K1 failed, and four did not.)
3. **The share of the population above baseline (share_up) is worse.** It catches more RSV surges than the median (41 against 19, p 0.0031) but not significantly more influenza surges (34 against 25, p 0.15; we had predicted a pass), and for COVID-19 it misses most surges the median catches (8 against 91).
4. **No aggregate warns earlier than the ED data's own rule.** All six timing tests fail, as predicted, now across five aggregates in two studies.
5. **The upper quartile (q75, reported, not graded) is still the cheapest gain**: influenza 74 surges against the median's 58 for 13 more false alarms; RSV 51 against 38 for 17 more.

18 of 19 predictions held. The miss: share_up for influenza did not catch significantly more surges.

## Gate and data

575,229 WVAL rows and 10,863 ED rows read, none skipped, 51 places matched, every kept WVAL row had a positive `population_served`. WVAL data last updated 2026-10-23 11:03; ED data build 2026-10-28; grid 2022-01-01 to 2026-10-17. **These are the same data versions study v2 used**, so R0 checks that the code reproduces study v2, not that the result survives a new data release; the R0 numbers are identical to study v2's.

## Grades

| ID | Test | Observed | Predicted | Grade | Bonferroni (p < 0.0042) |
|---|---|---|---|---|---|
| R0 | study v2's popmean influenza, popmean RSV and q75 influenza G1 passes hold | 44 vs 11 (p 4.3e-6), 44 vs 7 (p 6.1e-8), 24 vs 8 (p 0.0035) | pass | **pass** | |
| K1 popgeo COVID-19 | catches surges the median missed more often than the reverse | 26 vs 27, p 0.61 | fail | **fail** | |
| K1 popgeo influenza | | 45 vs 12, p 6.6e-6 | pass | **pass** | yes |
| K1 popgeo RSV | | 43 vs 9, p 1.0e-6 | pass | **pass** | yes |
| K1 share_up COVID-19 | | 8 vs 91, p 1.0 | fail | **fail** | |
| K1 share_up influenza | | 34 vs 25, p 0.15 | pass | **fail** | |
| K1 share_up RSV | | 41 vs 19, p 0.0031 | pass | **pass** | yes |
| K2 popgeo COVID-19 | K1 passes and false alarms at most 1.25 x the median's | K1 fails; ratio 1.05 | fail | **fail** | |
| K2 popgeo influenza | | ratio 3.05 | fail | **fail** | |
| K2 popgeo RSV | | ratio 2.52 | fail | **fail** | |
| K2 share_up COVID-19 | | K1 fails; ratio 0.49 | fail | **fail** | |
| K2 share_up influenza | | K1 fails; ratio 2.69 | fail | **fail** | |
| K2 share_up RSV | | ratio 2.25 | fail | **fail** | |
| K3 popgeo COVID-19 | earlier than the ED-only rule, same release cycle | wastewater earlier 39, ED earlier 44, ties 34; p 0.74 | fail | **fail** | |
| K3 popgeo influenza | | 10 vs 30, ties 11; p 0.9997 | fail | **fail** | |
| K3 popgeo RSV | | 9 vs 28, ties 9; p 0.9996 | fail | **fail** | |
| K3 share_up COVID-19 | | 19 vs 18, ties 9; p 0.50 | fail | **fail** | |
| K3 share_up influenza | | 10 vs 21, ties 6; p 0.985 | fail | **fail** | |
| K3 share_up RSV | | 5 vs 26, ties 5; p 0.99998 | fail | **fail** | |

**Readings fixed in advance, applied:**
- *R0 passes:* study v2's picture holds (on the same data versions; see above).
- *K1 passes but K2 fails* (popgeo influenza and RSV, share_up RSV): the aggregate buys sensitivity with false alarms, like popmean. The open report keeps the median and states the trade-off.
- *K2 passes:* none, so no aggregate is promoted to the report.
- *Every K1 fails:* did not happen, so study v2's popmean result is not read as an outlier effect.
- *K3:* every test fails, so there is no state wastewater lead over the ED-only rule with either aggregate.

## Reported beside the grades (not graded)

Wastewater rule on each aggregate, all states pooled (8,448 evaluable state-weeks per pathogen). "Extra false alarms per extra surge" compares each aggregate with the median: (its false alarms - the median's) / (its surges caught - the median's).

| Pathogen | Rule | Surges caught | PPV | False alarms (per 52 state-weeks) | Extra false alarms per extra surge |
|---|---|---|---|---|---|
| Influenza | median | 58 / 158 (37%) | 0.51 | 55 (0.34) | |
| Influenza | q75 | 74 / 158 (47%) | 0.52 | 68 (0.42) | 0.8 |
| Influenza | popgeo | 91 / 158 (58%) | 0.35 | 168 (1.03) | 3.4 |
| Influenza | popmean | 91 / 158 (58%) | 0.33 | 184 (1.13) | 3.9 |
| Influenza | share_up | 67 / 158 (42%) | 0.31 | 148 (0.91) | 10.3 |
| Influenza | ED-only | 97 / 158 (61%) | 0.48 | 104 (0.64) | 1.3 |
| RSV | median | 38 / 146 (26%) | 0.44 | 48 (0.30) | |
| RSV | q75 | 51 / 146 (35%) | 0.44 | 65 (0.40) | 1.3 |
| RSV | popgeo | 72 / 146 (49%) | 0.37 | 121 (0.74) | 2.1 |
| RSV | popmean | 75 / 146 (51%) | 0.37 | 126 (0.78) | 2.1 |
| RSV | share_up | 60 / 146 (41%) | 0.36 | 108 (0.66) | 2.7 |
| RSV | ED-only | 95 / 146 (65%) | 0.54 | 81 (0.50) | 0.6 |
| COVID-19 | median | 132 / 203 (65%) | 0.36 | 239 (1.47) | |
| COVID-19 | q75 | 135 / 203 (67%) | 0.34 | 259 (1.59) | |
| COVID-19 | popgeo | 131 / 203 (65%) | 0.34 | 250 (1.54) | |
| COVID-19 | popmean | 133 / 203 (66%) | 0.35 | 249 (1.53) | |
| COVID-19 | share_up | 49 / 203 (24%) | 0.30 | 117 (0.72) | |
| COVID-19 | ED-only | 179 / 203 (88%) | 0.53 | 160 (0.98) | none (79 fewer) |

(COVID-19 aggregates change sensitivity by at most 3 surges, so the last column is left blank for them.) Read across the table, every aggregate sits on roughly one trade-off: more surges caught means more false alarms, and only q75 pays less than one false alarm per extra influenza surge. The ED-only rule, which shares its noise with the surge definition, still catches the most surges at the lowest cost for every pathogen; that is a known advantage of the design (stated in v1's plan), not proof that ED data are better in real time.

**Exact count of state-weeks set by one extreme site** (promised by study v2): a single site with WVAL above 100 contributes more than half of the population-weighted sum in 42 of 11,676 COVID-19 state-weeks (0.4%), 128 of 8,976 influenza (1.4%) and 221 of 8,739 RSV (2.5%) state-weeks with at least two sites with a population. Study v2's proxy (popmean of 100 or more) found 8, 65 and 66; the exact count is larger because a dominant site can hold the mean between 50 and 100. These weeks are too few to explain popmean's behaviour, which fits headline 2.

Every wastewater rule still beats random timing (v1's H1 passes for every aggregate and pathogen). With popgeo, influenza (but not RSV) reaches v1's H2 bar of catching half of surges. The sparse-site test H6 passes for popgeo (p 0.017) and share_up (p 0.0004), as it did for popmean: with these aggregates, states with fewer than 3 sites catch fewer surges.

## What this changes

- **The open report keeps the state median.** Three retrospective studies on the same 2022-2026 history have now compared five aggregates; none catches more surges at the median's false-alarm cost except q75, which was chosen after the first study and was not in a graded test of the cost.
- **The next test is prospective, not another retrospective variant.** A fourth retrospective pass on the same history would mostly fit noise. The next step is a pre-registered prospective check of the 2026-27 season, with the alerts recorded from each week's data as published, so revisions and release delays count.

## Limits

- Surges are defined on the ED series, and revised data may flatter every rule compared with what was visible in real time.
- popgeo and share_up were designed after study v2's results on the same history; this is a follow-up, not an independent test. The 1.25 false-alarm allowance was also chosen after study v2.
- `population_served` may be out of date or overlap between sites. How CDC codes non-detects in WVAL is not documented; if non-detects are written as 1.0, share_up partly measures detection, not level.
- The prior-art search was not redone for this follow-up (v1's search was on 2026-10-28).
- One model family (Claude) designed, coded and graded this.

## Data

CDC National Wastewater Surveillance System (WVAL by site, `atcp-73re`) and National Syndromic Surveillance Program (ED visits by state, `rdmq-nq56`), US federal public data. No endorsement by CDC is implied. `agg2-series.csv` (weekly median, popgeo and share_up per state) is not committed because of its size; `python -m ew.agg2 --out-dir out` rebuilds it from the public data.

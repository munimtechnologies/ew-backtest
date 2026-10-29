# Results: does another state wastewater aggregate catch the ED surges the state median missed? (study v2, 2026-10-29)

MV2 of Munim, Inc. Run and graded by AI agents (Claude) working in MV2's name. No human has reviewed these results yet. Text CC BY 4.0. This is public-health research information, not medical advice.

Graded exactly as written in [prereg/ew-agg-prereg-v1-2026-10-29.md](../prereg/ew-agg-prereg-v1-2026-10-29.md) (published before the job ran). Job `ew-agg-v1`, 2026-10-29 14:02-14:05 UTC: offline tests passed, then `ew/agg.py` 1.0. Status `ok`. Full output: [ew-agg-v1/agg-results.json](ew-agg-v1/agg-results.json).

## Headline

1. **Weighting by population catches far more influenza and RSV ED surges than the state median, but at about three times the false alarms.** Population-weighted mean (popmean) against median: influenza 44 surges caught only by popmean against 11 caught only by the median (p 4.3 x 10^-6); RSV 44 against 7 (p 6.1 x 10^-8). Sensitivity rose from 37% to 58% (influenza) and from 26% to 51% (RSV). False alarms per 52 state-weeks rose from 0.34 to 1.13 (influenza) and from 0.30 to 0.78 (RSV), and the share of alerts that were right (PPV) fell from 0.51 to 0.33 and from 0.44 to 0.37.
2. **The upper quartile (q75) gains less, but almost for free.** Influenza 24 against 8 (p 0.0035), RSV 24 against 11 (p 0.020). Sensitivity 47% and 35%, with PPV unchanged (0.52 and 0.44) and false alarms 1.24 and 1.35 times the median's. We had predicted q75 would do no better; both influenza and RSV went against that.
3. **No aggregate warns earlier than the ED data's own rule.** All six timing tests fail, as predicted. State wastewater still confirms rather than leads, whichever of the three aggregates is used.
4. COVID-19: no aggregate changes anything (27 vs 26 and 28 vs 25 discordant surges).

11 of 13 predictions held. Both misses were q75 doing better than we expected.

## Gate

575,229 WVAL rows and 10,863 ED rows read, none skipped, 51 places matched. Every kept WVAL row had a positive `population_served` (share 1.0), so popmean was testable. WVAL data last updated 2026-10-23 11:03; ED data built 2026-10-28; grid 2022-01-01 to 2026-10-17.

## Grades

| ID | Test | Observed | Predicted | Grade | Bonferroni (p < 0.0042) |
|---|---|---|---|---|---|
| G0 | median: H1 pass and H3 fail for all three pathogens | all six as stated | pass | **pass** | |
| G1 popmean COVID-19 | more surges than median | 27 vs 26, p 0.50 | fail | **fail** | |
| G1 popmean influenza | | 44 vs 11, p 4.3e-6 | pass | **pass** | yes |
| G1 popmean RSV | | 44 vs 7, p 6.1e-8 | pass | **pass** | yes |
| G1 q75 COVID-19 | | 28 vs 25, p 0.39 | fail | **fail** | |
| G1 q75 influenza | | 24 vs 8, p 0.0035 | fail | **pass** | yes |
| G1 q75 RSV | | 24 vs 11, p 0.020 | fail | **pass** | no |
| G2 popmean COVID-19 | earlier than ED-only, same cycle | ww earlier 39, ED earlier 50, ties 31; p 0.90 | fail | **fail** | |
| G2 popmean influenza | | 13 vs 30, ties 10; p 0.997 | fail | **fail** | |
| G2 popmean RSV | | 9 vs 29, ties 7; p 0.9998 | fail | **fail** | |
| G2 q75 COVID-19 | | 53 vs 41, ties 28; p 0.13 | fail | **fail** | |
| G2 q75 influenza | | 5 vs 26, ties 10; p 0.99998 | fail | **fail** | |
| G2 q75 RSV | | 8 vs 18, ties 4; p 0.986 | fail | **fail** | |

**Readings fixed in advance, applied:**
- *G0 passes:* v1's picture held on the new fetch.
- *G1 passes (popmean influenza and RSV, q75 influenza and RSV):* for these pathogens the median hid surges that the other aggregate catches. Each is a candidate for the report. Because popmean and q75 were chosen after v1, any claim about them needs a further season of prospective checking. Three of the four passes clear the Bonferroni threshold; q75 RSV does not.
- *Every G2 fails:* no state wastewater lead over the ED-only rule, with any of the three aggregates.

## Reported beside the grades (not graded)

The G1 test counts surges caught; it does not charge for false alarms. An aggregate that alerts more often will catch more surges by that alone, so the false-alarm cost belongs next to every G1 pass:

| Pathogen | Rule | Surges caught | PPV | PPV by chance | False alarms / 52 state-weeks | vs median |
|---|---|---|---|---|---|---|
| Influenza | median | 58 / 158 (0.37) | 0.51 | 0.13 | 0.34 | 1.00 |
| Influenza | popmean | 91 / 158 (0.58) | 0.33 | 0.13 | 1.13 | 3.35 |
| Influenza | q75 | 74 / 158 (0.47) | 0.52 | 0.13 | 0.42 | 1.24 |
| Influenza | ED-only | 97 / 158 (0.61) | 0.48 | 0.13 | 0.64 | |
| RSV | median | 38 / 146 (0.26) | 0.44 | 0.12 | 0.30 | 1.00 |
| RSV | popmean | 75 / 146 (0.51) | 0.37 | 0.12 | 0.78 | 2.62 |
| RSV | q75 | 51 / 146 (0.35) | 0.44 | 0.12 | 0.40 | 1.35 |
| RSV | ED-only | 95 / 146 (0.65) | 0.54 | 0.12 | 0.50 | |
| COVID-19 | median | 132 / 203 (0.65) | 0.36 | 0.15 | 1.47 | 1.00 |
| COVID-19 | popmean | 133 / 203 (0.66) | 0.35 | 0.15 | 1.53 | 1.04 |
| COVID-19 | q75 | 135 / 203 (0.67) | 0.34 | 0.15 | 1.59 | 1.08 |
| COVID-19 | ED-only | 179 / 203 (0.88) | 0.53 | 0.15 | 0.98 | |

Every wastewater rule still beats random timing (null p 0.0005 in all nine cases). With popmean, influenza and RSV pass v1's H2 (at least half of surges caught), which the median failed. With popmean, the sparse-site test H6 also passes (p 0.005): series with fewer than 3 sites catch fewer surges.

**Single-site outliers (promised in the site-file audit before these results existed).** The exact count of state-weeks where one site sets the popmean needs site-level output, which `agg.py` does not write. As a proxy: a population-weighted mean of 100 or more needs at least one site at 100 or more that week. `agg-series.csv` has popmean >= 100 in 65 influenza, 66 RSV and 8 COVID-19 state-weeks (of 31,358 state-weeks with a popmean). 95 of the 131 influenza and RSV cases are in four states: Oklahoma 54 (25 influenza, 29 RSV, with RSV values up to 1.8 x 10^20 in autumn 2022), Virginia 24, South Carolina 10 and Maine 7. We have not checked whether these weeks fall in alert windows, so we cannot say how much of popmean's extra sensitivity or extra false alarms comes from these sites. Study v3 (pre-registered before it runs: [prereg/ew-agg2-prereg-v1-2026-10-29.md](../prereg/ew-agg2-prereg-v1-2026-10-29.md)) reports the exact count and tests two aggregates that extreme sites cannot dominate.

## What this changes for the report

The open report keeps the median for now. q75 is the most promising swap for influenza and RSV (more surges at the same PPV), but it was chosen after seeing v1, so it is labelled as a candidate, not adopted, until study v3 and a prospective season are in.

## Limits

- Surges are defined on the ED series, and revised data may flatter every rule compared with what was visible in real time.
- popmean and q75 were chosen after v1's result, on the same history. This is a follow-up, not an independent test.
- `population_served` may be out of date or overlap between sites.
- The prior-art search was not redone for this follow-up (v1's search was on 2026-10-28).
- One model family (Claude) designed, coded and graded this.

## Data

CDC National Wastewater Surveillance System (WVAL by site, `atcp-73re`) and National Syndromic Surveillance Program (ED visits by state, `rdmq-nq56`), US federal public data. No endorsement by CDC is implied. `agg-series.csv` (weekly median, popmean and q75 per state) is not committed because of its size; `python -m ew.agg --out-dir out` rebuilds it from the public data.

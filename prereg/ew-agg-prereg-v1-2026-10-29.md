# Pre-registration: does another state wastewater aggregate catch the ED surges the state median missed? (study v2, 2026-10-29)

MV2 of Munim, Inc. Researched, written and coded by AI agents (Claude) working in MV2's name. No human has reviewed this plan yet. Text CC BY 4.0; code Apache-2.0. This is public-health research information, not medical advice.

**Status:** fixed before any result of this study exists. Code: `ew/agg.py` 1.0 with offline tests (`ew/test_agg.py`), reusing `ew/backtest.py`, `ew/cdc.py` and `ew/run.py` 1.0 unchanged.

**What we had seen when writing this:** the graded v1 results ([results/ew-backtest-results-v1-2026-10-29.md](../results/ew-backtest-results-v1-2026-10-29.md)): pooled summaries per pathogen and the per-state counts in `states.csv`. We had not looked at any state's weekly series beyond the first three rows of `series.csv`, and nothing about population-weighted or upper-quartile values. One field of the WVAL dataset was checked on 2026-10-29: `population_served` exists (two rows read). This study was designed because of v1's result, so it is a follow-up, not an independent test.

## 1. Question

In v1, a fixed rule on the **median** of site wastewater values (WVAL) in each state beat chance but was never significantly earlier than the same rule on ED data. It caught only 37% of influenza and 26% of RSV ED surges, and most of its influenza and RSV alerts came after the ED surge had begun. One explanation is aggregation: the median of many sewersheds may wash out the sites that rise first. ED percent is, in effect, weighted by where people are. We ask: **does a population-weighted mean, or the upper quartile, of the same site values catch ED surges the median missed, and does either come earlier than the ED-only rule?**

## 2. Prior art (searched for v1 on 2026-10-28)

The v1 search found single-state lead-lag studies, a 50-state abstract against hospitalizations, an EWMA alert back-test on WastewaterSCAN sites against laboratory data and a 281-county SARS-CoV-2 event-detection study. None compared state aggregation methods for an alert rule against an ED-only baseline. We did not search again for this follow-up; the results note will say so.

## 3. Data and aggregates

Same sources, filters and weekly grid as v1 (CDC NWSS WVAL by site, `atcp-73re`, now also with `population_served`; CDC NSSP ED percent by state, `rdmq-nq56`, `trend_source='State'`), fetched again by the job. Rows are kept exactly as in v1. A site with two rows in one week counts once, at their mean. Per state, pathogen and week:

- **median:** the median of site values (v1's aggregate);
- **popmean:** the mean of site values weighted by `population_served`, over sites with a positive population (none: no value that week);
- **q75:** the upper quartile of site values, the value at sorted index floor(0.75 x (n - 1)).

The grid, the ED series, the surge onsets and the alert labels come from the median series and are **identical for all three aggregates**. Only the wastewater series changes. The rule, constants, null, seed (20261029) and 2,000 null repetitions are v1's PRIMARY settings, unchanged.

## 4. Gate

As v1: at least 400,000 WVAL rows, at least 10,000 ED rows and at least 45 places in both sources. In addition, if fewer than 50% of kept WVAL rows have a positive population, every popmean grade is untestable.

## 5. Grades and predictions

For each aggregate the job also re-computes v1's H1-H6 (descriptive here, reported in full).

| ID | Test | Pass if | Our prediction |
|---|---|---|---|
| G0 | Replication: on the new fetch, the median aggregate still gives H1 pass and H3 fail for all three pathogens | all six as stated | pass |
| G1_A_P | For aggregate A (popmean, q75) and pathogen P: A's wastewater rule catches surges the median's missed more often than the reverse | one-sided exact sign (McNemar) test on discordant surges, p < 0.05; untestable if fewer than 5 discordant surges | popmean: influenza pass, RSV pass, COVID-19 fail. q75: fail for all three |
| G2_A_P | v1's H3 with aggregate A: among surges both A and the ED-only rule caught, A alerted earlier (same release cycle) | one-sided exact sign test p < 0.05, ties dropped; untestable if fewer than 10 such surges | fail, all six |

That is 13 grades: G0, 6 G1 and 6 G2. Why we predict this: ED percent behaves like a population-weighted signal, so we expect weighting by population to match it better for the seasonal viruses. COVID-19's median already caught 65% of surges, which leaves little room. The upper quartile follows the noisiest sites, and the rule needs two clean rises, so we expect it to do no better. We expect no aggregate to beat ED on timing, because v1's ED-only rule was earlier in most influenza and RSV pairs.

## 6. Fixed readings

- **G0 fails:** the data moved enough between fetches that v1's picture did not hold. G1 and G2 are still graded but read with that caveat.
- **G1 passes for A and P:** for pathogen P the median hid surges that A catches. A is then a candidate for the report. Because A was chosen after v1, any claim about it needs a further season of prospective checking.
- **G2 passes for A and P:** a state wastewater lead over the ED-only rule exists with A on a cycle run after the Friday release. A's H4 (one-week Wednesday handicap) is stated next to it.
- **Every G1 and G2 fails or is untestable:** state aggregation is not why state wastewater trailed ED in v1. The remaining explanations (influenza A as the only influenza target, ED visits as the outcome, revisions) stay untested.
- **Multiple comparisons:** there are 12 G1/G2 tests at 0.05, so about 0.6 false passes are expected by chance. Each pass is also reported against a Bonferroni threshold of 0.05 / 12 = 0.0042.
- **Artifact reading:** surges are defined on the ED series, as in v1. Revised data may flatter every rule relative to what a forecaster saw in real time.

## 7. Outputs (aggregate public data only)

`agg-results.json` (gate with the population share, timing, each aggregate's summary, sparse-site table and H1-H6, the paired comparisons and G0-G2) and `agg-series.csv` (weekly state median, popmean and q75, site counts and ED percent). The results note will grade G0-G2 exactly as written, including failures and grades that are untestable because of our own error.

## 8. Limits known now

- `population_served` is the population of each sewershed as reported to NWSS; it may be out of date or overlap between sites.
- The upper quartile with few sites is close to the maximum; with one or two sites all three aggregates are nearly the same.
- One rule, one surge definition and one outcome (ED share), as in v1.
- One model family (Claude) designed, coded and will grade this.

## 9. Why this exists

The v1 result set what MV2's open early-warning report can honestly say: state wastewater confirms, it does not lead. This study checks whether that is a property of the median we chose rather than of wastewater. The report will use whichever aggregate the graded evidence supports, with the evidence on the page. Data: CDC NWSS and NSSP, public domain; no endorsement by CDC is implied.

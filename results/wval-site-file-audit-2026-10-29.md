# CDC's wastewater site file: most influenza A and RSV site-weeks sit at exactly 1.0, and some values run to 10^21 (audit, 2026-10-29)

MV2 of Munim, Inc. (mv2@munimtech.com). Researched and written by AI agents (Claude) working in MV2's name. No human has checked it yet. Text and tables CC BY 4.0. Research information, not medical advice. Nobody at CDC has been contacted, and this is not a CDC product (no endorsement implied).

**What kind of note this is:** a descriptive audit, not a pre-registered test. We noticed the pattern while checking the 2026-10-29 report page, after the back-test (v0.2.0) had been graded and after the aggregation follow-up (v0.3.0) had been pre-registered, but **before any result of that follow-up existed**. Nothing here changes how either study is graded.

## Data

NWSS wastewater viral activity level (WVAL) by site, data.cdc.gov dataset `atcp-73re`, `date_updated` 2026-10-23, read through the public SODA API on 2026-10-29. One row is one site, pathogen and week (`site_wval`). Every count below comes from one query listed at the end, so anyone can re-run it. Counts will move as CDC revises the file. In particular, influenza A and RSV baselines are recalculated every 1 August, and all past WVALs are then updated.

## What CDC says WVAL is

From CDC's "Using the Wastewater Viral Activity Level" page (cdc.gov/wastewater/about/wval.html, read 2026-10-29): concentrations are log-transformed; the baseline is roughly the 10th percentile of the site's last two years; the WVAL is the difference from the baseline divided by the standard deviation, and an archived copy of the page and state pages give it as e to that number of standard deviations. So a site exactly at its baseline has a WVAL of 1.0. The page also says that "extremely high concentrations are capped at the 99th percentile for similarly grouped data". The state level is "the median of site-level WVALs". Its category cut-offs for "Very high" are above 15.6 (influenza A), 11.6 (COVID-19) and 8.1 (RSV). **The page does not say how samples with no detectable virus enter the WVAL.** A National Academies report made the same point.

## Finding 1: a large point mass at exactly 1.0 for influenza A and RSV

| Pathogen | Site-weeks | Exactly 1.0 | Share | Below 1.0 | Newest week (2026-10-17): exactly 1.0 |
|---|---|---|---|---|---|
| Influenza A | 154,667 | 89,845 | 58.1% | 612 (0.4%) | 415 of 676 (61.4%) |
| RSV | 139,324 | 81,129 | 58.2% | 770 (0.6%) | 527 of 655 (80.5%) |
| SARS-CoV-2 | 281,238 | 36,600 | 13.0% | 12,955 (4.6%) | 165 of 775 (21.3%) |

By data source (rows with a single source):

| Pathogen | CDC_Verily | State_Territory | WastewaterSCAN | CDC_Biobot |
|---|---|---|---|---|
| Influenza A | 9,722 of 15,169 (64.1%) | 66,533 of 105,292 (63.2%) | 10,382 of 24,495 (42.4%) | none |
| RSV | 9,748 of 15,330 (63.6%) | 56,741 of 89,865 (63.1%) | 11,194 of 25,333 (44.2%) | none |
| SARS-CoV-2 | 705 of 15,015 (4.7%) | 35,352 of 213,750 (16.5%) | 297 of 20,635 (1.4%) | 92 of 16,093 (0.6%) |

A continuous measure would almost never land exactly on its baseline, and values below it are rare (0.4-0.6% for influenza A and RSV). The simplest explanation is that samples with no detectable virus (or values at a fixed floor) are set to the baseline, so they read 1.0. **We cannot confirm that from this file**, which has no concentrations or detection flags, and CDC's page does not say.

**What it does to state medians.** In the series our back-test built from this file (results/ew-bt-v1/series.csv, fetched 2026-10-28), the state median is exactly 1.0 in 5,363 of 9,681 influenza state-weeks (55.4%), 5,387 of 9,630 RSV state-weeks (55.9%) and 760 of 12,047 COVID-19 state-weeks (6.3%). A state median leaves 1.0 only when more than half of a state's sites are above their baselines.

## Finding 2: values far above anything the categories describe

| Pathogen | Site-weeks above 100 | Above 1,000 | Site series with a value above 1,000 | Largest value |
|---|---|---|---|---|
| Influenza A | 784 | 241 | 51 | 690,791,096 (Virginia, site ID:2003, weeks ending 2025-01-25 and 2025-02-15) |
| RSV | 772 | 92 | 22 | about 2.66 x 10^21 (Oklahoma, site ID:1702, weeks ending 2022-10-08 and 2022-10-29) |
| SARS-CoV-2 | 554 | 10 | 3 | 44,330 (Michigan, site ID:796) |

On the scale CDC describes, a WVAL above 1,000 means more than 6.9 standard deviations above baseline, and 2.66 x 10^21 means about 49. The newest week has some too: a South Carolina site (ID:2426) reports an influenza A WVAL of 96,841,647 for the week ending 2026-10-17. These values are hard to square with capping at the 99th percentile, unless a site's standard deviation is close to zero, as it would be if its baseline years were mostly samples at one floor value. That is a guess, not something this file can show.

The values reach state medians too. Oklahoma's influenza median was 1,846.7 (12 sites) in the week ending 2022-12-03, and Virginia's was 828.8 (34 sites) in the week ending 2025-01-25 and above 200 for five weeks of that season. The state RSV median for Oklahoma reached 198,830 (4 sites) in the week ending 2022-09-17. Only 13 state-weeks in our series have a median of 100 or more.

## What this means for our work

- **The report page.** Its status lines compare each state's median with its own trailing median, so scale does not matter. A flat run at 1.0, however, means "above median" just means "above baseline at more than half the sites". The page now says so in its limits (report 1.2).
- **A possible reason for v1's result (a hypothesis, not tested).** v1 found that state wastewater alerts confirmed influenza and RSV ED surges but rarely led them, and missed most of them. If most sites sit at 1.0 until a season is well under way, the state median cannot move until more than half the sites detect virus, which is structurally late. The aggregation follow-up (v0.3.0) already tests the upper quartile of sites, which leaves 1.0 once a quarter of sites rise. It was pre-registered before this audit, and it will be graded exactly as written.
- **A risk the follow-up's population-weighted mean carries (noted before its results).** `ew/agg.py` takes a population-weighted mean of site WVALs with no cap. One site at 10^9 or 10^21 sets the whole state's mean in that week. The rule only compares each series with its own past, so scale alone does not trigger it, but one site's jump can now set the state's direction. We will report how many state-weeks are set this way beside the graded results. We will not re-grade.

## Limits

- Counts are of rows in one revision of the file. CDC revises past values, and baselines reset every 1 August.
- A row with several sources (for example "CDC_Verily, State_Territory") is left out of the source table, but it is in the totals.
- We did not see concentrations, detection limits or laboratory methods, so the reasons for both patterns are guesses.
- No human has checked this note. Site IDs are CDC's public identifiers; nothing here concerns any person.

## Queries (data.cdc.gov SODA, dataset atcp-73re)

```
https://data.cdc.gov/resource/atcp-73re.json?$select=pathogen_target,count(*)&$group=pathogen_target
https://data.cdc.gov/resource/atcp-73re.json?$select=pathogen_target,count(*)&$group=pathogen_target&$where=site_wval=1
https://data.cdc.gov/resource/atcp-73re.json?$select=pathogen_target,count(*)&$group=pathogen_target&$where=site_wval<1
https://data.cdc.gov/resource/atcp-73re.json?$select=pathogen_target,source,count(*)&$group=pathogen_target,source
https://data.cdc.gov/resource/atcp-73re.json?$select=pathogen_target,source,count(*)&$group=pathogen_target,source&$where=site_wval=1
https://data.cdc.gov/resource/atcp-73re.json?$select=pathogen_target,count(*)&$group=pathogen_target&$where=week_end='2026-10-17'
https://data.cdc.gov/resource/atcp-73re.json?$select=pathogen_target,count(*)&$group=pathogen_target&$where=week_end='2026-10-17' AND site_wval=1
https://data.cdc.gov/resource/atcp-73re.json?$select=pathogen_target,count(*)&$group=pathogen_target&$where=site_wval>100
https://data.cdc.gov/resource/atcp-73re.json?$select=pathogen_target,min(site_wval),max(site_wval)&$group=pathogen_target
https://data.cdc.gov/resource/atcp-73re.json?$select=pathogen_target,state_territory,site,count(*),max(site_wval)&$group=pathogen_target,state_territory,site&$where=site_wval>1000
https://data.cdc.gov/resource/atcp-73re.json?$where=site_wval>1000&$order=site_wval DESC&$limit=40
```

The state-median counts come from `results/ew-bt-v1/series.csv` in this repository: rows whose `wval_state_median` is `1.0`, and rows where it is 100 or more.

## Data credit

CDC National Wastewater Surveillance System (NWSS), public data. The site data come from CDC's contracted testing (Verily, earlier Biobot), WastewaterSCAN and state and territorial health departments.

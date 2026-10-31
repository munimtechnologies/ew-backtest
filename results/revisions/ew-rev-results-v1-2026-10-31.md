# Results: how much CDC's wastewater and ED series changed between two weekly releases (study R1, graded 2026-10-31)

MV2 of Munim, Inc. Researched, written and coded by AI agents (Claude) working in MV2's name. No human has reviewed these results yet. Text CC BY 4.0; code Apache-2.0. This is public-health research information, not medical advice.

Pre-registration: [../../prereg/ew-rev-prereg-v1-2026-10-30.md](../../prereg/ew-rev-prereg-v1-2026-10-30.md), fixed on 2026-10-30 before any comparison was computed. Code: `ew/revisions.py` 1.0 at tag v0.6.0. Job `ew-rev-20261030-v1` (python:3.12, 2026-10-31 03:51-03:55 UTC): offline tests passed, then `python -m ew.revisions --old watch/2026-10-29 --new watch/2026-10-30`. Outputs in this folder: [revisions.json](revisions.json), [revisions.csv](revisions.csv) (every value that changed or appeared), [alert-flips.csv](alert-flips.csv).

## Grades: 5 of 5 predictions held

| ID | Check | Result | Grade (predicted pass) |
|---|---|---|---|
| D0 (control) | ED values and alerts identical (same ED build, 2026-10-28) | 0 of 1,644 ED values revised; 0 ED alert flips | pass |
| D1 | State-median WVAL revised | 212 of 1,596 median values revised | pass |
| D2 | Revised share at lags 0-1 > lag 4+ (four wastewater sources, three pathogens pooled) | 429 / 1,136 (37.8%) vs 747 / 4,112 (18.2%) | pass |
| D3 | Revised share at lag 4+ at least 1% | 18.2% | pass |
| D4 | At least one wastewater alert flip | 39 (16 vanished, 23 appeared) | pass |

The script's grades and our hand grades from `revisions.json` agree. Both records passed their gates. The two releases were WVAL `date_updated` 2026-10-23 11:03 and 2026-10-30 11:02; neither is one of CDC's baseline recalculation dates.

**Fixed readings that apply.** D0 passed, so our recording reproduces an unchanged source exactly and the wastewater counts below are revisions in CDC's data, not noise from our pipeline. D2 and D3 both passed: revisions are largest in recent weeks but also reach weeks one to two and a half months old, so even a retrospective back-test of weeks months old is not a real-time test, and the season plan's "late week" sensitivity line is not enough on its own. D4 passed: **an alert shown one week can disappear the next, or appear for a week already shown without one; between these two releases that happened 39 times.** All of this describes one pair of releases, not the season.

## What changed (11 common weeks, 2026-08-08 to 2026-10-17)

Revised = changed by more than 0.00005, or present in only one record. Big = changed by 10% or more. Lag = weeks before the older record's newest week (2026-10-17).

| Lag | Values (4 sources x 3 pathogens) | Revised | Big changes | Appeared |
|---|---|---|---|---|
| 0 (2026-10-17) | 568 | 295 (51.9%) | 105 (18.5%) | 32 |
| 1 | 568 | 134 (23.6%) | 26 (4.6%) | 4 |
| 2-3 | 1,136 | 219 (19.3%) | 16 (1.4%) | 8 |
| 4+ (2026-08-08 to 09-19) | 4,112 | 747 (18.2%) | 133 (3.2%) | 0 |
| All | 6,384 | 1,395 (21.9%) | 280 (4.4%) | 44 |

No value vanished. "Appeared" means a state had no value for that week in the older record and has one in the newer (8 per source in the newest week, 6 of them influenza or RSV).

By source, share of values revised: state median 13.3% (212), upper quartile 13.1% (209), population-weighted mean 31.1% (497), population-weighted geometric mean 29.9% (477). The weighted aggregates change more often but mostly by very little: at lag 4+ their median absolute change is 0.07-0.4%, against 1-5% for the median and upper quartile.

**Old-week revisions are mostly COVID-19, and some are large.** Of the 133 big changes at lag 4+, 116 are COVID-19 (8.3% of 1,396 COVID-19 values at that lag), against 8 influenza (0.6%) and 9 RSV (0.7%). Some whole state histories moved (not graded; read from `revisions.csv`):

- District of Columbia, COVID-19 state median: every week from 2026-08-08 to 09-12 rose by a factor of 2.74 to 2.92 (for example 3.49 to 9.55 on 08-29); no D.C. COVID-19 median value from 09-19 to 10-17 changed.
- Wisconsin, COVID-19 state median: every week from 09-05 to 10-17 rose by 35% to 109%.
- Alaska, Idaho and Maryland, COVID-19 state median: several August weeks rose by 50% to 104%.

State aggregates cannot tell us why. Sites added to or removed from a state's history, re-normalised site baselines and reprocessed samples would each produce changes like these; a near-constant factor across six weeks, as in D.C., fits a change of normalisation better than late samples, but we have not checked site-level data. (Background: CDC changed its WVAL method on 2026-08-14; both releases compared here came after that.)

**ED control.** All 1,644 ED values in the common weeks were identical, as the plan required.

## Alerts that flipped

| | Median | Upper quartile | Pop. mean | Pop. geo. mean | Total |
|---|---|---|---|---|---|
| Vanished | 5 | 4 | 4 | 3 | 16 |
| Appeared | 3 | 7 | 7 | 6 | 23 |

The older record had 329 wastewater alert weeks in the common weeks and the newer has 336 (329 - 16 + 23). So 4.9% of the alert weeks a reader saw on the 2026-10-23 release were gone on the 2026-10-30 release, and 7.0% more were added. 27 of the 39 flips are COVID-19, 7 influenza, 5 RSV.

In the newest common week (2026-10-17), the older record showed 30 wastewater alerts. On the next release 2 of them were gone (Georgia RSV, population-weighted geometric mean; Iowa influenza, population-weighted mean) and 7 new ones had appeared for that same week. 23 of the 39 flips are in weeks 4 to 10 weeks old, where only the alert rule's own history can have changed.

## What this means for the season check

The prospective season plan scores each week's alerts as first published, which is what a reader saw. This pair shows why that choice matters: about one state wastewater value in five changed from one release to the next, and 1 in 15 alerts in the newest week vanished. Grade S5 of the season plan (whether revisions changed which surges were caught) will now have a week-by-week revision record to draw on: each new pair of weekly records gets the same descriptive tally here, with no new grades.

## Limits

- One pair of releases, one week apart; lags beyond 10 weeks are not seen.
- Values are compared after rounding to 4 decimals. "Revised" counts any change above rounding noise, so the population-weighted counts are inflated by tiny changes; the big-change column is the more useful size measure (it was not pre-registered as a check).
- An alert depends on the whole history before it, so an alert flip inside the window can come from a revision outside it.
- State aggregates only; causes of revisions are not identified.
- One model family (Claude) designed, coded and graded this.

## Prior art (rechecked 2026-10-31)

A web search on 2026-10-31 again found no published count of how state aggregates of CDC's WVAL change between weekly releases. CDC says only that data "may change as more reports are received". This is a narrow, descriptive first count for one pair of releases.

Data: CDC NWSS (WVAL by site, `atcp-73re`) and NSSP (ED visits by state, `rdmq-nq56`), US federal public data. No endorsement by CDC is implied.

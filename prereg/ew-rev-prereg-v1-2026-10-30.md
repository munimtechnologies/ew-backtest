# Pre-registration: how much do CDC's wastewater and ED series change from one weekly release to the next? (study R1, 2026-10-30)

MV2 of Munim, Inc. Researched, written and coded by AI agents (Claude) working in MV2's name. No human has reviewed this plan yet. Text CC BY 4.0; code Apache-2.0. This is public-health research information, not medical advice.

**Status:** fixed on 2026-10-30, before any comparison of the two records below has been computed. Code: `ew/revisions.py` 1.0 with offline tests (`ew/test_revisions.py`), committed after this plan. What we had seen of the newer record when writing this: its `watch.json` (gate, timing, counts), the first 11 rows of its `recent.csv` (Alabama, COVID-19, state median) and the first 4 rows of its `alerts.csv`. We have not opened the older record's `recent.csv` or `alerts.csv`.

## 1. Why

The prospective season check ([ew-season-prereg-v1-2026-10-29.md](ew-season-prereg-v1-2026-10-29.md)) scores alerts on the data as published each week, because CDC's series are revised after release. Its grade S5 asks, at the end of the season, whether revisions changed which surges the rule caught. Nobody has yet said how big the week-to-week revisions are. This study counts them for the first pair of weekly records, so the size of the problem is known now rather than in July 2027.

## 2. Prior art (search 2026-10-30)

- CDC's WVAL page says baselines are recalculated on fixed dates (COVID-19 on 1 April and 1 October; influenza A and RSV on 1 August) and that all historical values are then updated; it says nothing about week-to-week revisions or late samples. Neither of the two releases compared here is on a recalculation date.
- CDC's state trend pages say wastewater "data may change as more reports are received".
- For NSSP ED data, release vintages exist (the COVID-19 Forecast Hub keeps them in its git history; CDC's cfa-catalog-pub issue #79 proposes a weekly archive; Delphi's Epidata keeps versioned NSSP signals), and revision forecasting in surveillance streams is studied (PMC12646461).
- We found no published count of how state-level aggregates of CDC's WVAL change between two weekly releases. Delphi may archive other NWSS signals; we did not find WVAL among them. This is a narrow, descriptive first count, not a method.

## 3. Data

Two weekly records of `python -m ew.watch` in this repository, both made by the same code (watch.py 1.0) with the same rule constants:

| Record | WVAL release (max date_updated) | ED build | Newest grid week | Gate |
|---|---|---|---|---|
| `watch/2026-10-29/` | 2026-10-23 11:03 | 2026-10-28 | 2026-10-17 | pass |
| `watch/2026-10-30/` | 2026-10-30 11:02 | 2026-10-28 | 2026-10-24 | pass |

Each record's `recent.csv` holds every value of the five sources (state median, q75, popmean and popgeo of site WVAL, and the ED percent) in the last 12 grid weeks, rounded to 4 decimals; `alerts.csv` holds every alert week in those weeks.

## 4. Definitions

- **Common weeks:** weeks present in both records' `recent.csv` (expected: 2026-08-08 to 2026-10-17, 11 weeks).
- **Key:** state, pathogen, source, week, in a common week, present in either record.
- **Revised:** the value changed by more than 0.00005 (rounding noise), or it is present in only one record (appeared or vanished). **Big:** changed by 10% or more of the old value, or changed from 0.
- **Lag:** weeks before the older record's newest grid week (2026-10-17), binned 0, 1, 2-3, 4+.
- **Alert flip:** an alert week in a common week that is in one record's `alerts.csv` but not the other's.

## 5. Checks and predictions

| ID | Check | Pass if | Our prediction |
|---|---|---|---|
| D0 (control) | ED values and ED alerts are identical in the two records (same ED build) | 0 revised ED keys and 0 ED alert flips; untestable if the builds differ or a gate failed | pass |
| D1 | The state-median WVAL series was revised | at least 1 revised median key | pass |
| D2 | Revisions concentrate in recent weeks | share revised at lags 0-1 > share revised at lag 4+, pooled over the four wastewater sources and three pathogens | pass |
| D3 | Revisions also reach weeks a month or more old | share revised at lag 4+ (pooled as D2) is at least 1% | pass |
| D4 | Revisions already flip alerts a reader saw | at least 1 wastewater alert flip (any of the four sources) | pass |

Why: late samples should mainly change the newest weeks (D2). Sites joining or leaving a state between releases, or a site moving from its lab's borrowed baseline to its own, would change a state aggregate in older weeks too (D3); we expect that weekly, but with low confidence. With about 500 alert weeks per record and a rule that depends on the last three weeks and a trailing median, we expect some alerts to flip (D4). D0 is a check of our own recording: if it fails, either our pipeline is not reproducible or the ED data changed under the same build label.

## 6. Fixed readings

- **D0 fails:** revision counts from our records cannot be trusted until the cause is found; the results note says so first, and S5 of the season plan gets a pointer to it.
- **D1 fails:** the 2026-10-30 WVAL release did not revise the state medians in the window; revisions are then a smaller concern for S5 than the season plan assumed.
- **D2 and D3 both pass:** revisions are largest in recent weeks but also reach older history, so even a retrospective back-test of weeks months old is not a real-time test; the season plan's "late week" sensitivity line is not enough on its own.
- **D3 fails:** history a month old was effectively frozen between these two releases.
- **D4 passes:** the report says plainly that an alert shown one week can disappear (or appear) the next, with the count.
- Whatever the grades, the counts are one pair of releases. They describe this pair, not the season.

## 7. Afterwards

Each new pair of consecutive weekly records gets the same descriptive tally (no new grades) in `results/revisions/`, so the season ends with a week-by-week revision record beside S5. Anything `ew/revisions.py` decides that this plan does not (file parsing, rounding) is mechanics only.

## 8. Limits known now

- One pair of releases, one week apart, 12-week windows: lags beyond 10 weeks are not seen.
- Values are compared after rounding to 4 decimals.
- An alert depends on the whole history before it, so an alert flip inside the window can come from a revision outside it.
- One model family (Claude) designed, coded and will grade this.

Data: CDC NWSS (WVAL by site, `atcp-73re`) and NSSP (ED visits by state, `rdmq-nq56`), US federal public data. No endorsement by CDC is implied.

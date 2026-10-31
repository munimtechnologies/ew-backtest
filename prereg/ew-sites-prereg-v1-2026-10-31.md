# Pre-registration: why do CDC's state wastewater values change between weekly releases? A site-level look (study R2, 2026-10-31)

MV2 of Munim, Inc. Researched, written and coded by AI agents (Claude) working in MV2's name. No human has reviewed this plan yet. Text CC BY 4.0; code Apache-2.0. This is public-health research information, not medical advice.

**Status:** fixed on 2026-10-31, before any site-level snapshot exists. Code: `ew/sites.py` 1.0 with offline tests (`ew/test_sites.py`), committed after this plan. The pair it grades has not been released yet.

## 1. Why

Study R1 ([results/revisions/ew-rev-results-v1-2026-10-31.md](../results/revisions/ew-rev-results-v1-2026-10-31.md)) found that between CDC's WVAL releases of 2026-10-23 and 2026-10-30, 21.9% of state wastewater values in the 11 common weeks changed, 18.2% of values four to ten weeks old changed, and 39 alert weeks flipped. Some whole state histories moved: the District of Columbia's COVID-19 median rose by a factor of 2.74 to 2.92 in each of six weeks. State values cannot say why. Three causes are possible, and each has a different consequence for an alert reader:

- **late sites:** a site's sample for a recent week arrives after the release, so the newest weeks fill in;
- **membership:** a site joins (often with a back-filled history) or leaves a state's set for a week;
- **values:** the same sites report different values for the same week, for example because a site's baseline was re-estimated. CDC's WVAL is e raised to the number of standard deviations above a site's baseline, so a shift in the baseline level multiplies all of that site's values by one factor.

## 2. Prior art (search 2026-10-30 and 2026-10-31)

We found no published count of week-to-week revisions in CDC's WVAL, at state or site level (R1's search, repeated on 2026-10-31). CDC says data "may change as more reports are received" and that baselines are recalculated on fixed dates (COVID-19 1 April and 1 October; influenza A and RSV 1 August); a web summary also reports a WVAL method change on 2026-08-14. Neither says how often site values change between other releases, or whether sites' histories are rescaled.

## 3. Data

From the weekly record of 2026-11-06 on, each weekly watch job also runs `python -m ew.sites snapshot`, which keeps every site's WVAL (the mean of its rows that week, as `ew.agg`), row count and population served in the newest 12 weeks of `atcp-73re`, in `watch/<date>/sites/`.

**The graded pair** is the first two consecutive weekly records that both contain `sites/` and both pass their gates: expected `watch/2026-11-06/` and `watch/2026-11-13/`. If a week is missed, the next such pair is graded and the note says which. A dry run on the 2026-10-30 release (one snapshot compared with itself) checks only E0 and file sizes; it grades nothing.

## 4. Definitions

- **Common weeks:** weeks present in both snapshots. **Lag:** weeks before the older snapshot's newest week, binned 0, 1, 2-3, 4+ (as R1).
- **Site-week:** one site's value for one pathogen and week. **Changed:** in both snapshots and differs by more than 0.000001 (values are written to 6 decimals). **Appeared / vanished:** in the newer / older snapshot only.
- **State median:** the median of a state-week's site values. **Revised:** rounded to 4 decimals it changed by more than 0.00005, or it exists in one snapshot only. A revised state median is **membership** if the state-week's set of sites differs between the snapshots, otherwise **values**.
- **Rescaled site:** at least 3 changed site-weeks in the common weeks, positive in both snapshots, whose new/old ratios are all within 2% of their median ratio, and that median is not within 2% of 1.

## 5. Checks and predictions

| ID | Check | Pass if | Our prediction |
|---|---|---|---|
| E0 (control) | Each snapshot is consistent with its own watch record | in both records: same WVAL release (max date_updated), and the medians of the site values reproduce every state-median value in `recent.csv` in the snapshot's weeks within 0.0001, none missing | pass |
| E1 | Site values a month or more old change | changed / site-weeks in both snapshots, at lag 4+, pooled over pathogens, is at least 1% | pass |
| E2 | Old-week state revisions come mostly from changed values, not membership | at lag 4+, "values" / revised state medians (pooled) is at least 0.5; untestable if fewer than 10 revised | pass (low confidence) |
| E3 | Some site histories are rescaled by one factor | at least 1 rescaled site | pass (low confidence) |
| E4 | Late sites fill in the newest week | appeared / site-weeks in the newer snapshot at lag 0 is at least 5% | pass |

Why: R1 found 18% of state values at lag 4+ revised, more than membership changes alone seem likely to produce in one week (E1, E2); D.C.'s near-constant factor fits a rescaled site (E3), but one state is thin evidence; R1 found new state values appearing only in the newest weeks, which fits late reporting (E4).

## 6. Fixed readings

Each check is read on its own; none depends on another except through E0.

- **E0 fails:** the snapshots do not reproduce the watch records (or came from a different release), so E1-E4 are reported but not interpreted. We fix the cause and grade the next pair under a dated addendum.
- **E1 passes:** site values a month or more old are revised between releases. **Fails:** they were effectively frozen in this pair; any old-week state revisions then come from membership.
- **E2 passes:** most old-week state revisions come from the same sites' values changing; a reader cannot treat a state's history as settled even when no site joined or left. **Fails:** most come from sites joining or leaving (including back-filled histories); site counts are then the warning sign to watch. **Untestable:** too few old-week revisions in this pair to say.
- **E3 passes:** at least one site's history moved by one factor, which fits a re-estimated baseline level; the note lists them. **Fails:** no such pattern in this pair; R1's D.C. pattern stays unexplained.
- **E4 passes:** late site reports are a main source of newest-week revisions; alerts in the newest week should be read as provisional. **Fails:** the newest week's sites were mostly complete at release.
- Whatever the grades, the counts describe one pair of releases.

## 7. Outputs and afterwards

`python -m ew.sites diff --old watch/<date1> --new watch/<date2>` writes `sitediff.json` (tallies, attribution, E0 detail, grades), `site-changes.csv`, `state-changes.csv` and `rescaled.csv` to `results/sites/`. Later pairs get the same descriptive tally, with no new grades. Anything `ew/sites.py` decides that this plan does not (file parsing, sorting) is mechanics only.

## 8. Limits known now

- One pair of releases; 12-week snapshots, so lags beyond 10-11 weeks are not seen.
- "Membership" is judged per state-week: a state-week where a site joined and other sites' values also changed counts as membership.
- A rescaled site fits a baseline-level change, but other causes could give a constant factor; we cannot confirm a cause without CDC.
- The snapshot and the watch record are two fetches minutes apart; E0 checks they read the same release.
- One model family (Claude) designed, coded and will grade this.

Data: CDC NWSS (WVAL by site, `atcp-73re`), US federal public data. No endorsement by CDC is implied.

#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""agg2: do outlier-resistant state wastewater aggregates catch more ED surges without more false alarms? (study v3)

Pre-registration: prereg/ew-agg2-prereg-v1-2026-10-29.md. Study v2 (ew.agg) found that a population-weighted
mean of site WVAL caught many more influenza and RSV ED surges than the state median, but with about three
times the false alarms, and some state-weeks were set by single sites with values up to 10^20. Here two new
aggregates of the same site values run through the same rule, surges and scoring (ew.backtest, PRIMARY):
- "popgeo": the population-weighted geometric mean, exp of the weighted mean of ln WVAL (WVAL is e to the
  number of standard deviations above a site's baseline, so this is the weighted mean of those SDs);
- "share_up": the share of the population served by sites above 1.0, the site's own baseline.
Both use only sites with a positive population_served; popgeo also leaves out sites with WVAL <= 0.
The median, popmean and q75 of study v2 are re-run on the same fetch for comparison.

Writes to --out-dir: agg2-results.json and agg2-series.csv. Standard library only.

Usage: python -m ew.agg2 --out-dir /out
"""
import argparse
import csv
import json
import math
import os
import statistics
import sys
import time
from datetime import datetime, timezone

from ew import agg
from ew import backtest as bt
from ew import cdc
from ew import run

PREREG = "prereg/ew-agg2-prereg-v1-2026-10-29.md"
CODE_VERSION = "1.0"
AGGS = ("median", "popmean", "q75", "popgeo", "share_up")
ALTS = ("popmean", "q75", "popgeo", "share_up")
GRADED = ("popgeo", "share_up")
REPLICATE = (("popmean", "influenza"), ("popmean", "rsv"), ("q75", "influenza"))
FA_FACTOR = 1.25
BASELINE = 1.0


def state_aggs(acc):
    """agg.state_aggs plus "popgeo": (value or None, sites used) and "share_up": (value or None, sites with a
    population). A site with two rows in one week counts once, at their mean."""
    out = agg.state_aggs(acc)
    for k, sites in acc.items():
        means = [(statistics.fmean(d["v"]), d["pop"]) for d in sites.values() if d["pop"]]
        pos = [(m, pop) for m, pop in means if m > 0]
        geo = math.exp(sum(pop * math.log(m) for m, pop in pos) / sum(pop for _, pop in pos)) if pos else None
        up = sum(pop for m, pop in means if m > BASELINE) / sum(pop for _, pop in means) if means else None
        out[k]["popgeo"] = (geo, len(pos))
        out[k]["share_up"] = (up, len(means))
    return out


def dominated(acc, floor=100.0):
    """Reported, not graded. Per pathogen: state-weeks with at least 2 sites with a population ("eligible"),
    and those where one site with WVAL above `floor` contributes more than half of sum(pop x WVAL), so that
    it alone sets the popmean ("state_weeks")."""
    out = {"floor": floor, "eligible": {p: 0 for p in bt.PATHOGENS}, "state_weeks": {p: 0 for p in bt.PATHOGENS}}
    for (st, p, wk), sites in acc.items():
        wp = [(statistics.fmean(d["v"]), d["pop"]) for d in sites.values() if d["pop"]]
        if len(wp) < 2:
            continue
        out["eligible"][p] += 1
        tot = sum(m * pop for m, pop in wp)
        m, pop = max(wp, key=lambda x: x[0] * x[1])
        if tot > 0 and m > floor and m * pop > 0.5 * tot:
            out["state_weeks"][p] += 1
    return out


def false_rate(summary, name, path):
    return summary[name][path]["ww"]["false_per_52_weeks"]


def fa_ratio(summary, name, path):
    """An aggregate's wastewater false alarms per 52 state-weeks over the median's; None if either is unknown."""
    a, m = false_rate(summary, name, path), false_rate(summary, "median", path)
    return None if a is None or m is None else bt.ratio(a, m)


def k1(c, no_pop):
    if no_pop or c["alt_only"] + c["median_only"] < agg.MIN_DISCORDANT or c["p_more"] is None:
        return "untestable"
    return "pass" if c["p_more"] < bt.ALPHA else "fail"


def grade(g1, comp, summary, share):
    """R0 and K1-K3 exactly as pre-registered. g1: H1-H6 of each aggregate; comp: agg.compare() per
    alternative; summary: bt summaries per aggregate; share: agg.pop_share() of the fetch."""
    no_pop = share is None or share < agg.MIN_POP_SHARE
    g = {"R0_replication": "pass" if all(k1(comp[a][p], False) == "pass" for a, p in REPLICATE) else "fail"}
    for a in GRADED:
        for p in bt.PATHOGENS:
            first = k1(comp[a][p], no_pop)
            fa_a, fa_m = false_rate(summary, a, p), false_rate(summary, "median", p)
            if first == "untestable" or fa_a is None or fa_m is None:
                second = "untestable"
            else:
                second = "pass" if first == "pass" and fa_a <= FA_FACTOR * fa_m else "fail"
            g["K1_%s_%s" % (a, p)] = first
            g["K2_%s_%s" % (a, p)] = second
            g["K3_%s_%s" % (a, p)] = "untestable" if no_pop else g1[a].get("H3_" + p, "untestable")
    return g


def analyse(aggs, base, reps=bt.NULL_REPS, share=None):
    """Run the v1 back-test on each aggregate over base's grid (base: bt.build_series of the median)."""
    out = {"summary": {}, "sparse_sites": {}, "grades_v1": {}}
    res = {}
    for name in AGGS:
        s = base if name == "median" else agg.swap_w(base, aggs, name)
        r, summ, sp, g = bt.run_backtest(s, bt.PRIMARY, reps, bt.SEED)
        res[name] = r
        out["summary"][name], out["sparse_sites"][name], out["grades_v1"][name] = summ, sp, g
    out["compare"] = {a: agg.compare(res[a], res["median"]) for a in ALTS}
    out["false_alarm_ratio"] = {a: {p: fa_ratio(out["summary"], a, p) for p in bt.PATHOGENS} for a in ALTS}
    out["grades"] = grade(out["grades_v1"], out["compare"], out["summary"], share)
    return out


def write_series(path, base, aggs):
    """One row per state, pathogen and week with any value: median, popgeo, share_up, site counts, ED percent."""
    r4 = lambda v: "" if v is None else round(v, 4)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["week_end", "state", "pathogen", "wval_median", "wval_popgeo", "share_up", "sites",
                    "sites_with_population", "ed_percent"])
        for (st, p), s in sorted(base.items()):
            for wk, e in zip(s["weeks"], s["e"]):
                a = aggs.get((st, p, wk))
                if a is None and e is None:
                    continue
                if a is None:
                    w.writerow([wk, st, p, "", "", "", 0, 0, e])
                else:
                    w.writerow([wk, st, p, r4(a["median"][0]), r4(a["popgeo"][0]), r4(a["share_up"][0]),
                                a["median"][1], a["share_up"][1], "" if e is None else e])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--null-reps", type=int, default=bt.NULL_REPS)
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    t0 = time.time()
    fetched_at = datetime.now(timezone.utc).isoformat()
    acc, meta = {}, {}
    for batch in cdc.fetch_pages(cdc.WVAL_ID, agg.SELECT):
        agg.add_sites(acc, batch, meta)
    ed, emeta = cdc.fetch_ed()
    aggs = state_aggs(acc)
    base = bt.build_series({k: v["median"] for k, v in aggs.items()}, ed)
    g = run.gate(meta, emeta, base)
    share = agg.pop_share(meta)
    g["kept_rows_without_population"] = meta.get("no_pop", 0)
    g["population_share"] = share
    out = {"prereg": PREREG, "code_version": CODE_VERSION, "params": bt.PRIMARY, "seed": bt.SEED,
           "null_reps": a.null_reps, "gate": g, "popmean_dominated": dominated(acc),
           "timing": {"fetched_at_utc": fetched_at, "wval_max_date_updated": meta.get("max_date_updated"),
                      "ed_max_buildnumber": emeta.get("max_buildnumber"),
                      "grid_first_week": next(iter(base.values()))["weeks"][0] if base else None,
                      "grid_last_week": next(iter(base.values()))["weeks"][-1] if base else None}}
    if base:
        write_series(os.path.join(a.out_dir, "agg2-series.csv"), base, aggs)
    if g["pass"]:
        out.update(analyse(aggs, base, a.null_reps, share))
    else:
        out["grades"] = {"status": "gate failed: nothing graded"}
    out["minutes"] = round((time.time() - t0) / 60, 1)
    with open(os.path.join(a.out_dir, "agg2-results.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, sort_keys=True)
    print(json.dumps({"gate": g, "grades": out["grades"], "minutes": out["minutes"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

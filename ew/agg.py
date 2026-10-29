#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""agg: does another state wastewater aggregate catch the ED surges the state median missed? (study v2)

Pre-registration: prereg/ew-agg-prereg-v1-2026-10-29.md. The v1 back-test used the median of site WVAL in
each state. Here the same rule, surges and scoring (ew.backtest, PRIMARY) run on three state aggregates of
the same site values, on one shared weekly grid:
- "median": the v1 aggregate (median over sites of each site's mean WVAL that week);
- "popmean": the mean of site WVAL weighted by population_served (sites with no positive population are
  left out);
- "q75": the upper quartile of site values (sorted index floor(0.75 * (n - 1)), as ew.backtest.quantile).
The ED series, surge onsets and alert labels are the same for every aggregate, so detections pair one to one.

Writes to --out-dir: agg-results.json and agg-series.csv. Standard library only.

Usage: python -m ew.agg --out-dir /out
"""
import argparse
import csv
import json
import os
import statistics
import sys
import time
from datetime import datetime, timezone

from ew import backtest as bt
from ew import cdc
from ew import run

PREREG = "prereg/ew-agg-prereg-v1-2026-10-29.md"
CODE_VERSION = "1.0"
AGGS = ("median", "popmean", "q75")
ALTS = ("popmean", "q75")
SELECT = cdc.WVAL_SELECT + ",population_served"
MIN_DISCORDANT = 5
MIN_POP_SHARE = 0.5


def add_sites(acc, rows, meta):
    """acc[(state, pathogen, week)][site] = {"v": [values], "pop": population or None}. Rows are kept
    exactly as in cdc.add_wval; meta also counts kept rows without a positive population ("no_pop")."""
    for r in rows:
        meta["rows"] = meta.get("rows", 0) + 1
        p = cdc.WVAL_TARGET.get(r.get("pathogen_target"))
        v = cdc.to_float(r.get("site_wval"))
        st, wk, site = r.get("state_territory"), cdc.week_of(r.get("week_end")), r.get("site")
        upd = r.get("date_updated") or ""
        if upd > meta.get("max_date_updated", ""):
            meta["max_date_updated"] = upd
        if p is None or v is None or not st or wk is None or site is None:
            meta["skipped"] = meta.get("skipped", 0) + 1
            continue
        pop = cdc.to_float(r.get("population_served"))
        if pop is None or pop <= 0:
            pop = None
            meta["no_pop"] = meta.get("no_pop", 0) + 1
        d = acc.setdefault((st, p, wk), {}).setdefault(site, {"v": [], "pop": None})
        d["v"].append(v)
        if pop is not None:
            d["pop"] = pop


def pop_share(meta):
    """Share of kept rows with a positive population; None if no row was kept."""
    kept = meta.get("rows", 0) - meta.get("skipped", 0)
    return 1 - meta.get("no_pop", 0) / kept if kept else None


def state_aggs(acc):
    """{(state, pathogen, week): {"median": (value, sites), "popmean": (value or None, sites with a
    population), "q75": (value, sites)}}. A site with two rows in one week counts once, at their mean."""
    out = {}
    for k, sites in acc.items():
        means = [(statistics.fmean(d["v"]), d["pop"]) for d in sites.values()]
        vals = [m for m, _ in means]
        wp = [(m, pop) for m, pop in means if pop]
        pm = sum(m * pop for m, pop in wp) / sum(pop for _, pop in wp) if wp else None
        out[k] = {"median": (statistics.median(vals), len(vals)), "popmean": (pm, len(wp)),
                  "q75": (bt.quantile(vals, 0.75), len(vals))}
    return out


def swap_w(series, aggs, name):
    """A copy of series with w and n taken from aggregate `name`; weeks and ED values unchanged."""
    out = {}
    for (st, p), s in series.items():
        got = [aggs.get((st, p, wk), {}).get(name) for wk in s["weeks"]]
        out[(st, p)] = {"weeks": s["weeks"], "e": s["e"],
                        "w": [g[0] if g else None for g in got], "n": [g[1] if g else 0 for g in got]}
    return out


def compare(alt, med):
    """Per pathogen: ED surges the alternative's wastewater rule caught and the median's missed, and the
    reverse, with a one-sided exact sign (McNemar) test that the alternative catches more; and, among
    surges both caught, how often the alternative alerted earlier (lead difference > 0)."""
    out = {}
    for path in bt.PATHOGENS:
        a_only = m_only = 0
        diffs = []
        for k in sorted(x for x in med if x[1] == path):
            da, dm = alt[k]["rules"]["ww"]["detected"], med[k]["rules"]["ww"]["detected"]
            for o in med[k]["events"]:
                if da[o] is not None and dm[o] is None:
                    a_only += 1
                elif dm[o] is not None and da[o] is None:
                    m_only += 1
                elif da[o] is not None:
                    diffs.append(da[o] - dm[o])
        more = bt.sign_test_greater([1] * a_only + [-1] * m_only)
        early = bt.sign_test_greater(diffs)
        out[path] = {"alt_only": a_only, "median_only": m_only, "p_more": more[3], "both": len(diffs),
                     "alt_earlier": early[0], "median_earlier": early[1], "ties": early[2], "p_earlier": early[3]}
    return out


def grade(g1, comp, share):
    """G0-G2 exactly as pre-registered. g1: the v1 grades (H1-H6) of each aggregate; comp: compare() per
    alternative; share: pop_share() of the fetch."""
    g = {"G0_replication": "pass" if all(g1["median"].get("H1_" + p) == "pass" and
                                         g1["median"].get("H3_" + p) == "fail" for p in bt.PATHOGENS) else "fail"}
    for a in ALTS:
        no_pop = a == "popmean" and (share is None or share < MIN_POP_SHARE)
        for p in bt.PATHOGENS:
            c = comp[a][p]
            if no_pop or c["alt_only"] + c["median_only"] < MIN_DISCORDANT or c["p_more"] is None:
                g["G1_%s_%s" % (a, p)] = "untestable"
            else:
                g["G1_%s_%s" % (a, p)] = "pass" if c["p_more"] < bt.ALPHA else "fail"
            g["G2_%s_%s" % (a, p)] = "untestable" if no_pop else g1[a].get("H3_" + p, "untestable")
    return g


def analyse(aggs, base, reps=bt.NULL_REPS, share=None):
    """Run the v1 back-test on each aggregate over base's grid (base: bt.build_series of the median)."""
    out = {"summary": {}, "sparse_sites": {}, "grades_v1": {}}
    res = {}
    for name in AGGS:
        s = base if name == "median" else swap_w(base, aggs, name)
        r, summ, sp, g = bt.run_backtest(s, bt.PRIMARY, reps, bt.SEED)
        res[name] = r
        out["summary"][name], out["sparse_sites"][name], out["grades_v1"][name] = summ, sp, g
    out["compare"] = {a: compare(res[a], res["median"]) for a in ALTS}
    out["grades"] = grade(out["grades_v1"], out["compare"], share)
    return out


def write_series(path, base, aggs):
    """One row per state, pathogen and week with any value: the three aggregates, site counts, ED percent."""
    r4 = lambda v: "" if v is None else round(v, 4)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["week_end", "state", "pathogen", "wval_median", "wval_popmean", "wval_q75", "sites",
                    "sites_with_population", "ed_percent"])
        for (st, p), s in sorted(base.items()):
            for wk, e in zip(s["weeks"], s["e"]):
                a = aggs.get((st, p, wk))
                if a is None and e is None:
                    continue
                if a is None:
                    w.writerow([wk, st, p, "", "", "", 0, 0, e])
                else:
                    w.writerow([wk, st, p, r4(a["median"][0]), r4(a["popmean"][0]), r4(a["q75"][0]),
                                a["median"][1], a["popmean"][1], "" if e is None else e])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--null-reps", type=int, default=bt.NULL_REPS)
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    t0 = time.time()
    fetched_at = datetime.now(timezone.utc).isoformat()
    acc, meta = {}, {}
    for batch in cdc.fetch_pages(cdc.WVAL_ID, SELECT):
        add_sites(acc, batch, meta)
    ed, emeta = cdc.fetch_ed()
    aggs = state_aggs(acc)
    base = bt.build_series({k: v["median"] for k, v in aggs.items()}, ed)
    g = run.gate(meta, emeta, base)
    share = pop_share(meta)
    g["kept_rows_without_population"] = meta.get("no_pop", 0)
    g["population_share"] = share
    out = {"prereg": PREREG, "code_version": CODE_VERSION, "params": bt.PRIMARY, "seed": bt.SEED,
           "null_reps": a.null_reps, "gate": g,
           "timing": {"fetched_at_utc": fetched_at, "wval_max_date_updated": meta.get("max_date_updated"),
                      "ed_max_buildnumber": emeta.get("max_buildnumber"),
                      "grid_first_week": next(iter(base.values()))["weeks"][0] if base else None,
                      "grid_last_week": next(iter(base.values()))["weeks"][-1] if base else None}}
    if base:
        write_series(os.path.join(a.out_dir, "agg-series.csv"), base, aggs)
    if g["pass"]:
        out.update(analyse(aggs, base, a.null_reps, share))
    else:
        out["grades"] = {"status": "gate failed: nothing graded"}
    out["minutes"] = round((time.time() - t0) / 60, 1)
    with open(os.path.join(a.out_dir, "agg-results.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, sort_keys=True)
    print(json.dumps({"gate": g, "grades": out["grades"], "minutes": out["minutes"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

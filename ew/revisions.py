#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""revisions: what changed between two weekly watch records.

Pre-registration: prereg/ew-rev-prereg-v1-2026-10-30.md. Each record in watch/<date>/ keeps every source's values
(recent.csv) and alert weeks (alerts.csv) in the last 12 grid weeks, as published that day. For the weeks both
records cover, this counts values that changed, appeared or vanished, by source, pathogen and lag (weeks before the
older record's newest grid week), and alert weeks that appeared or vanished. It also grades the plan's five fixed
checks D0-D4. Standard library only.

Writes to --out-dir:
- revisions.json: data versions of both records, the common weeks, the tallies, pooled shares, alert flips, grades;
- revisions.csv: one row per value that changed, appeared or vanished;
- alert-flips.csv: one row per alert week that appeared or vanished.

Usage: python -m ew.revisions --old watch/2026-10-29 --new watch/2026-10-30 --out-dir /out/rev
"""
import argparse
import csv
import json
import os
import statistics
import sys
from datetime import date

CODE_VERSION = "1.0"
PREREG = "prereg/ew-rev-prereg-v1-2026-10-30.md"
WW = ("median", "q75", "popmean", "popgeo")
SOURCES = WW + ("ed",)
LAGS = ("0", "1", "2-3", "4+")
TOL = 5e-5     # recent.csv rounds values to 4 decimals; smaller differences are float noise
BIG = 0.10     # a change of 10% or more of |old| (or any change from 0) is "big"
D3_MIN = 0.01
ROW_HEAD = ["state", "pathogen", "source", "week", "lag", "kind", "old", "new", "rel_change"]
FLIP_HEAD = ["state", "pathogen", "source", "alert_week", "kind"]


def read_record(folder):
    """(values {(state, pathogen, source, week): float}, alert keys, watch.json) of one watch record."""
    vals = {}
    with open(os.path.join(folder, "recent.csv"), newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            vals[(r["state"], r["pathogen"], r["source"], r["week"])] = float(r["value"])
    with open(os.path.join(folder, "alerts.csv"), newline="", encoding="utf-8") as f:
        alerts = {(r["state"], r["pathogen"], r["source"], r["alert_week"]) for r in csv.DictReader(f)}
    with open(os.path.join(folder, "watch.json"), encoding="utf-8") as f:
        meta = json.load(f)
    return vals, alerts, meta


def lag_bin(week, last):
    """Weeks from `week` back from `last` (the older record's newest grid week), binned."""
    d = (date.fromisoformat(last) - date.fromisoformat(week)).days // 7
    return "0" if d <= 0 else "1" if d == 1 else "2-3" if d <= 3 else "4+"


def common_weeks(old_vals, new_vals):
    return {k[3] for k in old_vals} & {k[3] for k in new_vals}


def compare(old_vals, new_vals, old_last):
    """(tally, rows) over the common weeks. tally[source][pathogen][lag]: n (keys in either record), changed (in
    both, |new - old| > TOL), big, vanished (old only), appeared (new only), med_abs_rel (median |relative change|
    of the changed values with old != 0, rounded to 4 decimals; None if there are none)."""
    weeks = common_weeks(old_vals, new_vals)
    tally, rows, rels = {}, [], {}
    for k in sorted(set(old_vals) | set(new_vals)):
        if k[3] not in weeks:
            continue
        lag = lag_bin(k[3], old_last)
        c = tally.setdefault(k[2], {}).setdefault(k[1], {}).setdefault(
            lag, {"n": 0, "changed": 0, "big": 0, "vanished": 0, "appeared": 0})
        c["n"] += 1
        o, n = old_vals.get(k), new_vals.get(k)
        if o is None:
            c["appeared"] += 1
            rows.append(list(k) + [lag, "appeared", "", n, ""])
        elif n is None:
            c["vanished"] += 1
            rows.append(list(k) + [lag, "vanished", o, "", ""])
        elif abs(n - o) > TOL:
            rel = (n - o) / abs(o) if o else None
            c["changed"] += 1
            c["big"] += rel is None or abs(rel) >= BIG
            if rel is not None:
                rels.setdefault((k[2], k[1], lag), []).append(abs(rel))
            rows.append(list(k) + [lag, "changed", o, n, "" if rel is None else round(rel, 4)])
    for s, by_path in tally.items():
        for path, by_lag in by_path.items():
            for lag, c in by_lag.items():
                r = rels.get((s, path, lag))
                c["med_abs_rel"] = round(statistics.median(r), 4) if r else None
    return tally, rows


def pooled(tally, sources, lags):
    """(revised, n) summed over the given sources and lags and every pathogen; revised = changed + vanished +
    appeared."""
    rev = n = 0
    for s in sources:
        for by_lag in tally.get(s, {}).values():
            for lag in lags:
                c = by_lag.get(lag)
                if c:
                    rev += c["changed"] + c["vanished"] + c["appeared"]
                    n += c["n"]
    return rev, n


def alert_flips(old_alerts, new_alerts, weeks):
    """({source: {"vanished", "appeared"}}, rows) for alert weeks inside `weeks`."""
    old = {a for a in old_alerts if a[3] in weeks}
    new = {a for a in new_alerts if a[3] in weeks}
    out = {s: {"vanished": 0, "appeared": 0} for s in SOURCES}
    rows = []
    for kind, keys in (("vanished", old - new), ("appeared", new - old)):
        for a in sorted(keys):
            out[a[2]][kind] += 1
            rows.append(list(a) + [kind])
    return out, rows


def grades(tally, flips, old_meta, new_meta):
    """The plan's D0-D4: "pass", "fail" or "untestable"."""
    ok = bool(old_meta["gate"]["pass"] and new_meta["gate"]["pass"])
    same_ed = old_meta["timing"]["ed_max_buildnumber"] == new_meta["timing"]["ed_max_buildnumber"]
    g = {}
    ed_rev, ed_n = pooled(tally, ("ed",), LAGS)
    ed_flips = flips["ed"]["vanished"] + flips["ed"]["appeared"]
    g["D0"] = "untestable" if not (ok and same_ed and ed_n) else "pass" if ed_rev == 0 and ed_flips == 0 else "fail"
    med_rev, med_n = pooled(tally, ("median",), LAGS)
    g["D1"] = "untestable" if not (ok and med_n) else "pass" if med_rev >= 1 else "fail"
    r_new, n_new = pooled(tally, WW, ("0", "1"))
    r_old, n_old = pooled(tally, WW, ("4+",))
    g["D2"] = "untestable" if not (ok and n_new and n_old) else "pass" if r_new / n_new > r_old / n_old else "fail"
    g["D3"] = "untestable" if not (ok and n_old) else "pass" if r_old / n_old >= D3_MIN else "fail"
    ww_flips = sum(flips[s]["vanished"] + flips[s]["appeared"] for s in WW)
    g["D4"] = "untestable" if not ok else "pass" if ww_flips >= 1 else "fail"
    return g


def write_csv(path, head, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(head)
        w.writerows(rows)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    old_vals, old_alerts, old_meta = read_record(a.old)
    new_vals, new_alerts, new_meta = read_record(a.new)
    weeks = common_weeks(old_vals, new_vals)
    tally, rows = compare(old_vals, new_vals, old_meta["timing"]["grid_last_week"])
    flips, flip_rows = alert_flips(old_alerts, new_alerts, weeks)
    out = {"prereg": PREREG, "code_version": CODE_VERSION,
           "records": {"old": os.path.basename(os.path.normpath(a.old)),
                       "new": os.path.basename(os.path.normpath(a.new))},
           "timing": {"old": old_meta["timing"], "new": new_meta["timing"]},
           "gates": {"old": old_meta["gate"]["pass"], "new": new_meta["gate"]["pass"]},
           "common_weeks": sorted(weeks), "tally": tally,
           "shares": {s: {lag: list(pooled(tally, (s,), (lag,))) for lag in LAGS} for s in SOURCES},
           "pooled_ww": {lag: list(pooled(tally, WW, (lag,))) for lag in LAGS},
           "alert_flips": flips, "grades": grades(tally, flips, old_meta, new_meta)}
    write_csv(os.path.join(a.out_dir, "revisions.csv"), ROW_HEAD, rows)
    write_csv(os.path.join(a.out_dir, "alert-flips.csv"), FLIP_HEAD, flip_rows)
    with open(os.path.join(a.out_dir, "revisions.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, sort_keys=True)
    print(json.dumps({"grades": out["grades"], "pooled_ww": out["pooled_ww"], "ed": out["shares"]["ed"],
                      "alert_flips": flips, "rows": len(rows), "flip_rows": len(flip_rows)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

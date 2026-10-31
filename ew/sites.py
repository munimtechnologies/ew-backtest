#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""sites: site-level WVAL snapshots for the weekly watch, and what changed at site level between two of them.

Pre-registration: prereg/ew-sites-prereg-v1-2026-10-31.md (study R2). Study R1 (ew.revisions) counted how
much state aggregates of CDC's WVAL change between weekly releases, but state values cannot say why. Each
weekly watch record now also keeps every site's value in the newest RECENT weeks, so a pair of records can
say whether a state median moved because sites joined or left that week ("membership") or because the
same sites' own values changed ("values"), and whether any site's history was rescaled by one factor.

snapshot writes to --out-dir:
- sites-covid.csv, sites-influenza.csv, sites-rsv.csv: one row per state, site and week in the newest RECENT
  weeks of the WVAL file: the site's WVAL that week (the mean of its rows, as ew.agg), its row count and
  population served;
- sites.json: data version (max date_updated), the weeks covered, row counts and file sizes.
diff (two watch records, each with a sites/ folder) writes to --out-dir:
- sitediff.json: site-week tallies by pathogen and lag, the state-median attribution, rescaled sites, the
  E0 consistency check of each record and the E0-E4 grades;
- site-changes.csv: one row per site-week that changed, appeared or vanished;
- state-changes.csv: one row per revised state median, with its attribution;
- rescaled.csv: one row per rescaled site.
Standard library only.

Usage: python -m ew.sites snapshot --out-dir /out/watch/sites
       python -m ew.sites diff --old watch/<date1> --new watch/<date2> --out-dir /out/sitediff
"""
import argparse
import csv
import json
import os
import statistics
import sys
from datetime import datetime, timezone

from ew import agg
from ew import cdc
from ew import revisions as rv

CODE_VERSION = "1.0"
PREREG = "prereg/ew-sites-prereg-v1-2026-10-31.md"
PATHOGENS = ("covid", "influenza", "rsv")
RECENT = 12
TOL = 1e-6            # site values are written with 6 decimals; an unchanged value is written identically
E0_TOL = 1e-4         # recent.csv rounds state medians to 4 decimals
E1_MIN = 0.01
E2_MIN_N = 10
E4_MIN = 0.05
RESCALE_MIN_WEEKS = 3
RESCALE_TOL = 0.02
PUBLISH_LIMIT = 1900000
CHECKS = ("E0", "E1", "E2", "E3", "E4")
SITE_HEAD = ["state", "site", "week", "wval", "rows", "population"]
CHANGE_HEAD = ["state", "pathogen", "site", "week", "lag", "kind", "old", "new"]
STATE_HEAD = ["state", "pathogen", "week", "lag", "attribution", "old_median", "new_median"]
RESCALE_HEAD = ["state", "pathogen", "site", "changed_weeks", "ratio_median", "ratio_min", "ratio_max"]


def snapshot_rows(acc, recent=RECENT):
    """({pathogen: rows}, weeks). acc: agg.add_sites output. Every site's value in the newest `recent` weeks,
    sorted by state, site and week."""
    weeks = sorted({k[2] for k in acc})[-recent:]
    keep = set(weeks)
    out = {p: [] for p in PATHOGENS}
    for (st, p, wk), sites in acc.items():
        if wk not in keep or p not in out:
            continue
        for site, d in sites.items():
            out[p].append([st, str(site), wk, round(statistics.fmean(d["v"]), 6), len(d["v"]),
                           "" if d["pop"] is None else int(round(d["pop"]))])
    for rows in out.values():
        rows.sort(key=lambda r: (r[0], r[1], r[2]))
    return out, weeks


def read_sites(folder):
    """({(state, pathogen, site, week): wval}, sites.json) of one snapshot folder."""
    with open(os.path.join(folder, "sites.json"), encoding="utf-8") as f:
        meta = json.load(f)
    vals = {}
    for p in PATHOGENS:
        with open(os.path.join(folder, "sites-%s.csv" % p), newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                vals[(r["state"], p, r["site"], r["week"])] = float(r["wval"])
    return vals, meta


def state_medians(vals):
    """{(state, pathogen, week): median of the site values}."""
    by = {}
    for (st, p, _, wk), v in vals.items():
        by.setdefault((st, p, wk), []).append(v)
    return {k: statistics.median(v) for k, v in by.items()}


def site_sets(vals):
    """{(state, pathogen, week): set of sites}."""
    out = {}
    for (st, p, site, wk) in vals:
        out.setdefault((st, p, wk), set()).add(site)
    return out


def compare_sites(old, new, old_last):
    """(tally, rows, weeks) over the weeks both snapshots cover. tally[pathogen][lag]: n (site-weeks in either
    snapshot), changed (in both, |new - old| > TOL), big (changed by rv.BIG of |old| or more, or from 0),
    appeared (new only), vanished (old only). Lag: weeks before `old_last`, binned as ew.revisions."""
    weeks = rv.common_weeks(old, new)
    tally, rows = {}, []
    for k in sorted(set(old) | set(new)):
        if k[3] not in weeks:
            continue
        lag = rv.lag_bin(k[3], old_last)
        c = tally.setdefault(k[1], {}).setdefault(lag, {"n": 0, "changed": 0, "big": 0, "appeared": 0,
                                                        "vanished": 0})
        c["n"] += 1
        o, n = old.get(k), new.get(k)
        if o is None:
            c["appeared"] += 1
            rows.append(list(k) + [lag, "appeared", "", n])
        elif n is None:
            c["vanished"] += 1
            rows.append(list(k) + [lag, "vanished", o, ""])
        elif abs(n - o) > TOL:
            c["changed"] += 1
            c["big"] += o == 0 or abs(n - o) / abs(o) >= rv.BIG
            rows.append(list(k) + [lag, "changed", o, n])
    return tally, rows, weeks


def attribute(old, new, weeks, old_last):
    """(attr, rows). attr[pathogen][lag] over state medians of the site values in `weeks`: n, revised (the
    median rounded to 4 decimals changed by more than rv.TOL, or exists in one snapshot only), and of those
    "membership" (the state-week's set of sites differs) or "values" (same sites, their values changed)."""
    mo, mn = state_medians(old), state_medians(new)
    so, sn = site_sets(old), site_sets(new)
    attr, rows = {}, []
    for k in sorted(set(mo) | set(mn)):
        st, p, wk = k
        if wk not in weeks:
            continue
        lag = rv.lag_bin(wk, old_last)
        c = attr.setdefault(p, {}).setdefault(lag, {"n": 0, "revised": 0, "membership": 0, "values": 0})
        c["n"] += 1
        o, n = mo.get(k), mn.get(k)
        if o is not None and n is not None and abs(round(n, 4) - round(o, 4)) <= rv.TOL:
            continue
        kind = "membership" if so.get(k, set()) != sn.get(k, set()) else "values"
        c["revised"] += 1
        c[kind] += 1
        rows.append([st, p, wk, lag, kind, "" if o is None else round(o, 4), "" if n is None else round(n, 4)])
    return attr, rows


def rescaled_sites(old, new, weeks):
    """Rows for sites with at least RESCALE_MIN_WEEKS changed values in `weeks` that are positive in both
    snapshots, all within RESCALE_TOL of their median ratio new/old, where that median is not within
    RESCALE_TOL of 1 (one factor moved the site's history)."""
    by = {}
    for k, o in old.items():
        n = new.get(k)
        if k[3] in weeks and n is not None and abs(n - o) > TOL and o > 0 and n > 0:
            by.setdefault(k[:3], []).append(n / o)
    out = []
    for key in sorted(by):
        r = by[key]
        if len(r) < RESCALE_MIN_WEEKS:
            continue
        m = statistics.median(r)
        if abs(m - 1) > RESCALE_TOL and all(abs(x / m - 1) <= RESCALE_TOL for x in r):
            out.append(list(key) + [len(r), round(m, 4), round(min(r), 4), round(max(r), 4)])
    return out


def e0_check(site_vals, site_meta, rec_vals, rec_meta):
    """One record's consistency: the snapshot and the watch record read the same WVAL release, and the
    medians of the site values reproduce every state-median value in recent.csv in the snapshot's weeks."""
    meds = state_medians(site_vals)
    weeks = set(site_meta["weeks"])
    n = bad = missing = 0
    for (st, p, src, wk), v in rec_vals.items():
        if src != "median" or wk not in weeks:
            continue
        n += 1
        m = meds.get((st, p, wk))
        if m is None:
            missing += 1
        elif abs(m - v) > E0_TOL:
            bad += 1
    same = site_meta.get("wval_max_date_updated") == rec_meta["timing"].get("wval_max_date_updated")
    return {"compared": n, "mismatched": bad, "missing": missing, "same_release": same,
            "ok": bool(same and n and not bad and not missing)}


def grades(e0, tally, attr, rescaled, gates_ok):
    """The plan's E0-E4: "pass", "fail" or "untestable". e0: {"old", "new"} from e0_check."""
    if not gates_ok:
        return {c: "untestable" for c in CHECKS}
    g = {"E0": "pass" if e0["old"]["ok"] and e0["new"]["ok"] else "fail"}
    both = changed = 0
    for by_lag in tally.values():
        c = by_lag.get("4+")
        if c:
            both += c["n"] - c["appeared"] - c["vanished"]
            changed += c["changed"]
    g["E1"] = "untestable" if not both else "pass" if changed / both >= E1_MIN else "fail"
    rev = sum(a["4+"]["revised"] for a in attr.values() if "4+" in a)
    val = sum(a["4+"]["values"] for a in attr.values() if "4+" in a)
    g["E2"] = "untestable" if rev < E2_MIN_N else "pass" if val / rev >= 0.5 else "fail"
    g["E3"] = "pass" if rescaled else "fail"
    app = n0 = 0
    for by_lag in tally.values():
        c = by_lag.get("0")
        if c:
            app += c["appeared"]
            n0 += c["n"] - c["vanished"]
    g["E4"] = "untestable" if not n0 else "pass" if app / n0 >= E4_MIN else "fail"
    return g


def snapshot_main(out_dir, get=None, pause=None):
    os.makedirs(out_dir, exist_ok=True)
    fetched_at = datetime.now(timezone.utc).isoformat()
    acc, meta = {}, {}
    for batch in cdc.fetch_pages(cdc.WVAL_ID, agg.SELECT, None, get, pause):
        agg.add_sites(acc, batch, meta)
    by_p, weeks = snapshot_rows(acc)
    sizes = {}
    for p in PATHOGENS:
        path = os.path.join(out_dir, "sites-%s.csv" % p)
        rv.write_csv(path, SITE_HEAD, by_p[p])
        sizes[p] = os.path.getsize(path)
    out = {"prereg": PREREG, "code_version": CODE_VERSION, "recent_weeks": RECENT, "weeks": weeks,
           "fetched_at_utc": fetched_at, "wval_max_date_updated": meta.get("max_date_updated"),
           "wval_rows": meta.get("rows", 0), "skipped_rows": meta.get("skipped", 0),
           "rows": {p: len(by_p[p]) for p in PATHOGENS}, "bytes": sizes,
           "over_publish_limit": [p for p in PATHOGENS if sizes[p] >= PUBLISH_LIMIT]}
    with open(os.path.join(out_dir, "sites.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, sort_keys=True)
    print(json.dumps({"weeks": [weeks[0], weeks[-1]] if weeks else [], "rows": out["rows"], "bytes": sizes,
                      "wval_max_date_updated": out["wval_max_date_updated"]}))
    return 0


def diff_main(old_dir, new_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    old_s, old_sm = read_sites(os.path.join(old_dir, "sites"))
    new_s, new_sm = read_sites(os.path.join(new_dir, "sites"))
    old_v, _, old_m = rv.read_record(old_dir)
    new_v, _, new_m = rv.read_record(new_dir)
    old_last = old_sm["weeks"][-1]
    tally, rows, weeks = compare_sites(old_s, new_s, old_last)
    attr, srows = attribute(old_s, new_s, weeks, old_last)
    resc = rescaled_sites(old_s, new_s, weeks)
    e0 = {"old": e0_check(old_s, old_sm, old_v, old_m), "new": e0_check(new_s, new_sm, new_v, new_m)}
    gates_ok = bool(old_m["gate"]["pass"] and new_m["gate"]["pass"])
    out = {"prereg": PREREG, "code_version": CODE_VERSION,
           "records": {"old": os.path.basename(os.path.normpath(old_dir)),
                       "new": os.path.basename(os.path.normpath(new_dir))},
           "releases": {"old": old_sm.get("wval_max_date_updated"), "new": new_sm.get("wval_max_date_updated")},
           "lag_reference_week": old_last, "common_weeks": sorted(weeks), "e0": e0,
           "site_tally": tally, "state_attribution": attr, "rescaled_sites": len(resc),
           "grades": grades(e0, tally, attr, resc, gates_ok)}
    rv.write_csv(os.path.join(out_dir, "site-changes.csv"), CHANGE_HEAD, rows)
    rv.write_csv(os.path.join(out_dir, "state-changes.csv"), STATE_HEAD, srows)
    rv.write_csv(os.path.join(out_dir, "rescaled.csv"), RESCALE_HEAD, resc)
    with open(os.path.join(out_dir, "sitediff.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, sort_keys=True)
    print(json.dumps({"grades": out["grades"], "e0": e0, "rescaled_sites": len(resc), "site_rows": len(rows),
                      "state_rows": len(srows)}))
    return 0


def main(argv=None, get=None, pause=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("snapshot")
    s.add_argument("--out-dir", required=True)
    d = sub.add_parser("diff")
    d.add_argument("--old", required=True)
    d.add_argument("--new", required=True)
    d.add_argument("--out-dir", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "snapshot":
        return snapshot_main(a.out_dir, get, pause)
    return diff_main(a.old, a.new, a.out_dir)


if __name__ == "__main__":
    sys.exit(main())

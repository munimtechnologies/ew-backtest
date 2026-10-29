#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""watch: a dated record of what each wastewater aggregate's rule and the ED-only rule show on today's data.

Pre-registration: prereg/ew-season-prereg-v1-2026-10-29.md (the prospective 2026-27 season check). The three
retrospective studies scored alerts on data as revised later. Here each run keeps what the rule showed on the
data as published that day, so the season can later be scored on the alerts a reader could have seen. Sources:
"median", "q75", "popmean", "popgeo" (state aggregates of site WVAL, ew.agg and ew.agg2) and "ed" (the ED-only
baseline), each through the same rule and constants (ew.backtest PRIMARY) and ew.report.explain.

Writes to --out-dir:
- watch.csv: one row per state, pathogen and source: the newest week with a value, its status, value,
  threshold and sites, whether that week is a new alert (1/0), and the last alert week;
- alerts.csv: every alert week of every source in the last RECENT weeks of the grid;
- recent.csv: every source's value in the last RECENT weeks, so revisions between runs can be counted;
- watch.json: data versions, the gate and per-source counts.
Standard library only.

Usage: python -m ew.watch --out-dir /out
"""
import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone

from ew import agg
from ew import agg2
from ew import backtest as bt
from ew import cdc
from ew import report
from ew import run

CODE_VERSION = "1.0"
PREREG = "prereg/ew-season-prereg-v1-2026-10-29.md"
SOURCES = ("median", "q75", "popmean", "popgeo", "ed")
RECENT = 12
WATCH_HEAD = ["state", "pathogen", "source", "week", "status", "value", "threshold", "sites", "new_alert",
              "last_alert"]
ALERT_HEAD = ["state", "pathogen", "source", "alert_week"]
RECENT_HEAD = ["state", "pathogen", "source", "week", "value"]


def r4(v):
    return "" if v is None else round(v, 4)


def source_series(base, aggs):
    """{source: {(state, pathogen): series}}. base: bt.build_series of the median; aggs: agg2.state_aggs.
    "ed" is base itself: snapshot() reads its ED percent."""
    out = {"median": base, "ed": base}
    for name in ("q75", "popmean", "popgeo"):
        out[name] = agg.swap_w(base, aggs, name)
    return out


def snapshot(srcs, p=None, recent=RECENT):
    """(watch rows, alert rows, value rows) for every source, then state and pathogen in sorted order."""
    p = p or bt.PRIMARY
    watch, alerts, vals = [], [], []
    for name in SOURCES:
        for k in sorted(srcs[name]):
            s = srcs[name][k]
            wk = s["weeks"]
            x = s["e"] if name == "ed" else s["w"]
            ex = report.explain(x, None if name == "ed" else s["n"], p)
            first = max(0, len(wk) - recent)
            watch.append([k[0], k[1], name, wk[ex["t"]], ex["status"], r4(ex["value"]), r4(ex["threshold"]),
                          "" if ex["sites"] is None else ex["sites"], int(ex["new_alert"]),
                          wk[ex["last_alert"]] if ex["last_alert"] is not None else ""])
            alerts += [[k[0], k[1], name, wk[t]] for t in ex["alerts"] if t >= first]
            vals += [[k[0], k[1], name, wk[t], r4(x[t])] for t in range(first, len(wk)) if x[t] is not None]
    return watch, alerts, vals


def counts(watch):
    """{source: {pathogen: {"series", "firing", "new", "stale"}}} from watch rows."""
    out = {}
    for st, path, name, _, status, _, _, _, new, _ in watch:
        c = out.setdefault(name, {}).setdefault(path, {"series": 0, "firing": 0, "new": 0, "stale": 0})
        c["series"] += 1
        c["firing"] += status == "rule firing"
        c["new"] += new
        c["stale"] += status == "stale"
    return out


def write_csv(path, head, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(head)
        w.writerows(rows)


def write_outputs(out_dir, watch, alerts, vals):
    write_csv(os.path.join(out_dir, "watch.csv"), WATCH_HEAD, watch)
    write_csv(os.path.join(out_dir, "alerts.csv"), ALERT_HEAD, alerts)
    write_csv(os.path.join(out_dir, "recent.csv"), RECENT_HEAD, vals)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    fetched_at = datetime.now(timezone.utc).isoformat()
    acc, meta = {}, {}
    for batch in cdc.fetch_pages(cdc.WVAL_ID, agg.SELECT):
        agg.add_sites(acc, batch, meta)
    ed, emeta = cdc.fetch_ed()
    aggs = agg2.state_aggs(acc)
    base = bt.build_series({k: v["median"] for k, v in aggs.items()}, ed)
    g = run.gate(meta, emeta, base)
    weeks = next(iter(base.values()))["weeks"] if base else []
    out = {"prereg": PREREG, "code_version": CODE_VERSION, "params": bt.PRIMARY, "recent_weeks": RECENT,
           "gate": g, "timing": {"fetched_at_utc": fetched_at, "wval_max_date_updated": meta.get("max_date_updated"),
                                 "ed_max_buildnumber": emeta.get("max_buildnumber"),
                                 "grid_first_week": weeks[0] if weeks else None,
                                 "grid_last_week": weeks[-1] if weeks else None}}
    watch, alerts, vals = snapshot(source_series(base, aggs)) if base else ([], [], [])
    write_outputs(a.out_dir, watch, alerts, vals)
    out["counts"] = counts(watch)
    out["rows"] = {"watch": len(watch), "alerts": len(alerts), "recent": len(vals)}
    with open(os.path.join(a.out_dir, "watch.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, sort_keys=True)
    print(json.dumps({"gate": g, "timing": out["timing"], "rows": out["rows"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""run: fetch the CDC series, run the pre-registered back-test and write aggregate results.

Pre-registration: prereg/ew-backtest-prereg-v1-2026-10-28.md.

Writes to --out-dir:
  results.json  gate, release timing, primary summary, H1-H6 grades, sensitivity grid (descriptive)
  series.csv    the weekly state series used (state WVAL median, site count, ED percent)
  states.csv    per state and pathogen: events, detections and alert outcomes of each rule

Usage: python -m ew.run --out-dir /out
"""
import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone

from ew import backtest as bt
from ew import cdc

PREREG = "prereg/ew-backtest-prereg-v1-2026-10-28.md"
CODE_VERSION = "1.0"
GATE_WVAL_ROWS = 400000
GATE_ED_ROWS = 10000
GATE_STATES = 45


def gate(wmeta, emeta, series):
    states = len({k[0] for k in series})
    ok = wmeta.get("rows", 0) >= GATE_WVAL_ROWS and emeta.get("rows", 0) >= GATE_ED_ROWS and states >= GATE_STATES
    return {"wval_rows": wmeta.get("rows", 0), "wval_skipped": wmeta.get("skipped", 0),
            "ed_rows": emeta.get("rows", 0), "ed_skipped": emeta.get("skipped", 0),
            "states_matched": states, "pass": ok}


def write_series(path, series):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["week_end", "state", "pathogen", "wval_state_median", "wval_sites", "ed_percent"])
        for (st, p), s in sorted(series.items()):
            for wk, x, n, e in zip(s["weeks"], s["w"], s["n"], s["e"]):
                if x is not None or e is not None:
                    w.writerow([wk, st, p, "" if x is None else round(x, 4), n, "" if e is None else e])


def write_states(path, series, results):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        head = ["state", "pathogen", "events", "median_sites"]
        for r in bt.RULES:
            head += [r + "_detected", r + "_true", r + "_false", r + "_in_episode"]
        w.writerow(head)
        for k in sorted(results):
            res = results[k]
            row = [k[0], k[1], len(res["events"]), bt.median_sites(series[k], res["labels"])]
            for r in bt.RULES:
                sc = res["rules"][r]
                row += [sum(1 for v in sc["detected"].values() if v is not None), sc["true"], sc["false"],
                        sc["episode"]]
            w.writerow(row)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--null-reps", type=int, default=bt.NULL_REPS)
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    t0 = time.time()
    fetched_at = datetime.now(timezone.utc).isoformat()
    wstate, wmeta = cdc.fetch_wval()
    ed, emeta = cdc.fetch_ed()
    series = bt.build_series(wstate, ed)
    g = gate(wmeta, emeta, series)
    timing = {"fetched_at_utc": fetched_at,
              "wval_last_week": max(k[2] for k in wstate) if wstate else None,
              "wval_max_date_updated": wmeta.get("max_date_updated"),
              "ed_last_week": max(k[2] for k in ed) if ed else None,
              "ed_max_buildnumber": emeta.get("max_buildnumber"),
              "grid_first_week": next(iter(series.values()))["weeks"][0] if series else None,
              "grid_last_week": next(iter(series.values()))["weeks"][-1] if series else None}
    out = {"prereg": PREREG, "code_version": CODE_VERSION, "params": bt.PRIMARY, "seed": bt.SEED,
           "null_reps": a.null_reps, "latency_weeks_wednesday": bt.LATENCY_WEEKS, "gate": g, "timing": timing}
    if series:
        write_series(os.path.join(a.out_dir, "series.csv"), series)
    if g["pass"]:
        results, summary, sparse, grades = bt.run_backtest(series, bt.PRIMARY, a.null_reps, bt.SEED)
        out.update({"summary": summary, "sparse_sites": sparse, "grades": grades})
        write_states(os.path.join(a.out_dir, "states.csv"), series, results)
        grid = []
        for p in bt.GRID:
            _, s2, sp2, _ = bt.run_backtest(series, p, 0, bt.SEED)
            grid.append({"params": p, "summary": s2, "sparse_sites": sp2})
        out["grid_descriptive"] = grid
    else:
        out["grades"] = {"status": "gate failed: nothing graded"}
    out["minutes"] = round((time.time() - t0) / 60, 1)
    with open(os.path.join(a.out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, sort_keys=True)
    print(json.dumps({"gate": g, "grades": out["grades"], "minutes": out["minutes"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

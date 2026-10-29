# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for ew.watch. Every expected value is traced by hand in the comments."""
import csv
import os
import tempfile
import unittest

from ew import backtest as bt
from ew import watch

WK = ["2026-01-%02d" % d for d in (3, 10, 17, 24, 31)] + ["2026-02-07", "2026-02-14", "2026-02-21"]
# A short window so 8 weeks are enough: thresholds from week 4 on, 3 known values, alerts 2 quiet weeks apart.
P = dict(bt.PRIMARY, window=4, min_hist=3, refractory=2)
M = [1.0, 1.0, 1.0, 1.0, 1.0, 2.0, 3.0, 4.0]    # median: fires weeks 6 and 7 -> one alert, week 6
Q = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 2.0, 3.0]    # q75: fires week 7 only -> new alert in the newest week
PM = [1.0, 1.0, 1.0, 1.0, 1.0, 2.0, 3.0, None]  # popmean: no value in week 7; fires week 6, its newest week
E = [1.0] * 8                                   # ED percent: flat, never above its threshold of 1.0


def sources():
    base = {("A", "rsv"): {"weeks": WK, "w": list(M), "n": [3] * 8, "e": list(E)}}
    aggs = {("A", "rsv", w): {"median": (M[i], 3), "q75": (Q[i], 3), "popmean": (PM[i], 2), "popgeo": (None, 0)}
            for i, w in enumerate(WK)}
    return watch.source_series(base, aggs)


class TestSnapshot(unittest.TestCase):
    def test_watch_rows(self):
        rows, alerts, vals = watch.snapshot(sources(), P)
        # median, week 7: 4 > 3 > 2 and above quantile([1, 1, 2, 3], 0.5) = 1 -> firing; the alert was week 6
        # (week 6: 3 > 2 > 1, above quantile([1, 1, 1, 2]) = 1, weeks 4-5 quiet), so week 7 is not new.
        # q75, week 7: 3 > 2 > 1 above 1 -> firing; week 6 failed (1 > 1 is false), so week 7 is a new alert.
        # popmean: newest value is week 6 (1 week behind, not stale): firing, new alert there.
        # popgeo: no values -> "no data", reported at the last grid week, no sites.
        # ed: 1.0 is not above its threshold 1.0 -> "at or below median"; ED rows carry no site count.
        self.assertEqual(rows, [
            ["A", "rsv", "median", WK[7], "rule firing", 4.0, 1.0, 3, 0, WK[6]],
            ["A", "rsv", "q75", WK[7], "rule firing", 3.0, 1.0, 3, 1, WK[7]],
            ["A", "rsv", "popmean", WK[6], "rule firing", 3.0, 1.0, 2, 1, WK[6]],
            ["A", "rsv", "popgeo", WK[7], "no data", "", "", "", 0, ""],
            ["A", "rsv", "ed", WK[7], "at or below median", 1.0, 1.0, "", 0, ""]])
        self.assertEqual(alerts, [["A", "rsv", "median", WK[6]], ["A", "rsv", "q75", WK[7]],
                                  ["A", "rsv", "popmean", WK[6]]])
        self.assertEqual(len(vals), 8 + 8 + 7 + 0 + 8)

    def test_recent_window(self):
        srcs = sources()
        # recent=2 keeps weeks 6 and 7: every alert above, and only the known values in those weeks.
        _, alerts, vals = watch.snapshot(srcs, P, recent=2)
        self.assertEqual(len(alerts), 3)
        self.assertEqual(vals, [["A", "rsv", "median", WK[6], 3.0], ["A", "rsv", "median", WK[7], 4.0],
                                ["A", "rsv", "q75", WK[6], 2.0], ["A", "rsv", "q75", WK[7], 3.0],
                                ["A", "rsv", "popmean", WK[6], 3.0],
                                ["A", "rsv", "ed", WK[6], 1.0], ["A", "rsv", "ed", WK[7], 1.0]])
        # recent=1 keeps week 7 only: the q75 alert.
        _, alerts, _ = watch.snapshot(srcs, P, recent=1)
        self.assertEqual(alerts, [["A", "rsv", "q75", WK[7]]])

    def test_counts(self):
        rows, _, _ = watch.snapshot(sources(), P)
        c = watch.counts(rows)
        self.assertEqual(c["median"]["rsv"], {"series": 1, "firing": 1, "new": 0, "stale": 0})
        self.assertEqual(c["q75"]["rsv"], {"series": 1, "firing": 1, "new": 1, "stale": 0})
        self.assertEqual(c["popmean"]["rsv"], {"series": 1, "firing": 1, "new": 1, "stale": 0})
        self.assertEqual(c["popgeo"]["rsv"], {"series": 1, "firing": 0, "new": 0, "stale": 0})
        self.assertEqual(c["ed"]["rsv"], {"series": 1, "firing": 0, "new": 0, "stale": 0})

    def test_write_outputs(self):
        rows, alerts, vals = watch.snapshot(sources(), P)
        with tempfile.TemporaryDirectory() as d:
            watch.write_outputs(d, rows, alerts, vals)
            with open(os.path.join(d, "watch.csv"), newline="", encoding="utf-8") as f:
                got = list(csv.reader(f))
            with open(os.path.join(d, "alerts.csv"), newline="", encoding="utf-8") as f:
                got_alerts = list(csv.reader(f))
            with open(os.path.join(d, "recent.csv"), newline="", encoding="utf-8") as f:
                got_vals = list(csv.reader(f))
        self.assertEqual(got[0], watch.WATCH_HEAD)
        self.assertEqual(len(got), 6)
        self.assertEqual(got[4], ["A", "rsv", "popgeo", WK[7], "no data", "", "", "", "0", ""])
        self.assertEqual(got_alerts[0], watch.ALERT_HEAD)
        self.assertEqual(got_alerts[2], ["A", "rsv", "q75", WK[7]])
        self.assertEqual((got_vals[0], len(got_vals)), (watch.RECENT_HEAD, 32))


if __name__ == "__main__":
    unittest.main()

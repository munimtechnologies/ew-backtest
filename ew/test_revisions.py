# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for ew.revisions. Every expected value is traced by hand in the comments."""
import csv
import json
import os
import tempfile
import unittest

from ew import revisions as rv

W0, W1, W2 = "2026-09-19", "2026-10-10", "2026-10-17"   # lags 4 (28 days), 1 and 0 before W2
OLD_ONLY, NEW_ONLY = "2026-09-12", "2026-10-24"         # weeks only one record has: never compared

OLD = {("A", "rsv", "median", OLD_ONLY): 1.0,
       ("A", "rsv", "median", W0): 1.0,
       ("A", "rsv", "median", W1): 2.0,
       ("A", "rsv", "median", W2): 3.0,
       ("A", "rsv", "ed", W0): 1.5, ("A", "rsv", "ed", W1): 1.5, ("A", "rsv", "ed", W2): 1.5,
       ("A", "rsv", "q75", W2): 0.0,
       ("A", "rsv", "popmean", W1): 4.0}
NEW = {("A", "rsv", "median", W0): 1.00004,    # 4e-5 <= TOL: unchanged
       ("A", "rsv", "median", W1): 2.5,        # +0.5 / 2.0 = 0.25: changed, big
       ("A", "rsv", "median", W2): 3.1,        # +0.1 / 3.0 = 0.0333: changed, not big
       ("A", "rsv", "median", NEW_ONLY): 4.0,
       ("A", "rsv", "ed", W0): 1.5, ("A", "rsv", "ed", W1): 1.5, ("A", "rsv", "ed", W2): 1.5,
       ("A", "rsv", "q75", W2): 1.0,           # from 0: changed, big, no relative change
       ("A", "rsv", "popgeo", W0): 2.0}        # appeared at lag 4+; popmean W1 vanished at lag 1
OLD_ALERTS = {("A", "rsv", "median", W1), ("A", "rsv", "q75", OLD_ONLY), ("A", "rsv", "ed", W2)}
NEW_ALERTS = {("A", "rsv", "median", W1), ("A", "rsv", "q75", W2), ("A", "rsv", "ed", W2),
              ("A", "rsv", "median", NEW_ONLY)}


def meta(build="2026-10-28", ok=True):
    return {"gate": {"pass": ok}, "timing": {"grid_last_week": W2, "ed_max_buildnumber": build}}


class TestRevisions(unittest.TestCase):
    def test_lag_bin(self):
        self.assertEqual([rv.lag_bin(w, W2) for w in (W2, W1, "2026-10-03", "2026-09-26", W0)],
                         ["0", "1", "2-3", "2-3", "4+"])

    def test_compare(self):
        tally, rows = rv.compare(OLD, NEW, W2)
        # Common weeks are W0, W1, W2; the OLD_ONLY and NEW_ONLY rows are skipped.
        self.assertEqual(tally["median"]["rsv"]["4+"],
                         {"n": 1, "changed": 0, "big": 0, "vanished": 0, "appeared": 0, "med_abs_rel": None})
        self.assertEqual(tally["median"]["rsv"]["1"],
                         {"n": 1, "changed": 1, "big": 1, "vanished": 0, "appeared": 0, "med_abs_rel": 0.25})
        self.assertEqual(tally["median"]["rsv"]["0"],
                         {"n": 1, "changed": 1, "big": 0, "vanished": 0, "appeared": 0, "med_abs_rel": 0.0333})
        self.assertEqual(tally["q75"]["rsv"]["0"],
                         {"n": 1, "changed": 1, "big": 1, "vanished": 0, "appeared": 0, "med_abs_rel": None})
        self.assertEqual(tally["popmean"]["rsv"]["1"]["vanished"], 1)
        self.assertEqual(tally["popgeo"]["rsv"]["4+"]["appeared"], 1)
        self.assertEqual(sorted(tally["ed"]["rsv"]), ["0", "1", "4+"])
        # Rows in key order (sources sort ed, median, popgeo, popmean, q75); unchanged values have no row.
        self.assertEqual(rows, [
            ["A", "rsv", "median", W1, "1", "changed", 2.0, 2.5, 0.25],
            ["A", "rsv", "median", W2, "0", "changed", 3.0, 3.1, 0.0333],
            ["A", "rsv", "popgeo", W0, "4+", "appeared", "", 2.0, ""],
            ["A", "rsv", "popmean", W1, "1", "vanished", 4.0, "", ""],
            ["A", "rsv", "q75", W2, "0", "changed", 0.0, 1.0, ""]])

    def test_pooled(self):
        tally, _ = rv.compare(OLD, NEW, W2)
        # Lags 0-1 over the four wastewater sources: median W1, median W2, q75 W2, popmean W1, all revised.
        self.assertEqual(rv.pooled(tally, rv.WW, ("0", "1")), (4, 4))
        # Lag 4+: median W0 unchanged, popgeo W0 appeared.
        self.assertEqual(rv.pooled(tally, rv.WW, ("4+",)), (1, 2))
        self.assertEqual(rv.pooled(tally, ("ed",), rv.LAGS), (0, 3))

    def test_alert_flips(self):
        flips, rows = rv.alert_flips(OLD_ALERTS, NEW_ALERTS, rv.common_weeks(OLD, NEW))
        # The OLD_ONLY q75 alert and the NEW_ONLY median alert are outside the common weeks; q75 W2 appeared.
        self.assertEqual(flips["q75"], {"vanished": 0, "appeared": 1})
        self.assertEqual(flips["median"], {"vanished": 0, "appeared": 0})
        self.assertEqual(flips["ed"], {"vanished": 0, "appeared": 0})
        self.assertEqual(rows, [["A", "rsv", "q75", W2, "appeared"]])

    def test_grades(self):
        tally, _ = rv.compare(OLD, NEW, W2)
        flips, _ = rv.alert_flips(OLD_ALERTS, NEW_ALERTS, rv.common_weeks(OLD, NEW))
        # D0: ED 0 of 3 revised, no ED flips, same build. D1: median 2 revised. D2: 4/4 = 1.0 > 1/2 = 0.5.
        # D3: 0.5 >= 0.01. D4: one wastewater alert flip.
        self.assertEqual(rv.grades(tally, flips, meta(), meta()),
                         {"D0": "pass", "D1": "pass", "D2": "pass", "D3": "pass", "D4": "pass"})
        # A different ED build makes D0 untestable; a failed gate makes everything untestable.
        self.assertEqual(rv.grades(tally, flips, meta(), meta("2026-10-29"))["D0"], "untestable")
        self.assertEqual(set(rv.grades(tally, flips, meta(), meta(ok=False)).values()), {"untestable"})

    def test_grades_fail(self):
        new = dict(NEW)
        new[("A", "rsv", "ed", W1)] = 1.6           # an ED value moved under the same build: D0 fails
        tally, _ = rv.compare(OLD, new, W2)
        flips, _ = rv.alert_flips(OLD_ALERTS, OLD_ALERTS, rv.common_weeks(OLD, new))   # no flips: D4 fails
        g = rv.grades(tally, flips, meta(), meta())
        self.assertEqual((g["D0"], g["D4"]), ("fail", "fail"))

    def test_main(self):
        with tempfile.TemporaryDirectory() as d:
            for name, vals, alerts in (("old", OLD, OLD_ALERTS), ("new", NEW, NEW_ALERTS)):
                os.makedirs(os.path.join(d, name))
                rv.write_csv(os.path.join(d, name, "recent.csv"), ["state", "pathogen", "source", "week", "value"],
                             [list(k) + [v] for k, v in sorted(vals.items())])
                rv.write_csv(os.path.join(d, name, "alerts.csv"), ["state", "pathogen", "source", "alert_week"],
                             [list(a) for a in sorted(alerts)])
                with open(os.path.join(d, name, "watch.json"), "w", encoding="utf-8") as f:
                    json.dump(meta(), f)
            out = os.path.join(d, "out")
            self.assertEqual(rv.main(["--old", os.path.join(d, "old"), "--new", os.path.join(d, "new"),
                                      "--out-dir", out]), 0)
            with open(os.path.join(out, "revisions.json"), encoding="utf-8") as f:
                res = json.load(f)
            with open(os.path.join(out, "revisions.csv"), newline="", encoding="utf-8") as f:
                got = list(csv.reader(f))
            with open(os.path.join(out, "alert-flips.csv"), newline="", encoding="utf-8") as f:
                got_flips = list(csv.reader(f))
        self.assertEqual(res["common_weeks"], [W0, W1, W2])
        self.assertEqual(res["records"], {"old": "old", "new": "new"})
        # Lag 0: median W2 and q75 W2 changed; lag 1: median W1 changed, popmean W1 vanished.
        self.assertEqual(res["pooled_ww"], {"0": [2, 2], "1": [2, 2], "2-3": [0, 0], "4+": [1, 2]})
        self.assertEqual(res["shares"]["ed"], {"0": [0, 1], "1": [0, 1], "2-3": [0, 0], "4+": [0, 1]})
        self.assertEqual(set(res["grades"].values()), {"pass"})
        self.assertEqual((got[0], len(got)), (rv.ROW_HEAD, 6))
        self.assertEqual(got[1], ["A", "rsv", "median", W1, "1", "changed", "2.0", "2.5", "0.25"])
        self.assertEqual(got_flips, [rv.FLIP_HEAD, ["A", "rsv", "q75", W2, "appeared"]])


if __name__ == "__main__":
    unittest.main()

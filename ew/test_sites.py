# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for ew.sites. Every expected value is traced by hand in the comments."""
import csv
import json
import os
import tempfile
import unittest

from ew import agg
from ew import sites as si

W0, W1, W2 = "2026-10-03", "2026-10-31", "2026-11-07"   # lags 4+ (35 days), 1 and 0 before W2
REL_OLD, REL_NEW = "2026-11-06 11:00", "2026-11-13 11:00"

# State A covid: s1's whole history doubles (rescaled); s2 never changes; s3 is late for W2 (appears).
# State B rsv: t2 joins with a back-filled W0 value (membership); t1's W2 moves by 4e-7 (below TOL).
OLD = {("A", "covid", "s1", W0): 2.0, ("A", "covid", "s1", W1): 4.0, ("A", "covid", "s1", W2): 6.0,
       ("A", "covid", "s2", W0): 1.0, ("A", "covid", "s2", W1): 1.0, ("A", "covid", "s2", W2): 1.0,
       ("A", "covid", "s3", W0): 3.0,
       ("B", "rsv", "t1", W0): 1.0, ("B", "rsv", "t1", W2): 2.0}
NEW = {("A", "covid", "s1", W0): 4.0, ("A", "covid", "s1", W1): 8.0, ("A", "covid", "s1", W2): 12.0,
       ("A", "covid", "s2", W0): 1.0, ("A", "covid", "s2", W1): 1.0, ("A", "covid", "s2", W2): 1.0,
       ("A", "covid", "s3", W0): 3.0, ("A", "covid", "s3", W2): 5.0,
       ("B", "rsv", "t1", W0): 1.0, ("B", "rsv", "t1", W2): 2.0000004,
       ("B", "rsv", "t2", W0): 7.0}
# State medians. Old: A W0 median(2,1,3) = 2.0; A W1 median(4,1) = 2.5; A W2 median(6,1) = 3.5; B W0 1.0; B W2 2.0.
# New: A W0 median(4,1,3) = 3.0; A W1 median(8,1) = 4.5; A W2 median(12,1,5) = 5.0; B W0 median(1,7) = 4.0;
# B W2 2.0000004.
OLD_MED = {("A", "covid", W0): 2.0, ("A", "covid", W1): 2.5, ("A", "covid", W2): 3.5,
           ("B", "rsv", W0): 1.0, ("B", "rsv", W2): 2.0}
NEW_MED = {("A", "covid", W0): 3.0, ("A", "covid", W1): 4.5, ("A", "covid", W2): 5.0,
           ("B", "rsv", W0): 4.0, ("B", "rsv", W2): 2.0000004}


def rec_vals(meds):
    """State medians as a watch record's recent.csv holds them: source "median", rounded to 4 decimals."""
    return {(st, p, "median", wk): round(v, 4) for (st, p, wk), v in meds.items()}


def site_meta(rel):
    return {"weeks": [W0, W1, W2], "wval_max_date_updated": rel}


def rec_meta(rel, ok=True):
    return {"gate": {"pass": ok}, "timing": {"wval_max_date_updated": rel, "grid_last_week": W2,
                                             "ed_max_buildnumber": "2026-11-11"}}


E0_OK = {"old": {"ok": True}, "new": {"ok": True}}


class TestSnapshot(unittest.TestCase):
    ROWS = [
        {"state_territory": "A", "site": "s1", "week_end": "2026-10-03T00:00:00.000", "pathogen_target": "SARS-CoV-2",
         "site_wval": "2.0", "date_updated": REL_NEW, "population_served": "1000"},
        {"state_territory": "A", "site": "s1", "week_end": "2026-10-03T00:00:00.000", "pathogen_target": "SARS-CoV-2",
         "site_wval": "4.0", "date_updated": REL_OLD, "population_served": "1000"},
        {"state_territory": "A", "site": "s2", "week_end": "2026-10-31", "pathogen_target": "RSV",
         "site_wval": "1.5", "date_updated": REL_OLD, "population_served": ""},
        {"state_territory": "A", "site": "s1", "week_end": "2026-09-26", "pathogen_target": "SARS-CoV-2",
         "site_wval": "9", "date_updated": REL_OLD, "population_served": "1000"},
        {"state_territory": "A", "site": "s9", "week_end": "2026-10-31", "pathogen_target": "Other",
         "site_wval": "1", "date_updated": REL_OLD, "population_served": "5"}]

    def test_snapshot_rows(self):
        acc, meta = {}, {}
        agg.add_sites(acc, self.ROWS, meta)
        by_p, weeks = si.snapshot_rows(acc, recent=2)
        # Weeks with kept rows: 09-26, 10-03, 10-31 (the "Other" row is skipped); the newest 2 are kept.
        self.assertEqual(weeks, ["2026-10-03", "2026-10-31"])
        # s1 on 10-03 has two rows: mean (2 + 4) / 2 = 3.0, rows 2, population 1000. s2 has no population.
        self.assertEqual(by_p, {"covid": [["A", "s1", "2026-10-03", 3.0, 2, 1000]], "influenza": [],
                                "rsv": [["A", "s2", "2026-10-31", 1.5, 1, ""]]})

    def test_snapshot_main(self):
        body = json.dumps(self.ROWS).encode()   # 5 rows < one page: a single fetch
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(si.main(["snapshot", "--out-dir", d], get=lambda url: body), 0)
            vals, meta = si.read_sites(d)
        # Default RECENT 12 keeps all three weeks; the max date_updated is REL_NEW.
        self.assertEqual(meta["weeks"], ["2026-09-26", "2026-10-03", "2026-10-31"])
        self.assertEqual(meta["wval_max_date_updated"], REL_NEW)
        self.assertEqual(meta["rows"], {"covid": 2, "influenza": 0, "rsv": 1})
        self.assertEqual(meta["over_publish_limit"], [])
        self.assertEqual(vals, {("A", "covid", "s1", "2026-09-26"): 9.0, ("A", "covid", "s1", "2026-10-03"): 3.0,
                                ("A", "rsv", "s2", "2026-10-31"): 1.5})


class TestDiff(unittest.TestCase):
    def test_medians_and_sets(self):
        self.assertEqual(si.state_medians(OLD), OLD_MED)
        self.assertEqual(si.state_medians(NEW), NEW_MED)
        self.assertEqual(si.site_sets(NEW)[("A", "covid", W2)], {"s1", "s2", "s3"})

    def test_compare_sites(self):
        tally, rows, weeks = si.compare_sites(OLD, NEW, W2)
        self.assertEqual(weeks, {W0, W1, W2})
        # covid 4+: s1, s2, s3 at W0; only s1 changed (2 -> 4, +100%: big).
        self.assertEqual(tally["covid"]["4+"], {"n": 3, "changed": 1, "big": 1, "appeared": 0, "vanished": 0})
        self.assertEqual(tally["covid"]["1"], {"n": 2, "changed": 1, "big": 1, "appeared": 0, "vanished": 0})
        # covid 0: s1 changed, s2 same, s3 appeared.
        self.assertEqual(tally["covid"]["0"], {"n": 3, "changed": 1, "big": 1, "appeared": 1, "vanished": 0})
        # rsv 4+: t1 same, t2 appeared; rsv 0: t1 moved 4e-7 <= TOL, unchanged.
        self.assertEqual(tally["rsv"]["4+"], {"n": 2, "changed": 0, "big": 0, "appeared": 1, "vanished": 0})
        self.assertEqual(tally["rsv"]["0"], {"n": 1, "changed": 0, "big": 0, "appeared": 0, "vanished": 0})
        self.assertEqual(rows, [["A", "covid", "s1", W0, "4+", "changed", 2.0, 4.0],
                                ["A", "covid", "s1", W1, "1", "changed", 4.0, 8.0],
                                ["A", "covid", "s1", W2, "0", "changed", 6.0, 12.0],
                                ["A", "covid", "s3", W2, "0", "appeared", "", 5.0],
                                ["B", "rsv", "t2", W0, "4+", "appeared", "", 7.0]])

    def test_attribute(self):
        attr, rows = si.attribute(OLD, NEW, {W0, W1, W2}, W2)
        # A W0 and W1: same sites, values moved. A W2: s3 joined. B W0: t2 joined. B W2: 2.0 both after rounding.
        self.assertEqual(attr["covid"]["4+"], {"n": 1, "revised": 1, "membership": 0, "values": 1})
        self.assertEqual(attr["covid"]["0"], {"n": 1, "revised": 1, "membership": 1, "values": 0})
        self.assertEqual(attr["rsv"]["4+"], {"n": 1, "revised": 1, "membership": 1, "values": 0})
        self.assertEqual(attr["rsv"]["0"], {"n": 1, "revised": 0, "membership": 0, "values": 0})
        self.assertEqual(rows, [["A", "covid", W0, "4+", "values", 2.0, 3.0],
                                ["A", "covid", W1, "1", "values", 2.5, 4.5],
                                ["A", "covid", W2, "0", "membership", 3.5, 5.0],
                                ["B", "rsv", W0, "4+", "membership", 1.0, 4.0]])

    def test_rescaled(self):
        # s1: three changed weeks, ratios 2, 2, 2: median 2 is not within 2% of 1, all within 2% of 2.
        self.assertEqual(si.rescaled_sites(OLD, NEW, {W0, W1, W2}), [["A", "covid", "s1", 3, 2.0, 2.0, 2.0]])
        new = dict(NEW)
        new[("A", "covid", "s1", W2)] = 13.0     # ratios 2, 2, 2.1667: 2.1667 / 2 - 1 = 0.083 > 0.02
        self.assertEqual(si.rescaled_sites(OLD, new, {W0, W1, W2}), [])
        self.assertEqual(si.rescaled_sites(OLD, NEW, {W0, W1}), [])   # only 2 changed weeks

    def test_e0(self):
        got = si.e0_check(OLD, site_meta(REL_OLD), rec_vals(OLD_MED), rec_meta(REL_OLD))
        self.assertEqual(got, {"compared": 5, "mismatched": 0, "missing": 0, "same_release": True, "ok": True})
        vals = rec_vals(OLD_MED)
        vals[("A", "covid", "median", W1)] = 2.6           # 0.1 off: mismatched
        vals[("C", "rsv", "median", W0)] = 1.0             # no sites for C: missing
        vals[("A", "covid", "median", "2026-09-19")] = 9.0  # week outside the snapshot: not compared
        vals[("A", "covid", "q75", W0)] = 9.0               # not the median: not compared
        got = si.e0_check(OLD, site_meta(REL_OLD), vals, rec_meta(REL_NEW))
        self.assertEqual(got, {"compared": 6, "mismatched": 1, "missing": 1, "same_release": False, "ok": False})

    def test_grades(self):
        tally, _, weeks = si.compare_sites(OLD, NEW, W2)
        attr, _ = si.attribute(OLD, NEW, weeks, W2)
        resc = si.rescaled_sites(OLD, NEW, weeks)
        # E1: lag 4+ site-weeks in both = (3 - 0) + (2 - 1) = 4, changed 1: 0.25 >= 0.01.
        # E2: 2 revised state medians at lag 4+ < 10: untestable. E3: one rescaled site.
        # E4: lag 0 appeared 1 of (3 + 1) new site-weeks = 0.25 >= 0.05.
        self.assertEqual(si.grades(E0_OK, tally, attr, resc, True),
                         {"E0": "pass", "E1": "pass", "E2": "untestable", "E3": "pass", "E4": "pass"})
        self.assertEqual(set(si.grades(E0_OK, tally, attr, resc, False).values()), {"untestable"})
        bad = {"old": {"ok": True}, "new": {"ok": False}}
        self.assertEqual(si.grades(bad, tally, attr, [], True)["E0"], "fail")
        self.assertEqual(si.grades(bad, tally, attr, [], True)["E3"], "fail")

    def test_grades_e2(self):
        # 10 revised at lag 4+: 6 values -> 0.6 >= 0.5 pass; 4 values -> 0.4 fail. No site tally: E1, E4 untestable.
        a = {"covid": {"4+": {"n": 20, "revised": 10, "membership": 4, "values": 6}}}
        b = {"covid": {"4+": {"n": 20, "revised": 10, "membership": 6, "values": 4}}}
        self.assertEqual(si.grades(E0_OK, {}, a, [], True),
                         {"E0": "pass", "E1": "untestable", "E2": "pass", "E3": "fail", "E4": "untestable"})
        self.assertEqual(si.grades(E0_OK, {}, b, [], True)["E2"], "fail")

    def test_diff_main(self):
        with tempfile.TemporaryDirectory() as d:
            for name, vals, meds, rel in (("old", OLD, OLD_MED, REL_OLD), ("new", NEW, NEW_MED, REL_NEW)):
                folder = os.path.join(d, name)
                os.makedirs(os.path.join(folder, "sites"))
                for p in si.PATHOGENS:
                    rows = [[st, site, wk, v, 1, ""] for (st, pp, site, wk), v in sorted(vals.items()) if pp == p]
                    si.rv.write_csv(os.path.join(folder, "sites", "sites-%s.csv" % p), si.SITE_HEAD, rows)
                with open(os.path.join(folder, "sites", "sites.json"), "w", encoding="utf-8") as f:
                    json.dump(site_meta(rel), f)
                si.rv.write_csv(os.path.join(folder, "recent.csv"), ["state", "pathogen", "source", "week", "value"],
                                [list(k) + [v] for k, v in sorted(rec_vals(meds).items())])
                si.rv.write_csv(os.path.join(folder, "alerts.csv"), ["state", "pathogen", "source", "alert_week"], [])
                with open(os.path.join(folder, "watch.json"), "w", encoding="utf-8") as f:
                    json.dump(rec_meta(rel), f)
            out = os.path.join(d, "out")
            self.assertEqual(si.main(["diff", "--old", os.path.join(d, "old"), "--new", os.path.join(d, "new"),
                                      "--out-dir", out]), 0)
            with open(os.path.join(out, "sitediff.json"), encoding="utf-8") as f:
                res = json.load(f)
            with open(os.path.join(out, "site-changes.csv"), newline="", encoding="utf-8") as f:
                changes = list(csv.reader(f))
            with open(os.path.join(out, "state-changes.csv"), newline="", encoding="utf-8") as f:
                states = list(csv.reader(f))
            with open(os.path.join(out, "rescaled.csv"), newline="", encoding="utf-8") as f:
                resc = list(csv.reader(f))
        # New B W2 median 2.0000004 is within E0_TOL of recent.csv's 2.0, so both records pass E0.
        self.assertEqual(res["grades"], {"E0": "pass", "E1": "pass", "E2": "untestable", "E3": "pass", "E4": "pass"})
        self.assertEqual(res["releases"], {"old": REL_OLD, "new": REL_NEW})
        self.assertEqual((res["lag_reference_week"], res["common_weeks"], res["rescaled_sites"]), (W2, [W0, W1, W2], 1))
        self.assertEqual((changes[0], len(changes)), (si.CHANGE_HEAD, 6))
        self.assertEqual(changes[1], ["A", "covid", "s1", W0, "4+", "changed", "2.0", "4.0"])
        self.assertEqual((states[0], len(states)), (si.STATE_HEAD, 5))
        self.assertEqual(resc, [si.RESCALE_HEAD, ["A", "covid", "s1", "3", "2.0", "2.0", "2.0"]])


if __name__ == "__main__":
    unittest.main()

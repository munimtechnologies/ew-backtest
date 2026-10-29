# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for ew.agg2. Every expected value is traced by hand in the comments."""
import csv
import os
import tempfile
import unittest

from ew import agg
from ew import agg2
from ew import backtest as bt

W1, W2, W3, W4 = "2026-01-03", "2026-01-10", "2026-01-17", "2026-01-24"


def row(site, week, value, pop=None, target="RSV"):
    r = {"state_territory": "A", "site": site, "week_end": week, "pathogen_target": target, "site_wval": value}
    if pop is not None:
        r["population_served"] = pop
    return r


ROWS = [row("s1", W1, "1.0", "100"), row("s1", W1, "3.0", "100"), row("s2", W1, "4.0", "300"),
        row("s3", W1, "10.0"), row("s4", W1, "6.0", "0"),
        row("s1", W2, "1.0", "100"), row("s2", W2, "3.0", "300"), row("s6", W2, "0.0", "100"), row("s7", W2, "5.0")]


def fa(v):
    return {"ww": {"false_per_52_weeks": v}}


class TestAggregates(unittest.TestCase):
    def test_state_aggs(self):
        acc, meta = {}, {}
        agg.add_sites(acc, ROWS, meta)
        out = agg2.state_aggs(acc)
        a = out[("A", "rsv", W1)]
        # Study v2 aggregates unchanged: site means [2, 4, 10, 6] -> median 5, q75 6; popmean (200 + 1200) / 400.
        self.assertEqual((a["median"], a["popmean"], a["q75"]), ((5.0, 4), (3.5, 2), (6.0, 4)))
        # Sites with a population: s1 (mean 2, 100) and s2 (4, 300); s3 has none and s4 has 0.
        # popgeo = exp((100 ln 2 + 300 ln 4) / 400) = exp(1.75 ln 2) = 2 ** 1.75; both above 1 -> share 1.
        self.assertAlmostEqual(a["popgeo"][0], 2 ** 1.75)
        self.assertEqual((a["popgeo"][1], a["share_up"]), (2, (1.0, 2)))
        b = out[("A", "rsv", W2)]
        # With a population: s1 (1.0, 100), s2 (3.0, 300), s6 (0.0, 100); s7 has none.
        # popgeo leaves out s6 (value 0): exp(300 ln 3 / 400) = 3 ** 0.75 over 2 sites.
        # share_up: only s2 is above 1.0 (1.0 is the baseline, not above it): 300 / 500 = 0.6 over 3 sites.
        self.assertAlmostEqual(b["popgeo"][0], 3 ** 0.75)
        self.assertEqual(b["popgeo"][1], 2)
        self.assertAlmostEqual(b["share_up"][0], 0.6)
        self.assertEqual(b["share_up"][1], 3)

    def test_dominated(self):
        acc, meta = {}, {}
        rows = ROWS + [row("s1", W3, "1000.0", "10"), row("s2", W3, "2.0", "1000"), row("s1", W4, "500.0", "10")]
        agg.add_sites(acc, rows, meta)
        d = agg2.dominated(acc)
        # W1: s1 2 x 100 = 200, s2 4 x 300 = 1200; s2 is over half but 4 is not above 100.
        # W2: 100, 900 and 0 from s1, s2, s6; s2 is over half but 3 is not above 100.
        # W3: 1000 x 10 = 10000 of 12000 and 1000 > 100 -> dominated. W4: one site only, not eligible.
        self.assertEqual(d, {"floor": 100.0, "eligible": {"covid": 0, "influenza": 0, "rsv": 3},
                             "state_weeks": {"covid": 0, "influenza": 0, "rsv": 1}})

    def test_no_population(self):
        acc, meta = {}, {}
        agg.add_sites(acc, [row("s3", W1, "10.0")], meta)
        a = agg2.state_aggs(acc)[("A", "rsv", W1)]
        self.assertEqual((a["popgeo"], a["share_up"], a["median"]), ((None, 0), (None, 0), (10.0, 1)))


class TestGrade(unittest.TestCase):
    def setUp(self):
        pass6 = {"alt_only": 6, "median_only": 0, "p_more": 1 / 64}
        none = {"alt_only": 0, "median_only": 0, "p_more": None}
        self.none = none
        self.g1 = {"median": {}, "popmean": {}, "q75": {}, "share_up": {},
                   "popgeo": {"H3_covid": "fail", "H3_influenza": "pass", "H3_rsv": "fail"}}
        # popgeo covid: 4 vs 4 -> P(X >= 4 | 8) = 163 / 256; share_up influenza: 3 + 1 < 5 discordant.
        self.comp = {"popmean": {"covid": none, "influenza": pass6, "rsv": pass6},
                     "q75": {"covid": none, "influenza": pass6, "rsv": none},
                     "popgeo": {"covid": {"alt_only": 4, "median_only": 4, "p_more": 163 / 256},
                                "influenza": pass6, "rsv": pass6},
                     "share_up": {"covid": none, "influenza": {"alt_only": 3, "median_only": 1, "p_more": 0.3125},
                                  "rsv": pass6}}
        self.summary = {"median": {"covid": fa(1.0), "influenza": fa(0.4), "rsv": fa(0.4)},
                        "popgeo": {"covid": fa(1.0), "influenza": fa(0.45), "rsv": fa(0.6)},
                        "share_up": {"covid": fa(2.0), "influenza": fa(0.3), "rsv": fa(None)}}

    def test_grade(self):
        g = agg2.grade(self.g1, self.comp, self.summary, 0.9)
        # R0: popmean influenza, popmean RSV and q75 influenza all pass (6 vs 0, p 1/64).
        # popgeo influenza: K1 pass and 0.45 <= 1.25 * 0.4 = 0.5 -> K2 pass. RSV: 0.6 > 0.5 -> K2 fail.
        # share_up RSV: K1 pass but its false-alarm rate is unknown -> K2 untestable. H3 missing -> untestable.
        self.assertEqual(g, {"R0_replication": "pass",
                             "K1_popgeo_covid": "fail", "K2_popgeo_covid": "fail", "K3_popgeo_covid": "fail",
                             "K1_popgeo_influenza": "pass", "K2_popgeo_influenza": "pass",
                             "K3_popgeo_influenza": "pass",
                             "K1_popgeo_rsv": "pass", "K2_popgeo_rsv": "fail", "K3_popgeo_rsv": "fail",
                             "K1_share_up_covid": "untestable", "K2_share_up_covid": "untestable",
                             "K3_share_up_covid": "untestable",
                             "K1_share_up_influenza": "untestable", "K2_share_up_influenza": "untestable",
                             "K3_share_up_influenza": "untestable",
                             "K1_share_up_rsv": "pass", "K2_share_up_rsv": "untestable",
                             "K3_share_up_rsv": "untestable"})

    def test_low_population_share_and_replication(self):
        low = agg2.grade(self.g1, self.comp, self.summary, 0.3)
        self.assertEqual(low["R0_replication"], "pass")
        self.assertEqual(sorted(set(v for k, v in low.items() if k != "R0_replication")), ["untestable"])
        self.comp["q75"]["influenza"] = self.none
        self.assertEqual(agg2.grade(self.g1, self.comp, self.summary, 0.9)["R0_replication"], "fail")

    def test_fa_ratio(self):
        self.assertAlmostEqual(agg2.fa_ratio(self.summary, "popgeo", "rsv"), 1.5)  # 0.6 / 0.4
        self.assertIsNone(agg2.fa_ratio(self.summary, "share_up", "rsv"))
        zero = {"median": {"covid": fa(0.0)}, "popgeo": {"covid": fa(1.0)}}
        self.assertIsNone(agg2.fa_ratio(zero, "popgeo", "covid"))


class TestAnalyse(unittest.TestCase):
    def test_tiny_run_and_series(self):
        rows = [row("s1", W1, "2.0", "10", "SARS-CoV-2"), row("s1", W2, "4.0", "10", "SARS-CoV-2")]
        acc, meta = {}, {}
        agg.add_sites(acc, rows, meta)
        aggs = agg2.state_aggs(acc)
        ed = {("A", "covid", W1): 1.0, ("A", "covid", W2): 2.0, ("A", "rsv", W2): 0.5}
        base = bt.build_series({k: v["median"] for k, v in aggs.items()}, ed)
        # Two weeks are far too few for any threshold: nothing fires, nothing is graded, R0 fails.
        out = agg2.analyse(aggs, base, reps=5, share=agg.pop_share(meta))
        self.assertEqual(sorted(out["summary"]), ["median", "popgeo", "popmean", "q75", "share_up"])
        self.assertEqual(len(out["grades"]), 19)
        self.assertEqual(out["grades"]["R0_replication"], "fail")
        self.assertEqual(sorted(set(v for k, v in out["grades"].items() if k != "R0_replication")), ["untestable"])
        self.assertIsNone(out["false_alarm_ratio"]["popgeo"]["covid"])
        self.assertEqual(sorted(out["compare"]), ["popgeo", "popmean", "q75", "share_up"])
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "agg2-series.csv")
            agg2.write_series(path, base, aggs)
            with open(path, newline="", encoding="utf-8") as f:
                got = list(csv.reader(f))
        # popgeo of one site is its own value; 2 and 4 are above 1.0, so share_up is 1.
        self.assertEqual(got, [["week_end", "state", "pathogen", "wval_median", "wval_popgeo", "share_up", "sites",
                                "sites_with_population", "ed_percent"],
                               [W1, "A", "covid", "2.0", "2.0", "1.0", "1", "1", "1.0"],
                               [W2, "A", "covid", "4.0", "4.0", "1.0", "1", "1", "2.0"],
                               [W2, "A", "rsv", "", "", "", "0", "0", "0.5"]])


if __name__ == "__main__":
    unittest.main()

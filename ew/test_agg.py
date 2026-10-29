# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for ew.agg. Every expected value is traced by hand in the comments."""
import csv
import os
import tempfile
import unittest

from ew import agg
from ew import backtest as bt

W1, W2 = "2026-01-03", "2026-01-10"

ROWS = [
    {"state_territory": "A", "site": "s1", "week_end": W1 + "T00:00:00.000", "pathogen_target": "RSV",
     "site_wval": "1.0", "population_served": "100", "date_updated": "2026-01-09 10:00"},
    {"state_territory": "A", "site": "s1", "week_end": W1, "pathogen_target": "RSV", "site_wval": "3.0",
     "population_served": "100", "date_updated": "2026-01-09 11:00"},
    {"state_territory": "A", "site": "s2", "week_end": W1, "pathogen_target": "RSV", "site_wval": "4.0",
     "population_served": "300"},
    {"state_territory": "A", "site": "s3", "week_end": W1, "pathogen_target": "RSV", "site_wval": "10.0"},
    {"state_territory": "A", "site": "s4", "week_end": W1, "pathogen_target": "RSV", "site_wval": "6.0",
     "population_served": "0"},
    {"state_territory": "A", "site": "s5", "week_end": W1, "pathogen_target": "Influenza B virus",
     "site_wval": "9.0", "population_served": "50"},
]


class TestAggregates(unittest.TestCase):
    def test_add_sites_and_state_aggs(self):
        acc, meta = {}, {}
        agg.add_sites(acc, ROWS, meta)
        # 6 rows; s5 skipped (not a WVAL target); s3 (no population) and s4 (population 0) kept, no_pop 2.
        self.assertEqual(meta, {"rows": 6, "skipped": 1, "no_pop": 2, "max_date_updated": "2026-01-09 11:00"})
        self.assertAlmostEqual(agg.pop_share(meta), 0.6)  # 1 - 2 / 5 kept rows
        self.assertIsNone(agg.pop_share({}))
        sites = acc[("A", "rsv", W1)]
        self.assertEqual(sites["s1"], {"v": [1.0, 3.0], "pop": 100.0})
        self.assertEqual((sites["s3"]["pop"], sites["s4"]["pop"]), (None, None))
        a = agg.state_aggs(acc)[("A", "rsv", W1)]
        # Site means [2, 4, 10, 6]: median (4 + 6) / 2 = 5; q75 = sorted [2, 4, 6, 10][floor(0.75 * 3) = 2] = 6;
        # popmean over s1, s2 only: (2 * 100 + 4 * 300) / 400 = 3.5.
        self.assertEqual(a, {"median": (5.0, 4), "popmean": (3.5, 2), "q75": (6.0, 4)})

    def test_swap_w(self):
        series = {("A", "rsv"): {"weeks": ["w1", "w2"], "w": [5.0, None], "n": [4, 0], "e": [1.0, 2.0]}}
        aggs = {("A", "rsv", "w1"): {"median": (5.0, 4), "popmean": (None, 0), "q75": (6.0, 4)}}
        q = agg.swap_w(series, aggs, "q75")[("A", "rsv")]
        self.assertEqual((q["weeks"], q["w"], q["n"], q["e"]), (["w1", "w2"], [6.0, None], [4, 0], [1.0, 2.0]))
        pm = agg.swap_w(series, aggs, "popmean")[("A", "rsv")]
        self.assertEqual((pm["w"], pm["n"]), ([None, None], [0, 0]))
        self.assertEqual(series[("A", "rsv")]["w"], [5.0, None])  # the input is not changed


class TestCompareAndGrade(unittest.TestCase):
    def test_compare(self):
        med = {("A", "rsv"): {"events": [5, 9, 13], "rules": {"ww": {"detected": {5: None, 9: 2, 13: 1}}}}}
        alt = {("A", "rsv"): {"events": [5, 9, 13], "rules": {"ww": {"detected": {5: 1, 9: 3, 13: 1}}}}}
        c = agg.compare(alt, med)
        # Onset 5: alternative only. 9: both, 3 - 2 = +1 (alternative earlier). 13: both, tie.
        # More: one +1 -> p = C(1,1) / 2 = 0.5. Earlier: [+1, 0] -> 1 positive, 1 tie, p = 0.5.
        self.assertEqual(c["rsv"], {"alt_only": 1, "median_only": 0, "p_more": 0.5, "both": 2, "alt_earlier": 1,
                                    "median_earlier": 0, "ties": 1, "p_earlier": 0.5})
        self.assertEqual(c["covid"], {"alt_only": 0, "median_only": 0, "p_more": None, "both": 0,
                                      "alt_earlier": 0, "median_earlier": 0, "ties": 0, "p_earlier": None})

    def test_grade(self):
        g1 = {"median": {"H1_covid": "pass", "H1_influenza": "pass", "H1_rsv": "pass",
                         "H3_covid": "fail", "H3_influenza": "fail", "H3_rsv": "fail"},
              "popmean": {"H3_covid": "fail", "H3_influenza": "pass", "H3_rsv": "untestable"},
              "q75": {"H3_covid": "fail", "H3_influenza": "fail", "H3_rsv": "fail"}}
        none = {"alt_only": 0, "median_only": 0, "p_more": None}
        # popmean: covid 4 vs 4 -> P(X >= 4 | 8) = 163 / 256; influenza 6 vs 0 -> 1 / 64; rsv 3 + 1 < 5.
        comp = {"popmean": {"covid": {"alt_only": 4, "median_only": 4, "p_more": 163 / 256},
                            "influenza": {"alt_only": 6, "median_only": 0, "p_more": 1 / 64},
                            "rsv": {"alt_only": 3, "median_only": 1, "p_more": 0.3125}},
                "q75": {"covid": none, "influenza": none, "rsv": none}}
        g = agg.grade(g1, comp, 0.9)
        self.assertEqual(g, {"G0_replication": "pass",
                             "G1_popmean_covid": "fail", "G2_popmean_covid": "fail",
                             "G1_popmean_influenza": "pass", "G2_popmean_influenza": "pass",
                             "G1_popmean_rsv": "untestable", "G2_popmean_rsv": "untestable",
                             "G1_q75_covid": "untestable", "G2_q75_covid": "fail",
                             "G1_q75_influenza": "untestable", "G2_q75_influenza": "fail",
                             "G1_q75_rsv": "untestable", "G2_q75_rsv": "fail"})
        low = agg.grade(g1, comp, 0.3)  # population on too few rows: every popmean grade is untestable
        self.assertEqual([low["G%d_popmean_%s" % (i, p)] for i in (1, 2) for p in bt.PATHOGENS], ["untestable"] * 6)
        self.assertEqual(low["G2_q75_rsv"], "fail")
        g1["median"]["H3_rsv"] = "pass"
        self.assertEqual(agg.grade(g1, comp, 0.9)["G0_replication"], "fail")


class TestAnalyse(unittest.TestCase):
    def test_tiny_run_and_series(self):
        rows = [{"state_territory": "A", "site": "s1", "week_end": W1, "pathogen_target": "SARS-CoV-2",
                 "site_wval": "2.0", "population_served": "10"},
                {"state_territory": "A", "site": "s1", "week_end": W2, "pathogen_target": "SARS-CoV-2",
                 "site_wval": "4.0", "population_served": "10"}]
        acc, meta = {}, {}
        agg.add_sites(acc, rows, meta)
        aggs = agg.state_aggs(acc)
        ed = {("A", "covid", W1): 1.0, ("A", "covid", W2): 2.0, ("A", "rsv", W2): 0.5}
        base = bt.build_series({k: v["median"] for k, v in aggs.items()}, ed)
        # Two weeks are far too few for any threshold: nothing fires, nothing is graded.
        out = agg.analyse(aggs, base, reps=5, share=agg.pop_share(meta))
        self.assertEqual(sorted(out["summary"]), ["median", "popmean", "q75"])
        self.assertEqual(len(out["grades"]), 13)
        self.assertEqual(out["grades"]["G0_replication"], "fail")
        self.assertEqual(sorted(set(v for k, v in out["grades"].items() if k != "G0_replication")), ["untestable"])
        self.assertEqual(out["compare"]["q75"]["covid"]["alt_only"], 0)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "agg-series.csv")
            agg.write_series(path, base, aggs)
            with open(path, newline="", encoding="utf-8") as f:
                got = list(csv.reader(f))
        # Influenza has nothing; RSV has only the ED value in W2.
        self.assertEqual(got, [["week_end", "state", "pathogen", "wval_median", "wval_popmean", "wval_q75", "sites",
                                "sites_with_population", "ed_percent"],
                               [W1, "A", "covid", "2.0", "2.0", "2.0", "1", "1", "1.0"],
                               [W2, "A", "covid", "4.0", "4.0", "4.0", "1", "1", "2.0"],
                               [W2, "A", "rsv", "", "", "", "0", "0", "0.5"]])


if __name__ == "__main__":
    unittest.main()

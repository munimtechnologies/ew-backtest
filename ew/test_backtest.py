# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for ew.backtest. Every expected value is traced by hand in the comments."""
import random
import unittest

from ew import backtest as bt


class TestThresholds(unittest.TestCase):
    def test_quantile(self):
        self.assertEqual(bt.quantile([3, 1, 2, 4], 0.5), 2)   # sorted [1,2,3,4], index int(1.5) = 1
        self.assertEqual(bt.quantile([3, 1, 2, 4], 0.75), 3)  # index int(2.25) = 2
        self.assertIsNone(bt.quantile([], 0.5))

    def test_weeks_between(self):
        self.assertEqual(bt.weeks_between("2022-01-01", "2022-01-22"),
                         ["2022-01-01", "2022-01-08", "2022-01-15", "2022-01-22"])

    def test_trailing_threshold(self):
        x = [1, 2, 3, 4, 5]
        self.assertEqual(bt.trailing_threshold(x, 4, 0.5, 4, 3), 2)   # past [1,2,3,4]
        self.assertIsNone(bt.trailing_threshold(x, 3, 0.5, 4, 3))     # t < window
        self.assertIsNone(bt.trailing_threshold([1, None, None, 4, 5], 4, 0.5, 4, 3))  # 2 values < 3

    def test_rule_flags(self):
        x = [1, 1, 1, 1, 2, 3, 4, 3, 5, 6]
        # t4: thr 1, 2>1 but 1>1 fails; t5: thr 1, 3>2>1; t6: thr 1, 4>3>2; t7: 3<4;
        # t8: past [2,3,4,3] -> thr 3, 5>3 but 3>4 fails; t9: past [3,4,3,5] -> thr 3, 6>5>3
        self.assertEqual(bt.rule_flags(x, 0.5, 4, 4),
                         [False, False, False, False, False, True, True, False, False, True])
        self.assertEqual(bt.rule_flags([1, None, 1, 1, 2], 0.5, 4, 4), [False] * 5)

    def test_above_flags(self):
        x = [1, 1, 1, 1, 2, 3, 4, 3, 5, 6]
        # q .75 thresholds from t4: 1, 1, 2, 3, 3, 4
        self.assertEqual(bt.above_flags(x, 0.75, 4, 4),
                         [None, None, None, None, True, True, True, False, True, True])
        self.assertEqual(bt.above_flags([1, None, 1, 1, 2], 0.75, 4, 4), [None] * 5)


class TestEventsAndLabels(unittest.TestCase):
    A = [None, False, False, True, True, True, False, False, False, True, False, False]

    def test_onsets(self):
        self.assertEqual(bt.onsets([False, True, True, False, False, False, True, False, True], 2), [6])

    def test_event_onsets(self):
        self.assertEqual(bt.event_onsets(self.A, 2), [3])  # t9 is a one-week blip

    def test_label_weeks(self):
        self.assertEqual(bt.label_weeks(self.A, [3], 2),
                         [None, None, "true", "true", "episode", "episode", "episode", "false", "false",
                          None, None, None])

    def test_detect(self):
        self.assertEqual(bt.detect([3], [1, 2], 2), {3: 2})
        self.assertEqual(bt.detect([3], [5], 2), {3: None})
        self.assertEqual(bt.detect([3], [0], 2), {3: None})


class TestStatistics(unittest.TestCase):
    def test_sign_test(self):
        self.assertEqual(bt.sign_test_greater([1, 1, 1, 0, -1]), (3, 1, 1, 5 / 16))
        self.assertEqual(bt.sign_test_greater([1, 1, 2], 1), (1, 0, 2, 0.5))
        self.assertEqual(bt.sign_test_greater([]), (0, 0, 0, None))

    def test_fisher_less(self):
        self.assertAlmostEqual(bt.fisher_less(0, 3, 3, 0), 0.05)  # C(3,0)C(3,3)/C(6,3) = 1/20
        self.assertAlmostEqual(bt.fisher_less(3, 0, 0, 3), 1.0)

    def test_null(self):
        labels = ["true", "false", "false", None, "episode"]
        vals = bt.null_ppvs([(labels, 4), (["true"], 0)], 3, random.Random(1))
        self.assertEqual(len(vals), 3)
        for v in vals:
            self.assertAlmostEqual(v, 1 / 3)  # all four evaluable weeks drawn every time
        self.assertEqual(bt.null_p(0.5, [0.2, 0.5, 0.6]), 0.75)


class TestBuildSeries(unittest.TestCase):
    def test_build(self):
        wstate = {("A", "rsv", "2022-01-01"): (1.5, 2), ("A", "rsv", "2022-01-15"): (2.5, 3),
                  ("B", "covid", "2022-01-01"): (1.0, 1)}
        ed = {("A", "rsv", "2022-01-08"): 0.5, ("A", "covid", "2022-01-22"): 0.7}
        s = bt.build_series(wstate, ed)
        self.assertEqual(sorted(s), [("A", "covid"), ("A", "influenza"), ("A", "rsv")])
        r = s[("A", "rsv")]
        self.assertEqual(r["weeks"], ["2022-01-01", "2022-01-08", "2022-01-15"])
        self.assertEqual(r["w"], [1.5, None, 2.5])
        self.assertEqual(r["n"], [2, 0, 3])
        self.assertEqual(r["e"], [None, 0.5, None])
        self.assertEqual(s[("A", "covid")]["e"], [None, None, None])  # 01-22 is past the last shared week
        self.assertEqual(bt.build_series(wstate, {}), {})


class TestEndToEnd(unittest.TestCase):
    """A 26-week cycle repeated 8 times. ED rises at phase 10 (2,3,4,5,4,3); wastewater two weeks earlier.
    Both trailing thresholds are 1 (40 of every 52 past weeks are 1). Events at phase 10 from week 56 on:
    62, 88, 114, 140, 166, 192. "ww" alerts at phase 9 (lead 1, true); "ed" alerts at phase 11 (after the
    onset, in episode); "both" alerts at phase 10 (lead 0, true). Evaluable weeks: 53..202 = 150."""

    def setUp(self):
        pe = [1.0] * 10 + [2.0, 3.0, 4.0, 5.0, 4.0, 3.0] + [1.0] * 10
        pw = [1.0] * 8 + [2.0, 3.0, 4.0, 5.0, 4.0, 3.0] + [1.0] * 12
        weeks = bt.weeks_between("2022-01-01", "2025-12-20")  # 2022-01-01 + 207 * 7 days
        self.assertEqual(len(weeks), 208)
        self.series = {("A", "rsv"): {"weeks": weeks, "w": pw * 8, "n": [3] * 208, "e": pe * 8}}

    def test_primary(self):
        results, summary, sparse, grades = bt.run_backtest(self.series, bt.PRIMARY, 50, bt.SEED)
        res = results[("A", "rsv")]
        self.assertEqual(res["events"], [62, 88, 114, 140, 166, 192])
        self.assertEqual(res["rules"]["ww"]["alerts"], [61, 87, 113, 139, 165, 191])
        self.assertEqual(res["rules"]["ed"]["alerts"], [63, 89, 115, 141, 167, 193])
        self.assertEqual(res["rules"]["both"]["alerts"], [62, 88, 114, 140, 166, 192])
        s = summary["rsv"]
        self.assertEqual((s["ww"]["events"], s["ww"]["detected"], s["ww"]["lead_median"]), (6, 6, 1))
        self.assertEqual((s["ww"]["alerts_true"], s["ww"]["alerts_false"], s["ww"]["alerts_in_episode"]), (6, 0, 0))
        self.assertEqual(s["ww"]["ppv"], 1.0)
        self.assertEqual(s["ww"]["evaluable_state_weeks"], 150)
        self.assertEqual((s["ed"]["detected"], s["ed"]["alerts_in_episode"]), (0, 6))
        self.assertIsNone(s["ed"]["ppv"])
        self.assertEqual((s["both"]["detected"], s["both"]["lead_median"], s["both"]["alerts_true"]), (6, 0, 6))
        self.assertEqual((s["paired"]["n_both"], s["paired"]["only_ww"], s["paired"]["only_ed"]), (0, 6, 0))
        self.assertIsNotNone(s["ww"]["null_p"])
        self.assertLess(s["ww"]["null_ppv_mean"], 1.0)
        self.assertEqual(summary["covid"]["ww"]["events"], 0)
        self.assertEqual(sparse["dense"], [6, 0])
        self.assertEqual(sparse["sparse"], [0, 0])
        self.assertEqual(grades["H2_rsv"], "untestable")  # 6 events < 20
        self.assertEqual(grades["H5_rsv"], "untestable")  # no ED alerts outside episodes
        self.assertEqual(grades["H6_sparse_sites"], "untestable")
        self.assertEqual(len(grades), 16)

    def test_grid_runs_without_nulls(self):
        for p in bt.GRID:
            _, summary, _, grades = bt.run_backtest(self.series, p, 0, bt.SEED)
            self.assertIsNone(summary["rsv"]["ww"]["null_p"])
            self.assertEqual(grades["H1_rsv"], "untestable")


if __name__ == "__main__":
    unittest.main()

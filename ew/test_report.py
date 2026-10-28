# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for ew.report. Every expected value is traced by hand in the comments."""
import contextlib
import csv
import io
import os
import tempfile
import unittest
from datetime import date, timedelta

from ew import backtest as bt
from ew import report as rp

SMALL = dict(bt.PRIMARY, window=4, min_hist=4)


class TestReadSeries(unittest.TestCase):
    def test_grid_and_gaps(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "series.csv")
            with open(path, "w", newline="", encoding="utf-8") as f:
                f.write("week_end,state,pathogen,wval_state_median,wval_sites,ed_percent\n"
                        "2026-01-03,A,covid,1.5,3,2.0\n"
                        "2026-01-17,A,covid,,0,2.5\n"
                        "2026-01-10,B,rsv,0.5,1,\n")
            s = rp.read_series(path)
        self.assertEqual(sorted(s), [("A", "covid"), ("B", "rsv")])
        self.assertEqual(s[("A", "covid")]["weeks"], ["2026-01-03", "2026-01-10", "2026-01-17"])
        self.assertEqual(s[("A", "covid")]["w"], [1.5, None, None])
        self.assertEqual(s[("A", "covid")]["n"], [3, 0, 0])
        self.assertEqual(s[("A", "covid")]["e"], [2.0, None, 2.5])
        self.assertEqual(s[("B", "rsv")]["w"], [None, 0.5, None])
        self.assertEqual(s[("B", "rsv")]["n"], [0, 1, 0])
        self.assertEqual(s[("B", "rsv")]["e"], [None, None, None])


class TestExplain(unittest.TestCase):
    def test_firing_old_alert(self):
        # Flags (test_backtest): [F,F,F,F,F,T,T,F,F,T]; onsets with refractory 4: only t5 (t9 has t5, t6
        # within 4 weeks). t9: past [3,4,3,5] -> threshold 3; 6 > 5 > 3.
        ex = rp.explain([1, 1, 1, 1, 2, 3, 4, 3, 5, 6], [2] * 10, SMALL)
        self.assertEqual((ex["t"], ex["status"], ex["threshold"], ex["prev"]), (9, "rule firing", 3, [3, 5]))
        self.assertEqual((ex["rising"], ex["alerts"], ex["last_alert"], ex["new_alert"], ex["sites"]),
                         (True, [5], 5, False, 2))

    def test_newest_known_week(self):
        # A trailing missing week is skipped: the newest week with a value is t9, as above.
        ex = rp.explain([1, 1, 1, 1, 2, 3, 4, 3, 5, 6, None], None, SMALL)
        self.assertEqual((ex["t"], ex["status"], ex["sites"]), (9, "rule firing", None))

    def test_above_not_rising(self):
        # t9: threshold 3 (past [3,4,3,5]); 4 > 3 but 4 < 5.
        ex = rp.explain([1, 1, 1, 1, 2, 3, 4, 3, 5, 4], None, SMALL)
        self.assertEqual((ex["status"], ex["rising"], ex["value"]), ("above median", False, 4))

    def test_at_or_below(self):
        ex = rp.explain([1, 1, 1, 1, 2, 3, 4, 3, 5, 2], None, SMALL)  # 2 <= 3
        self.assertEqual(ex["status"], "at or below median")

    def test_too_little_history_and_no_data(self):
        self.assertEqual(rp.explain([1, 2, 3], None, SMALL)["status"], "too little history")  # t2 < window 4
        ex = rp.explain([None, None], [0, 0], SMALL)
        self.assertEqual((ex["t"], ex["status"], ex["value"], ex["sites"]), (1, "no data", None, None))

    def test_new_alert_and_describe(self):
        # t5: past [1,1,1,2] -> threshold 1; 3 > 2 > 1; first firing week, so a new alert.
        ex = rp.explain([1, 1, 1, 1, 2, 3], [0, 0, 0, 0, 0, 7], SMALL)
        self.assertEqual((ex["status"], ex["new_alert"], ex["last_alert"]), ("rule firing", True, 5))
        weeks = ["w0", "w1", "w2", "w3", "w4", "w5"]
        self.assertEqual(rp.describe(ex, weeks, "WW"),
                         "WW, week ending w5: rule firing (new alert this week); value 3.00 vs trailing "
                         "52-week median 1.00; previous two weeks 1.00, 2.00; 7 sites; last alert: w5.")


class TestSvg(unittest.TestCase):
    def test_chart(self):
        s = {"weeks": ["a", "b", "c", "d"], "w": [1, 2, None, 4], "e": [1, 1, 1, 1]}
        svg = rp.svg_chart(s, 0, [("aw", [1, 5])], "X&Y")
        # dx = (640 - 8) / 3 = 210.67; x = 4 + i * dx -> 4.0, 214.7, 425.3, 636.0.
        # ww scale 0..4: y = 4 + 112 * (1 - v / 4) -> v1 88.0, v2 60.0, v4 4.0; ed scale 0..1: y 4.0.
        self.assertEqual(svg.count("<line"), 1)  # mark 5 is past the last week
        self.assertIn('<line class="aw" x1="214.7" y1="0" x2="214.7" y2="120"/>', svg)
        self.assertEqual(svg.count("<polyline"), 3)  # ww splits at the gap
        self.assertIn('<polyline class="ww" points="4.0,88.0 214.7,60.0"/>', svg)
        self.assertIn('<polyline class="ww" points="636.0,4.0"/>', svg)
        self.assertIn('<polyline class="ed" points="4.0,4.0 214.7,4.0 425.3,4.0 636.0,4.0"/>', svg)
        self.assertIn('aria-label="X&amp;Y"', svg)
        self.assertTrue(svg.endswith("</svg>"))


class TestMain(unittest.TestCase):
    def test_end_to_end(self):
        weeks = [(date(2025, 1, 4) + timedelta(days=7 * i)).isoformat() for i in range(60)]
        # Alpha covid under PRIMARY (window 52, min_hist 40): w is 1 for 57 weeks, then 2, 3, 4.
        # t57: 2 > 1 but 1 > 1 fails. t58: past 51 ones + [2] -> median index 25 -> 1; 3 > 2 > 1: fires,
        # the first firing week -> alert 58. t59: past 50 ones + [2, 3] -> 1; 4 > 3 > 2: fires, no new alert.
        # ED is flat 1.0: never above its median 1. Beta & Co rsv: no wastewater, flat ED 2.0.
        w = [1.0] * 57 + [2.0, 3.0, 4.0]
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "series.csv")
            with open(path, "w", newline="", encoding="utf-8") as f:
                cw = csv.writer(f)
                cw.writerow(["week_end", "state", "pathogen", "wval_state_median", "wval_sites", "ed_percent"])
                for i, wk in enumerate(weeks):
                    cw.writerow([wk, "Alpha", "covid", w[i], 5, 1.0])
                    cw.writerow([wk, "Beta & Co", "rsv", "", 0, 2.0])
            out = os.path.join(d, "report")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(rp.main(["--series", path, "--out-dir", out]), 0)
            with open(os.path.join(out, "index.html"), encoding="utf-8") as f:
                page = f.read()
            with open(os.path.join(out, "status.csv"), newline="", encoding="utf-8") as f:
                rows = list(csv.reader(f))
        self.assertEqual(page.count("<svg"), 2)
        self.assertIn("Beta &amp; Co", page)
        self.assertNotIn("Beta & Co", page)
        self.assertIn("not medical advice", page)
        self.assertNotIn("<script", page)
        self.assertEqual(rows[0], rp.STATUS_HEAD)
        self.assertEqual(rows[1], ["Alpha", "covid", weeks[59], "rule firing", "4.00", "1.00", "5", weeks[58],
                                   weeks[59], "at or below median", "1.00", "1.00", ""])
        self.assertEqual(rows[2], ["Beta & Co", "rsv", weeks[59], "no data", "n/a", "n/a", "", "",
                                   weeks[59], "at or below median", "2.00", "2.00", ""])
        self.assertEqual(len(rows), 3)

    def test_needs_an_input(self):
        with tempfile.TemporaryDirectory() as d:
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    rp.main(["--out-dir", d])


if __name__ == "__main__":
    unittest.main()

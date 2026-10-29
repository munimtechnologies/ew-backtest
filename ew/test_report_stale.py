# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for the stale status of ew.report 1.2. Every expected value is traced by hand."""
import unittest

from ew import backtest as bt
from ew import report as rp

SMALL = dict(bt.PRIMARY, window=4, min_hist=4)
WEEKS = ["w%02d" % i for i in range(13)]
# test_report's firing series, then three missing weeks: the newest value (t9) is 3 weeks before t12.
X_STALE = [1, 1, 1, 1, 2, 3, 4, 3, 5, 6, None, None, None]


class TestStale(unittest.TestCase):
    def test_three_weeks_behind_is_stale(self):
        # t9: threshold 3 (past [3,4,3,5]); it would be "rule firing", but 12 - 9 = 3 > STALE_WEEKS 2.
        ex = rp.explain(X_STALE, None, SMALL)
        self.assertEqual((ex["t"], ex["behind"], ex["status"], ex["threshold"], ex["value"]),
                         (9, 3, "stale", 3, 6))
        self.assertEqual((ex["alerts"], ex["last_alert"], ex["new_alert"]), ([5], 5, False))

    def test_two_weeks_behind_is_not_stale(self):
        ex = rp.explain(X_STALE[:12], None, SMALL)  # 11 - 9 = 2, not more than 2
        self.assertEqual((ex["behind"], ex["status"]), (2, "rule firing"))

    def test_stale_alert_week_is_not_new(self):
        # t5: past [1,1,1,2] -> threshold 1; 3 > 2 > 1, the first firing week, so alert 5; 8 - 5 = 3.
        ex = rp.explain([1, 1, 1, 1, 2, 3, None, None, None], None, SMALL)
        self.assertEqual((ex["t"], ex["status"], ex["last_alert"], ex["new_alert"]), (5, "stale", 5, False))

    def test_no_data_is_not_stale(self):
        ex = rp.explain([None, None, None, None], None, SMALL)
        self.assertEqual((ex["status"], ex["behind"]), ("no data", 0))

    def test_describe(self):
        ex = rp.explain(X_STALE, None, SMALL)
        self.assertEqual(rp.describe(ex, WEEKS, "WW"),
                         "WW, week ending w09: stale (nothing newer in the 3 weeks since); value 6.00 vs "
                         "trailing 52-week median 3.00; previous two weeks 3.00, 5.00; last alert: w05.")

    def test_render_does_not_count_stale(self):
        # ED is flat 1.0 to t12: threshold 1.0, 1.0 is not above it -> "at or below median", no alerts.
        series = {("A", "covid"): {"weeks": WEEKS, "w": X_STALE, "n": [1] * 13, "e": [1.0] * 13}}
        page, rows = rp.render(series, {}, rp.WEEKS_SHOWN, p=SMALL)
        self.assertEqual(rows, [["A", "covid", "w09", "stale", "6.00", "3.00", 1, "w05",
                                 "w12", "at or below median", "1.00", "1.00", ""]])
        self.assertIn("<tr><td>COVID-19</td><td>1</td><td>0</td><td>0</td><td>0</td><td>none</td></tr>", page)
        self.assertIn("stale (nothing newer in the 3 weeks since)", page)
        self.assertIn("exactly 1.0", page)
        self.assertIn(rp.AUDIT_URL, page)


if __name__ == "__main__":
    unittest.main()

# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for ew.cdc (no network: a fake get serves the pages)."""
import json
import unittest
import urllib.parse

from ew import cdc


def fake_get(pages, seen):
    def get(url):
        seen.append(urllib.parse.parse_qs(urllib.parse.urlsplit(url).query))
        return json.dumps(pages[len(seen) - 1]).encode()
    return get


class TestParse(unittest.TestCase):
    def test_to_float(self):
        self.assertEqual(cdc.to_float("2"), 2.0)
        self.assertIsNone(cdc.to_float("x"))
        self.assertIsNone(cdc.to_float(None))
        self.assertIsNone(cdc.to_float("nan"))

    def test_week_of(self):
        self.assertEqual(cdc.week_of("2026-10-17T00:00:00.000"), "2026-10-17")
        self.assertEqual(cdc.week_of("2026-10-17"), "2026-10-17")
        self.assertIsNone(cdc.week_of(None))
        self.assertIsNone(cdc.week_of("2026/10/17"))


class TestFetch(unittest.TestCase):
    def test_pages(self):
        seen = []
        got = list(cdc.fetch_pages("abcd-1234", "a,b", None, fake_get([[{"a": 1}, {"a": 2}], [{"a": 3}]], seen),
                                   page=2))
        self.assertEqual(got, [[{"a": 1}, {"a": 2}], [{"a": 3}]])
        self.assertEqual([q["$offset"] for q in seen], [["0"], ["2"]])
        self.assertEqual(seen[0]["$limit"], ["2"])
        self.assertEqual(seen[0]["$order"], [":id"])
        self.assertNotIn("$where", seen[0])

    def test_wval(self):
        rows = [
            {"state_territory": "A", "site": "s1", "week_end": "2026-10-17T00:00:00.000", "pathogen_target": "RSV",
             "site_wval": "1.0", "date_updated": "2026-10-23T11:03:00.000"},
            {"state_territory": "A", "site": "s1", "week_end": "2026-10-17T00:00:00.000", "pathogen_target": "RSV",
             "site_wval": "3.0"},
            {"state_territory": "A", "site": "s2", "week_end": "2026-10-17T00:00:00.000", "pathogen_target": "RSV",
             "site_wval": "5.0"},
            {"state_territory": "A", "site": "s3", "week_end": "2026-10-17", "pathogen_target": "Influenza B",
             "site_wval": "9"},
            {"state_territory": "A", "site": "s4", "week_end": "2026-10-17", "pathogen_target": "RSV"}]
        seen = []
        out, meta = cdc.fetch_wval(fake_get([rows], seen), page=10)
        # s1 counts once at mean 2.0; median of [2.0, 5.0] = 3.5 over 2 sites
        self.assertEqual(out, {("A", "rsv", "2026-10-17"): (3.5, 2)})
        self.assertEqual((meta["rows"], meta["skipped"]), (5, 2))
        self.assertEqual(meta["max_date_updated"], "2026-10-23T11:03:00.000")
        self.assertEqual(seen[0]["$select"], [cdc.WVAL_SELECT])

    def test_ed(self):
        rows = [{"geography": "Wyoming", "week_end": "2026-10-24T00:00:00.000", "percent_visits_covid": "0.77",
                 "percent_visits_influenza": "1.28", "buildnumber": "2026-10-28"},
                {"geography": "", "week_end": "2026-10-24"}]
        seen = []
        out, meta = cdc.fetch_ed(fake_get([rows], seen), page=10)
        self.assertEqual(out, {("Wyoming", "covid", "2026-10-24"): 0.77,
                               ("Wyoming", "influenza", "2026-10-24"): 1.28})
        self.assertEqual((meta["rows"], meta["skipped"], meta["max_buildnumber"]), (2, 1, "2026-10-28"))
        self.assertEqual(seen[0]["$where"], ["trend_source='State'"])


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""cdc: fetch and aggregate two public CDC weekly series through the Socrata (SODA) API on data.cdc.gov.

- NWSS Wastewater Viral Activity Level (WVAL) by site, dataset atcp-73re: SARS-CoV-2, influenza A and
  RSV. A state's weekly value is the median over its sites of each site's WVAL (a site with two rows in
  one week counts once, at their mean); the number of sites is kept as a completeness signal.
- NSSP emergency department visit percentages, dataset rdmq-nq56, rows with trend_source = 'State'
  (percent of ED visits for COVID-19, influenza and RSV, unsmoothed).

Both are US federal public data. Only aggregate weekly state values leave this module.
Standard library only.
"""
import json
import statistics
import time
import urllib.parse
import urllib.request

BASE = "https://data.cdc.gov/resource/%s.json"
WVAL_ID = "atcp-73re"
NSSP_ID = "rdmq-nq56"
WVAL_SELECT = "state_territory,site,week_end,pathogen_target,site_wval,date_updated"
NSSP_SELECT = "week_end,geography,percent_visits_covid,percent_visits_influenza,percent_visits_rsv,buildnumber"
NSSP_WHERE = "trend_source='State'"
WVAL_TARGET = {"SARS-CoV-2": "covid", "Influenza A virus": "influenza", "RSV": "rsv"}
ED_FIELD = {"covid": "percent_visits_covid", "influenza": "percent_visits_influenza", "rsv": "percent_visits_rsv"}
PAGE = 50000
UA = "ew-backtest/1.0 (MV2 of Munim, Inc.; mv2@munimtech.com)"


def http_get(url, tries=4, pause=None):
    """GET url and return the body as bytes, retrying with a growing pause."""
    pause = pause or time.sleep
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.read()
        except Exception:
            if k == tries - 1:
                raise
            pause(10 * (k + 1))


def soda_url(dataset, select, offset, page=PAGE, where=None):
    params = {"$select": select, "$order": ":id", "$limit": page, "$offset": offset}
    if where:
        params["$where"] = where
    return BASE % dataset + "?" + urllib.parse.urlencode(params)


def fetch_pages(dataset, select, where=None, get=None, pause=None, page=PAGE):
    """Yield each page (a list of row dicts) until a page comes back short."""
    get = get or (lambda u: http_get(u, pause=pause))
    offset = 0
    while True:
        batch = json.loads(get(soda_url(dataset, select, offset, page, where)))
        yield batch
        if len(batch) < page:
            return
        offset += page


def to_float(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None


def week_of(v):
    """'2026-10-17T00:00:00.000' or '2026-10-17' -> '2026-10-17'; None if malformed."""
    s = (v or "")[:10]
    return s if len(s) == 10 and s[4] == "-" and s[7] == "-" else None


def add_wval(acc, rows, meta):
    """Collect site values: acc[(state, pathogen, week)][site] = [values]. meta counts rows and kept rows."""
    for r in rows:
        meta["rows"] = meta.get("rows", 0) + 1
        p = WVAL_TARGET.get(r.get("pathogen_target"))
        v = to_float(r.get("site_wval"))
        st, wk, site = r.get("state_territory"), week_of(r.get("week_end")), r.get("site")
        upd = r.get("date_updated") or ""
        if upd > meta.get("max_date_updated", ""):
            meta["max_date_updated"] = upd
        if p is None or v is None or not st or wk is None or site is None:
            meta["skipped"] = meta.get("skipped", 0) + 1
            continue
        acc.setdefault((st, p, wk), {}).setdefault(site, []).append(v)


def state_wval(acc):
    """{(state, pathogen, week): (median of site values, number of sites)}."""
    return {k: (statistics.median([statistics.fmean(v) for v in sites.values()]), len(sites))
            for k, sites in acc.items()}


def add_ed(out, rows, meta):
    """out[(state, pathogen, week)] = percent of ED visits. meta counts rows."""
    for r in rows:
        meta["rows"] = meta.get("rows", 0) + 1
        st, wk = r.get("geography"), week_of(r.get("week_end"))
        b = r.get("buildnumber") or ""
        if b > meta.get("max_buildnumber", ""):
            meta["max_buildnumber"] = b
        if not st or wk is None:
            meta["skipped"] = meta.get("skipped", 0) + 1
            continue
        for p, f in ED_FIELD.items():
            v = to_float(r.get(f))
            if v is not None:
                out[(st, p, wk)] = v


def fetch_wval(get=None, pause=None, page=PAGE):
    acc, meta = {}, {}
    for batch in fetch_pages(WVAL_ID, WVAL_SELECT, None, get, pause, page):
        add_wval(acc, batch, meta)
    return state_wval(acc), meta


def fetch_ed(get=None, pause=None, page=PAGE):
    out, meta = {}, {}
    for batch in fetch_pages(NSSP_ID, NSSP_SELECT, NSSP_WHERE, get, pause, page):
        add_ed(out, batch, meta)
    return out, meta

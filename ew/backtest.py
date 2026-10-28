#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""backtest: one fixed wastewater alert rule against state ED-visit surges, with an ED-only baseline.

Pre-registration: prereg/ew-backtest-prereg-v1-2026-10-28.md. Every constant below is fixed there.

For each (state, pathogen) series on one weekly grid:
- Event (ED surge onset): the first of two weeks running with the ED percent above its trailing 52-week
  75th percentile, after 4 weeks running at or below it.
- Rule R(x, q) fires in week t when x[t] is above its trailing 52-week q-quantile and x rose two weeks
  running (x[t] > x[t-1] > x[t-2]). An alert is the first firing week after 4 quiet weeks.
  "ww" = R(state WVAL, 0.5); "ed" = R(ED percent, 0.5), the ED-only baseline; "both" = "ww" firing in a
  week when the ED percent also rose.
- An event is detected if an alert falls 0 to 4 weeks before its onset; lead = onset - earliest such alert.
- An alert is true if an event onset falls 0 to 4 weeks after it, "in episode" if the ED percent was
  already above its threshold the week before, and otherwise a false alarm. PPV = true / (true + false).
- Null: the same number of alerts per series placed at random evaluable weeks.

Thresholds use past weeks only (no look-ahead). Standard library only.
"""
import random
import statistics
from collections import Counter
from datetime import date, timedelta
from math import comb

PATHOGENS = ("covid", "influenza", "rsv")
RULES = ("ww", "ed", "both")
PRIMARY = {"q": 0.5, "event_q": 0.75, "window": 52, "min_hist": 40, "quiet": 4, "horizon": 4, "refractory": 4}
GRID = tuple(dict(PRIMARY, q=q, horizon=h) for q in (0.5, 0.75) for h in (4, 6))
LATENCY_WEEKS = 1
NULL_REPS = 2000
SEED = 20261029
SPARSE_SITES = 3
MIN_EVENTS = 20
MIN_PAIRED = 10
MIN_ALERTS = 20
MIN_GROUP = 10
ALPHA = 0.05


def quantile(v, q):
    """The value at index floor(q * (n - 1)) of the sorted values; None if empty."""
    if not v:
        return None
    s = sorted(v)
    return s[int(q * (len(s) - 1))]


def ratio(a, b):
    return a / b if b else None


def weeks_between(first, last):
    """ISO dates every 7 days from first to last inclusive."""
    d, end, out = date.fromisoformat(first), date.fromisoformat(last), []
    while d <= end:
        out.append(d.isoformat())
        d += timedelta(days=7)
    return out


def build_series(wstate, ed):
    """{(state, pathogen): {"weeks", "w", "n", "e"}} on one weekly grid, for states in both sources.

    wstate: {(state, pathogen, week): (wval, sites)}; ed: {(state, pathogen, week): percent}.
    The grid runs from the first week in either source to the last week both sources have."""
    states = sorted({k[0] for k in wstate} & {k[0] for k in ed})
    if not states:
        return {}
    first = min(min(k[2] for k in wstate), min(k[2] for k in ed))
    last = min(max(k[2] for k in wstate), max(k[2] for k in ed))
    weeks = weeks_between(first, last)
    out = {}
    for st in states:
        for p in PATHOGENS:
            wn = [wstate.get((st, p, wk)) for wk in weeks]
            out[(st, p)] = {"weeks": weeks, "w": [x[0] if x else None for x in wn],
                            "n": [x[1] if x else 0 for x in wn], "e": [ed.get((st, p, wk)) for wk in weeks]}
    return out


def trailing_threshold(x, t, q, window, min_hist):
    """q-quantile of x[t-window:t] (past weeks only); None before week `window` or with < min_hist values."""
    if t < window:
        return None
    hist = [v for v in x[t - window:t] if v is not None]
    if len(hist) < min_hist:
        return None
    return quantile(hist, q)


def rule_flags(x, q, window, min_hist):
    """R(x, q) per week: x[t] above its trailing q-quantile and x[t] > x[t-1] > x[t-2]; False if unknown."""
    out = []
    for t in range(len(x)):
        ok = False
        if t >= 2 and None not in (x[t], x[t - 1], x[t - 2]):
            th = trailing_threshold(x, t, q, window, min_hist)
            ok = th is not None and x[t] > th and x[t] > x[t - 1] > x[t - 2]
        out.append(ok)
    return out


def above_flags(x, q, window, min_hist):
    """True/False whether x[t] is above its trailing q-quantile; None when either is unknown."""
    out = []
    for t in range(len(x)):
        th = trailing_threshold(x, t, q, window, min_hist) if x[t] is not None else None
        out.append(None if th is None else x[t] > th)
    return out


def onsets(flags, refractory):
    """Weeks where a flag is set after `refractory` weeks without one."""
    return [t for t, f in enumerate(flags) if f and t >= refractory and not any(flags[t - refractory:t])]


def event_onsets(a, quiet):
    """Weeks t with a[t] and a[t+1] True after `quiet` weeks that are all known and False."""
    return [t for t in range(quiet, len(a) - 1)
            if a[t] is True and a[t + 1] is True and all(a[t - k] is False for k in range(1, quiet + 1))]


def label_weeks(a, events, horizon):
    """The outcome an alert in week t would get: "true" if an event onset falls in [t, t + horizon], else
    "episode" if a[t-1] is True, else "false". None (not evaluable) unless a[t-1] .. a[t+horizon+1] are known."""
    ev, n, out = set(events), len(a), []
    for t in range(n):
        if t < 1 or t + horizon + 1 >= n or any(a[k] is None for k in range(t - 1, t + horizon + 2)):
            out.append(None)
        elif any(o in ev for o in range(t, t + horizon + 1)):
            out.append("true")
        elif a[t - 1]:
            out.append("episode")
        else:
            out.append("false")
    return out


def detect(events, alerts, horizon):
    """{onset: lead} with lead = onset - earliest alert in [onset - horizon, onset]; None if no alert."""
    out = {}
    for o in events:
        hits = [o - t for t in alerts if o - horizon <= t <= o]
        out[o] = max(hits) if hits else None
    return out


def rule_set(s, p):
    w, e = s["w"], s["e"]
    fw = rule_flags(w, p["q"], p["window"], p["min_hist"])
    fe = rule_flags(e, p["q"], p["window"], p["min_hist"])
    fb = [bool(fw[t] and t >= 1 and e[t] is not None and e[t - 1] is not None and e[t] > e[t - 1])
          for t in range(len(w))]
    return {"ww": fw, "ed": fe, "both": fb}


def score(flags, events, labels, p):
    alerts = onsets(flags, p["refractory"])
    c = Counter(labels[t] for t in alerts if labels[t] is not None)
    return {"alerts": alerts, "detected": detect(events, alerts, p["horizon"]),
            "true": c["true"], "false": c["false"], "episode": c["episode"],
            "k": c["true"] + c["false"] + c["episode"]}


def run_series(s, p):
    a = above_flags(s["e"], p["event_q"], p["window"], p["min_hist"])
    events = event_onsets(a, p["quiet"])
    labels = label_weeks(a, events, p["horizon"])
    return {"events": events, "labels": labels,
            "rules": {r: score(f, events, labels, p) for r, f in rule_set(s, p).items()}}


def null_ppvs(items, reps, rng):
    """Pooled PPV when each series' k evaluable alerts are moved to k random evaluable weeks."""
    pools = [([l for l in labels if l is not None], k) for labels, k in items if k]
    vals = []
    for _ in range(reps):
        tr = fa = 0
        for pool, k in pools:
            for l in rng.sample(pool, k):
                tr += l == "true"
                fa += l == "false"
        if tr + fa:
            vals.append(tr / (tr + fa))
    return vals


def null_p(obs, nulls):
    return (1 + sum(1 for v in nulls if v >= obs)) / (1 + len(nulls))


def sign_test_greater(diffs, shift=0):
    """One-sided exact sign test that d - shift > 0; ties dropped. (positives, negatives, ties, p)."""
    pos = sum(1 for d in diffs if d - shift > 0)
    neg = sum(1 for d in diffs if d - shift < 0)
    n = pos + neg
    p = sum(comb(n, k) for k in range(pos, n + 1)) / 2 ** n if n else None
    return pos, neg, len(diffs) - n, p


def fisher_less(a, b, c, d):
    """One-sided Fisher exact p that the first row's share a / (a + b) is lower: P(X <= a)."""
    n_all, k_all, n_row = a + b + c + d, a + c, a + b
    den = comb(n_all, n_row)
    return sum(comb(k_all, x) * comb(n_all - k_all, n_row - x) for x in range(0, a + 1)) / den


def median_sites(s, labels):
    v = [n for n, l, w in zip(s["n"], labels, s["w"]) if l is not None and w is not None]
    return statistics.median(v) if v else None


def summarize(series, results, p, reps, seed):
    """Per pathogen: each rule's events, detections, leads, alert outcomes and PPV; nulls; paired leads."""
    rng = random.Random(seed)
    out = {}
    for path in PATHOGENS:
        keys = sorted(k for k in results if k[1] == path)
        agg = {"series": len(keys), "series_with_events": sum(1 for k in keys if results[k]["events"])}
        for r in RULES:
            ev = det = tr = fa = ep = 0
            leads = []
            for k in keys:
                sc = results[k]["rules"][r]
                for lead in sc["detected"].values():
                    ev += 1
                    if lead is not None:
                        det += 1
                        leads.append(lead)
                tr, fa, ep = tr + sc["true"], fa + sc["false"], ep + sc["episode"]
            weeks = sum(1 for k in keys for l in results[k]["labels"] if l is not None)
            agg[r] = {"events": ev, "detected": det, "sensitivity": ratio(det, ev),
                      "lead_median": statistics.median(leads) if leads else None,
                      "lead_counts": {str(l): leads.count(l) for l in range(p["horizon"] + 1)},
                      "alerts_true": tr, "alerts_false": fa, "alerts_in_episode": ep, "ppv": ratio(tr, tr + fa),
                      "evaluable_state_weeks": weeks, "false_per_52_weeks": ratio(fa * 52, weeks)}
        for r in ("ww", "ed"):
            nulls = null_ppvs([(results[k]["labels"], results[k]["rules"][r]["k"]) for k in keys], reps, rng)
            agg[r]["null_reps"] = len(nulls)
            agg[r]["null_ppv_mean"] = statistics.fmean(nulls) if nulls else None
            agg[r]["null_p"] = null_p(agg[r]["ppv"], nulls) if nulls and agg[r]["ppv"] is not None else None
        diffs, only_ww, only_ed, neither = [], 0, 0, 0
        for k in keys:
            dw, de = results[k]["rules"]["ww"]["detected"], results[k]["rules"]["ed"]["detected"]
            for o in results[k]["events"]:
                if dw[o] is not None and de[o] is not None:
                    diffs.append(dw[o] - de[o])
                elif dw[o] is not None:
                    only_ww += 1
                elif de[o] is not None:
                    only_ed += 1
                else:
                    neither += 1
        same, wed = sign_test_greater(diffs), sign_test_greater(diffs, LATENCY_WEEKS)
        agg["paired"] = {"n_both": len(diffs), "only_ww": only_ww, "only_ed": only_ed, "neither": neither,
                         "diff_median": statistics.median(diffs) if diffs else None,
                         "diff_counts": dict(sorted(Counter(diffs).items())),
                         "same_cycle": {"ww_earlier": same[0], "ed_earlier": same[1], "ties": same[2], "p": same[3]},
                         "wednesday_cycle": {"ww_earlier": wed[0], "ed_earlier": wed[1], "ties": wed[2], "p": wed[3]}}
        out[path] = agg
    return out


def sparse_table(series, results):
    """Wastewater-rule detections split by the series' median site count (< SPARSE_SITES = sparse)."""
    t = {"sparse": [0, 0], "dense": [0, 0], "no_sites": 0}
    for k in sorted(results):
        m = median_sites(series[k], results[k]["labels"])
        det = results[k]["rules"]["ww"]["detected"]
        if m is None:
            t["no_sites"] += len(det)
            continue
        g = "sparse" if m < SPARSE_SITES else "dense"
        for lead in det.values():
            t[g][0 if lead is not None else 1] += 1
    a, b = t["sparse"]
    c, d = t["dense"]
    t["p"] = fisher_less(a, b, c, d) if a + b and c + d else None
    return t


def grade(summary, sparse):
    """Pass / fail / untestable for H1-H6, exactly as pre-registered."""
    g = {}
    for path in PATHOGENS:
        s = summary[path]
        ww, ed, pr = s["ww"], s["ed"], s["paired"]
        n_ww, n_ed = ww["alerts_true"] + ww["alerts_false"], ed["alerts_true"] + ed["alerts_false"]
        if n_ww < MIN_ALERTS or ww["null_p"] is None:
            g["H1_" + path] = "untestable"
        else:
            g["H1_" + path] = "pass" if ww["null_p"] < ALPHA and ww["ppv"] > ww["null_ppv_mean"] else "fail"
        if ww["events"] < MIN_EVENTS:
            g["H2_" + path] = "untestable"
        else:
            g["H2_" + path] = "pass" if ww["sensitivity"] >= 0.5 else "fail"
        for h, cyc in (("H3_", "same_cycle"), ("H4_", "wednesday_cycle")):
            pv = pr[cyc]["p"]
            g[h + path] = "untestable" if pr["n_both"] < MIN_PAIRED or pv is None else (
                "pass" if pv < ALPHA else "fail")
        if n_ww < MIN_ALERTS or n_ed < MIN_ALERTS:
            g["H5_" + path] = "untestable"
        else:
            g["H5_" + path] = "pass" if ww["ppv"] >= ed["ppv"] else "fail"
    if sum(sparse["sparse"]) < MIN_GROUP or sum(sparse["dense"]) < MIN_GROUP or sparse["p"] is None:
        g["H6_sparse_sites"] = "untestable"
    else:
        g["H6_sparse_sites"] = "pass" if sparse["p"] < ALPHA else "fail"
    return g


def run_backtest(series, p=None, reps=NULL_REPS, seed=SEED):
    p = p or PRIMARY
    results = {k: run_series(s, p) for k, s in series.items()}
    summary = summarize(series, results, p, reps, seed)
    sparse = sparse_table(series, results)
    return results, summary, sparse, grade(summary, sparse)

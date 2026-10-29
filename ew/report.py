#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""report: one static HTML page showing where the pre-registered rule stands now, from series.csv.

No server and no scripts. For each state and pathogen it draws an inline SVG chart of the last --weeks
weeks: state WVAL and ED percent, each on its own 0..max scale, with the pre-registered ED surge onsets
and the weeks each rule alerted. It also explains each source's newest week in words: its status, the
value against the trailing median, the two weeks before, the site count and the last alert. The rules
and constants come from ew.backtest (PRIMARY, fixed in the pre-registration); nothing here is fitted.

With --backtest (a graded results.json from ew.run) the page also shows how often each rule's alerts
were right in the back-test, with the pre-registered reading for each pathogen. With --states (the
same run's states.csv) each state's block also gives that state's own back-test record.

Writes to --out-dir: index.html and status.csv (one row per state and pathogen).

Usage:
  python -m ew.report --series out/series.csv --out-dir out/report
  python -m ew.report --fetch --out-dir out/report     (fetches CDC first and writes series.csv too)
  python -m ew.report --fetch --backtest results.json --states states.csv --out-dir out/report
"""
import argparse
import csv
import html
import json
import os
import sys
from datetime import datetime, timezone

from ew import backtest as bt

CODE_VERSION = "1.1"
REPO_URL = "https://github.com/munimtechnologies/ew-backtest"
PREREG_URL = REPO_URL + "/blob/main/prereg/ew-backtest-prereg-v1-2026-10-28.md"
WEEKS_SHOWN = 104
W, H, PAD = 640, 120, 4
NAMES = {"covid": "COVID-19", "influenza": "Influenza", "rsv": "RSV"}
RULES = (("ww", "Wastewater"), ("ed", "ED only"), ("both", "Both rising"))
STATUS_HEAD = ["state", "pathogen", "ww_week", "ww_status", "ww_value", "ww_threshold", "ww_sites",
               "ww_last_alert", "ed_week", "ed_status", "ed_value", "ed_threshold", "ed_last_alert"]
CSS = ("body{font-family:Arial,sans-serif;max-width:980px;margin:24px auto;padding:0 12px;color:#222}"
       "table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:3px 6px;font-size:13px}"
       ".ch{display:block;border:1px solid #ddd;margin:4px 0;max-width:100%;height:auto}"
       ".ch polyline{fill:none;stroke-width:1.5}.ch polyline.ww{stroke:#1f6fb2}.ch polyline.ed{stroke:#d9822b}"
       ".ch line.ev{stroke:#ddd;stroke-width:6}.ch line.aw{stroke:#1f6fb2;stroke-dasharray:4 3}"
       ".ch line.ae{stroke:#d9822b;stroke-dasharray:1 3}"
       "p.st{font-size:13px;margin:2px 0}.ww{color:#1f6fb2}.ed{color:#d9822b}")


def esc(v):
    return html.escape(str(v), quote=True)


def num(v):
    return float(v) if v not in (None, "") else None


def fmt(v):
    return "n/a" if v is None else "%.2f" % v


def pct(v):
    return "n/a" if v is None else "%d%%" % round(100 * v)


def lead(v):
    return "n/a" if v is None else "%g" % v


def read_series(path):
    """series.csv (ew.run.write_series) back to {(state, pathogen): {"weeks", "w", "n", "e"}} on one
    weekly grid from the first to the last week in the file. Missing weeks are None (sites 0)."""
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return {}
    weeks = bt.weeks_between(min(r["week_end"] for r in rows), max(r["week_end"] for r in rows))
    idx = {wk: i for i, wk in enumerate(weeks)}
    out = {}
    for r in rows:
        i = idx.get(r["week_end"])
        if i is None:
            continue
        k = (r["state"], r["pathogen"])
        if k not in out:
            out[k] = {"weeks": weeks, "w": [None] * len(weeks), "n": [0] * len(weeks), "e": [None] * len(weeks)}
        out[k]["w"][i] = num(r["wval_state_median"])
        out[k]["n"][i] = int(r["wval_sites"] or 0)
        out[k]["e"][i] = num(r["ed_percent"])
    return out


def read_states(path):
    """states.csv (ew.run.write_states) to {(state, pathogen): row}, values kept as text."""
    with open(path, newline="", encoding="utf-8") as f:
        return {(r["state"], r["pathogen"]): r for r in csv.DictReader(f)}


def explain(x, n=None, p=None):
    """Why rule R(x, q) does or does not fire in the newest week with a value.

    status: "rule firing" (R holds), "above median" (above the trailing q-quantile but not rising two
    weeks running), "at or below median", "too little history" (no threshold yet) or "no data"."""
    p = p or bt.PRIMARY
    known = [i for i, v in enumerate(x) if v is not None]
    t = known[-1] if known else len(x) - 1
    flags = bt.rule_flags(x, p["q"], p["window"], p["min_hist"])
    alerts = bt.onsets(flags, p["refractory"])
    v = x[t] if known else None
    th = bt.trailing_threshold(x, t, p["q"], p["window"], p["min_hist"]) if known else None
    prev = [x[t - 2] if t >= 2 else None, x[t - 1] if t >= 1 else None]
    if v is None:
        status = "no data"
    elif th is None:
        status = "too little history"
    elif flags[t]:
        status = "rule firing"
    elif v > th:
        status = "above median"
    else:
        status = "at or below median"
    past = [a for a in alerts if a <= t]
    return {"t": t, "status": status, "value": v, "threshold": th, "prev": prev,
            "rising": None if None in (v, prev[0], prev[1]) else v > prev[1] > prev[0],
            "new_alert": bool(past) and past[-1] == t, "last_alert": past[-1] if past else None,
            "sites": n[t] if n is not None and known else None, "alerts": alerts}


def describe(ex, weeks, what):
    """One sentence for a reader: the newest week's status and the numbers behind it."""
    head = "%s, week ending %s: %s" % (what, weeks[ex["t"]], ex["status"])
    if ex["new_alert"]:
        head += " (new alert this week)"
    bits = [head]
    if ex["value"] is not None:
        bits.append("value %s vs trailing %d-week median %s" % (fmt(ex["value"]), bt.PRIMARY["window"],
                                                              fmt(ex["threshold"])))
        bits.append("previous two weeks %s, %s" % (fmt(ex["prev"][0]), fmt(ex["prev"][1])))
    if ex["sites"] is not None:
        bits.append("%d sites" % ex["sites"])
    bits.append("last alert: " + (weeks[ex["last_alert"]] if ex["last_alert"] is not None else "none"))
    return "; ".join(bits) + "."


def reading(grades, path):
    """The pre-registered fixed reading for one pathogen, from its graded H1, H3 and H4."""
    h1, h3, h4 = (grades.get("H%d_%s" % (i, path)) for i in (1, 3, 4))
    if h1 == "fail":
        return "Wastewater alerts were no better than chance, so no early-warning claim is made."
    if h1 != "pass":
        return "Not graded: too few alerts or surges."
    if h3 == "fail":
        return ("Wastewater alerts beat chance but did not come earlier than the ED-only rule: "
                "confirmation, not lead.")
    if h3 != "pass":
        return "Wastewater alerts beat chance; whether they came earlier could not be tested."
    if h4 == "pass":
        return "Wastewater alerts came earlier than the ED-only rule, even with a one-week publication delay."
    return ("Wastewater alerts came earlier than the ED-only rule only when the report runs after the "
            "Friday wastewater release.")


def backtest_section(res):
    """HTML: how often each rule's alerts were right in a graded back-test (results.json of ew.run)."""
    summ, grades = res.get("summary") or {}, res.get("grades") or {}
    head = "<h2>How reliable have these alerts been?</h2>"
    if not summ:
        return head + "<p>No graded back-test results were given.</p>"
    rows = ["<tr><th>Pathogen</th><th>Rule</th><th>ED surges caught</th><th>Alerts right (PPV)</th>"
            "<th>PPV by chance</th><th>False alarms per state-year</th><th>Median lead (weeks)</th></tr>"]
    notes = []
    for path in [x for x in bt.PATHOGENS if x in summ]:
        s = summ[path]
        name = NAMES.get(path, path)
        for key, label in RULES:
            r = s.get(key)
            if not r:
                continue
            rows.append("<tr><td>%s</td><td>%s</td><td>%d of %d (%s)</td><td>%s</td><td>%s</td><td>%s</td>"
                        "<td>%s</td></tr>"
                        % (esc(name), esc(label), r["detected"], r["events"], pct(r["sensitivity"]),
                           pct(r["ppv"]), pct(r.get("null_ppv_mean")), fmt(r["false_per_52_weeks"]),
                           lead(r["lead_median"])))
        sent = reading(grades, path)
        same = (s.get("paired") or {}).get("same_cycle")
        if same:
            sent += (" Of the surges both rules caught, wastewater alerted earlier in %d, the ED-only rule in "
                     "%d, and both in the same week in %d." % (same["ww_earlier"], same["ed_earlier"], same["ties"]))
        notes.append("<li><b>%s:</b> %s</li>" % (esc(name), esc(sent)))
    fetched = ((res.get("timing") or {}).get("fetched_at_utc") or "n/a")[:10]
    return (head + "<p>From the pre-registered back-test on data fetched %s, all states pooled. An ED surge "
            "is the ED percent rising above its trailing 75th percentile for two weeks after four quiet weeks. "
            "A surge is caught when an alert falls 0 to 4 weeks before its onset or in the onset week. An "
            "alert is right when a surge onset follows within 4 weeks; alerts during a surge already under way "
            "are left out of PPV. PPV by chance gives the same number of alerts random timing. Both rising "
            "means the wastewater rule firing in a week when the ED percent also rose; it is descriptive and "
            "was not graded. The ED-only rule shares its noise with the surge definition, which favours it on "
            "PPV and works against it on lead.</p>" % esc(fetched)
            + "<table>%s</table><ul>%s</ul>" % ("".join(rows), "".join(notes)))


def track(r):
    """One sentence: a state's back-test record for the wastewater and ED-only rules (a states.csv row)."""
    return ("Back-test record in this state: the wastewater rule caught %s of %s ED surges (%s alerts right, "
            "%s false alarms); the ED-only rule caught %s of %s (%s right, %s false)."
            % (r["ww_detected"], r["events"], r["ww_true"], r["ww_false"],
               r["ed_detected"], r["events"], r["ed_true"], r["ed_false"]))


def points(vals, vmax, x0, dx):
    """Polyline point strings, one per run of known values, on a 0..vmax scale."""
    runs, cur = [], []
    for i, v in enumerate(vals):
        if v is None:
            if cur:
                runs.append(cur)
                cur = []
            continue
        y = PAD + (H - 2 * PAD) * (1 - max(0.0, v) / vmax)
        cur.append("%.1f,%.1f" % (x0 + i * dx, y))
    if cur:
        runs.append(cur)
    return [" ".join(r) for r in runs]


def svg_chart(s, start, marks, label):
    """Inline SVG of weeks start.. of one series. marks: [(css class, [week index, ..])] drawn as
    vertical lines; then the ED percent ("ed") and state WVAL ("ww") lines, each on its own scale."""
    n = len(s["weeks"]) - start
    dx = (W - 2 * PAD) / max(1, n - 1)
    parts = ['<svg class="ch" viewBox="0 0 %d %d" width="%d" height="%d" role="img" aria-label="%s">'
             % (W, H, W, H, esc(label))]
    for cls, idxs in marks:
        for t in idxs:
            if start <= t < len(s["weeks"]):
                xx = PAD + (t - start) * dx
                parts.append('<line class="%s" x1="%.1f" y1="0" x2="%.1f" y2="%d"/>' % (cls, xx, xx, H))
    for key, cls in (("e", "ed"), ("w", "ww")):
        vals = s[key][start:]
        vmax = max((v for v in vals if v is not None and v > 0), default=1.0)
        for pts in points(vals, vmax, PAD, dx):
            parts.append('<polyline class="%s" points="%s"/>' % (cls, pts))
    parts.append("</svg>")
    return "".join(parts)


def status_row(k, s, ww, ed):
    wk = s["weeks"]
    last = lambda ex: wk[ex["last_alert"]] if ex["last_alert"] is not None else ""
    return [k[0], k[1], wk[ww["t"]], ww["status"], fmt(ww["value"]), fmt(ww["threshold"]), ww["sites"], last(ww),
            wk[ed["t"]], ed["status"], fmt(ed["value"]), fmt(ed["threshold"]), last(ed)]


def render(series, meta, weeks_shown=WEEKS_SHOWN, p=None, backtest=None, states=None):
    """(HTML page, status rows) for every series, states in name order. backtest: a results.json dict;
    states: read_states() output. Either may be None, and the page then leaves that part out."""
    p = p or bt.PRIMARY
    states = states or {}
    keys = sorted(series, key=lambda k: (k[0], bt.PATHOGENS.index(k[1]) if k[1] in bt.PATHOGENS else 9, k[1]))
    rows, blocks, tally = [], [], {}
    for k in keys:
        s = series[k]
        ww, ed = explain(s["w"], s["n"], p), explain(s["e"], None, p)
        a = bt.above_flags(s["e"], p["event_q"], p["window"], p["min_hist"])
        events = bt.event_onsets(a, p["quiet"])
        start = max(0, len(s["weeks"]) - weeks_shown)
        name = NAMES.get(k[1], k[1])
        chart = svg_chart(s, start, [("ev", events), ("aw", ww["alerts"]), ("ae", ed["alerts"])],
                          "%s, %s: state wastewater and ED percent" % (k[0], name))
        t = tally.setdefault(k[1], {"series": 0, "ww_firing": 0, "ww_new": 0, "ed_firing": 0, "ww_states": []})
        t["series"] += 1
        t["ww_firing"] += ww["status"] == "rule firing"
        t["ww_new"] += ww["new_alert"]
        t["ed_firing"] += ed["status"] == "rule firing"
        if ww["status"] == "rule firing":
            t["ww_states"].append(k[0])
        rows.append(status_row(k, s, ww, ed))
        rec = '<p class="st">%s</p>' % esc(track(states[k])) if k in states else ""
        blocks.append('<h3 id="%s">%s: %s</h3>%s<p class="st ww">%s</p><p class="st ed">%s</p>%s'
                      % (esc(k[0] + "-" + k[1]), esc(k[0]), esc(name), chart,
                         esc(describe(ww, s["weeks"], "Wastewater (state median WVAL)")),
                         esc(describe(ed, s["weeks"], "ED visits (percent, ED-only rule)")), rec))
    summary = ["<tr><th>Pathogen</th><th>States</th><th>Wastewater rule firing</th><th>New this week</th>"
               "<th>ED-only rule firing</th><th>States with the wastewater rule firing</th></tr>"]
    for path in sorted(tally, key=lambda x: bt.PATHOGENS.index(x) if x in bt.PATHOGENS else 9):
        t = tally[path]
        summary.append("<tr><td>%s</td><td>%d</td><td>%d</td><td>%d</td><td>%d</td><td>%s</td></tr>"
                       % (esc(NAMES.get(path, path)), t["series"], t["ww_firing"], t["ww_new"], t["ed_firing"],
                          esc(", ".join(t["ww_states"]) or "none")))
    weeks = next(iter(series.values()))["weeks"] if series else []
    page = [
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Wastewater and ED early-warning report</title><style>%s</style></head><body>" % CSS,
        "<h1>Wastewater and ED early-warning report: COVID-19, influenza and RSV by state</h1>",
        "<p>Generated %s from public CDC data (NWSS WVAL by site, dataset atcp-73re; NSSP ED visit "
        "percentages, dataset rdmq-nq56), weeks %s to %s. %s</p>"
        % (esc(meta.get("generated_utc", "")), esc(weeks[0] if weeks else "n/a"), esc(weeks[-1] if weeks else "n/a"),
           esc(meta.get("vintage", ""))),
        "<p><b>The rule</b> (fixed in advance, <a href=\"%s\">pre-registration</a>): it fires when a series is "
        "above its own trailing %d-week median and has risen two weeks running. An alert is the first firing "
        "week after %d quiet weeks. It runs on state wastewater (<span class=\"ww\">blue</span>) and, as the "
        "baseline, on ED visits alone (<span class=\"ed\">orange</span>). In the charts, dashed blue lines are "
        "wastewater alerts, dotted orange lines are ED-only alerts and wide grey bands are ED surge onsets "
        "(ED percent above its trailing 75th percentile for two weeks after %d quiet weeks). Each line has its "
        "own scale. How often these alerts were right in the past is measured by the back-test in the "
        "<a href=\"%s\">ew-backtest repository</a>.</p>"
        % (esc(PREREG_URL), p["window"], p["refractory"], p["quiet"], esc(REPO_URL)),
        "<p><b>Limits.</b> State medians hide very different sewersheds, and few sites make a noisy median. "
        "Both sources are revised after release and come out on different days. A firing rule is a signal to "
        "look closer, not a forecast. This is research information for public-health readers, not medical "
        "advice, not a forecast for any person or place, and not a CDC product (no endorsement implied).</p>",
        "<p>By MV2 of Munim, Inc. (mv2@munimtech.com). Code and text were made by AI agents (Claude) working "
        "in MV2's name; no human has reviewed this page. Code Apache-2.0; text and tables CC BY 4.0.</p>",
    ]
    if backtest is not None:
        page.append(backtest_section(backtest))
    page += ["<h2>Newest week at a glance</h2><table>%s</table>" % "".join(summary), "<h2>By state</h2>"]
    page += blocks
    page.append("</body></html>")
    return "\n".join(page), rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--series")
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--backtest", help="results.json of a graded ew.run back-test")
    ap.add_argument("--states", help="states.csv of the same back-test")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--weeks", type=int, default=WEEKS_SHOWN)
    a = ap.parse_args(argv)
    if not a.series and not a.fetch:
        ap.error("give --series or --fetch")
    os.makedirs(a.out_dir, exist_ok=True)
    meta = {"generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}
    backtest = None
    if a.backtest:
        with open(a.backtest, encoding="utf-8") as f:
            backtest = json.load(f)
    states = read_states(a.states) if a.states else None
    path = a.series
    if a.fetch:
        from ew import cdc
        from ew import run
        wstate, wmeta = cdc.fetch_wval()
        ed, emeta = cdc.fetch_ed()
        path = os.path.join(a.out_dir, "series.csv")
        run.write_series(path, bt.build_series(wstate, ed))
        meta["vintage"] = "Wastewater data updated %s; ED data build %s." % (
            wmeta.get("max_date_updated", "n/a")[:10], emeta.get("max_buildnumber", "n/a"))
    # Always render from the file, so --fetch and --series give the same page for the same data.
    series = read_series(path)
    page, rows = render(series, meta, a.weeks, backtest=backtest, states=states)
    with open(os.path.join(a.out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)
    with open(os.path.join(a.out_dir, "status.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(STATUS_HEAD)
        w.writerows(rows)
    firing = {}
    for r in rows:
        firing.setdefault(r[1], [0, 0])
        firing[r[1]][0] += r[3] == "rule firing"
        firing[r[1]][1] += r[9] == "rule firing"
    print(json.dumps({"code_version": CODE_VERSION, "series": len(rows), "html_bytes": len(page.encode("utf-8")),
                      "firing_ww_ed": firing, "backtest": backtest is not None,
                      "state_records": sum(1 for r in rows if (r[0], r[1]) in (states or {}))}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

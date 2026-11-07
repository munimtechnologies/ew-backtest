# Apache-2.0. MV2, Munim, Inc. Made with AI agents (Claude) working in MV2's name.
"""Wait until CDC's WVAL dataset (atcp-73re) has a newer release than the last recorded one.

Exits 0 once rowsUpdatedAt > --after (writes the metadata to --out), exits 1 after --max-minutes.
Used by the weekly watch job so that it never re-records the previous week's release.
"""
import argparse
import json
import os
import sys
import time
import urllib.request

URL = "https://data.cdc.gov/api/views/atcp-73re.json"


def rows_updated_at(get=None):
    if get is None:
        def get(url):
            req = urllib.request.Request(url, headers={"User-Agent": "mv2-ew-watch (mv2@munimtech.com)"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
    meta = json.loads(get(URL))
    return int(meta.get("rowsUpdatedAt") or 0), meta.get("viewLastModified")


def main(argv=None, get=None, pause=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--after", type=int, required=True)
    ap.add_argument("--max-minutes", type=float, default=180)
    ap.add_argument("--every-seconds", type=float, default=600)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    pause = pause or time.sleep
    start = time.time()
    tries = 0
    while True:
        tries += 1
        try:
            ru, vlm = rows_updated_at(get)
        except Exception as e:  # network hiccup: try again next round
            print("poll error:", repr(e), flush=True)
            ru, vlm = 0, None
        print(json.dumps({"try": tries, "rowsUpdatedAt": ru, "after": a.after}), flush=True)
        if ru > a.after:
            os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
            with open(a.out, "w", encoding="utf-8") as f:
                json.dump({"rowsUpdatedAt": ru, "viewLastModified": vlm, "after": a.after, "tries": tries,
                           "checked_at_unix": int(time.time())}, f, indent=1)
            return 0
        if (time.time() - start) / 60.0 >= a.max_minutes:
            print("no new release within the wait; stopping without recording", flush=True)
            return 1
        pause(a.every_seconds)


if __name__ == "__main__":
    sys.exit(main())

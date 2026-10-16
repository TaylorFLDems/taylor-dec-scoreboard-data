#!/usr/bin/env python3
"""
Freshness check for the dashboards. Runs hourly (state-check.yml).

The dashboards cannot read the state PublicStats page themselves: the page sends
no Access-Control-Allow-Origin header, so the browser blocks it (tested from
taylorfldems.org, Oct 16 2026). GitHub has no such limit. So this script reads
the page's "compiled" stamps, compares them with what latest.json holds, and
writes the answer to state_check.json, which the blocks CAN read.

  python check_state.py            fetch the page, write state_check.json
  python check_state.py --offline  recompare using the stamps already on file
                                   (used right after a catch-up pull)

Two stamps, because the state publishes twice on weekdays:
  county     the Taylor row, ~8:04 a.m. These are the numbers the blocks show.
  statewide  the statewide table, re-stamped ~11:01 a.m. on weekdays.
On weekends Taylor does not re-report, so `county` stays on Friday's stamp.

Writes "behind=true|false" to $GITHUB_OUTPUT so the workflow can run the full
pull when the state has posted something newer than we have.

Never exits non-zero for a fetch or parse failure: it records ok=false and the
error, and the badge says the check could not reach the state. The daily pull
is the one that goes red on parser drift.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime

import requests

from scrape import URL, TZ, parse

OUT = os.environ.get("CHECK_OUT", "state_check.json")
LATEST = os.environ.get("OUT", "latest.json")
FMT = "%m/%d/%Y %I:%M%p"          # "10/16/2026 8:04AM"


def stamp(s):
    """Parse the state's compiled stamp. None if blank or unreadable."""
    t = re.sub(r"\s+", " ", s or "").strip().upper()
    t = re.sub(r"\s+(AM|PM)$", r"\1", t)          # tolerate "8:04 AM"
    try:
        return datetime.strptime(t, FMT)
    except ValueError:
        return None


def newer(a, b):
    """True if stamp a is strictly later than stamp b (unreadable b counts as older)."""
    ta, tb = stamp(a), stamp(b)
    if ta is None:
        return False
    return tb is None or ta > tb


def ours():
    with open(LATEST) as f:
        days = json.load(f).get("days") or []
    d = days[-1] if days else {}
    return {"county_compiled": d.get("compiled", ""), "statewide_compiled": d.get("compiled_state", "")}


def load_prev():
    try:
        with open(OUT) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def main(offline=False):
    now = datetime.now(TZ).isoformat(timespec="seconds")
    prev = load_prev()
    rec = {
        "checked_at": now,
        "ok": True,
        "error": None,
        "last_ok_at": prev.get("last_ok_at"),
        "state": prev.get("state") or {"county_compiled": "", "statewide_compiled": ""},
        "source_url": URL,
    }

    if offline:
        rec["checked_at"] = prev.get("checked_at", now)
        rec["ok"] = prev.get("ok", True)
        rec["error"] = prev.get("error")
    else:
        try:
            r = requests.get(URL, timeout=45, headers={
                "User-Agent": "taylor-dec-scoreboard/1.0 (+https://github.com/TaylorFLDems)",
                "Accept": "text/html",
            })
            r.raise_for_status()
            p = parse(r.text)
            rec["state"] = {"county_compiled": p["compiled"], "statewide_compiled": p["compiled_state"]}
            rec["last_ok_at"] = now
        except Exception as e:                      # noqa: BLE001 - recorded, not raised
            rec["ok"] = False
            rec["error"] = f"{type(e).__name__}: {e}"[:300]
            print(f"::warning::could not read the state page: {rec['error']}")

    o = ours()
    rec["ours"] = o
    rec["behind"] = {
        "county": newer(rec["state"]["county_compiled"], o["county_compiled"]),
        "statewide": newer(rec["state"]["statewide_compiled"], o["statewide_compiled"]),
    }
    behind = rec["behind"]["county"] or rec["behind"]["statewide"]

    with open(OUT, "w") as f:
        json.dump(rec, f, indent=1)
        f.write("\n")

    print(f"state  county {rec['state']['county_compiled']!r}  statewide {rec['state']['statewide_compiled']!r}")
    print(f"ours   county {o['county_compiled']!r}  statewide {o['statewide_compiled']!r}")
    print(f"behind {behind}  ok {rec['ok']}")

    gh = os.environ.get("GITHUB_OUTPUT")
    if gh:
        with open(gh, "a") as f:
            f.write(f"behind={'true' if behind else 'false'}\n")


if __name__ == "__main__":
    main(offline="--offline" in sys.argv)

#!/usr/bin/env python3
"""
Tests for check_state.py. Uses the same page fixture as test_scrape.py and a
stubbed requests.get, so nothing touches the network.

Run: python3 test_check_state.py
"""
import json
import os
import sys
import tempfile

import requests

import contextlib
import io

import check_state

# Borrow the page fixture. test_scrape runs its own suite on import, so mute it.
with contextlib.redirect_stdout(io.StringIO()):
    from test_scrape import page

FAILS = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"  {detail}"))
    if not cond:
        FAILS.append(name)


def fixture(county_stamp):
    row = lambda a, b, c, d, t: ["Taylor", "49894 - General", a, b, "1", "1", t, county_stamp]
    return page(row("10", "5", "1", "1", "17"), row("4", "3", "1", "1", "9"),
                ["Taylor", "49894 - General", "0", "0", "0", "0", "0", ""], election="49894")


class Resp:
    def __init__(self, text, status=200):
        self.text, self.status_code = text, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")


def run(latest_days, html=None, error=None, prev=None, offline=False):
    d = tempfile.mkdtemp()
    latest, out, gh = (os.path.join(d, n) for n in ("latest.json", "state_check.json", "gh_out"))
    with open(latest, "w") as f:
        json.dump({"days": latest_days}, f)
    if prev is not None:
        with open(out, "w") as f:
            json.dump(prev, f)
    check_state.LATEST, check_state.OUT = latest, out
    os.environ["GITHUB_OUTPUT"] = gh

    def fake_get(*a, **k):
        if error:
            raise error
        return Resp(html)
    real, requests.get = requests.get, fake_get
    check_state.requests.get = fake_get
    try:
        check_state.main(offline=offline)
    finally:
        requests.get = real
        check_state.requests.get = real
    with open(out) as f:
        rec = json.load(f)
    with open(gh) as f:
        flag = f.read().strip()
    return rec, flag


day = lambda c, s: {"date": "2026-10-16", "compiled": c, "compiled_state": s}

# stamps parse, including the statewide newline form and a spaced AM/PM
check("stamp: compact", check_state.stamp("10/16/2026 8:04AM") is not None)
check("stamp: spaced", check_state.stamp("10/16/2026  8:04 am") is not None)
check("stamp: blank is None", check_state.stamp("") is None)
check("newer: 11:01 after 8:04", check_state.newer("10/16/2026 11:01AM", "10/16/2026 8:04AM"))
check("newer: next day beats same time", check_state.newer("10/17/2026 8:04AM", "10/16/2026 8:04AM"))
check("newer: equal is not newer", not check_state.newer("10/16/2026 8:04AM", "10/16/2026 8:04AM"))
check("newer: 12-hour clock (12:30PM after 11:01AM)", check_state.newer("10/16/2026 12:30PM", "10/16/2026 11:01AM"))

# current: our file matches the page
rec, flag = run([day("08/07/2026 8:03AM", "08/07/2026 11:01AM")], html=fixture("08/07/2026 8:03AM"))
check("current: ok", rec["ok"] is True, rec)
check("current: not behind", rec["behind"] == {"county": False, "statewide": False}, rec["behind"])
check("current: output false", flag == "behind=false", flag)
check("current: records page stamps", rec["state"]["county_compiled"] == "08/07/2026 8:03AM", rec["state"])
check("current: last_ok_at set", rec["last_ok_at"] == rec["checked_at"])

# behind: the page carries a newer Taylor stamp than latest.json
rec, flag = run([day("08/06/2026 8:03AM", "08/06/2026 11:01AM")], html=fixture("08/07/2026 8:03AM"))
check("behind: county", rec["behind"]["county"] is True, rec["behind"])
check("behind: output true", flag == "behind=true", flag)

# statewide-only republish (the 11:01 a.m. weekday stamp) still triggers a pull
rec, flag = run([day("08/07/2026 8:03AM", "08/07/2026 8:03AM")], html=fixture("08/07/2026 8:03AM"))
check("statewide-only: county not behind", rec["behind"]["county"] is False)
check("statewide-only: statewide behind", rec["behind"]["statewide"] is True)
check("statewide-only: output true", flag == "behind=true", flag)

# fetch failure: recorded, previous stamps kept, nothing raised
prev = {"checked_at": "2026-10-16T09:13:00-04:00", "last_ok_at": "2026-10-16T09:13:00-04:00", "ok": True,
        "state": {"county_compiled": "10/16/2026 8:04AM", "statewide_compiled": "10/16/2026 8:04AM"}}
rec, flag = run([day("10/16/2026 8:04AM", "10/16/2026 8:04AM")], error=requests.ConnectionError("reset"), prev=prev)
check("failure: ok false", rec["ok"] is False)
check("failure: error recorded", "reset" in (rec["error"] or ""), rec["error"])
check("failure: keeps last good stamps", rec["state"] == prev["state"], rec["state"])
check("failure: keeps last_ok_at", rec["last_ok_at"] == prev["last_ok_at"])
check("failure: not behind", flag == "behind=false", flag)

# a page that no longer parses is a failure, not a crash
rec, flag = run([day("10/16/2026 8:04AM", "10/16/2026 8:04AM")], html="<html>maintenance</html>")
check("unparseable: ok false", rec["ok"] is False and "ParseError" in rec["error"], rec["error"])

# offline recompare after a catch-up pull: keeps the check's own time, clears behind
prev = {"checked_at": "2026-10-16T11:13:00-04:00", "last_ok_at": "2026-10-16T11:13:00-04:00", "ok": True,
        "state": {"county_compiled": "10/16/2026 8:04AM", "statewide_compiled": "10/16/2026 11:01AM"}}
rec, flag = run([day("10/16/2026 8:04AM", "10/16/2026 11:01AM")], prev=prev, offline=True)
check("offline: keeps checked_at", rec["checked_at"] == prev["checked_at"], rec["checked_at"])
check("offline: no longer behind", flag == "behind=false" and not any(rec["behind"].values()), rec["behind"])

print()
if FAILS:
    print(f"{len(FAILS)} failed")
    sys.exit(1)
print("all passed")

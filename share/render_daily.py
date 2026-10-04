"""Render the daily Precinct 13 social graphic from p13.json.

Writes share/daily/p13-YYYY-MM-DD.png (today's date, Eastern) and
share/p13-today.png (same image, stable link). 1080x1080 for a Facebook or
Instagram feed post.

Shows only what the public scoreboard shows: Precinct 13 Democratic ballots,
the 600 goal with milestones, and the countdown. Aggregates only.

Usage:  python share/render_daily.py [--date YYYY-MM-DD]   (--date is for testing)
"""
import argparse, datetime as dt, html, json, os, shutil, sys
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
SHARE = ROOT / "share"
ASSETS = SHARE / "assets"

EV_START = dt.date(2026, 10, 24)
EV_END = dt.date(2026, 10, 31)
EDAY = dt.date(2026, 11, 3)
GOAL = 600
MILES = [100, 250]
PAGE = "taylorfldems.org/p13-scoreboard"


def nice(d):
    return f"{d:%b} {d.day}"


def plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def chip_text(today):
    if today < EV_START:
        n = (EV_START - today).days
        return "Early voting starts tomorrow" if n == 1 else f"Early voting in {n} days"
    if today <= EV_END:
        return "Early voting open through Oct 31" if today < EV_END else "Last day of early voting"
    if today < EDAY:
        return "Election Day is Tuesday"
    return "Election Day: polls open 7 AM to 7 PM"


def build(p, today):
    me = (p.get("precincts") or {}).get("013") or {}
    count = me.get("cast_before_eday")
    if count is None:
        sys.exit("p13.json has no Precinct 13 count; not rendering.")
    through = dt.date.fromisoformat(p["through"])

    hist = [h for h in p.get("history", []) if h.get("p13") is not None]
    delta_html = ""
    if len(hist) >= 2 and hist[-1]["p13"] > hist[-2]["p13"]:
        d = hist[-1]["p13"] - hist[-2]["p13"]
        delta_html = f'<span class="delta">+{d:,} since {nice(dt.date.fromisoformat(hist[-2]["date"]))}</span>'

    if count > 0:
        hero = (f'<div class="big">{count:,}</div>'
                f'<div class="lab">Precinct 13 Democratic ballots {delta_html}</div>'
                f'<div class="of">of {GOAL} by Nov 3</div>')
    else:
        # A zero count makes a poor headline, so lead with the countdown instead.
        if today < EV_START:
            n, what = (EV_START - today).days, "until early voting opens"
        else:
            n, what = max((EDAY - today).days, 0), "until Election Day"
        big, lab = (n, f'{"day" if n == 1 else "days"} {what}') if n else ("Today", "is Election Day")
        hero = (f'<div class="big">{big}</div>'
                f'<div class="lab">{lab}</div>'
                f'<div class="of">Every Precinct 13 neighbor who votes shows up on the scoreboard.</div>')

    chip = chip_text(today)
    if count == 0 and today < EV_START:
        chip = "Early voting Oct 24 to 31"  # the hero already shows the countdown
    nxt = next((m for m in MILES + [GOAL] if count < m), None)
    if nxt is None:
        next_line = "Goal reached. Keep going."
    elif count == 0:
        next_line = f"First milestone: {MILES[0]} ballots"
    else:
        target = f"the {GOAL} goal" if nxt == GOAL else f"{nxt}"
        next_line = f"{plural(nxt - count, 'more ballot')} to reach {target}"
    fill = min(100.0, 100.0 * count / GOAL)
    ticks = "".join(
        f'<b class="t" style="left:{100*m/GOAL:.2f}%"><span>{m}</span></b>' for m in MILES)

    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:Archivo;font-weight:700;src:url(fonts/archivo-latin-700-normal.woff2)}}
@font-face{{font-family:Archivo;font-weight:800;src:url(fonts/archivo-latin-800-normal.woff2)}}
@font-face{{font-family:Archivo;font-weight:900;src:url(fonts/archivo-latin-900-normal.woff2)}}
@font-face{{font-family:'Libre Franklin';font-weight:400;src:url(fonts/libre-franklin-latin-400-normal.woff2)}}
@font-face{{font-family:'Libre Franklin';font-weight:500;src:url(fonts/libre-franklin-latin-500-normal.woff2)}}
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:1080px;height:1080px;background:#0A3161;color:#fff;overflow:hidden}}
.c{{position:relative;width:1080px;height:1080px;padding:64px 72px 0;color:#fff}}
.top{{display:flex;justify-content:space-between;align-items:center}}
.logo{{height:84px;display:block}}
.chip{{font:800 21px Archivo;letter-spacing:.06em;text-transform:uppercase;background:#fff;color:#0A3161;padding:14px 22px;border-radius:999px}}
.kick{{display:flex;align-items:center;gap:14px;margin-top:84px;font:700 22px Archivo;letter-spacing:.14em;text-transform:uppercase}}
.kick:before{{content:"";width:38px;height:4px;background:#fff}}
.big{{font:900 250px/0.9 Archivo;letter-spacing:-.03em;margin-top:26px}}
.lab{{font:800 44px/1.15 Archivo;margin-top:22px;display:flex;align-items:center;gap:18px;flex-wrap:wrap}}
.delta{{font:800 22px Archivo;letter-spacing:.04em;text-transform:uppercase;background:#B31942;padding:10px 16px;border-radius:999px}}
.of{{font:500 32px/1.35 'Libre Franklin';color:rgba(255,255,255,.88);margin-top:14px;max-width:880px}}
.bar{{position:relative;margin-top:62px;width:936px;height:18px;background:rgba(255,255,255,.2);border-radius:4px}}
.fill{{position:absolute;left:0;top:0;bottom:0;background:#fff;border-radius:4px}}
.t{{position:absolute;top:-7px;width:3px;height:32px;background:rgba(255,255,255,.65);margin-left:-1.5px}}
.t span{{position:absolute;top:40px;left:50%;transform:translateX(-50%);font:700 21px Archivo;color:rgba(255,255,255,.85)}}
.end{{position:absolute;right:0;top:40px;font:700 21px Archivo;letter-spacing:.04em;text-transform:uppercase}}
.next{{margin-top:84px;font:500 28px 'Libre Franklin';color:rgba(255,255,255,.92)}}
.foot{{position:absolute;left:72px;right:72px;bottom:58px;display:flex;justify-content:space-between;align-items:flex-end}}
.url{{font:800 30px Archivo}}
.url small{{display:block;font:700 18px Archivo;letter-spacing:.12em;text-transform:uppercase;color:rgba(255,255,255,.75);margin-bottom:6px}}
.asof{{font:500 20px 'Libre Franklin';color:rgba(255,255,255,.7);text-align:right}}
.stripe{{position:absolute;left:0;right:0;bottom:0;height:20px;background-image:repeating-linear-gradient(120deg,#061f3e 0,#061f3e 14px,#B31942 14px,#B31942 28px,#fff 28px,#fff 42px)}}
</style></head><body><div class="c">
<div class="top"><img class="logo" src="logo-white.png" alt=""><div class="chip">{html.escape(chip)}</div></div>
<div class="kick">Precinct 13 Scoreboard</div>
{hero}
<div class="bar"><div class="fill" style="width:{fill:.2f}%"></div>{ticks}<div class="end">Goal: {GOAL}</div></div>
<div class="next">{html.escape(next_line)}</div>
</div>
<div class="foot"><div class="url"><small>Make your plan to vote</small>{PAGE}</div>
<div class="asof">Ballots counted through {nice(through)}</div></div>
<div class="stripe"></div></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="render as if today were this date (testing)")
    ap.add_argument("--out", help="write only this file (testing)")
    a = ap.parse_args()
    today = dt.date.fromisoformat(a.date) if a.date else dt.datetime.now(ZoneInfo("America/New_York")).date()
    if today > EDAY:
        print("After Election Day; nothing to render.")
        return
    p = json.loads((ROOT / "p13.json").read_text())
    page = ASSETS / "_render.html"
    page.write_text(build(p, today))
    from playwright.sync_api import sync_playwright
    out = Path(a.out) if a.out else SHARE / "daily" / f"p13-{today.isoformat()}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            pg = b.new_page(viewport={"width": 1080, "height": 1080})
            pg.goto(page.as_uri())
            pg.evaluate("document.fonts.ready")
            pg.screenshot(path=str(out))
            b.close()
    finally:
        page.unlink(missing_ok=True)
    if not a.out:
        shutil.copyfile(out, SHARE / "p13-today.png")
    print(f"Rendered {out.relative_to(ROOT) if not a.out else out} (P13 count through {p['through']})")


if __name__ == "__main__":
    main()

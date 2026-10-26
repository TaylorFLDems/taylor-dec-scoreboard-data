"""Render the daily Perry and Taylor County turnout graphic from neighborhoods.json.

Writes share/daily/turnout-YYYY-MM-DD.png (today's date, Eastern) and
share/turnout-today.png (same image, stable link). 1080x1080 for a Facebook or
Instagram feed post. Same look as the P13 graphic (render_daily.py).

Shows only what the public neighborhood scoreboard (/2026scoreboard) shows:
whole percentages of Democrats who have voted, for Perry, the county, and the
six county areas. Percentages only, no counts, no voter data.

Usage:  python share/render_turnout.py [--date YYYY-MM-DD] [--out FILE]   (testing)
"""
import argparse, datetime as dt, html, json, shutil, sys
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
SHARE = ROOT / "share"
ASSETS = SHARE / "assets"

EV_START = dt.date(2026, 10, 24)
EV_END = dt.date(2026, 10, 31)
EDAY = dt.date(2026, 11, 3)
PAGE = "taylorfldems.org/2026scoreboard"
# Same names as the county map on the neighborhood scoreboard page.
AREAS = {"perry": "Perry", "north": "North & West", "southwest": "Hampton Springs & Southwest",
         "east": "East County", "coast": "The Beaches", "south": "Salem & Steinhatchee"}


def nice(d):
    return f"{d:%b} {d.day}"


def chip_text(today):
    if today < EV_START:
        n = (EV_START - today).days
        return "Early voting starts tomorrow" if n == 1 else f"Early voting in {n} days"
    if today <= EV_END:
        return "Early voting open through Oct 31" if today < EV_END else "Last day of early voting"
    if today < EDAY:
        return "Election Day is Tuesday"
    return "Election Day: polls open 7 AM to 7 PM"


def gain(hist, key):
    """Points gained since the previous file, or None. History rows are keyed by the
    file's last activity date; the state posts each file the next morning."""
    h = [x for x in hist if isinstance(x.get(key), (int, float))]
    if len(h) < 2 or h[-1][key] <= h[-2][key]:
        return None
    prev_file = dt.date.fromisoformat(h[-2]["date"]) + dt.timedelta(days=1)
    d = h[-1][key] - h[-2][key]
    return f"+{d:g} {'point' if d == 1 else 'points'} since the {nice(prev_file)} file"


def build(n, today):
    perry, county, bk = n.get("perry"), n.get("county"), n.get("buckets") or {}
    if not isinstance(perry, (int, float)) or not isinstance(county, (int, float)):
        sys.exit("neighborhoods.json has no Perry or county share; not rendering.")
    file_day = dt.date.fromisoformat(n.get("file_date") or n["through"])
    hist = n.get("history", [])

    def stat(v, who, g):
        return (f'<div class="st"><div class="big">{v:g}<i>%</i></div>'
                f'<div class="lab">of {who} Democrats have voted</div>'
                + (f'<div class="delta">{html.escape(g)}</div>' if g else '') + '</div>')

    rows = sorted(((AREAS[k], bk[k], k == "perry") for k in AREAS if isinstance(bk.get(k), (int, float))),
                  key=lambda r: (-r[1], r[0]))
    top = max([r[1] for r in rows] + [1])
    bars = "".join(
        f'<div class="row{" me" if me else ""}"><span class="nm">{html.escape(name)}</span>'
        f'<span class="tr"><i style="width:{100 * v / top:.1f}%"></i></span><span class="v">{v:g}%</span></div>'
        for name, v, me in rows)

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
.kick{{display:flex;align-items:center;gap:14px;margin-top:56px;font:700 22px Archivo;letter-spacing:.14em;text-transform:uppercase}}
.kick:before{{content:"";width:38px;height:4px;background:#fff}}
.stats{{display:grid;grid-template-columns:1fr 1fr;gap:40px;margin-top:22px}}
.big{{font:900 168px/0.9 Archivo;letter-spacing:-.03em}}
.big i{{font-style:normal;font-size:96px;letter-spacing:0;margin-left:4px}}
.lab{{font:800 30px/1.2 Archivo;margin-top:14px;max-width:420px}}
.delta{{display:inline-block;font:800 19px Archivo;letter-spacing:.04em;text-transform:uppercase;background:#B31942;padding:9px 14px;border-radius:999px;margin-top:14px}}
.sec{{margin-top:44px;font:700 20px Archivo;letter-spacing:.14em;text-transform:uppercase;color:rgba(255,255,255,.8)}}
.rows{{margin-top:14px}}
.row{{display:grid;grid-template-columns:352px 1fr 84px;align-items:center;gap:16px;height:42px}}
.nm{{font:500 23px 'Libre Franklin';color:rgba(255,255,255,.9);white-space:nowrap}}
.tr{{position:relative;height:16px;background:rgba(255,255,255,.14);border-radius:3px}}
.tr i{{position:absolute;left:0;top:0;bottom:0;background:rgba(255,255,255,.55);border-radius:3px}}
.v{{font:800 25px Archivo;text-align:right}}
.row.me .nm{{font-family:Archivo;font-weight:800;color:#fff}}
.row.me .tr i{{background:#fff}}
.foot{{position:absolute;left:72px;right:72px;bottom:58px;display:flex;justify-content:space-between;align-items:flex-end}}
.url{{font:800 30px Archivo}}
.url small{{display:block;font:700 18px Archivo;letter-spacing:.12em;text-transform:uppercase;color:rgba(255,255,255,.75);margin-bottom:6px}}
.asof{{font:500 20px 'Libre Franklin';color:rgba(255,255,255,.7);text-align:right}}
.stripe{{position:absolute;left:0;right:0;bottom:0;height:20px;background-image:repeating-linear-gradient(120deg,#061f3e 0,#061f3e 14px,#B31942 14px,#B31942 28px,#fff 28px,#fff 42px)}}
</style></head><body><div class="c">
<div class="top"><img class="logo" src="logo-white.png" alt=""><div class="chip">{html.escape(chip_text(today))}</div></div>
<div class="kick">Taylor Democrats are voting</div>
<div class="stats">{stat(perry, "Perry", gain(hist, "perry"))}{stat(county, "Taylor County", gain(hist, "county"))}</div>
<div class="sec">Across the county</div>
<div class="rows">{bars}</div>
</div>
<div class="foot"><div class="url"><small>Find your neighborhood</small>{PAGE}</div>
<div class="asof">State file of {nice(file_day)}</div></div>
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
    n = json.loads((ROOT / "neighborhoods.json").read_text())
    page = ASSETS / "_render_turnout.html"
    page.write_text(build(n, today))
    from playwright.sync_api import sync_playwright
    out = Path(a.out) if a.out else SHARE / "daily" / f"turnout-{today.isoformat()}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            pg = b.new_page(viewport={"width": 1080, "height": 1080})
            pg.goto(page.as_uri())
            pg.evaluate("document.fonts.ready")
            # Refuse to write an image whose text spills out of the frame.
            spill = pg.evaluate("""() => [...document.querySelectorAll('.c *, .foot *')]
              .filter(e => { const r = e.getBoundingClientRect(); return r.width && (r.right > 1081 || r.bottom > 1081); })
              .map(e => e.className || e.tagName)""")
            if spill:
                sys.exit(f"Layout spills past the frame: {spill}")
            pg.screenshot(path=str(out))
            b.close()
    finally:
        page.unlink(missing_ok=True)
    if not a.out:
        shutil.copyfile(out, SHARE / "turnout-today.png")
    print(f"Rendered {out.relative_to(ROOT) if not a.out else out} (shares through {n['through']})")


if __name__ == "__main__":
    main()

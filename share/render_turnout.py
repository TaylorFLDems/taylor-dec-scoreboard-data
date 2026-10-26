"""Render the daily turnout graphics from neighborhoods.json.

Two images, each with a dated copy in share/daily/ (today's date, Eastern) and a
stable link:
  county  share/turnout-today.png  Perry and Taylor County, six county areas ranked
  city    share/perry-today.png    Perry, the neighborhood map, leading neighborhoods
1080x1080 for a Facebook or Instagram feed post. Same look as the P13 graphic (render_daily.py).

Shows only what the public neighborhood scoreboard (/2026scoreboard) shows:
whole percentages of Democrats who have voted, for Perry, the county, the six
county areas and the Perry neighborhoods. Percentages only, no counts, no voter data.

Usage:  python share/render_turnout.py [--date YYYY-MM-DD] [--kind city|county --out FILE]   (testing)
"""
import argparse, datetime as dt, html, json, re, shutil, sys
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


def top_rows(areas, limit=10, keep=6):
    """Perry neighborhoods for the city image, best first. Never cut a tie in half:
    take whole groups of equal shares while they fit in `limit` rows, and at least
    the leading `keep` rows' groups. Ties sort by name."""
    ranked = sorted(((k, v) for k, v in areas.items() if isinstance(v, (int, float))), key=lambda r: (-r[1], r[0]))
    out, i = [], 0
    while i < len(ranked):
        j = i
        while j < len(ranked) and ranked[j][1] == ranked[i][1]:
            j += 1
        if len(out) + (j - i) > limit and len(out) >= keep:
            break
        out += ranked[i:j]
        i = j
    return out[:limit]  # only bites if one tie group alone is longer than the list


# Map shading: the neighborhood page's five steps (scoreboard/neighborhoods, Main.dc.html).
SH = ["#C9D7E8", "#93B0D3", "#5A85BC", "#2B5A97", "#0A3161"]
NUM_ON_LIGHT = 2  # steps 0 and 1 are light; their number badges get dark text


def build_city(n, today, perry, file_day, g):
    """Perry image: the share, the neighborhood map shaded like the scoreboard page,
    and the leading neighborhoods. Only the leaders are labeled on the map, with
    letters in rank order (A = top). Oct 26, Trey: the page's 1 to 27 numbers
    confused people on the image (read as counts or ranks)."""
    areas = n.get("areas") or {}
    names = sorted(areas)  # map shapes and their #nums labels are in alphabetical order
    vals = [areas[k] if isinstance(areas[k], (int, float)) else 0 for k in names]
    if len(names) != 27:
        sys.exit(f"Expected the 27 Perry neighborhoods, got {len(names)}; not rendering.")
    step = max(1, -(-max(vals) // 5))
    shade = lambda v: min(4, int(v // step))
    svg = (ASSETS / "perry-map.svg").read_text()
    svg = svg[svg.index("<svg"):]
    for i, v in enumerate(vals):
        a = f'class="area" data-i="{i}"'
        assert svg.count(a) == 1, f"map has no single shape for {names[i]}"
        svg = svg.replace(a, f'{a} fill="{SH[shade(v)]}"')
    rng = lambda lo, hi: f"{lo}%" if lo == hi else f"{lo} to {hi}%"
    leg = ["0%" if step == 1 else f"Under {step}%", rng(step, 2 * step - 1), rng(2 * step, 3 * step - 1),
           rng(3 * step, 4 * step - 1), f"{4 * step}% and up"]
    legend = "".join(f'<span><i style="background:{SH[k]}"></i>{html.escape(t)}</span>' for k, t in enumerate(leg))
    leaders = top_rows(areas, limit=8, keep=5)
    letter = {k: "ABCDEFGH"[j] for j, (k, _) in enumerate(leaders)}
    # Relabel the map: leaders get their letter, every other neighborhood's label goes.
    for i, k in enumerate(names):
        old = re.search(r'<text x="[0-9.]+" y="[0-9.]+">%d</text>' % (i + 1), svg)
        assert old, f"map has no label for {k}"
        svg = svg.replace(old.group(0), old.group(0).replace(f">{i + 1}<", f">{letter[k]}<") if k in letter else "", 1)
    svg = svg.replace('<g id="nums" font-size="14"', '<g id="nums" font-size="17"', 1)
    rows = "".join(
        f'<div class="nb"><b class="badge{" dk" if shade(v) < NUM_ON_LIGHT else ""}" style="background:{SH[shade(v)]}">{letter[k]}</b>'
        f'<span class="nm">{html.escape(k)}</span><span class="v">{v:g}%</span></div>'
        for k, v in leaders)
    delta = f'<div class="delta">{html.escape(g)}</div>' if g else ''

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
.kick{{display:flex;align-items:center;gap:14px;margin-top:44px;font:700 22px Archivo;letter-spacing:.14em;text-transform:uppercase}}
.kick:before{{content:"";width:38px;height:4px;background:#fff}}
.hero{{display:flex;align-items:center;gap:30px;margin-top:14px}}
.big{{font:900 132px/0.9 Archivo;letter-spacing:-.03em}}
.big i{{font-style:normal;font-size:76px;letter-spacing:0;margin-left:2px}}
.lab{{font:800 32px/1.15 Archivo}}
.delta{{display:inline-block;font:800 19px Archivo;letter-spacing:.04em;text-transform:uppercase;background:#B31942;padding:9px 14px;border-radius:999px;margin-top:12px}}
.main{{display:grid;grid-template-columns:520px 1fr;gap:32px;margin-top:26px}}
.map{{position:relative;width:520px;height:531px;border-radius:10px;overflow:hidden;border:2px solid rgba(255,255,255,.85)}}
.map svg{{display:block;width:100%;height:100%}}
.sec{{font:700 19px Archivo;letter-spacing:.14em;text-transform:uppercase;color:rgba(255,255,255,.8)}}
.nb{{display:grid;grid-template-columns:38px 1fr auto;gap:12px;align-items:center;margin-top:14px}}
.badge{{width:38px;height:38px;border-radius:50%;display:grid;place-items:center;font:800 18px Archivo;color:#fff;border:2px solid rgba(255,255,255,.85)}}
.badge.dk{{color:#0A3161}}
.nm{{font:500 21px/1.2 'Libre Franklin';color:#fff}}
.v{{font:800 25px Archivo;text-align:right}}
.leg{{position:absolute;right:12px;top:12px;display:grid;gap:5px;padding:10px 12px;border-radius:8px;background:rgba(255,255,255,.94);font:500 15px 'Libre Franklin';color:#2D2926}}
.leg span{{display:flex;align-items:center;gap:8px}}
.leg i{{width:20px;height:14px;border-radius:3px;border:1px solid rgba(10,49,97,.35)}}
.leg .t{{font:700 12px Archivo;letter-spacing:.12em;text-transform:uppercase;color:#514b45;margin-bottom:2px}}
.note{{margin-top:22px;font:500 18px/1.45 'Libre Franklin';color:rgba(255,255,255,.75);max-width:380px}}
.foot{{position:absolute;left:72px;right:72px;bottom:58px;display:flex;justify-content:space-between;align-items:flex-end}}
.url{{font:800 30px Archivo}}
.url small{{display:block;font:700 18px Archivo;letter-spacing:.12em;text-transform:uppercase;color:rgba(255,255,255,.75);margin-bottom:6px}}
.asof{{font:500 20px 'Libre Franklin';color:rgba(255,255,255,.7);text-align:right}}
.stripe{{position:absolute;left:0;right:0;bottom:0;height:20px;background-image:repeating-linear-gradient(120deg,#061f3e 0,#061f3e 14px,#B31942 14px,#B31942 28px,#fff 28px,#fff 42px)}}
</style></head><body><div class="c">
<div class="top"><img class="logo" src="logo-white.png" alt=""><div class="chip">{html.escape(chip_text(today))}</div></div>
<div class="kick">Perry Neighborhood Scoreboard</div>
<div class="hero"><div class="big">{perry:g}<i>%</i></div><div><div class="lab">of Perry Democrats have voted</div>{delta}</div></div>
<div class="main"><div class="map">{svg}<div class="leg"><span class="t">Share who have voted</span>{legend}</div></div>
<div><div class="sec">Leading neighborhoods</div><div class="rows">{rows}</div>
<p class="note">Letters show where they are on the map. Find all 27 neighborhoods on the scoreboard page.</p></div></div>
</div>
<div class="foot"><div class="url"><small>Find your neighborhood</small>{PAGE}</div>
<div class="asof">State file of {nice(file_day)}</div></div>
<div class="stripe"></div></body></html>"""


def build(n, today, kind="county"):
    perry, county, bk = n.get("perry"), n.get("county"), n.get("buckets") or {}
    if not isinstance(perry, (int, float)) or not isinstance(county, (int, float)):
        sys.exit("neighborhoods.json has no Perry or county share; not rendering.")
    file_day = dt.date.fromisoformat(n.get("file_date") or n["through"])
    hist = n.get("history", [])

    def stat(v, who, g):
        return (f'<div class="st"><div class="big">{v:g}<i>%</i></div>'
                f'<div class="lab">of {who} Democrats have voted</div>'
                + (f'<div class="delta">{html.escape(g)}</div>' if g else '') + '</div>')

    if kind == "city":
        return build_city(n, today, perry, file_day, gain(hist, "perry"))
    rows = sorted(((AREAS[k], bk[k], k == "perry") for k in AREAS if isinstance(bk.get(k), (int, float))),
                  key=lambda r: (-r[1], r[0]))
    kick, sec = "Taylor Democrats are voting", "Across the county"
    stats = f'<div class="stats">{stat(perry, "Perry", gain(hist, "perry"))}{stat(county, "Taylor County", gain(hist, "county"))}</div>'
    if not rows:
        sys.exit("neighborhoods.json has no areas; not rendering.")
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
<div class="kick">{kick}</div>
{stats}
<div class="sec">{sec}</div>
<div class="rows">{bars}</div>
</div>
<div class="foot"><div class="url"><small>Find your neighborhood</small>{PAGE}</div>
<div class="asof">State file of {nice(file_day)}</div></div>
<div class="stripe"></div></body></html>"""


# kind -> (stable file, dated file prefix)
KINDS = {"county": ("turnout-today.png", "turnout"), "city": ("perry-today.png", "perry")}


def render(n, today, kind, out):
    page = ASSETS / f"_render_{kind}.html"
    page.write_text(build(n, today, kind))
    from playwright.sync_api import sync_playwright
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            pg = b.new_page(viewport={"width": 1080, "height": 1080})
            pg.goto(page.as_uri())
            pg.evaluate("document.fonts.ready")
            # Refuse to write an image whose text spills out of the frame or runs
            # into the footer.
            bad = pg.evaluate("""() => {
              const out = [...document.querySelectorAll('.c *, .foot *')]
                .filter(e => !e.closest('svg'))  // map shapes run past the map frame on purpose; it clips them
                .filter(e => { const r = e.getBoundingClientRect(); return r.width && (r.right > 1081 || r.bottom > 1081); })
                .map(e => e.className || e.tagName);
              const foot = document.querySelector('.foot');
              for (const sel of ['.rows', '.leg', '.map']) { const e = document.querySelector(sel);
                if (e && foot && e.getBoundingClientRect().bottom > foot.getBoundingClientRect().top - 24) out.push(sel + ' overlaps footer'); }
              return out; }""")
            if bad:
                sys.exit(f"{kind}: layout problem: {bad}")
            pg.screenshot(path=str(out))
            b.close()
    finally:
        page.unlink(missing_ok=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="render as if today were this date (testing)")
    ap.add_argument("--kind", choices=sorted(KINDS), help="render only this image (testing)")
    ap.add_argument("--out", help="write only this file (testing; needs --kind)")
    a = ap.parse_args()
    if a.out and not a.kind:
        ap.error("--out needs --kind")
    today = dt.date.fromisoformat(a.date) if a.date else dt.datetime.now(ZoneInfo("America/New_York")).date()
    if today > EDAY:
        print("After Election Day; nothing to render.")
        return
    n = json.loads((ROOT / "neighborhoods.json").read_text())
    for kind in ([a.kind] if a.kind else list(KINDS)):
        stable, prefix = KINDS[kind]
        out = Path(a.out) if a.out else SHARE / "daily" / f"{prefix}-{today.isoformat()}.png"
        render(n, today, kind, out)
        if not a.out:
            shutil.copyfile(out, SHARE / stable)
        print(f"Rendered {out if a.out else out.relative_to(ROOT)} (shares through {n['through']})")


if __name__ == "__main__":
    main()

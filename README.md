# taylor-dec-scoreboard-data

Public data behind the Taylor County DEC's 2026 general election dashboards on
taylorfldems.org (Solidarity Tech custom HTML blocks).

**Aggregate counts only.** Nothing in this repo identifies a voter. Party and
precinct totals are derived from public state statistics and, for `p13.json`,
from the confidential DS-DE 145/147 files, which never leave the DEC's private
repo. Only the totals are published here.

| File | Written by | What |
|---|---|---|
| `latest.json` | GitHub Action, 3x daily | County party totals from the FL DOS PublicStats page (election 49894) plus a snapshot of the county Turnout Quick View feed (election 85) |
| `p13.json` | DEC scheduled task, daily | Democratic ballots cast by precinct for 13, 14, 1, 2, 7, plus county chase counts |

Raw URLs (CORS-open, read by the blocks):

- https://raw.githubusercontent.com/TaylorFLDems/taylor-dec-scoreboard-data/main/latest.json
- https://raw.githubusercontent.com/TaylorFLDems/taylor-dec-scoreboard-data/main/p13.json

## Things that will bite

- Schedules are best-effort and UTC. The third cron exists for after DST ends Nov 1.
- The state file covers through the **previous day**; rows are stored by snapshot date.
- The run goes red (and GitHub emails) if the page's election ID changes, a
  Taylor row disappears, parties don't sum to total, or a cumulative count drops.
- Carried over from `tbluegator/taylor-dec-ev-data` (2026 primary). See
  `claude/taylor-ev-tracker-migration.md` in the Claude project for the history.

## Daily P13 graphic

`share/render_daily.py` turns `p13.json` into a 1080×1080 post image. The
"Daily P13 graphic" workflow runs it whenever `p13.json` changes and once each
morning (so the countdown advances on quiet days), then commits:

- `share/p13-today.png`: always today's image. Stable link:
  https://raw.githubusercontent.com/TaylorFLDems/taylor-dec-scoreboard-data/main/share/p13-today.png
- `share/daily/p13-YYYY-MM-DD.png`: one per day, for the record.

It shows only what the public scoreboard shows (P13 ballots, the 600 goal,
milestones, countdown). While the count is 0 it leads with the countdown
instead. Stops after Nov 3. Test a date locally with
`python share/render_daily.py --date 2026-10-27 --out test.png`.

`share/p13-scoreboard-share.png` is the separate, fixed link-preview image for
the page; its source is in the private ops repo (`scoreboard/share/`).

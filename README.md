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

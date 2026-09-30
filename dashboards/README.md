# Power BI dashboard — not built yet (M7 human deliverable)

**Status (2026-09-30): nothing to open here yet.** There is no `epra.pbix`, no
`exports/*.csv`, and no dashboard screenshots in the repository. The dashboard
depends on M6 (strategy results) and M7 (exports), neither of which is
implemented.

The `.pbix` is a human deliverable (AGENTS.md §2 item 5). At M7 the agent
prepares the `exports/` CSVs (DM-070) and completes the build instructions in
this file per SPEC-06 §4; the human then builds the dashboard:

- Data sources: the six CSVs in `exports/`, linked by relative paths
  (documented here at M7). Power BI reads ONLY from `exports/`, never from
  DuckDB directly (DM-070).
- Relationships and date table per SPEC-06 §4.
- Four pages: Headline / Market / Strategies / Risk (RP-401…404), each with one
  German subtitle sentence (RP-405).
- Screenshots of all four pages are saved as `docs/assets/dashboard_p1.png` …
  `dashboard_p4.png` and embedded in the README (RP-406). These files do not
  exist yet.
- `dashboards/epra.pbix` is committed once built (SPEC-06 §4).

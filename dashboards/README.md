# Power BI dashboard — built at M7 (human task)

The `.pbix` is a human deliverable (AGENTS.md §2 item 5). Agents prepare
`exports/` CSVs (DM-070) and, at M7, complete these build instructions per
SPEC-06 §4: data sources = the six CSVs in `exports/` via relative paths;
relationships per RP-4xx; four pages (Headline / Market / Strategies / Risk)
with one German subtitle sentence each (RP-405); screenshots to
`docs/assets/dashboard_p1..p4.png` (RP-406).

Power BI reads ONLY from `exports/` — never from DuckDB directly (DM-070).

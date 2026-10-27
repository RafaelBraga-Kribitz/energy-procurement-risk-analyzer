# ADR-022: Power BI as a PBIP text project, plus a static HTML twin
Date: 2026-10-27  |  Status: accepted

Amends: SPEC-06 §1 and RP-406 (`dashboards/epra.pbix`), Charter DL-6 (same
file name). Related: ADR-018 (fixture banner), ADR-020 §4 (build kit, page 5),
ADR-021 (colours), Charter O-4 (no hosted backend).

## Context

SPEC-06 §4 specifies the Power BI report precisely, and ADR-020 shipped a build
kit for it (`dashboards/README.md`, `measures.dax`, `theme.json`). The report
itself was still missing, because a `.pbix` is a binary that only Power BI
Desktop writes: an agent cannot author, diff, review or test it, and every
change would be invisible in a pull request.

Power BI Desktop also saves a report as a **Power BI Project (PBIP)**: the
semantic model as TMDL text and the report in the enhanced report format
(PBIR) as one JSON file per page and visual, each validated by a published
JSON schema. Desktop opens a PBIP directly and saves it back to a `.pbix` on
demand (*File → Save as*). PBIR is the default format of current Desktop
releases; older releases need the preview options *Power BI Project (.pbip)
save option*, *Store semantic model using TMDL format* and *Store reports
using enhanced metadata format (PBIR)*.

The owner also asked (27 Oct 2026) for a version of the same pages that opens
anywhere without Power BI: a reviewer without a Windows machine should still
see the dashboard.

## Decision

1. **The Power BI report is a PBIP in text form:** `dashboards/EPRA.pbip`,
   `dashboards/EPRA.SemanticModel/` (TMDL) and `dashboards/EPRA.Report/`
   (PBIR). It is the text-form equivalent of `dashboards/epra.pbix`. Desktop
   writes the `.pbix` from it on demand. The `.pbix` is not committed, because
   it would be a second, unreviewable copy of the same report.
   - The model loads `exports/*.csv` (DM-070) through one Power Query helper,
     `LoadExport`.
   - The folder is one text parameter, `ExportsPath`.
   - `DimMonth` is a marked daily date table. Monthly facts join it on the
     first day of their month.
   - Every DAX measure of the build kit is ported under its original name,
     with a description, a format string and a display folder.
   - `dashboards/measures.dax` stays as the readable mirror. A test keeps the
     two identical.
2. **One page registry, `epra.report.dashboard_pages`, defines the pages**
   (SPEC-06 §4 names, English headings, the German subtitles of RP-405, and
   the footer tags). The PBIP and the HTML twin both follow it. Tests check
   the PBIP and `dashboards/README.md` against it.
3. **The report cannot drift from its model.**
   - `tests/unit/test_pbip_integrity.py` checks the following:
     - every field that a visual, visual filter or formatting rule references
       exists in the TMDL;
     - relationships join existing columns toward a dimension;
     - each page has its title, German subtitle and footer;
     - every data visual has a title and alt text, and tab order is unique;
     - the registered theme is byte-identical to `dashboards/theme.json` and
       keeps the RP-704 strategy colours.
   - `scripts/validate_pbip.py` validates every PBIR/PBIP JSON file against
     the Microsoft schema that the file declares. It uses an offline copy of
     the schema tree (`make pbip-validate PBIP_SCHEMA_DIR=…`). Without a schema
     directory it skips, so CI needs no network.
4. **Static HTML twin.**
   - `make dashboard-html` (`epra.report.html_dashboard`, also part of
     `make all`) reads the same export CSVs and writes one self-contained
     file, `dashboards/html/index.html`.
   - The file holds the five pages as accessible tabs, inline-SVG charts drawn
     by vanilla JavaScript from embedded JSON, a data table under every chart,
     and light and dark design-system tokens (ADR-021).
   - There is no CDN, no web font and no network request.
   - **This is the owner's decision. It is a static, serverless file, not an
     app.** It has no backend, no server and no hosting, so Charter O-4 (no
     FastAPI/Streamlit/hosted backend) holds.
   - The build is deterministic: there is no build timestamp, and two builds
     on the same exports are byte-identical (A-4).
   - Headline cards read `ssot.csv` only (A-6). Chart values are aggregated
     from the same marts, and a test reconciles them with the SSOT.
5. **Fixture safety (ADR-018).**
   - On fixture exports both deliverables show the FIXTURE banner: the
     `Data Banner` measure in Power BI and a sticky banner in HTML.
   - `dashboards/html/` is git-ignored, so a fixture build cannot be
     committed by accident. After `make real-run` the owner commits it on
     purpose (`git add -f`).
   - No fixture screenshot is committed.

## Consequences

- **What stays human (AGENTS.md §2 item 5).** Nobody has opened this PBIP in
  Power BI Desktop yet. A person still has to:
  1. open it in Desktop;
  2. set `ExportsPath` and refresh;
  3. check the cards against the SSOT;
  4. save the `.pbix` if wanted;
  5. take the RP-406 screenshots.

  The steps are in `dashboards/README.md` §0. The PBIR files validate against
  Microsoft's schemas, but only Desktop can prove they load.
- Desktop rewrites some files when it saves (for example, it adds a base theme
  and `.platform` metadata). Such diffs are expected, and the integrity test
  still guards the references.
- Small-multiple histograms on the Risk page exist in the HTML twin (SPEC-06
  RP-404). In the PBIP, the histogram compares full spot and fixed annual
  through a series. Adding small multiples is a one-drag step in Desktop,
  listed in the checklist, because their PBIR role binding could not be
  verified without Desktop.
- The data-quality combo chart keeps SPEC-06's line-plus-column layout, which
  has two value axes. The HTML twin draws two aligned charts instead, because
  dual axes misread easily.
- The repository gains about 60 small JSON/TMDL files, two tests, one
  generator module with its CSS/JS assets, and two Make targets.

## Spec deviations (list REQ IDs affected, or "none")

- SPEC-06 §1 / RP-406 and Charter DL-6: `dashboards/epra.pbix` is delivered as
  the PBIP text project `dashboards/EPRA.pbip` (+ `EPRA.SemanticModel/`,
  `EPRA.Report/`); a `.pbix` is saved from it by Desktop when needed. The
  screenshots of RP-406 remain a human step after the real-data run.
- RP-404: in the PBIP the histogram shows S1 vs S3 as series rather than small
  multiples, until the small multiples are added in Desktop (see above).
- Output contracts of all existing artifacts are unchanged.

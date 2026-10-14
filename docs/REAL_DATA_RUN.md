# Real-data run — what is needed and how to run it

Everything in this repository was built and gated on the synthetic CI fixture
(ADR-018). This page is the hand-over for the first run on real data. One
command does the whole run; the rest of the page says what it needs, what to
check, and what to commit.

## 1. What is needed

| Item | Why | How to provide it |
|---|---|---|
| **ENTSO-E API token** | AT and DE-LU day-ahead prices, AT load and generation (SPEC-01) | Register at <https://transparency.entsoe.eu>, request REST API access (email to `transparency@entsoe.eu`, subject "Restful API access"), then generate the token under *My Account Settings*. Approval can take a few working days. |
| **Network access** to `web-api.tp.entsoe.eu` and `dataset.api.hub.geosphere.at` | ENTSO-E and GeoSphere APIs (GeoSphere needs no account) | Automatic on a normal machine; see §2b for a cloud session |
| *(optional)* ÖSPI months after 2026-08 | `data/manual/oespi_monthly.csv` ends 2026-08 | Transcribe new months with the double-entry procedure (`make oespi-reconcile`, ING-101). Without them the simulator carries the last value forward for the lock window (ADR-019) and says so. |

The token is a secret (A-7): only an environment variable `ENTSOE_API_TOKEN`
or a local `.env` file (gitignored). Never paste it in a chat, an issue or a
commit.

## 2a. Run on your own machine

```bash
git pull                       # main with M4-M7
cp .env.example .env           # put ENTSOE_API_TOKEN=... in .env
make setup
make real-run
```

`make real-run` does, in order:

1. checks that the token is set;
2. `clean-fixture` — deletes `data/raw`, `data/processed` and the warehouse **only
   if** the fixture marker `data/raw/_SYNTHETIC_FIXTURE.txt` exists (real data is
   never deleted; `data/manual` is never touched);
3. `backfill` (ENTSO-E 2019 → last complete month), `geosphere`, `calendar`;
4. `validate-ingest` — ingestion gates, report in `reports/ingestion/`;
5. `all` — dbt → load profile → analytics (AN-304 gate) → simulator (ST-602
   gate) → SSOT → exports → reports → README blocks, GV-303 number check;
6. `freshness` (data < 40 days old) and `warehouse` (full dbt build report).

Any gate failure stops the run with a non-zero exit. Expect roughly 20–60 minutes,
mostly the ENTSO-E backfill (it is polite to the API and pages its responses).

## 2b. Run it in a Claude Code cloud session instead

Two environment settings are needed (cloud environment menu in the session's
title bar → *Edit*), then start a **new** session and ask for the real-data run:

- **Secret:** add `ENTSOE_API_TOKEN` under *Network secrets* (or as an environment
  variable). The session reads only that variable name.
- **Network access:** add `web-api.tp.entsoe.eu` and `dataset.api.hub.geosphere.at`
  under *Allowed domains* (keep *Allow package managers* ticked). The build
  session's policy blocked both hosts. Steps:
  <https://code.claude.com/docs/en/cloud-environments#network-access>

## 3. What to check after the run

- [ ] `reports/ingestion/validation_<date>.md` — all ING gates PASS; note any
      investigation in `LIMITATIONS.md` §6 (R-8). Do not widen a gate without an ADR.
- [ ] `reports/analytics/a3_regime_stats.md` — **AN-304: PASS** on real data.
- [ ] Simulator log — **ST-602 (a)(b)(c): PASS**. If (a) fails, the ÖSPI
      translation is broken: stop and debug, never rationalize (SPEC-05 §9).
- [ ] `reports/NUMERIC_SSOT.md` has **no** FIXTURE banner; the README answer and
      results blocks now show euro figures; `make ssot-check` passes.
- [ ] Read `reports/EXEC_SUMMARY.md` §5 (recommendation) and edit the wording
      if you want; numbers must stay SSOT values (A-6).
- [ ] Look at every chart in `reports/` for clipped labels or odd titles.

## 4. What to commit (one PR, "data: first real-data run")

```bash
git add reports/ README.md LIMITATIONS.md docs/BUILD_LOG.md
git status        # data/, exports/*.csv and *.duckdb stay untracked (gitignored)
```

Add a `docs/BUILD_LOG.md` entry with the gate outputs. The golden tests do not
change: they use closed-form inputs, not market data.

## 5. After the real run

- Build the Power BI report from `exports/` (`dashboards/README.md`), save
  `dashboards/epra.pbix` and the screenshots `docs/assets/dashboard_p1…p5.png`.
- Set the repo secret `ENTSOE_API_TOKEN` (GitHub → Settings → Secrets → Actions)
  so the monthly refresh (`.github/workflows/refresh.yml`) runs on its own.
- In `braga-portfolio-docs`, move EPRA to `status: Complete` / `incomplete:
  false` once the `.pbix` and screenshots are committed, and update the README
  status line to match.
- Optional: Azure deployment (`docs/AZURE_DEPLOYMENT.md`).

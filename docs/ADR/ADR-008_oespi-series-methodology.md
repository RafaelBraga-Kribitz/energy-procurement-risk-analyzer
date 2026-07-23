# ADR-008: ÖSPI series methodology — one pinned source, pending human confirmation (ING-102)

**Status:** proposed — pending human confirmation at T2.05 transcription (D-01/D-04)
**Date:** 2026-07-23
**Deciders:** M2 auxiliary-data ingestion (EPRA-03), plan 03-05
**Related:** SPEC-01 §10 (ING-100..104), 03-CONTEXT.md D-01/D-02/D-04, research
Pitfall 2 (splicing the two ÖSPI methodologies), `LIMITATIONS.md` §2

## Context

The Austrian Energy Agency (AEA) publishes the ÖSPI (Österreichischer
Strompreisindex) monthly Base + Peak values (index base 2006 = 100) with no
machine API — only PDF/Excel "Monatswerte" downloads. There is no CSV/API, so
the values must be hand-transcribed into `data/manual/oespi_monthly.csv`
(double-entry, ING-101, `scripts/oespi_reconcile.py`).

ING-102 warns explicitly that the AEA has revised the ÖSPI methodology over
time and that **two page families exist simultaneously**:

1. **The continuously-published series** at
   `https://www.energyagency.at/fakten/strompreisindex` (labeled "alte
   Methode" / old method on the page itself, but still the actively-updated,
   currently-published series — the most recently fetched value at research
   time was for a 2026 month). This page has published **both Base and Peak**
   monthly values since a **September 2018** methodology refinement — meaning
   it plausibly covers the entire 2019→latest window as ONE consistent series
   with Peak available throughout.
2. **"Indices 2.0"** at `https://www.energyagency.at/fakten/strompreisindizes`
   — a newer family of 12 indices (monthly/quarterly/yearly ×
   total/base/peak/off-peak) launched in **December 2023 as a supplement, not
   a replacement**. It does NOT cover 2019–2023.

Splicing early years (2019–2023) from series (1) with later months (Dec
2023+) from series (2) would introduce a level/definitional discontinuity
exactly at the 2022-crisis-adjacent boundary — corrupting the ING-103
crisis-visibility gate ("2022 peak ≥ 3× 2019 mean") in a way that would be
hard to detect after the fact, since both halves individually look plausible
(research Pitfall 2). ING-102 requires this choice to be pinned in an ADR
before any transcription happens.

**This ADR does not itself transcribe any values** — it only pins which page
is the sole source for the human transcription step (T2.05). `load_oespi`
(`src/epra/ingest/oespi.py`) enforces the resulting single-series invariant
in code: it asserts `source_url` is constant across every row of the
committed CSV and raises rather than silently accepting a mid-series change.

## Decision

Pin series (1) — the continuously-published AEA *strompreisindex* page,
`https://www.energyagency.at/fakten/strompreisindex` — as the **sole**
transcription source for the entire 2019-01 → latest window. T2.05's human
double-entry transcription reads only from this one page/PDF for the whole
series; "Indices 2.0" is explicitly out of scope for 2019→latest and must
never be spliced in.

**This pick is a strong, research-backed candidate — not yet a locked
fact.** Per D-01/D-04, the human transcriber at T2.05 must confirm, at
transcription time, that:

- the page still (as of transcription) publishes both Base and Peak for
  every month 2019-01→latest with no sub-period gap, and
- no further AEA methodology revision has occurred since this research was
  conducted (2026-07-22) that would change which page is "the" continuously
  published series.

If either check fails at T2.05, the transcriber records the actual
discrepancy and this ADR is revised (or a follow-up ADR is written) — never
silently substituted.

## Consequences

- `load_oespi` asserts a single constant `source_url` value across every row
  of `data/manual/oespi_monthly.csv` (D-01) — a mid-series change raises
  `ContractError` naming the differing months, rather than silently
  accepting a splice.
- If Peak values turn out to be unavailable or discontinuous for part of the
  window (contradicting this research's Sept-2018-Base+Peak finding), the
  ING-104 base-only fallback applies: `load_oespi` sets
  `frame.attrs["peak_available"] = False` for the whole series rather than
  raising, and `gate_ing_103`'s positivity check skips the (all-NaN) Peak
  column in that mode. Recorded in `LIMITATIONS.md` §2.
- `gate_ing_103`'s crisis-visibility check (2022 max Base ≥ 3× 2019 mean
  Base) is only meaningful because this ADR keeps the pre-crisis (2019) and
  crisis (2022) values on the same methodology — a spliced series would make
  that comparison meaningless even if it happened to pass numerically.
- The real, human-transcribed `data/manual/oespi_monthly.csv` is the 03-06
  human checkpoint (D-05/D-06) — this plan's `load_oespi`/`gate_ing_103` ship
  and are unit-tested against a committed synthetic CSV
  (`tests/fixtures/oespi/synthetic_oespi_monthly.csv`) that exercises every
  ING-103 fail case; the absence of the real CSV is not a ship blocker here.
- If T2.05 confirmation contradicts this ADR's pick (e.g. the page's
  publication history has a gap this research didn't surface), this ADR's
  Status moves to a revision, not a silent code change.

## Spec deviations

None. ING-102 requires "record the choice + source URLs in an ADR" before
transcription — this ADR satisfies that requirement in-phase (per D-01's
"agent finds/verifies the source URL and drafts the methodology ADR first
(T2.04/03-05); the human confirms the source, then transcribes (T2.05)"
sequencing), with the human-confirmation step explicitly deferred to T2.05
rather than assumed.

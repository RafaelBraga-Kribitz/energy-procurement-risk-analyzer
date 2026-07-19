"""Ingestion validation gates — ``make validate-ingest`` (M1/M2).

Not yet implemented. Binding contract: SPEC-01 §8 (ENTSO-E), §9 (GeoSphere),
§10 (ÖSPI). Results are written to ``reports/ingestion/validation_<date>.md``.

Gate summary (fail-fast per EN-061 — a failed gate raises, never warns):

- ING-080 hour coverage per zone-year (≤ 24 missing; DST 23/25 check)
- ING-081 price bounds −500..5000 EUR/MWh (out of range ⇒ investigate, not clip)
- ING-082 annual mean plausibility table (per-year ranges; widening needs ADR)
- ING-083 negative prices must exist in 2023/2024/2025 (else parser bug)
- ING-084 load plausibility 3000-13000 MW hourly, 6000-9000 MW annual mean
- ING-085 price↔load join coverage ≥ 99.5% per year
- ING-094 GeoSphere coverage/range/seasonal means
- ING-101/103 ÖSPI reconciliation + series gates

A-2 applies verbatim: on failure, investigate the pipeline — never adjust data
to pass, never widen a gate without an ADR.

Implements (when built): ING-080..085, ING-094, ING-103.
"""

from __future__ import annotations

from collections.abc import Sequence

from epra.common.config import Settings

_MSG = "M1 not implemented yet — build per SPEC-01 §§8-11 (see module docstring)"


def run_gates(settings: Settings) -> None:
    """Run all applicable gates; raise on first hard failure (EN-061)."""
    raise NotImplementedError(_MSG)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: ``python -m epra.ingest.validate``."""
    raise NotImplementedError(_MSG)


if __name__ == "__main__":
    raise SystemExit(main())

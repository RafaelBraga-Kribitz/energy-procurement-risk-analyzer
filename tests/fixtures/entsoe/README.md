# ENTSO-E test fixtures

Committed XML samples for the ENTSO-E parser unit tests
(`tests/unit/test_entsoe_parse.py`, `tests/unit/test_aggregate_hourly.py`,
ING-070, T1.03a). All files are **synthetic** — hand-crafted to match the
Appendix A field paths of `docs/SPEC-01_data_ingestion.md` exactly (element
names, namespaces, `resolution`/`curveType`/currency/unit fields) rather than
truncated real API pulls, so no ENTSO-E account or token is needed to
regenerate or extend them. Every file is a few KB (well under the ING-070
200-row cap) so CI never needs network access (EN-070).

No API tokens or secrets appear in any fixture (A-7).

## File inventory

| File | Document type | REQ coverage |
|------|----------------|--------------|
| `prices_pt60m_at.xml` | `Publication_MarketDocument` (A44, AT) | ING-050 (EUR/MWH assertion), ING-060 (resolution=PT60M declared) |
| `prices_pt15m_at.xml` | `Publication_MarketDocument` (A44, AT) | ING-060 (resolution=PT15M declared, post-SDAC) |
| `prices_a03_forward_fill.xml` | `Publication_MarketDocument`, `curveType=A03` | ING-063 (forward-fill within period; 2 positions omitted, 2 filled) |
| `load_at.xml` | `GL_MarketDocument` (A65, AT actual load) | ING-032 (load contract), ING-060 (PT15M) |
| `gen_at.xml` | `GL_MarketDocument` (A75, AT generation per type) | ING-032 (long format, PSR type/name, aggregated vs consumption kind) |
| `acknowledgement.xml` | `Acknowledgement_MarketDocument` | ING-063 note / Appendix A "no data" handling -> `NoDataError` |
| `dst_spring.xml` | `Publication_MarketDocument`, 23 hourly points | ING-031/ING-005 (UTC persistence across the Europe/Vienna spring-forward transition, 2024-03-31) |
| `dst_fall.xml` | `Publication_MarketDocument`, 25 hourly points | ING-031/ING-005 (UTC persistence across the Europe/Vienna fall-back transition, 2024-10-27) |

Populate additional fixtures only as hand-crafted Appendix-A-shaped XML;
do not commit anything resembling a real API response body without
scrubbing tokens/identifiers first (none of these files were derived from a
live pull).

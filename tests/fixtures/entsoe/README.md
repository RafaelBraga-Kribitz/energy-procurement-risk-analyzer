# ENTSO-E test fixtures

Committed XML/parquet samples for `tests/test_raw_contracts.py` and the
ENTSO-E parser unit tests (ING-070, T1.03a). Expected coverage, each file
<= 200 rows and generated once from real ENTSO-E pulls so CI never needs
network access:

- PT60M day-ahead prices (AT and DE-LU)
- PT15M day-ahead prices (post SDAC 15-min switch)
- curveType A03 (forward-fill within period, ING-063)
- a DST transition day (last Sunday of March / October, ING-080)
- AT actual load (PT15M)
- AT generation per type, long format (ING-032)
- an `Acknowledgement_MarketDocument` (no-data) response

Populate this directory when implementing the fetch/parse plans; do not
commit synthetic data that isn't a fixture-worthy sample of a real response.

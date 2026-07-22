"""Ingest exception hierarchy — actionable failures for transport, auth, contract,
and validation-gate errors.

`epra.ingest` fails fast and loud (AGENTS A-1, A-2; CONVENTIONS "Error Handling"):
a retryable HTTP hiccup, a fatal auth/config error, an unexpected raw-parquet
shape, an absent request result, and a failed post-ingest gate are distinct
failure modes and get distinct exception types so callers (CLI `main()`,
`validate.run_gates()`, tests) can catch precisely instead of bare `Exception`.
Every subclass carries the concrete evidence (gate id, HTTP status, column
names) in its message — never a bare "something went wrong".

Implements: ING-006 (retry/non-retry HTTP error split), ING-008 (no secrets in
error text), ING-070 (contract violations), ING-080..085 (validation gates).
"""

from __future__ import annotations


class IngestError(Exception):
    """Base class for all `epra.ingest` failures.

    Never raised directly — always one of the subclasses below. Catching
    `IngestError` lets callers handle "any ingestion problem" without also
    swallowing unrelated bugs (`ValueError`, `KeyError`, ...) from elsewhere.
    """


class IngestAuthError(IngestError):
    """Authentication/authorization failed for an external source.

    Raised for missing/invalid tokens (ING-021) or HTTP 401/403 responses
    (ING-006 — never retried). The message must name the source and the
    corrective action; it must NEVER include the token value itself (A-7).
    """

    def __init__(self, source: str, detail: str) -> None:
        self.source = source
        self.detail = detail
        super().__init__(f"auth failed for source={source}: {detail}")


class IngestTransportError(IngestError):
    """Non-recoverable HTTP/network failure fetching from an external source.

    Raised after `tenacity` retries are exhausted (ING-006 `stop_after_attempt`)
    or immediately for a non-retryable 400 response. Carries the HTTP status
    code (if any) so the caller can distinguish "server is down" from
    "we sent a malformed request".
    """

    def __init__(self, source: str, detail: str, status_code: int | None = None) -> None:
        self.source = source
        self.detail = detail
        self.status_code = status_code
        status_part = f" status={status_code}" if status_code is not None else ""
        super().__init__(f"transport error for source={source}{status_part}: {detail}")


class ContractError(IngestError):
    """Raw or intermediate data does not match its documented contract.

    Raised when parsed data violates SPEC-01 §7 (column names/dtypes, ING-070)
    or an XML response fails an assertion the spec requires (e.g. currency !=
    EUR, unit != MWH — ING-050). The message states the expected vs. actual
    shape/value so the failure is diagnosable without re-running the parser.
    """

    def __init__(self, dataset: str, expected: str, actual: str) -> None:
        self.dataset = dataset
        self.expected = expected
        self.actual = actual
        super().__init__(f"contract violation in {dataset}: expected {expected}, got {actual}")


class GateFailure(IngestError):
    """A post-ingest validation gate (ING-080..085) failed.

    Raised by `validate.run_gates()` on the first hard gate failure
    (EN-061 — never warn-and-continue past a failed gate, never widen a gate
    without an ADR, A-2). Carries the gate id and its summary so the failure
    is traceable straight to the SPEC-01 §8 table row and the markdown
    report written to `reports/ingestion/`.
    """

    def __init__(self, gate_id: str, summary: str) -> None:
        self.gate_id = gate_id
        self.summary = summary
        super().__init__(f"validation gate {gate_id} failed: {summary}")


class DiscoveryError(IngestError):
    """Resource discovery found no candidate matching its selection rule.

    Raised by one-time discovery steps (e.g. `geosphere.discover_station`,
    ING-091) when nothing in the source's metadata matches the required
    selection criteria. The message must name every candidate that WAS
    available so the failure feeds directly into the resulting ADR or human
    checkpoint instead of a bare "not found".
    """

    def __init__(self, source: str, detail: str) -> None:
        self.source = source
        self.detail = detail
        super().__init__(f"discovery failed for source={source}: {detail}")


class NoDataError(IngestError):
    """An external source returned no data for a requested window.

    Distinguishes "no data because the window is in the future" (expected,
    not a failure) from "no data for a past window" (a real problem — see
    SPEC-01 Appendix A `Acknowledgement_MarketDocument` handling). Callers
    decide the correct response based on the window; this exception only
    reports what happened.
    """

    def __init__(self, source: str, window: str, reason: str) -> None:
        self.source = source
        self.window = window
        self.reason = reason
        super().__init__(f"no data from source={source} for window={window}: {reason}")

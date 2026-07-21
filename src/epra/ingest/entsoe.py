"""ENTSO-E ingestion — AT/DE-LU day-ahead prices, AT load, AT generation (M1).

Appendix-A XML parsers (``parse_publication_xml``, ``parse_gl_xml``),
``infer_resolution``, ``hourly_mean``, ``PSR_NAMES``, ``iter_chunks``, and the
full orchestration layer (``ingest_dataset``, ``backfill``,
``ingest_incremental``, ``latest_complete_month``) are implemented per
ADR-003 (``EntsoeRawClient`` transport + own first-party parsers, never
``EntsoePandasClient``). The CLI entrypoint (``main``) is still a
``NotImplementedError`` stub — built in the remainder of plan 02-05.

Key points:

- Wrap ``entsoe-py`` (``EntsoeRawClient``) — never call ``EntsoePandasClient``
  from analytics (ING-022, ADR-003).
- Request in <= 90-day chunks (ING-030); pass tz='Europe/Vienna' timestamps to
  entsoe-py but convert returned indexes to UTC IMMEDIATELY (ING-031, T-4) —
  the parsers below do this at the parse boundary via
  ``epra.common.timeutil.to_utc``.
- One parquet file per dataset per calendar month, atomic overwrite
  (ING-003): ``data/raw/<dataset>/<YYYY>/<dataset>_<YYYY-MM>.parquet``.
- Output columns must byte-match SPEC-01 §7 contracts (tested by ING-070).
- Persist ``resolution`` per row; PT15M stays PT15M in raw — hourly
  aggregation (``hourly_mean``, mean of quarters NOT sum — T-2) happens in
  dbt staging for the canonical analytical grain, ING-061/062.
- Retry/backoff per ING-006; >= 0.5 s between requests (ING-007); response
  cache per ING-009; request log line per ING-008 (token never logged, A-7).
  All implemented in ``_fetch.fetch_entsoe``, called from ``ingest_dataset``.
- ``latest_complete_month`` follows ADR-005 (adopts SG-02): the min of AT's
  and DE-LU's own latest complete price month, so downstream spread analysis
  never assumes a month either zone is still missing.

Implements: ING-001, ING-030, ING-031, ING-032, ING-040, ING-041, ING-042,
ING-050, ING-060, ING-061, ING-062, ING-063.
Implements (when built): ING-002, ING-010, ING-070.
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from calendar import monthrange
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Literal, cast

import pandas as pd

from epra.common.config import REPO_ROOT, Settings
from epra.common.timeutil import VIENNA, iter_month_starts, month_start, next_month, to_utc
from epra.ingest._fetch import (
    DocumentType,
    EntsoeQuery,
    TransportFn,
    _cache_request_url,
    fetch_entsoe,
)
from epra.ingest._io import request_hash, write_month
from epra.ingest.exceptions import ContractError, NoDataError

logger = logging.getLogger(__name__)

_MSG = "M1 not implemented yet — build per SPEC-01 §§2-8 (see module docstring)"

#: EIC domain code -> zone code (SPEC-01 §3 / Appendix A). Unknown EIC codes
#: pass through unchanged so a new domain is visible for debugging rather
#: than silently dropped.
_EIC_TO_ZONE: dict[str, str] = {
    "10YAT-APG------L": "AT",
    "10Y1001A1001A82H": "DE_LU",
}

#: PT resolution -> minutes-per-point (SPEC-01 §6 / ING-060).
_RESOLUTION_MINUTES: dict[str, int] = {"PT60M": 60, "PT30M": 30, "PT15M": 15}

#: Appendix B — PSR type code -> name. Unknown codes get
#: ``psr_name = 'UNKNOWN(<code>)'`` (never dropped, WARN logged).
PSR_NAMES: dict[str, str] = {
    "B01": "Biomass",
    "B02": "Fossil Brown coal/Lignite",
    "B03": "Fossil Coal-derived gas",
    "B04": "Fossil Gas",
    "B05": "Fossil Hard coal",
    "B06": "Fossil Oil",
    "B09": "Geothermal",
    "B10": "Hydro Pumped Storage",
    "B11": "Hydro Run-of-river and poundage",
    "B12": "Hydro Water Reservoir",
    "B13": "Marine",
    "B14": "Nuclear",
    "B15": "Other renewable",
    "B16": "Solar",
    "B17": "Waste",
    "B18": "Wind Offshore",
    "B19": "Wind Onshore",
    "B20": "Other",
}


# --------------------------------------------------------------------------
# XML helpers — namespace-agnostic (ENTSO-E documents use a single default
# namespace per document type; the exact URN has changed across schema
# versions, so match on local tag name via ElementTree's `{*}tag` wildcard).
# --------------------------------------------------------------------------


def _local_name(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def _child(elem: ET.Element, tag: str) -> ET.Element | None:
    return elem.find(f"{{*}}{tag}")


def _children(elem: ET.Element, tag: str) -> list[ET.Element]:
    return elem.findall(f"{{*}}{tag}")


def _text(elem: ET.Element | None) -> str | None:
    return elem.text.strip() if elem is not None and elem.text else None


def _reject_doctype(xml: str) -> None:
    """T-02-08/T-02-09 mitigation: refuse any XML with a DOCTYPE/ENTITY.

    ENTSO-E responses never declare a DOCTYPE. `xml.etree.ElementTree`
    (expat) does not resolve *external* entities, but internal entity
    expansion ("billion laughs") is still possible via a DOCTYPE — reject
    before parsing rather than rely on the parser's default limits.
    """
    head = xml[:4096].lower()
    if "<!doctype" in head or "<!entity" in head:
        raise ContractError(
            "entsoe_xml",
            expected="no DOCTYPE/ENTITY declaration",
            actual="DOCTYPE/ENTITY present in input",
        )


def _parse_entsoe_datetime(text: str | None) -> datetime:
    if text is None:
        raise ContractError("entsoe_xml", expected="ISO8601 timestamp", actual="missing")
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def _resolution_timedelta(resolution: str) -> timedelta:
    minutes = _RESOLUTION_MINUTES.get(resolution)
    if minutes is None:
        raise ContractError(
            "entsoe_xml",
            expected="resolution in {'PT60M', 'PT30M', 'PT15M'}",
            actual=resolution,
        )
    return timedelta(minutes=minutes)


def _acknowledgement_reason(root: ET.Element) -> str:
    reason = _child(root, "Reason")
    if reason is None:
        return "no Reason element in Acknowledgement_MarketDocument"
    return _text(_child(reason, "text")) or "no reason text given"


def _zone_from_domain(ts_elem: ET.Element) -> str:
    for tag in ("in_Domain.mRID", "out_Domain.mRID", "outBiddingZone_Domain.mRID"):
        text = _text(_child(ts_elem, tag))
        if text:
            return _EIC_TO_ZONE.get(text, text)
    return "UNKNOWN"


def _extract_points(period: ET.Element) -> dict[int, float]:
    """1-based position -> value, reading `price.amount` or `quantity`."""
    values: dict[int, float] = {}
    for point in _children(period, "Point"):
        position_text = _text(_child(point, "position"))
        if position_text is None:
            continue
        value_elem = _child(point, "price.amount")
        if value_elem is None:
            value_elem = _child(point, "quantity")
        value_text = _text(value_elem)
        if value_text is None:
            continue
        values[int(position_text)] = float(value_text)
    return values


def _apply_a03_fill(values: dict[int, float], num_positions: int) -> tuple[dict[int, float], int]:
    """Forward-fill omitted positions within ``[1, num_positions]`` (ING-063).

    Returns the completed position->value mapping and the count of positions
    that were filled (0 if every position was already present in the XML).
    """
    filled = dict(values)
    fill_count = 0
    last: float | None = None
    for position in range(1, num_positions + 1):
        if position in filled:
            last = filled[position]
            continue
        if last is None:
            raise ContractError(
                "entsoe_prices",
                expected="a value at position 1 (A03 forward-fill needs a seed)",
                actual=f"position 1..{position} missing",
            )
        filled[position] = last
        fill_count += 1
    return filled, fill_count


def _period_rows(
    ts_elem: ET.Element, curve_type: str | None
) -> tuple[list[tuple[datetime, str, float]], int]:
    """Expand every ``Period``/``Point`` in a ``TimeSeries`` into rows.

    Applies ING-063 A03 forward-fill within each period when
    ``curve_type == 'A03'``. Returns ``(ts_utc, resolution, value)`` rows and
    the total count of forward-filled points across all periods.
    """
    rows: list[tuple[datetime, str, float]] = []
    fill_count = 0
    for period in _children(ts_elem, "Period"):
        resolution = _text(_child(period, "resolution")) or ""
        delta = _resolution_timedelta(resolution)
        interval = _child(period, "timeInterval")
        if interval is None:
            raise ContractError("entsoe_xml", expected="Period/timeInterval", actual="missing")
        start = _parse_entsoe_datetime(_text(_child(interval, "start")))
        end = _parse_entsoe_datetime(_text(_child(interval, "end")))
        num_positions = round((end - start) / delta)

        values = _extract_points(period)
        if curve_type == "A03":
            values, filled = _apply_a03_fill(values, num_positions)
            fill_count += filled

        for position in sorted(values):
            ts_utc = to_utc(start + delta * (position - 1))
            rows.append((ts_utc, resolution, values[position]))
    return rows, fill_count


def parse_publication_xml(xml: str) -> pd.DataFrame:
    """Parse a ``Publication_MarketDocument`` (day-ahead prices, A44).

    Implements: ING-050 (currency/unit assertion), ING-060 (resolution
    persisted as declared in the XML), ING-063 (A03 forward-fill within a
    period), ING-031/ING-005 (UTC conversion at the parse boundary).

    Returns:
        DataFrame with columns ``ts_utc`` (UTC tz-aware), ``price_eur_mwh``,
        ``resolution``, ``zone``. ``frame.attrs["a03_fills"]`` holds the
        total count of forward-filled points (0 if the document has none).

    Raises:
        ContractError: currency != EUR or unit != MWH (ING-050), an
            unexpected root element, or a DOCTYPE/ENTITY declaration
            (T-02-09).
        NoDataError: the response is an ``Acknowledgement_MarketDocument``
            (no data for the requested window).
    """
    _reject_doctype(xml)
    root = ET.fromstring(xml)
    root_name = _local_name(root.tag)

    if root_name == "Acknowledgement_MarketDocument":
        raise NoDataError("entsoe", "requested window", _acknowledgement_reason(root))
    if root_name != "Publication_MarketDocument":
        raise ContractError(
            "entsoe_prices", expected="Publication_MarketDocument", actual=root_name
        )

    rows: list[dict[str, object]] = []
    total_fills = 0
    for ts_elem in _children(root, "TimeSeries"):
        currency = _text(_child(ts_elem, "currency_Unit.name"))
        if currency != "EUR":
            raise ContractError(
                "entsoe_prices", expected="currency_Unit.name=EUR", actual=f"{currency}"
            )
        unit = _text(_child(ts_elem, "price_Measure_Unit.name"))
        if unit != "MWH":
            raise ContractError(
                "entsoe_prices", expected="price_Measure_Unit.name=MWH", actual=f"{unit}"
            )

        zone = _zone_from_domain(ts_elem)
        curve_type = _text(_child(ts_elem, "curveType"))
        period_rows, fills = _period_rows(ts_elem, curve_type)
        total_fills += fills
        rows.extend(
            {"ts_utc": ts_utc, "price_eur_mwh": value, "resolution": resolution, "zone": zone}
            for ts_utc, resolution, value in period_rows
        )

    if total_fills:
        logger.warning("entsoe prices A03 forward-fill applied to %d point(s)", total_fills)

    frame = pd.DataFrame(rows, columns=["ts_utc", "price_eur_mwh", "resolution", "zone"])
    frame = frame.sort_values("ts_utc").reset_index(drop=True)
    frame.attrs["a03_fills"] = total_fills
    return frame


def parse_gl_xml(xml: str, kind: Literal["load", "generation"]) -> pd.DataFrame:
    """Parse a ``GL_MarketDocument`` (actual load A65 or generation A75).

    Implements: ING-032 (generation long format with PSR code+name, ING-060
    resolution, ING-031/ING-005 UTC conversion at the parse boundary,
    ING-063 A03 forward-fill).

    Args:
        xml: raw XML text (`_fetch.fetch_entsoe` return value).
        kind: ``"load"`` for AT actual load (A65), ``"generation"`` for AT
            generation per type (A75).

    Returns:
        ``kind="load"``: columns ``ts_utc, load_mw, resolution, zone``.
        ``kind="generation"``: long format, one row per PSR type per
            timestamp: ``ts_utc, psr_type, psr_name, kind, value_mw,
            resolution, zone`` where ``kind`` is ``"aggregated"`` (businessType
            A01/production) or ``"consumption"`` (businessType A04, e.g.
            pumped-storage charging).

    Raises:
        ContractError: unexpected root element or a DOCTYPE/ENTITY
            declaration (T-02-09).
        NoDataError: the response is an ``Acknowledgement_MarketDocument``.
    """
    _reject_doctype(xml)
    root = ET.fromstring(xml)
    root_name = _local_name(root.tag)

    if root_name == "Acknowledgement_MarketDocument":
        raise NoDataError("entsoe", "requested window", _acknowledgement_reason(root))
    if root_name != "GL_MarketDocument":
        raise ContractError(f"entsoe_{kind}", expected="GL_MarketDocument", actual=root_name)

    rows: list[dict[str, object]] = []
    for ts_elem in _children(root, "TimeSeries"):
        zone = _zone_from_domain(ts_elem)
        curve_type = _text(_child(ts_elem, "curveType"))
        period_rows, _fills = _period_rows(ts_elem, curve_type)

        if kind == "load":
            rows.extend(
                {"ts_utc": ts_utc, "load_mw": value, "resolution": resolution, "zone": zone}
                for ts_utc, resolution, value in period_rows
            )
            continue

        psr_elem = _child(ts_elem, "MktPSRType")
        psr_type = (_text(_child(psr_elem, "psrType")) if psr_elem is not None else None) or (
            "UNKNOWN"
        )
        psr_name = PSR_NAMES.get(psr_type)
        if psr_name is None:
            psr_name = f"UNKNOWN({psr_type})"
            logger.warning("entsoe generation: unrecognized PSR type code %s", psr_type)
        business_type = _text(_child(ts_elem, "businessType"))
        gen_kind: Literal["aggregated", "consumption"] = (
            "consumption" if business_type == "A04" else "aggregated"
        )
        rows.extend(
            {
                "ts_utc": ts_utc,
                "psr_type": psr_type,
                "psr_name": psr_name,
                "kind": gen_kind,
                "value_mw": value,
                "resolution": resolution,
                "zone": zone,
            }
            for ts_utc, resolution, value in period_rows
        )

    columns = (
        ["ts_utc", "load_mw", "resolution", "zone"]
        if kind == "load"
        else ["ts_utc", "psr_type", "psr_name", "kind", "value_mw", "resolution", "zone"]
    )
    frame = pd.DataFrame(rows, columns=columns)
    return frame.sort_values("ts_utc").reset_index(drop=True)


def infer_resolution(ts: pd.Series) -> str:
    """Infer ``PT60M``/``PT15M`` from the median spacing of a timestamp series.

    Implements: ING-060's spacing-inference fallback, used when a source
    does not expose ``resolution`` directly (e.g. after joining rows from
    multiple periods/months).

    Raises:
        ValueError: fewer than 2 timestamps supplied.
        ContractError: median spacing matches neither PT60M nor PT15M.
    """
    if len(ts) < 2:
        raise ValueError("infer_resolution requires at least 2 timestamps")
    sorted_ts = ts.sort_values().reset_index(drop=True)
    median_gap = cast("pd.Timedelta", sorted_ts.diff().dropna().median())
    median_minutes = median_gap.total_seconds() / 60
    if round(median_minutes) == 60:
        return "PT60M"
    if round(median_minutes) == 15:
        return "PT15M"
    raise ContractError(
        "entsoe_resolution",
        expected="median spacing of 60 or 15 minutes",
        actual=f"{median_minutes} minutes",
    )


def hourly_mean(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """Aggregate sub-hourly rows to hourly by arithmetic MEAN — never sum (T-2).

    Implements: ING-061 (canonical hourly grain via mean of quarters), ING-062
    (guards the sum/mean confusion trap). Works for any numeric value column
    (``price_eur_mwh``, ``load_mw``, ``value_mw``, ...).

    Args:
        df: frame with a ``ts_utc`` column (any sub-hourly or hourly
            resolution) and ``value_col``.
        value_col: name of the numeric column to average.

    Returns:
        DataFrame with columns ``ts_utc`` (floored to the hour) and
        ``value_col``, one row per distinct hour.
    """
    result = (
        df.assign(ts_utc=df["ts_utc"].dt.floor("h"))
        .groupby("ts_utc", as_index=False)[value_col]
        .mean()  # NEVER .sum() here — T-2 / ING-062
    )
    return cast(pd.DataFrame, result)


def iter_chunks(start: date, end: date) -> Iterator[tuple[date, date]]:
    """Quarterly ``(start, end)`` request windows covering ``iter_month_starts``.

    Groups the month starts from ``timeutil.iter_month_starts`` into chunks
    of up to 3 months so a caller can request in <= 90-day windows (ING-030)
    without walking one month at a time.

    Yields:
        ``(chunk_start, chunk_end)`` where ``chunk_start`` is the first day
        of the first month in the chunk and ``chunk_end`` is the first day
        of the month after the chunk's last month (exclusive upper bound).
    """
    months = list(iter_month_starts(start, end))
    for i in range(0, len(months), 3):
        chunk = months[i : i + 3]
        yield chunk[0], next_month(chunk[-1])


@dataclass(frozen=True)
class _DatasetSpec:
    """Maps a §7 raw dataset name to the ENTSO-E document type + zone to fetch."""

    document_type: DocumentType
    zone_key: str  # key into settings.zones


#: The four SPEC-01 §3/§7 datasets this module ingests (ING-001).
_DATASET_SPECS: dict[str, _DatasetSpec] = {
    "entsoe_prices_at": _DatasetSpec("day_ahead_prices", "at"),
    "entsoe_prices_delu": _DatasetSpec("day_ahead_prices", "delu"),
    "entsoe_load_at": _DatasetSpec("load", "at"),
    "entsoe_gen_at": _DatasetSpec("generation", "at"),
}

#: Dataset keys in a fixed, deterministic iteration order (ING-040).
_DATASET_KEYS: tuple[str, ...] = tuple(_DATASET_SPECS)


def _parse_document(document_type: DocumentType, xml: str) -> pd.DataFrame:
    """Dispatch to the right Appendix-A parser for `document_type`."""
    if document_type == "day_ahead_prices":
        return parse_publication_xml(xml)
    kind: Literal["load", "generation"] = "load" if document_type == "load" else "generation"
    return parse_gl_xml(xml, kind)


def _write_by_month(
    frame: pd.DataFrame, dataset_key: str, req_hash: str, settings: Settings
) -> None:
    """Split `frame` into calendar-month slices and `write_month` each (ING-003).

    Grouping is by the UTC calendar month of `ts_utc` -- the same boundary
    `write_month`'s own validation enforces (§7 path `<dataset>_<YYYY-MM>`).
    A failure writing any one month raises immediately; `write_month`'s
    atomic temp-file-then-rename means no partial file is ever left for that
    month, and no later month in this frame gets written either (ING-003).
    """
    if frame.empty:
        return
    years = frame["ts_utc"].dt.year
    months = frame["ts_utc"].dt.month
    for year, month in sorted({(int(y), int(m)) for y, m in zip(years, months, strict=True)}):
        mask = (years == year) & (months == month)
        write_month(frame.loc[mask], dataset_key, date(year, month, 1), req_hash, settings)


def ingest_dataset(
    settings: Settings,
    dataset_key: str,
    start: date,
    end: date,
    transport: TransportFn | None = None,
    *,
    use_cache: bool = True,
) -> None:
    """Fetch, parse, and persist one §7 dataset over `[start, end]` (ING-001, ING-030).

    Iterates `iter_chunks` (<=90-day request windows per ING-030), fetches
    each chunk through `_fetch.fetch_entsoe` (the `transport` seam lets tests
    inject fixture XML instead of hitting the network -- ADR-003), parses
    with the parser matching `dataset_key`'s document type, and writes one
    parquet per calendar month via `_io.write_month`.

    A chunk with no data (`NoDataError` -- an `Acknowledgement_MarketDocument`
    response) is logged and skipped, not raised (SPEC-01 Appendix A: "no data
    for a future/edge window" is expected, not a failure). Any other parse or
    write failure propagates immediately -- ingestion never continues past a
    contract violation (A-2).

    Args:
        dataset_key: one of `entsoe_prices_at`, `entsoe_prices_delu`,
            `entsoe_load_at`, `entsoe_gen_at`.
        transport: forwarded to `fetch_entsoe`; `None` uses the real network.
        use_cache: forwarded to `fetch_entsoe` (`--no-cache` semantics).
    """
    spec = _DATASET_SPECS[dataset_key]
    zone_cfg = settings.zones[spec.zone_key]

    for chunk_start, chunk_end in iter_chunks(start, end):
        period_start = to_utc(
            datetime(chunk_start.year, chunk_start.month, chunk_start.day, tzinfo=VIENNA)
        )
        period_end = to_utc(datetime(chunk_end.year, chunk_end.month, chunk_end.day, tzinfo=VIENNA))
        query = EntsoeQuery(
            document_type=spec.document_type,
            domain=zone_cfg.eic,
            period_start=period_start,
            period_end=period_end,
        )
        # request_hash() strips the securityToken value regardless of what's
        # passed, so a placeholder here yields the identical hash fetch_entsoe
        # computes internally from the real token -- no second token read.
        req_hash = request_hash(_cache_request_url(query, "x"))

        try:
            xml = fetch_entsoe(query, settings, use_cache=use_cache, transport=transport)
            frame = _parse_document(spec.document_type, xml)
        except NoDataError as exc:
            logger.info(
                "dataset=%s window=%s..%s no data: %s", dataset_key, chunk_start, chunk_end, exc
            )
            continue

        fills = frame.attrs.get("a03_fills", 0)
        if fills:
            logger.info(
                "dataset=%s window=%s..%s a03_fills=%d",
                dataset_key,
                chunk_start,
                chunk_end,
                fills,
            )

        _write_by_month(frame, dataset_key, req_hash, settings)


def backfill(
    settings: Settings,
    start: date,
    end: date,
    transport: TransportFn | None = None,
    *,
    use_cache: bool = True,
) -> None:
    """Full ingestion of all four ENTSO-E datasets for [start, end] (ING-040).

    Calls `ingest_dataset` once per dataset key in `_DATASET_KEYS`'s fixed
    order. `transport`/`use_cache` are forwarded unchanged so callers (the
    CLI, tests) control every fetch through the single injectable seam.
    """
    for dataset_key in _DATASET_KEYS:
        ingest_dataset(settings, dataset_key, start, end, transport, use_cache=use_cache)


def ingest_incremental(
    settings: Settings,
    transport: TransportFn | None = None,
    *,
    use_cache: bool = True,
) -> None:
    """45-day lookback re-ingestion — ENTSO-E restates recent data (ING-041).

    Re-ingests all four datasets over `[today - incremental_lookback_days,
    today]`, rewriting the affected month files (`write_month`'s atomic
    overwrite makes this idempotent, ING-003).
    """
    end = date.today()
    start = end - timedelta(days=settings.ingest.incremental_lookback_days)
    for dataset_key in _DATASET_KEYS:
        ingest_dataset(settings, dataset_key, start, end, transport, use_cache=use_cache)


_MONTH_FILENAME_RE = re.compile(r"_(\d{4})-(\d{2})\.parquet$")


def _month_from_path(path: Path) -> date:
    """Parse the `<YYYY>-<MM>` month out of a §7 raw parquet filename."""
    match = _MONTH_FILENAME_RE.search(path.name)
    if match is None:
        raise ContractError(
            "entsoe_raw_layout", expected="<dataset>_<YYYY-MM>.parquet", actual=path.name
        )
    return date(int(match.group(1)), int(match.group(2)), 1)


def _dataset_root(dataset: str, settings: Settings) -> Path:
    """Absolute `data/raw/<dataset>/` root (mirrors `_io._data_raw_root`)."""
    p = settings.paths.data_raw
    root = p if p.is_absolute() else REPO_ROOT / p
    return root / dataset


def _complete_price_months(dataset: str, settings: Settings) -> list[date]:
    """Months (any order) where every UTC calendar day has >=1 price row.

    "Complete" per ADR-005: after `hourly_mean` aggregation, every day of the
    file's own calendar month has at least one hourly row. Rows are grouped
    by the UTC calendar day of `ts_utc` -- the same boundary `write_month`
    partitions files on, so no second timezone conversion is needed here.
    """
    root = _dataset_root(dataset, settings)
    if not root.exists():
        return []
    complete: list[date] = []
    for parquet_path in sorted(root.glob("*/*.parquet")):
        month = _month_from_path(parquet_path)
        frame = pd.read_parquet(parquet_path, columns=["ts_utc", "price_eur_mwh"])
        if frame.empty:
            continue
        hourly = hourly_mean(frame, "price_eur_mwh")
        present_days = set(hourly["ts_utc"].dt.date)
        _, days_in_month = monthrange(month.year, month.month)
        expected_days = {date(month.year, month.month, d) for d in range(1, days_in_month + 1)}
        if expected_days <= present_days:
            complete.append(month)
    return complete


def latest_complete_month(settings: Settings) -> date:
    """First day of the last calendar month with ALL days of price data present.

    Computed from ingested data, never assumed (ING-042). Per ADR-005 (adopts
    SG-02): returns `min(latest complete AT-prices month, latest complete
    DE-LU-prices month)` so a downstream AT/DE-LU spread calculation never
    assumes a month where either zone is still incomplete. Downstream modules
    (dbt freshness, SPEC-05 forward window) call this instead of guessing.

    Raises:
        NoDataError: no complete month exists yet for AT and/or DE-LU prices
            (e.g. `backfill` has not run) -- computed, not assumed (ING-042).
    """
    at_months = _complete_price_months("entsoe_prices_at", settings)
    delu_months = _complete_price_months("entsoe_prices_delu", settings)
    if not at_months or not delu_months:
        raise NoDataError(
            "entsoe",
            "prices",
            "no complete calendar month of AT and/or DE-LU day-ahead prices "
            "has been ingested yet; run backfill first (ING-042/ADR-005)",
        )
    return month_start(min(max(at_months), max(delu_months)))


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: ``python -m epra.ingest.entsoe --start YYYY-MM-DD --end YYYY-MM-DD`` (ING-002)."""
    raise NotImplementedError(_MSG)


if __name__ == "__main__":
    raise SystemExit(main())

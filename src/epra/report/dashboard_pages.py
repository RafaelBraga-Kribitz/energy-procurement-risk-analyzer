"""Dashboard page registry: ONE definition for the Power BI report and its HTML twin.

Both deliverables of ADR-022 read their page set from here: the PBIP report in
``dashboards/EPRA.Report`` (checked by ``tests/unit/test_pbip_integrity.py``) and
the static HTML twin written by :mod:`epra.report.html_dashboard`. Page names are
the SPEC-06 §4 names (English, RP-705); each page carries exactly one German
subtitle sentence (RP-405), taken verbatim from ``dashboards/README.md``.

Implements: RP-401..RP-405, ADR-020 §4 (page 5), ADR-022.
"""

from __future__ import annotations

from dataclasses import dataclass

#: RP-702 source note, identical on every page of both deliverables.
SOURCE_NOTE = "Source: ENTSO-E Transparency / AEA ÖSPI / own calculations"

#: Epistemic notes, word for word the `Epistemic Note …` measures in the model.
EPISTEMIC_STRATEGIES = (
    "CALIBRATED · constructed load profile (SPEC-03) · contract prices via ÖSPI proxy"
)
EPISTEMIC_RISK = "SIMULATED · seeded block bootstrap of historical months · not a forecast"
EPISTEMIC_VERIFIED = "VERIFIED · computed from ENTSO-E day-ahead prices, no modelling"

#: The `Data Banner` text on a fixture run (ADR-018), word for word the measure.
FIXTURE_BANNER = "FIXTURE RUN — synthetic CI data, NOT results (ADR-018)"


@dataclass(frozen=True)
class DashboardPage:
    """One report page: id, SPEC-06 name, English heading, German subtitle, footer tag.

    Implements: RP-401..RP-405.
    """

    page_id: str
    title: str
    heading: str
    subtitle_de: str
    requirement: str
    epistemic: str


#: The five pages, in report order (SPEC-06 §4 + ADR-020 §4).
PAGES: tuple[DashboardPage, ...] = (
    DashboardPage(
        "headline",
        "Headline",
        "What the wrong procurement strategy cost a 50 GWh Styrian manufacturer",
        "Was hat die falsche Beschaffungsstrategie 2021–2025 gekostet, und welches Risiko bleibt?",
        "RP-401",
        EPISTEMIC_STRATEGIES,
    ),
    DashboardPage(
        "market",
        "Market",
        "The Austrian day-ahead market since 2019",
        "Der österreichische Day-Ahead-Markt: Preisniveau, negative Stunden "
        "und Abstand zu Deutschland.",
        "RP-402",
        EPISTEMIC_VERIFIED,
    ),
    DashboardPage(
        "strategies",
        "Strategies",
        "Annual energy cost of each procurement strategy, 2021–2025",
        "Jährliche Energiekosten je Strategie für einen Verbraucher mit 50 GWh pro Jahr.",
        "RP-403",
        EPISTEMIC_STRATEGIES,
    ),
    DashboardPage(
        "risk",
        "Risk",
        "What the next 12 months could cost, by strategy",
        "Kostenverteilung der nächsten 12 Monate aus {n_paths} simulierten Pfaden "
        "– keine Prognose.",
        "RP-404",
        EPISTEMIC_RISK,
    ),
    DashboardPage(
        "data-quality",
        "Data quality",
        "How complete and clean the input data is",
        "Vollständigkeit und Qualität der Eingangsdaten je Monat.",
        "ADR-020 §3",
        EPISTEMIC_VERIFIED,
    ),
)


def german_int(value: int) -> str:
    """German thousands separator for the one number inside a subtitle: 2000 → ``2.000``.

    RP-705 keeps German conventions out of charts; a German subtitle (RP-405)
    is the one place they belong.

    Implements: RP-405, RP-705.
    """
    return f"{value:,d}".replace(",", ".")


def subtitle(page: DashboardPage, n_paths: int) -> str:
    """The page's German subtitle with the configured path count filled in.

    Implements: RP-405.
    """
    return page.subtitle_de.format(n_paths=german_int(n_paths))

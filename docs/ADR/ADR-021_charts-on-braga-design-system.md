# ADR-021: Charts on the Braga design system v2.1
Date: 2026-10-26  |  Status: accepted

Amends: SPEC-06 RP-704 (strategy colour families and palette). Related: ADR-020.

## Context

The owner's decision (26 Oct 2026) is that every public portfolio repository
draws its charts on the Braga design system v2.1. That system is defined in
braga-portfolio-v2 `design-system/DECISIONS.md`, and its chart rules are in
D-053, delivered through the `bk-viz` 2.0.0 package. RP-704 as written names
specific colour families: S1 red, S2 orange, S3 blue, and the Okabe-Ito palette.
The design system reserves red and orange tints for its good/bad diverging
scale. It assigns unordered series to its categorical slots in order, and it
keeps hex values out of consuming repositories. Keeping RP-704's literal
families would put a second palette beside the system the portfolio site and
every other repository use.

RP-704's output contract is the part the reader depends on:
1. colours are defined once in `src/epra/report/style.py`;
2. a strategy keeps the same colour in every PNG and in the Power BI theme;
3. hybrids are interpolated between the S1 and S3 endpoints;
4. the strategies stay distinguishable to colour-blind readers.

## Decision

1. Strategy colours come from the design system's categorical roles through
   `bk-viz`:
   - S3 (fixed) takes `cat-1`;
   - S1 (spot) takes `cat-2`;
   - S2 (ÖSPI-indexed) takes `cat-3`;
   - hybrids S4_h are interpolated from S1 to S3 by the hedge ratio, as before.
2. The mapping, the interpolation and the "defined once" rule stay in
   `src/epra/report/style.py`. The Power BI theme is still built from the same
   constants, and the existing test checks that it matches (RP-704).
3. Okabe-Ito is replaced by the design system's categorical palette. The colour
   names in RP-704 (red, orange) no longer apply.

## Consequences

- Every strategy chart and the Power BI theme change colour once; no number,
  label or chart structure changes.
- Colour-blind check (Machado 2009 simulation, CIELAB ΔE between S1, S2 and S3):
  - normal vision: at least 75;
  - deuteranopia: at least 52;
  - protanopia: at least 51;
  - tritanopia: 17 between S2 and S3.
  S2 and S3 are therefore close under tritanopia, the rarest form. This is
  accepted as a known limitation; the legend still names every strategy.
- A future change to the design system's categorical slots reaches this
  repository through the `bk-viz` pin, not through an edit here.

## Spec deviations (list REQ IDs affected, or "none")

RP-704: the colour families (S1 red, S2 orange) and the Okabe-Ito palette are
replaced as above. The rest of RP-704 is unchanged.

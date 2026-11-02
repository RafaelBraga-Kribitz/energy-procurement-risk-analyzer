# Energie-Beschaffungsrisiko-Analyse (EPRA)

[🇧🇷 PT-BR](README.pt-BR.md) · [🇬🇧 EN-UK](README.md) · [🇦🇹 DE-AT](README.de-AT.md)

## Überblick

EPRA vergleicht Beschaffungsstrategien für einen konstruierten steirischen Industrieverbraucher mit **50 GWh Jahresverbrauch**. Grundlage sind reale Preise des österreichischen Day-Ahead-Markts von 2021 bis 2025. Der Referenzfall bildet kein reales Unternehmen ab.

Historisch war der jährliche Fixpreis mit kalibrierten Gesamtkosten von €30,17 Mio. am günstigsten. Für die kommenden zwölf Monate hat der Jahresfixpreis die niedrigsten erwarteten simulierten Kosten (€4,77 Mio.). Die Hybridstrategie mit 70 % Fixpreis weist die geringste P95-Exposition auf (€6,44 Mio. gegenüber €6,61 Mio.). P95 bedeutet, dass ungefähr 5 % der simulierten Kosten darüber liegen.

Die Simulation zieht vergangene Preise neu; sie ist keine Preisprognose. Das Lastprofil ist konstruiert. Vertragspreise werden durch den ÖSPI angenähert und stammen nicht aus tatsächlichen Lieferantenangeboten.

## Was das Projekt zeigt

- Import von Preisen über die ENTSO-E-Transparenzplattform.
- Datenpipeline, SQL/dbt-Abfragen und Datenqualitätsprüfungen.
- Vergleich von sechs Optionen: Spotmarkt, ÖSPI-indexiert, Jahresfixpreis und drei Hybridanteile.
- Getrennte Kennzeichnung verifizierter Daten, kalibrierter Annahmen und simulierter Ergebnisse.

Das [vollständige README auf Englisch](README.md) enthält Tabellen, Diagramme, Quellen, Grenzen und Architektur. Die [Executive Summary](reports/EXEC_SUMMARY.md) fasst die Entscheidung für CFO und Einkauf zusammen. Pipeline und erster Echtdatenlauf sind abgeschlossen; die Aktualisierung in Power BI Desktop steht noch aus.

[Repository](https://github.com/RafaelBraga-Kribitz/energy-procurement-risk-analyzer) · [Datenqualität](reports/data_quality/DATA_QUALITY.md) · [Einschränkungen](LIMITATIONS.md)

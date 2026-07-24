# API Coverage — GeoSphere Data Hub (dataset.api.hub.geosphere.at)

> Full coverage by default. Opt-outs are explicit, reasoned decisions.
> Scope is bounded by SPEC-01 §9 (ING-090..094): daily mean air temperature for one Graz station.
> GeoSphere is a passive, no-auth public data source (CC-BY 4.0), not a service EPRA calls back into.

| capability | decision | reason |
|---|---|---|
| station metadata / discovery (`/station/historical/klima-v2-1d/metadata`) | INTEGRATE | ING-091 station discovery (03-03) |
| historical daily station data (`/station/historical/klima-v2-1d`, `tl_mittel`) | INTEGRATE | ING-090/092/093 daily mean temperature ingest (03-04) |
| dataset listing (`/datasets`) | INTEGRATE | ING-091 fallback to verify/substitute the `klima-v2-1d` dataset id if renamed (03-03, ADR-007) |
| other datasets (gridded / spatial / raster products) | OPT-OUT | out of scope — SPEC-01 §9 needs only station-based daily mean temperature |
| current / forecast / nowcast endpoints | OPT-OUT | out of scope — EPRA ingests historical 2019→latest only (window.start_date 2019-01-01) |
| sub-daily / hourly resolutions (other `klima-*` datasets) | OPT-OUT | not needed — §7 GeoSphere contract is daily `date`-grain (`geosphere_graz_daily`) |
| parameters other than `tl_mittel` (precip, wind, humidity, …) | OPT-OUT | not needed — SPEC-01 §9 specifies daily mean air temperature only |
| authentication / API-key flows | OPT-OUT | not applicable — GeoSphere public data requires no auth (ING-093) |

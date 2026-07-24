# Ingestion validation report — 2026-07-22



**Overall: ALL GATES PASSED**

### ING-080 — PASS

all zone-years within coverage (<=24 missing hours); DST hour counts correct

```
              zone  year    check  expected  actual  missing_hours    scope   ok
  entsoe_prices_at  2019 coverage      8760    8760            0.0 complete True
  entsoe_prices_at  2019  dst_mar        23      23            NaN complete True
  entsoe_prices_at  2019  dst_oct        25      25            NaN complete True
  entsoe_prices_at  2020 coverage      8784    8784            0.0 complete True
  entsoe_prices_at  2020  dst_mar        23      23            NaN complete True
  entsoe_prices_at  2020  dst_oct        25      25            NaN complete True
  entsoe_prices_at  2021 coverage      8760    8760            0.0 complete True
  entsoe_prices_at  2021  dst_mar        23      23            NaN complete True
  entsoe_prices_at  2021  dst_oct        25      25            NaN complete True
  entsoe_prices_at  2022 coverage      8760    8760            0.0 complete True
  entsoe_prices_at  2022  dst_mar        23      23            NaN complete True
  entsoe_prices_at  2022  dst_oct        25      25            NaN complete True
  entsoe_prices_at  2023 coverage      8760    8760            0.0 complete True
  entsoe_prices_at  2023  dst_mar        23      23            NaN complete True
  entsoe_prices_at  2023  dst_oct        25      25            NaN complete True
  entsoe_prices_at  2024 coverage      8784     910         7874.0 boundary True
entsoe_prices_delu  2019 coverage      8760    8760            0.0 complete True
entsoe_prices_delu  2019  dst_mar        23      23            NaN complete True
entsoe_prices_delu  2019  dst_oct        25      25            NaN complete True
entsoe_prices_delu  2020 coverage      8784    8784            0.0 complete True
entsoe_prices_delu  2020  dst_mar        23      23            NaN complete True
entsoe_prices_delu  2020  dst_oct        25      25            NaN complete True
entsoe_prices_delu  2021 coverage      8760    8760            0.0 complete True
entsoe_prices_delu  2021  dst_mar        23      23            NaN complete True
entsoe_prices_delu  2021  dst_oct        25      25            NaN complete True
entsoe_prices_delu  2022 coverage      8760    8760            0.0 complete True
entsoe_prices_delu  2022  dst_mar        23      23            NaN complete True
entsoe_prices_delu  2022  dst_oct        25      25            NaN complete True
entsoe_prices_delu  2023 coverage      8760    8760            0.0 complete True
entsoe_prices_delu  2023  dst_mar        23      23            NaN complete True
entsoe_prices_delu  2023  dst_oct        25      25            NaN complete True
entsoe_prices_delu  2024 coverage      8784     910         7874.0 boundary True
    entsoe_load_at  2019 coverage      8760    8760            0.0 complete True
    entsoe_load_at  2019  dst_mar        23      23            NaN complete True
    entsoe_load_at  2019  dst_oct        25      25            NaN complete True
    entsoe_load_at  2020 coverage      8784    8784            0.0 complete True
    entsoe_load_at  2020  dst_mar        23      23            NaN complete True
    entsoe_load_at  2020  dst_oct        25      25            NaN complete True
    entsoe_load_at  2021 coverage      8760    8760            0.0 complete True
    entsoe_load_at  2021  dst_mar        23      23            NaN complete True
    entsoe_load_at  2021  dst_oct        25      25            NaN complete True
    entsoe_load_at  2022 coverage      8760    8760            0.0 complete True
    entsoe_load_at  2022  dst_mar        23      23            NaN complete True
    entsoe_load_at  2022  dst_oct        25      25            NaN complete True
    entsoe_load_at  2023 coverage      8760    8760            0.0 complete True
    entsoe_load_at  2023  dst_mar        23      23            NaN complete True
    entsoe_load_at  2023  dst_oct        25      25            NaN complete True
    entsoe_load_at  2024 coverage      8784    1438         7346.0 boundary True
```

### ING-081 — PASS

all 44734 hourly AT price(s) within [-500.0, 5000.0] EUR/MWh

### ING-082 — PASS

all annual means within the SPEC-01 §8 plausibility table

```
 year  mean_price_eur_mwh expected_range    scope   ok
 2019               40.14       (25, 55) complete True
 2020               33.09       (20, 50) complete True
 2021              108.59      (80, 130) complete True
 2022              264.41     (200, 320) complete True
 2023              102.04      (70, 140) complete True
 2024               76.38      (50, 110) boundary True
```

### ING-083 — PASS

at least one negative hourly AT price present in each complete required year (2023)

```
 year  n_negative   ok
 2023         109 True
```

### ING-084 — PASS

AT load within hourly and annual mean plausibility bands

### ING-085 — PASS

price/load join coverage >=99.5% for every year

```
 year  price_hours  matched_hours  coverage    scope   ok
 2019         8760           8760       1.0 complete True
 2020         8784           8784       1.0 complete True
 2021         8760           8760       1.0 complete True
 2022         8760           8760       1.0 complete True
 2023         8760           8760       1.0 complete True
 2024          910            910       1.0 boundary True
```

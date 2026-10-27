# Ingestion validation report — 2026-10-28



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
  entsoe_prices_at  2024 coverage      8784    8784            0.0 complete True
  entsoe_prices_at  2024  dst_mar        23      23            NaN complete True
  entsoe_prices_at  2024  dst_oct        25      25            NaN complete True
  entsoe_prices_at  2025 coverage      8760    8760            0.0 complete True
  entsoe_prices_at  2025  dst_mar        23      23            NaN complete True
  entsoe_prices_at  2025  dst_oct        25      25            NaN complete True
  entsoe_prices_at  2026 coverage      8760    6551         2209.0 boundary True
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
entsoe_prices_delu  2024 coverage      8784    8784            0.0 complete True
entsoe_prices_delu  2024  dst_mar        23      23            NaN complete True
entsoe_prices_delu  2024  dst_oct        25      25            NaN complete True
entsoe_prices_delu  2025 coverage      8760    8760            0.0 complete True
entsoe_prices_delu  2025  dst_mar        23      23            NaN complete True
entsoe_prices_delu  2025  dst_oct        25      25            NaN complete True
entsoe_prices_delu  2026 coverage      8760    6551         2209.0 boundary True
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
    entsoe_load_at  2024 coverage      8784    8784            0.0 complete True
    entsoe_load_at  2024  dst_mar        23      23            NaN complete True
    entsoe_load_at  2024  dst_oct        25      25            NaN complete True
    entsoe_load_at  2025 coverage      8760    8760            0.0 complete True
    entsoe_load_at  2025  dst_mar        23      23            NaN complete True
    entsoe_load_at  2025  dst_oct        25      25            NaN complete True
    entsoe_load_at  2026 coverage      8760    6551         2209.0 boundary True
```

### ING-081 — PASS

all 67919 hourly AT price(s) within [-500.0, 5000.0] EUR/MWh

### ING-082 — PASS

all annual means within the SPEC-01 §8 plausibility table

```
 year  mean_price_eur_mwh expected_range    scope   ok
 2019               40.06       (25, 55) complete True
 2020               33.14       (20, 50) complete True
 2021              106.85      (80, 130) complete True
 2022              261.40     (200, 320) complete True
 2023              102.14      (70, 140) complete True
 2024               81.54      (50, 110) complete True
 2025               98.94      (40, 140) complete True
 2026              121.83           None boundary True
```

### ING-083 — PASS

at least one negative hourly AT price present in each complete required year (2023/2024/2025)

```
 year  n_negative   ok
 2023         111 True
 2024         296 True
 2025         378 True
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
 2024         8784           8784       1.0 complete True
 2025         8760           8760       1.0 complete True
 2026         6551           6551       1.0 boundary True
```

### ING-094 — PASS

coverage/range/seasonal-mean checks all pass

```
       check                        expected                  actual   ok
    coverage >=99% of 2019-01-01..2026-09-30 1.0000 (2830/2830 days) True
       range              [-30.0, 42.0] degC   0 row(s) out of range True
   july_mean                    (15.0, 30.0)                   22.28 True
january_mean                    (-10.0, 8.0)                    1.56 True
```

### ING-103 — PASS

continuity/positivity/crisis-visibility/MoM checks all pass

```
            check          expected                                             actual   ok
       continuity           no gaps                                               none True
       positivity               > 0                              0 non-positive row(s) True
crisis_visibility >= 3.0x 2019 mean 2022 max=660.44 vs 2019 mean=103.54 (need >= 3.0x) True
       mom_change            <= 60%                     0 month(s) exceeding threshold True
```

### ING-111 — PASS

holiday-count/fixed-holiday/peak-hour checks all pass

```
             check                                                             expected                               actual   ok
holiday_count_2024                                                                   13                                   13 True
    fixed_holidays                                 [2024-01-01, 2024-05-01, 2024-12-25] [2024-01-01, 2024-05-01, 2024-12-25] True
 peak_hour_mon_sun Mon 2024-01-08 10:00 local=peak; Sun 2024-01-07 10:00 local=off-peak  monday_peak=True, sunday_peak=False True
```

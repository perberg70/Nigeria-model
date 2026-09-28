# Nigeria GDP series — World Bank World Development Indicators

Benchmark for the prototype's GDP-growth slider.

- **Source:** World Bank indicators API,
  `https://api.worldbank.org/v2/country/NGA/indicator/<INDICATOR>?format=json&date=2005:2025`
- **Retrieved:** 2026-08-17 (database updated 2026-07-13; recent years may be revised).
- **Licence:** CC BY 4.0,
  https://datacatalog.worldbank.org/search/dataset/0037712/World-Development-Indicators

## Files

| File | Indicator | Contents |
|---|---|---|
| `NY.GDP.MKTP.CN.json` | GDP (current local currency) | Nominal GDP in naira |
| `NY.GDP.MKTP.KD.ZG.json` | GDP growth (annual %) | Real growth |
| `NY.GDP.DEFL.KD.ZG.json` | Inflation, GDP deflator (annual %) | |
| `NY.GDP.MKTP.CD.json` | GDP (current US$) | Context only |
| `FP.CPI.TOTL.ZG.json` | Inflation, consumer prices (annual %) | Cross-check |
| `nigeria_gdp_wdi_2005_2025.csv` | All five joined by year, plus nominal growth computed from the naira series | Derived |

The JSON files are unmodified API responses.

## Two warnings

1. **2019 is a level break, not growth.** Nominal GDP jumps 58.9% against 2.2% real growth because
   Nigeria's statistics bureau rebased to 2019. Exclude or bridge 2019 in any average.
2. **Do not compute growth from the US$ series.** It falls from US$647bn (2022) to US$252bn (2024)
   while naira GDP rises 36% — the naira devaluation, not a 60% contraction.

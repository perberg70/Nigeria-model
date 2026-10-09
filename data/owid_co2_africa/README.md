# African CO₂ by source, population and GDP, 2000–2024 — Our World in Data

An extract of Our World in Data's CO₂ dataset. It covers the 54 African countries plus OWID's "Africa"
aggregate, used to compare Nigeria's carbon intensity with the rest of the continent's. It
supports the carbon-intensity check in
`../scenario_compass_africa_r10/carbon_intensity/` (experiment branch). **The prototype does not
use it.**

- **Source file:** `owid-co2-data.csv` from the `owid/co2-data` repository, master branch,
  `https://raw.githubusercontent.com/owid/co2-data/master/owid-co2-data.csv`.
- **Retrieved:** 2026-10-09 by a Claude Code session. The commit hash was not recorded, because
  github.com itself was blocked by the session's network policy. Column definitions come from
  `owid-co2-codebook.csv` in the same repository, read at the same time.
- **Licence:** Our World in Data publishes the dataset under CC BY 4.0, with the original
  sources credited. `[GAP: the licence statement was not re-read at source this session.]`

## Extraction

The extract keeps every row with an African ISO code (54 countries; Western Sahara has no rows) or
`country == "Africa"`, for 2000–2024, and 13 columns. Values are as published, unmodified.

Check: the 54 country rows sum to the "Africa" aggregate's CO₂, to within 0.1 Mt in every year
checked.

| Column | Definition (OWID codebook) | Unit | Underlying source |
|---|---|---|---|
| `co2` | Annual total CO₂, excluding land-use change | Mt | Global Carbon Budget (2025) |
| `coal_co2`, `oil_co2`, `gas_co2`, `flaring_co2`, `cement_co2`, `other_industry_co2` | CO₂ by source | Mt | Global Carbon Budget (2025) |
| `gdp` | Total output, adjusted for inflation and living costs | international-$, 2011 prices | Maddison Project Database 2023 |
| `population` | Population | people | OWID population sources (2024) |
| `primary_energy_consumption` | Primary energy (excludes traditional biomass) | TWh | U.S. EIA International Energy Data (2026); Energy Institute Statistical Review |

## Caveats

1. **Nigeria's oil CO₂ more than doubles from 2009 to 2010** (27.3 → 58.7 Mt), while IEA
   commercial final energy rises 19%. This is almost certainly a break in the underlying data,
   not a change in emissions. The prototype draws the same Global Carbon Budget series as its
   observed history line (`../global_carbon_budget_nigeria/`), so the 2009–2010 jump is visible
   there too.
2. **Flaring is a large and shrinking share of Nigeria's CO₂:** 53% in 2000, 25% in 2010, 8% in
   2023.
3. **Maddison GDP for Nigeria grows much faster over 2000–2010 than WDI real GDP:** about
   11–14% a year against 6–8% from 2005. Any CO₂/GDP trend for Nigeria in that decade depends on
   which series is used.
4. **Maddison GDP is missing for Eritrea, Sudan, Somalia and South Sudan**, so regional GDP
   ratios use the other 50 countries (94% of population). Maddison has no 2023 or 2024 values.
5. **Nigeria's `primary_energy_consumption` is erratic** (EIA data; for example, 2010 is below
   2008). The check uses IEA final energy for Nigeria instead.

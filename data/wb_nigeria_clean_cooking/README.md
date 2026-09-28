# Nigeria — share of people mainly using clean cooking fuels (SDG 7.1.2)

- **Indicator:** World Bank `EG.CFT.ACCS.ZS`, "Access to clean fuels and technologies for cooking
  (% of population)".
- **Source:** Tracking SDG 7: The Energy Progress Report (IEA, IRENA, UNSD, World Bank, WHO), 2025,
  via the World Bank API:
  https://api.worldbank.org/v2/country/NGA/indicator/EG.CFT.ACCS.ZS?format=json&per_page=100&date=2000:2025
- **Retrieved:** 2026-09-28 (dataset last updated 2026-07-13).
- **Licence:** CC BY-NC 3.0 IGO.

## File

`EG.CFT.ACCS.ZS_nigeria.csv` — annual values 2000–2023 as returned by the API (2024 and 2025 are
empty at source).

## Definition

Despite the word "access" in its title, the indicator is *"the proportion of total population
primarily using clean cooking fuels and technologies for cooking. Under WHO guidelines, kerosene
is excluded from clean cooking fuels."* It measures the fuel people mainly cook with. People not
counted here cook mainly with wood, charcoal or kerosene — the population WHO's household
air-pollution deaths are attributed to.

## Values used by the prototype

| Year | Clean cooking | Polluting fuels |
|---|---|---|
| 2021 | 21.85% | 78.15% |
| 2023 | 26.2% | 73.8% |

## Caveats

- The series is modelled by WHO from household surveys (Stoner et al. 2021, *Nature
  Communications* 12:5793), so year-to-year values are smoothed.
- It rose from 0.7% (2000) to 26.2% (2023), about 2.6 percentage points a year since 2016, while
  real income per head was roughly flat.

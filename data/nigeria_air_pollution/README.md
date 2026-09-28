# Nigeria air-pollution mortality and exposure — WHO and World Bank

- **Sources:**
  - WHO Global Health Observatory OData API,
    `https://ghoapi.azureedge.net/api/<INDICATOR>?$filter=SpatialDim eq 'NGA'`
  - World Bank World Development Indicators, `EN.ATM.PM25.MC.M3` (database updated 2026-07-13).
- **Retrieved:** 2026-08-17.
- **Licences:** World Bank WDI: CC BY 4.0. WHO GHO: check WHO's terms before reuse.

## Files

| File | Indicator | Contents |
|---|---|---|
| `AIR_11_nigeria.json` | Household air pollution attributable deaths | 2021, by sex and cause |
| `AIR_41_nigeria.json` | Ambient air pollution attributable deaths | 2021, by sex and cause |
| `AIR_42_nigeria.json` | Ambient attributable death rate, age-standardised, per 100 000 | 2021 |
| `EN.ATM.PM25.MC.M3_nigeria.json` | PM2.5 mean annual exposure, µg/m³ | 2000–2023 |
| `who_deaths_nigeria_2021.csv` | AIR_11 and AIR_41, both sexes, six causes, with uncertainty intervals | derived from the JSON files |

The JSON files are the unmodified API responses.

## Headline figures, both sexes, 2021

| | Deaths | 95% uncertainty interval |
|---|---|---|
| Household (AIR_11) | **156,483** | 131,472–178,292 |
| Ambient (AIR_41) | 106,962 | 83,995–132,590 |

Ambient age-standardised death rate: 77.6 per 100 000 (62.5–95.2). PM2.5 exposure: 65.7 µg/m³
(2023).

The prototype uses the household figure, 156,483 deaths in 2021, as its starting point.

## Caveats

- **Do not add the two totals.** WHO attributes the same deaths to household and ambient exposure
  through overlapping pathways; the combined burden is a separate WHO indicator.
- Both are modelled attributions (exposure × concentration-response), not death counts.

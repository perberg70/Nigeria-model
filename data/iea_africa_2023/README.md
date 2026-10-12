# IEA regional data — Africa

Exports from the International Energy Agency's Africa region charts, annual 2000–2023. They supply
the observed final-energy series for the whole continent, which is like-for-like with IMAGE 3.2's
"Final Energy" variable. **The prototype does not use them**; they serve the carbon-intensity
check in `../scenario_compass_africa_r10/carbon_intensity/` (experiment branch).

- **Copied into this repository** on 2026-10-09 from MSc-thesis `02_literature/data/iea_africa_2023/`
  (commit `1c58444`), at Per's request. The CSVs are byte-identical copies.
- **Originally retrieved by:** Per, 2026-09-18, on an ordinary connection (`iea.org` is blocked
  from Claude Code sessions). `[GAP: the exact IEA page was not recorded; the files carry IEA's
  chart-export naming.]`
- **Licence:** CC BY 4.0, on the same basis as the Nigeria chart exports in `../iea_nigeria_2023/`.
  That reading of the IEA terms comes from search-result summaries, not the terms page itself.
  Confirm before publication.

## Required attribution

> IEA 2026; *[chart title]*, https://www.iea.org, Licence: CC BY 4.0

## Files

| File | Contents | Years |
|---|---|---|
| `total_final_consumption_by_sector_africa_2000_2023.csv` | Total final consumption across 8 sectors, TJ | 2000–2023 |
| `residential_final_consumption_by_source_africa_2000_2023.csv` | Residential final consumption by source, TJ | 2000–2023 |
| `commercial_final_consumption_by_source_africa_2000_2023.csv` | Commercial and public services final consumption by source, TJ | 2000–2023 |
| `industry_final_consumption_by_source_africa_2000_2023.csv` | Industry final consumption by source, TJ | 2000–2023 |
| `transport_final_consumption_by_source_africa_2000_2023.csv` | Transport final consumption by source, TJ | 2000–2023 |
| `electricity_generation_by_source_africa_2000_2023.csv` | Electricity generation by 12 sources, GWh | 2000–2023 |
| `total_electricity_production_africa_2000_2023.csv` | Total electricity production, GWh | 2000–2023 |
| `total_energy_supply_per_gdp_ppp_africa_2000_2023.csv` | IEA's own intensity indicator, labelled "MJ per 2015 USD PPP" (values near 2,500 read as per thousand dollars) | 2000–2023 |

## Checks recorded in MSc-thesis

- **Reconciliation:** summed across sources, the four by-source files reconcile to the sector
  totals within 0.02%. Together they cover 92% of total final consumption in 2010; agriculture,
  fishing, other and non-energy use have no by-source file. Blank cells are read as zero.
- **Electricity:** the twelve generation sources sum to the total within 5 GWh in every year
  checked.
- **Africa TFC:** 17.6 EJ (2010), 20.1 EJ (2015), 21.3 EJ (2020), 23.6 EJ (2023).
- **Membership:** IEA "Africa" is the whole continent (54 countries; IEA *World Energy Balances
  2024* documentation pp. 35 and 46). AR6 R10 "Africa" is the same list plus Mayotte, Réunion and
  Western Sahara.

## How the carbon-intensity check uses them

Africa's biomass is "Biofuels and waste" summed over the four by-source files. Commercial final
energy is the sector total minus that biomass, so the 8% of final consumption without a by-source
file counts as commercial.

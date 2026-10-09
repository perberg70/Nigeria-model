# Nigeria energy balance — International Energy Agency

Chart exports from the IEA's Nigeria country pages, plus the IEA balance documentation.

- **Source:** https://www.iea.org/countries/nigeria
- **Retrieved:** 2026-08-06.
- **Licence:** CC BY 4.0. Required attribution:
  *IEA 2026; [chart title], https://www.iea.org/countries/nigeria, Licence: CC BY 4.0*

## Files

| File | Contents | Years |
|---|---|---|
| `total_final_consumption_by_fuel_2023.csv` | Total final consumption by 5 fuels, TJ | 2023 |
| `total_final_consumption_by_sector_2023.csv` | Total final consumption by 7 sectors, TJ | 2023 |
| `total_energy_supply_2023.csv` | Total energy supply by 6 carriers, TJ | 2023 |
| `electricity_generation_2023.csv` | Electricity generation by technology, GWh | 2023 |
| `domestic_energy_production_2000_2023.csv` | Production by carrier, TJ | 2000–2023 |
| `total_final_consumption_by_sector_2000_2023.csv` | Final consumption by sector, TJ | 2000–2023 |
| `electricity_final_consumption_by_sector_2000_2023.csv` | Electricity consumption by sector, TJ | 2000–2023 |
| `IEA_World_Energy_Balances_2024_documentation.pdf` | Definitions behind the balances (Nigeria notes on pp. 502–503) | 2024 edition |

## Key figures, 2023

- Total final consumption: 2,465,907 TJ (by sector; the by-fuel file gives 2,465,909 TJ).
- Electricity: 121,690 TJ, which is 4.93% of final consumption.
- Residential: 1,075,640 TJ, of which electricity 62,895 TJ (5.85%).
- Generation: 40,958 GWh — gas 31,640, hydro 9,107, solar 211.

## Caveats from the IEA's own Nigeria notes

- Back-up generator fuel and output *"may not be properly reported"* and *"may be substantial in
  Nigeria"* (p. 502). The generation figure contains no oil-fired or generator line.
- Oil-product data *"may not account for 'unofficial' oil products exports to neighbouring
  countries"* (p. 502).
- *"Electricity losses have been fixed at 15% starting from 2007"* (p. 503) — an assumption, not a
  measurement.

## Addendum 2026-10-09: two tables from a later IEA release

Copied on 2026-10-09 from MSc-thesis `02_literature/data/iea_nigeria_2023/` (commit `1c58444`),
at Per's request; byte-identical. Both tables were transcribed by hand in MSc-thesis on
2026-10-08 from the IEA Energy Statistics Data Browser ("Browse as tables", Nigeria, 2023). The
page stated "Last updated 28 Sep 2026" and Licence CC BY 4.0, with no edition name. An
independent subagent checked every cell against the live page the same day, with no mismatches.
No capture of the page is saved.

| File | Contents |
|---|---|
| `iea_nigeria_2023_final_consumption_by_fuel_and_sector_current_release.csv` | 2023 total final consumption, every sector by fuel (coal, oil products, gas, biofuels and waste, electricity), TJ. The only IEA source here that splits biomass by sector |
| `iea_nigeria_2023_electricity_generation_and_consumption_current_release.csv` | 2023 electricity balance, GWh: generation by technology, exports, own use, losses, final consumption by sector |

**They are a different release from the files above** and do not agree with them:

| 2023 | Files above | Current release |
|---|---|---|
| Total final consumption | 2,465,907 TJ | 2,450,511 TJ |
| Biofuels and waste | 1,233,622 TJ | 1,218,797 TJ |
| Electricity, final | 121,690 TJ | 119,530 TJ |
| Generation | 40,958 GWh | 40,975 GWh |

The two releases must not be mixed within one calculation. The 2000–2022 annual files have no
current-release counterpart.

**Which release this repository uses:**
- **Current release:** MSc-thesis moved its build script and prototype to the current release on
  2026-10-08. The sector-conversion analysis
  (`../scenario_compass_africa_r10/partial_adjustment/sector_conversion.py`) uses it.
- **Older release:** this repository's `build_nigeria_baseline.py` and prototype still use it, as
  do the time-series analyses.

Cite as: IEA 2026; *Energy Statistics Data Browser, Balances, Nigeria, 2023*,
https://www.iea.org/data-and-statistics/data-tools/energy-statistics-data-browser, Licence: CC BY 4.0
(as stated on the page).

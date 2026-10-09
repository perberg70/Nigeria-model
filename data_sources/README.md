# Data sources

Every external source used by `prototype/africa-prototype.html`. Retrieval details and
processing are described in each `data/<folder>/README.md`.

## Datasets

| Folder | Source | Used for | URL |
|---|---|---|---|
| `iiasa_ssp_nigeria` | IIASA SSP Scenario Explorer: IIASA-WiC POP 2025 population, OECD ENV-Growth 2025 GDP\|PPP | Population by SSP; income per head | https://ssp.apps.ece.iiasa.ac.at/ |
| `scenario_compass_africa_r10` | Scenario Compass, IMAGE 3.2 SSP2021, Africa R10 region | Baseline electrification, low-emission electricity share, final-energy intensity | https://scenariocompass.org/scenario-dashboard |
| `iea_nigeria_2023` | International Energy Agency, Nigeria country data 2023 (CC BY 4.0) | Final energy consumption by sector and fuel; electricity generation | https://www.iea.org/countries/nigeria |
| `global_carbon_budget_nigeria` | Global Carbon Budget via Our World in Data | Observed CO₂ emissions | https://ourworldindata.org/grapher/annual-co2-emissions-per-country |
| `worldbank_nigeria_gdp` | World Bank, World Development Indicators | GDP growth reference | https://datacatalog.worldbank.org/search/dataset/0037712/World-Development-Indicators |
| `wb_nigeria_clean_cooking` | World Bank EG.CFT.ACCS.ZS, Tracking SDG 7 (CC BY-NC 3.0 IGO) | Share of people mainly using clean cooking fuels | https://api.worldbank.org/v2/country/NGA/indicator/EG.CFT.ACCS.ZS |
| `nigeria_air_pollution` | WHO Global Health Observatory (AIR_11, AIR_41, AIR_42) | Household air-pollution deaths, 2021 | https://ghoapi.azureedge.net/api/ |
| `seforall_nigeria_etp` | SEforALL and Federal Government of Nigeria, Energy Transition & Investment Plan update (2024) | Renewable resource limits, back-up generator capacity, cooking-stove mix | https://www.seforall.org/system/files/2025-05/Nigeria-ETIP-u.pdf |
| `irena_nigeria_capacity` | IRENA electricity statistics | Generation by technology, cross-check | https://www.irena.org/Data |
| `owid_nigeria_electricity_trade` | Our World in Data, net electricity imports | Electricity balance | https://ourworldindata.org/grapher/net-electricity-imports.csv |
| `unsd_energy_nigeria` | UN Statistics Division energy statistics | Back-up generator fuel, cross-check | https://data.un.org/WS/rest/data/UNSD,DF_UNDATA_ENERGY/ |
| `nbs_petroleum_products` | Nigerian National Bureau of Statistics, Petroleum Statistics Report 2023 | Petrol and diesel volumes for the back-up generator estimate | https://www.nigerianstat.gov.ng/pdfuploads/Petroleum_Statistics_Repor_2023.pdf |
| `ipcc_2006_emission_factors` | IPCC 2006 Guidelines, Volume 2 (Energy) | CO₂ emission factors for fuels | https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/2_Volume2/ |
| `nigeria_regional_climate` | World Bank Climate Change Knowledge Portal, CMIP6 | State-level temperature and rainfall change | https://climateknowledgeportal.worldbank.org/download-data |
| `cckp_nigeria_heat` | World Bank Climate Change Knowledge Portal API | Hot-day counts | https://cckpapi.worldbank.org/cckp/v1/ |
| `tra420_ssp119_run` | Integrated assessment model run (FaIR climate module, pulse-based social cost of carbon) | Social cost of carbon and temperature path, SSP1-1.9 | see folder README |

## Datasets used only by experiment analyses (not by the prototype)

| Folder | Source | Used for | URL |
|---|---|---|---|
| `iea_africa_2023` | International Energy Agency, Africa region chart exports, 2000–2023 (CC BY 4.0); copied from MSc-thesis | Africa final energy for the carbon-intensity check | https://www.iea.org |
| `owid_co2_africa` | Our World in Data CO₂ dataset: Global Carbon Budget 2025, Maddison Project 2023 GDP, EIA/Energy Institute primary energy | African CO₂ by source, GDP and commercial primary energy for the carbon-intensity check | https://github.com/owid/co2-data |
| `iea_nigeria_2023` (two `*_current_release.csv` tables) | IEA Energy Statistics Data Browser, Nigeria 2023, "Last updated 28 Sep 2026" (CC BY 4.0); copied from MSc-thesis | Sector-by-fuel final energy and electricity balance for the sector-conversion analysis | https://www.iea.org/data-and-statistics/data-tools/energy-statistics-data-browser |

## Parameters from publications

| Parameter | Value | Source |
|---|---|---|
| Income elasticity of household solid-fuel use | −0.67 | Burke & Csereklyei (2016), Table 3 Panel C. https://doi.org/10.1016/j.eneco.2016.07.004 |
| Income elasticity of total energy | 0.36 (25th income percentile), rising by 0.13 per log unit of income (integrated: 0.36L + 0.065L²) | Burke & Csereklyei (2016), Table 5 col. 7 (10-year growth rates, 1960–2010). https://doi.org/10.1016/j.eneco.2016.07.004 |
| Value of a statistical life, Nigeria | US$0.485 million (2015 USD) | Viscusi & Masterman (2017). https://doi.org/10.1017/bca.2017.12 |
| Life-cycle CO₂ emission factors for electricity (hydropower, nuclear, wind, biomass, solar, gas) | ecoinvent v3.10.1, allocation cut-off by classification — a licensed (paid) database, not open data | Wernet et al. (2016). https://doi.org/10.1007/s11367-016-1087-8 |
| Diesel generator emission factor | 1.27 kg CO₂/kWh | Kambhampati et al. (2024), Table 8. https://doi.org/10.1088/1742-6596/2929/1/012008 |
| Population projections | IIASA-WiC | KC & Lutz (2017). https://doi.org/10.1016/j.gloenvcha.2014.06.004 |
| Scenario framework | SSPs | Riahi et al. (2017). https://doi.org/10.1016/j.gloenvcha.2016.05.009 |

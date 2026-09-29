# Nigeria Energy Transition & Investment Plan (2024 update) — chart data

The plan publishes its power, fuel-demand and cooking numbers only as bar charts. The CSVs here
are recovered from the chart geometry in the PDF and checked against figures the plan states in
its text.

- **Source:** *Nigeria Energy Transition & Investment Plan Update (2024)*, SEforALL and the
  Federal Government of Nigeria, 67 pp.,
  https://www.seforall.org/system/files/2025-05/Nigeria-ETIP-u.pdf
  (linked from https://www.seforall.org/our-work/initiatives-projects/energy-transition-plans/nigeria)
- **Retrieved:** 2026-08-29. The PDF is included unchanged.
- **Licence:** check SEforALL's terms of use before reuse.

## Files

| File | Contents | PDF page |
|---|---|---|
| `Nigeria-ETIP-u.pdf` | The source document | — |
| `etp_capacity_GW.csv` | Installed capacity by technology, 2020–2060, GW | 17 |
| `etp_generation_TWh.csv` | Generation by technology, 2020–2060, TWh | 18 |
| `etp_oil_BAU_demand_PJ.csv` | Oil demand by sector, business as usual, PJ | 22 |
| `etp_gas_BAU_demand_PJ.csv` | Gas demand by sector, business as usual, PJ | 22 |
| `etp_cooking.csv` | Cooking stoves by fuel (national, urban, rural, '000 units) and cooking fuel demand (PJ), 2020–2060 | 37–40 |
| `extract_etp_charts.py` | Extracts the capacity and generation charts | |
| `extract_etp_demand.py` | Extracts the oil and gas demand charts | |
| `extract_etp_cooking.py` | Extracts the cooking charts | |

Reproduce (requires `pypdf`):

```
python3 extract_etp_charts.py  Nigeria-ETIP-u.pdf .
python3 extract_etp_demand.py  Nigeria-ETIP-u.pdf .
python3 extract_etp_cooking.py Nigeria-ETIP-u.pdf .
```

Each extractor checks its output against statements in the plan's text and writes no CSV if a
check fails.

## Method

Every bar segment is a filled rectangle in the PDF. The extractors read each rectangle's colour
and height, calibrate heights against the axis labels, identify series by legend colour (or by
stack order on p.18, where two series share one colour), and assign bars to the nearest year
label. Heights are quantised to 0.75 pt, which sets the precision of every value.

## Validation

Capacity and generation (all within the 0.75 pt quantum):

| Check | Extracted | Stated in the plan |
|---|---|---|
| 2060 solar PV incl. decentralised | 445.6 TWh | 446 (p.18) |
| 2060 hydropower | 38.5 TWh | 39 (p.18) |
| 2060 biomass | 32.6 TWh | 32 (p.18) |
| 2060 hydrogen | 4.4 TWh | 4 (p.18) |
| 2060 gas capacity (on-grid + captive + embedded) | 11.9 GW | 11.8 (p.17) |
| 2060 hydrogen capacity | 35.8 GW | 36 (p.17) |
| 2060 biomass capacity | 6.0 GW | 6 (p.17) |
| 2060 total capacity excl. imports/exports | 277.2 GW | 277 (p.2, p.17) |

Cooking:

| Check | Extracted | Stated in the plan |
|---|---|---|
| Biofuels fuel demand 2060 | 36.8 PJ | "peaking at 36 PJ in 2060" (p.40) |
| LPG fuel demand peak | 59.0 PJ (2025) | "peaks at 58 PJ in the mid-20's" (p.40) |
| Rural electric stoves 2040 | 52.5% | ">50%" (p.39) |
| Rural biofuels 2060 | 39.8% | "40%" (p.39) |
| National = urban + rural | 99.7% (2020), 99.75% (2060) | consistency check |

## Notes for users

- The generation and capacity figures are chart readings, not published numbers.
- The `Imports` and `Exports` rows are not generation technologies and are excluded from totals;
  the plan's 277 GW total reproduces only without them.
- Some statements in the plan's text do not match its own charts, e.g. "209 GW solar in 2050"
  (p.17) is the 2060 value; the 2050 value is 173.6 GW.
- The cooking charts from 2025 onward are the plan's net-zero pathway, not a business-as-usual
  projection. The 2020 column is the starting position: 15,786 thousand LPG, 471 thousand electric,
  4,005 thousand biofuel and 24,032 thousand traditional-biomass stoves nationally.
- The 2020 electric stove bar is 1.5 pt tall, so its value (471 thousand) carries a range of about
  ±25%.
- Stove counts are not the same as people's main fuel: LPG plus electric stoves are 36.7% of
  stoves in 2020, while 18.9% of people mainly used clean fuel that year (World Bank / WHO).

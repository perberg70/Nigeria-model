# Colombia prototype — design v2 (canvas sources)

**Status:** reference canvas; its presentation is now applied to the runnable
`../colombia-prototype.html`. See `../README.md` for integration provenance and
retained model limitations. These artboards are not the runtime prototype. These files are the sources of a claude.ai
Design canvas that lays out the Colombia v2 prototype
(MSc-thesis `05_ui_design/prototypes/colombia-prototype-v2.html`, commit `92e6f31`) in the layout
of this repository's Nigeria prototype (`prototype/africa-prototype.html`, commit `1ca6791`):
top step bar, settings strip, fold-out information layers, result tiles and a department-level
regional map. The owner's canvas link is https://claude.ai/artifact/2YxRn7cQpoRG1w2ab9RgEq (private).

**Not published.** Each `.dc.html` file loads `./support.js`, which only the Design canvas
provides, so the files do not render as standalone pages. The Pages workflow copies
`../colombia-prototype.html`, the adapted boundary JSON and its map licence notice;
none of these artboards reaches the public site.

| File | Contents |
|---|---|
| `canvas.json` | Canvas index: artboard positions, sizes and titles |
| `proto.css` | Shared styles; tokens and fonts copied from the Nigeria prototype |
| `Main.dc.html` | Step 1 — country picker (South America map) |
| `Step2.dc.html` | Step 2 — four levers, "About this lever" folds, NDC and provenance sub-folds, optional source mix |
| `Step3.dc.html` | Step 3 — SSP cards |
| `Step4.dc.html` | Step 4 — emissions, social cost of carbon, electricity-generation emissions |
| `Step5.dc.html` | Step 5 — ambient and household air pollution |
| `Step6.dc.html` | Step 6 — national climate tiles, regional maps, five-pathway comparison |
| `RegionMap.dc.html` | Department map component, imported twice by step 6 and once by `InfoLayers` |
| `InfoLayers.dc.html` | The fold-out layers opened, including the Andean department drill-down |

## Where the numbers come from

Every value is copied from `colombia-prototype-v2.html` rendered at its default settings
(Colombia, SSP2-4.5, mitigation −60%, GDP growth 2.0%, electrification 40%, low-emission
generation 90%). Nothing recomputes: the step 2 sliders and step 3 cards respond on their own
artboard only. Treat any figure here as a copy of v2, not as an independent result.

Two deliberate departures from v2, both from the review below:

- **Step 6 region centres** come from the CCKP region ensemble (MSc-thesis
  `02_literature/data/south_america_regional_climate/cckp_cmip6_region_ensemble_2080-2099.csv`),
  so each region's centre and its 10th–90th range describe one distribution. v2 shows the median
  of the department medians beside the ensemble range. Values that change: temperature Amazonia
  2.04 → 2.00, Caribbean 2.09 → 2.06, Orinoquia 2.32 → 2.28, Pacific 2.07 → 1.99 °C; rainfall
  Amazonia −25 → −23, Andean +13 → +48, Caribbean −29 → −13, Orinoquia −28 → −36,
  Pacific +435 → +445 mm/yr.
- **Step 5 ambient interval** is WHO AIR_41's published 11,051–20,348 (MSc-thesis
  `02_literature/data/colombia_air_pollution/who_air41_colombia_2021.csv`), not v2's 11,050–20,353,
  which comes from fixed multipliers.

## Department map

- **Source:** geoBoundaries gbOpen COL ADM1, simplified release (boundary ID
  `COL-ADM1-13589884`; source OpenStreetMap, Wambacher; boundary year 2017; built 2023-12-12),
  licence ODbL 1.0 (© OpenStreetMap contributors), downloaded 2026-10-16. The mainland drawing
  holds 31 departments and Bogotá D.C.
- **Method:** `regional_climate.zone_geometry.build_zone_map` from this repository (commit
  `1ca6791`), simplification tolerance 0.06°; polygons under 0.01 square degrees dropped;
  San Andrés, Providencia y Santa Catalina excluded from the mainland drawing and shown as an
  inset; coordinates rounded to 0.1 viewBox units. Departments are grouped into the five natural
  regions using the department-to-region table in v2 (`UNIT_CLIMATE`). Two names were joined by
  hand: "Bogota Capital District" → "Bogotá, D.C." and "Quindío" → "Quindio".
- **Frozen geometry now reproducible.** The original geographic boundary file and
  simplification script remain unavailable. The integration preserves the canvas SVG
  paths in `../department-boundaries.json` and embeds them with
  `scripts/build_department_map.py --config prototype/colombia/map-config.yaml`. This
  reproduces the snapshot, not its original geographic simplification.
- **Licence and data access.** The adapted boundary collection is distributed as a
  Derivative Database under [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/),
  © OpenStreetMap contributors, via geoBoundaries (source: OpenStreetMap, Wambacher).
  The complete machine-readable dataset is [../department-boundaries.json](../department-boundaries.json),
  including mainland paths and schematic inset coordinates. It is also deployed
  alongside the runtime prototype, with a free download link on each map.
  [../MAP-LICENSE.txt](../MAP-LICENSE.txt) records scope, source links, alterations
  and the complete-data offer. This addresses distribution in this public repository
  as well as the eventual Pages site; it does not relicense the surrounding code
  or independently sourced model data.

## Inconsistencies recorded when the canvas was created

The runtime import uses a newer source commit that already fixes the regional
centres, WHO interval and valuation disclosures. The earlier energy calibration
remains explicitly distinguished from the revised BECO reference marks. The list
below is the historical canvas review, not a list of current runtime defects.

- Step 4's "What the three lines are" fold in v2 still describes the older "pressure curve"
  method (a normalized final-energy-intensity factor). The paragraph beside it describes the
  current one: the paired R5 carbon index with reported biomass CCS added back. The design's fold
  uses that current wording.
- v2's health and uncertainty panels give US$3.0m per statistical life; its result tiles
  compute at US$1.67m.
- v2's step 2 slider references (17.8% electrification, 76.4% low-emission) come from an
  earlier UPME edition that is not archived. The design recomputes both marks from the revised
  UPME workbook `BECO_VER_01_1975_2024.xlsx` (SHA-256 `6cd7674e…`, sheet `BECO_Datos 2006-2024`):
  18.9% electrification in 2024 (282,640 / 1,498,690 TJ) and 70.3% low-emission grid generation
  in 2024 (hydro, wind and solar 208,355 / 296,486 TJ of grid plants; 76.6% in 2023). Step 5's
  results were computed in v2 from the older values and are not yet recomputed.
- v2 records a value-per-life range (US$1.21m–7.81m) and says it is disclosed on screen, but never
  renders it. The design shows it.
- Two sources behind displayed figures are not archived in either repository: the NDC 3.0 PDF
  (the design labels its figures "as quoted in v2") and the earlier UPME edition behind v2's
  1,528,901 TJ for 2023 (the revised workbook gives 1,497,259 TJ). The design no longer depends
  on that edition.

## Review

An independent `thesis-gap-flagger` review ran on 2026-10-16. Its triage is the 2026-10-16
`thesis-gap-flagger` entry in MSc-thesis `09_project_management/review_log.md`; this revision
carries the accepted fixes.

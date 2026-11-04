# Colombia prototype v2

The runnable `prototype/colombia-prototype.html` combines the MSc-thesis v2 model with the
Colombia v2 design canvas already in PR #24. It is self-contained: no build tool,
canvas runtime, external JavaScript, fonts, or data downloads are needed to use it.

## Sources and scope

- Runtime and embedded model data: `perberg70/MSc-thesis`, commit
  `e25546bbd08e5b3ed527fc42c0f6a3b66317cb5e`,
  `05_ui_design/prototypes/colombia-prototype-v2.html`.
- Presentation: the Colombia v2 design canvas, PR #24 head
  `4530918248340e8cead94268961ebee326d199fe`. Its artboards were committed here as
  `prototype/colombia/design-v2/` and moved on 2026-11-04 to `perberg70/MSc-thesis`,
  `05_ui_design/mock-ups/colombia-v2-design-canvas/`, which holds the thesis's UI design
  material; they were never part of the published site.
- The applied design includes the top step bar, live settings strip, expandable
  lever/source/uncertainty explanations, result tiles, department maps and inline
  regional drill-down. The canvas files remain reference artboards, not runtime pages.
- Post-import fixes, applied here and in the source on 2026-11-04 (MSc-thesis
  `086a202`, from the Codex review of PR #24): a source group whose every source is
  pinned now totals 100% (previously a shortfall counted as emission-free), and chart
  tooltips use each chart's own series names and unit (step 5 showed deaths as "Mt").
- The imported calculations and embedded data are preserved. This is a deployment
  snapshot, not a migration of the thesis repository's Python model or raw research
  datasets. Future model updates should come from that source with its provenance.

The newer source already corrects the WHO AIR_41 interval, value-of-statistical-life
explanations and regional ensemble medians that the canvas README flagged. These
fixes are retained. Canvas numbers are not pasted over computed results.

## Deployment

`.github/workflows/deploy-pages.yml` assembles the existing Nigeria page and this
file into `_site/nigeria/index.html` and `_site/colombia/index.html`. The landing
page links to both. A missing Colombia entry point now fails assembly rather than
silently publishing a broken link. The complete adapted boundary JSON and
map licence notice (`data/colombia_department_boundaries/`) are also deployed
beside the prototype, under the same file names the page links to. No design-canvas
artboards are deployed.

After PR #24 is merged to `main`, its push triggers the Pages workflow. The expected
URL is <https://perberg70.github.io/Nigeria-model/colombia/>. This change does not
merge the PR or publish a live deployment itself.

For a local preview, open `prototype/colombia-prototype.html` in a browser, or run
`python -m http.server 8000` at the repository root and visit
`http://localhost:8000/prototype/colombia-prototype.html`. In a local preview the maps'
"complete adapted data" and licence links point beside the page and do not resolve; on the
published site they do. The PDF and CSV exports link to the published copies.

## Navigation and export alignment with Africa

The interaction reference is `prototype/africa-prototype.html` at Nigeria-model
commit `1ca6791eddbf3a35e558b1d6c34eca9cd4460d69`.

- Screens 2–6 have a labelled Back button leading to the preceding screen.
- The final screen's “Save this outcome” panel offers “Save as PDF” and
  “Download data (CSV)”, matching Africa. PDF opens a printable report and invokes
  the browser's Print / Save as PDF dialog; a blocked popup falls back to an
  in-page report.
- Both formats capture the current country, SSP, drivers, resolved source mix,
  all three results screens, assumptions, caveats and provenance. The PDF includes
  charts and maps; CSV includes displayed result tiles and data tables.
- Exports read the current view outputs rather than maintaining separate model
  calculations. Ambient and household health effects remain separate, with their
  overlap warning. Map attribution and the adapted-data link remain in exports.
- “Explore or change your pathway again” returns to the pathway controls.
  Open explanation panels survive control changes on the same screen.

Country-specific results remain Colombia's: Nigeria's hot-day counts, generator
model and clean-cooking target are not transplanted into the Colombia report.

## Map snapshot

The department maps embed a frozen snapshot of the design canvas's 32 mainland
department/district outlines (geoBoundaries gbOpen COL ADM1, ODbL 1.0). Its provenance,
licence, the regeneration command and the upstream gap are in
`data/colombia_department_boundaries/README.md`.

## Retained model limitations

- Revised BECO 2024 context marks follow the canvas: electricity is 18.9% of final
  energy (282,640 / 1,498,690 TJ), and hydro/wind/solar are 70.3% of grid generation
  (208,355 / 296,486 TJ). Source: UPME `BECO_VER_01_1975_2024.xlsx`, sheet
  `BECO_Datos 2006-2024`, as documented by the canvas.
- The health model remains on its inherited earlier energy basis: 17.8%
  electrification and 76.4% low-emission generation. Its earlier UPME edition is
  not archived here. The context-marker disclosures explicitly distinguish these
  values from the revised markers and from the electricity module's Ember 2024
  mix. Updating the health calibration is separate model work.
- Other countries retain the source prototype's illustrative/transferred profiles
  and disclosures. The Colombia model's source limitations, uncertainty conventions,
  and SCC proxies remain visible in the interface.

## Verification

```sh
python -m py_compile scripts/build_department_map.py tests/test_colombia_prototype.py
ruff check .
ruff format --check .
# Requires Playwright and Chromium (CHROMIUM_PATH selects it); skipped when missing.
pytest --basetemp=./.pytest_tmp -m browser
```

The browser check covers all six screens at desktop/mobile widths, a live keyboard
slider change, baseline isolation, all five SSPs, department drill-down, country
switching, labelled back navigation, disclosure persistence, actual CSV/PDF
exports and the popup-blocked print fallback, as well as browser errors. During integration the imported model was also
compared with the pinned MSc-thesis source across five SSPs and three driver
configurations: emissions, power, cumulative emissions, damage, regional climate
and health inputs were unchanged.

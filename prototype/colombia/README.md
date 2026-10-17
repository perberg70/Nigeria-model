# Colombia prototype v2

The runnable `colombia-prototype.html` combines the MSc-thesis v2 model with the
Colombia v2 design canvas already in PR #24. It is self-contained: no build tool,
canvas runtime, external JavaScript, fonts, or data downloads are needed to use it.

## Sources and scope

- Runtime and embedded model data: `perberg70/MSc-thesis`, commit
  `e25546bbd08e5b3ed527fc42c0f6a3b66317cb5e`,
  `05_ui_design/prototypes/colombia-prototype-v2.html`.
- Presentation: `design-v2/` in `perberg70/Nigeria-model`, PR #24 head
  `4530918248340e8cead94268961ebee326d199fe`.
- The applied design includes the top step bar, live settings strip, expandable
  lever/source/uncertainty explanations, result tiles, department maps and inline
  regional drill-down. The canvas files remain reference artboards, not runtime pages.
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
silently publishing a broken link. No design-canvas files are deployed.

After PR #24 is merged to `main`, its push triggers the Pages workflow. The expected
URL is <https://perberg70.github.io/Nigeria-model/colombia/>. This change does not
merge the PR or publish a live deployment itself.

For a local preview, open `colombia-prototype.html` in a browser, or run
`python -m http.server 8000` at the repository root and visit
`http://localhost:8000/prototype/colombia/colombia-prototype.html`.

## Map snapshot and reproducibility

`department-boundaries.json` preserves the canvas's 32 mainland department/district
paths in SVG coordinates, grouped into the five natural regions. San Andrés,
Providencia y Santa Catalina is represented by the labelled inset. The geometry
comes from geoBoundaries gbOpen COL ADM1, boundary ID `COL-ADM1-13589884`, with
OpenStreetMap/Wambacher provenance (2017 boundaries; canvas retrieval 2026-10-16).
Geometry is distributed under ODbL 1.0, © OpenStreetMap contributors. Attribution
and the licence link are also displayed on each map.

Regenerate the embedded snapshot from the repository root:

```sh
python scripts/build_department_map.py --config prototype/colombia/map-config.yaml
```

The script requires explicit configuration and reads only the named boundary file
and prototype. Repeated runs reproduce the embedded block byte for byte.

**Upstream gap:** the original geographic boundary file and one-off simplification
script are unavailable. This build reproduces the frozen canvas geometry, not the
original geographic simplification. Do not describe the snapshot as GeoJSON or as
a newly validated administrative dataset. Map colours represent regional estimates;
select a region for the separate department-level CCKP estimates.

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
python -m py_compile scripts/build_department_map.py tests/browser/colombia_smoke.py
ruff check .
ruff format --check .
# Requires Playwright and Chromium; optionally set CHROMIUM_PATH.
python tests/browser/colombia_smoke.py
```

The browser check covers all six screens at desktop/mobile widths, a live keyboard
slider change, baseline isolation, all five SSPs, department drill-down, country
switching and browser errors. During integration the imported model was also
compared with the pinned MSc-thesis source across five SSPs and three driver
configurations: emissions, power, cumulative emissions, damage, regional climate
and health inputs were unchanged.

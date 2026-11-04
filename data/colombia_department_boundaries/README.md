# Colombia department boundaries — design-canvas snapshot

Department outlines drawn by the Colombia prototype's regional maps
(`prototype/colombia-prototype.html`, block `DEPARTMENT_MAP`).

| File | Contents |
|---|---|
| `department-boundaries.json` | 32 mainland department/district paths in SVG display coordinates, their names, five-region grouping and viewBox; San Andrés inset coordinates |
| `MAP-LICENSE.txt` | Scoped ODbL 1.0 notice, upstream links and the complete-data offer |

Both files are also published beside the prototype at
<https://perberg70.github.io/Nigeria-model/colombia/>, under the same names the page links to.

## Provenance and reproduction

`department-boundaries.json` preserves the canvas's 32 mainland department/district
paths in SVG coordinates, grouped into the five natural regions. San Andrés,
Providencia y Santa Catalina is represented by the labelled inset. The geometry
comes from geoBoundaries gbOpen COL ADM1, boundary ID `COL-ADM1-13589884`, with
OpenStreetMap/Wambacher provenance (2017 boundaries; canvas retrieval 2026-10-16).
Geometry is distributed under ODbL 1.0, © OpenStreetMap contributors. Attribution
and the licence link are also displayed on each map, together with a free download
of the complete adapted boundary dataset. See [MAP-LICENSE.txt](MAP-LICENSE.txt)
for the scoped ODbL licence, upstream links and data-access offer. We treat the
adapted boundary collection as a Derivative Database and distribute it under
ODbL 1.0; application code and independent model data are outside that notice.

Regenerate the embedded snapshot from the repository root:

```sh
python scripts/build_department_map.py --config config.yaml
```

The script reads `colombia_department_map` in `config.yaml` (boundary file, expected
unit count, prototype) and nothing else. Repeated runs reproduce the embedded block byte for byte.

**Upstream gap:** the original geographic boundary file and one-off simplification
script are unavailable. This build reproduces the frozen canvas geometry, not the
original geographic simplification. Do not describe the snapshot as GeoJSON or as
a newly validated administrative dataset. Map colours represent regional estimates;
select a region for the separate department-level CCKP estimates.

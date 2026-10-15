# Zone-map borders: audit and assumptions (2026-10-15)

Nigerian researchers reported that the geopolitical-zone borders in the prototype's regional
climate maps did not match reality. They were right. This note records what was wrong, what was
not, and the assumptions behind the regional figures.

## What was wrong: the drawn borders

The two maps ("Regional temperature change", "Regional yearly rainfall change") did not draw
real boundaries. Each zone was the Voronoi cell around one hand-placed point, clipped to the
national outline (the removed `regionalAreaCell`, with `x`/`y` points hand-pasted into
`regionalClimate`, as of commit `59019f6`). The text called the shapes "schematic", but they
were wrong enough to mislead.

**Method.** The old points were fractions of the outline's padded bounding box: North Central
(.49, .49), North East (.72, .25), North West (.27, .22), South East (.67, .69), South South
(.49, .84), South West (.25, .70). They were placed in degrees by matching the outline's bounding
box to that of the GRID3 2022 state file in this repository
(`data/nigeria_regional_climate/geoBoundaries-NGA-ADM1_simplified.geojson`). The aspect ratios
differ by 1.6%, so expect positional error of a few hundredths of a degree near edges. Each state
was then sampled on a 0.04° grid (cos-latitude weighted), and every sample was assigned to its
nearest point, which is the same as asking which Voronoi cell it fell in. A state's "centre" is
the area-weighted mean of its samples. The percentages below are shares of sampled area, not of
states. The audit ran as a one-off script that is not committed; the coordinates above and the
boundary file are enough to repeat it.

Results:

- **15 of the 37 states** (36 states and the FCT) had their centre drawn in the wrong zone.
- **The drawn South East contained none of the real South East.** Its point mapped to about
  11.05°E, 6.89°N, in Taraba on the Cameroon border. The drawn area was 66% Taraba, 24% Adamawa
  and 10% Benue.
- Share of each drawn zone that belonged to its own states: North Central 55%, North East 88%,
  North West 76%, South East 0%, South South 55%, South West 41%.

| State | Official zone | Drawn as (centre) |
|---|---|---|
| Abia, Ebonyi, Enugu, Imo | South East | South South |
| Anambra | South East | South West |
| Delta, Edo, Bayelsa | South South | South West |
| Kwara, Kogi | North Central | South West |
| Niger | North Central | North West |
| Kaduna, Kano | North West | North Central |
| Jigawa | North West | North East |
| Taraba | North East | South East |

Partly misdrawn, but with the centre in the right zone: Bauchi (55% drawn as North Central),
Adamawa (46% South East) and Benue (50% split between South East and South South).

Moving the six points to the true zone centroids was tested and rejected, because it still
misplaced the centres of 7 states (same
method; centroids by area). Voronoi cells cannot follow the shape of the South East or South South.

**Fix.** The maps now draw every state from the GRID3 boundaries and colour it by its zone,
with heavier lines on zone borders (`scripts/build_zone_map.py`, `docs/regional_climate.md`).

## What was right: the numbers

- **State-to-zone grouping.** `data/nigeria_regional_climate/admin1_units.yaml` puts every
  state in the conventional six-zone grouping (checked by hand on 2026-10-15): North Central (Benue, FCT, Kogi, Kwara, Nasarawa, Niger, Plateau);
  North East (Adamawa, Bauchi, Borno, Gombe, Taraba, Yobe); North West (Jigawa, Kaduna, Kano,
  Katsina, Kebbi, Sokoto, Zamfara); South East (Abia, Anambra, Ebonyi, Enugu, Imo); South South
  (Akwa Ibom, Bayelsa, Cross River, Delta, Edo, Rivers); South West (Ekiti, Lagos, Ogun, Ondo,
  Osun, Oyo).
- **Values.** Zone values, legend values and the state tables behind each click use this
  grouping, so the drawing error did not reach them. The prototype's copies are hand-pasted from
  the CSVs (`docs/ssp_baseline.md`), and this audit did not re-check them. Only the shapes were wrong, so a reader could pick the wrong
  territory for a zone (for example, read Taraba as South East).

## Assumptions behind the regional figures

1. **Source.** The state values are World Bank CCKP CMIP6 (`cmip6-x0.25`) Admin-1 anomalies for
   2080–2099 against 1995–2014 (retrieved 2026-08-21/22). CCKP computes them on its own Admin-1
   boundaries, not GRID3. The size of the difference between the two sets has not been measured
   [GAP]. The new drawing
   changes no number.
2. **Aggregation.** A zone's value is the unweighted **median of its states**, taken per climate
   model. The displayed median and 10th–90th percentiles are then taken across models. It is not
   area-weighted (Niger State counts as much as Lagos), not population-weighted, and not an
   official CCKP zonal product.
3. **Model spread, not probability.** The p10–p90 range is the spread across CMIP6 models. CCKP
   publishes no individual-model runs for SSP1-1.9, so that pathway shows a median only.
4. **Zones are political, not climatic.** The six geopolitical zones are a political and
   administrative convention. A zone median can hide strong gradients inside the zone; North
   East, for example, spans 6.4°N to 13.7°N, and North Central spans 6.4°N to 11.4°N (computed from
   the GRID3 file above). Clicking a zone lists
   the value for each of its states.
5. **Labels.** "Abuja" is CCKP's label for the Federal Capital Territory, and "Nassarawa" is
   CCKP's spelling of Nasarawa. The boundary file is joined on ISO 3166-2 codes, so the
   spelling difference has no effect.
6. **Map drawing.** The projection is equirectangular, with longitude scaled by the cosine of
   the mid-latitude. Shared borders are simplified to about 0.02°, roughly 2 km. This is fine
   for a 230-pixel map but is not a cartographic product.

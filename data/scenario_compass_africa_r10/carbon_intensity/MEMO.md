# Does Nigeria's carbon intensity match Africa's?

Branch `experiment/partial-adjustment`, 2026-10-09. Per's question: the energy systems of
Nigeria and Africa R10 do not match, but perhaps their carbon intensities do. If they did, an R10
carbon-intensity path could be a candidate for transfer. The baseline transfers none
(`../build_nigeria_baseline.py` docstring).

- **Script:** `carbon_intensity_check.py`.
- **Output:** `carbon_intensity_output.txt`, which uses only data held in this repository.
- **Earlier work:** the 2026-09-18 backtest (MSc-thesis `03_models/`) compared one metric over
  one window (CO₂ per final energy, 2010→2020: R10 −7.7%, Nigeria −18.0%), using IMAGE's own
  calibration rows as R10's history. This memo uses observed data for Africa and splits the
  question into levels, trends and co-movement.

## Short answer

**Levels: no.** On every metric Nigeria sits below the rest of Africa:

| Metric | Nigeria as a share of rest of Africa (excl. South Africa) |
|---|---|
| CO₂ per unit of GDP (fuel combustion only) | 0.5–0.6× |
| CO₂ per unit of commercial energy (energy without traditional biomass) | about 0.85× (closest); from the like-for-like comparison marked `[Pending]` below |

**Trends since 2010: roughly yes, against Africa without South Africa.**

- **The trends are close.** Both fall at about 0.5–1.2% a year. The year-to-year changes
  correlate moderately (r ≈ 0.55–0.63 over 12 years).
- **Whole Africa does not fit.** Its CO₂/GDP falls faster (−1.5%/yr), pulled by South Africa's
  coal.
- **Before 2010 nothing matches.** Nigeria's numbers are dominated by flaring cuts and by a data
  break (below).

**IMAGE's 2010–2020 rows reproduce observed Africa's CO₂ per final energy, but not its CO₂/GDP.**
The CO₂/GDP failure is the known IMAGE GDP artifact.

**IMAGE's forward paths decarbonise much faster than history**, except SSP3 and SSP5:

- **SSP2-4.5:** commercial-energy carbon intensity falls 1.8% a year to 2050, against about 1% a
  year observed.
- **Coal:** about a fifth of that decline is coal, which Nigeria does not have.

## Data and two breaks that decide the reading

- **Sources:** CO₂ by source (Global Carbon Budget 2025), GDP (Maddison 2023) and commercial
  primary energy (EIA/EI) for all 54 African countries come from Our World in Data
  (`../../owid_co2_africa/`). Nigeria's final energy comes from the IEA (`../../iea_nigeria_2023/`).
- **Nigeria's commercial final energy** is IEA total final consumption minus biomass. Biomass is
  estimated as biofuels-and-waste production × the 2023 final/supply ratio (0.899).
- **Two "rest of Africa" regions** keep Nigeria out of its own comparison:
  - Africa without Nigeria and South Africa;
  - Africa without Nigeria.
- **Break 1, data.** Nigeria's oil CO₂ more than doubles from 2009 to 2010 (27 → 59 Mt), while
  commercial final energy rises 19%. Every Nigerian intensity jumps that year, so trends are fitted
  separately for 2000–2009 and 2010–2022/23.
- **Break 2, real.** Flaring fell from 53% of Nigeria's CO₂ in 2000 to 8% in 2023 (51 → 11 Mt). It
  drives most of Nigeria's pre-2010 decline and has no counterpart in a regional fuel-use path.
  "Combustion CO₂" below excludes flaring and cement.
- **GDP source.** Maddison grows Nigeria's GDP about 11–14% a year in 2005–2010, against WDI's
  6–8%. Nigeria's CO₂/GDP trend after 2010 is −1.1%/yr on Maddison and −0.6%/yr on WDI.

## Results

**What the CO₂ is made of (share of total), 2023:**

| | Coal | Oil | Gas | Flaring | Cement |
|---|---:|---:|---:|---:|---:|
| Nigeria | 3% | 51% | 29% | 8% | 8% |
| Africa excl. South Africa | 7% | 50% | 30% | 5% | 8% |
| Africa | 29% | 39% | 21% | 4% | 6% |

Without South Africa, the rest of the continent's CO₂ looks like Nigeria's today. In 2000 it did
not, because of Nigeria's flaring (53% of its CO₂ that year).

**Trends after the break, 2010–2022/23 (fitted, %/yr):**

| Metric | Nigeria | Africa excl. ZA+NGA | Africa |
|---|---:|---:|---:|
| CO₂ / GDP | −1.1 (WDI GDP: −0.6) | −0.8 | −1.5 |
| Combustion CO₂ / GDP | −0.2 | −0.7 | −1.6 |
| Combustion CO₂ / commercial energy | −1.8 (final energy) | −0.5 (primary) | −0.9 (primary) |

Over 2011–2022/23 the trends are −0.7 vs −0.9 (CO₂/GDP) and −1.2 vs −0.7 (commercial energy),
with r = 0.55–0.63. Nigeria's commercial-energy level is final energy and the regions' is primary,
so compare these as rates, not levels.

**Levels.** Combustion CO₂ per GDP: Nigeria is 0.48–0.60 of Africa excl. ZA+NGA over 2010–2022.

**`[Pending]` Like-for-like final energy for Africa.** IEA Africa final consumption is held in
the MSc-thesis repository (`02_literature/data/iea_africa_2023/`), not here. Run the script with
`--iea-africa <that folder>` for the final-energy rows of sections B and C, and the observed
final-energy rows in section D. Copying those files into this repository is Per's decision.

**IMAGE's 2010–2020 rows against observed Africa:**

| | IMAGE 2010→2015 | Observed 2010→2015 | IMAGE 2015→2020 | Observed 2015→2020 |
|---|---:|---:|---:|---:|
| CO₂ | +9.3% | +9.8% | +10.2% | +2.5% |
| CO₂ / GDP | −32.8% | −9.5% | −2.3% | −6.8% |

- **CO₂/GDP:** IMAGE fails, for the same GDP reason found on 2026-09-18.
- **CO₂ per final energy:** IMAGE tracks observed Africa closely. This needs the `--iea-africa`
  data; see the session report.
- **2015→2020:** the CO₂ gap reflects 2020, a COVID year that IMAGE's 2021 release does not
  contain.

**What an R10 path would carry (IMAGE, change 2020→2050, fossil-and-industry CO₂ per commercial
final energy):**

| Marker | Change by 2050 | %/yr | Without coal | %/yr | Coal share of CO₂, 2020 → 2050 |
|---|---:|---:|---:|---:|---|
| SSP1-1.9 | −95% | −9.5 | n/a | | net CO₂ near zero |
| SSP1-2.6 | −68% | −3.7 | −64% | −3.4 | 32% → 25% |
| SSP2-4.5 | −43% | −1.8 | −34% | −1.4 | 32% → 22% |
| SSP3-7.0 | −24% | −0.9 | −23% | −0.9 | 32% → 31% |
| SSP5-8.5 | −18% | −0.7 | −19% | −0.7 | 32% → 33% |

- **The "without coal" column** removes primary coal × 94.6 kg/GJ. It has no CCS adjustment, so
  it understates the remainder where coal is captured.
- **Per total final energy, the paths differ:** SSP2 falls only 15% by 2050, and SSP3 and SSP5
  rise. Biomass leaving the denominator pushes this measure up, so it mixes fuel switching
  (`../partial_adjustment/SECTOR_CONVERSION.md`) with decarbonisation.

## What this means for a transfer

1. **Levels never transfer.** Every comparison here is a relative-change question, as the
   baseline's other R10 factors already are.
2. **The candidate metric is combustion CO₂ per commercial final energy.** It is the closest match
   in level, its trends match the rest of Africa since 2010, and it keeps biomass switching out of
   the carbon-intensity factor. The sector-conversion work handles biomass switching separately.
3. **Use the path without coal, not R10's raw path.** In SSP2-4.5, coal is about 8 of the 43
   points by 2050.
4. **Flaring needs its own Nigeria-specific term.** It is 8% of Nigeria's CO₂ today and was the
   main reason for the pre-2010 decline. An energy-use intensity path does not represent it.
5. **The scenario pace is a scenario assumption, not a historical match.**
   - SSP3-7.0 and SSP5-8.5 decline at about the historical pace (−0.7 to −0.9%/yr).
   - SSP2-4.5 is about 1.5–2× history.
   - SSP1 is a policy pathway.

   History can show that Nigeria has co-moved with the rest of Africa. It cannot show that Nigeria
   will follow a faster-than-history scenario.
6. **Interaction with the sliders.** The electrification and low-emission sliders already change
   power-sector CO₂. A transferred commercial-energy intensity would also include R10's power
   decarbonisation. It should apply only to direct fuel use, or the power sector is counted
   twice. **Per's decision**, together with the open choices in `SECTOR_CONVERSION.md`.

## Limits

- **The window is short:** 12–13 annual changes after the 2010 break. Trends within about
  0.5 pt/yr of each other are not distinguishable, and r ≈ 0.6 on 12 points is weak evidence.
  Common shocks (2020) raise r.
- **Estimated biomass:** Nigeria's commercial final energy uses estimated biomass, so the
  charcoal-conversion share is held at its 2023 value.
- **Mixed denominators:** the regional commercial-energy rows here are primary energy, Nigeria's
  are final. Rates are comparable; levels are not.
- **Data quality:** Maddison GDP is missing for four countries. Nigeria's EIA primary energy is not
  used because it is erratic.
- **IMAGE:** its CO₂ is fossil-and-industry (total minus AFOLU), its final energy runs 9–17% above
  the IEA's, and its coal CO₂ is approximated.

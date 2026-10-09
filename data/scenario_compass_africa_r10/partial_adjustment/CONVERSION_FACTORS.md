# Unit conversions for the Table 5 coefficients

> **Pointer (2026-10-09):** this memo covers unit, time-scale and boundary conversions of the
> paper's coefficients. The physical conversion factors that change as end uses move from fuels
> to electricity are explored in `SECTOR_CONVERSION.md`.

Branch `experiment/partial-adjustment`, 2026-10-09. Asks which conversion factors the variant in
`partial_adjustment_variant.py` needs to carry Burke & Csereklyei (2016) Table 5 into the
prototype's data, and what each one does to the results. Script: `conversion_factors.py`
(imports the variant and leaves it unchanged). Full output: `conversion_factors_output.txt`.
Page references are to CAMA Working Paper 45/2016, the version held in MSc-thesis
`02_literature/`.

## What the coefficients were estimated on

| Quantity | Paper (Table 5, Eq. 5) | Variant |
|---|---|---|
| Time | 10-year average annual log growth (difference of logs divided by 10), regressed on decade-start levels (p. 8; Table 5 notes) | annual grid, 2023–2100 |
| Income | Penn World Table 7.1, PPP-converted GDP per head, chain series, 2005 prices (p. 10; App. A1). For the ETA interaction it is demeaned over the 463-observation sample (Table 5 notes) | OECD ENV-Growth 2025 GDP\|PPP, USD_2015, for Nigeria; IMAGE 3.2 GDP\|PPP, USD_2010, for R10 |
| Energy | total **primary** energy supply, kgoe per head (App. A1, A3) | IEA total **final** consumption, TJ, for Nigeria; IMAGE Final Energy, EJ, for R10 |

Each unit difference falls into one of three cases:

- **Cancels**: a pure unit factor. It drops out of the log differences and the alpha calibration.
- **Matters**: a level conversion that changes the result.
- **Not a unit question**: a boundary difference, where no single factor converts one quantity into the other.

## Short answer

| Conversion | Needed? | Recommendation | Effect on 2100 variant/current |
|---|---|---|---|
| TJ ↔ kgoe (1 kgoe = 41.868 MJ) | No: cancels | Do not apply | 0 (checked: ≤ 1e-15) |
| USD_2015 ↔ USD_2010/2017 ↔ 2005 I$, as a price-base factor | No for growth terms; **wrong tool** for the level | Do not apply | 0 for growth terms |
| Decade κ, θ → annual λ | Optional | Keep λ = −κ = 0.023 | at most 0.005 |
| Income **level** for the ETA term | **Yes** | Splice into PWT 7.1 units, then compute the sample mean | 0.944–0.979 → up to 0.976–0.994 |
| Primary → final boundary | Yes, as a re-weighting | Per's decision. If applied: to Nigeria *and* the region, using the terms both routes agree on | 0.98–1.28 depending on route; 0.67–0.86 if Nigeria only |

## A. Time scale: decade coefficients → annual closing speed

In Eq. 5 a level gap is retained at 1 + 10κ = 0.770 per decade. Three annual closing speeds are
possible:

| Conversion | λ (/yr) | Retention per decade | Half-life |
|---|---:|---:|---:|
| linear, −κ (variant) | 0.02300 | 0.792 | 29.8 yr |
| geometric, 1 − (1 + 10κ)^0.1 | 0.02580 | 0.770 | 26.5 yr |
| log, −ln(1 + 10κ)/10 | 0.02614 | 0.767 | 26.2 yr |

The geometric value reproduces the decade decay exactly. Even so, it tracks the decade recursion
*less* well than the linear value:

| | linear | geometric |
|---|---|---|
| Test 1, largest gap | 0.0060 log points | 0.0067 log points |
| Test 2, 2063–2073 window | −0.002 | +0.009 |

The annual grid already front-loads each decade's response (see `MEMO.md`, Tests 1 and 2), and
the slower linear λ happens to offset that. Scenario ratios move by at most 0.005.

**Keep λ = −κ.** θ needs no separate conversion: it scales with λ, and b = −θ/κ = 0.696 is
unchanged.

Three things need no time conversion at all:

- **β and η** are ratios of growth to growth.
- **The decade dummies** are already in annual-growth units.

One timing difference remains, and it is small. The annual code evaluates η at last year's income;
the paper holds it at decade-start income for ten years. For a decade of growth at x̄ per year,
the annual β averages about 0.13 × 5x̄ higher, which is +0.016 at 2.5 % per year. This is part
of the front-loading.

## B. Income level: the one conversion that matters

**Where the level enters.** β·Δg and the target slope use log *differences*, and α absorbs the
level. So any constant price-base factor cancels; section D confirms this numerically. Income
enters as a *level* only through the ETA term:

```
d = ln Y_NGA − mean₄₆₃(ln Y_t−10),   in PWT 7.1 units
```

The variant assumes d = −0.923, which puts Nigeria at the 25th percentile and gives β₀ = 0.36.

**A price-base factor cannot do this conversion.**

- Nigeria's 2010 GDP per head is US$4,759 in the OECD series (USD_2010 PPP).
- Penn World Table 7.1 gives $1,695 (2005 I$).
- The gap is 1.03 log units (×2.81), *before* any 2010 → 2005 deflation.

Such a gap probably reflects Nigeria's GDP rebasing and later price-comparison (ICP) rounds; this
is not checked here. Converting the OECD series to 2005 dollars with a deflator would misplace
Nigeria by about one log unit, or 0.13 in β₀.

**The consistent route is a splice.** Take PWT 7.1's own Nigeria level, which the estimation saw
(Nigeria is in the sample, App. A2), and add real growth since 2010 from the OECD series.

- Growth per head 2010–2023 is ×1.007, the same in all three price bases.
- Nigeria 2023 is therefore ≈ $1,708 in 2005 I$.
- The 2006–2010 PWT 7.1 values swing between $1,649 and $1,931, so the anchor is uncertain by
  about ±0.08 log units.

**The missing number is the sample mean.** The paper does not report it; it gives only
25th = mean − 0.923 and 75th = mean + 1.077.

- The only level reference is Table 2, col. 7 (2010 cross-section, log income not demeaned). It
  puts the 2010 25th percentile at exp((0.63 + 1.20)/0.22) ≈ $4,100. Coefficient rounding alone
  spans $2,700–6,400.
- The pooled Table 5 sample (start years 1960–2000) sits lower, by an amount not measured here.

| 25th percentile of the t−10 sample (2005 I$) | d | β₀ | 2050 var/cur | 2100 var/cur |
|---|---:|---:|---|---|
| = Nigeria, current assumption | −0.923 | 0.360 | 0.959–0.990 | 0.944–0.979 |
| $2,000 | −1.081 | 0.339 | 0.968–0.992 | 0.950–0.981 |
| $2,500 | −1.304 | 0.310 | 0.981–0.994 | 0.958–0.985 |
| $3,000 | −1.487 | 0.287 | 0.992–0.996 | 0.965–0.989 |
| $4,098 (Table 2, 2010) | −1.798 | 0.246 | 1.000–1.011 | 0.976–0.994 |

**The direction is clear even though the size is not.** In the paper's own units, Nigeria very
likely sits *below* the 25th percentile.

- The paper's 2010 sample has only 11 low-income countries out of 132 (App. A3).
- Its pooled start years are earlier, and therefore poorer, than 2023.
- The 29th-percentile placement (WDI 2023, 197 countries) uses a different distribution and does
  not carry over.

Table 7's Sub-Saharan Africa estimate (0.16) also lies below 0.36. The baseline's own 0.36 rests
on the same placement, so converting d would move the current construction too. The ratios above
hold the current construction fixed.

**The region.** In 2023, R10's GDP per head is 0.084 log units below Nigeria's. Both figures are in
USD_2010 PPP but come from different vintages (IMAGE SSP2021 against OECD 2025). Giving the region
its own d_R = d − 0.084 moves 2100 var/cur from 0.944–0.979 to 0.951–0.995.

**To close it:**

1. Download PWT 7.1. This session's network policy blocked the download; the Nigeria values above
   were read from FRED's republication through a web search and are unverified.
2. Rebuild the 463-observation sample: the App. A2 countries, at decade starts 1960, 1971, 1980,
   1990 and 2000, wherever IEA data exist.
3. Check that its 25th and 75th percentiles fall at mean −0.923 and +1.077, which validates the
   rebuild against Table 5.
4. Compute d from the splice.

## C. Boundary: primary-energy coefficients on final energy

This is not a unit conversion. Nigeria's 2023 TES/TFC ratio is 1.241, but a ratio of levels says
nothing about how the two elasticities relate. Eq. 3 instead lets the Table 5 sector columns be
re-weighted. The weights come from Nigeria's 2023 IEA shares:

- residences 0.45, transport 0.33, industry 0.16, services 0.06 of the five final sectors;
- "Other" is 0.22 of TES.

| | β | β at 25th | η | κ | long run |
|---|---:|---:|---:|---:|---:|
| Table 5 total (TPES, published) | 0.480 | 0.360 | 0.130 | −0.023 | 0.71 |
| Eq. 3 check: six sectors weighted by TES | 0.434 | 0.369 | 0.072 | −0.032 | 0.66 |
| Final, bottom-up: five sectors by share | 0.390 | 0.295 | 0.104 | −0.033 | 0.52 |
| Final, top-down: total minus "Other" | 0.449 | 0.284 | 0.178 | −0.022 | 0.59 |

**What the routes agree on.**

- At Nigeria's percentile, the Eq. 3 check reproduces the published 0.36 (0.369).
- Both final-energy routes give **β₀ ≈ 0.28–0.30** and a **long run of ≈ 0.52–0.59**.
- They do not agree on η or κ, and neither does the check (η 0.072 against 0.13). Eq. 3
  decomposes the elasticity, not the interaction or the convergence terms. Those two stay
  unidentified for final energy unless a sector-by-sector partial adjustment is built.

**Results** (R recalibrated through whatever law the region is given):

| Leg | 2050 var/cur | 2100 var/cur |
|---|---|---|
| TPES total (variant) | 0.959–0.990 | 0.944–0.979 |
| Final top-down, Nigeria and region | 0.985–0.999 | 0.975–1.004 |
| Final, agreed terms only (β₀ 0.289, b 0.552; η, λ unconverted), both | 1.001–1.019 | 1.001–1.076 |
| Final bottom-up, both | 1.001–1.032 | 1.012–1.135 |
| Final bottom-up, region at its own IMAGE mix* | 1.021–1.085 | 1.074–1.277 |
| Final bottom-up, Nigeria only (breaks closure) | 0.887–0.962 | 0.665–0.855 |

\* IMAGE reports Residential and Commercial together; the split uses Nigeria's
residences:services ratio, which is an assumption.

**Why a lower elasticity *raises* Nigeria's path.** IMAGE "Final Energy" has the same boundary as
Nigeria's TFC, so closure requires stripping the region with the same final-energy law. Under
recalibration, a change shared by both laws acts only on the gap in income growth. Nigeria's
growth per head is 0.7–0.95 points per year *below* R10's in every marker:

| | SSP1 | SSP2 | SSP3 | SSP5 |
|---|---:|---:|---:|---:|
| Nigeria (%/yr) | 3.01 | 2.54 | 1.11 | 3.65 |
| R10 (%/yr) | 3.95 | 3.42 | 1.83 | 4.60 |

Converting Nigeria alone pushes the opposite way (0.67–0.86) and mixes boundaries inside one
identity. Residences carry β ≈ 0.00 at the 25th percentile, the paper's biomass-switching effect,
so this conversion overlaps with Option D (MSc-thesis 2026-10-03 memo).

## D. Pure unit factors cancel

Both checks run against the plain recalibrated variant:

- **GDP:** switching to the USD_2010 rows changes 2100 var/cur by at most 3e-15.
- **Energy:** switching the anchor to kgoe changes it by at most 1e-15.

IMAGE's USD_2010 GDP enters only as log changes and through R, so it needs no conversion.

Energy *levels* in kgoe would matter in one case only: placing Nigeria's starting gap x* − x
against the paper's sample. Nigeria's 2023 TES is 330 kgoe per head, against a low-income mean of
396 kgoe in the 2010 cross-section. The variant assumes a zero starting gap (the α calibration),
and the paper does not report the intercept and control coefficients needed to do better.

## Recommendation

1. **Pure unit factors** (energy units, price bases): apply none.
2. **Time scale:** keep λ = −κ. It tracks the decade benchmark better than the exact geometric
   conversion.
3. **Income level:** the one conversion the method needs.
   - Replace the 25th-percentile assumption with a PWT 7.1 splice, plus the reconstructed sample
     mean (section B).
   - Do not use a deflator or price-base factor.
   - Expected direction: β₀ below 0.36, roughly 0.25–0.34. Effect on the variant/current ratios is
     small (at most +0.03 in 2100 and +0.05 in 2050), because recalibration re-absorbs most of it. The baseline's 0.36 rests on
     the same placement.
4. **Primary → final boundary** (open, Per's decision):
   - If adopted, apply it to Nigeria and the region alike.
   - Convert only β₀ and the long-run target (β₀ ≈ 0.29, b ≈ 0.55), or build a sector-by-sector
     partial adjustment.
   - Report the result as a sensitivity: 2100 at 1.00–1.08 of current for the agreed-terms leg.

## Limits

- **PWT 7.1 Nigeria values** come from FRED (RGDPCHNGA625NUPN) through a web search. They were
  not downloaded or verified, and are volatile year to year.
- **The level of the t−10 sample mean is unknown.** The table in section B is a function of an
  assumed 25th percentile, not an estimate.
- **The Table 2 back-out is sensitive to coefficient rounding** ($2,700–6,400).
- **Sector weights are fixed at their 2023 values.** Eq. 3 is exact only for small changes, so the
  weights would drift over the horizon.
- **Built here, not taken from the paper:**
  - the averaged "agreed-terms" values;
  - the split of IMAGE's Residential and Commercial using Nigeria's ratio.
- **Unchanged inputs:** all runs use the variant's plain, recalibrated, no-decade-effects leg and
  the older IEA release (2,465,907 TJ). The ratios do not depend on the anchor level; the sector
  weights in section C would shift slightly with the 28 Sep 2026 release.

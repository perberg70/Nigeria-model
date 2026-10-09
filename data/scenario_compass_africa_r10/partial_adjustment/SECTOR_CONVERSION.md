# Energy conversion under electrification, sector by sector

Branch `experiment/partial-adjustment`, 2026-10-09. Explores Per's question: when energy systems
move from fuels to electricity, the conversion factors change. This alters total energy demand,
and any overall primary-to-final factor depends on the transitions in each sector.

- **Script:** `sector_conversion.py`. **Full output:** `sector_conversion_output.txt`.
- **Not changed:** the variant, the baseline builder and the prototype.
- **Different question:** `CONVERSION_FACTORS.md` covers unit conversions of the Table 5
  coefficients, not this.

**Scope flag (AGENTS.md).** This is energy-system modelling. The 2026-08-20 memo (MSc-thesis
`03_models/`) recommended against a hand-built efficiency fix, and the 2026-08-26 council found
that efficiency ratios belong as input-scaling factors, not substitution parameters. Both
remain open decisions for Per.

## The two conversion layers move in opposite directions

```
energy service  ←(end-use efficiency η)–  final energy  ←(supply factor PEF)–  primary energy
```

**End use.** Electricity delivers more service per unit of final energy than the fuel it
displaces. The ratio ρ = η_electric / η_displaced ranges from about 1.1 for industrial boiler
heat to 6–10 for a three-stone fire. At the same service, displacing fuel d needs only d/ρ of
electricity, so **final energy falls**.

**Supply.** Each unit of final electricity needs more primary energy than biomass or oil
products do. Its PEF depends on the power mix:

| Power mix | PEF (primary per unit of final electricity) |
|---|---:|
| all gas (UNSD plant efficiency 34.8%) | 3.48 |
| Nigeria's 2023 grid | 2.97 |
| 72% low-emission, 28% gas | 1.85 |
| all solar or hydro (grid losses only, ×1.21) | 1.21 |

So **P/F rises** with electrification, and how much depends on the mix.

The prototype converts one-for-one (ρ = 1). It holds total final energy fixed and gives
electricity a growing share of it, so it captures neither layer.

## 1. Nigeria 2023, by sector and carrier

| PJ (UNSD 2023) | biomass | LPG, kerosene | gas, coal, fuel oil | petrol, diesel | electricity | total |
|---|---:|---:|---:|---:|---:|---:|
| residential | 935 | 77 | — | — | 63 | 1,075 |
| commercial | 119 | 0 | — | — | 29 | 148 |
| industry | 178 | 0 | 178 | 0 | 30 | 386 |
| transport | — | — | — | 772 (+9 jet) | — | 781 |
| non-energy and other | — | 8 | 74 | — | — | 87 |
| **total** | **1,232** | **85** | **252** | **772** | **122** | **2,477** |

- **Match with the IEA:** sector totals agree within 2–4% (industry 386 vs 372; total 2,477 vs
  2,466 PJ). The labels for the UNSD codes 1234 and 1235 are assigned by matching them to IEA
  rows.
- **Biomass** is 50% of final energy, and residential biomass alone is 38%.
- **Electricity** is 4.9% of final energy.

Most of Nigeria's final energy therefore sits in the uses with the largest ρ: open-fire
cooking and road transport.

## 2. Primary-to-final, 2023

- **Gas power plants:** 327 PJ of gas in, 114 PJ of electricity out, an efficiency of 34.8%.
- **Losses:** gross generation is 1.21 × final electricity (the IEA fixes losses at 15%).
- **Charcoal kilns:** 186 PJ of wood makes 44 PJ of charcoal, an efficiency of 24% (PEF 4.18).
- **P/F:** the demand-linked conversion alone gives **1.15**, against the IEA's TES/TFC of 1.24.
  The remaining 203 PJ is mostly gas burned by the oil and gas industry (UNSD 0912, 118 PJ),
  which is tied to export production rather than domestic demand.

## 3. End-use efficiency ratios (ρ)

| Displaced use | Low / central / high | Evidence |
|---|---|---|
| Cooking on wood or residues | 4 / 6 / 10 | ETP 2.0 charts (pp. 37–40), per stove: biomass 6.6 GJ against electric 1.1–1.5 GJ, giving 4.3–6.2. This assumes equal service per stove and is our derivation. A Uganda controlled cooking test ("Techno-economic analysis of clean cooking technologies and fuels in Uganda", 2025, FAO AGRIS record; found by web search, **unverified**) uses 102.4 MJ (three-stone fire), 38.8 MJ (improved wood stove) and 10.4 MJ (hotplate) per kg of beans, giving three-stone fire / hotplate 9.8 and improved wood stove / hotplate 3.7 |
| Charcoal | 2 / 3 / 4 | **Assumption** |
| LPG | 1.2 / 1.5 / 2 | ETP per stove 1.3–1.9; Uganda test 1.27. Akpasoh & Edeminam (2023, Nigeria) give 3.7–7.1 for an electric pressure cooker, an upper bound |
| Kerosene | 1.5 / 2 / 3 | Akpasoh & Edeminam 1.7–3.6 (upper bound, lower heating values assumed) |
| Road fuels | 2.3 / 3 / 5 | US DOE (found by web search): electric vehicles about 60% grid-to-wheel (77% in an older figure), petrol vehicles 12–30% |
| Industrial heat, fossil | 1.0 / 1.1 / 1.5 | **Assumption**: resistance heating against boilers; heat pumps at the high end |
| Industrial heat, wood | 1.5 / 2.5 / 4 | **Assumption** |
| Back-up generators → grid | 4–6.7 | 15–25% generator efficiency (2026-08-29 boundary memo) |

Aviation fuel, lubricants and non-energy use are treated as not electrifiable. This caps the
reachable electricity share at 91%.

## 4. What electrification does to final and primary energy (2023 structure, same service)

The prototype sets one national share, e. Turning that into sector changes needs an
**allocation rule**: which sectors switch first. That rule is where the sector-wise transitions
enter the overall factor.

| Rule | e | F/F0, central ρ | F/F0, ρ range | P/F, 2023 grid | P/F, 72% low | P/P0, 2023 grid | P/P0, 72% low |
|---|---:|---:|---|---:|---:|---:|---:|
| pro rata | 0.20 | 0.78 | 0.67–0.84 | 1.44 | 1.22 | 0.97 | 0.82 |
| cooking first | 0.20 | 0.67 | 0.58–0.72 | 1.44 | 1.21 | 0.83 | 0.70 |
| transport first | 0.20 | 0.78 | 0.63–0.84 | 1.47 | 1.24 | 0.99 | 0.84 |
| industry first | 0.20 | 0.88 | 0.77–0.95 | 1.46 | 1.23 | 1.12 | 0.95 |
| IMAGE SSP2-4.5 pattern | 0.20 | 0.78 | 0.67–0.85 | 1.43 | 1.21 | 0.96 | 0.81 |
| pro rata | 0.67 | 0.46 | 0.33–0.56 | 2.33 | 1.58 | 0.92 | 0.63 |
| cooking first | 0.67 | 0.40 | 0.29–0.50 | 2.32 | 1.57 | 0.80 | 0.54 |
| industry first | 0.67 | 0.46 | 0.33–0.57 | 2.38 | 1.63 | 0.95 | 0.65 |
| IMAGE SSP2-4.5 pattern | 0.67 | 0.45 | 0.33–0.56 | 2.32 | 1.57 | 0.91 | 0.62 |

F0 = final energy in 2023, P0 = primary energy in 2023, P = primary energy. Today's P/F is 1.15
(bottom-up). The IMAGE pattern splits new electricity household 0.46, industry 0.50, transport
0.05, as IMAGE R10 adds it over 2023–2050.

**Final energy falls steeply at the same service.**

- At 20% electricity, final energy is 0.67–0.88 of today's, depending on the allocation rule.
- At 67%, it is 0.40–0.46. With ρ uncertainty included, 0.29–0.57.
- The one-for-one model keeps it at 1.00. At 67% it therefore overstates electricity by a
  factor of 2.2–2.5 (central ρ).

**Which sectors switch matters most at moderate shares.**

- At 20%, cooking first gives 0.67 and industry first gives 0.88.
- At high shares the rules converge, because every route has to take on the large biomass and
  road-fuel uses.

**The overall P/F factor is not fixed.**

- It rises from 1.15 to 1.2–2.4. The power mix drives it as much as electrification does.
- Primary energy falls to 0.54–0.65 of today's when the power is mostly low-emission. With
  today's gas-heavy grid, it falls only to 0.80–0.95.
- With industry first at 20% on today's grid, primary energy *rises* (1.12).

## 5. Back-up generators: a boundary term of the same size

The prototype counts about 20.6 TWh of generator output as electricity. The generator fuel stays
in final energy, if it is recorded at all:

- UNSD books all petrol and almost all diesel to road transport.
- The IEA notes that generator inputs and outputs "may not be properly reported" (p. 502).

**If the fuel is inside final energy**, replacing that output with grid power at the same
service cuts final energy by **222–420 PJ, or 9–17% of the 2023 total**, at 25–15% generator
efficiency. If the fuel is not recorded, today's final energy is understated instead.

**The share definition is also a choice.** The prototype's 2023 electrification share of 8.99%
uses gross generation plus generator output. The final-electricity share in the balance is
4.9%.

## 6. IMAGE Africa R10: the factor moves with each SSP's own transitions

| Marker | P/F 2020 → 2050 → 2100 | Electricity share of F, 2100 | ε_P/F, 2020→2050 | ε_P/F, 2020→2100 |
|---|---|---:|---:|---:|
| SSP1-1.9 | 1.33 → 1.41 → 1.49 | 0.61 | +0.043 | +0.036 |
| SSP1-2.6 | 1.33 → 1.32 → 1.47 | 0.59 | −0.005 | +0.033 |
| SSP2-4.5 | 1.33 → 1.35 → 1.54 | 0.53 | +0.017 | +0.053 |
| SSP5-8.5 | 1.33 → 1.57 → 1.76 | 0.61 | +0.102 | +0.077 |

- **SSP3** is not shown: its primary biomass is missing from the export.
- **Why P/F rises even with low-carbon power:** it rises under SSP1-1.9, where 84% of power is
  low-carbon by 2050. Modern bioenergy (biofuels, biomass power, bioenergy with carbon capture)
  raises primary biomass per unit of final solid biomass from 1.07 in 2020 to 2.6 in 2050 and
  4.9 in 2100.
- **Conventions:** IMAGE uses the IAMC direct-equivalent convention; the paper's TPES uses the
  IEA physical-energy-content convention. They differ only for nuclear, which is small in Africa.

**The residential and commercial sector shows the conversion effect directly.** Weighting IMAGE's
carriers by central end-use efficiencies:

| 2020 → 2050 | Final energy per head (ε) | Energy service per head (ε) |
|---|---|---|
| SSP1, SSP2, SSP3 | falls (−0.30 to −0.14) | rises (+0.26 to +0.35) |
| SSP5 | flat (+0.07) | rises (+0.61) |

IMAGE's residential and commercial final-energy path is shaped by fuel switching, not by falling
demand for service. This is the mechanism the R10 residual R carries, consistent with the Option D
finding (MSc-thesis 2026-10-08) that most of R's "efficiency" is biomass switching.

## 7. What this means for the demand law and the variant

**The elasticity has to be converted using the future P/F factor.**

- The rule is **ε_final = ε_primary − ε_P/F**.
- The paper's TPES elasticity embeds the 1960–2010 average ε_P/F. That period's electrification
  was thermal. The paper's own sector columns imply about **+0.07** at Nigeria's percentile and
  **+0.12 to +0.19** in the long run (`CONVERSION_FACTORS.md` §C).
- IMAGE's SSP paths give **−0.005 to +0.10** for R10.
- Nigeria's own future value depends on its transitions: section 4 runs from P/F nearly flat
  (mostly low-emission power) to P/F doubling (gas power).
- No single primary-to-final factor exists. ε_P/F has to come from the same sector-and-power-mix
  path the scenario assumes.

**The level effect is larger than the elasticity effect.** Moving from one-for-one to
constant-service conversion changes final energy by a factor of 0.3–0.9 at high electrification.
Converting the elasticity moves it by about 0.07.

**The design that avoids double counting** keeps energy service invariant across the user's
technology choices:

1. **Baseline: keep the current structure** (final-energy law × R10 residual). R already carries
   IMAGE's conversion path for each SSP.
2. **User's pathway:** multiply final energy by
   **K(t) = F(e_user(t)) / F(e_base(t))** at constant service, using sector ρ and an allocation
   rule.
   - K is measured from the baseline's own electrification, not from 2023. It therefore adds only
     the user's deviation and does not double-count what R holds.
   - SSP2-4.5 in 2050 (IMAGE allocation, central ρ; 2050 assumed to have the 2023 structure):

     | Slider | K | Final electricity, one-for-one | Final electricity, converted | Final energy |
     |---|---:|---:|---:|---:|
     | 20% | 0.96 | 157 TWh | 150 TWh | 5.16 → 4.93 EJ |
     | 40% | 0.81 | 313 TWh | 252 TWh | 5.16 → 4.15 EJ |
     | 67% | 0.66 | 525 TWh | 348 TWh | 5.16 → 3.42 EJ |

     The slider's share is mapped to a final-electricity share by the 2023 ratio of 0.547. The
     prototype itself displays gross generation including generators, which is about 1.8 times
     these figures on the 2023 definition.
3. **P/F** is needed only to report primary energy, or to convert the TPES elasticity (point
   above). Take it from the chosen power mix and allocation, not as a constant.

**Decisions for Per:**

- **Allocation rule.** Default to IMAGE's sector pattern for the selected SSP (consistent with
  R), or show the band across rules.
- **ρ:** show it as a range or a point. The range in this memo is wide (F/F0 0.29–0.57 at 67%).
- **Slider definition:** share of final energy, as now, or share of service. The two agree only
  at 0% and 100%.
- **Generator boundary:** whether generator output belongs in the electrification share at all.

## Limits

- **Industry and charcoal ρ are assumptions.** The cooking evidence is a derived ETP ratio
  (equal service per stove assumed), a Uganda test found by web search and not verified, and an
  upper-bound Nigerian test. The transport ratio comes from US DOE figures found by web search.
- **The structure is static.** 2050 is given 2023's sector-carrier structure. There is no rebound
  effect: cheaper service may raise demand for it. Within a sector, fuels are displaced pro rata.
- **Data:**
  - UNSD codes 1234 and 1235 are labelled by matching them to IEA rows.
  - The location of generator fuel is unknown.
  - The older IEA release is used throughout. The ratios are insensitive to it.
- **IMAGE:** P/F for SSP3 is not formed. Primary energy is summed from eight sources; geothermal
  and "other" are not in the export.

"""Build the Nigeria SSP baseline for africa-prototype.html.

Written 2026-09-09 for the method Per set out this session. Builds, per SSP
marker and per year to 2100:

    emisMt     Nigeria's fossil-and-industrial CO2 baseline, Mt/yr
              built from Nigeria's population and GDP-per-capita paths
              through a stage-sensitive aggregate-energy demand relation
    elecShare  Nigeria's electrification (electricity generated / total final energy)
    lowShare   low-emission share of all Nigeria's electricity   [layer 1]
    lowMix     composition WITHIN the low-emission group          [layer 2]
    popN       Nigeria's own population, from the IIASA export

Nigeria's observed 2024 emissions set the position. Nigeria's population and
GDP-per-capita paths set the macroeconomic pressure through the Burke &
Csereklyei (2016) aggregate-energy relation, with the marginal income
elasticity increasing as GDP per capita rises. An Africa R10 efficiency
residual -- R10's final-energy path divided by what its own population and
income per head give through the same relation -- is applied as an aggregate
efficiency, structure, and technology proxy, so the income effect is not
counted twice. R10 carbon intensity is not transferred to
Nigeria. R10 continues to supply the separate power-sector baseline and the
SSP marker mapping. This deliberately avoids presenting an unverified
regional carbon-intensity path as a Nigerian carbon-intensity forecast.

`scripts/run_ssp_baseline.py --update-prototype` copies the four generated
blocks (js_block.py) into the standalone prototype/africa-prototype.html file
(prototype.py). The generated block remains the canonical data artifact; the
HTML copy is kept in sync for the prototype.

THE DENOMINATOR QUESTION, decided 2026-09-09. The by-fuel generation rows do
not reconcile with the reported `Secondary Energy|Electricity` total in the two
SSP1 markers -- components exceed it by 1.6% at 2050 and 32.9% at 2100 (README
finding 1; cause unverified, plausibly electricity to hydrogen and synfuels
counted net in the total and gross in the rows). Shares here therefore use
SUM(by-fuel rows) as the denominator, never the reported total, so layers 1 and
2 are consistent with each other. The cost is a <=1.5 pp difference from the
published total at 2100, confined to SSP1; at 2050 it is 0.2-0.3 pp.

WHAT THE BASELINE DOES *NOT* CARRY, and why:
  * No Africa R10 carbon-intensity change is applied to the economy-wide
    emissions line. The R10 final-energy/GDP ratio is used only as a relative
    aggregate efficiency/technology/structure proxy; Nigerian fugitive and
    industrial-process emissions are not separately estimated here.
  * The fossil group's internal split (gas vs back-up diesel) is NOT
    transferred from R10. It follows Nigeria's own rule, k = k0 x e0/e with
    gas the residual (section 6 below; it is not held constant -- that rule
    was tested and rejected on 2026-09-09). Africa R10's fossil composition is driven by
    coal-to-gas substitution -- 39% of the regional fossil group is coal and
    none of Nigeria's is -- and its `Oil` category is oil-fired power stations,
    not a decentralised back-up fleet. Transferring it would retire Nigeria's
    generators to 1.4-8.5% of fossil by 2050 in EVERY scenario including the
    slow-development one, which is the Energy Transition Plan's own net-zero
    outcome arriving in a no-policy baseline.
  * No Nigerian policy. The ETP is a policy trajectory and belongs to the
    comparison, not to the baseline.

All observed anchors, elasticities and envelope limits are read from the
``ssp_baseline`` section of the configuration, where each carries its source.
"""

from __future__ import annotations

import csv
import logging
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from config_paths import ConfigError, require, require_path
from scenario_data import IiasaExport, Marker, interp, load_markers, narratives, read_series
from units import HOURS_PER_YEAR, TJ_PER_GWH

LOGGER = logging.getLogger("ssp_baseline.builder")

LOW = ["Hydro", "Solar", "Wind", "Nuclear", "Biomass"]
FOS = ["Coal", "Gas", "Oil"]
ALLS = LOW + FOS + ["Other"]


@dataclass(frozen=True)
class BaselineParams:
    """Everything the builder reads from the configuration."""

    region_name: str
    markers: dict[str, Marker]
    base_year: int
    anchor_year: int
    end_year: int
    image_dir: Path
    iiasa: IiasaExport
    iea_final_current: Path
    iea_electricity_current: Path
    output_block: Path
    prototype_html: Path
    cumulative_start_year: int
    diagnostics_year: int
    # --- the region's observed anchors ---------------------------------------
    generation_gwh: dict[str, float]  # base-year grid generation by IAMC source (ALLS)
    iea_generation_lines: dict[str, str]  # IAMC source -> line of the IEA electricity table
    genset_gwh: float
    tfe_tj: float
    anchor_mt: float
    # --- demand relation ----------------------------------------------------
    elasticity: float
    elasticity_q: float
    cook_elasticity: float
    # --- physical envelope --------------------------------------------------
    hydro_ceiling_gw: float
    wind_ceiling_gw: float
    hydro_capacity_gw: float
    cf_wind: float

    @classmethod
    def from_config(cls, config: Mapping[str, Any]) -> BaselineParams:
        a = "ssp_baseline.anchors"
        d = "ssp_baseline.demand"
        e = "ssp_baseline.envelope"
        generation = dict(require(config, f"{a}.generation_gwh"))
        if set(generation) != set(ALLS):
            raise ConfigError(
                f"{a}.generation_gwh must list every source {ALLS} (0.0 for an observed zero); "
                f"got {sorted(generation)}"
            )
        lines = dict(require(config, "inputs.iea_generation_lines"))
        if not set(lines) <= set(ALLS):
            raise ConfigError(
                f"inputs.iea_generation_lines: unknown sources {set(lines) - set(ALLS)}"
            )
        base_year = int(require(config, "time_horizon.base_year"))
        end_year = int(require(config, "time_horizon.end_year"))
        diagnostics_year = int(require(config, "ssp_baseline.diagnostics_year"))
        if not base_year <= diagnostics_year <= end_year:
            raise ConfigError("ssp_baseline.diagnostics_year must lie within time_horizon")
        return cls(
            region_name=require(config, "region.name"),
            markers=load_markers(config),
            base_year=base_year,
            anchor_year=int(require(config, "time_horizon.anchor_year")),
            end_year=end_year,
            image_dir=require_path(config, "inputs.image_dir"),
            iiasa=IiasaExport.from_config(config),
            iea_final_current=require_path(config, "inputs.iea.final_by_fuel_and_sector_current"),
            iea_electricity_current=require_path(config, "inputs.iea.electricity_current"),
            output_block=require_path(config, "ssp_baseline.output_block"),
            prototype_html=require_path(config, "ssp_baseline.prototype_html"),
            cumulative_start_year=int(require(config, "ssp_baseline.cumulative_start_year")),
            diagnostics_year=diagnostics_year,
            generation_gwh=generation,
            iea_generation_lines=lines,
            genset_gwh=require(config, f"{a}.genset_gwh"),
            tfe_tj=require(config, f"{a}.total_final_energy_tj"),
            anchor_mt=require(config, f"{a}.emissions_mt"),
            elasticity=require(config, f"{d}.elasticity"),
            elasticity_q=require(config, f"{d}.elasticity_quadratic"),
            cook_elasticity=require(config, f"{d}.cooking_elasticity"),
            hydro_ceiling_gw=require(config, f"{e}.hydro_ceiling_gw"),
            wind_ceiling_gw=require(config, f"{e}.wind_ceiling_gw"),
            hydro_capacity_gw=require(config, f"{e}.hydro_capacity_gw"),
            cf_wind=require(config, f"{e}.wind_capacity_factor"),
        )

    # Derived anchors, in the order and form the original constants used.
    @property
    def grid_gwh(self) -> float:
        return sum(self.generation_gwh[n] for n in ALLS)

    @property
    def hydro_gwh(self) -> float:
        return self.generation_gwh["Hydro"]

    @property
    def all_gwh(self) -> float:
        return self.grid_gwh + self.genset_gwh

    @property
    def low_gwh(self) -> float:
        return sum(self.generation_gwh[n] for n in LOW)

    @property
    def elec_base(self) -> float:
        """Electrification in the base year: (grid + gensets) / total final energy.

        BOUNDARY: genset output is counted as electricity while the gensets' fuel stays in
        total final energy (see the genset_gwh note in config.yaml).
        """
        return self.all_gwh * TJ_PER_GWH / self.tfe_tj

    @property
    def low_base(self) -> float:
        return self.low_gwh / self.all_gwh

    @property
    def fossil_gwh(self) -> float:
        return self.all_gwh - self.low_gwh  # grid fossil plus back-up generators

    @property
    def k0(self) -> float:
        """Gensets' share OF FOSSIL generation in the base year (0.3946)."""
        return self.genset_gwh / self.fossil_gwh

    # --- THE REGION'S PHYSICAL ENVELOPE ---------------------------------------
    # Energy Transition Plan p.64 resource potential: PHYSICAL LIMITS, not policy
    # targets, which is why they may be used in a no-policy baseline while the ETP's
    # generation mix (its net-zero case) may not.
    # WIND IS CAPPED ON THE TOTAL, which includes offshore: IAMC common-definitions makes
    # `Wind` the parent of `Wind|Onshore` and `Wind|Offshore`, and only the aggregate was
    # downloaded. So this asserts NIGERIA BUILDS NO OFFSHORE WIND. Per's ruling 2026-09-09,
    # grounded in the ETP's own optimiser -- offered offshore with full costs and no resource
    # cap, it built none across a run to 2060 -- but an assumption, not a measurement.
    # Solar's 210 GW is UTILITY-SCALE ONLY; the ETP leaves distributed and stand-alone
    # uncapped, which is why solar is the overflow recipient rather than a capped source.
    @property
    def cf_hydro(self) -> float:
        """0.520, DERIVED from the region's own data (see config: mixes years)."""
        return self.hydro_gwh / (self.hydro_capacity_gw * HOURS_PER_YEAR)

    @property
    def ceil_hydro(self) -> float:
        return self.hydro_ceiling_gw * HOURS_PER_YEAR * self.cf_hydro / 1000  # 125 TWh/yr

    @property
    def ceil_wind(self) -> float:
        return self.wind_ceiling_gw * HOURS_PER_YEAR * self.cf_wind / 1000  # 8.4 TWh/yr

    @property
    def lowmix_base(self) -> dict[str, float]:
        """Composition of the base year's low-emission generation, by source."""
        return {n: self.generation_gwh[n] / self.low_gwh for n in LOW}

    @property
    def years(self) -> list[int]:
        return list(range(self.base_year, self.end_year + 1))

    @property
    def narratives(self) -> list[str]:
        return narratives(self.markers)


@dataclass
class BaselineResult:
    """The baseline per marker, plus the inputs the block and diagnostics reuse."""

    params: BaselineParams
    years: list[int]
    block: dict[str, dict[str, Any]]
    checks: list[tuple[str, float, float, float, float]]
    pop: dict[str, dict[int, float]]
    gdp: dict[str, dict[int, float]]
    cook: dict[str, list[float]] = field(default_factory=dict)


# IEA RELEASE. The base-year anchors come from the IEA Energy Statistics Data Browser
# tables for Nigeria dated 28 Sep 2026, saved in data/iea_nigeria_2023/*_current_release.csv.
# Refreshed 2026-10-09 (ported from MSc-thesis, where the same refresh was made on
# 2026-10-08) from an older release (total final energy 2,465,907 TJ; grid 40,958 GWh = gas
# 31,640 + hydro 9,107 + solar 211). The older exports stay in that folder as the audit
# trail; the two releases must not be mixed in one calculation. The check below ties the
# configured anchors to the saved tables, so the two cannot drift apart silently: each
# source's generation must equal its configured line, and a source without a line must
# be an observed zero.
def check_iea_anchors(params: BaselineParams) -> None:
    f1, f2 = params.iea_final_current, params.iea_electricity_current
    for f in (f1, f2):
        if not f.exists():
            raise FileNotFoundError(f"IEA current-release table not found, anchors unchecked: {f}")
    with f1.open(encoding="utf-8", newline="") as fh:
        tot = {r["sector"]: r for r in csv.DictReader(fh)}["Total final consumption"]
    with f2.open(encoding="utf-8", newline="") as fh:
        gen = {r["line"]: float(r["value_GWh"]) for r in csv.DictReader(fh)}
    if float(tot["total_TJ"]) != params.tfe_tj:
        raise ValueError("total_final_energy_tj differs from the saved IEA table")
    lines = params.iea_generation_lines
    for source, gwh in params.generation_gwh.items():
        observed = gen[lines[source]] if source in lines else 0.0
        if gwh != observed:
            raise ValueError(
                "%s generation differs from the saved IEA table (%s configured, %s in the table)"
                % (source, gwh, observed)
            )


# --- ONE INCOME-DRIVEN INDEX FOR HOUSEHOLD SOLID-FUEL USE, ported 2026-10-09 from MSc-thesis
# idx(t) = (income per head_t / income per head_BASE_YEAR) ** cook_elasticity, on the
# region's own SSP path (IIASA / OECD ENV-Growth export). The prototype's clean-cooking
# baseline reads it: the polluting share of people is p_t = p_2023 x idx (emitted as BLOCK
# 4, NGA_DATA.health.pollutingIdxSSP, together with the elasticity, which the slider path
# also reads). It replaces the hand-pasted gdpSSP table the prototype held until 2026-10-09;
# the baseline clean-cooking shares are unchanged by the switch. The prototype holds a PASTED
# COPY of the block, spliced in by --update-prototype, so re-run the script after any change.
# In MSc-thesis the same function also feeds the residential-biomass bucket of an offline
# sector-split test; decision record there: 03_models/2026-10-09_shared-cooking-index.md.
def cook_index(
    gdp: Mapping[int, float],
    pop: Mapping[int, float],
    year: int,
    base_year: int,
    elasticity: float,
) -> float:
    """(income per head at `year` / income per head in `base_year`) ** elasticity.

    Income per head is the narrative's GDP|PPP over its population, each linearly interpolated on
    the export's grid exactly as country_series() and interp() define them (2023 and 2024 are
    themselves interpolated between the 2020 and 2025 historical anchors).
    """

    def income(y):
        return interp(y, gdp) / interp(y, pop)

    return (income(year) / income(base_year)) ** elasticity


def apply_envelope(params: BaselineParams, lowmix_series, low_twh_series):
    """The region's resource envelope, applied to the whole trajectory at once.

    PATH-DEPENDENT, which is why it cannot be a per-year function: the hydro
    floor RATCHETS. Dams are not demolished, so hydro may never fall below the
    highest level it has already reached. Per's ruling 2026-09-09.

    Order, and it matters:
      1. ceilings  -- hydro and wind are physically bounded; the overflow goes
                      to SOLAR, the one low-emission source Nigeria has in
                      abundance and whose stated cap covers utility scale only.
      2. floor     -- hydro is held at its running maximum; the deficit comes
                      back out of SOLAR and NUCLEAR pro rata, then biomass.
    The group always sums to its layer-1 total, so layer 2 can never contradict
    layer 1.
    """
    ceil_hydro = params.ceil_hydro
    ceil = {"Hydro": ceil_hydro, "Wind": params.ceil_wind}
    out_series, hi_water = [], 0.0
    for mix, low_twh in zip(lowmix_series, low_twh_series, strict=False):
        out, pool = {}, 0.0
        for n in LOW:
            want = mix[n] * low_twh
            if n in ceil and want > ceil[n]:
                out[n] = ceil[n]
                pool += want - ceil[n]
            else:
                out[n] = want
        out["Solar"] += pool

        hi_water = min(max(hi_water, out["Hydro"]), ceil_hydro)
        if out["Hydro"] < hi_water - 1e-9:
            need = hi_water - out["Hydro"]
            for donors in (["Solar", "Nuclear"], ["Biomass"]):
                avail = sum(out[n] for n in donors)
                if avail <= 1e-12:
                    continue
                take = min(need, avail)
                for n in donors:
                    out[n] -= take * out[n] / avail
                need -= take
                if need <= 1e-9:
                    break
            out["Hydro"] = hi_water - need
        tot = sum(out.values())
        out_series.append({n: (out[n] / tot if tot > 0 else 0.0) for n in LOW})
    return out_series


def build_baseline(params: BaselineParams) -> BaselineResult:
    """Compute the baseline for every configured marker."""

    check_iea_anchors(params)
    p = params
    base_year, anchor_year, end_year = p.base_year, p.anchor_year, p.end_year
    elasticity, elasticity_q = p.elasticity, p.elasticity_q
    elec_base, low_base, lowmix_base = p.elec_base, p.low_base, p.lowmix_base

    def image(fn):
        return read_series(p.image_dir, fn)

    tot = image("Secondary Energy - Electricity.csv")
    fe = image("Final Energy.csv")
    r10_gdp = image("GDP - PPP.csv")
    r10_pop = image("Population.csv")
    parts = {n: image("Secondary Energy - Electricity - %s.csv" % n) for n in ALLS}
    fill_years = (base_year, anchor_year)
    pop = p.iiasa.series(p.iiasa.population, p.narratives, fill_years)
    gdp = p.iiasa.series(p.iiasa.gdp, p.narratives, fill_years)

    # ANNUAL, not the source's 5-year grid. The model evaluates at integer years,
    # and interpolating a SHARE and a TOTAL separately does not preserve a cap
    # between grid points -- on the 5-year grid wind came out 1.5% and hydro 1.8%
    # above their ceilings in the in-between years. Emitting every year makes the
    # lookup exact and the envelope hold by construction. Costs about 40 KB.
    years = p.years
    block, checks = {}, []

    for pid, marker in p.markers.items():
        scen, narrative = marker.key, marker.narrative
        # --- regional series, all on sum(parts) where a share is involved ----
        sumparts = {y: sum(parts[n][scen][y] for n in ALLS) for y in tot[scen]}
        gen_over_fe = {y: tot[scen][y] / fe[scen][y] for y in tot[scen]}

        # R10 EFFICIENCY RESIDUAL. Africa R10's Final Energy/GDP falls for two
        # reasons: energy grows more slowly than income (the income effect the
        # Burke & Csereklyei relation already applies to Nigeria) and genuine
        # efficiency, structure and technology change. Using the raw ratio
        # counted the income effect twice (until 2026-10-03). The factor kept is
        # the part of R10's own final-energy path that its population and income
        # per head, run through the SAME relation, do not explain:
        #   T(y, ref) = [FE(y)/FE(ref)] / [P(y)/P(ref) * exp(b L + q L^2)],
        #   L = ln(GDPpc(y) / GDPpc(ref)), all Africa R10.
        # It is referenced to the same year as the Nigerian factor it multiplies,
        # since the quadratic makes it depend on the reference year.
        def r10_efficiency(y, ref, scen=scen):
            fr = interp(y, fe[scen]) / interp(ref, fe[scen])
            pr = interp(y, r10_pop[scen]) / interp(ref, r10_pop[scen])
            L = math.log(
                (interp(y, r10_gdp[scen]) / interp(y, r10_pop[scen]))
                / (interp(ref, r10_gdp[scen]) / interp(ref, r10_pop[scen]))
            )
            return fr / (pr * math.exp(elasticity * L + elasticity_q * L * L))

        # LAYER 1 IS A TWO-WAY SPLIT, so its denominator must be low+fossil only.
        # `Other` is IAMC's own catch-all -- "sources that do not fit any other
        # category" (common-definitions tag_secondary_electricity_sources.yaml)
        # -- neither low-emission nor fossil by definition. Codex review
        # 2026-09-10 caught that low_frac was computed as 1-fossil_frac over
        # sumparts (which INCLUDES Other), silently folding the whole category
        # into "low-emission". Verified against the source CSVs: Other reaches
        # 8.59pp of SSP3-7.0 generation in 2050, inflating that marker's low
        # share from a correct 30.38% to 38.97% -- material, not a rounding
        # matter, and it would have propagated into baseLowShareAt and the
        # whole envelope downstream. Fixed by excluding Other from BOTH
        # fractions' denominator, so low_frac + fossil_frac == 1 exactly with
        # Other genuinely dropped rather than absorbed into either side.
        lowfos = {y: sum(parts[n][scen][y] for n in LOW + FOS) for y in tot[scen]}
        fossil_frac = {y: sum(parts[n][scen][y] for n in FOS) / lowfos[y] for y in lowfos}
        low_frac = {y: 1.0 - fossil_frac[y] for y in fossil_frac}
        lowsum = {y: sum(parts[n][scen][y] for n in LOW) for y in sumparts}
        lowmix = {
            n: {y: (parts[n][scen][y] / lowsum[y] if lowsum[y] > 0 else 0.0) for y in lowsum}
            for n in LOW
        }

        g0 = interp(base_year, gen_over_fe)  # regional electrification at the base year
        l0 = interp(base_year, low_frac)  # regional low share at the base year

        rec = {
            "emisMt": [],
            "populationFactor": [],
            "gdpPerCapitaFactor": [],
            "demandFactor": [],
            "r10FinalEnergyIntensityFactor": [],
            "incomeElasticity": [],
            "elecShare": [],
            "lowShare": [],
            "energyTJ": [],
            "r10EnergyIntensityFactor": [],
            "lowMix": {n: [] for n in LOW},
            "popN": [],
            "gensetFossil": [],
        }
        p0, y0 = pop[narrative][base_year], (gdp[narrative][base_year] / pop[narrative][base_year])
        p_anchor = interp(anchor_year, pop[narrative])
        y_anchor = interp(anchor_year, gdp[narrative]) / p_anchor

        for y in years:
            # 1. ECONOMY-WIDE EMISSIONS -- Nigeria-specific socioeconomic
            #    pressure construction. The observed 2024 fossil-and-industrial
            #    CO2 level is scaled by population and the integrated
            #    Burke & Csereklyei aggregate-energy relation. The R10
            #    efficiency residual (see r10_efficiency) supplies an aggregate
            #    proxy for efficiency, structure, and technology change. R10 carbon
            #    intensity is deliberately not transferred.
            pt = interp(y, pop[narrative])
            yt = interp(y, gdp[narrative]) / pt
            p_factor = pt / p_anchor
            y_factor = yt / y_anchor
            log_income = math.log(y_factor)
            demand_factor = p_factor * math.exp(
                elasticity * log_income + elasticity_q * log_income * log_income
            )
            marginal_beta = elasticity + 2.0 * elasticity_q * log_income
            r10_factor = r10_efficiency(y, anchor_year)
            rec["populationFactor"].append(round(p_factor, 6))
            rec["gdpPerCapitaFactor"].append(round(y_factor, 6))
            rec["demandFactor"].append(round(demand_factor, 6))
            rec["r10FinalEnergyIntensityFactor"].append(round(r10_factor, 6))
            rec["incomeElasticity"].append(round(marginal_beta, 6))
            rec["emisMt"].append(round(max(0.0, p.anchor_mt * demand_factor * r10_factor), 3))

            # 2. ELECTRIFICATION -- index on the generation basis, both sides.
            rec["elecShare"].append(round(min(1.0, elec_base * interp(y, gen_over_fe) / g0), 6))

            # 3. LAYER 1 -- low-emission share of all electricity, index-transferred.
            rec["lowShare"].append(round(min(1.0, low_base * interp(y, low_frac) / l0), 6))

            # 4. LAYER 2 -- within-low composition, converging from Nigeria's own
            #    2023 split toward the regional one, linear over 2023-2100.
            #    Nigeria is 97.7% hydro today; holding that fixed would meet a
            #    rising low share almost entirely with hydro its rivers cannot
            #    supply. The regional composition is a technology signal, not a
            #    policy one -- SSP3 stays hydro-heavy, SSP1 goes wind-and-solar.
            f = min(1.0, max(0.0, (y - base_year) / float(end_year - base_year)))
            for n in LOW:
                rec["lowMix"][n].append(
                    round(lowmix_base[n] + f * (interp(y, lowmix[n]) - lowmix_base[n]), 6)
                )

            # 5. TOTAL FINAL ENERGY on the baseline. THE GDP SLIDER MUST NOT
            #    ENTER HERE -- it is a policy lever and this is the no-policy
            #    case. The prototype's stage-sensitive demand form is used
            #    unchanged,
            #        E(t) = E_2023 x (Pop_t/Pop_2023)
            #               x exp(B0 L + Q L^2), L = ln(y_t/y_2023),
            #    so the marginal beta is B0 + 2 Q L rather than one fixed B.
            #    The same R10 efficiency residual is then
            #    applied to this baseline energy path as a scenario-wide
            #    efficiency/structure/technology envelope. It is normalized
            #    separately to 2023 so the observed final-energy anchor stays
            #    exactly at total_final_energy_tj.
            #    but y is the SCENARIO's own GDP per capita for NIGERIA (IIASA
            #    export, OECD ENV-Growth 2025, GDP|PPP in billion USD_2015/yr),
            #    not the user's growth rate. Only the ratio is used, so the
            #    currency base is immaterial.
            pt = interp(y, pop[narrative])
            yt = interp(y, gdp[narrative]) / pt
            L = math.log(yt / y0)
            income_factor = math.exp(elasticity * L + elasticity_q * L * L)
            r10_energy_factor = r10_efficiency(y, base_year)
            rec["energyTJ"].append(
                round(p.tfe_tj * (pt / p0) * income_factor * r10_energy_factor, 1)
            )
            rec["r10EnergyIntensityFactor"].append(round(r10_energy_factor, 6))
            rec["popN"].append(int(round(pt)))

            # 6. THE FOSSIL SPLIT.  k = k0 x e0/e  -- back-up generators' share
            #    of fossil electricity falls in inverse proportion to
            #    electrification, on the reasoning that what retires a
            #    generator is the grid arriving. Per's ruling of 2026-09-09 is
            #    that gensets are a share of the fossil part of the mix (so
            #    100% renewable stays reachable); the inverse-proportional FORM
            #    is this generator's choice, picked among four candidate rules
            #    on the absolute fleet each implied:
            #      held at k0          k = k0
            #      k0 x e0/e           k = k0 x e0/e            <- taken
            #      g0 x e0/e           k = (g0 x e0/e) / (1-low)  (g0 = gensets'
            #                                     share of ALL electricity, 2023)
            #      k0 x (1-e)/(1-e0)   k = k0 x (1-e)/(1-e0)
            #    The 2100 fleets are NOT quoted here. They depend on the energy
            #    path, and a set written into this comment on 2026-09-10 went
            #    stale three days later when the R10 intensity proxy lowered
            #    that path -- and was then copied into a memo as evidence
            #    (03_models/2026-09-14_genset-baseline-validation-limits.md,
            #    corrected 2026-09-20). They are printed instead, every run, in
            #    the CANDIDATE RULES table of print_diagnostics(); read them
            #    there. On the 2026-09-20 path the taken rule was the
            #    LOWEST of the four, and it shrinks the fleet only under the
            #    SSP1 markers; the share k falls under every marker, the fleet
            #    does not.
            #    Gas is the residual, 1 - k, so the baseline's fossil half
            #    decarbonises by diesel-to-gas substitution -- 1.27 kg CO2/kWh
            #    down to 0.608, roughly halving each displaced kilowatt-hour.
            #    [GAP: inverse proportionality asserts that k x e is constant.
            #    Nothing in this repository measures Nigerian grid reliability,
            #    so only the direction of the SHARE and the 2023 level are
            #    defensible; nothing held here discriminates between the four
            #    rules.]
            e_t = rec["elecShare"][-1]
            rec["gensetFossil"].append(round(min(max(p.k0 * elec_base / e_t, 0.0), 1.0), 6))

        # --- 7. THE REGION'S RESOURCE ENVELOPE, applied to the whole trajectory --
        low_twh = [
            rec["lowShare"][i] * rec["elecShare"][i] * rec["energyTJ"][i] / TJ_PER_GWH / 1000.0
            for i in range(len(years))
        ]
        desired = [{n: rec["lowMix"][n][i] for n in LOW} for i in range(len(years))]
        capped = apply_envelope(p, desired, low_twh)
        for i in range(len(years)):
            for n in LOW:
                rec["lowMix"][n][i] = round(capped[i][n], 6)

        anchor_index = years.index(anchor_year)
        if abs(rec["emisMt"][anchor_index] - p.anchor_mt) > 0.001:
            raise ValueError("%s: %d emissions anchor is not reproduced" % (scen, anchor_year))
        block[pid] = rec

        # --- self-checks, printed not asserted away ------------------------
        checks.append(
            (
                pid,
                abs(rec["elecShare"][0] - elec_base),
                abs(rec["lowShare"][0] - low_base),
                abs(sum(rec["lowMix"][n][0] for n in LOW) - 1.0),
                max(abs(sum(rec["lowMix"][n][i] for n in LOW) - 1.0) for i in range(len(years))),
            )
        )

    cook = {
        narr: [
            round(cook_index(gdp[narr], pop[narr], y, base_year, p.cook_elasticity), 7)
            for y in years
        ]
        for narr in p.narratives
    }
    return BaselineResult(
        params=p, years=years, block=block, checks=checks, pop=pop, gdp=gdp, cook=cook
    )


def print_diagnostics(result: BaselineResult) -> None:
    """Self-checks, the envelope at its caps and the candidate fossil-split rules."""

    p, years, block = result.params, result.years, result.block
    b, mid, end = p.base_year, p.diagnostics_year, p.end_year
    print("CHECKS  (all should be ~0)")
    print(
        "%-8s %12s %12s %12s %12s"
        % ("marker", "elec@%d" % b, "low@%d" % b, "mix@%d" % b, "mix worst")
    )
    for c in result.checks:
        print("%-8s %12.2e %12.2e %12.2e %12.2e" % c)
    print()
    print(
        "%s anchors reproduced: elec %.6f  low %.6f  hydro %.6f  k0 %.6f"
        % (p.region_name, p.elec_base, p.low_base, p.lowmix_base["Hydro"], p.k0)
    )
    print()
    print(
        "ENVELOPE  hydro ceiling %.1f TWh (%s GW x %.3f)   wind ceiling %.1f TWh (%s GW x %.2f)"
        % (p.ceil_hydro, p.hydro_ceiling_gw, p.cf_hydro, p.ceil_wind, p.wind_ceiling_gw, p.cf_wind)
    )
    print(
        "%-8s low-emission generation at its cap, TWh (hydro / wind), %d and %d"
        % ("marker", mid, end)
    )
    for pid in p.markers:
        r = block[pid]
        i_mid, i_end = years.index(mid), years.index(end)

        def lt(i, r=r):
            return r["lowShare"][i] * r["elecShare"][i] * r["energyTJ"][i] / TJ_PER_GWH / 1000.0

        print(
            "%-8s %d hydro %6.1f  wind %5.1f   |   %d hydro %6.1f  wind %5.1f   |  "
            "genset share of fossil %5.1f%% -> %4.1f%%"
            % (
                pid,
                mid,
                r["lowMix"]["Hydro"][i_mid] * lt(i_mid),
                r["lowMix"]["Wind"][i_mid] * lt(i_mid),
                end,
                r["lowMix"]["Hydro"][i_end] * lt(i_end),
                r["lowMix"]["Wind"][i_end] * lt(i_end),
                r["gensetFossil"][i_mid] * 100,
                r["gensetFossil"][i_end] * 100,
            )
        )
    print()

    # The four candidate rules for the fossil split (section 6 in build_baseline),
    # as the absolute back-up-generator fleet each implies in the end year.
    # Printed rather than written into a comment because the figures move
    # with the energy path -- see the section 6 comment for what happened
    # when they were hard-coded. fleet = elec x energy/3.6 x (1-low) x k.
    e0, k0 = p.elec_base, p.k0
    g0 = p.genset_gwh / p.all_gwh
    print(
        "CANDIDATE RULES  back-up-generator fleet in %d, TWh, from %.1f TWh in %d"
        % (end, p.genset_gwh / 1000.0, b)
    )
    print(
        "%-8s %12s %12s %12s %18s" % ("marker", "held k0", "k0*e0/e", "g0*e0/e", "k0*(1-e)/(1-e0)")
    )
    for pid in p.markers:
        r = block[pid]
        i = years.index(end)
        e, low = r["elecShare"][i], r["lowShare"][i]
        total = e * r["energyTJ"][i] / TJ_PER_GWH / 1000.0
        fossil = total * (1.0 - low)
        print(
            "%-8s %12.1f %12.1f %12.1f %18.1f"
            % (
                pid,
                fossil * k0,
                fossil * r["gensetFossil"][i],
                total * g0 * e0 / e,
                fossil * k0 * (1.0 - e) / (1.0 - e0),
            )
        )
    print("(taken: k0*e0/e -- the column that must equal gensetFossil x fossil generation)")
    print()

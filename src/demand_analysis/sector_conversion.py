"""Sector-wise energy conversion factors under electrification.

EXPERIMENT BRANCH `experiment/partial-adjustment`, written 2026-10-09.
Companion to SECTOR_CONVERSION.md. Explores the question Per raised on
2026-10-09: when end uses move from fuels to electricity, the final energy
needed for the same energy service falls (an electric stove or motor turns
more of its input into service than a fire or an engine), while the primary
energy behind each unit of final electricity depends on the power mix. A
single primary-to-final factor therefore cannot be fixed in advance; it is
the share-weighted result of sector-by-sector transitions.

Nothing here changes the variant, the baseline builder or the prototype.

Sections
  1. Nigeria 2023 final energy by sector and carrier: IEA current release
     (28 Sep 2026) sector-by-fuel table, with UNSD splitting each IEA fuel
     cell into the carriers the efficiency ratios need
  2. Primary-to-final factors by carrier, 2023, and the bottom-up P/F
  3. End-use efficiency ratios rho = eta_electric / eta_displaced, with
     the evidence behind each range
  4. National electrification -> final energy, by sector allocation rule
     (constant energy service); electricity and P/F under four power mixes
  5. Back-up generators: the boundary term
  6. IMAGE Africa R10: how P/F and the final-energy elasticity move with
     the SSP's own sector transitions, and a useful-energy check on R&C
  7. What it means for the demand law: eps_final = eps_primary - eps_P/F,
     and an SSP2-4.5 2050 illustration

Run: python scripts/run_sector_conversion.py --config config.yaml
(report in sector_conversion_output.txt)

The efficiency ratios, electrification targets, genset efficiencies, the UNSD
code maps, the low-emission power case, the ETP and IMAGE years and the
illustration marker come from the ``sector_conversion`` section of the
configuration; the back-up generator output from ``ssp_baseline.anchors`` and the
IEA generation lines from ``inputs.iea_generation_lines``. The report text
describes the 2023 IEA/UNSD snapshot the inputs hold.
"""

from __future__ import annotations

import csv
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config_paths import ConfigError, require, require_path
from scenario_data import Marker, interp, load_markers, read_label_values, read_series
from ssp_baseline import block_series as read_block_series, block_years
from units import TJ_PER_GWH


@dataclass(frozen=True)
class SectorConversionParams:
    region_name: str
    markers: dict[str, Marker]
    base_year: int
    end_year: int
    image_dir: Path
    unsd: Path
    iea_final_current: Path
    iea_electricity_current: Path
    iea_tes_2023: Path
    iea_tfc_2023: Path
    etp_cooking: Path
    baseline_block: Path
    genset_gwh: float
    generation_lines: dict[str, str]  # IAMC source -> line of the IEA electricity table
    unsd_carriers: dict[str, str]  # UNSD COMMODITY code -> carrier (CARRIERS)
    unsd_sectors: dict[str, str]  # UNSD TRANSACTION code -> sector (SECTORS)
    unsd_flows: dict[str, tuple[str, str]]  # section 2 flows, (COMMODITY, TRANSACTION)
    low_share: float  # low-emission share of generation in section 2's second power case
    etp_years: tuple[int, int]  # ETP cooking charts: (year of all stoves, later year)
    image_reference_year: int
    image_comparison_years: tuple[int, ...]
    rho: dict[tuple[str, str], tuple[float, float, float]]
    targets: tuple[float, ...]
    genset_efficiencies: tuple[float, ...]
    useful_electric_efficiency: float
    useful_other_fuel_rho: float
    useful_solid_biomass_rho: float
    illustration_pathway: str
    illustration_year: int

    @classmethod
    def from_config(cls, config: Mapping[str, Any]) -> SectorConversionParams:
        s = "sector_conversion"
        rho = {}
        for group, carriers in require(config, f"{s}.rho").items():
            for carrier, values in carriers.items():
                if len(values) != 3:
                    raise ValueError(f"{s}.rho.{group}.{carrier}: need (low, central, high)")
                rho[(group, carrier)] = tuple(float(v) for v in values)
        pathway = require(config, f"{s}.illustration_pathway")
        require(config, f"scenarios.{pathway}")
        lines = dict(require(config, "inputs.iea_generation_lines"))
        if "Gas" not in lines or not set(lines) - {"Gas"} <= set(AT_OUTPUT):
            # Section 2 measures thermal efficiency on the UNSD gas-plant pair only and
            # counts every other source at output.
            raise ConfigError(
                "inputs.iea_generation_lines: section 2 needs a Gas line and otherwise only "
                f"sources counted at output {AT_OUTPUT}; got {sorted(lines)}"
            )
        carriers = _codes(config, f"{s}.unsd.carriers", CARRIERS)
        if list(carriers.values()).count("electricity") != 1:
            raise ConfigError(f"{s}.unsd.carriers: map exactly one commodity to electricity")
        flows = {}
        for name in UNSD_FLOWS:
            pair = require(config, f"{s}.unsd.flows.{name}")
            if len(pair) != 2 or not all(isinstance(c, str) for c in pair):
                raise ConfigError(f"{s}.unsd.flows.{name}: need two quoted codes")
            flows[name] = (pair[0], pair[1])
        etp_years = tuple(int(y) for y in require(config, f"{s}.etp_cooking_years"))
        if len(etp_years) != 2:
            raise ConfigError(f"{s}.etp_cooking_years: need [year of all stoves, later year]")
        return cls(
            region_name=require(config, "region.name"),
            markers=load_markers(config),
            base_year=int(require(config, "time_horizon.base_year")),
            end_year=int(require(config, "time_horizon.end_year")),
            image_dir=require_path(config, "inputs.image_dir"),
            unsd=require_path(config, "inputs.unsd_energy"),
            iea_final_current=require_path(config, "inputs.iea.final_by_fuel_and_sector_current"),
            iea_electricity_current=require_path(config, "inputs.iea.electricity_current"),
            iea_tes_2023=require_path(config, "inputs.iea.total_energy_supply_2023"),
            iea_tfc_2023=require_path(config, "inputs.iea.final_by_sector_2023"),
            etp_cooking=require_path(config, "inputs.etp_cooking"),
            baseline_block=require_path(config, "ssp_baseline.output_block"),
            genset_gwh=require(config, "ssp_baseline.anchors.genset_gwh"),
            generation_lines=lines,
            unsd_carriers=carriers,
            unsd_sectors=_codes(config, f"{s}.unsd.sectors", SECTORS),
            unsd_flows=flows,
            low_share=require(config, f"{s}.low_emission_power_share"),
            etp_years=etp_years,
            image_reference_year=int(require(config, f"{s}.image_reference_year")),
            image_comparison_years=tuple(
                int(y) for y in require(config, f"{s}.image_comparison_years")
            ),
            rho=rho,
            targets=tuple(require(config, f"{s}.electrification_targets")),
            genset_efficiencies=tuple(require(config, f"{s}.genset_efficiencies")),
            useful_electric_efficiency=require(
                config, f"{s}.useful_energy_check.electric_efficiency"
            ),
            useful_other_fuel_rho=require(config, f"{s}.useful_energy_check.other_fuel_rho"),
            useful_solid_biomass_rho=require(config, f"{s}.useful_energy_check.solid_biomass_rho"),
            illustration_pathway=pathway,
            illustration_year=int(require(config, f"{s}.illustration_year")),
        )

    @property
    def years(self) -> list[int]:
        return list(range(self.base_year, self.end_year + 1))

    @property
    def low_case(self) -> str:
        """Name of section 2's low-emission power case, e.g. electricity_72pc_low."""
        return "electricity_%.0fpc_low" % (100 * self.low_share)


def _codes(config: Mapping[str, Any], key: str, allowed: list[str]) -> dict[str, str]:
    """A UNSD code map: quoted codes onto names this module knows."""
    codes = dict(require(config, key))
    for code, name in codes.items():
        if not isinstance(code, str):
            raise ConfigError(f"{key}: code {code!r} must be quoted (YAML reads 0100 as 64)")
        if name not in allowed:
            raise ConfigError(f"{key}.{code}: {name!r} is not one of {allowed}")
    return codes


# Sources whose generation section 2 counts at output (primary = generation).
AT_OUTPUT = ("Hydro", "Solar", "Wind")
# The UNSD (COMMODITY, TRANSACTION) flows section 2 reads (sector_conversion.unsd.flows).
UNSD_FLOWS = ("gas_to_power", "thermal_output", "wood_to_kilns", "charcoal_output", "gas_own_use")


# --------------------------------------------------------------------------
# 1. BASE YEAR BY SECTOR AND CARRIER (UNSD)
# Carriers and sectors are the names below; the UNSD codes that map onto them
# are configuration (sector_conversion.unsd).
CARRIERS = [
    "wood",
    "charcoal",
    "lpg",
    "kerosene",
    "gas",
    "coal",
    "fuel_oil",
    "gasoline",
    "diesel",
    "jet",
    "other_oil",
    "electricity",
]
SECTORS = [
    "residential",
    "commercial",
    "industry",
    "transport",
    "agriculture",
    "other",
    "non_energy",
]


def unsd_2023(p: SectorConversionParams):
    """Final energy in TJ, {sector: {carrier: TJ}}, plus the transformation
    rows needed for primary-energy factors."""
    carrier, sector = p.unsd_carriers, p.unsd_sectors
    m = {s: {c: 0.0 for c in CARRIERS} for s in SECTORS}
    extra = {}
    with p.unsd.open(encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            if r["TIME_PERIOD"] != str(p.base_year):
                continue
            com, tr, v = r["COMMODITY"], r["TRANSACTION"], float(r["OBS_VALUE"])
            if carrier.get(com) == "electricity":
                tj = v * TJ_PER_GWH
            elif r["UNIT_MEASURE"] == "TJ":
                tj = v
            else:
                tj = v * float(r["CONVERSION_FACTOR"] or 0)
            extra[(com, tr)] = tj
            if com in carrier and tr in sector:
                m[sector[tr]][carrier[com]] += tj
    return m, extra


IEA_SECTOR = {
    "Industry": "industry",
    "Transport": "transport",
    "Residential": "residential",
    "Commercial and public services": "commercial",
    "Agriculture and forestry": "agriculture",
    "Other non-specified": "other",
    "Non-energy use": "non_energy",
}
IEA_FUEL = {
    "coal_and_coal_products_TJ": "coal",
    "oil_products_TJ": "oil",
    "natural_gas_TJ": "gas",
    "biofuels_and_waste_TJ": "bio",
    "electricity_TJ": "electricity",
}
FUEL_GROUP = {
    "wood": "bio",
    "charcoal": "bio",
    "lpg": "oil",
    "kerosene": "oil",
    "gasoline": "oil",
    "diesel": "oil",
    "jet": "oil",
    "fuel_oil": "oil",
    "other_oil": "oil",
    "gas": "gas",
    "coal": "coal",
    "electricity": "electricity",
}
GROUP_DEFAULT = {
    "bio": "wood",
    "oil": "diesel",
    "gas": "gas",
    "coal": "coal",
    "electricity": "electricity",
}


def iea_current(p: SectorConversionParams, u):
    """IEA current-release 2023 final consumption, {sector: {carrier: TJ}}.
    The IEA table has five fuels; each cell is split into the carriers of
    CARRIERS in proportion to the UNSD 2023 split of the same sector and fuel
    group (wood vs charcoal; LPG, kerosene, petrol, diesel, jet, fuel oil).
    The IEA cell sets the level, UNSD only the within-cell shares."""
    m = {s: {c: 0.0 for c in CARRIERS} for s in SECTORS}
    with p.iea_final_current.open(encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            if r["sector"] not in IEA_SECTOR:
                continue
            s = IEA_SECTOR[r["sector"]]
            for col, g in IEA_FUEL.items():
                v = float(r[col]) if r[col].strip() else 0.0
                members = [c for c in CARRIERS if FUEL_GROUP[c] == g]
                base = sum(u[s][c] for c in members)
                if base > 0:
                    for c in members:
                        m[s][c] += v * u[s][c] / base
                else:
                    m[s][GROUP_DEFAULT[g]] += v
    return m


def iea_electricity(p: SectorConversionParams):
    with p.iea_electricity_current.open(encoding="utf-8-sig") as fh:
        return {r["line"]: float(r["value_GWh"]) for r in csv.DictReader(fh)}


def grid_generation(p: SectorConversionParams, el) -> float:
    """Base-year grid generation, GWh: the configured IEA generation lines summed."""
    return sum(el[line] for line in p.generation_lines.values())


def section1(p: SectorConversionParams):
    u, extra = unsd_2023(p)
    m = iea_current(p, u)
    print(
        "1. %s 2023 FINAL ENERGY BY SECTOR AND CARRIER (IEA current release, PJ;"
        % p.region_name.upper()
    )
    print("   UNSD 2023 splits each IEA fuel cell into carriers)")
    print("  %-12s" % "" + "".join("%9s" % c[:8] for c in CARRIERS) + "%9s" % "total")
    for s in SECTORS:
        print(
            "  %-12s" % s
            + "".join("%9.1f" % (m[s][c] / 1e3) for c in CARRIERS)
            + "%9.1f" % (sum(m[s].values()) / 1e3)
        )
    col = {c: sum(m[s][c] for s in SECTORS) for c in CARRIERS}
    tot = sum(col.values())
    print(
        "  %-12s" % "total"
        + "".join("%9.1f" % (col[c] / 1e3) for c in CARRIERS)
        + "%9.1f" % (tot / 1e3)
    )
    print("  check, sector totals PJ (UNSD / IEA current release):")
    print(
        "   "
        + "  ".join(
            "%s %.0f/%.0f" % (s[:5], sum(u[s].values()) / 1e3, sum(m[s].values()) / 1e3)
            for s in SECTORS
        )
    )

    def ub(s):
        return (u[s]["wood"] + u[s]["charcoal"]) / 1000.0

    def mb(s):
        return (m[s]["wood"] + m[s]["charcoal"]) / 1000.0

    print(
        "   biomass by sector (UNSD / IEA): "
        + "  ".join(
            "%s %.0f/%.0f" % (s[:5], ub(s), mb(s))
            for s in ("residential", "commercial", "industry")
        )
    )
    print("   total %.0f / %.0f PJ" % (sum(sum(u[s].values()) for s in SECTORS) / 1e3, tot / 1e3))
    bio = sum(m[s]["wood"] + m[s]["charcoal"] for s in SECTORS)
    print(
        "  biomass (wood, residues, charcoal) %.0f PJ = %.1f%% of final energy; residential"
        % (bio / 1e3, 100 * bio / tot)
    )
    print(
        "  %.0f PJ of it; electricity %.2f%% of final energy"
        % (
            (m["residential"]["wood"] + m["residential"]["charcoal"]) / 1e3,
            100 * col["electricity"] / tot,
        )
    )
    print()
    return m, extra


# --------------------------------------------------------------------------
# 2. PRIMARY-TO-FINAL FACTORS BY CARRIER, 2023
def section2(p: SectorConversionParams, m, extra):
    el = iea_electricity(p)  # IEA current release, GWh
    gen = grid_generation(p, el)
    fin_el = sum(m[s]["electricity"] for s in SECTORS)
    flow = p.unsd_flows
    gas_in = extra[flow["gas_to_power"]]  # UNSD: gas into power plants
    gas_gen = extra[flow["thermal_output"]]  # UNSD: gas-fired output
    wood_in = extra[flow["wood_to_kilns"]]  # wood into charcoal kilns
    char_out = extra[flow["charcoal_output"]]  # charcoal produced
    eta_gas = gas_gen / gas_in  # UNSD pair, one source
    gap = gen / el["Total final consumption"]  # generation per final kWh
    gas_sh = el[p.generation_lines["Gas"]] / gen
    low = p.low_share
    pef = {
        "electricity_2023": gap * (gas_sh / eta_gas + (1 - gas_sh)),
        "electricity_all_gas": gap / eta_gas,
        p.low_case: gap * (low + (1 - low) / eta_gas),
        "electricity_all_solar_hydro": gap,
    }
    kiln = char_out / wood_in
    pef_fuel = {c: 1.0 for c in CARRIERS}
    pef_fuel["charcoal"] = 1 / kiln
    print("2. PRIMARY-TO-FINAL FACTORS (PEF, primary per unit of final), 2023")
    print(
        "  gas plants: %.0f TJ in -> %.0f TJ out, efficiency %.3f (UNSD 088 and output)"
        % (gas_in, gas_gen, eta_gas)
    )
    print(
        "  generation / final electricity = %.0f / %.0f GWh = %.4f (IEA current release; exports,"
        % (gen, el["Total final consumption"], gap)
    )
    print(
        "  own use, losses fixed at 15%%, and a statistical difference); gas %.1f%% of generation"
        % (100 * gas_sh)
    )
    print(
        "  charcoal kilns: %.0f TJ wood -> %.0f TJ charcoal, efficiency %.3f -> PEF %.2f"
        % (wood_in, char_out, kiln, 1 / kiln)
    )
    print("  electricity PEF per final unit (non-combustible renewables at output, the IEA")
    print("  physical-energy-content convention that the paper's TPES uses):")
    for k, v in pef.items():
        print("    %-30s %.3f" % (k, v))
    tfc = sum(sum(m[s].values()) for s in SECTORS)
    bottom = (
        sum(m[s][c] * pef_fuel[c] for s in SECTORS for c in CARRIERS if c != "electricity")
        + fin_el * pef["electricity_2023"]
    )
    # TES is held only for the older release, so it is compared with the older
    # release's own TFC, never with the current-release matrix
    tes_old = sum(read_label_values(p.iea_tes_2023).values())
    tfc_old = sum(read_label_values(p.iea_tfc_2023).values())
    print(
        "  P/F bottom-up %.3f (demand-linked conversion only); IEA TES/TFC %.3f (older release,"
        % (bottom / tfc, tes_old / tfc_old)
    )
    print("  the only TES held). The difference is mainly gas burned by the oil and gas industry")
    print(
        "  itself (UNSD 0912 %.0f PJ) and statistical differences, tied to production for export."
        % (extra[flow["gas_own_use"]] / 1e3)
    )
    print()
    return pef, pef_fuel


# --------------------------------------------------------------------------
# 3. END-USE EFFICIENCY RATIOS rho = eta_elec / eta_displaced (low, central, high)
def etp_ratios(p: SectorConversionParams):
    rows = {}
    with p.etp_cooking.open(encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            rows[(r["chart"], r["series"])] = r

    def st(s, y):
        return float(rows["national_stoves", s][y])

    def pj(s, y):
        return float(rows["fuel_demand", s][y])

    y0, y1 = (str(y) for y in p.etp_years)
    bio0 = pj("Biomass", y0) / (st("Traditional biomass", y0) + st("Biofuels", y0))
    lpg0 = pj("LPG", y0) / st("LPG", y0)
    el0 = pj("Electric", y0) / st("Electric", y0)
    el1 = pj("Electric", y1) / st("Electric", y1)
    lpg1 = pj("LPG", y1) / st("LPG", y1)
    return bio0, lpg0, el0, el1, lpg1


# rho = eta_electric / eta_displaced, (low, central, high) by (sector group,
# carrier), comes from sector_conversion.rho in the configuration.
GROUP = {
    "residential": "household",
    "commercial": "household",
    "industry": "industry",
    "agriculture": "industry",
    "other": "household",
    "transport": "transport",
}
NOT_ELECTRIFIABLE = {("transport", "jet"), ("transport", "other_oil")}


def rho_for(rho, sector, carrier, case):
    g = GROUP.get(sector)
    if (
        g is None
        or carrier in ("electricity", "other_oil")
        or (sector, carrier) in NOT_ELECTRIFIABLE
    ):
        return None
    if g == "transport":
        key = ("transport", "road")
    elif (
        g == "industry"
        and carrier not in ("wood", "charcoal")
        or g == "household"
        and carrier in ("gasoline", "diesel", "fuel_oil", "coal")
    ):
        key = ("industry", "fossil")
    else:
        key = (g, carrier)
    return rho[key][case]


def section3(p: SectorConversionParams):
    bio0, lpg0, el0, el1, lpg1 = etp_ratios(p)
    y0, y1 = p.etp_years
    print("3. END-USE EFFICIENCY RATIOS rho = eta_electric / eta_displaced")
    print("  Evidence (final energy for the same service; ratios derived here unless stated):")
    print(
        "  - ETP 2.0 cooking charts (%s, net-zero pathway, pp. 37-40), per stove per year:"
        % p.region_name
    )
    print(
        "    biomass %.2f GJ, LPG %.2f GJ (%d); electric %.2f GJ (%d), %.2f GJ (%d), "
        "LPG %.2f GJ (%d)"
        % (bio0 * 1e3, lpg0 * 1e3, y0, el0 * 1e3, y0, el1 * 1e3, y1, lpg1 * 1e3, y1)
    )
    print(
        "    -> biomass/electric %.1f-%.1f, LPG/electric %.1f-%.1f, if service per stove is equal"
        % (bio0 / el1, bio0 / el0, lpg0 / el1, lpg0 / el0)
    )
    print("    (an assumption; the ETP states no efficiencies and its PJ do not match IEA levels)")
    print(
        "  - Uganda controlled cooking test (Ahimbisibwe et al. 2025, Archives of Agriculture and"
    )
    print(
        "    Environmental Science 10(2):303-315; read 2026-10-09, MSc-thesis sources.yaml), "
        "Table 2,"
    )
    print(
        "    MJ per 0.5 kg test meal of beans (labelled per kg in the paper): hotplate 10.42 (rated"
    )
    print("    1000 W x 174 min, not metered), LPG 13.28, improved wood 38.81, three-stone 102.44,")
    print("    charcoal 9.18 / 6.72, briquettes 5.18 / 3.75")
    print("    -> three-stone/electric 9.8, improved wood/electric 3.7, LPG/electric 1.27,")
    print("       charcoal/electric 0.64-0.88 (BELOW 1, against the charcoal range used)")
    print("    Low confidence: single values, no variance, internal inconsistencies.")
    print(
        "  - Akpasoh & Edeminam 2023, Nigeria CCT (sources.yaml; LHVs assumed): electric pressure"
    )
    print("    cooker vs LPG 3.7-7.1, vs kerosene 1.7-3.6 -- an upper bound (sealed cooker)")
    print("  - US DOE (fueleconomy.gov / Fact #750, via web search): EV ~60% grid-to-wheel (77%")
    print("    older figure), gasoline vehicles 12-30% -> ratio about 2.3-5")
    print("  - Back-up gensets 15-25% fuel-to-electricity (2026-08-29 boundary memo) -> 4-6.7")
    print("  - Industry: no source held; boiler vs resistance heating assumed 1.0-1.5, fuelwood")
    print(
        "    process heat vs electric 1.5-4. ASSUMPTIONS, flagged. "
        "The ETP industry charts (pp.27-29)"
    )
    print(
        "    switch fuels one-for-one, heat pumps included (rho = 1), so they give no basis either."
    )
    print("  Ranges used (low / central / high):")
    for k, v in p.rho.items():
        print("    %-24s %4.1f %4.1f %4.1f" % ("%s, %s" % k, *v))
    print("  Not electrifiable here: aviation fuel, lubricants/bitumen, non-energy use.")
    print()


# --------------------------------------------------------------------------
# 4. NATIONAL ELECTRIFICATION -> FINAL ENERGY, BY ALLOCATION RULE
def pools(rho, m, case):
    """Electrifiable non-electric final energy: list of (sector, carrier, TJ, rho)."""
    out = []
    for s in SECTORS:
        for c in CARRIERS:
            r = rho_for(rho, s, c, case) if m[s][c] > 0 else None
            if r is not None:
                out.append((s, c, m[s][c], r))
    return out


ORDER = {
    "cooking first": ["residential", "commercial", "other", "transport", "industry", "agriculture"],
    "transport first": [
        "transport",
        "residential",
        "commercial",
        "other",
        "industry",
        "agriculture",
    ],
    "industry first": [
        "industry",
        "agriculture",
        "transport",
        "commercial",
        "other",
        "residential",
    ],
}


def displace(pl, rule, t, weights=None):
    """Displacement d_p for each pool at scale parameter t in [0, 1]."""
    if rule == "pro rata":
        return [t * p[2] for p in pl]
    if rule == "IMAGE pattern":
        # new electricity by sector proportional to IMAGE R10's own increments;
        # t scales the total; within a sector pro rata across carriers.
        # At t = 1 every sector is fully switched (scale 1/min weight).
        d = [0.0] * len(pl)
        xmax = sum(p[2] / p[3] for p in pl) / min(weights.values())
        for g, w in weights.items():
            idx = [i for i, p in enumerate(pl) if GROUP.get(p[0]) == g]
            A = sum(pl[i][2] / pl[i][3] for i in idx)
            f = min(1.0, t * xmax * w / A) if A else 0.0
            for i in idx:
                d[i] = f * pl[i][2]
        return d
    total = t * sum(p[2] for p in pl)
    d = []
    for _p in pl:
        d.append(0.0)
    for sec in ORDER[rule]:
        for i, p in enumerate(pl):
            if p[0] == sec and total > 0:
                take = min(p[2], total)
                d[i] = take
                total -= take
    return d


def outcome(m, pl, d):
    F0 = sum(sum(m[s].values()) for s in SECTORS)
    E0 = sum(m[s]["electricity"] for s in SECTORS)
    disp = sum(d)
    new_e = sum(di / p[3] for di, p in zip(d, pl, strict=False))
    F = F0 - disp + new_e
    return F, E0 + new_e, F0, E0


def solve(m, pl, rule, share, weights=None):
    lo, hi = 0.0, 1.0
    F, E, F0, E0 = outcome(m, pl, displace(pl, rule, hi, weights))
    if share > E / F:
        return None
    for _ in range(80):
        mid = (lo + hi) / 2
        F, E, _, _ = outcome(m, pl, displace(pl, rule, mid, weights))
        if share > E / F:
            lo = mid
        else:
            hi = mid
    d = displace(pl, rule, hi, weights)
    F, E, F0, E0 = outcome(m, pl, d)
    return F, E, F0, E0, d


def image_weights(p: SectorConversionParams):
    scen, y1 = p.markers[p.illustration_pathway].key, p.illustration_year

    def s(fn):
        return read_series(p.image_dir, fn)[scen]

    inc = {
        "household": s("Final Energy - Residential and Commercial - Electricity.csv"),
        "industry": s("Final Energy - Industry - Electricity.csv"),
        "transport": s("Final Energy - Transportation - Electricity.csv"),
    }
    dlt = {g: interp(y1, v) - interp(p.base_year, v) for g, v in inc.items()}
    tot = sum(dlt.values())
    return {g: v / tot for g, v in dlt.items()}


def p_over_f(m, pl, d, F, E, pef_el, pef_fuel):
    P = 0.0
    for s in SECTORS:
        for c in CARRIERS:
            if c != "electricity":
                P += m[s][c] * pef_fuel[c]
    for di, p in zip(d, pl, strict=False):
        P -= di * pef_fuel[p[1]]
    return (P + E * pef_el) / F


def section4(p: SectorConversionParams, m, pef, pef_fuel):
    w = image_weights(p)
    print("4. NATIONAL ELECTRIFICATION AT CONSTANT ENERGY SERVICE, 2023 STRUCTURE")
    print("  Target: electricity share of final energy (e). Displaced fuel d becomes d/rho of")
    print("  electricity. The prototype converts 1:1 (rho = 1). IMAGE pattern = new electricity")
    print(
        "  split as IMAGE R10 %s adds it %d-%d: "
        % (p.markers[p.illustration_pathway].label, p.base_year, p.illustration_year)
        + ", ".join("%s %.2f" % kv for kv in w.items())
    )
    F0 = sum(sum(m[s].values()) for s in SECTORS)
    E0 = sum(m[s]["electricity"] for s in SECTORS)
    print(
        "  2023: final energy %.0f PJ, electricity %.0f PJ (%.1f%%)"
        % (F0 / 1e3, E0 / 1e3, 100 * E0 / F0)
    )
    rules = ["pro rata", "cooking first", "transport first", "industry first", "IMAGE pattern"]
    targets = p.targets
    print()
    print("  F/F0 = final energy relative to 2023 at the same service (central rho; lo/hi =")
    print("  high/low rho). The 1:1 model keeps F/F0 = 1, so its electricity at the same share is")
    print("  1/(F/F0) times this. P/F and P/P0 (primary relative to 2023) with the 2023 grid and")
    low = "%.0f" % (100 * p.low_share)
    print("  with %s%% low-emission power (bottom-up convention of section 2)." % low)
    PF0 = p_over_f(
        m,
        pools(p.rho, m, 1),
        [0.0] * len(pools(p.rho, m, 1)),
        F0,
        E0,
        pef["electricity_2023"],
        pef_fuel,
    )
    print(
        "  %-16s %5s %8s %8s %9s %8s %8s %8s %8s"
        % (
            "rule",
            "e",
            "F/F0",
            "F/F0 lo",
            "F/F0 hi",
            "P/F 23",
            "P/F " + low,
            "P/P0 23",
            "P/P0 " + low,
        )
    )
    results = {}
    for rule in rules:
        for e in targets:
            row = {}
            for case in (0, 1, 2):
                pl = pools(p.rho, m, case)
                res = solve(m, pl, rule, e, w)
                row[case] = (res, pl)
            res, pl = row[1]
            if res is None:
                print("  %-16s %5.2f   not reachable (non-electrifiable uses remain)" % (rule, e))
                continue
            F, E, _, _, d = res
            lo = row[2][0][0] / F0 if row[2][0] else float("nan")  # high rho -> lowest F
            hi = row[0][0][0] / F0 if row[0][0] else float("nan")
            pf23 = p_over_f(m, pl, d, F, E, pef["electricity_2023"], pef_fuel)
            pf_low = p_over_f(m, pl, d, F, E, pef[p.low_case], pef_fuel)
            results[(rule, e)] = (F / F0, E, pf23, pf_low)
            print(
                "  %-16s %5.2f %8.3f %8.3f %9.3f %8.3f %8.3f %8.3f %8.3f"
                % (
                    rule,
                    e,
                    F / F0,
                    lo,
                    hi,
                    pf23,
                    pf_low,
                    pf23 * F / (PF0 * F0),
                    pf_low * F / (PF0 * F0),
                )
            )
    pl = pools(p.rho, m, 1)
    F, E, _, _ = outcome(m, pl, [p[2] for p in pl])
    print(
        "  maximum reachable share (all electrifiable uses switched, central rho): %.1f%%, "
        "final energy %.3f of 2023" % (100 * E / F, F / F0)
    )
    pf0 = p_over_f(m, pl, [0.0] * len(pl), F0, E0, pef["electricity_2023"], pef_fuel)
    print("  P/F today (bottom-up, same convention): %.3f" % pf0)
    print()
    return results


# --------------------------------------------------------------------------
# 5. GENSETS
def section5(p: SectorConversionParams, m):
    gwh = p.genset_gwh  # prototype's 2023 genset output estimate
    F0 = sum(sum(m[s].values()) for s in SECTORS)
    print("5. BACK-UP GENERATORS: THE BOUNDARY TERM")
    print(
        "  The prototype counts an estimated %.1f TWh of genset output as electricity, while"
        % (gwh / 1000)
    )
    print("  the fuel stays in final energy if it is recorded at all (UNSD books all petrol and")
    print(
        '  almost all diesel to road transport; the IEA says genset inputs and outputs "may not be'
    )
    print(
        '  properly reported", p. 502). Replacing that output with grid power at constant service:'
    )
    for eta in p.genset_efficiencies:
        fuel = gwh * TJ_PER_GWH / eta
        save = fuel - gwh * TJ_PER_GWH
        print(
            "    genset efficiency %.0f%%: fuel %.0f PJ, final energy falls by %.0f PJ "
            "(%.1f%% of 2023)" % (100 * eta, fuel / 1e3, save / 1e3, 100 * save / F0)
        )
    print("  ...if the fuel is inside final energy. If it is not recorded, final energy is")
    print("  understated today and nothing falls. The prototype's 2023 electrification share")
    print(
        "  (8.99%%, older release) also uses gross generation plus genset output, against %.2f%%"
        % (100 * sum(m[s]["electricity"] for s in SECTORS) / F0)
    )
    print("  final electricity in the balance; the share definition is itself a boundary choice.")
    print()


# --------------------------------------------------------------------------
# 6. IMAGE AFRICA R10
PRIMARY = ["Biomass", "Coal", "Gas", "Oil", "Hydro", "Nuclear", "Solar", "Wind"]


def section6(p: SectorConversionParams):
    def series(fn):
        return read_series(p.image_dir, fn)

    fe, gdp, pop = series("Final Energy.csv"), series("GDP - PPP.csv"), series("Population.csv")
    fel = series("Final Energy - Electricity.csv")
    fbio = series("Final Energy - Solids - Biomass.csv")
    prim = {k: series("Primary Energy - %s.csv" % k) for k in PRIMARY}
    # by-fuel rows, not the reported total, which the SSP1 by-fuel rows exceed
    # (scenario_compass_africa_r10/README.md)
    byfuel = {
        k: series("Secondary Energy - Electricity - %s.csv" % k)
        for k in ("Biomass", "Coal", "Gas", "Hydro", "Nuclear", "Oil", "Other", "Solar", "Wind")
    }
    LOWC = ("Hydro", "Solar", "Wind", "Nuclear", "Biomass")
    rc, rce = (
        series("Final Energy - Residential and Commercial.csv"),
        series("Final Energy - Residential and Commercial - Electricity.csv"),
    )
    rcb = series("Final Energy - Residential and Commercial - Solids - Biomass.csv")
    print("6. IMAGE 3.2 AFRICA R10: P/F MOVES WITH THE SSP'S OWN SECTOR TRANSITIONS")
    print("  P = sum of primary energy by source (IAMC direct-equivalent convention);")
    print("  F = final energy. eps = d ln(per-head quantity) / d ln(income per head).")
    print(
        "  %-7s %5s %7s %7s %7s %7s %8s | %7s %7s %7s"
        % (
            "marker",
            "year",
            "P/F",
            "el/F",
            "bio/F",
            "low/gen",
            "Pbio/Fbio",
            "eps_F",
            "eps_P",
            "eps_P/F",
        )
    )
    ref, compare = p.image_reference_year, p.image_comparison_years
    rows = {}
    for pid, marker in p.markers.items():
        sc = marker.key
        have = all(sc in prim[k] for k in PRIMARY)
        base = {}
        for y in (ref, *compare):
            F = interp(y, fe[sc])
            P = sum(interp(y, prim[k][sc]) for k in PRIMARY) if have else float("nan")
            yp = interp(y, gdp[sc]) / interp(y, pop[sc])
            n = interp(y, pop[sc])
            gen = sum(interp(y, byfuel[k][sc]) for k in byfuel if sc in byfuel[k])
            lowsh = sum(interp(y, byfuel[k][sc]) for k in LOWC if sc in byfuel[k]) / gen
            pb = interp(y, prim["Biomass"][sc]) / interp(y, fbio[sc]) if have else float("nan")
            vals = (P / F, interp(y, fel[sc]) / F, interp(y, fbio[sc]) / F, lowsh, pb)
            if y == ref:
                base = dict(F=F / n, P=P / n, y=yp, pf=P / F)
                tail = ""
            else:
                dl = math.log(yp / base["y"])
                eF = math.log((F / n) / base["F"]) / dl
                eP = math.log((P / n) / base["P"]) / dl if have else float("nan")
                tail = "%7.3f %7.3f %7.3f" % (eF, eP, eP - eF)
                rows[(pid, y)] = (eF, eP)
            print(
                "  %-7s %5d %7.3f %7.3f %7.3f %7.3f %8.2f | %s"
                % (pid, y, vals[0], vals[1], vals[2], vals[3], vals[4], tail)
            )
    print("  (SSP3 primary biomass is missing from the export, so its P is not formed.")
    print("  Pbio/Fbio = primary biomass per unit of final solid biomass: above 1 it carries")
    print("  modern bioenergy conversion -- biofuels, biomass power, BECCS in SSP1-1.9.)")
    print()
    # useful-energy check on Residential and Commercial
    eff = p.useful_electric_efficiency
    other_rho, bio_rho = p.useful_other_fuel_rho, p.useful_solid_biomass_rho
    print("  Useful-energy check, Residential and Commercial (central rho: electricity")
    print(
        "  eta %.2f, other fuels %.2f/%s, solid biomass %.2f/%s):"
        % (eff, eff, other_rho, eff, bio_rho)
    )
    print("  %-7s %6s %10s %10s %10s" % ("marker", "to", "eps_final", "eps_useful", "useful/F"))
    for pid, marker in p.markers.items():
        sc = marker.key

        def useful(y, sc=sc):
            t, e, b = interp(y, rc[sc]), interp(y, rce[sc]), interp(y, rcb[sc])
            return eff * e + (eff / other_rho) * (t - e - b) + (eff / bio_rho) * b, t

        u0, f0 = useful(ref)
        n0, y0 = interp(ref, pop[sc]), interp(ref, gdp[sc]) / interp(ref, pop[sc])
        for y in compare:
            u, f = useful(y)
            n, yp = interp(y, pop[sc]), interp(y, gdp[sc]) / interp(y, pop[sc])
            dl = math.log(yp / y0)
            print(
                "  %-7s %6d %10.3f %10.3f %10.3f"
                % (
                    pid,
                    y,
                    math.log((f / n) / (f0 / n0)) / dl,
                    math.log((u / n) / (u0 / n0)) / dl,
                    u / f,
                )
            )
    print("  Reading: where eps_useful sits well above eps_final, IMAGE's R&C final-energy path")
    print("  is shaped by conversion (fuel switching), not by falling service per head.")
    print()
    return rows


# --------------------------------------------------------------------------
# 7. WHAT IT MEANS FOR THE DEMAND LAW
def block_series(p: SectorConversionParams, pid, key):
    """One BLOCK 2 series of the generated baseline block (ssp_baseline.output_block)."""
    text = p.baseline_block.read_text(encoding="utf-8")
    if block_years(text) != p.years:
        raise ValueError(
            f"{p.baseline_block}: year grid differs from time_horizon; "
            "re-run scripts/run_ssp_baseline.py"
        )
    return read_block_series(text, pid, key)


def section7(p: SectorConversionParams, m, results, rows):
    print("7. WHAT IT MEANS FOR THE DEMAND LAW")
    print("  eps_final = eps_primary - eps_P/F. The paper estimates eps_primary on 1960-2010 data,")
    print("  when electrification was thermal and raised P/F with income. Its own sector columns")
    print("  imply eps_P/F of about +0.07 at Nigeria's percentile and +0.12 to +0.19 in the long")
    print(
        "  run (CONVERSION_FACTORS.md section C: final 0.28-0.30 vs total 0.36; 0.52-0.59 vs 0.71)."
    )
    for y in p.image_comparison_years:
        print(
            "  IMAGE R10, %d -> %d: eps_P/F = " % (p.image_reference_year, y)
            + ", ".join(
                "%s %+.3f" % (pid, rows[(pid, y)][1] - rows[(pid, y)][0])
                for pid in p.markers
                if (pid, y) in rows and rows[(pid, y)][1] == rows[(pid, y)][1]
            )
        )
    print()
    # Illustration marker and year (sector_conversion.illustration_*)
    pid_i, y_i = p.illustration_pathway, p.illustration_year
    years = p.years
    tj = block_series(p, pid_i, "energyTJ")[years.index(y_i)]
    s_base = block_series(p, pid_i, "elecShare")[years.index(y_i)]
    F0 = sum(sum(m[s].values()) for s in SECTORS)
    E0 = sum(m[s]["electricity"] for s in SECTORS)
    el = iea_electricity(p)
    gen = grid_generation(p, el)
    proto_2023 = (gen + p.genset_gwh) * TJ_PER_GWH / F0  # prototype definition, current release
    proto_to_final = (E0 / F0) / proto_2023  # 2023 final share / prototype share
    print(
        "  %s in %d (baseline final energy %.2f EJ, prototype electrification %.1f%%)."
        % (p.markers[pid_i].label, y_i, tj / 1e6, 100 * s_base)
    )
    print("  Approximation: %d has 2023's sector-carrier structure; prototype shares map to" % y_i)
    print(
        "  final-electricity shares by the 2023 ratio %.3f. TWh are final electricity."
        % proto_to_final
    )
    w = image_weights(p)
    pl = pools(p.rho, m, 1)
    eb = s_base * proto_to_final
    base = solve(m, pl, "IMAGE pattern", eb, w)
    print(
        "  %-24s %10s %12s %12s %10s"
        % ("slider (prototype %)", "1:1 TWh", "converted TWh", "final EJ", "K")
    )
    for s_user in p.targets:
        e = s_user * proto_to_final
        res = solve(m, pl, "IMAGE pattern", e, w)
        K = res[0] / base[0]
        e11 = e * tj / TJ_PER_GWH / 1e3
        conv = e * tj * K / TJ_PER_GWH / 1e3
        print(
            "  %-24s %10.0f %12.0f %12.2f %10.3f"
            % ("%.0f%%" % (100 * s_user), e11, conv, tj * K / 1e6, K)
        )
    print("  K = final energy at the user's electrification / at the baseline's, same service,")
    print("  IMAGE allocation, central rho. The prototype applies K = 1.")
    print()


def report(p: SectorConversionParams) -> None:
    m, extra = section1(p)
    pef, pef_fuel = section2(p, m, extra)
    section3(p)
    results = section4(p, m, pef, pef_fuel)
    section5(p, m)
    rows = section6(p)
    section7(p, m, results, rows)

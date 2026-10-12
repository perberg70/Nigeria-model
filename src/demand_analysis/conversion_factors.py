"""Which conversion factors does the partial-adjustment variant need?

EXPERIMENT BRANCH `experiment/partial-adjustment`, written 2026-10-09.
Companion to partial_adjustment.py (imported, not modified) and
CONVERSION_FACTORS.md. The variant takes Burke & Csereklyei (2016) Table 5
coefficients, estimated on

  * 10-year average annual log growth rates, decade-start levels (Eq. 5);
  * income: Penn World Table 7.1 "PPP-converted GDP per capita (chain
    series) at 2005 constant prices" (Appendix A1), demeaned over the
    463-observation sample for the ETA interaction (Table 5 notes);
  * energy: total PRIMARY energy supply (TPES), kgoe per capita
    (Appendix A1, A3),

and applies them to an annual grid, IIASA/OECD ENV-Growth 2025 GDP|PPP in
USD_2015/yr, IMAGE R10 GDP|PPP in USD_2010/yr, and IEA total FINAL
consumption in TJ. This module sorts every unit difference into one of
three bins and quantifies the ones that matter:

  A. time scale    decade coefficients -> annual closing speed LAMBDA
  B. income level  the ETA interaction is the only term that reads the
                   LEVEL of income, so only it needs a level conversion
  C. boundary      TPES coefficients applied to final energy
  D. cancels       pure unit factors (TJ vs kgoe, USD_2010 vs USD_2015)
                   that drop out of log differences and the alpha
                   calibration; verified numerically below

Run: python scripts/run_conversion_factors.py --config config.yaml
(report in conversion_factors_output.txt)

Two inputs come from outside this repository and are flagged where used:
Nigeria's PWT 7.1 rgdpch values (FRED series RGDPCHNGA625NUPN, read via
web search on 2026-10-09, not downloaded; ``conversion_factors.pwt71_rgdpch``),
and the 463-observation sample mean of t-10 log GDP per capita, which the
paper does not report and which could not be reconstructed here (PWT 7.1
download blocked by this session's network policy).
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from config_paths import ConfigError, require, require_path
from scenario_data import historical_series, interp, narratives, read_label_values, read_series
from units import MJ_PER_KGOE

from .partial_adjustment import PartialAdjustmentParams, decade_recursion, pa_path
from .reporting import short_year
from .table5 import Table5Column, load_table5

# IEA sector names -> paper sectors (Appendix A1). Non-energy use and
# "other non-specified" are not among the paper's five final sectors; the
# paper books them in "Other".
IEA_SECTOR = {
    "Residential": "residences",
    "Agriculture and forestry": "agriculture",
    "Transport": "transport",
    "Industry": "industry",
    "Commercial and public services": "services",
}


@dataclass(frozen=True)
class Table2Col7:
    b1: float
    b2: float
    e25: float


@dataclass(frozen=True)
class ConversionFactorsParams:
    region_name: str
    pa: PartialAdjustmentParams
    table5: dict[str, Table5Column]
    table2: Table2Col7
    pwt71: dict[int, float]
    pwt71_splice_year: int
    gdp_price_bases: tuple[str, ...]  # IIASA GDP|PPP rows compared in section B
    image_price_base: str  # the row in IMAGE R10's price base
    sample_p25_cases: tuple[float, ...]  # assumed 25th percentiles, 2005 I$
    iea_tes_2023: Path
    iea_tfc_2023: Path
    region_mix_pathway: str

    @classmethod
    def from_config(cls, config: Mapping[str, Any]) -> ConversionFactorsParams:
        t2 = "parameters.burke_csereklyei_2016.table2_col7"
        c = "conversion_factors"
        pathway = require(config, f"{c}.region_mix_pathway")
        require(config, f"scenarios.{pathway}")
        pa = PartialAdjustmentParams.from_config(config)
        pwt71 = {int(y): float(v) for y, v in require(config, f"{c}.pwt71_rgdpch").items()}
        splice = int(require(config, f"{c}.pwt71_splice_year"))
        if splice not in pwt71:
            raise ConfigError(f"{c}.pwt71_splice_year: {splice} is not in {c}.pwt71_rgdpch")
        bases = tuple(require(config, f"{c}.gdp_price_bases"))
        image_base = require(config, f"{c}.image_price_base")
        for unit in (pa.iiasa.gdp.unit, image_base):
            if unit not in bases:
                raise ConfigError(f"{c}.gdp_price_bases: {unit!r} must be one of them")
        return cls(
            region_name=require(config, "region.name"),
            pa=pa,
            table5=load_table5(config),
            table2=Table2Col7(
                b1=require(config, f"{t2}.b1"),
                b2=require(config, f"{t2}.b2"),
                e25=require(config, f"{t2}.e25"),
            ),
            pwt71=pwt71,
            pwt71_splice_year=splice,
            gdp_price_bases=bases,
            image_price_base=image_base,
            sample_p25_cases=tuple(require(config, f"{c}.sample_p25_cases")),
            iea_tes_2023=require_path(config, "inputs.iea.total_energy_supply_2023"),
            iea_tfc_2023=require_path(config, "inputs.iea.final_by_sector_2023"),
            region_mix_pathway=pathway,
        )


def price_base(unit: str) -> str:
    """The price base an IIASA GDP unit names: "billion USD_2010/yr" -> "USD_2010"."""
    return unit.replace("billion ", "").replace("/yr", "")


# --------------------------------------------------------------------------
# Scenario runner: the variant's plain/recalibrated/delta-off leg with every
# parameter exposed, so each conversion can be switched on by itself.
def run_markers(c: ConversionFactorsParams, nga, reg=None, gdp_unit=None, anchor_tj=None):
    """nga/reg: dicts with beta_mean, eta, b_target, lam, g_dev0. Returns
    {pid: (var/cur at the comparison year, var/cur at the end year, var end-year TJ)},
    the comparison year being partial_adjustment.comparison_year; 'cur' is the current
    construction, unchanged (0.36 L + 0.065 L^2, old-law R). reg may also be
    a function of the marker id, for region parameters that vary by marker."""
    p = c.pa
    b0, q0 = p.current.elasticity, p.current.quadratic
    base_year, end_year, mid = p.base_year, p.end_year, p.comparison_year
    anchor_tj = p.tfe_tj if anchor_tj is None else anchor_tj
    gdp_spec = p.iiasa.gdp if gdp_unit is None else replace(p.iiasa.gdp, unit=gdp_unit)
    reg = reg or nga
    reg_for = reg if callable(reg) else (lambda pid: reg)
    fe, r10_gdp, r10_pop = (
        read_series(p.image_dir, "Final Energy.csv"),
        read_series(p.image_dir, "GDP - PPP.csv"),
        read_series(p.image_dir, "Population.csv"),
    )
    narrs = narratives(p.markers)
    pop = p.iiasa.series(p.iiasa.population, narrs, p.fill_years)
    gdp = p.iiasa.series(gdp_spec, narrs, p.fill_years)
    years = p.years
    out = {}
    for pid, marker in p.markers.items():
        scen, narrative = marker.key, marker.narrative
        p0 = pop[narrative][base_year]
        log_g = {y: math.log(interp(y, gdp[narrative]) / interp(y, pop[narrative])) for y in years}
        r_log_g = {y: math.log(interp(y, r10_gdp[scen]) / interp(y, r10_pop[scen])) for y in years}
        log_x0 = math.log(anchor_tj / pop[narrative][base_year])
        r_log_x0 = math.log(interp(base_year, fe[scen]) / interp(base_year, r10_pop[scen]))
        n = pa_path(
            years,
            log_g,
            log_x0,
            p.t5,
            beta_mean=nga["beta_mean"],
            eta=nga["eta"],
            b_target=nga["b_target"],
            lam=nga["lam"],
            g_dev0=nga["g_dev0"],
        )
        rp = reg_for(pid)
        r = pa_path(
            years,
            r_log_g,
            r_log_x0,
            p.t5,
            beta_mean=rp["beta_mean"],
            eta=rp["eta"],
            b_target=rp["b_target"],
            lam=rp["lam"],
            g_dev0=rp["g_dev0"],
        )
        res = {}
        for y in (mid, end_year):
            pt = interp(y, pop[narrative])
            fe_ratio = interp(y, fe[scen]) / interp(base_year, fe[scen])
            pop_ratio = interp(y, r10_pop[scen]) / interp(base_year, r10_pop[scen])
            Lr = r_log_g[y] - r_log_g[base_year]
            L = log_g[y] - log_g[base_year]
            r_var = fe_ratio / (pop_ratio * math.exp(r[y] - r[base_year]))
            r_old = fe_ratio / (pop_ratio * math.exp(b0 * Lr + q0 * Lr * Lr))
            var = anchor_tj * (pt / p0) * math.exp(n[y] - n[base_year]) * r_var
            cur = anchor_tj * (pt / p0) * math.exp(b0 * L + q0 * L * L) * r_old
            res[y] = (var, cur)
        out[pid] = (
            res[mid][0] / res[mid][1],
            res[end_year][0] / res[end_year][1],
            res[end_year][0],
        )
    return out


def base_params(c: ConversionFactorsParams, **kw):
    t5 = c.pa.t5
    p = dict(beta_mean=t5.beta, eta=t5.eta, b_target=t5.long_run, lam=t5.lam, g_dev0=c.pa.deviation)
    p.update(kw)
    return p


def print_runs(c: ConversionFactorsParams, label_runs):
    markers = c.pa.markers
    head = "v/c%s  v/c%s" % (short_year(c.pa.comparison_year), short_year(c.pa.end_year))
    print("  %-34s" % "leg" + "".join("%14s" % pid for pid in markers))
    print("  %-34s" % "" + "".join("%14s" % head for _ in markers))
    for label, runs in label_runs:
        print(
            "  %-34s" % label
            + "".join("%7.3f%7.3f" % (runs[pid][0], runs[pid][1]) for pid in markers)
        )
    print()


# --------------------------------------------------------------------------
# A. TIME SCALE
def section_a(c: ConversionFactorsParams):
    p = c.pa
    t5, dev, b = p.t5, p.deviation, p.base_year
    rho10 = 1 + 10 * t5.kappa  # decade retention of a level gap
    lams = [
        ("linear  -kappa", -t5.kappa),
        ("geometric 1-(1+10k)^0.1", 1 - rho10**0.1),
        ("log  -ln(1+10k)/10", -math.log(rho10) / 10),
    ]
    print("A. TIME SCALE: decade coefficients -> annual closing speed")
    print("  Eq. 5 is in annual-average growth units on decade-start levels, so a")
    print("  level gap is retained 1+10*kappa = %.3f per decade. Candidate annual" % rho10)
    print(
        "  closing speeds (theta scales with lambda; b = -theta/kappa = %.4f fixed):"
        % (-t5.theta / t5.kappa)
    )
    for name, lam in lams:
        print(
            "    %-26s lambda = %.5f  decade retention %.4f  annual theta %.5f  half-life %.1f yr"
            % (
                name,
                lam,
                (1 - lam) ** 10,
                lam * -t5.theta / t5.kappa,
                math.log(2) / -math.log(1 - lam),
            )
        )
    print("  beta, eta and the decade dummies need no time conversion: beta and eta")
    print("  are growth-on-growth ratios and the dummies are already in annual-")
    print('  growth units (Table 5 notes: "differenced logs divided by 10").')
    print()

    years = p.years
    tests = p.tests
    g0 = math.log(tests.income_per_head)
    shock = {y: g0 + (math.log(tests.shock) if y >= tests.shock_year else 0.0) for y in years}
    growth = {y: g0 + tests.sustained_growth * (y - b) for y in years}
    d1 = decade_recursion(t5, dev, shock, g0, b, p.end_year)
    d2 = decade_recursion(t5, dev, growth, g0, b, p.end_year)
    print(
        "  Test 1 (shock) and Test 2 (%g%%/yr growth): annual PA minus decade recursion"
        % (100 * tests.sustained_growth)
    )
    print(
        "  %-26s %10s %10s %10s | %10s %10s %10s"
        % (
            "lambda",
            "T1 %d" % (b + 10),
            "T1 %d" % (b + 40),
            "T1 max|.|",
            "T2 %02d-%02d" % (b % 100, (b + 10) % 100),
            "T2 %02d-%02d" % ((b + 40) % 100, (b + 50) % 100),
            "T2 max|.|",
        )
    )
    for name, lam in lams:
        p1 = pa_path(years, shock, 0.0, t5, lam=lam, g_dev0=dev)
        p2 = pa_path(years, growth, 0.0, t5, lam=lam, g_dev0=dev)
        g1 = {y: p1[y] - d1[y] for y in d1 if y > b}
        w = {
            y: (p2[y + 10] - p2[y] - (d2[y + 10] - d2[y])) / (10 * tests.sustained_growth)
            for y in range(b, p.end_year - 10, 10)
        }
        print(
            "  %-26s %10.4f %10.4f %10.4f | %10.4f %10.4f %10.4f"
            % (
                name,
                g1[b + 10],
                g1[b + 40],
                max(abs(v) for v in g1.values()),
                w[b],
                w[b + 40],
                max(abs(v) for v in w.values()),
            )
        )
    print("  (T1 in log points of energy; T2 in window-elasticity units)")
    print()
    print("  Scenario runs (plain target, eta active, R recalibrated):")
    print_runs(c, [(name, run_markers(c, base_params(c, lam=lam))) for name, lam in lams])


# --------------------------------------------------------------------------
# B. INCOME LEVEL
def section_b(c: ConversionFactorsParams):
    p = c.pa
    t5, dev, base = p.t5, p.deviation, p.base_year
    t2 = c.table2
    iiasa, popspec, gdpspec = p.iiasa.path, p.iiasa.population, p.iiasa.gdp
    where = dict(region=p.iiasa.region)
    print("B. INCOME LEVEL: only the ETA interaction reads the level of income")
    print("  beta*dg and the target slope use log DIFFERENCES (any constant price-base")
    print("  factor cancels) and alpha absorbs the level, so the income conversion")
    print("  only enters through d = ln Y_NGA - mean_463(ln Y_t-10) in PWT 7.1 units.")
    splice = c.pwt71_splice_year
    pop = historical_series(iiasa, popspec.variable, popspec.unit, model=popspec.model, **where)

    def at(series, y):
        # A year off the export's grid is interpolated on it, as country_series fills it.
        return series[y] if y in series else interp(y, series)

    pc = {}
    for unit in c.gdp_price_bases:
        g = historical_series(iiasa, gdpspec.variable, unit, model=gdpspec.model, **where)
        pc[unit] = {splice: g[splice] / pop[splice] * 1e3, base: at(g, base) / at(pop, base) * 1e3}
    growth_since = pc[gdpspec.unit][base] / pc[gdpspec.unit][splice]
    image_unit = c.image_price_base
    print("  %s GDP per head, OECD ENV-Growth 2025 (IIASA export), PPP:" % c.region_name)
    for unit, v in pc.items():
        print(
            "    %-22s %d %7.0f   %d %7.0f"
            % (unit.replace("billion ", ""), splice, v[splice], base, v[base])
        )
    print(
        "    real growth per head %d->%d: x%.4f (%.2f log points); identical in all three"
        % (splice, base, growth_since, math.log(growth_since) * 100)
    )
    print("    rows: the three price bases differ by a constant factor")
    print(
        "  %s, PWT 7.1 rgdpch (2005 I$), FRED RGDPCHNGA625NUPN [via web search, unverified]:"
        % c.region_name
    )
    print("    " + "  ".join("%d %.0f" % kv for kv in sorted(c.pwt71.items())))
    pwt_splice = c.pwt71[splice]
    pwt23 = pwt_splice * growth_since
    lo, hi = min(c.pwt71.values()) * growth_since, max(c.pwt71.values()) * growth_since
    print(
        "    spliced %d = PWT 7.1 %d x OECD growth since %d = %.0f "
        "(%d-%d base range %.0f-%.0f)"
        % (base, splice, splice, pwt23, min(c.pwt71), max(c.pwt71), lo, hi)
    )
    gap = math.log(pc[image_unit][splice] / pwt_splice)
    print(
        "    level gap in %d, OECD %s PPP vs PWT 7.1: %.2f log units (x%.2f) --"
        % (splice, price_base(image_unit), gap, math.exp(gap))
    )
    print("    before any 2010->2005 deflation; a price-base conversion factor cannot close it")
    print()

    def e(b1, b2, e25):
        return math.exp((e25 - b1) / (2 * b2))

    p25_2010 = e(t2.b1, t2.b2, t2.e25)
    rng = sorted(
        e(b1, b2, e25)
        for b1 in (t2.b1 - 0.005, t2.b1 + 0.005)
        for b2 in (t2.b2 - 0.005, t2.b2 + 0.005)
        for e25 in (t2.e25 - 0.005, t2.e25 + 0.005)
    )
    print("  The sample mean of ln Y_t-10 is not reported. Table 5 fixes the 25th percentile")
    print("  at mean - %.3f. Only reference point for its level: Table 2 col. 7 (2010" % -dev)
    print(
        "  cross-section, undemeaned): 25th percentile = exp((%.2f%+.2f)/%.2f) = $%.0f"
        % (t2.e25, -t2.b1, 2 * t2.b2, p25_2010)
    )
    print(
        "  (coefficient rounding alone spans $%.0f-$%.0f). The pooled t-10 sample"
        % (rng[0], rng[-1])
    )
    print("  (start years 1960-2000) sits lower, by an unmeasured amount.")
    print(
        "  d for %s %d (spliced PWT 7.1 value $%.0f) as a function of the unknown"
        % (c.region_name, base, pwt23)
    )
    print("  25th percentile of the t-10 sample, and the starting 10-year elasticity:")
    print("  %-30s %8s %8s" % ("assumed 25th pct (2005 I$)", "d", "beta_0"))
    cases = (
        [("= %s (current assumption)" % c.region_name, pwt23)]
        + [("$%d" % p25, p25) for p25 in c.sample_p25_cases]
        + [("$%.0f (Table 2, 2010)" % p25_2010, p25_2010)]
    )
    ds = []
    for label, p25 in cases:
        d = dev - math.log(p25 / pwt23)
        ds.append((label, d))
        print("  %-30s %8.3f %8.3f" % (label, d, t5.beta + t5.eta * d))
    print()
    print("  Scenario runs, %s AND region at the same d (as in the variant):" % c.region_name)
    print_runs(
        c,
        [
            ("d %.2f  (%s)" % (d, label[:18]), run_markers(c, base_params(c, g_dev0=d)))
            for label, d in ds
        ],
    )

    # Region: own position, from IMAGE R10 USD_2010 PPP against the IIASA
    # USD_2010 row (different vintages of the same price base).
    r_gdp = read_series(p.image_dir, "GDP - PPP.csv")
    r_pop = read_series(p.image_dir, "Population.csv")
    nga_10 = pc[image_unit][base]
    print(
        "  Region at its own position: d_R = d + ln(R10 GDP per head / %s), %d,"
        % (c.region_name, base)
    )
    print(
        "  both in %s PPP (IMAGE SSP2021 vs OECD ENV-Growth 2025, different vintages):"
        % price_base(image_unit)
    )
    rows = []
    for pid, marker in p.markers.items():
        scen = marker.key
        r10 = interp(base, r_gdp[scen]) / interp(base, r_pop[scen]) * 1e3
        off = math.log(r10 / nga_10)
        print(
            "    %-7s R10 %6.0f  %s %6.0f  ln ratio %+.3f" % (pid, r10, c.region_name, nga_10, off)
        )
        rows.append(off)
    off = sum(rows) / len(rows)
    print_runs(
        c,
        [
            ("same d (variant)", run_markers(c, base_params(c))),
            (
                "region d_R = d %+.3f" % off,
                run_markers(c, base_params(c), reg=base_params(c, g_dev0=dev + off)),
            ),
        ],
    )


# --------------------------------------------------------------------------
# C. BOUNDARY: TPES coefficients on final energy
def section_c(c: ConversionFactorsParams):
    p = c.pa
    t5all, dev, base = c.table5, p.deviation, p.base_year
    tes = read_label_values(c.iea_tes_2023)
    tfc = read_label_values(c.iea_tfc_2023)
    tes_total, tfc_total = sum(tes.values()), sum(tfc.values())
    sec = {IEA_SECTOR[k]: v for k, v in tfc.items() if k in IEA_SECTOR}
    five = sum(sec.values())
    other = tes_total - five
    print('C. BOUNDARY: Table 5 "total" is TPES; the variant drives IEA total final consumption')
    print(
        "  %s %d (IEA): TES %.0f TJ, TFC %.0f TJ, TES/TFC %.3f; five paper sectors"
        % (c.region_name, base, tes_total, tfc_total, tes_total / tfc_total)
    )
    print(
        '  %.0f TJ (%.1f%% of TFC; non-energy use and non-specified are "Other" in the paper)'
        % (five, 100 * five / tfc_total)
    )
    popspec = p.iiasa.population
    pop_hist = historical_series(
        p.iiasa.path, popspec.variable, popspec.unit, model=popspec.model, region=p.iiasa.region
    )
    pop23 = interp(base, pop_hist) * popspec.scale
    print(
        "  per head: TES %.0f kgoe, TFC %.0f kgoe (1 kgoe = %.3f MJ); paper 2010 cross-section"
        % (
            tes_total * 1e6 / MJ_PER_KGOE / pop23,
            tfc_total * 1e6 / MJ_PER_KGOE / pop23,
            MJ_PER_KGOE,
        )
    )
    print("  means: all 2,725.8, low-income 396.2 kgoe TPES (Appendix A3)")
    w_tes = {s: v / tes_total for s, v in sec.items()}
    w_tes["other"] = other / tes_total
    w_fin = {s: v / five for s, v in sec.items()}
    keys = ("beta", "b25", "b75", "eta", "kappa", "lr")

    def col(s, k):
        return getattr(t5all[s], k)

    def agg(w, k):
        return sum(w[s] * col(s, k) for s in w)

    so = w_tes["other"]
    top = {k: (col("total", k) - so * col("other", k)) / (1 - so) for k in keys}
    print(
        "  weights, share of TES:   " + "  ".join("%s %.3f" % (s[:5], w) for s, w in w_tes.items())
    )
    print(
        "  weights, share of five:  " + "  ".join("%s %.3f" % (s[:5], w) for s, w in w_fin.items())
    )
    print()
    print("  %-44s" % "" + "".join("%8s" % k for k in keys))
    print(
        "  %-44s" % "Table 5 total (published)" + "".join("%8.3f" % col("total", k) for k in keys)
    )
    print(
        "  %-44s" % "Eq. 3 check: six sectors weighted by TES"
        + "".join("%8.3f" % agg(w_tes, k) for k in keys)
    )
    print(
        "  %-44s" % "final, bottom-up: five sectors by TFC share"
        + "".join("%8.3f" % agg(w_fin, k) for k in keys)
    )
    print(
        "  %-44s" % "final, top-down: (total - s_O*other)/(1-s_O)"
        + "".join("%8.3f" % top[k] for k in keys)
    )
    print("  (lr is the share-weighted reported long-run elasticity; kappa the share-weighted")
    print("   convergence coefficient. Shares are 2023 values held fixed, Eq. 3 is exact only")
    print("   for small changes; a sector-by-sector PA would let them drift.)")
    print()
    bu = dict(
        beta_mean=agg(w_fin, "beta"),
        eta=agg(w_fin, "eta"),
        b_target=agg(w_fin, "lr"),
        lam=-agg(w_fin, "kappa"),
        g_dev0=dev,
    )
    td = dict(
        beta_mean=top["beta"],
        eta=top["eta"],
        b_target=top["lr"],
        lam=-top["kappa"],
        g_dev0=dev,
    )
    # The two routes agree on the elasticity at Nigeria's percentile and,
    # roughly, on the long run; they disagree on eta and kappa, which Eq. 3
    # does not decompose (the TES-weighted check misses both). This leg
    # converts only the agreed terms and leaves eta and kappa at Table 5.
    b25_f = (agg(w_fin, "b25") + top["b25"]) / 2
    lr_f = (agg(w_fin, "lr") + top["lr"]) / 2
    agreed = base_params(c, beta_mean=b25_f - p.t5.eta * dev, b_target=lr_f)
    print(
        "  agreed-terms leg: beta_0 %.3f (mean of the two routes), b_target %.3f; eta %.2f"
        % (b25_f, lr_f, p.t5.eta)
    )
    print("  and lambda %.3f unconverted" % -p.t5.kappa)

    # Region at its own IMAGE base-year sector mix. IMAGE reports Residential and
    # Commercial together; it is split in the country's residences:services ratio
    # (an assumption), and the unallocated remainder is left out.
    rc_res = w_fin["residences"] / (w_fin["residences"] + w_fin["services"])
    reg_w = {}
    for pid, marker in p.markers.items():
        scen = marker.key
        f = {
            k: interp(base, read_series(p.image_dir, "Final Energy - %s.csv" % k)[scen])
            for k in ("Industry", "Residential and Commercial", "Transportation")
        }
        tot = sum(f.values())
        w = {
            "industry": f["Industry"] / tot,
            "transport": f["Transportation"] / tot,
            "residences": rc_res * f["Residential and Commercial"] / tot,
            "services": (1 - rc_res) * f["Residential and Commercial"] / tot,
        }
        reg_w[pid] = dict(
            beta_mean=agg(w, "beta"),
            eta=agg(w, "eta"),
            b_target=agg(w, "lr"),
            lam=-agg(w, "kappa"),
            g_dev0=dev,
        )
    shown = reg_w[c.region_mix_pathway]
    print(
        "  region bottom-up at its own %d mix (%s): beta %.3f, b25 %.3f, eta %.3f,"
        % (
            base,
            p.markers[c.region_mix_pathway].label,
            shown["beta_mean"],
            shown["beta_mean"] + shown["eta"] * dev,
            shown["eta"],
        )
    )
    print("  kappa %.3f, lr %.3f" % (-shown["lam"], shown["b_target"]))
    print()
    print("  Scenario runs (R recalibrated through whichever law the region is given):")
    print_runs(
        c,
        [
            ("TPES total (variant)", run_markers(c, base_params(c))),
            ("final bottom-up, both", run_markers(c, bu)),
            ("final bottom-up, region own mix", run_markers(c, bu, reg=lambda pid: reg_w[pid])),
            ("final top-down, both", run_markers(c, td)),
            ("final agreed terms, both", run_markers(c, agreed)),
            ("final bottom-up, %s only" % c.region_name, run_markers(c, bu, reg=base_params(c))),
        ],
    )
    print('  The last leg breaks closure: IMAGE "Final Energy" has the same boundary as')
    print(
        "  %s's TFC, so the region must be stripped with the same final-energy law." % c.region_name
    )
    print()


# --------------------------------------------------------------------------
# D. FACTORS THAT CANCEL
def section_d(c: ConversionFactorsParams):
    print("D. PURE UNIT FACTORS CANCEL (numerical check)")
    ref = run_markers(c, base_params(c))
    alt_gdp = run_markers(c, base_params(c), gdp_unit=c.image_price_base)
    alt_e = run_markers(c, base_params(c), anchor_tj=c.pa.tfe_tj * 1e6 / MJ_PER_KGOE)
    d_gdp = max(abs(alt_gdp[p][1] - ref[p][1]) for p in ref)
    d_e = max(abs(alt_e[p][1] - ref[p][1]) for p in ref)
    end = c.pa.end_year
    print(
        "  GDP in %s instead of %s rows:   max |change| in var/cur %d = %.1e"
        % (price_base(c.image_price_base), price_base(c.pa.iiasa.gdp.unit), end, d_gdp)
    )
    print(
        "  energy anchor in kgoe instead of TJ:          max |change| in var/cur %d = %.1e"
        % (end, d_e)
    )
    print("  IMAGE R10 GDP stays in USD_2010: it enters only as log changes and in R.")
    print()


def report(c: ConversionFactorsParams) -> None:
    section_a(c)
    section_b(c)
    section_c(c)
    section_d(c)

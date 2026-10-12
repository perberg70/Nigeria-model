"""Partial-adjustment demand variant for the Nigeria baseline.

EXPERIMENT BRANCH `experiment/partial-adjustment`, written 2026-10-08.
Implements the two coherence tests and the partial-adjustment variant
specified in the Master Thesis project report
(03_models/2026-10-08_kimi-elasticity-literature/
africa-energy-demand-elasticity-assessment.pplx.md, sections "Elasticity
coherence tests" and "Partial-adjustment variant: equations and
assumptions"). Nothing here changes the baseline builder; this module is a
standalone comparator.

THE CURRENT CONSTRUCTION, for reference. The baseline uses
    ln(E/E0) = ln(P/P0) + 0.36 L + 0.065 L^2 + ln(R), L = ln(y/y0),
the integrated 10-year elasticity from Burke & Csereklyei (2016, Energy
Economics 58:199-210) Table 5 column "total". It has no state variable in
which pending adjustment can live: under a once-and-for-all income shock it
jumps once and stops, and cannot approach the paper's long-run elasticity
-THETA/KAPPA = 0.016/0.023 ~= 0.70. That is the missing-convergence finding
the two tests below operationalise.

THE VARIANT. Annual grid 2023-2100, per-capita final energy x_t and
per-capita income g_t in logs:

    x*_t = alpha + B_TARGET * g_t                        (income-consistent level)
    x_t  = x_{t-1} + BETA_10 * (g_t - g_{t-1})
                      + LAMBDA * (x*_{t-1} - x_{t-1}) + DELTA_t
    E_t  = P_t * exp(x_t)

Parameter mapping (declared assumptions, not estimates; Table 5, total):
  BETA_10  = 0.48 + ETA*(g_demeaned_t-1), ETA = 0.13     10-year elasticity
  LAMBDA   = -KAPPA = 0.023 /yr (annual linearisation of the decade form)
  B_TARGET = -THETA/KAPPA = 0.016/0.023 ~= 0.70. Footnote 3's generalized
             long-run slope -(THETA + ETA*x_bar)/KAPPA under sustained
             growth x_bar EMERGES from the dynamics once ETA is active
             (steady state of the recursion: n = b*x_bar + (ETA/LAMBDA)*x_bar^2
             = -(THETA + ETA*x_bar)*x_bar/KAPPA); injecting it into b_target
             as well double-counts (Codex review P1, PR #9). The correct
             growth-adjusted leg is the STATIC approximation: ETA switched
             off dynamically and b_target = -(THETA + ETA*x_bar)/KAPPA.
  DELTA_t  = 0 by default; with DELTA_MODE='decade-effects' the most
             recent observed decade dummy (-0.029/yr, 2001-2010 relative to
             the 1970 base) is carried forward as a constant -- an explicit
             "latest regime persists" assumption, not a replay of the
             historical dummy sequence (Codex review P2b, PR #9)
  alpha    calibrated so x_2023 equals the IEA anchor's log per-capita
             final energy.

R IS RECALIBRATED, as the report's recalibration identity requires: within
each scenario the variant's R10 factor is the regional final-energy ratio
divided by what the REGION's own population and income paths give through
the SAME variant law, evaluated on the regional series. Otherwise the
residual would silently re-impose the old dynamics.

KNOWN LIMITS (stated here so they are not rediscovered downstream):
  * Boundary: Table 5 total is a PRIMARY-energy elasticity applied here to
    a FINAL-energy anchor (IEA 2023 TFE, biomass-inclusive). The variant
    inherits the mismatch; it does not resolve it.
  * Income units: ETA's interaction needs 2005-PPP demeaned log income from
    the paper's 1960-2010 sample. The IIASA export is USD_2015/yr PPP. The
    2023 anchor is mapped to the paper's 25th-percentile deviation
    (0.36 - 0.48)/0.13 = -0.923 log units, the same approximation the
    baseline makes; flagged, not defended.
  * LAMBDA is an annual linearisation of a decade-sampled estimate; the
    decade-step recursion in coherence_test_shock() is the benchmark, and
    run_all() prints the annual-versus-decade endpoint gap.
  * Prices omitted, as in the baseline (weak average evidence for non-OECD;
    unresolved).

Coefficients come from ``parameters.burke_csereklyei_2016`` and the current law
from ``ssp_baseline.demand``; the test design and leg sequence from the
``partial_adjustment`` section of the configuration.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config_paths import ConfigError, require, require_path
from scenario_data import IiasaExport, Marker, interp, load_markers, narratives, read_series

from .table5 import CurrentLaw, Table5Column, load_current_law, load_table5

DELTA_MODES = ("off", "decade-effects")
B_MODES = ("plain", "static-adjusted")
R_MODES = ("recalibrated", "fixed-old")


@dataclass(frozen=True)
class CoherenceTestDesign:
    """Synthetic income paths of the two coherence tests (only changes matter)."""

    income_per_head: float
    sustained_growth: float
    shock: float
    shock_year: int


@dataclass(frozen=True)
class PartialAdjustmentParams:
    markers: dict[str, Marker]
    base_year: int
    anchor_year: int
    end_year: int
    image_dir: Path
    iiasa: IiasaExport
    tfe_tj: float
    t5: Table5Column
    decade_effects: tuple[float, ...]
    current: CurrentLaw
    tests: CoherenceTestDesign
    runs: tuple[dict[str, Any], ...]

    @classmethod
    def from_config(cls, config: Mapping[str, Any]) -> PartialAdjustmentParams:
        t = "partial_adjustment.coherence_tests"
        runs = tuple(dict(r) for r in require(config, "partial_adjustment.runs"))
        for r in runs:
            if (
                r.get("delta_mode") not in DELTA_MODES
                or r.get("b_mode") not in B_MODES
                or r.get("r_mode") not in R_MODES
                or not isinstance(r.get("eta"), bool)
            ):
                raise ConfigError(f"partial_adjustment.runs: invalid leg {r!r}")
        return cls(
            markers=load_markers(config),
            base_year=int(require(config, "time_horizon.base_year")),
            anchor_year=int(require(config, "time_horizon.anchor_year")),
            end_year=int(require(config, "time_horizon.end_year")),
            image_dir=require_path(config, "inputs.image_dir"),
            iiasa=IiasaExport.from_config(config),
            tfe_tj=require(config, "ssp_baseline.anchors.total_final_energy_tj"),
            t5=load_table5(config)["total"],
            decade_effects=tuple(
                require(config, "parameters.burke_csereklyei_2016.table5_decade_effects_total")
            ),
            current=load_current_law(config),
            tests=CoherenceTestDesign(
                income_per_head=require(config, f"{t}.income_per_head"),
                sustained_growth=require(config, f"{t}.sustained_growth"),
                shock=require(config, f"{t}.shock"),
                shock_year=int(require(config, f"{t}.shock_year")),
            ),
            runs=runs,
        )

    @property
    def deviation(self) -> float:
        """The base year's income mapped to the paper's 25th-percentile deviation:
        (0.36 - 0.48) / 0.13 = -0.923 log units below the sample mean. Same
        approximation as the baseline; flagged in the module docstring."""
        return (self.current.elasticity - self.t5.beta) / self.t5.eta

    @property
    def years(self) -> list[int]:
        return list(range(self.base_year, self.end_year + 1))

    @property
    def fill_years(self) -> tuple[int, int]:
        """Years interpolated into the five-yearly IIASA grid, as in the baseline."""
        return (self.base_year, self.anchor_year)


def pa_path(
    years: Sequence[int],
    log_g: Mapping[int, float],
    log_x0: float,
    t5: Table5Column,
    *,
    beta_mean: float | None = None,
    eta: float | None = None,
    b_target: float | None = None,
    lam: float | None = None,
    delta_mode: str = "off",
    decade_effects: Sequence[float] = (),
    g_dev0: float = 0.0,
) -> dict[int, float]:
    """Annual partial-adjustment path. Returns dict year -> log per-capita
    energy. Unset coefficients default to the Table 5 column `t5`. g_dev0 is the
    anchor-year income's deviation from the paper's sample mean (log units), for
    the ETA interaction; the deviation at time t is (g_t - g_anchor) + g_dev0,
    i.e. own growth since the anchor plus the anchor's position. The baseline
    makes the same move implicitly by integrating beta(L) from a 25th-percentile
    start."""
    beta_mean = t5.beta if beta_mean is None else beta_mean
    eta = t5.eta if eta is None else eta
    b_target = t5.long_run if b_target is None else b_target
    lam = t5.lam if lam is None else lam
    if delta_mode == "decade-effects" and not decade_effects:
        raise ValueError("delta_mode='decade-effects' needs the Table 5 decade effects")
    g_anchor = log_g[years[0]]
    alpha = log_x0 - b_target * g_anchor
    x = log_x0
    out = {years[0]: x}
    for i in range(1, len(years)):
        y, y_prev = years[i], years[i - 1]
        g_prev = log_g[y_prev]
        deviation = (g_prev - g_anchor) + g_dev0
        beta = beta_mean + eta * deviation if eta else beta_mean
        x_star_prev = alpha + b_target * g_prev
        delta = 0.0
        if delta_mode == "decade-effects":
            # Codex review P2b (PR #9): Table 5's decade dummies are
            # calendar-period intercepts relative to a 1970 base, not a
            # sequence of shocks that can be shifted forward. The explicit
            # forecast assumption made here: the most recent observed
            # regime (the 2001-2010 dummy, -0.029/yr) persists over the
            # whole projection horizon.
            delta = decade_effects[-1]
        x = x + beta * (log_g[y] - g_prev) + lam * (x_star_prev - x) + delta
        out[y] = x
    return out


def growth_adjusted_b(t5: Table5Column, x_bar: float) -> float:
    """Footnote 3: long-run elasticity with sustained future growth x."""
    return -(t5.theta + t5.eta * x_bar) / t5.kappa


def decade_recursion(
    t5: Table5Column,
    deviation: float,
    log_g: Mapping[int, float],
    g0: float,
    base_year: int,
    end_year: int,
) -> dict[int, float]:
    """Decade-step recursion (faithful Equation 5 roll), x in deviations from the
    base-year anchor: theta*(g_t-10 - g_base) + kappa*(x_t-10 - x_base), with the
    base year at the paper's 25th-percentile deviation."""
    dec = {base_year: 0.0}
    for y in range(base_year + 10, end_year + 1, 10):
        dg = log_g[y] - log_g[y - 10]
        beta = t5.beta + t5.eta * (deviation + (log_g[y - 10] - g0))
        dec[y] = (
            (1 + 10 * t5.kappa) * dec[y - 10] + beta * dg + 10 * t5.theta * (log_g[y - 10] - g0)
        )
    return dec


def coherence_test_growth(p: PartialAdjustmentParams) -> None:
    """TEST 2 (sustained growth): income per capita grows at a constant
    2%/yr for the whole horizon. Benchmark: footnote 3's generalized
    long-run elasticity -(THETA + ETA*x_bar)/KAPPA = 0.809. Each path's
    elasticity is measured as the ratio of the log energy change to the log
    income change over a window. The PA paths' window elasticities should
    converge toward the benchmark; the current construction's window
    elasticity, 0.36 + 0.065*(L1+L2), grows linearly with cumulated income
    and never converges to anything. The annual PA is run with the PLAIN
    target (-THETA/KAPPA) and ETA active: its convergence to 0.809 is the
    numerical verification of the Codex P1 point that the growth adjustment
    emerges from the dynamics and must not be injected into b_target."""
    t5, cur_law = p.t5, p.current
    years = p.years
    x_bar = p.tests.sustained_growth
    g0 = math.log(p.tests.income_per_head)
    log_g = {y: g0 + x_bar * (y - p.base_year) for y in years}

    pa = pa_path(years, log_g, 0.0, t5, g_dev0=p.deviation)
    dec = decade_recursion(t5, p.deviation, log_g, g0, p.base_year, p.end_year)

    def cur(y):
        L = x_bar * (y - p.base_year)
        return cur_law.elasticity * L + cur_law.quadratic * L * L

    target = growth_adjusted_b(t5, x_bar)
    print("TEST 2: sustained income growth (%.1f%%/yr, constant)" % (100 * x_bar))
    print("  footnote-3 long-run elasticity -(theta+eta*x_bar)/kappa: %.4f" % target)
    print("  %-12s %14s %14s %14s" % ("window", "current", "annual PA", "decade Eq5"))
    for y1 in range(p.base_year, p.end_year - 10 + 1, 10):
        y2 = y1 + 10
        w = "%d-%d" % (y1, y2)
        pa_el = (pa[y2] - pa[y1]) / (x_bar * 10)
        dec_el = (dec[y2] - dec[y1]) / (x_bar * 10)
        cur_el = (cur(y2) - cur(y1)) / (x_bar * 10)
        print("  %-12s %14.4f %14.4f %14.4f" % (w, cur_el, pa_el, dec_el))
    print("  READING: the PA window elasticities should converge toward")
    print("  %.4f from below; the current construction should drift upward" % target)
    print("  linearly with cumulated income and never settle.")
    print()


def coherence_test_shock(p: PartialAdjustmentParams) -> None:
    """TEST 1 (shock-then-flat): income per capita +10% at 2024, then flat.
    Benchmark: the long-run-implied endpoint -THETA/KAPPA = 0.696 of the log
    income gap. The current construction and the decade recursion and the
    annual approximation are all run so they can be compared directly."""
    t5, cur_law = p.t5, p.current
    years = p.years
    g0 = math.log(p.tests.income_per_head)  # arbitrary level; only changes matter
    shock = math.log(p.tests.shock)
    log_g = {y: g0 + (shock if y >= p.tests.shock_year else 0.0) for y in years}

    # Current construction (integrated 10-year elasticity, quadratic form)
    current = {
        y: cur_law.elasticity * (log_g[y] - g0) + cur_law.quadratic * (log_g[y] - g0) ** 2
        for y in years
    }

    # Annual partial adjustment, calibrated alpha for a zero baseline.
    # Codex review P2 (PR #9): both PA benchmarks must start from the SAME
    # income-percentile elasticity as the current construction (0.36 at the
    # 25th percentile), so the path gap isolates convergence rather than
    # conflating it with a different starting percentile.
    pa = pa_path(years, log_g, 0.0, t5, g_dev0=p.deviation)

    # Decade-step recursion with the same 25th-percentile anchor deviation.
    dec = decade_recursion(t5, p.deviation, log_g, g0, p.base_year, p.end_year)

    lr = t5.long_run * shock
    print(
        "TEST 1: shock-then-flat income (+%g%% at %d, then constant)"
        % (100 * (p.tests.shock - 1), p.tests.shock_year)
    )
    print("  long-run-implied endpoint of log energy gap: %.4f" % lr)
    print("  %-6s %14s %14s %14s" % ("year", "current", "annual PA", "decade Eq5"))
    b = p.base_year
    for y in (b, b + 10, b + 30, b + 50, p.end_year):
        row = [y, current[y], pa[y], dec.get(y, float("nan"))]
        print(
            "  %-6d %14.4f %14.4f %14s"
            % (row[0], row[1], row[2], ("%.4f" % row[3]) if row[3] == row[3] else "n/a")
        )
    print("  READING: the current construction should jump once and stop;")
    print("  the PA paths should keep moving toward %.4f with a" % lr)
    print("  half-life of about ln(2)/%.3f = %.0f years." % (t5.lam, math.log(2) / t5.lam))
    print()


def run_all(
    p: PartialAdjustmentParams,
    delta_mode: str = "off",
    eta: bool = True,
    b_mode: str = "plain",
    r_mode: str = "recalibrated",
) -> None:
    """Run the variant on all SSP markers and print the comparison
    against the current construction.

    r_mode='recalibrated': R recomputed through the SAME variant law on the
    regional paths (the report's closure-consistent convention).
    r_mode='fixed-old':    R kept at the current construction's law -- a
    conditional experiment under an independent structural assumption about
    R, NOT a confidence interval. Common time effects (delta_mode) cancel
    exactly under 'recalibrated' and survive only under 'fixed-old'."""
    t5, cur_law, dev = p.t5, p.current, p.deviation
    b0, q0 = cur_law.elasticity, cur_law.quadratic
    base_year, end_year = p.base_year, p.end_year
    fe = read_series(p.image_dir, "Final Energy.csv")
    r10_gdp = read_series(p.image_dir, "GDP - PPP.csv")
    r10_pop = read_series(p.image_dir, "Population.csv")
    narrs = narratives(p.markers)
    pop = p.iiasa.series(p.iiasa.population, narrs, p.fill_years)
    gdp = p.iiasa.series(p.iiasa.gdp, narrs, p.fill_years)
    years = p.years

    # Every narrative shares the Historical Reference row up to the base year, so
    # the base-year population (and so the anchor) is the same whichever is used.
    log_x0_nga = math.log(p.tfe_tj / pop[narrs[0]][base_year])
    print(
        "Variant run: delta_mode=%s  eta=%s  b_mode=%s  r_mode=%s"
        % (delta_mode, eta, b_mode, r_mode)
    )
    print(
        "%-8s %10s %10s %10s %12s %12s %10s %10s"
        % (
            "marker",
            "x_bar %/yr",
            "b_target",
            "R10 eps*",
            "cur 2100 TJ",
            "var 2100 TJ",
            "var/cur50",
            "var/cur100",
        )
    )
    print("  (* R10 eps is the scenario-path proxy, not a structural elasticity)")
    for pid, marker in p.markers.items():
        scen, narrative = marker.key, marker.narrative
        # The country's own paths
        p0 = pop[narrative][base_year]
        log_g = {y: math.log(interp(y, gdp[narrative]) / interp(y, pop[narrative])) for y in years}
        x_bar = (log_g[end_year] - log_g[base_year]) / (end_year - base_year)
        if b_mode == "static-adjusted":
            # Codex review P1 (PR #9): with ETA active the dynamics already
            # produce footnote 3's asymptotic slope; injecting it into
            # b_target double-counts. The correct growth-adjusted leg keeps
            # the generalized slope STATIC and switches the dynamic ETA
            # interaction off. Codex review P2a (PR #9): switching ETA off
            # must NOT silently revert beta to the sample mean 0.48; freeze
            # it at the Nigeria 25th-percentile calibration 0.36 so this
            # leg differs from the plain run only in the target.
            nga_eta, b_target = 0.0, growth_adjusted_b(t5, x_bar)
            nga_beta = t5.beta + t5.eta * dev
        else:
            nga_eta, b_target = (t5.eta if eta else 0.0), t5.long_run
            nga_beta = t5.beta
        nga_pa = pa_path(
            years,
            log_g,
            log_x0_nga,
            t5,
            beta_mean=nga_beta,
            eta=nga_eta,
            b_target=b_target,
            delta_mode=delta_mode,
            decade_effects=p.decade_effects,
            g_dev0=dev,
        )

        # Scenario-path proxy for the income response embedded in the IMAGE
        # R10 scenario itself: the ratio of cumulative log changes in
        # regional per-capita final energy and income, 2023-2100. This is a
        # scenario-path association, NOT the model's structural income
        # elasticity (structural change, prices and policy assumptions move
        # with income along the path); printed as the diagnostic the report
        # calls the single most consequential unverified number.
        r_eps_path = math.log(
            interp(end_year, fe[scen])
            / interp(base_year, fe[scen])
            / (interp(end_year, r10_pop[scen]) / interp(base_year, r10_pop[scen]))
        ) / (
            math.log(
                interp(end_year, r10_gdp[scen])
                / interp(end_year, r10_pop[scen])
                / (interp(base_year, r10_gdp[scen]) / interp(base_year, r10_pop[scen]))
            )
        )

        # Regional paths through the SAME law (for R recalibration)
        r_log_g = {y: math.log(interp(y, r10_gdp[scen]) / interp(y, r10_pop[scen])) for y in years}
        r_log_x0 = math.log(interp(base_year, fe[scen]) / interp(base_year, r10_pop[scen]))
        # The region is run through the same law with the same 25th-
        # percentile anchor deviation as Nigeria, mirroring the baseline's
        # symmetric use of the elasticity for both. Flagged in the docstring as
        # an approximation, not a measurement of R10's sample position. In
        # static-adjusted mode the region gets its OWN growth-adjusted
        # target, from its own mean income growth.
        r_x_bar = (r_log_g[end_year] - r_log_g[base_year]) / (end_year - base_year)
        r_b = growth_adjusted_b(t5, r_x_bar) if b_mode == "static-adjusted" else b_target
        r_pa = pa_path(
            years,
            r_log_g,
            r_log_x0,
            t5,
            beta_mean=nga_beta,
            eta=nga_eta,
            b_target=r_b,
            delta_mode=delta_mode,
            decade_effects=p.decade_effects,
            g_dev0=dev,
        )

        # Variant energy with R per r_mode
        cur_2100 = var_2100 = cur_2050 = var_2050 = None
        for y in years:
            pt = interp(y, pop[narrative])
            fe_ratio = interp(y, fe[scen]) / interp(base_year, fe[scen])
            pop_ratio = interp(y, r10_pop[scen]) / interp(base_year, r10_pop[scen])
            Lr = r_log_g[y] - r_log_g[base_year]
            if r_mode == "recalibrated":
                # R10 residual: observed regional FE ratio divided by what
                # the region's own population and income give through the
                # variant law
                r10_residual = fe_ratio / (pop_ratio * math.exp(r_pa[y] - r_pa[base_year]))
            else:
                # conditional experiment: R from the CURRENT law
                r10_residual = fe_ratio / (pop_ratio * math.exp(b0 * Lr + q0 * Lr * Lr))
            E = p.tfe_tj * (pt / p0) * math.exp(nga_pa[y] - nga_pa[base_year]) * r10_residual
            if y in (2050, end_year):
                L = log_g[y] - log_g[base_year]
                r10_old = fe_ratio / (pop_ratio * math.exp(b0 * Lr + q0 * Lr * Lr))
                cur = p.tfe_tj * (pt / p0) * math.exp(b0 * L + q0 * L * L) * r10_old
                if y == 2050:
                    cur_2050, var_2050 = cur, E
                else:
                    cur_2100, var_2100 = cur, E
        print(
            "%-8s %10.2f %10.3f %10.3f %12.0f %12.0f %10.3f %10.3f"
            % (
                pid,
                x_bar * 100,
                b_target,
                r_eps_path,
                cur_2100,
                var_2100,
                var_2050 / cur_2050,
                var_2100 / cur_2100,
            )
        )
    print()


def report(p: PartialAdjustmentParams) -> None:
    """The full printed report: both coherence tests, then each configured leg."""
    coherence_test_shock(p)
    coherence_test_growth(p)
    for leg in p.runs:
        run_all(p, **leg)

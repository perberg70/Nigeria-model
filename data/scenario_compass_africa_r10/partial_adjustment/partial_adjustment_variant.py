#!/usr/bin/env python3
"""Partial-adjustment demand variant for the Nigeria baseline.

EXPERIMENT BRANCH `experiment/partial-adjustment`, written 2026-10-08.
Implements the two coherence tests and the partial-adjustment variant
specified in the Master Thesis project report
(03_models/2026-10-08_kimi-elasticity-literature/
africa-energy-demand-elasticity-assessment.pplx.md, sections "Elasticity
coherence tests" and "Partial-adjustment variant: equations and
assumptions"). Nothing here changes the baseline builder; this script is a
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
  DELTA_t  = 0 by default; the paper's decade effects (-0.021 to -0.029/yr
             for total energy) are available as DELTA_MODE='decade-effects'
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
"""
import csv, io, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SC   = os.path.join(HERE, '..', 'image32_ssp2021')
POP  = os.path.join(HERE, '..', '..', 'iiasa_ssp_nigeria',
                    'Population_GDP_PPP_IIASA_SSP_15_Nigeria.csv')

MARKERS = {
    'ssp119': ('SSP2021-SSP1-SPA1-19-Default', 'SSP1'),
    'ssp126': ('SSP2021-SSP1-SPA1-26-Default', 'SSP1'),
    'ssp245': ('SSP2021-SSP2-SPA2-45-Default', 'SSP2'),
    'ssp370': ('SSP2021-SSP3-Baseline',        'SSP3'),
    'ssp585': ('SSP2021-SSP5-Baseline',        'SSP5'),
}

# Nigeria anchors, identical to build_nigeria_baseline.py
NGA_TFE_TJ = 2465907.0
BASE_YEAR, END_YEAR = 2023, 2100

# Burke & Csereklyei (2016) Table 5, column "total energy"
BETA_MEAN = 0.48      # 10-year elasticity at mean initial log income
ETA       = 0.13      # interaction per log unit of (demeaned) initial income
THETA     = 0.016     # initial log income level
KAPPA     = -0.023    # initial log energy level (conditional convergence)
LAMBDA    = -KAPPA    # annual closing speed, linearisation
# Nigeria's 2023 income is mapped to the paper's 25th-percentile deviation:
# (0.36 - 0.48) / 0.13 = -0.923 log units below the sample mean. Same
# approximation as the baseline; flagged in the module docstring.
NGA_2023_DEVIATION = (0.36 - 0.48) / ETA
# Table 5 decade effects for total energy (annual growth units), 1981-2010
DECADE_EFFECTS = [-0.021, -0.025, -0.029, -0.029]


def series(fn):
    out = {}
    with io.open(os.path.join(SC, fn), encoding='utf-8-sig') as fh:
        for r in csv.DictReader(fh):
            out.setdefault(r['Scenario name'], {})[int(r['year'])] = float(r['value'])
    return out


def interp(y, d):
    ys = sorted(d)
    if y <= ys[0]:  return d[ys[0]]
    if y >= ys[-1]: return d[ys[-1]]
    for a, b in zip(ys, ys[1:]):
        if a <= y <= b:
            return d[a] + (d[b] - d[a]) * (y - a) / (b - a)


def nigeria_series(variable, unit=None, scale=1.0):
    historical, forecasts = None, {}
    with io.open(POP, encoding='utf-8-sig') as fh:
        for r in csv.DictReader(fh):
            if r['variable'] != variable:
                continue
            if unit is not None and r['unit'] != unit:
                continue
            yrs = {int(k): float(v) * scale for k, v in r.items()
                   if k.strip().isdigit() and v not in ('', None)}
            if r['scenario'] == 'Historical Reference':
                historical = yrs
            elif r['scenario'] in {n for _, n in MARKERS.values()}:
                forecasts[r['scenario']] = yrs
    out = {}
    for narrative, forecast in forecasts.items():
        yrs = {y: v for y, v in historical.items() if y <= 2025}
        yrs.update(forecast)
        for y in (BASE_YEAR, 2024):
            if y not in yrs:
                yrs[y] = interp(y, historical)
        out[narrative] = yrs
    return out


def pa_path(years, log_g, log_x0, beta_mean=BETA_MEAN, eta=ETA,
            b_target=None, lam=LAMBDA, delta_mode='off', g_dev0=0.0):
    """Annual partial-adjustment path. Returns dict year -> log per-capita
    energy. g_dev0 is the anchor-year income's deviation from the paper's
    sample mean (log units), for the ETA interaction; the deviation at time
    t is (g_t - g_anchor) + g_dev0, i.e. own growth since the anchor plus
    the anchor's position. The baseline makes the same move implicitly by
    integrating beta(L) from a 25th-percentile start."""
    if b_target is None:
        b_target = -THETA / KAPPA
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
        if delta_mode == 'decade-effects':
            d = min(len(DECADE_EFFECTS) - 1, (y_prev - BASE_YEAR) // 10)
            delta = DECADE_EFFECTS[d]
        x = x + beta * (log_g[y] - g_prev) + lam * (x_star_prev - x) + delta
        out[y] = x
    return out


def growth_adjusted_b(x_bar):
    """Footnote 3: long-run elasticity with sustained future growth x."""
    return -(THETA + ETA * x_bar) / KAPPA


def coherence_test_growth():
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
    years = list(range(BASE_YEAR, END_YEAR + 1))
    x_bar = 0.02
    g0 = math.log(8000.0)
    log_g = {y: g0 + x_bar * (y - BASE_YEAR) for y in years}

    pa = pa_path(years, log_g, 0.0, g_dev0=NGA_2023_DEVIATION)

    dec = {2023: 0.0}
    for y in range(2033, END_YEAR + 1, 10):
        dg = log_g[y] - log_g[y - 10]
        beta = BETA_MEAN + ETA * (NGA_2023_DEVIATION + (log_g[y - 10] - g0))
        dec[y] = ((1 + 10 * KAPPA) * dec[y - 10]
                  + beta * dg
                  + 10 * THETA * (log_g[y - 10] - g0))

    def cur(y):
        L = x_bar * (y - BASE_YEAR)
        return 0.36 * L + 0.065 * L * L

    target = growth_adjusted_b(x_bar)
    print('TEST 2: sustained income growth (2.0%/yr, constant)')
    print('  footnote-3 long-run elasticity -(theta+eta*x_bar)/kappa: %.4f' % target)
    print('  %-12s %14s %14s %14s' % ('window', 'current', 'annual PA', 'decade Eq5'))
    for y1 in range(2023, 2093, 10):
        y2 = y1 + 10
        w = '%d-%d' % (y1, y2)
        pa_el = (pa[y2] - pa[y1]) / (x_bar * 10)
        dec_el = (dec[y2] - dec[y1]) / (x_bar * 10)
        cur_el = (cur(y2) - cur(y1)) / (x_bar * 10)
        print('  %-12s %14.4f %14.4f %14.4f' % (w, cur_el, pa_el, dec_el))
    print('  READING: the PA window elasticities should converge toward')
    print('  %.4f from below; the current construction should drift upward' % target)
    print('  linearly with cumulated income and never settle.')
    print()


def coherence_test_shock():
    """TEST 1 (shock-then-flat): income per capita +10% at 2024, then flat.
    Benchmark: the long-run-implied endpoint -THETA/KAPPA = 0.696 of the log
    income gap. The current construction and the decade recursion and the
    annual approximation are all run so they can be compared directly."""
    years = list(range(BASE_YEAR, END_YEAR + 1))
    g0 = math.log(8000.0)          # arbitrary level; only changes matter
    shock = math.log(1.10)
    log_g = {y: g0 + (shock if y >= 2024 else 0.0) for y in years}

    # Current construction (integrated 10-year elasticity, quadratic form)
    current = {y: 0.36 * (log_g[y] - g0) + 0.065 * (log_g[y] - g0) ** 2
               for y in years}

    # Annual partial adjustment, calibrated alpha for a zero baseline.
    # Codex review P2 (PR #9): both PA benchmarks must start from the SAME
    # income-percentile elasticity as the current construction (0.36 at the
    # 25th percentile), so the path gap isolates convergence rather than
    # conflating it with a different starting percentile.
    pa = pa_path(years, log_g, 0.0, g_dev0=NGA_2023_DEVIATION)

    # Decade-step recursion (faithful Equation 5 roll), x in deviations from
    # the 2023 anchor: theta*(g_t-10 - g_2023) + kappa*(x_t-10 - x_2023),
    # with the same 25th-percentile anchor deviation.
    dec = {2023: 0.0}
    for y in range(2033, END_YEAR + 1, 10):
        if y - 10 not in dec:
            dec[y - 10] = dec.get(y - 10, 0.0)
        dg = log_g[y] - log_g[y - 10]
        beta = BETA_MEAN + ETA * (NGA_2023_DEVIATION + (log_g[y - 10] - g0))
        dec[y] = ((1 + 10 * KAPPA) * dec[y - 10]
                  + beta * dg
                  + 10 * THETA * (log_g[y - 10] - g0))

    lr = -THETA / KAPPA * shock
    print('TEST 1: shock-then-flat income (+10% at 2024, then constant)')
    print('  long-run-implied endpoint of log energy gap: %.4f' % lr)
    print('  %-6s %14s %14s %14s' % ('year', 'current', 'annual PA', 'decade Eq5'))
    for y in (2023, 2033, 2053, 2073, 2100):
        row = [y, current[y], pa[y], dec.get(y, float('nan'))]
        print('  %-6d %14.4f %14.4f %14s' %
              (row[0], row[1], row[2],
               ('%.4f' % row[3]) if row[3] == row[3] else 'n/a'))
    print('  READING: the current construction should jump once and stop;')
    print('  the PA paths should keep moving toward %.4f with a' % lr)
    print('  half-life of about ln(2)/%.3f = %.0f years.' % (LAMBDA, math.log(2) / LAMBDA))
    print()


def run_all(delta_mode='off', eta=True, b_mode='plain', r_mode='recalibrated'):
    """Run the variant on all five SSP markers and print the comparison
    against the current construction.

    r_mode='recalibrated': R recomputed through the SAME variant law on the
    regional paths (the report's closure-consistent convention).
    r_mode='fixed-old':    R kept at the current construction's law -- a
    conditional experiment under an independent structural assumption about
    R, NOT a confidence interval. Common time effects (delta_mode) cancel
    exactly under 'recalibrated' and survive only under 'fixed-old'."""
    fe      = series('Final Energy.csv')
    r10_gdp = series('GDP - PPP.csv')
    r10_pop = series('Population.csv')
    pop     = nigeria_series('Population', 'million', 1e6)
    gdp     = nigeria_series('GDP|PPP', 'billion USD_2015/yr', 1e9)
    years   = list(range(BASE_YEAR, END_YEAR + 1))

    log_x0_nga = math.log(NGA_TFE_TJ / pop['SSP2'][BASE_YEAR])
    print('Variant run: delta_mode=%s  eta=%s  b_mode=%s  r_mode=%s' %
          (delta_mode, eta, b_mode, r_mode))
    print('%-8s %10s %10s %10s %12s %12s %10s %10s' %
          ('marker', 'x_bar %/yr', 'b_target', 'R10 eps*',
           'cur 2100 TJ', 'var 2100 TJ', 'var/cur50', 'var/cur100'))
    print('  (* R10 eps is the scenario-path proxy, not a structural elasticity)')
    for pid, (scen, narrative) in MARKERS.items():
        # Nigeria paths
        p0 = pop[narrative][BASE_YEAR]
        log_g = {y: math.log(interp(y, gdp[narrative]) / interp(y, pop[narrative]))
                 for y in years}
        x_bar = (log_g[END_YEAR] - log_g[BASE_YEAR]) / (END_YEAR - BASE_YEAR)
        if b_mode == 'static-adjusted':
            # Codex review P1 (PR #9): with ETA active the dynamics already
            # produce footnote 3's asymptotic slope; injecting it into
            # b_target double-counts. The correct growth-adjusted leg keeps
            # the generalized slope STATIC and switches the dynamic ETA
            # interaction off.
            nga_eta, b_target = 0.0, growth_adjusted_b(x_bar)
        else:
            nga_eta, b_target = (ETA if eta else 0.0), -THETA / KAPPA
        nga_pa = pa_path(years, log_g, log_x0_nga, eta=nga_eta,
                         b_target=b_target, delta_mode=delta_mode,
                         g_dev0=NGA_2023_DEVIATION)

        # Scenario-path proxy for the income response embedded in the IMAGE
        # R10 scenario itself: the ratio of cumulative log changes in
        # regional per-capita final energy and income, 2023-2100. This is a
        # scenario-path association, NOT the model's structural income
        # elasticity (structural change, prices and policy assumptions move
        # with income along the path); printed as the diagnostic the report
        # calls the single most consequential unverified number.
        r_eps_path = (math.log(interp(END_YEAR, fe[scen]) / interp(BASE_YEAR, fe[scen])
                             / (interp(END_YEAR, r10_pop[scen]) / interp(BASE_YEAR, r10_pop[scen])))
                      / (math.log(interp(END_YEAR, r10_gdp[scen]) / interp(END_YEAR, r10_pop[scen])
                                / (interp(BASE_YEAR, r10_gdp[scen]) / interp(BASE_YEAR, r10_pop[scen])))))

        # Regional paths through the SAME law (for R recalibration)
        r_log_g = {y: math.log(interp(y, r10_gdp[scen]) / interp(y, r10_pop[scen]))
                   for y in years}
        r_log_x0 = math.log(interp(BASE_YEAR, fe[scen]) / interp(BASE_YEAR, r10_pop[scen]))
        # The region is run through the same law with the same 25th-
        # percentile anchor deviation as Nigeria, mirroring the baseline's
        # symmetric use of ELASTICITY for both. Flagged in the docstring as
        # an approximation, not a measurement of R10's sample position. In
        # static-adjusted mode the region gets its OWN growth-adjusted
        # target, from its own mean income growth.
        r_x_bar = (r_log_g[END_YEAR] - r_log_g[BASE_YEAR]) / (END_YEAR - BASE_YEAR)
        r_b = growth_adjusted_b(r_x_bar) if b_mode == 'static-adjusted' else b_target
        r_pa = pa_path(years, r_log_g, r_log_x0, eta=nga_eta,
                       b_target=r_b, delta_mode=delta_mode,
                       g_dev0=NGA_2023_DEVIATION)

        # Variant energy with R per r_mode
        cur_2100 = var_2100 = cur_2050 = var_2050 = None
        for y in years:
            pt = interp(y, pop[narrative])
            fe_ratio = interp(y, fe[scen]) / interp(BASE_YEAR, fe[scen])
            pop_ratio = interp(y, r10_pop[scen]) / interp(BASE_YEAR, r10_pop[scen])
            Lr = r_log_g[y] - r_log_g[BASE_YEAR]
            if r_mode == 'recalibrated':
                # R10 residual: observed regional FE ratio divided by what
                # the region's own population and income give through the
                # variant law
                r10_residual = fe_ratio / (pop_ratio * math.exp(
                    r_pa[y] - r_pa[BASE_YEAR]))
            else:
                # conditional experiment: R from the CURRENT law
                r10_residual = fe_ratio / (pop_ratio * math.exp(
                    0.36 * Lr + 0.065 * Lr * Lr))
            E = NGA_TFE_TJ * (pt / p0) * math.exp(
                nga_pa[y] - nga_pa[BASE_YEAR]) * r10_residual
            if y in (2050, END_YEAR):
                L = log_g[y] - log_g[BASE_YEAR]
                r10_old = fe_ratio / (pop_ratio * math.exp(
                    0.36 * Lr + 0.065 * Lr * Lr))
                cur = NGA_TFE_TJ * (pt / p0) * math.exp(
                    0.36 * L + 0.065 * L * L) * r10_old
                if y == 2050:
                    cur_2050, var_2050 = cur, E
                else:
                    cur_2100, var_2100 = cur, E
        print('%-8s %10.2f %10.3f %10.3f %12.0f %12.0f %10.3f %10.3f' %
              (pid, x_bar * 100, b_target, r_eps_path,
               cur_2100, var_2100, var_2050 / cur_2050, var_2100 / cur_2100))
    print()


if __name__ == '__main__':
    coherence_test_shock()
    coherence_test_growth()
    run_all(delta_mode='off', eta=True, b_mode='plain')
    run_all(delta_mode='off', eta=True, b_mode='static-adjusted')
    run_all(delta_mode='decade-effects', eta=True, b_mode='plain')
    run_all(delta_mode='decade-effects', eta=True, b_mode='plain',
            r_mode='fixed-old')

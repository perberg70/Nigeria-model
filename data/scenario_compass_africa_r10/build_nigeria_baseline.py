#!/usr/bin/env python3
"""Build the Nigeria SSP baseline block for africa-prototype.html.

Written 2026-09-09 for the method Per set out this session. Emits a JavaScript
object holding, per SSP marker and per year to 2100:

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

Pass --update-prototype to copy the four generated blocks into the standalone
prototype/africa-prototype.html file. The generated block remains
the canonical data artifact; the HTML copy is kept in sync for the prototype.

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
"""
import csv, io, json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SC   = os.path.join(HERE, 'image32_ssp2021')
POP  = os.path.join(HERE, '..', 'iiasa_ssp_nigeria',
                    'Population_GDP_PPP_IIASA_SSP_15_Nigeria.csv')

# prototype pathway id -> (Scenario Compass scenario, IIASA population narrative)
MARKERS = {
    'ssp119': ('SSP2021-SSP1-SPA1-19-Default', 'SSP1'),
    'ssp126': ('SSP2021-SSP1-SPA1-26-Default', 'SSP1'),
    'ssp245': ('SSP2021-SSP2-SPA2-45-Default', 'SSP2'),
    'ssp370': ('SSP2021-SSP3-Baseline',        'SSP3'),
    'ssp585': ('SSP2021-SSP5-Baseline',        'SSP5'),
}
LOW  = ['Hydro', 'Solar', 'Wind', 'Nuclear', 'Biomass']
FOS  = ['Coal', 'Gas', 'Oil']
ALLS = LOW + FOS + ['Other']

# --- Nigeria's observed anchors, all already in the prototype ---------------
NGA_GRID_GWH   = 40975.0          # IEA 2023 grid generation: gas 31,601 + hydro 9,107 + solar 267 (page prints 40,976; its three lines sum to 40,975)
NGA_GENSET_GWH = 20600.0          # ETP 296.3 PJ at 25% efficiency; conditional estimate
NGA_HYDRO_GWH  = 9107.0
NGA_SOLAR_GWH  = 267.0            # IEA 2023, current release (211 in the older one)
NGA_TFE_TJ     = 2450511.0        # IEA 2023 total final energy, current release, Total row (sector rows sum to 2,450,509)
NGA_ANCHOR_MT  = 135.824          # Global Carbon Budget, 2024
ANCHOR_YEAR    = 2024
BASE_YEAR      = 2023
END_YEAR       = 2100

NGA_ALL_GWH   = NGA_GRID_GWH + NGA_GENSET_GWH
NGA_LOW_GWH   = NGA_HYDRO_GWH + NGA_SOLAR_GWH
NGA_ELEC_2023 = NGA_ALL_GWH * 3.6 / NGA_TFE_TJ
NGA_LOW_2023  = NGA_LOW_GWH / NGA_ALL_GWH
NGA_FOSSIL_GWH = NGA_ALL_GWH - NGA_LOW_GWH            # 52,201 = grid gas 31,601 + gensets 20,600
NGA_K0        = NGA_GENSET_GWH / NGA_FOSSIL_GWH       # 0.3946: gensets' share OF FOSSIL, 2023
# IEA RELEASE. The 2023 anchors above come from the IEA Energy Statistics Data Browser tables for Nigeria
# dated 28 Sep 2026, saved in data/iea_nigeria_2023/*_current_release.csv. Refreshed 2026-10-09 (ported
# from MSc-thesis, where the same refresh was made on 2026-10-08) from an older release (total final energy
# 2,465,907 TJ; grid 40,958 GWh = gas 31,640 + hydro 9,107 + solar 211). The older exports stay in that
# folder as the audit trail; the two releases must not be mixed in one calculation. The check below ties
# the typed constants to the saved tables, so the two cannot drift apart silently.
def _check_iea_anchors():
    d = os.path.join(HERE, '..', 'iea_nigeria_2023')
    f1 = os.path.join(d, 'iea_nigeria_2023_final_consumption_by_fuel_and_sector_current_release.csv')
    f2 = os.path.join(d, 'iea_nigeria_2023_electricity_generation_and_consumption_current_release.csv')
    if not (os.path.exists(f1) and os.path.exists(f2)):
        print('note: IEA current-release tables not found beside this script; anchors not cross-checked')
        return
    with io.open(f1, encoding='utf-8', newline='') as fh:
        tot = {r['sector']: r for r in csv.DictReader(fh)}['Total final consumption']
    with io.open(f2, encoding='utf-8', newline='') as fh:
        gen = {r['line']: float(r['value_GWh']) for r in csv.DictReader(fh)}
    assert float(tot['total_TJ']) == NGA_TFE_TJ, 'NGA_TFE_TJ differs from the saved IEA table'
    assert gen['Hydropower'] == NGA_HYDRO_GWH and gen['Solar PV'] == NGA_SOLAR_GWH, 'hydro/solar differ'
    assert gen['Natural gas'] + gen['Hydropower'] + gen['Solar PV'] == NGA_GRID_GWH, 'grid total differs'


_check_iea_anchors()

# Burke & Csereklyei (2016), Table 5, column 7 (total energy): the 10-year
# growth-rates model, estimated on within-country growth over 1960-2010. The
# 10-year elasticity is 0.48 at the sample's mean t-10 log GDP per capita and
# rises by eta = 0.13 per log unit of income (0.36 at the 25th percentile, 0.62
# at the 75th). Nigeria starts at the 25th-percentile value, 0.36 (Per's
# decision, 2026-10-05), matching its 29th-percentile position in 2023 world
# GDP per capita (MSc-thesis 03_models/2026-09-02 memo); the paper's percentiles
# are for its 1960-2010 sample, so that match is approximate. Integrating
# beta(L) = 0.36 + 0.13 L gives ln(E/E0) = 0.36 L + 0.065 L^2. The 10-year form
# integrated over decades is a projection assumption, not the paper's dynamic
# model. The Table 2 cross-section (0.63 at the 25th
# percentile, 0.11 squared term) was used until 2026-10-02 and is not, because it
# compares countries at one date rather than following growth over time.
ELASTICITY    = 0.36
ELASTICITY_Q  = 0.065

# --- NIGERIA'S PHYSICAL ENVELOPE -------------------------------------------
# Energy Transition Plan p.64, "Techno-economic assumptions in the power sector",
# column "Resource potential". These are PHYSICAL LIMITS FOR NIGERIA, not policy
# targets, which is why they may be used in a no-policy baseline while the ETP's
# generation mix (its net-zero case) may not.
#     large hydro 24 GW  ·  small hydro 3.5 GW  ·  utility solar 210 GW
#     onshore wind 3.2 GW  ·  biomass 29,800 PJ  ·  nuclear: none stated
CF_HYDRO   = NGA_HYDRO_GWH / (2.0 * 8760)   # 0.520, DERIVED from Nigeria's own data:
                                            # 9,107 GWh over the ETP's stated 2 GW (p.17).
                                            # [GAP: mixes years -- generation is 2023,
                                            # capacity is 2020. If capacity grew between
                                            # them the true factor, and the ceiling, are lower.]
CF_WIND    = 0.30                           # ASSUMED. Nigeria generated zero wind in 2023,
                                            # so nothing can be derived. Per's ruling
                                            # 2026-09-09. The cap binds at any plausible
                                            # value: even at an impossible CF of 1.0,
                                            # 3.2 GW yields only 28 TWh.
CEIL_HYDRO = 27.5 * 8760 * CF_HYDRO / 1000  # 125 TWh/yr
CEIL_WIND  = 3.2 * 8760 * CF_WIND  / 1000   # 8.4 TWh/yr
# WIND IS CAPPED ON THE TOTAL, which includes offshore: IAMC common-definitions makes
# `Wind` the parent of `Wind|Onshore` and `Wind|Offshore`, and only the aggregate was
# downloaded. So this asserts NIGERIA BUILDS NO OFFSHORE WIND. Per's ruling 2026-09-09,
# grounded in the ETP's own optimiser -- offered offshore with full costs and no resource
# cap, it built none across a run to 2060 -- but an assumption, not a measurement.
# Solar's 210 GW is UTILITY-SCALE ONLY; the ETP leaves distributed and stand-alone
# uncapped, which is why solar is the overflow recipient rather than a capped source.
NGA_LOWMIX    = {'Hydro': NGA_HYDRO_GWH / NGA_LOW_GWH,
                 'Solar': NGA_SOLAR_GWH / NGA_LOW_GWH,
                 'Wind': 0.0, 'Nuclear': 0.0, 'Biomass': 0.0}


def series(fn):
    out = {}
    with io.open(os.path.join(SC, fn), encoding='utf-8-sig') as fh:
        for r in csv.DictReader(fh):
            out.setdefault(r['Scenario name'], {})[int(r['year'])] = float(r['value'])
    return out


def interp(y, d):
    """Linear interpolation on a dict {year: value}; clamped at both ends."""
    ys = sorted(d)
    if y <= ys[0]:  return d[ys[0]]
    if y >= ys[-1]: return d[ys[-1]]
    for a, b in zip(ys, ys[1:]):
        if a <= y <= b:
            return d[a] + (d[b] - d[a]) * (y - a) / (b - a)


def nigeria_series(variable, unit=None, scale=1.0):
    """Nigeria's own population or GDP to 2100 -- no regional transfer.

    The export carries one Historical Reference row through 2025 and separate
    narrative rows from 2025 onward. Historical values are shared by all
    narratives; 2023 and 2024 are linearly interpolated between the 2020 and
    2025 historical anchors because this export is five-yearly. Scenario rows
    supply 2025 onward. This avoids the previous forecast-based back-cast.
    """
    historical = None
    forecasts = {}
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
            elif r['scenario'] in {narrative for _, narrative in MARKERS.values()}:
                forecasts[r['scenario']] = yrs

    if historical is None:
        raise ValueError('%s: Historical Reference row is missing' % variable)
    if 2020 not in historical or 2025 not in historical:
        raise ValueError('%s: Historical Reference must contain 2020 and 2025' % variable)

    out = {}
    for narrative, forecast in forecasts.items():
        yrs = {y: v for y, v in historical.items() if y <= 2025}
        yrs.update(forecast)
        for y in (BASE_YEAR, ANCHOR_YEAR):
            if y not in yrs:
                yrs[y] = interp(y, historical)
        out[narrative] = yrs

    missing = sorted({narrative for _, narrative in MARKERS.values()} - set(out))
    if missing:
        raise ValueError('%s: missing narrative rows: %s' % (variable, ', '.join(missing)))
    return out


# --- ONE INCOME-DRIVEN INDEX FOR HOUSEHOLD SOLID-FUEL USE, ported 2026-10-09 from MSc-thesis ---------
# idx(t) = (income per head_t / income per head_BASE_YEAR) ** COOK_ELASTICITY, on Nigeria's own SSP
# path (IIASA / OECD ENV-Growth export). The prototype's clean-cooking baseline reads it: the polluting
# share of people is p_t = p_2023 x idx (emitted below as BLOCK 4, NGA_DATA.health.pollutingIdxSSP,
# together with the elasticity, which the slider path also reads). It replaces the hand-pasted gdpSSP
# table the prototype held until 2026-10-09; the baseline clean-cooking shares are unchanged by the
# switch. The prototype holds a PASTED COPY of the block, spliced in by --update-prototype, so re-run
# this script after any change. In MSc-thesis the same function also feeds the residential-biomass
# bucket of an offline sector-split test; decision record there: 03_models/2026-10-09_shared-cooking-
# index.md. -0.67: Burke & Csereklyei (2016), CAMA WP 45/2016, Table 3 Panel C col. 1, SE 0.22: the GDP
# elasticity of residential primary solid-biofuel use per head in a 2010 cross-section of up to 132
# countries. TRANSFERRED to Nigeria and applied as a time path, and applied to a SHARE OF PEOPLE rather
# than energy per head (an assumption); not a Nigerian estimate.
COOK_ELASTICITY = -0.67

_INCOME_CACHE = {}


def _income_series(narrative):
    if not _INCOME_CACHE:
        gdp = nigeria_series('GDP|PPP', 'billion USD_2015/yr', 1e9)
        pop = nigeria_series('Population', 'million', 1e6)
        for n in gdp:
            _INCOME_CACHE[n] = (gdp[n], pop[n])
    return _INCOME_CACHE[narrative]


def cook_index(narrative, year):
    """(income per head at `year` / income per head in BASE_YEAR) ** COOK_ELASTICITY.

    Income per head is the narrative's GDP|PPP over its population, each linearly interpolated on the
    export's grid exactly as nigeria_series() and interp() define them (2023 and 2024 are themselves
    interpolated between the 2020 and 2025 historical anchors).
    """
    gdp, pop = _income_series(narrative)

    def income(y):
        return interp(y, gdp) / interp(y, pop)

    return (income(year) / income(BASE_YEAR)) ** COOK_ELASTICITY


def apply_envelope(lowmix_series, low_twh_series):
    """Nigeria's resource envelope, applied to the whole trajectory at once.

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
    ceil = {'Hydro': CEIL_HYDRO, 'Wind': CEIL_WIND}
    out_series, hi_water = [], 0.0
    for mix, low_twh in zip(lowmix_series, low_twh_series):
        out, pool = {}, 0.0
        for n in LOW:
            want = mix[n] * low_twh
            if n in ceil and want > ceil[n]:
                out[n] = ceil[n]; pool += want - ceil[n]
            else:
                out[n] = want
        out['Solar'] += pool

        hi_water = min(max(hi_water, out['Hydro']), CEIL_HYDRO)
        if out['Hydro'] < hi_water - 1e-9:
            need = hi_water - out['Hydro']
            for donors in (['Solar', 'Nuclear'], ['Biomass']):
                avail = sum(out[n] for n in donors)
                if avail <= 1e-12:
                    continue
                take = min(need, avail)
                for n in donors:
                    out[n] -= take * out[n] / avail
                need -= take
                if need <= 1e-9:
                    break
            out['Hydro'] = hi_water - need
        tot = sum(out.values())
        out_series.append({n: (out[n] / tot if tot > 0 else 0.0) for n in LOW})
    return out_series


def replace_fragment(text, start_marker, end_marker, fragment):
    """Replace one generated object fragment while preserving line indentation."""
    start = text.index(start_marker)
    line_start = text.rfind('\n', 0, start) + 1
    end = text.index(end_marker, start)
    return text[:line_start] + fragment.rstrip() + '\n\n' + text[end:]


def update_prototype(out):
    """Copy the generated blocks into the standalone prototype when requested."""
    prototype = os.path.normpath(os.path.join(HERE, '..', '..',
                                               'prototype',
                                               'africa-prototype.html'))
    with io.open(out, encoding='utf-8') as fh:
        generated = fh.read()
    with io.open(prototype, encoding='utf-8') as fh:
        html = fh.read()

    def fragment(marker, next_marker=None):
        start = generated.index(marker) + len(marker)
        end = generated.index(next_marker, start) if next_marker else len(generated)
        return generated[start:end].strip('\r\n')

    html = replace_fragment(
        html, 'emissions:{', '  /* --- Social Cost of Carbon',
        fragment('/* ---- BLOCK 1: drop-in replacement for NGA_DATA.emissions ---- */\n',
                 '/* ---- BLOCK 2: NGA_DATA.power.sspBaseline ---- */'))
    html = replace_fragment(
        html, 'sspBaseline:{', '         totalEnergy2023TJ:',
        fragment('/* ---- BLOCK 2: NGA_DATA.power.sspBaseline ---- */\n',
                 '/* ---- BLOCK 3: NGA_DATA.power.popSSP, historical reference plus forecasts ---- */'))
    html = replace_fragment(
        html, 'popSSP:{', '         elasticityTotal:',
        fragment('/* ---- BLOCK 3: NGA_DATA.power.popSSP, historical reference plus forecasts ---- */\n',
                 '/* ---- BLOCK 4: NGA_DATA.health.pollutingIdxSSP ---- */'))
    # BLOCK 4 ends at its OWN closing brace, not at a comment, because the prototype carries no
    # comments to anchor on.
    if 'pollutingIdxSSP:{' not in html:
        raise ValueError('prototype has no pollutingIdxSSP block')
    start = html.index('pollutingIdxSSP:{')
    line_start = html.rfind('\n', 0, start) + 1
    close = html.index('\n    },', start) + len('\n    },')
    html = (html[:line_start]
            + fragment('/* ---- BLOCK 4: NGA_DATA.health.pollutingIdxSSP ---- */\n').rstrip()
            + html[close:])

    with io.open(prototype, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(html)
    print('updated: %s' % prototype)


def main():
    tot   = series('Secondary Energy - Electricity.csv')
    fe    = series('Final Energy.csv')
    r10_gdp = series('GDP - PPP.csv')
    r10_pop = series('Population.csv')
    parts = {n: series('Secondary Energy - Electricity - %s.csv' % n) for n in ALLS}
    pop   = nigeria_series('Population', 'million', 1e6)
    gdp   = nigeria_series('GDP|PPP', 'billion USD_2015/yr', 1e9)

    # ANNUAL, not the source's 5-year grid. The model evaluates at integer years,
    # and interpolating a SHARE and a TOTAL separately does not preserve a cap
    # between grid points -- on the 5-year grid wind came out 1.5% and hydro 1.8%
    # above their ceilings in the in-between years. Emitting every year makes the
    # lookup exact and the envelope hold by construction. Costs about 40 KB.
    years = list(range(BASE_YEAR, END_YEAR + 1))
    block, checks = {}, []

    for pid, (scen, narrative) in MARKERS.items():
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
            L = math.log((interp(y, r10_gdp[scen]) / interp(y, r10_pop[scen])) /
                         (interp(ref, r10_gdp[scen]) / interp(ref, r10_pop[scen])))
            return fr / (pr * math.exp(ELASTICITY * L + ELASTICITY_Q * L * L))
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
        lowfos      = {y: sum(parts[n][scen][y] for n in LOW + FOS) for y in tot[scen]}
        fossil_frac = {y: sum(parts[n][scen][y] for n in FOS) / lowfos[y] for y in lowfos}
        low_frac    = {y: 1.0 - fossil_frac[y] for y in fossil_frac}
        lowsum      = {y: sum(parts[n][scen][y] for n in LOW) for y in sumparts}
        lowmix      = {n: {y: (parts[n][scen][y] / lowsum[y] if lowsum[y] > 0 else 0.0)
                           for y in lowsum} for n in LOW}

        g0   = interp(BASE_YEAR, gen_over_fe)      # regional electrification at 2023
        l0   = interp(BASE_YEAR, low_frac)         # regional low share at 2023

        rec = {'emisMt': [], 'populationFactor': [], 'gdpPerCapitaFactor': [],
               'demandFactor': [], 'r10FinalEnergyIntensityFactor': [],
               'incomeElasticity': [],
               'elecShare': [], 'lowShare': [], 'energyTJ': [],
               'r10EnergyIntensityFactor': [],
               'lowMix': {n: [] for n in LOW}, 'popN': [], 'gensetFossil': []}
        p0, y0 = pop[narrative][BASE_YEAR], (gdp[narrative][BASE_YEAR] / pop[narrative][BASE_YEAR])
        p_anchor = interp(ANCHOR_YEAR, pop[narrative])
        y_anchor = interp(ANCHOR_YEAR, gdp[narrative]) / p_anchor

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
                ELASTICITY * log_income + ELASTICITY_Q * log_income * log_income)
            marginal_beta = ELASTICITY + 2.0 * ELASTICITY_Q * log_income
            r10_factor = r10_efficiency(y, ANCHOR_YEAR)
            rec['populationFactor'].append(round(p_factor, 6))
            rec['gdpPerCapitaFactor'].append(round(y_factor, 6))
            rec['demandFactor'].append(round(demand_factor, 6))
            rec['r10FinalEnergyIntensityFactor'].append(round(r10_factor, 6))
            rec['incomeElasticity'].append(round(marginal_beta, 6))
            rec['emisMt'].append(round(max(
                0.0, NGA_ANCHOR_MT * demand_factor * r10_factor), 3))

            # 2. ELECTRIFICATION -- index on the generation basis, both sides.
            rec['elecShare'].append(round(min(1.0, NGA_ELEC_2023 * interp(y, gen_over_fe) / g0), 6))

            # 3. LAYER 1 -- low-emission share of all electricity, index-transferred.
            rec['lowShare'].append(round(min(1.0, NGA_LOW_2023 * interp(y, low_frac) / l0), 6))

            # 4. LAYER 2 -- within-low composition, converging from Nigeria's own
            #    2023 split toward the regional one, linear over 2023-2100.
            #    Nigeria is 97.7% hydro today; holding that fixed would meet a
            #    rising low share almost entirely with hydro its rivers cannot
            #    supply. The regional composition is a technology signal, not a
            #    policy one -- SSP3 stays hydro-heavy, SSP1 goes wind-and-solar.
            f = min(1.0, max(0.0, (y - BASE_YEAR) / float(END_YEAR - BASE_YEAR)))
            for n in LOW:
                rec['lowMix'][n].append(round(NGA_LOWMIX[n] + f * (interp(y, lowmix[n]) - NGA_LOWMIX[n]), 6))

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
            #    exactly at NGA_TFE_TJ.
            #    but y is the SCENARIO's own GDP per capita for NIGERIA (IIASA
            #    export, OECD ENV-Growth 2025, GDP|PPP in billion USD_2015/yr),
            #    not the user's growth rate. Only the ratio is used, so the
            #    currency base is immaterial.
            pt = interp(y, pop[narrative])
            yt = interp(y, gdp[narrative]) / pt
            L = math.log(yt / y0)
            income_factor = math.exp(ELASTICITY * L + ELASTICITY_Q * L * L)
            r10_energy_factor = r10_efficiency(y, BASE_YEAR)
            rec['energyTJ'].append(round(
                NGA_TFE_TJ * (pt / p0) * income_factor * r10_energy_factor, 1))
            rec['r10EnergyIntensityFactor'].append(round(r10_energy_factor, 6))
            rec['popN'].append(int(round(pt)))

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
            #    the CANDIDATE RULES table below main()'s ENVELOPE block; read
            #    them there. On the 2026-09-20 path the taken rule was the
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
            e_t = rec['elecShare'][-1]
            rec['gensetFossil'].append(round(min(max(NGA_K0 * NGA_ELEC_2023 / e_t, 0.0), 1.0), 6))

        # --- 7. NIGERIA'S RESOURCE ENVELOPE, applied to the whole trajectory --
        low_twh = [rec['lowShare'][i] * rec['elecShare'][i] * rec['energyTJ'][i] / 3.6 / 1000.0
                   for i in range(len(years))]
        desired = [{n: rec['lowMix'][n][i] for n in LOW} for i in range(len(years))]
        capped  = apply_envelope(desired, low_twh)
        for i in range(len(years)):
            for n in LOW:
                rec['lowMix'][n][i] = round(capped[i][n], 6)

        anchor_index = years.index(ANCHOR_YEAR)
        if abs(rec['emisMt'][anchor_index] - NGA_ANCHOR_MT) > 0.001:
            raise ValueError('%s: 2024 emissions anchor is not reproduced' % scen)
        block[pid] = rec

        # --- self-checks, printed not asserted away ------------------------
        checks.append((pid,
            abs(rec['elecShare'][0] - NGA_ELEC_2023),
            abs(rec['lowShare'][0]  - NGA_LOW_2023),
            abs(sum(rec['lowMix'][n][0] for n in LOW) - 1.0),
            max(abs(sum(rec['lowMix'][n][i] for n in LOW) - 1.0) for i in range(len(years)))))

    print('CHECKS  (all should be ~0)')
    print('%-8s %12s %12s %12s %12s' % ('marker', 'elec@2023', 'low@2023', 'mix@2023', 'mix worst'))
    for c in checks:
        print('%-8s %12.2e %12.2e %12.2e %12.2e' % c)
    print()
    print('Nigeria anchors reproduced: elec %.6f  low %.6f  hydro %.6f  k0 %.6f' %
          (NGA_ELEC_2023, NGA_LOW_2023, NGA_LOWMIX['Hydro'], NGA_K0))
    print()
    print('ENVELOPE  hydro ceiling %.1f TWh (27.5 GW x %.3f)   wind ceiling %.1f TWh (3.2 GW x %.2f)'
          % (CEIL_HYDRO, CF_HYDRO, CEIL_WIND, CF_WIND))
    print('%-8s %s' % ('marker', 'low-emission generation at its cap, TWh (hydro / wind), 2050 and 2100'))
    for pid in MARKERS:
        r = block[pid]; i50, i100 = years.index(2050), years.index(2100)
        lt = lambda i: r['lowShare'][i] * r['elecShare'][i] * r['energyTJ'][i] / 3.6 / 1000.0
        print('%-8s 2050 hydro %6.1f  wind %5.1f   |   2100 hydro %6.1f  wind %5.1f   |  genset share of fossil %5.1f%% -> %4.1f%%'
              % (pid, r['lowMix']['Hydro'][i50]*lt(i50), r['lowMix']['Wind'][i50]*lt(i50),
                 r['lowMix']['Hydro'][i100]*lt(i100), r['lowMix']['Wind'][i100]*lt(i100),
                 r['gensetFossil'][i50]*100, r['gensetFossil'][i100]*100))
    print()

    # The four candidate rules for the fossil split (section 6 in the loop
    # above), as the absolute back-up-generator fleet each implies in 2100.
    # Printed rather than written into a comment because the figures move
    # with the energy path -- see the section 6 comment for what happened
    # when they were hard-coded. fleet = elec x energy/3.6 x (1-low) x k.
    e0, k0 = NGA_ELEC_2023, NGA_K0
    g0 = NGA_GENSET_GWH / NGA_ALL_GWH
    print('CANDIDATE RULES  back-up-generator fleet in 2100, TWh, from %.1f TWh in 2023' % (NGA_GENSET_GWH / 1000.0))
    print('%-8s %12s %12s %12s %18s' % ('marker', 'held k0', 'k0*e0/e', 'g0*e0/e', 'k0*(1-e)/(1-e0)'))
    for pid in MARKERS:
        r = block[pid]; i = years.index(2100)
        e, low = r['elecShare'][i], r['lowShare'][i]
        total = e * r['energyTJ'][i] / 3.6 / 1000.0
        fossil = total * (1.0 - low)
        print('%-8s %12.1f %12.1f %12.1f %18.1f' % (
            pid, fossil * k0, fossil * r['gensetFossil'][i],
            total * g0 * e0 / e, fossil * k0 * (1.0 - e) / (1.0 - e0)))
    print('(taken: k0*e0/e -- the column that must equal gensetFossil x fossil generation)')
    print()

    # cumulative Mt 2025-2100, trapezoid on the annual interpolation, as the
    # figure printed under the emissions chart
    def cumulative(mt):
        d = dict(zip(years, mt))
        return int(round(sum((interp(y, d) + interp(y + 1, d)) / 2.0
                             for y in range(2025, END_YEAR))))

    out = os.path.join(HERE, 'nigeria_baseline_block.js')
    with io.open(out, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('/* GENERATED by data/scenario_compass_africa_r10/\n'
                 '   build_nigeria_baseline.py -- do not hand-edit, re-run to regenerate.\n'
                 '   Economy-wide emissions are Nigeria national drivers through the\n'
                 '   stage-sensitive Burke & Csereklyei aggregate-energy relation;\n'
                 '   an R10 efficiency residual (income effect removed) is an efficiency /\n'
                 '   technology proxy; R10 carbon intensity is not transferred.\n'
                 '   Sources, the transfer rule, the denominator decision and what is\n'
                 '   deliberately NOT carried are in that script\'s docstring. */\n\n')

        fh.write('/* ---- BLOCK 1: drop-in replacement for NGA_DATA.emissions ---- */\n')
        fh.write('  emissions:{\n    years:%s,\n' % json.dumps(years))
        for pid in MARKERS:
            fh.write('    %s:{mt:%s, populationFactor:%s, gdpPerCapitaFactor:%s,\n'
                     '       demandFactor:%s, r10FinalEnergyIntensityFactor:%s,\n'
                     '       incomeElasticity:%s, cum:%d},\n'
                     % (pid, json.dumps(block[pid]['emisMt']),
                        json.dumps(block[pid]['populationFactor']),
                        json.dumps(block[pid]['gdpPerCapitaFactor']),
                        json.dumps(block[pid]['demandFactor']),
                        json.dumps(block[pid]['r10FinalEnergyIntensityFactor']),
                        json.dumps(block[pid]['incomeElasticity']),
                        cumulative(block[pid]['emisMt'])))
        fh.write('  },\n\n')

        fh.write('/* ---- BLOCK 2: NGA_DATA.power.sspBaseline ---- */\n')
        fh.write('         sspBaseline:{\n           years:%s,\n' % json.dumps(years))
        for pid in MARKERS:
            r = block[pid]
            fh.write('           %s:{elecShare:%s,\n' % (pid, json.dumps(r['elecShare'])))
            fh.write('             lowShare:%s,\n' % json.dumps(r['lowShare']))
            fh.write('             energyTJ:%s,\n' % json.dumps(r['energyTJ']))
            fh.write('             r10EnergyIntensityFactor:%s,\n' %
                     json.dumps(r['r10EnergyIntensityFactor']))
            fh.write('             gensetFossil:%s,\n' % json.dumps(r['gensetFossil']))
            fh.write('             lowMix:{%s}},\n' % ','.join(
                '%s:%s' % (n, json.dumps(r['lowMix'][n])) for n in LOW))
        fh.write('         },\n\n')

        fh.write('/* ---- BLOCK 3: NGA_DATA.power.popSSP, historical reference plus forecasts ---- */\n')
        fh.write('         popSSP:{\n')
        for narr in ['SSP1', 'SSP2', 'SSP3', 'SSP5']:
            ys = pop[narr]
            fh.write('           %s:{%s},\n' % (narr, ','.join(
                '%d:%d' % (y, round(ys[y])) for y in sorted(ys))))
        fh.write('         },\n\n')

        fh.write('/* ---- BLOCK 4: NGA_DATA.health.pollutingIdxSSP ---- */\n')
        fh.write('    pollutingIdxSSP:{\n      eps:%s, years:%s,\n' % (COOK_ELASTICITY, json.dumps(years)))
        for narr in ['SSP1', 'SSP2', 'SSP3', 'SSP5']:
            fh.write('      %s:%s,\n' % (narr, json.dumps([round(cook_index(narr, y), 7) for y in years])))
        fh.write('    },\n')
    if '--update-prototype' in sys.argv[1:]:
        update_prototype(out)
    print('written: %s  (%d bytes)' % (out, os.path.getsize(out)))
    return 0


if __name__ == '__main__':
    sys.exit(main())

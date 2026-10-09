#!/usr/bin/env python3
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

Run: python sector_conversion.py  (output in sector_conversion_output.txt)
"""
import csv, io, math, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', '..')
UNSD = os.path.join(DATA, 'unsd_energy_nigeria', 'unsd_nigeria_energy_2020_2023.csv')
IEA = os.path.join(DATA, 'iea_nigeria_2023')
ETP = os.path.join(DATA, 'seforall_nigeria_etp', 'etp_cooking.csv')
SC = os.path.join(HERE, '..', 'image32_ssp2021')
BLOCK = os.path.join(HERE, '..', 'nigeria_baseline_block.js')

# --------------------------------------------------------------------------
# 1. NIGERIA 2023 BY SECTOR AND CARRIER (UNSD)
# Carriers: UNSD commodity codes. 0100 is the coal aggregate (0129 is its
# only component and is skipped to avoid double counting).
CARRIER = {
    '0100': 'coal', '3000': 'gas', '4630': 'lpg', '4652': 'gasoline',
    '4661': 'jet', '4669': 'kerosene', '4670': 'diesel', '4680': 'fuel_oil',
    '4692': 'other_oil', '4699': 'other_oil', '5110': 'wood', '5120': 'wood',
    '5150': 'wood', '5160': 'charcoal', '7000': 'electricity',
}
# Sectors: UNSD transaction codes. 1234/1235 are labelled by their match to
# the IEA country page (1235 electricity = IEA commercial and public services
# 29,184 TJ; 1234 kerosene = IEA other non-specified 8,096 TJ), since the
# UNSD code list is not held in this repository.
SECTOR = {'1231': 'residential', '1235': 'commercial', '121': 'industry',
          '122': 'transport', '1232': 'agriculture', '1234': 'other',
          '11': 'non_energy'}
CARRIERS = ['wood', 'charcoal', 'lpg', 'kerosene', 'gas', 'coal', 'fuel_oil',
            'gasoline', 'diesel', 'jet', 'other_oil', 'electricity']
SECTORS = ['residential', 'commercial', 'industry', 'transport', 'agriculture',
           'other', 'non_energy']


def unsd_2023():
    """Final energy in TJ, {sector: {carrier: TJ}}, plus the transformation
    rows needed for primary-energy factors."""
    m = {s: {c: 0.0 for c in CARRIERS} for s in SECTORS}
    extra = {}
    with io.open(UNSD, encoding='utf-8-sig') as fh:
        for r in csv.DictReader(fh):
            if r['TIME_PERIOD'] != '2023':
                continue
            com, tr, v = r['COMMODITY'], r['TRANSACTION'], float(r['OBS_VALUE'])
            if com == '7000':
                tj = v * 3.6
            elif r['UNIT_MEASURE'] == 'TJ':
                tj = v
            else:
                tj = v * float(r['CONVERSION_FACTOR'] or 0)
            extra[(com, tr)] = tj
            if com in CARRIER and tr in SECTOR:
                m[SECTOR[tr]][CARRIER[com]] += tj
    return m, extra


def iea_csv(name):
    out = {}
    with io.open(os.path.join(IEA, name), encoding='utf-8-sig') as fh:
        for r in list(csv.reader(fh))[1:]:
            if len(r) >= 2 and r[1].strip():
                out[r[0]] = float(r[1])
    return out


IEA_CUR = 'iea_nigeria_2023_final_consumption_by_fuel_and_sector_current_release.csv'
IEA_EL = 'iea_nigeria_2023_electricity_generation_and_consumption_current_release.csv'
IEA_SECTOR = {'Industry': 'industry', 'Transport': 'transport', 'Residential': 'residential',
              'Commercial and public services': 'commercial', 'Agriculture and forestry': 'agriculture',
              'Other non-specified': 'other', 'Non-energy use': 'non_energy'}
IEA_FUEL = {'coal_and_coal_products_TJ': 'coal', 'oil_products_TJ': 'oil', 'natural_gas_TJ': 'gas',
            'biofuels_and_waste_TJ': 'bio', 'electricity_TJ': 'electricity'}
FUEL_GROUP = {'wood': 'bio', 'charcoal': 'bio', 'lpg': 'oil', 'kerosene': 'oil', 'gasoline': 'oil',
              'diesel': 'oil', 'jet': 'oil', 'fuel_oil': 'oil', 'other_oil': 'oil', 'gas': 'gas',
              'coal': 'coal', 'electricity': 'electricity'}
GROUP_DEFAULT = {'bio': 'wood', 'oil': 'diesel', 'gas': 'gas', 'coal': 'coal', 'electricity': 'electricity'}


def iea_current(u):
    """IEA current-release 2023 final consumption, {sector: {carrier: TJ}}.
    The IEA table has five fuels; each cell is split into the carriers of
    CARRIERS in proportion to the UNSD 2023 split of the same sector and fuel
    group (wood vs charcoal; LPG, kerosene, petrol, diesel, jet, fuel oil).
    The IEA cell sets the level, UNSD only the within-cell shares."""
    m = {s: {c: 0.0 for c in CARRIERS} for s in SECTORS}
    with io.open(os.path.join(IEA, IEA_CUR), encoding='utf-8-sig') as fh:
        for r in csv.DictReader(fh):
            if r['sector'] not in IEA_SECTOR:
                continue
            s = IEA_SECTOR[r['sector']]
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


def iea_electricity():
    with io.open(os.path.join(IEA, IEA_EL), encoding='utf-8-sig') as fh:
        return {r['line']: float(r['value_GWh']) for r in csv.DictReader(fh)}


def section1():
    u, extra = unsd_2023()
    m = iea_current(u)
    print('1. NIGERIA 2023 FINAL ENERGY BY SECTOR AND CARRIER (IEA current release, PJ;')
    print('   UNSD 2023 splits each IEA fuel cell into carriers)')
    print('  %-12s' % '' + ''.join('%9s' % c[:8] for c in CARRIERS) + '%9s' % 'total')
    for s in SECTORS:
        print('  %-12s' % s + ''.join('%9.1f' % (m[s][c] / 1e3) for c in CARRIERS)
              + '%9.1f' % (sum(m[s].values()) / 1e3))
    col = {c: sum(m[s][c] for s in SECTORS) for c in CARRIERS}
    tot = sum(col.values())
    print('  %-12s' % 'total' + ''.join('%9.1f' % (col[c] / 1e3) for c in CARRIERS)
          + '%9.1f' % (tot / 1e3))
    print('  check, sector totals PJ (UNSD / IEA current release):')
    print('   ' + '  '.join('%s %.0f/%.0f' % (s[:5], sum(u[s].values()) / 1e3, sum(m[s].values()) / 1e3)
                           for s in SECTORS))
    ub = lambda s: (u[s]['wood'] + u[s]['charcoal']) / 1e3
    mb = lambda s: (m[s]['wood'] + m[s]['charcoal']) / 1e3
    print('   biomass by sector (UNSD / IEA): ' + '  '.join(
        '%s %.0f/%.0f' % (s[:5], ub(s), mb(s)) for s in ('residential', 'commercial', 'industry')))
    print('   total %.0f / %.0f PJ' % (sum(sum(u[s].values()) for s in SECTORS) / 1e3, tot / 1e3))
    bio = sum(m[s]['wood'] + m[s]['charcoal'] for s in SECTORS)
    print('  biomass (wood, residues, charcoal) %.0f PJ = %.1f%% of final energy; residential'
          % (bio / 1e3, 100 * bio / tot))
    print('  %.0f PJ of it; electricity %.2f%% of final energy' %
          ((m['residential']['wood'] + m['residential']['charcoal']) / 1e3, 100 * col['electricity'] / tot))
    print()
    return m, extra


# --------------------------------------------------------------------------
# 2. PRIMARY-TO-FINAL FACTORS BY CARRIER, 2023
def section2(m, extra):
    el = iea_electricity()                            # IEA current release, GWh
    gen = el['Natural gas'] + el['Hydropower'] + el['Solar PV']
    fin_el = sum(m[s]['electricity'] for s in SECTORS)
    gas_in = extra[('3000', '088')]                   # UNSD: gas into power plants
    gas_gen = extra[('7000T', '01')]                  # UNSD: gas-fired output
    wood_in = extra[('5110', '085CH')]                # wood into charcoal kilns
    char_out = extra[('5160', '01')]                  # charcoal produced
    eta_gas = gas_gen / gas_in                        # UNSD pair, one source
    gap = gen / el['Total final consumption']         # generation per final kWh
    gas_sh = el['Natural gas'] / gen
    pef = {'electricity_2023': gap * (gas_sh / eta_gas + (1 - gas_sh)),
           'electricity_all_gas': gap / eta_gas,
           'electricity_72pc_low': gap * (0.72 + 0.28 / eta_gas),
           'electricity_all_solar_hydro': gap}
    kiln = char_out / wood_in
    pef_fuel = {c: 1.0 for c in CARRIERS}
    pef_fuel['charcoal'] = 1 / kiln
    print('2. PRIMARY-TO-FINAL FACTORS (PEF, primary per unit of final), 2023')
    print('  gas plants: %.0f TJ in -> %.0f TJ out, efficiency %.3f (UNSD 088 and output)' % (gas_in, gas_gen, eta_gas))
    print('  generation / final electricity = %.0f / %.0f GWh = %.4f (IEA current release; exports,'
          % (gen, el['Total final consumption'], gap))
    print('  own use, losses fixed at 15%%, and a statistical difference); gas %.1f%% of generation' % (100 * gas_sh))
    print('  charcoal kilns: %.0f TJ wood -> %.0f TJ charcoal, efficiency %.3f -> PEF %.2f'
          % (wood_in, char_out, kiln, 1 / kiln))
    print('  electricity PEF per final unit (non-combustible renewables at output, the IEA')
    print('  physical-energy-content convention that the paper\'s TPES uses):')
    for k, v in pef.items():
        print('    %-30s %.3f' % (k, v))
    tfc = sum(sum(m[s].values()) for s in SECTORS)
    bottom = sum(m[s][c] * pef_fuel[c] for s in SECTORS for c in CARRIERS if c != 'electricity') \
        + fin_el * pef['electricity_2023']
    # TES is held only for the older release, so it is compared with the older
    # release's own TFC, never with the current-release matrix
    tes_old = sum(iea_csv('total_energy_supply_2023.csv').values())
    tfc_old = sum(iea_csv('total_final_consumption_by_sector_2023.csv').values())
    print('  P/F bottom-up %.3f (demand-linked conversion only); IEA TES/TFC %.3f (older release,'
          % (bottom / tfc, tes_old / tfc_old))
    print('  the only TES held). The difference is mainly gas burned by the oil and gas industry')
    print('  itself (UNSD 0912 %.0f PJ) and statistical differences, tied to production for export.'
          % (extra[('3000', '0912')] / 1e3))
    print()
    return pef, pef_fuel


# --------------------------------------------------------------------------
# 3. END-USE EFFICIENCY RATIOS rho = eta_elec / eta_displaced (low, central, high)
def etp_ratios():
    rows = {}
    with io.open(ETP, encoding='utf-8-sig') as fh:
        for r in csv.DictReader(fh):
            rows[(r['chart'], r['series'])] = r
    st = lambda s, y: float(rows[('national_stoves', s)][y])
    pj = lambda s, y: float(rows[('fuel_demand', s)][y])
    bio20 = pj('Biomass', '2020') / (st('Traditional biomass', '2020') + st('Biofuels', '2020'))
    lpg20 = pj('LPG', '2020') / st('LPG', '2020')
    el20 = pj('Electric', '2020') / st('Electric', '2020')
    el50 = pj('Electric', '2050') / st('Electric', '2050')
    lpg50 = pj('LPG', '2050') / st('LPG', '2050')
    return bio20, lpg20, el20, el50, lpg50


RHO = {
    # (sector group, carrier): (low, central, high)
    ('household', 'wood'):     (4.0, 6.0, 10.0),
    ('household', 'charcoal'): (2.0, 3.0, 4.0),
    ('household', 'lpg'):      (1.2, 1.5, 2.0),
    ('household', 'kerosene'): (1.5, 2.0, 3.0),
    ('household', 'gas'):      (1.2, 1.5, 2.0),
    ('industry', 'wood'):      (1.5, 2.5, 4.0),
    ('industry', 'charcoal'):  (1.5, 2.0, 3.0),
    ('industry', 'fossil'):    (1.0, 1.1, 1.5),
    ('transport', 'road'):     (2.3, 3.0, 5.0),
}
GROUP = {'residential': 'household', 'commercial': 'household', 'industry': 'industry',
         'agriculture': 'industry', 'other': 'household', 'transport': 'transport'}
NOT_ELECTRIFIABLE = {('transport', 'jet'), ('transport', 'other_oil')}


def rho_for(sector, carrier, case):
    g = GROUP.get(sector)
    if g is None or carrier in ('electricity', 'other_oil') or (sector, carrier) in NOT_ELECTRIFIABLE:
        return None
    if g == 'transport':
        key = ('transport', 'road')
    elif g == 'industry' and carrier not in ('wood', 'charcoal'):
        key = ('industry', 'fossil')
    elif g == 'household' and carrier in ('gasoline', 'diesel', 'fuel_oil', 'coal'):
        key = ('industry', 'fossil')
    else:
        key = (g, carrier)
    return RHO[key][case]


def section3():
    bio20, lpg20, el20, el50, lpg50 = etp_ratios()
    print('3. END-USE EFFICIENCY RATIOS rho = eta_electric / eta_displaced')
    print('  Evidence (final energy for the same service; ratios derived here unless stated):')
    print('  - ETP 2.0 cooking charts (Nigeria, net-zero pathway, pp. 37-40), per stove per year:')
    print('    biomass %.2f GJ, LPG %.2f GJ (2020); electric %.2f GJ (2020), %.2f GJ (2050), LPG %.2f GJ (2050)'
          % (bio20 * 1e3, lpg20 * 1e3, el20 * 1e3, el50 * 1e3, lpg50 * 1e3))
    print('    -> biomass/electric %.1f-%.1f, LPG/electric %.1f-%.1f, if service per stove is equal'
          % (bio20 / el50, bio20 / el20, lpg20 / el50, lpg20 / el20))
    print('    (an assumption; the ETP states no efficiencies and its PJ do not match IEA levels)')
    print('  - Uganda controlled cooking test (2025, via web search, unverified): 1 kg beans,')
    print('    hotplate 10.42 MJ, LPG 13.28, improved wood 38.81, three-stone 102.44 MJ')
    print('    -> three-stone/electric 9.8, improved wood/electric 3.7, LPG/electric 1.27')
    print('  - Akpasoh & Edeminam 2023, Nigeria CCT (sources.yaml; LHVs assumed): electric pressure')
    print('    cooker vs LPG 3.7-7.1, vs kerosene 1.7-3.6 -- an upper bound (sealed cooker)')
    print('  - US DOE (fueleconomy.gov / Fact #750, via web search): EV ~60% grid-to-wheel (77%')
    print('    older figure), gasoline vehicles 12-30% -> ratio about 2.3-5')
    print('  - Back-up gensets 15-25% fuel-to-electricity (2026-08-29 boundary memo) -> 4-6.7')
    print('  - Industry: no source held; boiler vs resistance heating assumed 1.0-1.5, fuelwood')
    print('    process heat vs electric 1.5-4. ASSUMPTIONS, flagged.')
    print('  Ranges used (low / central / high):')
    for k, v in RHO.items():
        print('    %-24s %4.1f %4.1f %4.1f' % ('%s, %s' % k, *v))
    print('  Not electrifiable here: aviation fuel, lubricants/bitumen, non-energy use.')
    print()


# --------------------------------------------------------------------------
# 4. NATIONAL ELECTRIFICATION -> FINAL ENERGY, BY ALLOCATION RULE
def pools(m, case):
    """Electrifiable non-electric final energy: list of (sector, carrier, TJ, rho)."""
    out = []
    for s in SECTORS:
        for c in CARRIERS:
            r = rho_for(s, c, case) if m[s][c] > 0 else None
            if r is not None:
                out.append((s, c, m[s][c], r))
    return out


ORDER = {
    'cooking first':   ['residential', 'commercial', 'other', 'transport', 'industry', 'agriculture'],
    'transport first': ['transport', 'residential', 'commercial', 'other', 'industry', 'agriculture'],
    'industry first':  ['industry', 'agriculture', 'transport', 'commercial', 'other', 'residential'],
}


def displace(pl, rule, t, weights=None):
    """Displacement d_p for each pool at scale parameter t in [0, 1]."""
    if rule == 'pro rata':
        return [t * p[2] for p in pl]
    if rule == 'IMAGE pattern':
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
    for p in pl:
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
    E0 = sum(m[s]['electricity'] for s in SECTORS)
    disp = sum(d)
    new_e = sum(di / p[3] for di, p in zip(d, pl))
    F = F0 - disp + new_e
    return F, E0 + new_e, F0, E0


def solve(m, pl, rule, share, weights=None):
    lo, hi = 0.0, 1.0
    F, E, F0, E0 = outcome(m, pl, displace(pl, rule, hi, weights))
    if E / F < share:
        return None
    for _ in range(80):
        mid = (lo + hi) / 2
        F, E, _, _ = outcome(m, pl, displace(pl, rule, mid, weights))
        if E / F < share:
            lo = mid
        else:
            hi = mid
    d = displace(pl, rule, hi, weights)
    F, E, F0, E0 = outcome(m, pl, d)
    return F, E, F0, E0, d


def image_weights(scen='SSP2021-SSP2-SPA2-45-Default', y1=2050):
    s = lambda fn: series(fn)[scen]
    inc = {'household': s('Final Energy - Residential and Commercial - Electricity.csv'),
           'industry': s('Final Energy - Industry - Electricity.csv'),
           'transport': s('Final Energy - Transportation - Electricity.csv')}
    dlt = {g: interp(y1, v) - interp(2023, v) for g, v in inc.items()}
    tot = sum(dlt.values())
    return {g: v / tot for g, v in dlt.items()}


def p_over_f(m, pl, d, F, E, pef_el, pef_fuel):
    P = 0.0
    for s in SECTORS:
        for c in CARRIERS:
            if c != 'electricity':
                P += m[s][c] * pef_fuel[c]
    for di, p in zip(d, pl):
        P -= di * pef_fuel[p[1]]
    return (P + E * pef_el) / F


def section4(m, pef, pef_fuel):
    w = image_weights()
    print('4. NATIONAL ELECTRIFICATION AT CONSTANT ENERGY SERVICE, 2023 STRUCTURE')
    print('  Target: electricity share of final energy (e). Displaced fuel d becomes d/rho of')
    print('  electricity. The prototype converts 1:1 (rho = 1). IMAGE pattern = new electricity')
    print('  split as IMAGE R10 SSP2-4.5 adds it 2023-2050: ' +
          ', '.join('%s %.2f' % kv for kv in w.items()))
    F0 = sum(sum(m[s].values()) for s in SECTORS)
    E0 = sum(m[s]['electricity'] for s in SECTORS)
    print('  2023: final energy %.0f PJ, electricity %.0f PJ (%.1f%%)' % (F0 / 1e3, E0 / 1e3, 100 * E0 / F0))
    rules = ['pro rata', 'cooking first', 'transport first', 'industry first', 'IMAGE pattern']
    targets = (0.20, 0.40, 0.67)
    print()
    print('  F/F0 = final energy relative to 2023 at the same service (central rho; lo/hi =')
    print('  high/low rho). The 1:1 model keeps F/F0 = 1, so its electricity at the same share is')
    print('  1/(F/F0) times this. P/F and P/P0 (primary relative to 2023) with the 2023 grid and')
    print('  with 72% low-emission power (bottom-up convention of section 2).')
    PF0 = p_over_f(m, pools(m, 1), [0.0] * len(pools(m, 1)), F0, E0, pef['electricity_2023'], pef_fuel)
    print('  %-16s %5s %8s %8s %9s %8s %8s %8s %8s' %
          ('rule', 'e', 'F/F0', 'F/F0 lo', 'F/F0 hi', 'P/F 23', 'P/F 72', 'P/P0 23', 'P/P0 72'))
    results = {}
    for rule in rules:
        for e in targets:
            row = {}
            for case in (0, 1, 2):
                pl = pools(m, case)
                res = solve(m, pl, rule, e, w)
                row[case] = (res, pl)
            res, pl = row[1]
            if res is None:
                print('  %-16s %5.2f   not reachable (non-electrifiable uses remain)' % (rule, e))
                continue
            F, E, _, _, d = res
            lo = row[2][0][0] / F0 if row[2][0] else float('nan')   # high rho -> lowest F
            hi = row[0][0][0] / F0 if row[0][0] else float('nan')
            pf23 = p_over_f(m, pl, d, F, E, pef['electricity_2023'], pef_fuel)
            pf72 = p_over_f(m, pl, d, F, E, pef['electricity_72pc_low'], pef_fuel)
            results[(rule, e)] = (F / F0, E, pf23, pf72)
            print('  %-16s %5.2f %8.3f %8.3f %9.3f %8.3f %8.3f %8.3f %8.3f' %
                  (rule, e, F / F0, lo, hi, pf23, pf72, pf23 * F / (PF0 * F0), pf72 * F / (PF0 * F0)))
    pl = pools(m, 1)
    F, E, _, _ = outcome(m, pl, [p[2] for p in pl])
    print('  maximum reachable share (all electrifiable uses switched, central rho): %.1f%%, '
          'final energy %.3f of 2023' % (100 * E / F, F / F0))
    pf0 = p_over_f(m, pl, [0.0] * len(pl), F0, E0, pef['electricity_2023'], pef_fuel)
    print('  P/F today (bottom-up, same convention): %.3f' % pf0)
    print()
    return results


# --------------------------------------------------------------------------
# 5. GENSETS
def section5(m):
    gwh = 20600.0                      # prototype's 2023 genset output estimate
    F0 = sum(sum(m[s].values()) for s in SECTORS)
    print('5. BACK-UP GENERATORS: THE BOUNDARY TERM')
    print('  The prototype counts an estimated 20.6 TWh of genset output as electricity, while')
    print('  the fuel stays in final energy if it is recorded at all (UNSD books all petrol and')
    print('  almost all diesel to road transport; the IEA says genset inputs and outputs "may not be')
    print('  properly reported", p. 502). Replacing that output with grid power at constant service:')
    for eta in (0.15, 0.20, 0.25):
        fuel = gwh * 3.6 / eta
        save = fuel - gwh * 3.6
        print('    genset efficiency %.0f%%: fuel %.0f PJ, final energy falls by %.0f PJ (%.1f%% of 2023)'
              % (100 * eta, fuel / 1e3, save / 1e3, 100 * save / F0))
    print('  ...if the fuel is inside final energy. If it is not recorded, final energy is')
    print('  understated today and nothing falls. The prototype\'s 2023 electrification share')
    print('  (8.99%%, older release) also uses gross generation plus genset output, against %.2f%%'
          % (100 * sum(m[s]['electricity'] for s in SECTORS) / F0))
    print('  final electricity in the balance; the share definition is itself a boundary choice.')
    print()


# --------------------------------------------------------------------------
# 6. IMAGE AFRICA R10
def series(fn):
    out = {}
    with io.open(os.path.join(SC, fn), encoding='utf-8-sig') as fh:
        for r in csv.DictReader(fh):
            out.setdefault(r['Scenario name'], {})[int(r['year'])] = float(r['value'])
    return out


def interp(y, d):
    ys = sorted(d)
    if y <= ys[0]:
        return d[ys[0]]
    if y >= ys[-1]:
        return d[ys[-1]]
    for a, b in zip(ys, ys[1:]):
        if a <= y <= b:
            return d[a] + (d[b] - d[a]) * (y - a) / (b - a)


SCEN = [('ssp119', 'SSP2021-SSP1-SPA1-19-Default'), ('ssp126', 'SSP2021-SSP1-SPA1-26-Default'),
        ('ssp245', 'SSP2021-SSP2-SPA2-45-Default'), ('ssp370', 'SSP2021-SSP3-Baseline'),
        ('ssp585', 'SSP2021-SSP5-Baseline')]
PRIMARY = ['Biomass', 'Coal', 'Gas', 'Oil', 'Hydro', 'Nuclear', 'Solar', 'Wind']


def section6():
    fe, gdp, pop = series('Final Energy.csv'), series('GDP - PPP.csv'), series('Population.csv')
    fel = series('Final Energy - Electricity.csv')
    fbio = series('Final Energy - Solids - Biomass.csv')
    prim = {k: series('Primary Energy - %s.csv' % k) for k in PRIMARY}
    # by-fuel rows, not the reported total, which the SSP1 by-fuel rows exceed
    # (scenario_compass_africa_r10/README.md)
    byfuel = {k: series('Secondary Energy - Electricity - %s.csv' % k)
              for k in ('Biomass', 'Coal', 'Gas', 'Hydro', 'Nuclear', 'Oil', 'Other', 'Solar', 'Wind')}
    LOWC = ('Hydro', 'Solar', 'Wind', 'Nuclear', 'Biomass')
    rc, rce = (series('Final Energy - Residential and Commercial.csv'),
               series('Final Energy - Residential and Commercial - Electricity.csv'))
    rcb = series('Final Energy - Residential and Commercial - Solids - Biomass.csv')
    print('6. IMAGE 3.2 AFRICA R10: P/F MOVES WITH THE SSP\'S OWN SECTOR TRANSITIONS')
    print('  P = sum of primary energy by source (IAMC direct-equivalent convention);')
    print('  F = final energy. eps = d ln(per-head quantity) / d ln(income per head).')
    print('  %-7s %5s %7s %7s %7s %7s %8s | %7s %7s %7s' %
          ('marker', 'year', 'P/F', 'el/F', 'bio/F', 'low/gen', 'Pbio/Fbio', 'eps_F', 'eps_P', 'eps_P/F'))
    rows = {}
    for pid, sc in SCEN:
        have = all(sc in prim[k] for k in PRIMARY)
        base = {}
        for y in (2020, 2050, 2100):
            F = interp(y, fe[sc])
            P = sum(interp(y, prim[k][sc]) for k in PRIMARY) if have else float('nan')
            yp = interp(y, gdp[sc]) / interp(y, pop[sc])
            n = interp(y, pop[sc])
            gen = sum(interp(y, byfuel[k][sc]) for k in byfuel if sc in byfuel[k])
            lowsh = sum(interp(y, byfuel[k][sc]) for k in LOWC if sc in byfuel[k]) / gen
            pb = interp(y, prim['Biomass'][sc]) / interp(y, fbio[sc]) if have else float('nan')
            vals = (P / F, interp(y, fel[sc]) / F, interp(y, fbio[sc]) / F, lowsh, pb)
            if y == 2020:
                base = dict(F=F / n, P=P / n, y=yp, pf=P / F)
                tail = ''
            else:
                dl = math.log(yp / base['y'])
                eF = math.log((F / n) / base['F']) / dl
                eP = math.log((P / n) / base['P']) / dl if have else float('nan')
                tail = '%7.3f %7.3f %7.3f' % (eF, eP, eP - eF)
                rows[(pid, y)] = (eF, eP)
            print('  %-7s %5d %7.3f %7.3f %7.3f %7.3f %8.2f | %s' %
                  (pid, y, vals[0], vals[1], vals[2], vals[3], vals[4], tail))
    print('  (SSP3 primary biomass is missing from the export, so its P is not formed.')
    print('  Pbio/Fbio = primary biomass per unit of final solid biomass: above 1 it carries')
    print('  modern bioenergy conversion -- biofuels, biomass power, BECCS in SSP1-1.9.)')
    print()
    # useful-energy check on Residential and Commercial
    print('  Useful-energy check, Residential and Commercial (central rho: electricity')
    print('  eta 0.70, other fuels 0.70/1.5, solid biomass 0.70/6):')
    print('  %-7s %6s %10s %10s %10s' % ('marker', 'to', 'eps_final', 'eps_useful', 'useful/F'))
    for pid, sc in SCEN:
        def useful(y):
            t, e, b = interp(y, rc[sc]), interp(y, rce[sc]), interp(y, rcb[sc])
            return 0.70 * e + (0.70 / 1.5) * (t - e - b) + (0.70 / 6) * b, t
        u0, f0 = useful(2020)
        n0, y0 = interp(2020, pop[sc]), interp(2020, gdp[sc]) / interp(2020, pop[sc])
        for y in (2050, 2100):
            u, f = useful(y)
            n, yp = interp(y, pop[sc]), interp(y, gdp[sc]) / interp(y, pop[sc])
            dl = math.log(yp / y0)
            print('  %-7s %6d %10.3f %10.3f %10.3f' % (
                pid, y, math.log((f / n) / (f0 / n0)) / dl, math.log((u / n) / (u0 / n0)) / dl, u / f))
    print('  Reading: where eps_useful sits well above eps_final, IMAGE\'s R&C final-energy path')
    print('  is shaped by conversion (fuel switching), not by falling service per head.')
    print()
    return rows


# --------------------------------------------------------------------------
# 7. WHAT IT MEANS FOR THE DEMAND LAW
def block_series(pid, key):
    txt = open(BLOCK, encoding='utf-8').read()
    i = txt.index('%s:{elecShare' % pid)
    j = txt.index('%s:[' % key, i)
    k = txt.index(']', j)
    return [float(x) for x in txt[j + len(key) + 2:k].split(',')]


def section7(m, results, rows):
    print('7. WHAT IT MEANS FOR THE DEMAND LAW')
    print('  eps_final = eps_primary - eps_P/F. The paper estimates eps_primary on 1960-2010 data,')
    print('  when electrification was thermal and raised P/F with income. Its own sector columns')
    print('  imply eps_P/F of about +0.07 at Nigeria\'s percentile and +0.12 to +0.19 in the long')
    print('  run (CONVERSION_FACTORS.md section C: final 0.28-0.30 vs total 0.36; 0.52-0.59 vs 0.71).')
    for y in (2050, 2100):
        print('  IMAGE R10, 2020 -> %d: eps_P/F = ' % y + ', '.join(
            '%s %+.3f' % (pid, rows[(pid, y)][1] - rows[(pid, y)][0])
            for pid, _ in SCEN if (pid, y) in rows and rows[(pid, y)][1] == rows[(pid, y)][1]))
    print()
    # SSP2-4.5 2050 illustration
    years = list(range(2023, 2101))
    tj = block_series('ssp245', 'energyTJ')[years.index(2050)]
    s_base = block_series('ssp245', 'elecShare')[years.index(2050)]
    F0 = sum(sum(m[s].values()) for s in SECTORS)
    E0 = sum(m[s]['electricity'] for s in SECTORS)
    el = iea_electricity()
    gen = el['Natural gas'] + el['Hydropower'] + el['Solar PV']
    proto_2023 = (gen + 20600.0) * 3.6 / F0    # prototype definition, current release
    proto_to_final = (E0 / F0) / proto_2023    # 2023 final share / prototype share
    print('  SSP2-4.5 in 2050 (baseline final energy %.2f EJ, prototype electrification %.1f%%).'
          % (tj / 1e6, 100 * s_base))
    print('  Approximation: 2050 has 2023\'s sector-carrier structure; prototype shares map to')
    print('  final-electricity shares by the 2023 ratio %.3f. TWh are final electricity.' % proto_to_final)
    w = image_weights()
    pl = pools(m, 1)
    eb = s_base * proto_to_final
    base = solve(m, pl, 'IMAGE pattern', eb, w)
    print('  %-24s %10s %12s %12s %10s' % ('slider (prototype %)', '1:1 TWh', 'converted TWh',
                                            'final EJ', 'K'))
    for s_user in (0.20, 0.40, 0.67):
        e = s_user * proto_to_final
        res = solve(m, pl, 'IMAGE pattern', e, w)
        K = res[0] / base[0]
        e11 = e * tj / 3.6 / 1e3
        conv = e * tj * K / 3.6 / 1e3
        print('  %-24s %10.0f %12.0f %12.2f %10.3f' % ('%.0f%%' % (100 * s_user), e11, conv,
                                                     tj * K / 1e6, K))
    print('  K = final energy at the user\'s electrification / at the baseline\'s, same service,')
    print('  IMAGE allocation, central rho. The prototype applies K = 1.')
    print()


if __name__ == '__main__':
    m, extra = section1()
    pef, pef_fuel = section2(m, extra)
    section3()
    results = section4(m, pef, pef_fuel)
    section5(m)
    rows = section6()
    section7(m, results, rows)

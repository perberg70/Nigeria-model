"""Does Nigeria's carbon intensity match Africa's (and IMAGE's Africa R10)?

EXPERIMENT BRANCH `experiment/partial-adjustment`, written 2026-10-09, for
Per's question: the energy systems differ, but perhaps the carbon intensity
matches. If it did, an R10 carbon-intensity path could be a candidate for
transfer (the baseline currently transfers none; see src/ssp_baseline/builder.py
docstring). Companion: data/scenario_compass_africa_r10/carbon_intensity/MEMO.md.

Observed data (2000-2024):
  * CO2 by source, population, GDP: Our World in Data CO2 dataset (Global
    Carbon Budget 2025; GDP Maddison Project 2023, 2011 int-$), African rows
    in data/owid_co2_africa/
  * Commercial primary energy for Africa and South Africa: the same file
    (Energy Institute / EIA; excludes traditional biomass)
  * Nigeria final energy: IEA, data/iea_nigeria_2023/
  * Africa final energy: IEA Africa chart exports, data/iea_africa_2023/
    (copied from MSc-thesis on 2026-10-09; --iea-africa DIR overrides)
Model data: IMAGE 3.2 Africa R10, data/scenario_compass_africa_r10/image32_ssp2021/
(2010-2020 rows are shared calibration values, not observations).

Run: python scripts/run_carbon_intensity.py --config config.yaml [--iea-africa DIR]
Nigeria's final-energy series are the IEA older release throughout (the only
2000-2023 series held); the current release covers 2023 alone.

The countries compared are configured (region.iso3, carbon_intensity.exclude_iso3,
carbon_intensity.owid_aggregate), and so are the trend, co-movement and IMAGE years.
The report labels are built from the same keys plus carbon_intensity.labels (region
name, ISO codes, the aggregate's and the excluded country's printed names), so they
follow the configured comparison. Prose notes about the data held (the 2010 break,
EIA's erratic primary energy) describe the committed inputs.
"""

from __future__ import annotations

import csv
import json
import logging
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config_paths import ConfigError, require, require_path, resolve_path
from scenario_data import Marker, load_markers, read_series, read_year_totals
from units import KWH_PER_GJ

from .reporting import short_year

AGGREGATE_KEY = "_aggregate"  # the OWID continental aggregate row, kept apart from countries
REGION_COLUMNS = (
    "co2",
    "coal_co2",
    "oil_co2",
    "gas_co2",
    "flaring_co2",
    "cement_co2",
    "gdp",
    "population",
)
# CO2 components that combustion() and section A take as 0 when blank
CO2_PARTS = ("coal_co2", "oil_co2", "gas_co2", "flaring_co2", "cement_co2")

LOGGER = logging.getLogger("demand_analysis.carbon_intensity")


@dataclass(frozen=True)
class ReportLabels:
    """Printed names of the configured rows (carbon_intensity.labels); they select nothing."""

    exclude_name: str
    exclude_short: str
    exclude_code: str
    aggregate_short: str
    aggregate_adjective: str


def _year_pair(pair: Any, key: str) -> tuple[int, int]:
    """A configured [first year, last year] window, inclusive."""
    if not isinstance(pair, list) or len(pair) != 2 or pair[0] > pair[1]:
        raise ConfigError(f"{key}: need [first year, last year], got {pair!r}")
    return int(pair[0]), int(pair[1])


@dataclass(frozen=True)
class CarbonIntensityParams:
    region_name: str
    iso3: str
    exclude_iso3: str
    owid_aggregate: str
    labels: ReportLabels
    markers: dict[str, Marker]
    image_dir: Path
    owid: Path
    wdi_growth: Path
    iea_tfc_series: Path
    iea_production_series: Path
    iea_africa_dir: Path | None
    first_year: int
    last_year: int
    gdp_first_year: int
    gdp_last_year: int
    wdi_base_year: int
    coal_ef: float
    bio_final_tj: float
    bio_supply_tj: float
    image_history_pathway: str
    aggregate_check_year: int
    trend_windows: tuple[tuple[int, int], ...]
    comovement_years: tuple[int, int]
    comovement_years_final_energy: tuple[int, int]
    image_history_years: tuple[int, ...]
    image_forward_years: tuple[int, int, int]  # reference, mid, end

    @classmethod
    def from_config(
        cls, config: Mapping[str, Any], iea_africa_override: Path | None = None
    ) -> CarbonIntensityParams:
        c = "carbon_intensity"
        first, last = require(config, f"{c}.observed_years")
        gdp_first, gdp_last = require(config, f"{c}.gdp_coverage_years")
        pathway = require(config, f"{c}.image_history_pathway")
        require(config, f"scenarios.{pathway}")
        if iea_africa_override is not None:
            africa = iea_africa_override
        else:
            # null in the config skips the Africa final-energy rows; the report says so.
            configured = require(config, "inputs.iea_africa_dir")
            africa = resolve_path(config, configured) if configured else None
        if africa is not None and not africa.is_dir():
            raise FileNotFoundError(f"IEA Africa directory not found: {africa}")
        windows = require(config, f"{c}.trend_windows")
        if not windows:
            raise ConfigError(f"{c}.trend_windows: need at least one window")
        history = tuple(int(y) for y in require(config, f"{c}.image_history_years"))
        if len(history) < 2 or list(history) != sorted(history):
            raise ConfigError(f"{c}.image_history_years: need two or more years, ascending")
        f = f"{c}.image_forward_years"
        return cls(
            region_name=require(config, "region.name"),
            iso3=require(config, "region.iso3"),
            exclude_iso3=require(config, f"{c}.exclude_iso3"),
            owid_aggregate=require(config, f"{c}.owid_aggregate"),
            labels=ReportLabels(
                **{k: require(config, f"{c}.labels.{k}") for k in ReportLabels.__annotations__}
            ),
            markers=load_markers(config),
            image_dir=require_path(config, "inputs.image_dir"),
            owid=require_path(config, "inputs.owid_co2"),
            wdi_growth=require_path(config, "inputs.wdi_gdp_growth"),
            iea_tfc_series=require_path(config, "inputs.iea.final_by_sector_2000_2023"),
            iea_production_series=require_path(config, "inputs.iea.domestic_production_2000_2023"),
            iea_africa_dir=africa,
            first_year=int(first),
            last_year=int(last),
            gdp_first_year=int(gdp_first),
            gdp_last_year=int(gdp_last),
            wdi_base_year=int(require(config, f"{c}.wdi_index_base_year")),
            coal_ef=require(config, f"{c}.coal_emission_factor"),
            bio_final_tj=require(config, f"{c}.biomass_final_tj_2023"),
            bio_supply_tj=require(config, f"{c}.biomass_supply_tj_2023"),
            image_history_pathway=pathway,
            aggregate_check_year=int(require(config, f"{c}.aggregate_check_year")),
            trend_windows=tuple(_year_pair(w, f"{c}.trend_windows") for w in windows),
            comovement_years=_year_pair(
                require(config, f"{c}.comovement_years"), f"{c}.comovement_years"
            ),
            comovement_years_final_energy=_year_pair(
                require(config, f"{c}.comovement_years_final_energy"),
                f"{c}.comovement_years_final_energy",
            ),
            image_history_years=history,
            image_forward_years=(
                int(require(config, f"{f}.reference")),
                int(require(config, f"{f}.mid")),
                int(require(config, f"{f}.end")),
            ),
        )

    @property
    def years(self) -> list[int]:
        return list(range(self.first_year, self.last_year + 1))

    @property
    def bio_final_per_supply(self) -> float:
        """Biomass final / supply, 2023, held constant (see the config's ASSUMED note)."""
        return self.bio_final_tj / self.bio_supply_tj


# --------------------------------------------------------------------------
def load_owid(p: CarbonIntensityParams):
    with p.owid.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    def f(v):
        return float(v) if v not in ("", None) else None

    by = {}
    for r in rows:
        key = AGGREGATE_KEY if r["country"] == p.owid_aggregate else r["iso_code"]
        by.setdefault(key, {})[int(r["year"])] = {
            k: f(r[k]) for k in r if k not in ("country", "iso_code", "year")
        }
    return by


def region(p: CarbonIntensityParams, by, exclude=(), need_gdp=False):
    """Sum the aggregate's countries (iso rows), optionally excluding some and, for
    GDP ratios, restricting to countries with GDP in every year of the coverage
    window (2000-2022) so numerator and denominator cover the same set. Other
    columns sum whichever countries report that year (see coverage_gaps)."""
    isos = [k for k in by if k != AGGREGATE_KEY and k not in exclude]
    if need_gdp:
        window = range(p.gdp_first_year, p.gdp_last_year + 1)
        isos = [k for k in isos if all(by[k].get(y, {}).get("gdp") for y in window)]
    out = {}
    for y in p.years:
        d = {}
        for c in REGION_COLUMNS:
            vals = [by[k][y][c] for k in isos if y in by[k] and by[k][y].get(c) is not None]
            d[c] = sum(vals) if vals else None
        out[y] = d
    return out, isos


def year_ranges(years):
    """[2000, 2001, 2002, 2005] -> '2000-2002, 2005'."""
    out, ys = [], sorted(years)
    for i, y in enumerate(ys):
        if i and y == ys[i - 1] + 1:
            out[-1][1] = y
        else:
            out.append([y, y])
    return ", ".join(str(a) if a == b else "%d-%d" % (a, b) for a, b in out)


def coverage_gaps(by, isos, columns, years):
    """{column: {iso: [years blank]}} for countries that report a column in some
    of the years but not all, so a regional sum changes its country set by year."""
    out = {}
    for c in columns:
        gaps = {}
        for k in isos:
            blank = [y for y in years if by[k].get(y, {}).get(c) is None]
            if blank and len(blank) < len(years):
                gaps[k] = blank
        if gaps:
            out[c] = gaps
    return out


def warn_coverage_gaps(p: CarbonIntensityParams, by):
    """Log, once per column, the country-years regional sums treat as 0. GDP is
    left out: GDP ratios use only countries covering the whole window."""
    isos = [k for k in by if k != AGGREGATE_KEY]
    columns = [c for c in REGION_COLUMNS if c != "gdp"]
    for c, gaps in coverage_gaps(by, isos, columns, p.years).items():
        never = [k for k in isos if all(by[k].get(y, {}).get(c) is None for y in p.years)]
        LOGGER.warning(
            "OWID %s: regional sums change country set by year; blank country-years are "
            "summed as 0: %s (%d countries never report it)",
            c,
            "; ".join("%s %s" % (k, year_ranges(ys)) for k, ys in sorted(gaps.items())),
            len(never),
        )


def blank_parts(s, years, columns=CO2_PARTS):
    """{column: [years]} where total CO2 is present but a component is blank."""
    out = {}
    for c in columns:
        ys = [y for y in years if s.get(y, {}).get("co2") is not None and s[y].get(c) is None]
        if ys:
            out[c] = ys
    return out


def combustion(d):
    """Fuel-combustion CO2: total minus flaring and cement (other industry is
    not reported for these countries)."""
    if d["co2"] is None:
        return None
    return d["co2"] - (d["flaring_co2"] or 0) - (d["cement_co2"] or 0)


def country_final(p: CarbonIntensityParams):
    tfc = read_year_totals(p.iea_tfc_series)
    bio = read_year_totals(p.iea_production_series, {"Biofuels and waste"})
    com = {y: tfc[y] - p.bio_final_per_supply * bio[y] for y in tfc}
    return tfc, com


def africa_final(d: Path):
    tfc = read_year_totals(d / "total_final_consumption_by_sector_africa_2000_2023.csv")
    bio = {}
    for s in ("residential", "commercial", "industry", "transport"):
        part = read_year_totals(
            d / ("%s_final_consumption_by_source_africa_2000_2023.csv" % s),
            {"Biofuels and waste"},
        )
        blank = [y for y in tfc if y not in part]
        if blank:
            LOGGER.warning(
                "IEA Africa %s biofuels and waste blank in %s; commercial final energy "
                "counts it as 0 there",
                s,
                year_ranges(blank),
            )
        for y, v in part.items():
            bio[y] = bio.get(y, 0.0) + v
    com = {y: tfc[y] - bio.get(y, 0.0) for y in tfc}
    return tfc, com


def wdi_gdp_index(p: CarbonIntensityParams, level_base):
    """GDP index chained by WDI real growth from the Maddison level in wdi_base_year."""
    with p.wdi_growth.open(encoding="utf-8") as fh:
        rows = json.load(fh)[1]
    g = {int(r["date"]): r["value"] for r in rows if r["value"] is not None}
    out = {p.wdi_base_year: level_base}
    for y in range(p.wdi_base_year + 1, p.last_year + 1):
        out[y] = out[y - 1] * (1 + g[y] / 100)
    return out


# --------------------------------------------------------------------------
def pct(a, b):
    return 100 * (b / a - 1) if a and b else float("nan")


def corr(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y, strict=False))
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    return sxy / (sx * sy) if sx and sy else float("nan")


def trend(s, y0, y1):
    """OLS slope of ln(s) on year, %/yr, over the years present in [y0, y1]."""
    ys = [y for y in range(y0, y1 + 1) if s.get(y)]
    if len(ys) < 4:
        return float("nan")
    lx = [math.log(s[y]) for y in ys]
    mx, my = sum(ys) / len(ys), sum(lx) / len(lx)
    b = sum((y - mx) * (v - my) for y, v in zip(ys, lx, strict=False)) / sum(
        (y - mx) ** 2 for y in ys
    )
    return 100 * (math.exp(b) - 1)


def dlog(s, y0, y1):
    return [math.log(s[y] / s[y - 1]) for y in range(y0 + 1, y1 + 1)]


def show(
    title,
    unit,
    series,
    windows,
    years=(2000, 2005, 2009, 2010, 2015, 2020, 2022, 2023),
    ref=None,
):
    """Levels in the printed `years` (report layout only), plus OLS trends within each
    window of carbon_intensity.trend_windows: the data regimes either side of the
    break in the region's oil CO2."""
    print("  %s (%s)" % (title, unit))
    print(
        "    %-30s" % ""
        + "".join("%7d" % y for y in years)
        + " ".join("%10s" % ("tr %s-%s" % (short_year(a), short_year(b))) for a, b in windows)
    )
    for name, s in series:
        cells = "".join("%7s" % ("%.3g" % s[y] if s.get(y) else "-") for y in years)
        trends = " ".join("%9.1f%%" % trend(s, a, b) for a, b in windows)
        print("    %-30s%s%s" % (name, cells, trends))
    if ref:
        a, b = ref
        print(
            "    %s / %s, level: %s"
            % (
                a[0],
                b[0],
                ", ".join(
                    "%d %.2f" % (y, a[1][y] / b[1][y]) for y in years if a[1].get(y) and b[1].get(y)
                ),
            )
        )


def comove(name_a, a, name_b, b, y0, y1):
    ya = [y for y in range(y0, y1 + 1) if a.get(y) and b.get(y)]
    y0, y1 = ya[0], ya[-1]
    da, db = dlog(a, y0, y1), dlog(b, y0, y1)
    print(
        "    %-24s vs %-26s %d-%d: r(annual change) %+.2f; trend %+.1f%%/yr vs %+.1f%%/yr"
        % (name_a, name_b, y0, y1, corr(da, db), trend(a, y0, y1), trend(b, y0, y1))
    )


# --------------------------------------------------------------------------
def report(p: CarbonIntensityParams):
    iea_africa = p.iea_africa_dir
    iso, excl = p.iso3, p.exclude_iso3
    years = p.years
    coal_ef = p.coal_ef
    windows = p.trend_windows

    # Printed names, from region.*, carbon_intensity.owid_aggregate and .labels.
    lab = p.labels
    name, agg, agg_short = p.region_name, p.owid_aggregate, lab.aggregate_short
    agg_excl = "%s excl. %s" % (agg, lab.exclude_name)  # the aggregate without exclude_iso3
    rest = "%s excl. %s and %s" % (agg, lab.exclude_code, iso)  # ... and without the region
    rest_plus = "%s excl. %s+%s" % (agg, lab.exclude_code, iso)
    agg_xn = "%s excl. %s" % (agg, iso)  # the aggregate without the region
    nga_mad = "%s (Maddison GDP)" % name
    nga_comm = "%s, per commercial final" % name
    rest_prim = "%s excl. %s+%s, OWID prim." % (agg_short, lab.exclude_code, iso)
    nga_comb_comm = "%s, comb. per comm. final" % name
    xn_comb_comm = "%s, comb/comm.fin" % agg_xn
    nga_tot = "%s, per total final" % name
    xn_tot = "%s, per total final" % agg_xn

    def image_series(fn):
        return read_series(p.image_dir, fn)

    by = load_owid(p)
    nga = by[iso]
    afr, afr_isos = region(p, by)
    afr_g, afr_g_isos = region(p, by, need_gdp=True)
    exz_g, _ = region(p, by, exclude=(excl,), need_gdp=True)
    exz, _ = region(p, by, exclude=(excl,))
    rest_g, _ = region(p, by, exclude=(excl, iso), need_gdp=True)
    rest_r, _ = region(p, by, exclude=(excl, iso))
    afr_xn, _ = region(p, by, exclude=(iso,))
    warn_coverage_gaps(p, by)
    for label, s in (
        (name, nga),
        (agg, afr),
        (agg_excl, exz),
        (rest, rest_r),
        (agg_xn, afr_xn),
        ("%s, GDP set" % agg, afr_g),
        ("%s, GDP set" % agg_excl, exz_g),
        ("%s, GDP set" % rest, rest_g),
    ):
        for c, ys in blank_parts(s, years).items():
            LOGGER.warning("%s %s blank in %s, taken as 0", label, c, year_ranges(ys))
    cy = p.aggregate_check_year
    print(
        'Check: sum of %d %s country rows vs OWID "%s" CO2, %d: %.1f vs %.1f Mt'
        % (
            len(afr_isos),
            lab.aggregate_adjective,
            p.owid_aggregate,
            cy,
            afr[cy]["co2"],
            by[AGGREGATE_KEY][cy]["co2"],
        )
    )
    print(
        "GDP ratios use the %d countries with Maddison GDP in every year %d-%d "
        "(missing: %s)"
        % (
            len(afr_g_isos),
            p.gdp_first_year,
            p.gdp_last_year,
            ", ".join(sorted(set(afr_isos) - set(afr_g_isos))),
        )
    )
    print()

    # A. composition (the printed years are report layout)
    print("A. WHAT THE CO2 IS MADE OF (share of fossil-and-industry CO2)")
    print(
        "    %-26s %6s %6s %6s %6s %7s %6s %8s"
        % ("", "year", "coal", "oil", "gas", "flaring", "cement", "total Mt")
    )
    for label, s in ((name, nga), (agg, afr), (agg_excl, exz)):
        for y in (2000, 2010, 2023):
            d = s[y]
            sh = [
                100 * (d[c] or 0) / d["co2"]
                for c in ("coal_co2", "oil_co2", "gas_co2", "flaring_co2", "cement_co2")
            ]
            print(
                "    %-26s %6d %5.0f%% %5.0f%% %5.0f%% %6.0f%% %5.0f%% %8.1f"
                % (label, y, *sh, d["co2"])
            )
    print()

    # B. intensities
    print("B. CARBON INTENSITIES, OBSERVED")
    g_nga = {y: nga[y]["gdp"] for y in years if nga.get(y, {}).get("gdp")}
    g_nga_wdi = wdi_gdp_index(p, g_nga[p.wdi_base_year])

    def co2(s):
        return {y: s[y]["co2"] for y in years if s.get(y, {}).get("co2")}

    def comb(s):
        return {y: combustion(s[y]) for y in years if s.get(y, {}).get("co2")}

    def per(num, den, k=1.0):
        return {y: k * num[y] / den[y] for y in num if den.get(y)}

    def gdp(s):
        return {y: s[y]["gdp"] for y in years if s.get(y, {}).get("gdp")}

    ci_gdp = {
        nga_mad: per(co2(nga), g_nga, 1e9),
        "%s (WDI real growth)" % name: per(co2(nga), g_nga_wdi, 1e9),
        agg: per(co2(afr_g), gdp(afr_g), 1e9),
        agg_excl: per(co2(exz_g), gdp(exz_g), 1e9),
        rest: per(co2(rest_g), gdp(rest_g), 1e9),
    }
    show(
        "B1. CO2 per GDP, fossil and industry",
        "kg per 2011 int-$",
        list(ci_gdp.items()),
        windows,
        ref=((name, ci_gdp[nga_mad]), (agg, ci_gdp[agg])),
    )
    cb_gdp = {
        nga_mad: per(comb(nga), g_nga, 1e9),
        agg: per(comb(afr_g), gdp(afr_g), 1e9),
        agg_excl: per(comb(exz_g), gdp(exz_g), 1e9),
        rest: per(comb(rest_g), gdp(rest_g), 1e9),
    }
    show(
        "B2. CO2 per GDP, fuel combustion only (no flaring, no cement)",
        "kg per 2011 int-$",
        list(cb_gdp.items()),
        windows,
        ref=((name, cb_gdp[nga_mad]), (rest, cb_gdp[rest])),
    )

    def pe(iso):
        return {
            y: by[iso][y]["primary_energy_consumption"]
            for y in years
            if by[iso].get(y, {}).get("primary_energy_consumption")
        }

    pe_afr = {
        y: by[AGGREGATE_KEY][y]["primary_energy_consumption"]
        for y in years
        if by[AGGREGATE_KEY].get(y, {}).get("primary_energy_consumption")
    }
    pe_exz = {y: pe_afr[y] - pe(excl)[y] for y in pe_afr if y in pe(excl)}
    pe_rest = {y: pe_exz[y] - pe(iso)[y] for y in pe_exz if y in pe(iso)}
    tfc_n, com_n = country_final(p)
    ci_e = {
        nga_comm: per(comb(nga), com_n, 1e9 / 1e3),
        "%s, per OWID primary" % name: per(comb(nga), pe(iso), 1e9 / (1e9 / KWH_PER_GJ)),
        "%s, per OWID primary" % agg: per(comb(afr), pe_afr, 1e9 / (1e9 / KWH_PER_GJ)),
        "%s excl. %s, OWID prim." % (agg, lab.exclude_short): per(
            comb(exz), pe_exz, 1e9 / (1e9 / KWH_PER_GJ)
        ),
        rest_prim: per(comb(rest_r), pe_rest, 1e9 / (1e9 / KWH_PER_GJ)),
    }
    print()
    show(
        "B3. Combustion CO2 per unit of commercial energy (no traditional biomass)",
        "kg/GJ",
        list(ci_e.items()),
        windows,
    )
    print("    (%s's OWID primary energy is EIA data and erratic -- e.g. 2010 below 2008;" % name)
    print("     its commercial final energy is IEA TFC minus estimated biomass. Final and")
    print("     primary are different denominators: compare changes, not levels, across them.)")
    ci_f = {
        nga_tot: per(co2(nga), tfc_n, 1e9 / 1e3),
        "%s, comb. per total final" % name: per(comb(nga), tfc_n, 1e9 / 1e3),
    }
    if iea_africa:
        tfc_a, com_a = africa_final(iea_africa)
        ci_f["%s, per total final" % agg] = per(co2(afr), tfc_a, 1e9 / 1e3)
        ci_f["%s, comb. per total final" % agg] = per(comb(afr), tfc_a, 1e9 / 1e3)
        tfc_xn = {y: tfc_a[y] - tfc_n[y] for y in tfc_a if y in tfc_n}
        com_xn = {y: com_a[y] - com_n[y] for y in com_a if y in com_n}
        ci_f[xn_tot] = per(co2(afr_xn), tfc_xn, 1e9 / 1e3)
        ci_e2 = {
            nga_comb_comm: ci_e[nga_comm],
            "%s, comb. per comm. final" % agg: per(comb(afr), com_a, 1e9 / 1e3),
            xn_comb_comm: per(comb(afr_xn), com_xn, 1e9 / 1e3),
        }
    print()
    show(
        "B4. CO2 per total final energy (biomass in the denominator)",
        "kg/GJ",
        list(ci_f.items()),
        windows,
    )
    if iea_africa:
        print()
        show(
            "B5. Combustion CO2 per commercial final energy, like for like",
            "kg/GJ",
            list(ci_e2.items()),
            windows,
            ref=((name, ci_e2[nga_comb_comm]), (agg_xn, ci_e2[xn_comb_comm])),
        )
    else:
        print(
            "    (%s final energy not found: pass --iea-africa DIR for B4/B5 %s rows.)" % (agg, agg)
        )
    print()

    # C. co-movement
    print("C. DO THEY MOVE TOGETHER? %s against the rest of %s (%s removed, so" % (name, agg, name))
    print(
        "   no mechanical correlation), after the 2010 break; r = correlation of annual log changes"
    )
    g0, g1 = p.comovement_years
    f0, f1 = p.comovement_years_final_energy
    comove("%s CO2/GDP" % iso, ci_gdp[nga_mad], rest_plus, ci_gdp[rest], g0, g1)
    comove("%s comb/GDP" % iso, cb_gdp[nga_mad], rest_plus, cb_gdp[rest], g0, g1)
    comove(
        "%s comb/comm.final" % iso,
        ci_e[nga_comm],
        "%s excl. %s+%s /prim." % (agg_short, lab.exclude_code, iso),
        ci_e[rest_prim],
        f0,
        f1,
    )
    if iea_africa:
        comove(
            "%s comb/comm.final" % iso,
            ci_e2[nga_comb_comm],
            "%s /comm.fin" % agg_xn,
            ci_e2[xn_comb_comm],
            f0,
            f1,
        )
        comove(
            "%s CO2/total final" % iso, ci_f[nga_tot], "%s /tot.fin" % agg_xn, ci_f[xn_tot], f0, f1
        )
    print()

    # D. IMAGE R10 "history" against observed aggregate
    hist = p.image_history_years
    steps = list(zip(hist, hist[1:], strict=False))
    print(
        "D. IMAGE R10 %d-%d ROWS AGAINST OBSERVED %s (relative change)"
        % (hist[0], hist[-1], agg.upper())
    )
    co2_i, afolu = image_series("Emissions - CO2.csv"), image_series("Emissions - CO2 - AFOLU.csv")
    fe_i, gdp_i = image_series("Final Energy.csv"), image_series("GDP - PPP.csv")
    feb_i = image_series("Final Energy - Solids - Biomass.csv")
    shown = p.markers[p.image_history_pathway]
    sc = shown.key
    ff = {y: co2_i[sc][y] - afolu[sc][y] for y in hist}
    print(
        "    fossil-and-industry CO2, Mt: IMAGE %s; GCB %s"
        % (
            ", ".join("%d %.0f" % (y, ff[y]) for y in ff),
            ", ".join("%d %.0f" % (y, afr[y]["co2"]) for y in ff),
        )
    )
    rows = [
        ("CO2", ff, co2(afr)),
        ("CO2/GDP", {y: ff[y] / gdp_i[sc][y] for y in ff}, ci_gdp[agg]),
        (
            "CO2/final energy",
            {y: ff[y] / fe_i[sc][y] for y in ff},
            ci_f.get("%s, per total final" % agg),
        ),
        (
            "CO2/commercial final",
            {y: ff[y] / (fe_i[sc][y] - feb_i[sc][y]) for y in ff},
            ci_e2.get("%s, comb. per comm. final" % agg) if iea_africa else None,
        ),
    ]
    print(
        "    %-22s" % ""
        + "".join(
            " %12s %12s"
            % (
                "IMAGE %s-%s" % (short_year(a), short_year(b)),
                "obs %s-%s" % (short_year(a), short_year(b)),
            )
            for a, b in steps
        )
    )
    for label, im, ob in rows:
        cells = ""
        for a, b in steps:
            o = "%11.1f%%" % pct(ob[a], ob[b]) if ob else "%12s" % "n/a"
            cells += " %11.1f%% %s" % (pct(im[a], im[b]), o)
        print("    %-22s%s" % (label, cells))
    print(
        "    (IMAGE rows are identical across markers to <0.15%%; %s shown. Observed" % shown.label
    )
    print("     rows: GCB CO2, Maddison GDP, IEA Africa final energy. IMAGE CO2/commercial final")
    print("     uses total CO2 and the observed row combustion CO2, since IMAGE does not separate")
    print("     flaring and cement.)")
    print()

    # E. IMAGE forward: what an R10 carbon-intensity path would carry
    ref, mid, end = p.image_forward_years
    r_, m_, e_ = short_year(ref), short_year(mid), short_year(end)
    print("E. IMAGE R10 FORWARD: WHAT AN R10 CARBON-INTENSITY PATH WOULD CARRY")
    pe_coal = image_series("Primary Energy - Coal.csv")
    print("    fossil-and-industry CO2 per final energy (all, and commercial = without solid")
    print(
        '    biomass), change from %d; "ex-coal" removes primary coal x %.1f kg/GJ from the'
        % (ref, coal_ef)
    )
    print(
        "    numerator (no CCS adjustment, so it fails where coal carries CCS or net CO2 nears 0)"
    )
    print(
        "    %-8s %8s %9s %9s %9s %11s %12s %12s"
        % (
            "marker",
            "CO2/FE" + r_,
            "FE ->" + m_,
            "FE ->" + e_,
            "comm->" + m_,
            "coal sh." + r_,
            "coal sh." + m_,
            "ex-coal comm->" + m_,
        )
    )
    for pid, marker in p.markers.items():
        s_ = marker.key

        def f(y, s_=s_):
            return co2_i[s_][y] - afolu[s_][y]

        def com(y, s_=s_):
            return fe_i[s_][y] - feb_i[s_][y]

        def coal(y, s_=s_):
            return pe_coal[s_][y] * coal_ef  # EJ x kg/GJ = Mt

        ok_mid = f(mid) > coal(mid)

        def exc(y):
            return (f(y) - coal(y)) / com(y)

        print(
            "    %-8s %8.1f %8.1f%% %8.1f%% %8.1f%% %10.0f%% %11s %12s"
            % (
                pid,
                f(ref) / fe_i[s_][ref],
                pct(f(ref) / fe_i[s_][ref], f(mid) / fe_i[s_][mid]),
                pct(f(ref) / fe_i[s_][ref], f(end) / fe_i[s_][end]),
                pct(f(ref) / com(ref), f(mid) / com(mid)),
                100 * coal(ref) / f(ref),
                ("%.0f%%" % (100 * coal(mid) / f(mid))) if ok_mid else "n/a",
                ("%.1f%%" % pct(exc(ref), exc(mid))) if ok_mid else "n/a",
            )
        )
    print(
        "    (kg CO2/GJ final energy, %d. Observed %s coal share of CO2, GCB: "
        "%.0f%% in %d.)" % (ref, agg, 100 * afr[ref]["coal_co2"] / afr[ref]["co2"], ref)
    )

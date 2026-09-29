"""Fetch Nigeria Admin-1 CMIP6 anomalies and derive six-zone prototype values.

The World Bank CCKP API returns 36 Nigerian states plus Abuja/FCT.  The
prototype aggregation below is deliberately a median of the constituent
state-level aggregates, with the state minimum and maximum retained.  It is
not an area-weighted zonal climate product.
"""

from __future__ import annotations

import csv
import json
import math
import re
import statistics
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path


API = (
    "https://cckpapi.worldbank.org/cckp/v1/"
    "cmip6-x0.25_climatology_tas,pr_anomaly_annual_2080-2099_"
    "median_{pathway}_ensemble_all_mean/all_countries_subnationals?_format=json"
)
NATIONAL_API = (
    "https://cckpapi.worldbank.org/cckp/v1/"
    "cmip6-x0.25_climatology_tas,pr_anomaly_annual_2080-2099_"
    "{percentile}_{pathway}_ensemble_all_mean/NGA?_format=json"
)
MODEL_API = (
    "https://cckpapi.worldbank.org/cckp/v1/"
    "cmip6-x0.25_climatology_tas,pr_anomaly_annual_2080-2099_"
    "mean_{pathway}_{model}_{variant}_mean/all_countries_subnationals?_format=json"
)
S3_DATASETS = (
    "https://wbg-cckp.s3.amazonaws.com/?list-type=2&"
    "prefix=data/cmip6-x0.25/{variable}/&delimiter=/"
)
PATHWAYS = ("ssp119", "ssp126", "ssp245", "ssp370", "ssp585")
PERCENTILES = ("median", "p10", "p90")
MODEL_PATHWAYS = ("ssp126", "ssp245", "ssp370", "ssp585")

# Codes and names are returned together by the same endpoint with _format=xlsx.
# Keeping the mapping explicit makes code/name changes visible in review.
CODE_TO_STATE = {
    "NGA.1822211": "Adamawa",
    "NGA.1822212": "Akwa Ibom",
    "NGA.1822213": "Anambra",
    "NGA.1822215": "Benue",
    "NGA.1822216": "Borno",
    "NGA.1822217": "Cross River",
    "NGA.1822218": "Delta",
    "NGA.1822219": "Edo",
    "NGA.1822221": "Abuja",
    "NGA.1822222": "Imo",
    "NGA.1822223": "Jigawa",
    "NGA.1822224": "Kaduna",
    "NGA.1822225": "Kano",
    "NGA.1822226": "Katsina",
    "NGA.1822227": "Kebbi",
    "NGA.1822228": "Kogi",
    "NGA.1822229": "Kwara",
    "NGA.1822230": "Lagos",
    "NGA.1822231": "Niger",
    "NGA.1822232": "Ogun",
    "NGA.1822234": "Osun",
    "NGA.1822235": "Oyo",
    "NGA.1822239": "Taraba",
    "NGA.1822240": "Yobe",
    "NGA.18265698": "Abia",
    "NGA.18265699": "Bauchi",
    "NGA.18265700": "Bayelsa",
    "NGA.18265701": "Ebonyi",
    "NGA.18265702": "Ekiti",
    "NGA.18265703": "Enugu",
    "NGA.18265704": "Gombe",
    "NGA.18265705": "Nassarawa",
    "NGA.18265706": "Ondo",
    "NGA.18265707": "Plateau",
    "NGA.18265708": "Rivers",
    "NGA.18265709": "Sokoto",
    "NGA.18265710": "Zamfara",
}

STATE_TO_ZONE = {
    **{s: "North Central" for s in ("Benue", "Kogi", "Kwara", "Nassarawa", "Niger", "Plateau", "Abuja")},
    **{s: "North East" for s in ("Adamawa", "Bauchi", "Borno", "Gombe", "Taraba", "Yobe")},
    **{s: "North West" for s in ("Jigawa", "Kaduna", "Kano", "Katsina", "Kebbi", "Sokoto", "Zamfara")},
    **{s: "South East" for s in ("Abia", "Anambra", "Ebonyi", "Enugu", "Imo")},
    **{s: "South South" for s in ("Akwa Ibom", "Bayelsa", "Cross River", "Delta", "Edo", "Rivers")},
    **{s: "South West" for s in ("Ekiti", "Lagos", "Ogun", "Ondo", "Osun", "Oyo")},
}


def scalar(record: dict[str, float]) -> float:
    if len(record) != 1:
        raise ValueError(f"Expected one climatology value, got {record!r}")
    return float(next(iter(record.values())))


def fetch(pathway: str) -> list[dict[str, object]]:
    url = API.format(pathway=pathway)
    request = urllib.request.Request(url, headers={"User-Agent": "MSc-thesis climate-data retrieval/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = json.load(response)
    if payload.get("metadata", {}).get("status") != "success":
        raise RuntimeError(payload.get("metadata"))

    rows = []
    for code, state in CODE_TO_STATE.items():
        rows.append(
            {
                "pathway": pathway,
                "code": code,
                "state": state,
                "zone": STATE_TO_ZONE[state],
                "temperature_anomaly_c": scalar(payload["data"]["tas"][code]),
                "precipitation_anomaly_mm_year": scalar(payload["data"]["pr"][code]),
            }
        )
    return rows


def fetch_national(pathway: str) -> list[dict[str, object]]:
    rows = []
    for percentile in PERCENTILES:
        url = NATIONAL_API.format(pathway=pathway, percentile=percentile)
        request = urllib.request.Request(
            url, headers={"User-Agent": "MSc-thesis climate-data retrieval/1.0"}
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = json.load(response)
        if payload.get("metadata", {}).get("status") != "success":
            raise RuntimeError(payload.get("metadata"))
        rows.append(
            {
                "pathway": pathway,
                "percentile": percentile,
                "temperature_anomaly_c": scalar(payload["data"]["tas"]["NGA"]),
                "precipitation_anomaly_mm_year": scalar(payload["data"]["pr"]["NGA"]),
            }
        )
    return rows


def discover_model_runs(variable: str) -> dict[str, set[tuple[str, str]]]:
    """Return the individual model/variant runs CCKP publishes by pathway."""
    url = S3_DATASETS.format(variable=variable)
    request = urllib.request.Request(
        url, headers={"User-Agent": "MSc-thesis climate-data retrieval/1.0"}
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        root = ET.fromstring(response.read())
    namespace = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
    output: dict[str, set[tuple[str, str]]] = defaultdict(set)
    pattern = re.compile(
        rf"data/cmip6-x0\.25/{re.escape(variable)}/"
        r"(?P<model>.+)-(?P<variant>r\d+i\d+p\d+f\d+)-(?P<pathway>ssp\d+)/$"
    )
    for node in root.findall("s3:CommonPrefixes/s3:Prefix", namespace):
        match = pattern.match(node.text or "")
        if match:
            output[match.group("pathway")].add(
                (match.group("model"), match.group("variant"))
            )
    return output


def fetch_model_states(task: tuple[str, str, str]) -> list[dict[str, object]]:
    pathway, model, variant = task
    url = MODEL_API.format(pathway=pathway, model=model, variant=variant)
    request = urllib.request.Request(
        url, headers={"User-Agent": "MSc-thesis climate-data retrieval/1.0"}
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = json.load(response)
    if payload.get("metadata", {}).get("status") != "success":
        raise RuntimeError(payload.get("metadata"))
    data = payload.get("data", {})
    if not isinstance(data, dict):
        return []
    temperature = data.get("tas", {})
    precipitation = data.get("pr", {})
    return [
        {
            "pathway": pathway,
            "model": model,
            "variant": variant,
            "code": code,
            "state": state,
            "zone": STATE_TO_ZONE[state],
            "temperature_anomaly_c": scalar(temperature[code]) if code in temperature else None,
            "precipitation_anomaly_mm_year": (
                scalar(precipitation[code]) if code in precipitation else None
            ),
        }
        for code, state in CODE_TO_STATE.items()
    ]


def fetch_all_model_states() -> list[dict[str, object]]:
    tas_runs = discover_model_runs("tas")
    pr_runs = discover_model_runs("pr")
    tasks = [
        (pathway, model, variant)
        for pathway in MODEL_PATHWAYS
        for model, variant in sorted(tas_runs[pathway] | pr_runs[pathway])
    ]
    rows: list[dict[str, object]] = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        for result in executor.map(fetch_model_states, tasks):
            rows.extend(result)
    return rows


def percentile(values: list[float], probability: float) -> float:
    """Linear percentile interpolation, matching the usual ensemble quantile."""
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def derive_model_zone_rows(
    state_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in state_rows:
        grouped[
            (
                str(row["pathway"]),
                str(row["model"]),
                str(row["variant"]),
                str(row["zone"]),
            )
        ].append(row)
    output = []
    for (pathway, model, variant, zone), rows in sorted(grouped.items()):
        temperatures = [
            float(r["temperature_anomaly_c"])
            for r in rows
            if r["temperature_anomaly_c"] is not None
        ]
        precipitation = [
            float(r["precipitation_anomaly_mm_year"])
            for r in rows
            if r["precipitation_anomaly_mm_year"] is not None
        ]
        output.append(
            {
                "pathway": pathway,
                "model": model,
                "variant": variant,
                "zone": zone,
                "state_count": len(rows),
                "temperature_anomaly_c": (
                    round(statistics.median(temperatures), 3) if temperatures else None
                ),
                "precipitation_anomaly_mm_year": (
                    round(statistics.median(precipitation), 3) if precipitation else None
                ),
            }
        )
    return output


def derive_zone_ensemble_rows(
    model_zone_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in model_zone_rows:
        grouped[(str(row["pathway"]), str(row["zone"]))].append(row)
    output = []
    for (pathway, zone), rows in sorted(grouped.items()):
        temperatures = [
            float(r["temperature_anomaly_c"])
            for r in rows
            if r["temperature_anomaly_c"] is not None
        ]
        precipitation = [
            float(r["precipitation_anomaly_mm_year"])
            for r in rows
            if r["precipitation_anomaly_mm_year"] is not None
        ]
        output.append(
            {
                "pathway": pathway,
                "zone": zone,
                "temperature_model_count": len(temperatures),
                "precipitation_model_count": len(precipitation),
                "temperature_median_c": round(statistics.median(temperatures), 2),
                "temperature_p10_c": round(percentile(temperatures, 0.10), 2),
                "temperature_p90_c": round(percentile(temperatures, 0.90), 2),
                "precipitation_median_mm_year": round(statistics.median(precipitation), 2),
                "precipitation_p10_mm_year": round(percentile(precipitation, 0.10), 2),
                "precipitation_p90_mm_year": round(percentile(precipitation, 0.90), 2),
            }
        )
    return output


def derive_zone_rows(state_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in state_rows:
        grouped[(str(row["pathway"]), str(row["zone"]))].append(row)

    output = []
    for (pathway, zone), rows in sorted(grouped.items()):
        temperatures = [float(r["temperature_anomaly_c"]) for r in rows]
        precipitation = [float(r["precipitation_anomaly_mm_year"]) for r in rows]
        output.append(
            {
                "pathway": pathway,
                "zone": zone,
                "state_count": len(rows),
                "temperature_median_c": round(statistics.median(temperatures), 2),
                "temperature_min_c": round(min(temperatures), 2),
                "temperature_max_c": round(max(temperatures), 2),
                "precipitation_median_mm_year": round(statistics.median(precipitation), 2),
                "precipitation_min_mm_year": round(min(precipitation), 2),
                "precipitation_max_mm_year": round(max(precipitation), 2),
            }
        )
    return output


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    out = root / "data" / "nigeria_regional_climate"
    state_rows = [row for pathway in PATHWAYS for row in fetch(pathway)]
    national_rows = [row for pathway in PATHWAYS for row in fetch_national(pathway)]
    zone_rows = derive_zone_rows(state_rows)
    model_state_rows = fetch_all_model_states()
    model_zone_rows = derive_model_zone_rows(model_state_rows)
    zone_ensemble_rows = derive_zone_ensemble_rows(model_zone_rows)
    write_csv(out / "cckp_cmip6_admin1_anomalies_2080-2099.csv", state_rows)
    write_csv(out / "cckp_cmip6_geopolitical_zone_summary_2080-2099.csv", zone_rows)
    write_csv(out / "cckp_cmip6_nigeria_ensemble_2080-2099.csv", national_rows)
    write_csv(out / "cckp_cmip6_model_admin1_anomalies_2080-2099.csv", model_state_rows)
    write_csv(out / "cckp_cmip6_model_geopolitical_zone_2080-2099.csv", model_zone_rows)
    write_csv(out / "cckp_cmip6_geopolitical_zone_ensemble_2080-2099.csv", zone_ensemble_rows)
    print(
        f"Retrieved {date.today().isoformat()}: {len(state_rows)} state rows; "
        f"{len(zone_rows)} zone rows; {len(national_rows)} national ensemble rows; "
        f"{len(model_state_rows)} model-state rows; {len(zone_ensemble_rows)} zonal ensemble rows"
    )


if __name__ == "__main__":
    main()

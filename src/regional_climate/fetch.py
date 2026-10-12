"""Fetch CMIP6 anomalies for one country's Admin-1 units from the World Bank CCKP API.

Network access is required (cckpapi.worldbank.org and the CCKP S3 listing). The
country code, period, pathways and the Admin-1 unit list come from the
``regional_climate`` section of the configuration.
"""

from __future__ import annotations

import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any

from config_paths import require, require_path

from .admin_units import AdminUnit, load_admin_units

API = (
    "https://cckpapi.worldbank.org/cckp/v1/"
    "cmip6-x0.25_climatology_tas,pr_anomaly_annual_{period}_"
    "median_{pathway}_ensemble_all_mean/all_countries_subnationals?_format=json"
)
NATIONAL_API = (
    "https://cckpapi.worldbank.org/cckp/v1/"
    "cmip6-x0.25_climatology_tas,pr_anomaly_annual_{period}_"
    "{percentile}_{pathway}_ensemble_all_mean/{country}?_format=json"
)
MODEL_API = (
    "https://cckpapi.worldbank.org/cckp/v1/"
    "cmip6-x0.25_climatology_tas,pr_anomaly_annual_{period}_"
    "mean_{pathway}_{model}_{variant}_mean/all_countries_subnationals?_format=json"
)
S3_DATASETS = (
    "https://wbg-cckp.s3.amazonaws.com/?list-type=2&prefix=data/cmip6-x0.25/{variable}/&delimiter=/"
)


@dataclass(frozen=True)
class FetchSettings:
    iso3: str
    period: str
    pathways: tuple[str, ...]
    model_pathways: tuple[str, ...]
    percentiles: tuple[str, ...]
    units: tuple[AdminUnit, ...]
    user_agent: str
    timeout_s: float
    max_workers: int
    output_dir: Path
    outputs: dict[str, str]

    @classmethod
    def from_config(cls, config: Mapping[str, Any]) -> FetchSettings:
        c = "regional_climate"
        return cls(
            iso3=require(config, "region.iso3"),
            period=str(require(config, f"{c}.period")),
            pathways=tuple(require(config, f"{c}.pathways")),
            model_pathways=tuple(require(config, f"{c}.model_pathways")),
            percentiles=tuple(require(config, f"{c}.percentiles")),
            units=tuple(load_admin_units(require_path(config, f"{c}.admin_units"))),
            user_agent=require(config, f"{c}.user_agent"),
            timeout_s=require(config, f"{c}.timeout_s"),
            max_workers=int(require(config, f"{c}.max_workers")),
            output_dir=require_path(config, f"{c}.output_dir"),
            outputs={
                k: require(config, f"{c}.outputs.{k}")
                for k in (
                    "admin1",
                    "zone_summary",
                    "national_ensemble",
                    "model_admin1",
                    "model_zone",
                    "zone_ensemble",
                )
            },
        )


def scalar(record: dict[str, float]) -> float:
    if len(record) != 1:
        raise ValueError(f"Expected one climatology value, got {record!r}")
    return float(next(iter(record.values())))


def _get(s: FetchSettings, url: str):
    request = urllib.request.Request(url, headers={"User-Agent": s.user_agent})
    return urllib.request.urlopen(request, timeout=s.timeout_s)


def _get_json(s: FetchSettings, url: str) -> dict:
    with _get(s, url) as response:
        payload = json.load(response)
    if payload.get("metadata", {}).get("status") != "success":
        raise RuntimeError(payload.get("metadata"))
    return payload


def fetch(s: FetchSettings, pathway: str) -> list[dict[str, object]]:
    payload = _get_json(s, API.format(period=s.period, pathway=pathway))

    rows = []
    for unit in s.units:
        code = unit.code
        rows.append(
            {
                "pathway": pathway,
                "code": code,
                "state": unit.state,
                "zone": unit.zone,
                "temperature_anomaly_c": scalar(payload["data"]["tas"][code]),
                "precipitation_anomaly_mm_year": scalar(payload["data"]["pr"][code]),
            }
        )
    return rows


def fetch_national(s: FetchSettings, pathway: str) -> list[dict[str, object]]:
    rows = []
    for percentile in s.percentiles:
        url = NATIONAL_API.format(
            period=s.period, pathway=pathway, percentile=percentile, country=s.iso3
        )
        payload = _get_json(s, url)
        rows.append(
            {
                "pathway": pathway,
                "percentile": percentile,
                "temperature_anomaly_c": scalar(payload["data"]["tas"][s.iso3]),
                "precipitation_anomaly_mm_year": scalar(payload["data"]["pr"][s.iso3]),
            }
        )
    return rows


def discover_model_runs(s: FetchSettings, variable: str) -> dict[str, set[tuple[str, str]]]:
    """Return the individual model/variant runs CCKP publishes by pathway."""
    with _get(s, S3_DATASETS.format(variable=variable)) as response:
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
            output[match.group("pathway")].add((match.group("model"), match.group("variant")))
    return output


def fetch_model_states(s: FetchSettings, task: tuple[str, str, str]) -> list[dict[str, object]]:
    pathway, model, variant = task
    url = MODEL_API.format(period=s.period, pathway=pathway, model=model, variant=variant)
    payload = _get_json(s, url)
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
            "code": unit.code,
            "state": unit.state,
            "zone": unit.zone,
            "temperature_anomaly_c": (
                scalar(temperature[unit.code]) if unit.code in temperature else None
            ),
            "precipitation_anomaly_mm_year": (
                scalar(precipitation[unit.code]) if unit.code in precipitation else None
            ),
        }
        for unit in s.units
    ]


def fetch_all_model_states(s: FetchSettings) -> list[dict[str, object]]:
    tas_runs = discover_model_runs(s, "tas")
    pr_runs = discover_model_runs(s, "pr")
    tasks = [
        (pathway, model, variant)
        for pathway in s.model_pathways
        for model, variant in sorted(tas_runs[pathway] | pr_runs[pathway])
    ]
    rows: list[dict[str, object]] = []
    with ThreadPoolExecutor(max_workers=s.max_workers) as executor:
        for result in executor.map(partial(fetch_model_states, s), tasks):
            rows.extend(result)
    return rows

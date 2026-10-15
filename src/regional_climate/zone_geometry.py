"""Draw the prototype's zone maps from real state boundaries (offline, no network).

States are joined to ``admin1_units`` on ISO 3166-2 code, projected equirectangularly (x scaled
by the cosine of the mid-latitude) and simplified one shared border at a time, so that
neighbouring states keep identical edges and no gaps or overlaps open between them. Borders
between states of different zones form the zone outline; borders with one state form the
national outline. The result is spliced into the prototype as ``NIGERIA_ZONE_MAP``.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path

from .admin_units import AdminUnit

Point = tuple[float, float]

JS_START = "const NIGERIA_ZONE_MAP={"
JS_END = "\n};\n"
WIDTH = 100.0


@dataclass(frozen=True)
class ZoneMap:
    view_box: tuple[float, float, float, float]
    states: list[tuple[str, str, str]]  # (state, zone, SVG path)
    zone_borders: str
    outline: str


def load_state_rings(path: Path, units: list[AdminUnit]) -> dict[str, list[list[Point]]]:
    """Outer rings per state, keyed by ``AdminUnit.state``; every unit must match one feature."""

    with path.open(encoding="utf-8") as fh:
        features = json.load(fh)["features"]
    by_iso = {u.iso3166_2: u for u in units}
    rings: dict[str, list[list[Point]]] = {}
    unmatched = []
    for feature in features:
        unit = by_iso.get(feature["properties"].get("shapeISO"))
        if unit is None:
            unmatched.append(feature["properties"].get("shapeName"))
            continue
        if unit.state in rings:
            raise ValueError(f"{path}: {unit.iso3166_2} appears more than once")
        geometry = feature["geometry"]
        polygons = (
            geometry["coordinates"]
            if geometry["type"] == "MultiPolygon"
            else [geometry["coordinates"]]
        )
        if any(len(polygon) > 1 for polygon in polygons):
            raise ValueError(f"{path}: {unit.state} has interior rings, which are not drawn")
        rings[unit.state] = [[(float(x), float(y)) for x, y in polygon[0]] for polygon in polygons]
    missing = [u.state for u in units if u.state not in rings]
    if unmatched or missing:
        raise ValueError(
            f"{path}: boundary features without an admin unit {unmatched}; "
            f"admin units without a boundary feature {missing}"
        )
    return rings


def _perpendicular(p: Point, a: Point, b: Point) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    if dx == 0 and dy == 0:
        return math.hypot(p[0] - a[0], p[1] - a[1])
    return abs(dy * p[0] - dx * p[1] + b[0] * a[1] - b[1] * a[0]) / math.hypot(dx, dy)


def douglas_peucker(points: list[Point], tolerance: float) -> list[Point]:
    """Simplify a polyline, keeping both end points (iterative, no recursion limit)."""

    if len(points) < 3:
        return list(points)
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        first, last = stack.pop()
        index, distance = 0, -1.0
        for i in range(first + 1, last):
            d = _perpendicular(points[i], points[first], points[last])
            if d > distance:
                index, distance = i, d
        if distance > tolerance:
            keep[index] = True
            stack += [(first, index), (index, last)]
    return [p for p, k in zip(points, keep, strict=True) if k]


def _open_ring(ring: list[Point]) -> list[Point]:
    return ring[:-1] if ring[0] == ring[-1] else list(ring)


def build_zone_map(
    rings: dict[str, list[list[Point]]], zone_of: dict[str, str], simplify_deg: float
) -> ZoneMap:
    """Project, simplify and assemble state, zone-border and outline paths."""

    # Which states each vertex and each edge belong to. The data must share border vertices
    # exactly: an edge is on the national border (one state) or between two states.
    vertex_states: dict[Point, set[str]] = defaultdict(set)
    edge_states: dict[frozenset[Point], set[str]] = defaultdict(set)
    for state, state_rings in rings.items():
        for ring in state_rings:
            pts = _open_ring(ring)
            for i, p in enumerate(pts):
                vertex_states[p].add(state)
                edge_states[frozenset((p, pts[(i + 1) % len(pts)]))].add(state)
    shared_badly = [sorted(s) for s in edge_states.values() if len(s) > 2]
    if shared_badly:
        raise ValueError(f"edges shared by more than two states: {shared_badly[:3]}")
    on_outline = {p for e, s in edge_states.items() if len(s) == 1 for p in e}

    def is_node(p: Point) -> bool:
        n = len(vertex_states[p])
        return n >= 3 or (n == 2 and p in on_outline)

    lons = [p[0] for p in vertex_states]
    lats = [p[1] for p in vertex_states]
    lon0, lat1 = min(lons), max(lats)
    x_scale = math.cos(math.radians((min(lats) + lat1) / 2))
    k = WIDTH / ((max(lons) - lon0) * x_scale)

    def project(p: Point) -> Point:
        return (round((p[0] - lon0) * x_scale * k, 2), round((lat1 - p[1]) * k, 2))

    tolerance = simplify_deg * k
    simplified: dict[tuple[Point, ...], list[Point]] = {}
    arc_states: dict[tuple[Point, ...], set[str]] = {}

    def simplify_arc(arc: list[Point]) -> list[Point]:
        """The same border is simplified once, whichever state walks it and in which direction."""
        key = min(tuple(arc), tuple(reversed(arc)))
        if key not in simplified:
            projected = [project(p) for p in key]
            if key[0] == key[-1]:  # a closed loop: split at its farthest point first
                far = max(range(len(key)), key=lambda i: math.dist(projected[0], projected[i]))
                out = douglas_peucker(projected[: far + 1], tolerance)[:-1]
                out += douglas_peucker(projected[far:], tolerance)
            else:
                out = douglas_peucker(projected, tolerance)
            simplified[key] = out
            arc_states[key] = edge_states[frozenset((key[0], key[1]))]
        out = simplified[key]
        return out if key == tuple(arc) else list(reversed(out))

    state_paths = []
    for state in sorted(rings, key=lambda s: (zone_of[s], s)):
        subpaths = []
        for ring in rings[state]:
            pts = _open_ring(ring)
            nodes = [i for i, p in enumerate(pts) if is_node(p)] or [0]
            pts = pts[nodes[0] :] + pts[: nodes[0]]
            nodes = [i - nodes[0] for i in nodes] + [len(pts)]
            pts = pts + [pts[0]]
            drawn: list[Point] = []
            for start, end in pairwise(nodes):
                drawn += simplify_arc(pts[start : end + 1])[:-1]
            if len(set(drawn)) < 3:
                raise ValueError(f"{state}: a ring collapsed under simplification")
            subpaths.append(_path(drawn, closed=True))
        state_paths.append((state, zone_of[state], "".join(subpaths)))

    zone_borders, outline = [], []
    for key, states in sorted(arc_states.items()):
        if len(states) == 1:
            outline.append(_path(simplified[key], closed=False))
        elif len({zone_of[s] for s in states}) == 2:
            zone_borders.append(_path(simplified[key], closed=False))

    height = round((lat1 - min(lats)) * k, 2)
    return ZoneMap((0.0, 0.0, WIDTH, height), state_paths, "".join(zone_borders), "".join(outline))


def _path(points: list[Point], closed: bool) -> str:
    text = "L".join(f"{x:g} {y:g}" for x, y in points)
    return "M" + text + ("Z" if closed else "")


def render_js(zone_map: ZoneMap, source_label: str) -> str:
    """The ``NIGERIA_ZONE_MAP`` statement spliced into the prototype."""

    rows = ",\n".join(
        f"    [{json.dumps(state)},{json.dumps(zone)},{json.dumps(d)}]"
        for state, zone, d in zone_map.states
    )
    view_box = ",".join(f"{v:g}" for v in zone_map.view_box)
    return (
        f"{JS_START}\n"
        f"  source:{json.dumps(source_label)},\n"
        f"  viewBox:[{view_box}],\n"
        f"  states:[\n{rows}\n  ],\n"
        f"  zoneBorders:{json.dumps(zone_map.zone_borders)},\n"
        f"  outline:{json.dumps(zone_map.outline)}"
        f"{JS_END}"
    )


def splice_zone_map(html: str, block: str) -> str:
    """Replace the prototype's ``NIGERIA_ZONE_MAP`` statement; a missing anchor raises."""

    if html.count(JS_START) != 1:
        raise ValueError(f"prototype must contain exactly one {JS_START!r}")
    start = html.index(JS_START)
    end = html.index(JS_END, start) + len(JS_END)
    return html[:start] + block + html[end:]

#!/usr/bin/env python3
"""Build data/cameras.json: a snapshot of LA-area cameras that the map loads instantly.

The free Overpass servers are often slow or busy, so the page starts from this
snapshot (refreshed daily by .github/workflows/update-data.yml) and only asks
Overpass live when you press "Refresh live" or browse outside the snapshot area.

    python3 scripts/build_snapshot.py

Sources:
  OpenStreetMap via Overpass (ODbL): ALPR and speed camera nodes
  LADOT Speed Safety System (public ArcGIS layers): camera sites and corridors
"""
import json
import math
import os
import sys
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cameras_to_kml import build_query, overpass  # noqa: E402

# south,west,north,east: Los Angeles County's populated area
BBOX = (33.70, -118.95, 34.45, -117.65)
ARCGIS = "https://services.arcgis.com/G3nmNsarwQblLhip/arcgis/rest/services"
LADOT_CAMERAS = ARCGIS + "/CameraSystemLabels_view/FeatureServer/0"
LADOT_CORRIDORS = ARCGIS + "/ApprovedLocations_04012026_view/FeatureServer/0"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "cameras.json")

# OSM tags worth showing in the map's popups; everything else is dropped to keep the file small
KEEP_TAGS = {
    "manufacturer", "brand", "operator", "direction", "camera:direction", "camera:mount",
    "surveillance:zone", "maxspeed", "name", "ref", "description", "note", "check_date",
}


def get_geojson(layer):
    url = layer + "/query?where=1%3D1&outFields=*&outSR=4326&f=geojson"
    req = urllib.request.Request(url, headers={"User-Agent": "la-camera-watch"})
    with urllib.request.urlopen(req, timeout=60) as res:
        return json.load(res)["features"]


def rings(geom):
    if geom["type"] == "Polygon":
        return [geom["coordinates"][0]]
    return [poly[0] for poly in geom["coordinates"]]


def inside(pt, ring):
    x, y, hit = pt[0], pt[1], False
    for (x1, y1), (x2, y2) in zip(ring, ring[-1:] + ring[:-1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            hit = not hit
    return hit


def meters(a, b):
    """Rough distance in meters between two [lon, lat] points (fine at city scale)."""
    dx = (a[0] - b[0]) * 111320 * math.cos(math.radians(a[1]))
    dy = (a[1] - b[1]) * 110540
    return math.hypot(dx, dy)


def corridor_for(pt, corridors):
    """The corridor polygon a camera sits in, else the nearest one within 250 m."""
    best, best_d = None, 250
    for c in corridors:
        if any(inside(pt, r) for r in c["rings"]):
            return c
        d = min(meters(pt, v) for r in c["rings"] for v in r)
        if d < best_d:
            best, best_d = c, d
    return best


def round_ring(ring):
    return [[round(x, 5), round(y, 5)] for x, y in ring]


def main():
    s, w, n, e = BBOX
    print("Overpass: cameras in {},{},{},{}…".format(s, w, n, e))
    osm = []
    for el in overpass(build_query("{},{},{},{}".format(s, w, n, e))):
        tags = el.get("tags", {})
        kind = "alpr" if tags.get("surveillance:type") == "ALPR" else "speed"
        osm.append([el["id"], round(el["lat"], 6), round(el["lon"], 6), kind,
                    {k: v for k, v in tags.items() if k in KEEP_TAGS}])

    print("LADOT: camera sites and corridors…")
    corridors = []
    for i, f in enumerate(get_geojson(LADOT_CORRIDORS)):
        p = f["properties"]
        corridors.append({
            "id": i,
            "street": p.get("StreetName"), "from": p.get("XStreet1"), "to": p.get("XStreet2"),
            "limit": p.get("speed_limi"), "school": p.get("SchoolNearby") == "Yes",
            "rings": [round_ring(r) for r in rings(f["geometry"])],
        })
    ladot = []
    for f in get_geojson(LADOT_CAMERAS):
        pt = f["geometry"]["coordinates"]
        c = corridor_for(pt, corridors)
        ladot.append({
            "id": f["properties"].get("ID"), "lat": round(pt[1], 6), "lon": round(pt[0], 6),
            "status": f["properties"].get("System"),
            "corridor": c["id"] if c else None,
        })

    snapshot = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bbox": BBOX,
        "osm": sorted(osm),
        "ladot": ladot,
        "corridors": corridors,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, separators=(",", ":"), ensure_ascii=False)
    n_alpr = sum(1 for c in osm if c[3] == "alpr")
    print("Wrote {}: {} ALPR, {} speed (OSM), {} LADOT sites, {} corridors ({:.0f} KB)".format(
        os.path.normpath(OUT), n_alpr, len(osm) - n_alpr, len(ladot), len(corridors),
        os.path.getsize(OUT) / 1024))


if __name__ == "__main__":
    main()

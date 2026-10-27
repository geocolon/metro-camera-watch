#!/usr/bin/env python3
"""Build per-region camera snapshots that the map loads instantly.

The free Overpass servers are often slow or busy, so the page starts from these
snapshots (refreshed daily by .github/workflows/update-data.yml) and only asks
Overpass live when you press "Refresh live data" or browse outside every region.

    python3 scripts/build_snapshot.py            # every region
    python3 scripts/build_snapshot.py ny         # just one

Writes data/<region>.json for each region and data/regions.json, the list the
page reads first. A region whose download fails keeps its previous file.

Sources:
  OpenStreetMap via Overpass (ODbL): ALPR and speed camera nodes
  LADOT Speed Safety System (public ArcGIS layers): LA camera sites and corridors
  (New York City doesn't publish its speed camera locations.)
"""
import json
import math
import os
import sys
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cameras_to_kml import build_query, overpass  # noqa: E402

# bbox is south, west, north, east
REGIONS = {
    "la": {"name": "Los Angeles area", "bbox": (33.70, -118.95, 34.45, -117.65), "ladot": True},
    # NYC's five boroughs, Yonkers and lower Westchester, Long Island to Montauk, and nearby New Jersey
    "ny": {"name": "New York City area", "bbox": (40.45, -74.35, 41.25, -71.80)},
}
ARCGIS = "https://services.arcgis.com/G3nmNsarwQblLhip/arcgis/rest/services"
LADOT_CAMERAS = ARCGIS + "/CameraSystemLabels_view/FeatureServer/0"
LADOT_CORRIDORS = ARCGIS + "/ApprovedLocations_04012026_view/FeatureServer/0"
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")

# OSM tags worth showing in the map's popups; everything else is dropped to keep the files small
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


def osm_cameras(bbox):
    osm = []
    for el in overpass(build_query("{},{},{},{}".format(*bbox))):
        tags = el.get("tags", {})
        kind = "alpr" if tags.get("surveillance:type") == "ALPR" else "speed"
        osm.append([el["id"], round(el["lat"], 6), round(el["lon"], 6), kind,
                    {k: v for k, v in tags.items() if k in KEEP_TAGS}])
    return sorted(osm)


def ladot_cameras():
    corridors = []
    for i, f in enumerate(get_geojson(LADOT_CORRIDORS)):
        p = f["properties"]
        corridors.append({
            "id": i,
            "street": p.get("StreetName"), "from": p.get("XStreet1"), "to": p.get("XStreet2"),
            "limit": p.get("speed_limi"), "school": p.get("SchoolNearby") == "Yes",
            "rings": [round_ring(r) for r in rings(f["geometry"])],
        })
    city = []
    for f in get_geojson(LADOT_CAMERAS):
        pt = f["geometry"]["coordinates"]
        c = corridor_for(pt, corridors)
        city.append({
            "id": f["properties"].get("ID"), "lat": round(pt[1], 6), "lon": round(pt[0], 6),
            "status": f["properties"].get("System"),
            "corridor": c["id"] if c else None,
        })
    return city, corridors


def build(region_id):
    region = REGIONS[region_id]
    print("{}: asking Overpass for cameras…".format(region["name"]))
    snapshot = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bbox": region["bbox"],
        "osm": osm_cameras(region["bbox"]),
        "city": [],
        "corridors": [],
    }
    if region.get("ladot"):
        print("{}: LADOT camera sites and corridors…".format(region["name"]))
        snapshot["city"], snapshot["corridors"] = ladot_cameras()
    path = os.path.join(DATA, region_id + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, separators=(",", ":"), ensure_ascii=False)
    n_alpr = sum(1 for c in snapshot["osm"] if c[3] == "alpr")
    print("Wrote {}: {} ALPR, {} speed (OSM), {} city sites ({:.0f} KB)".format(
        os.path.normpath(path), n_alpr, len(snapshot["osm"]) - n_alpr, len(snapshot["city"]),
        os.path.getsize(path) / 1024))


def write_index():
    """data/regions.json: every region that has a snapshot file, with its counts."""
    index = []
    for region_id, region in REGIONS.items():
        path = os.path.join(DATA, region_id + ".json")
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            snap = json.load(f)
        n_alpr = sum(1 for c in snap["osm"] if c[3] == "alpr")
        index.append({
            "id": region_id, "name": region["name"], "bbox": region["bbox"],
            "file": "data/{}.json".format(region_id), "generated": snap["generated"],
            "counts": {"alpr": n_alpr, "speed": len(snap["osm"]) - n_alpr, "city": len(snap["city"])},
        })
    with open(os.path.join(DATA, "regions.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, indent=1)


def main():
    wanted = sys.argv[1:] or list(REGIONS)
    unknown = [r for r in wanted if r not in REGIONS]
    if unknown:
        sys.exit("Unknown region(s): {}. Choose from: {}".format(", ".join(unknown), ", ".join(REGIONS)))
    os.makedirs(DATA, exist_ok=True)
    failed = []
    for region_id in wanted:
        try:
            build(region_id)
        except Exception as e:  # keep the previous file and carry on with the other regions
            print("{}: failed ({}); keeping the previous snapshot".format(region_id, e), file=sys.stderr)
            failed.append(region_id)
    write_index()
    if len(failed) == len(wanted):
        sys.exit(1)


if __name__ == "__main__":
    main()

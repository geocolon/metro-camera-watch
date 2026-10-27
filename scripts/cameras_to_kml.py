#!/usr/bin/env python3
"""Export ALPR (Flock etc.) and speed cameras from OpenStreetMap to KML.

Import the resulting file into Google My Maps (Create map -> Import) to get
two layers: license plate readers and speed cameras.

    python3 scripts/cameras_to_kml.py                 # Los Angeles area
    python3 scripts/cameras_to_kml.py --bbox 33.9,-118.5,34.2,-118.1 -o la.kml

Data (c) OpenStreetMap contributors, ODbL. Camera locations are largely
contributed through DeFlock (https://deflock.me).
"""
import argparse
import json
import sys
import urllib.parse
import urllib.request
from xml.sax.saxutils import escape

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
# south,west,north,east (Overpass order): roughly the City of Los Angeles
LA_BBOX = "33.70,-118.67,34.34,-118.15"


def build_query(bbox):
    return """[out:json][timeout:120];
(
  node["surveillance:type"="ALPR"]({bbox});
  node["highway"="speed_camera"]({bbox});
);
out body;""".format(bbox=bbox)


def overpass(query):
    data = urllib.parse.urlencode({"data": query}).encode()
    last_err = None
    for url in OVERPASS_ENDPOINTS:
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": "la-camera-watch"})
            with urllib.request.urlopen(req, timeout=180) as res:
                result = json.load(res)
            # A busy server can answer 200 with a "remark" (timeout, out of memory) and no data.
            if result.get("remark") and not result.get("elements"):
                raise RuntimeError(result["remark"])
            return result.get("elements", [])
        except Exception as e:  # try the next mirror
            last_err = e
            print("  {} failed: {}".format(url, e), file=sys.stderr)
    raise last_err


def placemark(el, title):
    tags = el.get("tags", {})
    rows = "<br>".join("{} = {}".format(k, v) for k, v in sorted(tags.items()))
    link = "https://www.openstreetmap.org/node/{}".format(el["id"])
    desc = "{}<br><br>{}".format(rows, link)
    return """    <Placemark>
      <name>{}</name>
      <description><![CDATA[{}]]></description>
      <Point><coordinates>{},{},0</coordinates></Point>
    </Placemark>""".format(escape(title), desc.replace("]]>", "]]&gt;"), el["lon"], el["lat"])


def to_kml(elements):
    alpr, speed = [], []
    for el in elements:
        tags = el.get("tags", {})
        if tags.get("surveillance:type") == "ALPR":
            maker = tags.get("manufacturer") or tags.get("brand") or "maker unknown"
            alpr.append(placemark(el, "License plate reader ({})".format(maker)))
        else:
            speed.append(placemark(el, "Speed camera"))

    def folder(name, marks):
        return "  <Folder>\n    <name>{}</name>\n{}\n  </Folder>".format(name, "\n".join(marks))

    kml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
  <name>LA Camera Watch</name>
  <description>Data (c) OpenStreetMap contributors, ODbL</description>
{}
{}
</Document>
</kml>
""".format(folder("ALPR / Flock", alpr), folder("Speed cameras", speed))
    return kml, len(alpr), len(speed)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--bbox", default=LA_BBOX, help="south,west,north,east (default: Los Angeles)")
    p.add_argument("-o", "--output", default="cameras.kml", help="output file (default: cameras.kml)")
    args = p.parse_args()

    print("Asking OpenStreetMap for cameras in {}…".format(args.bbox))
    kml, n_alpr, n_speed = to_kml(overpass(build_query(args.bbox)))
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(kml)
    print("Wrote {}: {} ALPR, {} speed cameras".format(args.output, n_alpr, n_speed))


if __name__ == "__main__":
    main()

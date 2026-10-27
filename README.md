# LA Camera Watch

A live map of automated license plate readers (ALPR, such as Flock Safety) and speed cameras in Los Angeles.

**Live map:** https://geocolon.github.io/la-camera-watch/

## How it works

- `index.html` is a single static page built on [Leaflet](https://leafletjs.com). It has no backend.
- Each time you load the page or press **Refresh this area**, your browser asks the [Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API) for OpenStreetMap camera nodes inside the visible map:
  - `surveillance:type=ALPR` for license plate readers
  - `highway=speed_camera` for speed cameras
- It also loads LADOT's official speed safety camera sites from the city's public ArcGIS map ([program page](https://ladot.lacity.gov/speed-safety-system)).
- Where a camera has a `direction` tag, a short line shows which way it points.

## Run locally

OSM's tile servers block pages opened straight from disk, so serve the folder:

```bash
python3 -m http.server 8000
```

Then open http://localhost:8000/.

## Export to Google My Maps

`scripts/cameras_to_kml.py` writes a KML file with two layers (ALPR and speed cameras). It uses only the Python standard library.

```bash
python3 scripts/cameras_to_kml.py
```

Pass `--bbox south,west,north,east` for another area or `-o file.kml` to rename the output. In [Google My Maps](https://www.google.com/mymaps), choose **Create a new map → Import** and select `cameras.kml`.

## Add a missing camera

Camera locations come from volunteers. If you spot one that isn't on the map, add it with [DeFlock](https://deflock.me) or edit OpenStreetMap directly.

## Credits and license

- Map data © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), available under the Open Database License (ODbL).
- Much of the ALPR data is contributed through [DeFlock](https://deflock.me).
- Official speed camera sites: [LADOT Speed Safety System](https://ladot.lacity.gov/speed-safety-system).
- Map library: [Leaflet](https://leafletjs.com) (BSD-2-Clause).

The code in this repository is released under the [MIT License](LICENSE). The camera data is not covered by that license; it stays under the ODbL.

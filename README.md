# Metro Camera Watch - CA, NY

A map of automated license plate readers (ALPR, such as Flock Safety) and speed cameras, with spoken alerts while you drive. It has saved data for the Los Angeles and New York City areas, and fetches live data anywhere else.

**Live map:** https://geocolon.github.io/metro-camera-watch/

## Features

- **Camera icons you can tell apart without color.** Each type has its own shape and a camera symbol: plate readers are squares, speed cameras are circles, and official city speed cameras are diamonds (solid when live, outline while under construction). Colors come from the Okabe-Ito palette, which stays distinct with common color blindness. A small pointer shows which way a camera faces when that's known.
- **Address search.** Type an address or place, like Google Maps, and pick from the suggestions (arrow keys and Enter work too). A pin drops there, the status says how many cameras are within half a mile, and the camera list is sorted by distance from that address. Search uses [Photon](https://photon.komoot.io), OpenStreetMap's address search.
- **Drive mode.** It follows your location and shows your speed, and inside LA's speed camera corridors it shows the posted limit. As you approach a camera, it plays a chime, says something like "Speed camera ahead, 950 feet", vibrates (Android) and shows a large banner. It only warns about cameras in your direction of travel, and gives more warning at higher speeds. It keeps the screen on while it runs.
- **Phone-first layout.** There's a Google Maps-style bottom sheet and large touch targets. You can add it to your home screen to use it like an app (Share → Add to Home Screen on iPhone).
- **Dark mode** follows your system setting.

## Accessibility

- Every camera is a keyboard-focusable button with a spoken name, and **Cameras in view** is a text list of the nearest cameras with distance and direction. Choosing one opens its details and moves focus there.
- A skip link goes straight to the list. Focus outlines are always visible, and touch targets are at least 44 px.
- Status updates and drive alerts are announced to screen readers through live regions.
- Meaning never depends on color alone: shapes, symbols and text labels carry it too. There's also a **Bigger camera icons** setting.
- Animations are turned off when your system asks for reduced motion.

## How it works

- `index.html` is a single static page built on [Leaflet](https://leafletjs.com) and [Leaflet.markercluster](https://github.com/Leaflet/Leaflet.markercluster). It has no backend.
- It starts from saved regional snapshots built by `scripts/build_snapshot.py`. Plate readers come from [DeFlock's published OpenStreetMap extract](https://deflock.me), a static file that loads even when Overpass is overloaded; speed cameras come from Overpass. `data/regions.json` lists them, and each region's file (`data/la.json`, `data/ny.json`) loads only when you look at or search in that area. A GitHub Action (`.github/workflows/update-data.yml`) refreshes them every day. The free Overpass servers are often slow, so the snapshots keep the map fast and reliable.
  - **Los Angeles area:** OpenStreetMap cameras plus LADOT's official speed camera sites.
  - **New York City area** (the five boroughs, Yonkers and lower Westchester, Long Island and nearby New Jersey): OpenStreetMap cameras. NYC doesn't publish its speed camera locations, so only cameras that volunteers have mapped appear.
  - To add a region, add it to `REGIONS` in `scripts/build_snapshot.py`.
- **Refresh live data** asks the [Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API) for the latest OpenStreetMap edits in view:
  - `surveillance:type=ALPR` for license plate readers
  - `highway=speed_camera` for speed cameras
  
  Browsing or driving outside every saved region fetches live data automatically.
- City camera sites and corridors (street, cross streets, speed limit) come from LADOT's public ArcGIS layers ([program page](https://ladot.lacity.gov/speed-safety-system)).

### Drive mode limits

Web pages can't run in the background. Keep the page open and on screen in a phone mount; locking the phone or switching apps pauses alerts. Set things up before you drive, and always follow posted limits, because the camera data is incomplete.

## Run locally

OSM's tile servers block pages opened straight from disk, so serve the folder:

```bash
python3 -m http.server 8000
```

Then open http://localhost:8000/. Location and drive mode need `localhost` or HTTPS.

## Scripts

Both use only the Python standard library (3.7+).

```bash
python3 scripts/build_snapshot.py
```

Rebuilds every region's snapshot. Name regions to rebuild only those, for example `python3 scripts/build_snapshot.py ny`.

```bash
python3 scripts/cameras_to_kml.py
```

Writes `cameras.kml` for [Google My Maps](https://www.google.com/mymaps): choose **Create a new map → Import**. Pass `--bbox south,west,north,east` for another area.

## Add a missing camera

Camera locations come from volunteers. If you spot one that isn't on the map, add it with [DeFlock](https://deflock.me) or edit OpenStreetMap directly.

## Credits and license

- Map data and tiles © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), available under the Open Database License (ODbL).
- Much of the ALPR data is contributed through [DeFlock](https://deflock.me).
- Official speed camera sites: [LADOT Speed Safety System](https://ladot.lacity.gov/speed-safety-system).
- Map libraries: [Leaflet](https://leafletjs.com) (BSD-2-Clause) and Leaflet.markercluster (MIT).

The code in this repository is released under the [MIT License](LICENSE). The camera data is not covered by that license; it stays under the ODbL.

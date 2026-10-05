# Treasury Building–Business Mapper

A QGIS plugin for mapping building footprints and geotagging business
permit records. It is intended for an LGU Treasury workflow where business
records need a reliable spatial link to a building or parcel.

Version 0.2.3 provides the installable plugin shell and map-first working UI. It can
search compatible loaded layers, zoom to results, add a business record, place
or move its point, intersect it with a building, and validate core attributes.

## Intended workflow

1. Load a GeoPackage containing building polygons and business records.
2. Search by parcel, building, owner, business, or permit number.
3. Zoom to a result.
4. Click **Add permit**, place its point, and then enter its details.
5. Automatically associate the point with the building it intersects.
6. Review unmatched, ambiguous, and duplicate records.
7. Save the result as a GeoPackage.

See [Architecture](docs/architecture.md), [UI specification](docs/ui.md), and
[implementation plan](docs/implementation-plan.md).

## Data fields

The `buildings` polygon layer uses `building_id`, `parcel_id`,
`building_name`, `owner_name`, and `height_m`.

The `businesses` point layer uses `business_id`, `building_id`,
`business_name`, `owner_name`, `permit_no`, and `match_status`.

IDs are text values so leading zeroes and local numbering formats are retained.

## Developer setup

The core code has no third-party dependency. Run its tests with:

```bash
python3 -m unittest discover -s tests/unit -v
```

On a machine with QGIS and PyQGIS installed, run the complete suite with:

```bash
make test
```

This includes headless QGIS tests for layer schemas, spatial association,
record persistence, ribbon switching, and active-mode search.

QGIS supplies PyQGIS and Qt; they should not be installed from PyPI. The plugin
will import Qt through `qgis.PyQt` for compatibility with QGIS 3.x.

## Build the installable ZIP

From the repository root, run:

```bash
make package
```

This creates `dist/treasury_mapper-0.2.3.zip` with the required top-level
`treasury_mapper` directory.

## QGIS installation

The release artifact will be a ZIP whose top-level directory is
`treasury_mapper`. In QGIS:

1. Open **Plugins > Manage and Install Plugins**.
2. Choose **Install from ZIP**.
3. Select the release ZIP and confirm installation.
4. Enable **Treasury Building–Business Mapper** in the Installed tab.
5. Open it from **Plugins > Treasury Mapper**.

To try it without preparing data, click **Create empty demo layers**. This also
adds an online Google Hybrid XYZ basemap when available. Choose **Buildings**,
click **Add building**, draw its corners, and right-click to finish. Then choose
**Permits**, click **Add permit**, click the permit location, and enter its
details. Each creation command commits its new feature and ends the edit mode
that it started. Demo layers are held in memory; use QGIS **Export > Save
Features As** to save them to a GeoPackage.

For development, copy or symlink `treasury_mapper/` into the active QGIS
profile's `python/plugins/` directory, restart QGIS, then enable the plugin.
Typical profile locations are:

- Linux: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
- Windows: `%APPDATA%\\QGIS\\QGIS3\\profiles\\default\\python\\plugins\\`
- macOS: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`

## Using existing layers

Load a polygon layer containing the documented building fields and a point
layer containing the business fields. Choose both layers in the dock. The dock
shows missing fields and enables its actions once the schemas are valid.

## Compatibility target

The minimum declared target is QGIS 3.0. Development should also be checked on
the current QGIS LTR. APIs unavailable in 3.0 need a compatible path or an
explicit release-note limitation.

## Privacy

Only synthetic sample records belong in this repository. Real taxpayer,
business-owner, and permit data must stay in the LGU-controlled environment.

# Architecture

## Shape of the application

The plugin is a thin QGIS interface around testable business rules.

```text
QGIS dock widget and map tool
            |
            v
Application services (search, place, associate, validate, export)
            |
            v
Ports for feature and layer access
            |
            v
PyQGIS / GeoPackage adapters
```

The source tree should converge on:

```text
treasury_mapper/
  __init__.py              QGIS class factory
  metadata.txt             plugin metadata; qgisMinimumVersion=3.0
  plugin.py                action and dock-widget lifecycle
  core/                    plain Python rules (no QGIS imports)
  adapters/                layer, GeoPackage, and spatial index access
  ui/                      dock, forms, and map tools
tests/
  unit/                    runs with ordinary Python
  qgis/                    runs in a QGIS test environment
sample_data/               synthetic data and generator only
```

## Services

`SearchService` returns ranked results. Initial ranking is exact ID, prefix,
then substring. Empty queries return no results.

`AssociationService` receives stable IDs of polygons intersecting the point.
Zero candidates produces `unmatched`, one produces `matched`, and more than one
produces `multiple`. The UI asks the user to resolve a multiple match.

`ValidationService` reports missing and duplicate IDs, invalid height,
business links that refer to no building, and geometry-based match states.

`GeoPackageRepository` creates the schema, reads records, applies edits, and
exports layers. Business rules remain unaware of PyQGIS types.

## Spatial matching

The initial relationship is point-in-polygon intersection. The adapter first
transforms the point into the building layer CRS. A `QgsSpatialIndex` narrows
candidate polygons, followed by an exact geometry intersection test.

Boundary points can intersect adjacent buildings. This yields `multiple`; the
plugin highlights candidates and asks the user to choose. A chosen override
stores the selected `building_id`, while validation can still report ambiguity.

## Editing and persistence

New permit creation is geometry-first: capture a point, collect attributes,
then save point geometry, `building_id`, and `match_status` together. Building
creation starts polygon capture and commits after the normal QGIS attribute
form accepts the feature. Edit sessions started by the plugin end after a
successful creation. On failure the edit is rolled back and a message is shown.

Demo setup may add a Google Hybrid XYZ raster at the bottom of the layer tree.
This optional online layer is visual context only and is never a data source for
matching or persistence.

The GeoPackage is the system of record for the prototype. Export preserves
field names, CRS, geometry types, and stable IDs.

## Compatibility

QGIS 3.0 uses Python 3 and PyQt5, but its bundled Python is older than current
LTR versions. Avoid modern-only syntax, import Qt from `qgis.PyQt`, and
feature-detect newer QGIS APIs. Core tests remain runnable outside QGIS.

## Future boundary

Django/PostGIS synchronization and GeoServer publishing can be later adapters.
They are not part of this prototype.

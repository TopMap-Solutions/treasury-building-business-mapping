# Treasury Building–Business Mapping

## Goal

Build a small QGIS plugin for LGU Treasury staff to locate parcels/buildings,
place business-permit points, and associate each business with a building.
The prototype must work with sample data and store its results in a GeoPackage.

## Supported environment

- QGIS 3.0 or newer, with priority given to the current QGIS LTR
- Python and PyQGIS supplied by QGIS
- PyQt5 through `qgis.PyQt`; do not import a system PyQt installation
- GeoPackage as the storage and exchange format

Keep syntax compatible with the Python version bundled with the oldest supported
QGIS release. Do not add Django, PostGIS, GeoServer, or network services unless
the user explicitly expands the scope.

## Prototype workflow

1. Open or create the project GeoPackage.
2. Load the `buildings` polygon layer and `businesses` point layer.
3. Search by parcel ID, building name, owner, business ID, business name, or
   business owner.
4. Select a result and zoom the map to it.
5. Select an existing business record or create one, then place its point.
6. Find the building polygon intersecting the point and save its `building_id`.
7. Flag points with no building match, multiple matches, missing IDs, or
   duplicate IDs.
8. Save/export the validated layers to a GeoPackage.

New records use a geometry-first interaction. **Add building** starts polygon
capture; after the polygon is finished, QGIS collects its attributes and the
plugin commits the new feature. **Add permit** starts point capture; after the
map click, the plugin collects permit attributes and saves geometry, link, and
status together. A command-status label must always explain what map action is
active. Edit mode started by the plugin must end after successful creation.

## Required data model

### `buildings` polygon layer

| Field | Type | Requirement |
| --- | --- | --- |
| `building_id` | text | required, unique, stable |
| `parcel_id` | text | searchable |
| `building_name` | text | searchable, optional |
| `owner_name` | text | searchable, optional |
| `height_m` | decimal | optional, non-negative |

### `businesses` point layer

| Field | Type | Requirement |
| --- | --- | --- |
| `business_id` | text | required, unique, stable |
| `building_id` | text | nullable until matched |
| `business_name` | text | required, searchable |
| `owner_name` | text | searchable, optional |
| `permit_no` | text | optional, searchable |
| `match_status` | text | `matched`, `unmatched`, or `multiple` |

Use text identifiers because LGU identifiers may contain leading zeroes,
letters, or punctuation. Geometry is the source of the building match;
`building_id` is the stored link used for reporting and validation.

## Architecture rules

- Put business rules, search normalization, matching decisions, and validation
  in `treasury_mapper/core/`. This code must not import QGIS or Qt.
- Put GeoPackage and layer access in `treasury_mapper/adapters/`.
- Put QGIS map tools, dock widgets, and dialogs in `treasury_mapper/ui/`.
- Keep the plugin entry point thin. UI handlers call core services rather than
  containing matching or validation rules.
- Use QGIS edit commands/transactions so edits can be undone when supported.
- Do not create an empty permit record before its map point is chosen.
- Only auto-commit an edit session that the plugin started. Preserve edit
  sessions that were already active when a plugin command began.
- Never use a display label or internal QGIS feature ID as a permanent link.
- Reproject geometries to a common CRS before spatial matching.
- If a point intersects more than one polygon, do not choose silently. Mark it
  `multiple` and let the user choose a building.

See `docs/architecture.md` and `docs/ui.md` before implementing a workflow.

## Development workflow

- Preserve unrelated user changes in the working tree.
- Add or update tests for core behavior. Core tests run without QGIS.
- Put QGIS-dependent integration and dock tests in `tests/qgis/`. They must use
  synthetic in-memory layers and the offscreen Qt platform.
- Use only synthetic records. Never commit live taxpayer, owner, permit, or
  credential data.
- Demo setup adds Google Hybrid as an XYZ basemap when it is available. Treat
  it as an online convenience layer; core drawing must still work if it fails.
- Package `treasury_mapper/icon.svg` and use it for plugin and dock branding.
- Run `make test` before packaging. It is the required full test gate and runs
  both the core and PyQGIS suites.
- Run `make test-core` for the QGIS-independent unit suite alone.
- Run `make test-qgis` for layer, geometry, persistence, and dock UI tests.
- Do not create a release ZIP when any test is failing.
- Verify metadata and imports on the oldest practical supported QGIS version,
  and manually smoke-test on the current QGIS LTR before release.

## Definition of done

- The plugin installs from a ZIP or local plugin folder.
- Sample building and business layers load from a GeoPackage.
- Search finds either record type and zooms to a selection.
- A business point can be placed or moved and associated with a building.
- Unmatched, multiply matched, missing-ID, and duplicate-ID records are shown.
- Results save to a GeoPackage and reopen without losing links.
- `make test` passes and README installation steps have been verified.

# Implementation plan

## Milestone 1: repository and rules

- Define field names, record models, match states, validation, and search.
- Add QGIS-independent unit tests.
- Document architecture, UI, compatibility, and installation.

Exit: core tests pass without QGIS and the data model is stable.

## Milestone 2: installable plugin shell

- Add QGIS plugin metadata and class factory.
- Add the dock widget, menu/toolbar action, and layer selectors.
- Package a ZIP QGIS can install.

Exit: the plugin installs on the target QGIS LTR and opens its dock.

## Milestone 3: GeoPackage and search

- Create/open required layers and verify fields.
- Add synthetic sample data.
- Search either layer, select results, and zoom to geometry.

Exit: every documented field is searchable and results zoom reliably.

## Milestone 4: geotag and associate

- Add the point placement/move map tool.
- Use a spatial index and exact intersection to find buildings.
- Handle zero, one, and multiple matches and update atomically.

Exit: a business can be placed, linked, saved, reopened, and moved.

## Milestone 5: validation and export

- Implement issue list and zoom-to-issue.
- Validate identifiers, attributes, stored links, and spatial matches.
- Export both layers to a selected GeoPackage.

Exit: all prototype workflow steps work with sample data.

## Milestone 6: compatibility and release

- Run core and QGIS integration tests.
- Smoke-test on current QGIS LTR and the oldest practical supported build.
- Verify installation instructions and create the installable ZIP.


# User interface specification

## Main dock

Use one narrow QGIS dock, inspired by a simple parcel-search interface. Two
exclusive ribbon buttons switch the dock between Buildings and Permits. The
single layer selector and all commands follow the active ribbon.

```text
+----------------------------------+
| Treasury Mapper                  |
| [ Buildings ] [ Permits ]        |
| [ active layer               v ] |
| [ parcel, business, owner... ] 🔍|
|----------------------------------|
| Results                          |
| BLDG  01-0042  Mercado Building |
| BIZ   BP-1021  Juan's Pharmacy  |
|----------------------------------|
| Selected business               |
| BP-1021 | Juan's Pharmacy       |
| Owner: Juan Dela Cruz            |
| Building: B-0042 (matched)       |
|                                  |
| [Zoom] [Add permit]              |
| [Place / Move Point]             |
| [Create empty demo layers]       |
+----------------------------------+
```

Search runs after a short typing delay or when Enter is pressed. Building mode
searches only the selected polygon layer and Permit mode searches only the
selected point layer. Double-clicking zooms to a result. The add button reads
**Add building** or **Add permit** according to the selected ribbon. Selecting
a permit shows the point-placement controls. Validation is intentionally not
shown in this basic dock.

## Point placement

1. Select or create a business record.
2. For a new permit, **Add permit** immediately activates a crosshair map tool.
3. Click the visible building footprint, then enter the permit details.
4. The command-status bar reports the active drawing instruction and outcome.
5. A single match is saved. No match is saved as `unmatched`. Multiple matches
   open a chooser showing building ID, parcel, name, and owner.
6. Geometry, attributes, building link, and status are committed together, and
   the plugin's edit mode ends.
7. **Place / Move Point** remains available for an existing selected permit.
8. Escape cancels without creating or changing a record.

For a new building, **Add building** starts QGIS polygon capture before the
attribute form. Right-click ends the polygon, QGIS requests the fields, and the
plugin commits the completed feature and ends the edit mode it started.

Keep the map visible throughout. Avoid multi-page wizards.

## Validation view

The issue table contains severity, layer, record ID, and message. Clicking an
issue selects and zooms to the feature when geometry exists. Initial checks:

- missing or duplicate `building_id` or `business_id`;
- missing business name or negative building height;
- business point outside all buildings or intersecting multiple buildings;
- stored `building_id` missing from the building layer;
- stored link disagreeing with an unambiguous spatial match.

Use the QGIS message bar for feedback. Disable actions requiring a selected
business, and always show the selected record's current match status.

"""Main Treasury Mapper dock widget."""

import os

from qgis.PyQt.QtCore import QTimer, Qt
from qgis.PyQt.QtGui import QPixmap
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDockWidget,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from qgis.core import Qgis, QgsMapLayer, QgsProject, QgsWkbTypes

from ..adapters.qgis_layers import (
    BUILDING_FIELDS,
    BUSINESS_FIELDS,
    add_business_at_point,
    add_google_hybrid_layer,
    building_records,
    business_records,
    create_demo_layers,
    feature_by_value,
    missing_fields,
    point_in_buildings,
    update_business_point,
    zoom_to_feature,
)
from ..core.association import associate
from ..core.search import search_records
from .map_tools import BusinessPointTool


class TreasuryMapperDock(QDockWidget):
    def __init__(self, iface):
        QDockWidget.__init__(self, "Treasury Mapper", iface.mainWindow())
        self.setObjectName("TreasuryMapperDock")
        self.iface = iface
        self.selected_result = None
        self.selected_business_fid = None
        self.mode = "building"
        self.building_layer_id = None
        self.business_layer_id = None
        self.previous_map_tool = None
        self.creating_business = False
        self.pending_building_layer = None
        self.stop_building_edit_after_add = False
        self.point_tool = BusinessPointTool(
            iface.mapCanvas(), self._point_clicked, self._cancel_point_tool
        )
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(250)
        self.timer.timeout.connect(self.run_search)
        self._build_ui()
        QgsProject.instance().layersAdded.connect(self.refresh_layers)
        QgsProject.instance().layersRemoved.connect(self.refresh_layers)
        self.refresh_layers()

    def _build_ui(self):
        body = QWidget(self)
        layout = QVBoxLayout(body)

        brand = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(
            QPixmap(os.path.join(os.path.dirname(os.path.dirname(__file__)), "icon.svg"))
            .scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        title = QLabel("<b>Treasury Mapper</b>")
        brand.addWidget(logo)
        brand.addWidget(title)
        brand.addStretch(1)
        layout.addLayout(brand)

        ribbon = QHBoxLayout()
        ribbon.setSpacing(0)
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        self.building_mode_button = self._ribbon_button("Buildings")
        self.permit_mode_button = self._ribbon_button("Permits")
        self.building_mode_button.setChecked(True)
        self.mode_group.addButton(self.building_mode_button)
        self.mode_group.addButton(self.permit_mode_button)
        self.building_mode_button.clicked.connect(lambda: self.switch_mode("building"))
        self.permit_mode_button.clicked.connect(lambda: self.switch_mode("business"))
        ribbon.addWidget(self.building_mode_button)
        ribbon.addWidget(self.permit_mode_button)
        layout.addLayout(ribbon)

        self.layer_combo = QComboBox()
        self.layer_combo.currentIndexChanged.connect(self._layer_changed)
        layout.addWidget(self.layer_combo)

        self.schema_label = QLabel("Choose the two layers.")
        self.schema_label.setWordWrap(True)
        layout.addWidget(self.schema_label)

        self.command_label = QLabel("Ready")
        self.command_label.setWordWrap(True)
        self.command_label.setStyleSheet(
            "QLabel { padding: 6px; border-left: 4px solid #DD8637; "
            "background: palette(alternate-base); font-weight: bold; }"
        )
        layout.addWidget(self.command_label)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Parcel, building, owner, business, permit...")
        self.search_edit.textChanged.connect(lambda _text: self.timer.start())
        self.search_edit.returnPressed.connect(self.run_search)
        layout.addWidget(self.search_edit)

        self.results = QListWidget()
        self.results.setSelectionMode(QAbstractItemView.SingleSelection)
        self.results.itemSelectionChanged.connect(self._result_selected)
        self.results.itemDoubleClicked.connect(lambda _item: self.zoom_selected())
        layout.addWidget(self.results, 1)

        actions = QHBoxLayout()
        self.zoom_button = QPushButton("Zoom")
        self.zoom_button.clicked.connect(self.zoom_selected)
        self.add_button = QPushButton("Add business")
        self.add_button.clicked.connect(self.add_active_record)
        actions.addWidget(self.zoom_button)
        actions.addWidget(self.add_button)
        layout.addLayout(actions)

        self.selection_label = QLabel("No business selected")
        self.selection_label.setWordWrap(True)
        layout.addWidget(self.selection_label)

        self.place_button = QPushButton("Place / move selected business point")
        self.place_button.clicked.connect(self.activate_point_tool)
        layout.addWidget(self.place_button)

        self.demo_button = QPushButton("Create empty demo layers")
        self.demo_button.clicked.connect(self.create_demo)
        layout.addWidget(self.demo_button)

        self.setWidget(body)
        self._update_actions()

    def _ribbon_button(self, text):
        button = QToolButton()
        button.setText(text)
        button.setCheckable(True)
        button.setToolButtonStyle(Qt.ToolButtonTextOnly)
        button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        button.setMinimumHeight(34)
        button.setStyleSheet(
            "QToolButton { padding: 7px; border: 1px solid palette(mid); "
            "background: palette(button); font-weight: bold; }"
            "QToolButton:checked { background: palette(highlight); "
            "color: palette(highlighted-text); }"
        )
        return button

    def _message(self, text, level=Qgis.Info, duration=5):
        self.iface.messageBar().pushMessage("Treasury Mapper", text, level=level, duration=duration)

    def _layer(self, layer_id):
        return QgsProject.instance().mapLayer(layer_id) if layer_id else None

    def building_layer(self):
        return self._layer(self.building_layer_id)

    def business_layer(self):
        return self._layer(self.business_layer_id)

    def active_layer(self):
        return self.building_layer() if self.mode == "building" else self.business_layer()

    def refresh_layers(self, *_args):
        valid_ids = set(QgsProject.instance().mapLayers().keys())
        if self.building_layer_id not in valid_ids:
            self.building_layer_id = self._preferred_layer_id(QgsWkbTypes.PolygonGeometry, "buildings")
        if self.business_layer_id not in valid_ids:
            self.business_layer_id = self._preferred_layer_id(QgsWkbTypes.PointGeometry, "businesses")
        self._populate_layer_combo()
        self._layers_changed()

    def _preferred_layer_id(self, geometry_type, preferred_name):
        fallback = None
        for layer in QgsProject.instance().mapLayers().values():
            if layer.type() != QgsMapLayer.VectorLayer or layer.geometryType() != geometry_type:
                continue
            if fallback is None:
                fallback = layer.id()
            if layer.name().casefold() == preferred_name:
                return layer.id()
        return fallback

    def _populate_layer_combo(self):
        geometry_type = (
            QgsWkbTypes.PolygonGeometry if self.mode == "building" else QgsWkbTypes.PointGeometry
        )
        selected_id = self.building_layer_id if self.mode == "building" else self.business_layer_id
        placeholder = "Select building layer..." if self.mode == "building" else "Select permit layer..."
        self.layer_combo.blockSignals(True)
        self.layer_combo.clear()
        self.layer_combo.addItem(placeholder, None)
        for layer in QgsProject.instance().mapLayers().values():
            if layer.type() == QgsMapLayer.VectorLayer and layer.geometryType() == geometry_type:
                self.layer_combo.addItem(layer.name(), layer.id())
        index = self.layer_combo.findData(selected_id)
        self.layer_combo.setCurrentIndex(index if index >= 0 else 0)
        self.layer_combo.blockSignals(False)

    def _layer_changed(self, *_args):
        if self.mode == "building":
            self.building_layer_id = self.layer_combo.currentData()
        else:
            self.business_layer_id = self.layer_combo.currentData()
        self._layers_changed()

    def switch_mode(self, mode):
        self.mode = mode
        self.selected_result = None
        self.selected_business_fid = None
        self.results.clear()
        self.search_edit.clear()
        self._populate_layer_combo()
        self._layers_changed()

    def _layers_changed(self, *_args):
        layer = self.active_layer()
        required = BUILDING_FIELDS if self.mode == "building" else BUSINESS_FIELDS
        label = "building" if self.mode == "building" else "permit"
        missing = missing_fields(layer, required) if layer else []
        if missing:
            self.schema_label.setText("Missing fields: " + ", ".join(missing))
        elif layer:
            self.schema_label.setText("{0} layer ready. Search or add a record.".format(label.title()))
        else:
            self.schema_label.setText("Choose a {0} layer.".format(label))
        self.search_edit.setPlaceholderText(
            "Parcel, building, or owner..." if self.mode == "building"
            else "Business, owner, or permit..."
        )
        self.add_button.setText("Add building" if self.mode == "building" else "Add permit")
        permit_mode = self.mode == "business"
        self.selection_label.setVisible(permit_mode)
        self.place_button.setVisible(permit_mode)
        self.run_search()
        self._update_actions()

    def active_layer_is_ready(self):
        layer = self.active_layer()
        fields = BUILDING_FIELDS if self.mode == "building" else BUSINESS_FIELDS
        return bool(layer and not missing_fields(layer, fields))

    def placement_is_ready(self):
        buildings = self.building_layer()
        businesses = self.business_layer()
        return bool(buildings and businesses and not missing_fields(buildings, BUILDING_FIELDS)
                    and not missing_fields(businesses, BUSINESS_FIELDS))

    def create_demo(self):
        authid = self.iface.mapCanvas().mapSettings().destinationCrs().authid() or "EPSG:4326"
        buildings, businesses = create_demo_layers(authid)
        basemap = add_google_hybrid_layer()
        self.building_layer_id = buildings.id()
        self.business_layer_id = businesses.id()
        self.refresh_layers()
        if basemap is None:
            self._message("Demo layers created, but Google Hybrid could not be loaded.", Qgis.Warning)
        else:
            self._message("Demo layers and Google Hybrid were added. Start by drawing a building.")

    def run_search(self):
        self.results.clear()
        if not self.active_layer_is_ready():
            return
        query = self.search_edit.text()
        buildings = building_records(self.building_layer()) if self.mode == "building" else []
        businesses = business_records(self.business_layer()) if self.mode == "business" else []
        for result in search_records(query, buildings, businesses)[:100]:
            prefix = "BLDG" if result.record_type == "building" else "BIZ"
            item = QListWidgetItem("{0}  {1}  {2}".format(prefix, result.record_id, result.label))
            item.setData(Qt.UserRole, (result.record_type, result.record_id))
            self.results.addItem(item)

    def _result_selected(self):
        items = self.results.selectedItems()
        self.selected_result = items[0].data(Qt.UserRole) if items else None
        if self.selected_result and self.selected_result[0] == "business":
            feature = feature_by_value(self.business_layer(), "business_id", self.selected_result[1])
            self.selected_business_fid = feature.id() if feature is not None else None
            self._show_business(feature)
        elif self.selected_result:
            self.selected_business_fid = None
            self.selection_label.setText("No business selected")
        self._update_actions()

    def _show_business(self, feature):
        if feature is None:
            self.selection_label.setText("No business selected")
            return
        name = feature["business_name"]
        building = feature["building_id"] or "not linked"
        status = feature["match_status"] or "not placed"
        self.selection_label.setText(
            "Selected: {0}\nBuilding: {1} ({2})".format(name, building, status)
        )

    def zoom_selected(self):
        if not self.selected_result:
            return
        record_type, record_id = self.selected_result
        layer = self.building_layer() if record_type == "building" else self.business_layer()
        field_name = "building_id" if record_type == "building" else "business_id"
        feature = feature_by_value(layer, field_name, record_id)
        if feature is None or not zoom_to_feature(self.iface, layer, feature):
            self._message("The selected record has no geometry yet.", Qgis.Warning)

    def start_business_drawing(self):
        if not self.placement_is_ready():
            self._message("Choose valid building and permit layers first.", Qgis.Warning)
            return
        if self.business_layer().isEditable():
            self._message("Save or cancel current permit-layer edits first.", Qgis.Warning)
            return
        self.creating_business = True
        self.selected_business_fid = None
        self.previous_map_tool = self.iface.mapCanvas().mapTool()
        self.iface.mapCanvas().setMapTool(self.point_tool)
        self.command_label.setText("DRAW PERMIT: Click its location on the map. Press Esc to cancel.")
        self.add_button.setText("Drawing permit point…")
        self._message("Click the permit location. Its details will be requested after the point is placed.")

    def add_active_record(self):
        if self.mode == "business":
            self.start_business_drawing()
            return
        layer = self.building_layer()
        if not self.active_layer_is_ready():
            return
        self.iface.setActiveLayer(layer)
        already_editable = layer.isEditable()
        if not already_editable and not layer.startEditing():
            QMessageBox.critical(self, "Could not edit layer", "The building layer could not enter edit mode.")
            return
        if self.pending_building_layer is not None:
            try:
                self.pending_building_layer.featureAdded.disconnect(self._building_feature_added)
            except (TypeError, RuntimeError):
                pass
        self.pending_building_layer = layer
        self.stop_building_edit_after_add = not already_editable
        layer.featureAdded.connect(self._building_feature_added)
        self.iface.actionAddFeature().trigger()
        self.command_label.setText("DRAW BUILDING: Click each corner, then right-click to finish.")
        self._message("Click around the building, then right-click to finish and enter its details.")

    def _building_feature_added(self, _feature_id):
        layer = self.pending_building_layer
        if layer is None:
            return
        try:
            layer.featureAdded.disconnect(self._building_feature_added)
        except (TypeError, RuntimeError):
            pass
        self.pending_building_layer = None
        QTimer.singleShot(0, lambda: self._finish_building_add(layer))

    def _finish_building_add(self, layer):
        if self.stop_building_edit_after_add and layer.isEditable():
            if not layer.commitChanges():
                QMessageBox.critical(
                    self, "Could not save building", "; ".join(layer.commitErrors())
                )
                return
        self.stop_building_edit_after_add = False
        self.command_label.setText("Building saved. Choose Add building to draw another.")
        self.run_search()
        self._message("Building saved and drawing finished.")

    def activate_point_tool(self):
        if self.selected_business_fid is None or not self.placement_is_ready():
            return
        self.previous_map_tool = self.iface.mapCanvas().mapTool()
        self.iface.mapCanvas().setMapTool(self.point_tool)
        self._message("Click the map to place the selected business point. Press Esc to cancel.")

    def _point_clicked(self, point):
        if self.creating_business:
            self._create_business_at_point(point)
            return
        if self.selected_business_fid is None:
            return
        candidates = point_in_buildings(
            point,
            self.iface.mapCanvas().mapSettings().destinationCrs(),
            self.building_layer(),
        )
        result = associate(candidates)
        if result.match_status == "multiple":
            chosen, ok = self._choose_building(result.candidates)
            if not ok:
                return
            result = associate([chosen])
        try:
            update_business_point(
                self.business_layer(),
                self.selected_business_fid,
                point,
                self.iface.mapCanvas().mapSettings().destinationCrs(),
                result,
            )
        except Exception as error:
            QMessageBox.critical(self, "Could not place point", str(error))
            return
        if self.previous_map_tool is not None:
            self.iface.mapCanvas().setMapTool(self.previous_map_tool)
        self.business_layer().triggerRepaint()
        feature = next(
            self.business_layer().getFeatures(), None
        ) if self.selected_business_fid is None else self.business_layer().getFeature(self.selected_business_fid)
        self._show_business(feature)
        if result.match_status == "matched":
            self._message("Business point linked to building {0}.".format(result.building_id))
        else:
            self._message("Point saved, but it does not intersect a building.", Qgis.Warning)

    def _create_business_at_point(self, point):
        candidates = point_in_buildings(
            point,
            self.iface.mapCanvas().mapSettings().destinationCrs(),
            self.building_layer(),
        )
        result = associate(candidates)
        if result.match_status == "multiple":
            chosen, ok = self._choose_building(result.candidates)
            if not ok:
                self._finish_point_drawing("Permit drawing cancelled.")
                return
            result = associate([chosen])
        dialog = BusinessDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            self._finish_point_drawing("Permit drawing cancelled.")
            return
        values = dialog.values()
        if feature_by_value(self.business_layer(), "business_id", values["business_id"]):
            QMessageBox.warning(self, "Duplicate ID", "That business ID already exists.")
            self._finish_point_drawing("Permit was not created.")
            return
        try:
            self.selected_business_fid = add_business_at_point(
                self.business_layer(),
                values,
                point,
                self.iface.mapCanvas().mapSettings().destinationCrs(),
                result,
            )
        except Exception as error:
            QMessageBox.critical(self, "Could not add permit", str(error))
            self._finish_point_drawing("Permit was not created.")
            return
        self.selected_result = ("business", values["business_id"])
        feature = feature_by_value(self.business_layer(), "business_id", values["business_id"])
        self._show_business(feature)
        self.business_layer().triggerRepaint()
        status = "Permit saved and linked to {0}.".format(result.building_id)
        if result.match_status != "matched":
            status = "Permit saved as unmatched."
        self._finish_point_drawing(status)
        self.run_search()
        self._update_actions()

    def _finish_point_drawing(self, status):
        self.creating_business = False
        if self.previous_map_tool is not None:
            self.iface.mapCanvas().setMapTool(self.previous_map_tool)
        self.command_label.setText(status)
        self.add_button.setText("Add permit")
        self._message(status)

    def _cancel_point_tool(self):
        if self.creating_business:
            self._finish_point_drawing("Permit drawing cancelled.")
            return
        if self.iface.mapCanvas().mapTool() == self.point_tool and self.previous_map_tool:
            self.iface.mapCanvas().setMapTool(self.previous_map_tool)
        self.command_label.setText("Point move cancelled.")

    def _choose_building(self, candidates):
        combo = QComboBox()
        for building_id in candidates:
            feature = feature_by_value(self.building_layer(), "building_id", building_id)
            label = building_id
            if feature is not None:
                label += " — " + str(feature["building_name"] or feature["parcel_id"] or "")
            combo.addItem(label, building_id)
        box = QMessageBox(self)
        box.setWindowTitle("Choose building")
        box.setText("This point touches more than one building. Choose the correct one.")
        box.layout().addWidget(combo, 1, 1)
        box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        accepted = box.exec_() == QMessageBox.Ok
        return combo.currentData(), accepted

    def _update_actions(self):
        ready = self.active_layer_is_ready()
        self.search_edit.setEnabled(ready)
        self.add_button.setEnabled(ready)
        self.zoom_button.setEnabled(bool(self.selected_result))
        self.place_button.setEnabled(
            self.mode == "business" and self.placement_is_ready()
            and self.selected_business_fid is not None
        )

    def cleanup(self):
        try:
            QgsProject.instance().layersAdded.disconnect(self.refresh_layers)
            QgsProject.instance().layersRemoved.disconnect(self.refresh_layers)
        except (TypeError, RuntimeError):
            pass
        if self.iface.mapCanvas().mapTool() == self.point_tool and self.previous_map_tool:
            self.iface.mapCanvas().setMapTool(self.previous_map_tool)
        if self.pending_building_layer is not None:
            try:
                self.pending_building_layer.featureAdded.disconnect(self._building_feature_added)
            except (TypeError, RuntimeError):
                pass


class BusinessDialog(QDialog):
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.setWindowTitle("Add business permit")
        layout = QFormLayout(self)
        self.business_id = QLineEdit()
        self.business_name = QLineEdit()
        self.owner_name = QLineEdit()
        self.permit_no = QLineEdit()
        layout.addRow("Business ID *", self.business_id)
        layout.addRow("Business name *", self.business_name)
        layout.addRow("Owner", self.owner_name)
        layout.addRow("Permit number", self.permit_no)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _accept_if_valid(self):
        if not self.business_id.text().strip() or not self.business_name.text().strip():
            QMessageBox.warning(self, "Required fields", "Business ID and business name are required.")
            return
        self.accept()

    def values(self):
        return {
            "business_id": self.business_id.text().strip(),
            "building_id": None,
            "business_name": self.business_name.text().strip(),
            "owner_name": self.owner_name.text().strip(),
            "permit_no": self.permit_no.text().strip(),
            "match_status": "unmatched",
        }

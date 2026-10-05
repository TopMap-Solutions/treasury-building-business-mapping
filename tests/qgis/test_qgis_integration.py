"""Integration tests that run against the PyQGIS installation."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qgis.PyQt.QtWidgets import QAction, QMainWindow
from qgis.core import (
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsRectangle,
)
from qgis.gui import QgsMapCanvas, QgsMessageBar

from treasury_mapper.adapters.qgis_layers import (
    BUILDING_FIELDS,
    BUSINESS_FIELDS,
    add_business,
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
from treasury_mapper.core.association import associate
from treasury_mapper.plugin import TreasuryMapperPlugin
from treasury_mapper.ui.dock import TreasuryMapperDock


QGIS_APP = None


def setUpModule():
    global QGIS_APP
    QGIS_APP = QgsApplication([], True)
    QGIS_APP.initQgis()


def tearDownModule():
    QgsProject.instance().clear()
    QGIS_APP.exitQgis()


class FakeIface(object):
    def __init__(self):
        self.window = QMainWindow()
        self.canvas = QgsMapCanvas()
        self.bar = QgsMessageBar()
        self.active_layer = None
        self.add_feature_action = QAction("Add feature", self.window)
        self.menu_actions = []
        self.toolbar_actions = []
        self.docks = []

    def mainWindow(self):
        return self.window

    def mapCanvas(self):
        return self.canvas

    def messageBar(self):
        return self.bar

    def setActiveLayer(self, layer):
        self.active_layer = layer
        return True

    def actionAddFeature(self):
        return self.add_feature_action

    def addPluginToMenu(self, _menu, action):
        self.menu_actions.append(action)

    def removePluginMenu(self, _menu, action):
        if action in self.menu_actions:
            self.menu_actions.remove(action)

    def addToolBarIcon(self, action):
        self.toolbar_actions.append(action)

    def removeToolBarIcon(self, action):
        if action in self.toolbar_actions:
            self.toolbar_actions.remove(action)

    def addDockWidget(self, _area, dock):
        self.docks.append(dock)

    def removeDockWidget(self, dock):
        if dock in self.docks:
            self.docks.remove(dock)


def add_test_building(layer, building_id="B-001", wkt=None):
    feature = QgsFeature(layer.fields())
    feature["building_id"] = building_id
    feature["parcel_id"] = "P-001"
    feature["building_name"] = "Test Building"
    feature["owner_name"] = "Test Owner"
    feature["height_m"] = 5.0
    feature.setGeometry(
        QgsGeometry.fromWkt(wkt or "POLYGON((0 0, 0 1, 1 1, 1 0, 0 0))")
    )
    if layer.isEditable():
        success = layer.addFeature(feature)
    else:
        success, _features = layer.dataProvider().addFeatures([feature])
    if not success:
        raise AssertionError("Could not create test building")
    layer.updateExtents()


class QgisLayerIntegrationTest(unittest.TestCase):
    def setUp(self):
        QgsProject.instance().clear()
        self.buildings, self.businesses = create_demo_layers("EPSG:4326")

    def tearDown(self):
        QgsProject.instance().clear()

    def test_demo_layers_have_expected_schemas(self):
        self.assertEqual([], missing_fields(self.buildings, BUILDING_FIELDS))
        self.assertEqual([], missing_fields(self.businesses, BUSINESS_FIELDS))
        self.assertTrue(self.buildings.isValid())
        self.assertTrue(self.businesses.isValid())

    def test_records_are_converted_to_core_models(self):
        add_test_building(self.buildings)
        add_business(
            self.businesses,
            {
                "business_id": "BP-001",
                "building_id": None,
                "business_name": "Test Shop",
                "owner_name": "Test Owner",
                "permit_no": "2026-001",
                "match_status": "unmatched",
            },
        )
        self.assertEqual("B-001", building_records(self.buildings)[0].building_id)
        self.assertEqual("Test Shop", business_records(self.businesses)[0].business_name)

    def test_point_intersection_and_business_update_are_persisted(self):
        add_test_building(self.buildings)
        feature_id = add_business(
            self.businesses,
            {
                "business_id": "BP-001",
                "building_id": None,
                "business_name": "Test Shop",
                "owner_name": "Test Owner",
                "permit_no": "2026-001",
                "match_status": "unmatched",
            },
        )
        point = QgsPointXY(0.5, 0.5)
        candidates = point_in_buildings(point, self.buildings.crs(), self.buildings)
        result = associate(candidates)
        update_business_point(self.businesses, feature_id, point, self.businesses.crs(), result)
        saved = feature_by_value(self.businesses, "business_id", "BP-001")
        self.assertEqual("B-001", saved["building_id"])
        self.assertEqual("matched", saved["match_status"])
        self.assertFalse(saved.geometry().isEmpty())

    def test_intersection_reports_zero_and_multiple_candidates(self):
        add_test_building(self.buildings, "B-001")
        add_test_building(self.buildings, "B-002")
        inside = point_in_buildings(QgsPointXY(0.5, 0.5), self.buildings.crs(), self.buildings)
        outside = point_in_buildings(QgsPointXY(5, 5), self.buildings.crs(), self.buildings)
        self.assertEqual({"B-001", "B-002"}, set(inside))
        self.assertEqual([], outside)
        self.assertEqual("multiple", associate(inside).match_status)
        self.assertEqual("unmatched", associate(outside).match_status)

    def test_new_permit_is_created_with_geometry_and_editing_stops(self):
        add_test_building(self.buildings)
        values = {
            "business_id": "BP-002",
            "building_id": None,
            "business_name": "Map First Shop",
            "owner_name": "Test Owner",
            "permit_no": "2026-002",
            "match_status": "unmatched",
        }
        point = QgsPointXY(0.5, 0.5)
        result = associate(point_in_buildings(point, self.buildings.crs(), self.buildings))

        add_business_at_point(self.businesses, values, point, self.businesses.crs(), result)

        saved = feature_by_value(self.businesses, "business_id", "BP-002")
        self.assertFalse(saved.geometry().isEmpty())
        self.assertEqual("B-001", saved["building_id"])
        self.assertFalse(self.businesses.isEditable())

    def test_google_hybrid_is_added_only_once(self):
        first = add_google_hybrid_layer()
        second = add_google_hybrid_layer()
        self.assertIsNotNone(first)
        self.assertEqual(first.id(), second.id())
        names = [layer.name() for layer in QgsProject.instance().mapLayers().values()]
        self.assertEqual(1, names.count("Google Hybrid"))

    def test_permit_zoom_uses_local_scale_instead_of_point_extent(self):
        feature_id = add_business_at_point(
            self.businesses,
            {
                "business_id": "BP-ZOOM",
                "building_id": None,
                "business_name": "Zoom Test",
                "owner_name": "Owner",
                "permit_no": "2026-ZOOM",
                "match_status": "unmatched",
            },
            QgsPointXY(125.6, 7.1),
            self.businesses.crs(),
            associate([]),
        )
        feature = self.businesses.getFeature(feature_id)
        iface = FakeIface()
        iface.mapCanvas().setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
        iface.mapCanvas().setExtent(QgsRectangle(124, 6, 127, 9))

        self.assertTrue(zoom_to_feature(iface, self.businesses, feature))

        center = iface.mapCanvas().center()
        self.assertAlmostEqual(125.6, center.x(), places=5)
        self.assertAlmostEqual(7.1, center.y(), places=5)
        self.assertAlmostEqual(500, iface.mapCanvas().scale(), delta=5)
        self.assertEqual([feature_id], self.businesses.selectedFeatureIds())


class DockUiIntegrationTest(unittest.TestCase):
    def setUp(self):
        QgsProject.instance().clear()
        self.iface = FakeIface()
        self.dock = TreasuryMapperDock(self.iface)
        self.buildings, self.businesses = create_demo_layers("EPSG:4326")
        self.dock.building_layer_id = self.buildings.id()
        self.dock.business_layer_id = self.businesses.id()
        self.dock.refresh_layers()

    def tearDown(self):
        self.dock.cleanup()
        self.dock.deleteLater()
        QgsProject.instance().clear()

    def test_ribbons_switch_layer_and_primary_action(self):
        self.assertTrue(self.dock.building_mode_button.isChecked())
        self.assertEqual("buildings", self.dock.layer_combo.currentText())
        self.assertEqual("Add building", self.dock.add_button.text())
        self.assertTrue(self.dock.add_button.isEnabled())

        self.dock.permit_mode_button.click()

        self.assertTrue(self.dock.permit_mode_button.isChecked())
        self.assertEqual("businesses", self.dock.layer_combo.currentText())
        self.assertEqual("Add permit", self.dock.add_button.text())

    def test_search_is_scoped_to_active_ribbon(self):
        add_test_building(self.buildings)
        add_business(
            self.businesses,
            {
                "business_id": "BP-001",
                "building_id": None,
                "business_name": "Test Shop",
                "owner_name": "Owner",
                "permit_no": "2026-001",
                "match_status": "unmatched",
            },
        )
        self.dock.search_edit.setText("Test")
        self.dock.run_search()
        self.assertEqual(1, self.dock.results.count())
        self.assertTrue(self.dock.results.item(0).text().startswith("BLDG"))

        self.dock.permit_mode_button.click()
        self.dock.search_edit.setText("Test")
        self.dock.run_search()
        self.assertEqual(1, self.dock.results.count())
        self.assertTrue(self.dock.results.item(0).text().startswith("BIZ"))

    def test_add_building_activates_editing_and_qgis_digitizing(self):
        triggered = []
        self.iface.add_feature_action.triggered.connect(lambda: triggered.append(True))

        self.dock.add_button.click()

        self.assertIs(self.buildings, self.iface.active_layer)
        self.assertTrue(self.buildings.isEditable())
        self.assertEqual([True], triggered)

        add_test_building(self.buildings)
        QgsApplication.processEvents()

        self.assertFalse(self.buildings.isEditable())
        self.assertIn("Building saved", self.dock.command_label.text())

    def test_add_permit_starts_with_map_drawing(self):
        self.dock.permit_mode_button.click()

        self.dock.add_button.click()

        self.assertTrue(self.dock.creating_business)
        self.assertIs(self.dock.point_tool, self.iface.mapCanvas().mapTool())
        self.assertEqual(0, self.businesses.featureCount())
        self.assertIn("DRAW PERMIT", self.dock.command_label.text())


class PluginLifecycleIntegrationTest(unittest.TestCase):
    def setUp(self):
        QgsProject.instance().clear()
        self.iface = FakeIface()

    def tearDown(self):
        QgsProject.instance().clear()

    def test_plugin_registers_opens_and_unloads_cleanly(self):
        plugin = TreasuryMapperPlugin(self.iface)
        plugin.initGui()
        self.assertEqual(1, len(self.iface.menu_actions))
        self.assertEqual(1, len(self.iface.toolbar_actions))

        plugin.show_dock()
        self.assertEqual(1, len(self.iface.docks))
        self.assertIsNotNone(plugin.dock)

        plugin.unload()
        self.assertEqual([], self.iface.menu_actions)
        self.assertEqual([], self.iface.toolbar_actions)
        self.assertEqual([], self.iface.docks)
        self.assertIsNone(plugin.dock)


if __name__ == "__main__":
    unittest.main()

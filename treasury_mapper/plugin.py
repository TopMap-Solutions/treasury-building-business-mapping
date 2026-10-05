"""QGIS plugin lifecycle."""

import os

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from .ui.dock import TreasuryMapperDock


class TreasuryMapperPlugin(object):
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dock = None

    def initGui(self):
        icon = QIcon(os.path.join(os.path.dirname(__file__), "icon.svg"))
        self.action = QAction(icon, "Treasury Mapper", self.iface.mainWindow())
        self.action.setObjectName("treasuryMapperAction")
        self.action.triggered.connect(self.show_dock)
        self.iface.addPluginToMenu("&Treasury Mapper", self.action)
        self.iface.addToolBarIcon(self.action)

    def show_dock(self):
        if self.dock is None:
            self.dock = TreasuryMapperDock(self.iface)
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock)
        self.dock.refresh_layers()
        self.dock.show()
        self.dock.raise_()

    def unload(self):
        if self.action is not None:
            self.iface.removePluginMenu("&Treasury Mapper", self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action.deleteLater()
            self.action = None
        if self.dock is not None:
            self.dock.cleanup()
            self.iface.removeDockWidget(self.dock)
            self.dock.deleteLater()
            self.dock = None

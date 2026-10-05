"""Map tool used to place a business point."""

from qgis.PyQt.QtCore import Qt
from qgis.gui import QgsMapToolEmitPoint


class BusinessPointTool(QgsMapToolEmitPoint):
    def __init__(self, canvas, callback, cancel_callback=None):
        QgsMapToolEmitPoint.__init__(self, canvas)
        self.callback = callback
        self.cancel_callback = cancel_callback
        self.setCursor(Qt.CrossCursor)

    def canvasReleaseEvent(self, event):
        point = self.toMapCoordinates(event.pos())
        self.callback(point)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and self.cancel_callback is not None:
            self.cancel_callback()
            return
        QgsMapToolEmitPoint.keyPressEvent(self, event)

"""QGIS plugin entry point."""


def classFactory(iface):
    """Create the plugin instance. QGIS calls this function."""
    from .plugin import TreasuryMapperPlugin

    return TreasuryMapperPlugin(iface)

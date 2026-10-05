"""QGIS layer helpers used by the dock widget."""

from qgis.core import (
    QgsCoordinateTransform,
    QgsFeature,
    QgsFeatureRequest,
    QgsGeometry,
    QgsProject,
    QgsRasterLayer,
    QgsRectangle,
    QgsSpatialIndex,
    QgsVectorLayer,
    QgsWkbTypes,
)

from ..core.models import Building, Business

BUILDING_FIELDS = (
    "building_id",
    "parcel_id",
    "building_name",
    "owner_name",
    "height_m",
)
BUSINESS_FIELDS = (
    "business_id",
    "building_id",
    "business_name",
    "owner_name",
    "permit_no",
    "match_status",
)

PERMIT_ZOOM_SCALE = 500


def field_value(feature, name, default=None):
    index = feature.fields().indexFromName(name)
    if index < 0:
        return default
    value = feature[index]
    if value is None:
        return default
    return value


def missing_fields(layer, required):
    names = set(field.name() for field in layer.fields())
    return [name for name in required if name not in names]


def building_records(layer):
    records = []
    for feature in layer.getFeatures():
        height = field_value(feature, "height_m")
        try:
            height = float(height) if height not in (None, "") else None
        except (TypeError, ValueError):
            height = -1
        records.append(
            Building(
                str(field_value(feature, "building_id", "") or ""),
                str(field_value(feature, "parcel_id", "") or ""),
                str(field_value(feature, "building_name", "") or ""),
                str(field_value(feature, "owner_name", "") or ""),
                height,
            )
        )
    return records


def business_records(layer):
    records = []
    for feature in layer.getFeatures():
        records.append(
            Business(
                str(field_value(feature, "business_id", "") or ""),
                str(field_value(feature, "building_id", "") or ""),
                str(field_value(feature, "business_name", "") or ""),
                str(field_value(feature, "owner_name", "") or ""),
                str(field_value(feature, "permit_no", "") or ""),
                str(field_value(feature, "match_status", "") or ""),
            )
        )
    return records


def feature_by_value(layer, field_name, value):
    index = layer.fields().indexFromName(field_name)
    if index < 0:
        return None
    request = QgsFeatureRequest().setFilterExpression(
        '"{0}" = {1}'.format(field_name, quoted_value(value))
    )
    return next(layer.getFeatures(request), None)


def quoted_value(value):
    return "'{}'".format(str(value).replace("'", "''"))


def zoom_to_feature(iface, layer, feature):
    geometry = feature.geometry()
    if geometry is None or geometry.isEmpty():
        return False
    display_geometry = QgsGeometry(geometry)
    if layer.crs() != iface.mapCanvas().mapSettings().destinationCrs():
        transform = QgsCoordinateTransform(
            layer.crs(),
            iface.mapCanvas().mapSettings().destinationCrs(),
            QgsProject.instance(),
        )
        display_geometry.transform(transform)
    canvas = iface.mapCanvas()
    if (
        QgsWkbTypes.geometryType(display_geometry.wkbType())
        == QgsWkbTypes.PointGeometry
    ):
        if display_geometry.isMultipart():
            points = display_geometry.asMultiPoint()
            if not points:
                return False
            center = points[0]
        else:
            center = display_geometry.asPoint()
        canvas.setCenter(center)
        canvas.zoomScale(PERMIT_ZOOM_SCALE)
    else:
        extent = display_geometry.boundingBox()
        extent.scale(1.5)
        canvas.setExtent(extent)
    layer.selectByIds([feature.id()])
    if hasattr(canvas, "flashFeatureIds"):
        canvas.flashFeatureIds(layer, [feature.id()])
    canvas.refresh()
    return True


def point_in_buildings(point, point_crs, building_layer):
    """Return IDs of building geometries intersecting a map point."""
    if point_crs != building_layer.crs():
        transform = QgsCoordinateTransform(
            point_crs, building_layer.crs(), QgsProject.instance()
        )
        point = transform.transform(point)
    point_geometry = QgsGeometry.fromPointXY(point)
    index = QgsSpatialIndex(building_layer.getFeatures())
    candidates = index.intersects(
        QgsRectangle(point.x(), point.y(), point.x(), point.y())
    )
    matches = []
    for feature in building_layer.getFeatures(
        QgsFeatureRequest().setFilterFids(candidates)
    ):
        if feature.geometry().intersects(point_geometry):
            value = field_value(feature, "building_id")
            if value:
                matches.append(str(value))
    return matches


def update_business_point(layer, feature_id, point, point_crs, association):
    """Atomically update point geometry and association attributes."""
    if point_crs != layer.crs():
        transform = QgsCoordinateTransform(
            point_crs, layer.crs(), QgsProject.instance()
        )
        point = transform.transform(point)
    started = not layer.isEditable()
    if started and not layer.startEditing():
        raise RuntimeError("The business layer could not enter edit mode.")
    layer.beginEditCommand("Place business permit point")
    try:
        if not layer.changeGeometry(feature_id, QgsGeometry.fromPointXY(point)):
            raise RuntimeError("The point geometry could not be updated.")
        building_index = layer.fields().indexFromName("building_id")
        status_index = layer.fields().indexFromName("match_status")
        if not layer.changeAttributeValue(
            feature_id, building_index, association.building_id
        ):
            raise RuntimeError("The building link could not be updated.")
        if not layer.changeAttributeValue(
            feature_id, status_index, association.match_status
        ):
            raise RuntimeError("The match status could not be updated.")
        layer.endEditCommand()
        if started and not layer.commitChanges():
            raise RuntimeError(
                "The business edit could not be saved: "
                + "; ".join(layer.commitErrors())
            )
    except Exception:
        layer.destroyEditCommand()
        if started:
            layer.rollBack()
        raise


def add_business(layer, values):
    started = not layer.isEditable()
    if started and not layer.startEditing():
        raise RuntimeError("The business layer could not enter edit mode.")
    feature = QgsFeature(layer.fields())
    for name, value in values.items():
        index = layer.fields().indexFromName(name)
        if index >= 0:
            feature[index] = value
    if not layer.addFeature(feature):
        if started:
            layer.rollBack()
        raise RuntimeError("The business record could not be added.")
    if started and not layer.commitChanges():
        raise RuntimeError("The business record could not be saved.")
    value = values.get("business_id")
    saved = feature_by_value(layer, "business_id", value)
    return saved.id() if saved is not None else feature.id()


def add_business_at_point(layer, values, point, point_crs, association):
    """Create a complete permit point and leave the layer out of edit mode."""
    if point_crs != layer.crs():
        transform = QgsCoordinateTransform(
            point_crs, layer.crs(), QgsProject.instance()
        )
        point = transform.transform(point)
    if layer.isEditable():
        raise RuntimeError(
            "Save or cancel existing business-layer edits before adding a permit."
        )
    if not layer.startEditing():
        raise RuntimeError("The business layer could not enter edit mode.")
    feature = QgsFeature(layer.fields())
    for name, value in values.items():
        index = layer.fields().indexFromName(name)
        if index >= 0:
            feature[index] = value
    feature["building_id"] = association.building_id
    feature["match_status"] = association.match_status
    feature.setGeometry(QgsGeometry.fromPointXY(point))
    if not layer.addFeature(feature):
        layer.rollBack()
        raise RuntimeError("The permit point could not be added.")
    if not layer.commitChanges():
        errors = "; ".join(layer.commitErrors())
        layer.rollBack()
        raise RuntimeError("The permit point could not be saved: " + errors)
    saved = feature_by_value(layer, "business_id", values.get("business_id"))
    return saved.id() if saved is not None else feature.id()


def add_google_hybrid_layer():
    """Add one Google Hybrid XYZ layer at the bottom of the project."""
    for layer in QgsProject.instance().mapLayers().values():
        if layer.name() == "Google Hybrid":
            return layer
    uri = (
        "type=xyz&url=https://mt1.google.com/vt/lyrs%3Dy%26x%3D{x}%26y%3D{y}"
        "%26z%3D{z}&zmax=22&zmin=0"
    )
    layer = QgsRasterLayer(uri, "Google Hybrid", "wms")
    if not layer.isValid():
        return None
    QgsProject.instance().addMapLayer(layer, False)
    QgsProject.instance().layerTreeRoot().addLayer(layer)
    return layer


def create_demo_layers(crs_authid):
    """Create synthetic in-memory layers so the plugin can be tried immediately."""
    buildings = QgsVectorLayer(
        "Polygon?crs={0}&field=building_id:string(40)&field=parcel_id:string(40)"
        "&field=building_name:string(120)&field=owner_name:string(120)&field=height_m:double".format(
            crs_authid
        ),
        "buildings",
        "memory",
    )
    businesses = QgsVectorLayer(
        "Point?crs={0}&field=business_id:string(40)&field=building_id:string(40)"
        "&field=business_name:string(120)&field=owner_name:string(120)"
        "&field=permit_no:string(60)&field=match_status:string(20)".format(crs_authid),
        "businesses",
        "memory",
    )
    QgsProject.instance().addMapLayer(buildings)
    QgsProject.instance().addMapLayer(businesses)
    return buildings, businesses

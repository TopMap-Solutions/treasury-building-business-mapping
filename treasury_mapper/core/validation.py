"""Attribute and relationship validation for prototype records."""

from collections import Counter

from .models import ValidationIssue


def _duplicate_ids(records, field_name):
    values = [getattr(record, field_name) for record in records]
    return set(value for value, count in Counter(values).items() if value and count > 1)


def validate_records(buildings, businesses):
    issues = []
    building_ids = set(record.building_id for record in buildings if record.building_id)
    duplicate_buildings = _duplicate_ids(buildings, "building_id")
    duplicate_businesses = _duplicate_ids(businesses, "business_id")

    for record in buildings:
        if not record.building_id:
            issues.append(ValidationIssue("missing_id", "building", None, "Building ID is required."))
        elif record.building_id in duplicate_buildings:
            issues.append(ValidationIssue("duplicate_id", "building", record.building_id, "Building ID is duplicated."))
        if record.height_m is not None and record.height_m < 0:
            issues.append(ValidationIssue("invalid_height", "building", record.building_id, "Building height cannot be negative."))

    for record in businesses:
        if not record.business_id:
            issues.append(ValidationIssue("missing_id", "business", None, "Business ID is required."))
        elif record.business_id in duplicate_businesses:
            issues.append(ValidationIssue("duplicate_id", "business", record.business_id, "Business ID is duplicated."))
        if not str(record.business_name or "").strip():
            issues.append(ValidationIssue("missing_name", "business", record.business_id, "Business name is required."))
        if record.building_id and record.building_id not in building_ids:
            issues.append(ValidationIssue("broken_link", "business", record.business_id, "Stored building ID does not exist."))
        if record.match_status not in ("matched", "unmatched", "multiple"):
            issues.append(ValidationIssue("invalid_status", "business", record.business_id, "Match status is invalid."))
    return issues


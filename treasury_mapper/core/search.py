"""Search and ranking rules with no QGIS dependencies."""

from .models import SearchResult


def normalize(value):
    """Return a case-insensitive, whitespace-normalized search value."""
    return " ".join(str(value or "").casefold().split())


def _score(query, values):
    normalized = [normalize(value) for value in values if value is not None]
    if query in normalized:
        return 300
    if any(value.startswith(query) for value in normalized):
        return 200
    if any(query in value for value in normalized):
        return 100
    return 0


def search_records(query, buildings, businesses):
    """Search both record collections and return best matches first."""
    query = normalize(query)
    if not query:
        return []

    results = []
    for record in buildings:
        score = _score(
            query,
            (record.building_id, record.parcel_id, record.building_name, record.owner_name),
        )
        if score:
            label = record.building_name or record.parcel_id or record.building_id
            results.append(SearchResult("building", record.building_id, label, score, record))

    for record in businesses:
        score = _score(
            query,
            (record.business_id, record.business_name, record.owner_name, record.permit_no),
        )
        if score:
            label = record.business_name or record.business_id
            results.append(SearchResult("business", record.business_id, label, score, record))

    return sorted(
        results,
        key=lambda result: (-result.score, normalize(result.label), result.record_id),
    )


"""Plain record types shared by core services."""

from collections import namedtuple


Building = namedtuple(
    "Building", "building_id parcel_id building_name owner_name height_m"
)
Business = namedtuple(
    "Business",
    "business_id building_id business_name owner_name permit_no match_status",
)
SearchResult = namedtuple("SearchResult", "record_type record_id label score record")
ValidationIssue = namedtuple("ValidationIssue", "code record_type record_id message")
Association = namedtuple("Association", "building_id match_status candidates")


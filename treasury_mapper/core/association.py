"""Decide the stored result from spatial match candidates."""

from .models import Association


def associate(candidate_building_ids):
    candidates = tuple(sorted(set(value for value in candidate_building_ids if value)))
    if not candidates:
        return Association(None, "unmatched", candidates)
    if len(candidates) == 1:
        return Association(candidates[0], "matched", candidates)
    return Association(None, "multiple", candidates)


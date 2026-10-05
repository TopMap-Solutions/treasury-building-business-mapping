import unittest

from treasury_mapper.core.association import associate
from treasury_mapper.core.models import Building, Business
from treasury_mapper.core.search import search_records
from treasury_mapper.core.validation import validate_records


class CoreRulesTest(unittest.TestCase):
    def setUp(self):
        self.buildings = [
            Building("B-001", "01-0042", "Mercado Building", "Maria Santos", 8.5),
            Building("B-002", "01-0043", "Civic Arcade", "LGU", 5.0),
        ]
        self.businesses = [
            Business("BP-1021", "B-001", "Juan's Pharmacy", "Juan Dela Cruz", "2026-1021", "matched"),
        ]

    def test_searches_both_record_types_case_insensitively(self):
        self.assertEqual("building", search_records("mercado", self.buildings, self.businesses)[0].record_type)
        self.assertEqual("business", search_records("JUAN", self.buildings, self.businesses)[0].record_type)

    def test_exact_identifier_ranks_above_substring(self):
        result = search_records("B-001", self.buildings, self.businesses)[0]
        self.assertEqual("B-001", result.record_id)
        self.assertEqual(300, result.score)

    def test_association_has_three_explicit_outcomes(self):
        self.assertEqual("unmatched", associate([]).match_status)
        self.assertEqual("B-001", associate(["B-001"]).building_id)
        self.assertEqual("multiple", associate(["B-002", "B-001"]).match_status)

    def test_validation_finds_expected_issues(self):
        buildings = self.buildings + [Building("B-001", "x", "Other", "Owner", -1)]
        businesses = [Business("BP-1", "missing", "", "Owner", None, "matched")]
        codes = set(issue.code for issue in validate_records(buildings, businesses))
        expected = {"duplicate_id", "invalid_height", "missing_name", "broken_link"}
        self.assertTrue(expected.issubset(codes))


if __name__ == "__main__":
    unittest.main()


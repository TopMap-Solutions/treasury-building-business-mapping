import configparser
import os
import unittest


class PluginMetadataTest(unittest.TestCase):
    def test_qgis_metadata_contains_required_release_fields(self):
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        metadata_path = os.path.join(project_root, "treasury_mapper", "metadata.txt")
        parser = configparser.ConfigParser()
        loaded = parser.read(metadata_path)

        self.assertEqual([metadata_path], loaded)
        self.assertTrue(parser.has_section("general"))
        for field in ("name", "description", "version", "qgisMinimumVersion", "author"):
            self.assertTrue(parser.get("general", field).strip(), field)
        self.assertEqual("3.0", parser.get("general", "qgisMinimumVersion"))
        icon_path = os.path.join(project_root, "treasury_mapper", parser.get("general", "icon"))
        self.assertTrue(os.path.isfile(icon_path))


if __name__ == "__main__":
    unittest.main()

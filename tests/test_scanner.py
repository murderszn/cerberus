import unittest
import json
import os

class TestChecks(unittest.TestCase):
    def test_checks_json_exists(self):
        self.assertTrue(os.path.exists("checks.json"))
        with open("checks.json") as f:
            data = json.load(f)
            self.assertIn("checks", data)
            self.assertIn("agents", data)

if __name__ == "__main__":
    unittest.main()

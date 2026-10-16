import csv
import tempfile
import unittest
from pathlib import Path
from scd2 import DataQualityError, get_history, load_file, reset_database
from reporting import generate_report


class SCD2Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = self.root / "test.db"
        self.input = self.root / "input.csv"
        reset_database(self.db)

    def tearDown(self):
        self.temp.cleanup()

    def write_csv(self, rows):
        with self.input.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=["customer_id", "customer_name", "city", "segment", "effective_date"]
            )
            writer.writeheader()
            writer.writerows(rows)
        return self.input

    def row(self, customer_id="C1", name="Asha", city="Lucknow",
            segment="Standard", effective_date="2026-01-01"):
        return {"customer_id": customer_id, "customer_name": name, "city": city,
                "segment": segment, "effective_date": effective_date}

    def test_new_customer_creates_first_current_version(self):
        self.write_csv([self.row()])
        result = load_file(self.input, self.db)
        history = get_history("C1", self.db)
        self.assertEqual(result["status"], "processed")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["is_current"], 1)

    def test_changed_city_preserves_old_version(self):
        self.write_csv([self.row()])
        load_file(self.input, self.db)
        self.write_csv([self.row(city="Delhi", segment="Premium", effective_date="2026-03-01")])
        load_file(self.input, self.db)
        history = get_history("C1", self.db)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["city"], "Lucknow")
        self.assertEqual(history[0]["is_current"], 0)
        self.assertEqual(history[0]["effective_to"], "2026-03-01")
        self.assertEqual(history[1]["city"], "Delhi")
        self.assertEqual(history[1]["is_current"], 1)

    def test_exact_rerun_is_idempotent(self):
        self.write_csv([self.row()])
        first = load_file(self.input, self.db)
        second = load_file(self.input, self.db)
        self.assertEqual(first["status"], "processed")
        self.assertEqual(second["status"], "skipped_duplicate_batch")
        self.assertEqual(len(get_history("C1", self.db)), 1)

    def test_unchanged_attributes_do_not_create_new_version(self):
        self.write_csv([self.row()])
        load_file(self.input, self.db)
        self.write_csv([self.row(effective_date="2026-02-01")])
        result = load_file(self.input, self.db)
        self.assertEqual(result["inserted_versions"], 0)
        self.assertEqual(len(get_history("C1", self.db)), 1)

    def test_out_of_order_change_is_rejected(self):
        self.write_csv([self.row(effective_date="2026-02-01")])
        load_file(self.input, self.db)
        self.write_csv([self.row(city="Delhi", effective_date="2026-01-15")])
        with self.assertRaises(DataQualityError):
            load_file(self.input, self.db)
        self.assertEqual(len(get_history("C1", self.db)), 1)

    def test_duplicate_customer_in_file_is_rejected(self):
        self.write_csv([self.row(), self.row(city="Delhi")])
        with self.assertRaises(DataQualityError):
            load_file(self.input, self.db)

    def test_report_is_valid_json(self):
        self.write_csv([self.row()])
        load_file(self.input, self.db)
        out = self.root / "out"
        report = generate_report(self.db, out)
        self.assertTrue(Path(report["json"]).exists())
        self.assertTrue(Path(report["markdown"]).exists())


if __name__ == "__main__":
    unittest.main()

"""Tests for the LayerLog command-line application."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from layerlog.cli import main


class LayerLogCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Path(self.temp_dir.name) / "prints.json"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_cli(self, *arguments: str) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(["--db", str(self.database), *arguments])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_add_persists_a_print(self) -> None:
        code, output, _ = self.run_cli(
            "add",
            "--name", "Benchy",
            "--printer", "Bambu A1",
            "--material", "PLA",
            "--grams", "18.5",
            "--minutes", "13",
            "--notes", "First test",
        )
        self.assertEqual(code, 0)
        self.assertIn("Saved Benchy", output)
        entries = json.loads(self.database.read_text(encoding="utf-8"))
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["name"], "Benchy")
        self.assertEqual(entries[0]["grams"], 18.5)
        self.assertEqual(entries[0]["notes"], "First test")

    def test_list_shows_saved_print(self) -> None:
        self.run_cli("add", "--name", "Cube", "--printer", "Ender", "--grams", "4", "--minutes", "12")
        code, output, _ = self.run_cli("list")
        self.assertEqual(code, 0)
        self.assertIn("Cube", output)
        self.assertIn("Ender", output)

    def test_stats_totals_multiple_prints(self) -> None:
        self.run_cli("add", "--name", "One", "--printer", "A1", "--material", "PLA", "--grams", "10", "--minutes", "30")
        self.run_cli("add", "--name", "Two", "--printer", "A1", "--material", "PETG", "--grams", "20", "--minutes", "45")
        code, output, _ = self.run_cli("stats")
        self.assertEqual(code, 0)
        self.assertIn("Prints recorded: 2", output)
        self.assertIn("Filament used:   30.00 g", output)
        self.assertIn("1h 15m", output)
        self.assertIn("PETG", output)

    def test_negative_filament_is_rejected(self) -> None:
        code, _, error = self.run_cli(
            "add", "--name", "Bad", "--printer", "A1", "--grams", "-1"
        )
        self.assertEqual(code, 2)
        self.assertIn("grams cannot be negative", error)

    def test_empty_database_is_friendly(self) -> None:
        code, output, _ = self.run_cli("list")
        self.assertEqual(code, 0)
        self.assertIn("No print jobs recorded yet", output)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bsdgs_verifier.config import ConfigManager
from bsdgs_verifier.gui import Application


class OutputSettingsTest(unittest.TestCase):
    def test_output_directories_are_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager = ConfigManager(root / "config.json")
            config = manager.load()
            config.reports.reports_output_dir = str(root / "relatorios")
            config.reports.logs_output_dir = str(root / "logs")
            config.schedule.reports_output_dir = str(root / "agendado" / "relatorios")
            config.schedule.logs_output_dir = str(root / "agendado" / "logs")
            manager.save(config)

            loaded = manager.load()
            self.assertEqual(loaded.reports.reports_output_dir, str(root / "relatorios"))
            self.assertEqual(loaded.reports.logs_output_dir, str(root / "logs"))
            self.assertEqual(
                loaded.schedule.reports_output_dir,
                str(root / "agendado" / "relatorios"),
            )
            self.assertEqual(
                loaded.schedule.logs_output_dir,
                str(root / "agendado" / "logs"),
            )

    def test_last_run_datetime_uses_brazilian_format_and_utc_offset(self) -> None:
        formatted = Application._format_run_datetime("2026-08-04T14:05:08-03:00")
        self.assertEqual(formatted, "04/08/2026 às 14:05:08 (UTC-03:00)")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bsdgs_verifier.config import ConfigManager


class ConfigMigrationTest(unittest.TestCase):
    def test_legacy_truncated_names_are_corrected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "bsdgs": [
                            {
                                "id": "legacy-comunidades",
                                "name": "BSDG_ComunidadesN… (confirmar nome completo)",
                                "needs_name_confirmation": True,
                            },
                            {
                                "id": "legacy-internacionalizacao",
                                "name": "BSDG_Internacionaliza… (confirmar nome completo)",
                                "needs_name_confirmation": True,
                            },
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            config = ConfigManager(path).load()
            self.assertEqual(config.bsdgs[0].name, "BSDG_ComunidadesNoMapa")
            self.assertEqual(config.bsdgs[1].name, "BSDG_Internacionalização")
            self.assertFalse(config.bsdgs[0].needs_name_confirmation)
            self.assertFalse(config.bsdgs[1].needs_name_confirmation)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bsdgs_verifier.scanner import discover_gpkg_files


class ScannerTest(unittest.TestCase):
    def test_recursive_discovery_is_case_insensitive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / "Áreas Protegidas (APT)"
            nested.mkdir()
            (nested / "APT_sambaquis.GPKG").write_bytes(b"placeholder")
            (nested / "ignorar.txt").write_text("x", encoding="utf-8")
            files = discover_gpkg_files(root, recursive=True)
            self.assertEqual(len(files), 1)
            self.assertEqual(files[0].name, "APT_sambaquis.GPKG")


if __name__ == "__main__":
    unittest.main()

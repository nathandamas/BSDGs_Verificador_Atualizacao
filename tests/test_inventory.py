from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bsdgs_verifier.inventory import InventoryDB


class InventoryDBTest(unittest.TestCase):
    def test_schema_is_created(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "inventory.sqlite"
            database = InventoryDB(path)
            self.assertTrue(path.exists())
            self.assertIsNone(database.latest_run())


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from contextlib import closing

from bsdgs_verifier.config import ConfigManager
from bsdgs_verifier.inventory import InventoryDB
from bsdgs_verifier.models import AppConfig, BsdgConfig
from bsdgs_verifier.reports import ReportWriter
from bsdgs_verifier.service import VerificationService


class VerificationServiceTest(unittest.TestCase):
    def test_initial_scan_registers_valid_geopackage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            gpkg_dir = root / "gpkg" / "APT"
            gpkg_dir.mkdir(parents=True)
            gpkg_path = gpkg_dir / "APT_sambaquis.gpkg"
            self._create_gpkg(gpkg_path)

            config_path = root / "config.json"
            config_manager = ConfigManager(config_path)
            config = AppConfig(
                version=1,
                bsdgs=[
                    BsdgConfig(
                        id="teste",
                        name="BSDG_Teste",
                        local_path=str(root / "gpkg"),
                        enabled=True,
                        recursive=True,
                    )
                ],
            )
            config_manager.save(config)

            inventory = InventoryDB(root / "inventory.sqlite")
            service = VerificationService(
                config_manager=config_manager,
                inventory=inventory,
                report_writer=ReportWriter(root / "reports"),
            )
            summary = service.run_scan(mode="TESTE")

            self.assertEqual(summary.total_files, 1)
            self.assertEqual(summary.new_files, 1)
            self.assertEqual(summary.valid_files, 1)
            self.assertEqual(summary.invalid_files, 0)
            self.assertTrue(summary.report_paths)


    def test_scan_can_override_report_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            gpkg_dir = root / "gpkg" / "APT"
            gpkg_dir.mkdir(parents=True)
            gpkg_path = gpkg_dir / "APT_sambaquis.gpkg"
            self._create_gpkg(gpkg_path)

            config_manager = ConfigManager(root / "config.json")
            config = AppConfig(
                version=1,
                bsdgs=[
                    BsdgConfig(
                        id="teste",
                        name="BSDG_Teste",
                        local_path=str(root / "gpkg"),
                        enabled=True,
                        recursive=True,
                    )
                ],
            )
            config_manager.save(config)

            inventory = InventoryDB(root / "inventory.sqlite")
            service = VerificationService(
                config_manager=config_manager,
                inventory=inventory,
                report_writer=ReportWriter(root / "relatorios_padrao"),
            )
            custom_reports = root / "relatorios_escolhidos"
            summary = service.run_scan(mode="TESTE", report_output_dir=custom_reports)

            self.assertTrue(summary.report_paths)
            self.assertTrue(all(Path(item).parent == custom_reports for item in summary.report_paths))

    @staticmethod
    def _create_gpkg(path: Path) -> None:
        with closing(sqlite3.connect(path)) as connection:
            connection.executescript(
                """
                CREATE TABLE gpkg_spatial_ref_sys (
                    srs_name TEXT NOT NULL,
                    srs_id INTEGER NOT NULL PRIMARY KEY,
                    organization TEXT NOT NULL,
                    organization_coordsys_id INTEGER NOT NULL,
                    definition TEXT NOT NULL,
                    description TEXT
                );
                INSERT INTO gpkg_spatial_ref_sys VALUES
                    ('SIRGAS 2000', 4674, 'EPSG', 4674, 'undefined', 'teste');

                CREATE TABLE gpkg_contents (
                    table_name TEXT NOT NULL PRIMARY KEY,
                    data_type TEXT NOT NULL,
                    identifier TEXT UNIQUE,
                    description TEXT DEFAULT '',
                    last_change DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                    min_x DOUBLE, min_y DOUBLE, max_x DOUBLE, max_y DOUBLE,
                    srs_id INTEGER
                );
                CREATE TABLE gpkg_geometry_columns (
                    table_name TEXT NOT NULL,
                    column_name TEXT NOT NULL,
                    geometry_type_name TEXT NOT NULL,
                    srs_id INTEGER NOT NULL,
                    z TINYINT NOT NULL,
                    m TINYINT NOT NULL,
                    PRIMARY KEY (table_name, column_name)
                );
                CREATE TABLE APT_sambaquis (id INTEGER PRIMARY KEY, geom BLOB);
                INSERT INTO gpkg_contents(table_name, data_type, identifier, description, srs_id)
                VALUES ('APT_sambaquis', 'features', 'APT_sambaquis', 'teste', 4674);
                INSERT INTO gpkg_geometry_columns VALUES
                ('APT_sambaquis', 'geom', 'POINT', 4674, 0, 0);
                """
            )


if __name__ == "__main__":
    unittest.main()

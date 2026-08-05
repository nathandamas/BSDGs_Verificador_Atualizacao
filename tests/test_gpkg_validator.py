from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from bsdgs_verifier.gpkg_validator import GeoPackageValidator
from bsdgs_verifier.models import ValidationStatus


class GeoPackageValidatorTest(unittest.TestCase):
    def test_valid_minimal_feature_geopackage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "teste.gpkg"

            # O context manager nativo de sqlite3 não fecha a conexão.
            # closing() garante o fechamento do arquivo no Windows.
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
                connection.commit()

            result = GeoPackageValidator(run_quick_check=True).validate(path)
            self.assertEqual(result.status, ValidationStatus.VALID)
            self.assertTrue(result.is_geopackage)
            self.assertEqual(result.feature_layer_count, 1)
            self.assertEqual(result.layers[0].geometry_type, "POINT")
            self.assertEqual(result.layers[0].srs_id, 4674)

    def test_rejects_plain_sqlite_without_gpkg_tables(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plain.sqlite"

            with closing(sqlite3.connect(path)) as connection:
                connection.execute("CREATE TABLE teste(id INTEGER)")
                connection.commit()

            result = GeoPackageValidator().validate(path)
            self.assertEqual(result.status, ValidationStatus.INVALID)
            self.assertFalse(result.is_geopackage)


if __name__ == "__main__":
    unittest.main()

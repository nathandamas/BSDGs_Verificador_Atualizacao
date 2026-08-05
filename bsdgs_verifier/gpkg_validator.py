from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any

from .constants import KNOWN_GEOMETRY_TYPES
from .models import LayerValidation, ValidationResult, ValidationStatus

LOGGER = logging.getLogger(__name__)
SQLITE_HEADER = b"SQLite format 3\x00"


class GeoPackageValidator:
    """Validador estrutural de GeoPackage usando apenas a biblioteca padrão.

    A validação confirma o contêiner SQLite, as tabelas centrais do GeoPackage,
    as referências de gpkg_contents/gpkg_geometry_columns e as declarações de
    geometria/SRS. Não substitui uma auditoria geométrica completa com GDAL/OGR.
    """

    def __init__(
        self,
        run_quick_check: bool = True,
        count_features: bool = False,
        timeout_seconds: int = 10,
    ) -> None:
        self.run_quick_check = run_quick_check
        self.count_features = count_features
        self.timeout_seconds = timeout_seconds

    def validate(self, path: Path) -> ValidationResult:
        try:
            file_size = path.stat().st_size
        except OSError as exc:
            return ValidationResult(
                status=ValidationStatus.ERROR,
                is_sqlite=False,
                is_geopackage=False,
                error_message=str(exc),
                issues=["Não foi possível ler os metadados do arquivo."],
            )

        if file_size == 0:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                is_sqlite=False,
                is_geopackage=False,
                file_size=0,
                issues=["O arquivo está vazio."],
            )

        try:
            with path.open("rb") as stream:
                header = stream.read(len(SQLITE_HEADER))
        except (PermissionError, OSError) as exc:
            return ValidationResult(
                status=ValidationStatus.ERROR,
                is_sqlite=False,
                is_geopackage=False,
                file_size=file_size,
                error_message=str(exc),
                issues=["O arquivo não pôde ser aberto para leitura."],
            )

        if header != SQLITE_HEADER:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                is_sqlite=False,
                is_geopackage=False,
                file_size=file_size,
                issues=["O cabeçalho não corresponde a um banco SQLite válido."],
            )

        result = ValidationResult(
            status=ValidationStatus.NOT_VALIDATED,
            is_sqlite=True,
            is_geopackage=False,
            file_size=file_size,
        )

        try:
            uri = f"{path.resolve().as_uri()}?mode=ro"
            with sqlite3.connect(uri, uri=True, timeout=self.timeout_seconds) as connection:
                connection.row_factory = sqlite3.Row
                connection.execute("PRAGMA query_only = ON")
                self._validate_connection(connection, result)
        except sqlite3.DatabaseError as exc:
            result.status = ValidationStatus.ERROR
            result.error_message = str(exc)
            result.issues.append("O SQLite retornou erro ao abrir ou consultar o arquivo.")
            LOGGER.warning("Erro SQLite em %s: %s", path, exc)
            return result
        except (PermissionError, OSError) as exc:
            result.status = ValidationStatus.ERROR
            result.error_message = str(exc)
            result.issues.append("O arquivo está bloqueado, indisponível ou sem permissão de leitura.")
            return result

        result.status = ValidationStatus.VALID if not result.issues else ValidationStatus.INVALID
        return result

    def _validate_connection(self, connection: sqlite3.Connection, result: ValidationResult) -> None:
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
            ).fetchall()
        }

        required = {"gpkg_spatial_ref_sys", "gpkg_contents"}
        missing = sorted(required - tables)
        if missing:
            result.issues.append(
                "Tabelas centrais ausentes: " + ", ".join(missing)
            )
            return

        result.is_geopackage = True

        if self.run_quick_check:
            rows = connection.execute("PRAGMA quick_check").fetchall()
            quick_messages = [str(row[0]) for row in rows]
            result.quick_check_ok = quick_messages == ["ok"]
            if not result.quick_check_ok:
                result.issues.append(
                    "Falha no PRAGMA quick_check: " + "; ".join(quick_messages[:10])
                )

        contents_columns = self._column_names(connection, "gpkg_contents")
        required_contents_columns = {
            "table_name",
            "data_type",
            "identifier",
            "description",
            "srs_id",
        }
        missing_columns = sorted(required_contents_columns - contents_columns)
        if missing_columns:
            result.issues.append(
                "gpkg_contents sem colunas obrigatórias: " + ", ".join(missing_columns)
            )
            return

        content_rows = connection.execute(
            """
            SELECT table_name, data_type, identifier, description, srs_id
            FROM gpkg_contents
            ORDER BY table_name
            """
        ).fetchall()

        geometry_rows: dict[str, sqlite3.Row] = {}
        if "gpkg_geometry_columns" in tables:
            geometry_columns = self._column_names(connection, "gpkg_geometry_columns")
            required_geometry_columns = {
                "table_name",
                "column_name",
                "geometry_type_name",
                "srs_id",
                "z",
                "m",
            }
            missing_geometry_columns = sorted(required_geometry_columns - geometry_columns)
            if missing_geometry_columns:
                result.issues.append(
                    "gpkg_geometry_columns sem colunas obrigatórias: "
                    + ", ".join(missing_geometry_columns)
                )
            else:
                for row in connection.execute(
                    """
                    SELECT table_name, column_name, geometry_type_name, srs_id, z, m
                    FROM gpkg_geometry_columns
                    """
                ).fetchall():
                    geometry_rows[str(row["table_name"])] = row

        srs_ids = {
            int(row[0])
            for row in connection.execute(
                "SELECT srs_id FROM gpkg_spatial_ref_sys"
            ).fetchall()
        }

        content_table_names: set[str] = set()
        for content in content_rows:
            table_name = str(content["table_name"])
            data_type = str(content["data_type"]).lower()
            content_table_names.add(table_name)
            layer = LayerValidation(
                table_name=table_name,
                data_type=data_type,
                identifier=content["identifier"],
                description=content["description"],
                srs_id=content["srs_id"],
                table_exists=table_name in tables,
            )

            if not layer.table_exists:
                layer.valid = False
                layer.issues.append("A tabela declarada em gpkg_contents não existe.")

            if data_type == "features":
                result.feature_layer_count += 1
                geometry = geometry_rows.get(table_name)
                if geometry is None:
                    layer.valid = False
                    layer.issues.append(
                        "Camada vetorial sem registro em gpkg_geometry_columns."
                    )
                else:
                    self._validate_feature_layer(connection, layer, geometry, srs_ids)
            elif data_type == "tiles":
                result.tile_layer_count += 1
            elif data_type == "attributes":
                result.attribute_layer_count += 1
            else:
                layer.warnings.append(
                    f"Tipo de conteúdo não central ou pertencente a extensão: {data_type}."
                )

            if self.count_features and layer.table_exists and data_type in {"features", "attributes"}:
                try:
                    layer.feature_count = int(
                        connection.execute(
                            f"SELECT COUNT(*) FROM {self._quote_identifier(table_name)}"
                        ).fetchone()[0]
                    )
                except sqlite3.DatabaseError as exc:
                    layer.warnings.append(f"Não foi possível contar registros: {exc}")

            if layer.issues:
                result.issues.extend(
                    f"{table_name}: {message}" for message in layer.issues
                )
            result.warnings.extend(
                f"{table_name}: {message}" for message in layer.warnings
            )
            result.layers.append(layer)

        # Registros geométricos órfãos também tornam o pacote inconsistente.
        orphan_geometry_tables = sorted(set(geometry_rows) - content_table_names)
        for table_name in orphan_geometry_tables:
            result.issues.append(
                f"gpkg_geometry_columns referencia '{table_name}', ausente em gpkg_contents."
            )

        result.layer_count = len(result.layers)

    def _validate_feature_layer(
        self,
        connection: sqlite3.Connection,
        layer: LayerValidation,
        geometry: sqlite3.Row,
        srs_ids: set[int],
    ) -> None:
        content_srs_id = layer.srs_id
        layer.geometry_column = str(geometry["column_name"])
        layer.geometry_type = str(geometry["geometry_type_name"]).upper()
        layer.srs_id = int(geometry["srs_id"])
        if content_srs_id is not None and int(content_srs_id) != layer.srs_id:
            layer.valid = False
            layer.issues.append(
                f"SRID divergente: gpkg_contents={content_srs_id} e gpkg_geometry_columns={layer.srs_id}."
            )
        layer.z = int(geometry["z"])
        layer.m = int(geometry["m"])

        if layer.geometry_type not in KNOWN_GEOMETRY_TYPES:
            layer.valid = False
            layer.issues.append(
                f"Tipo de geometria não reconhecido: {layer.geometry_type}."
            )

        if layer.z not in {0, 1, 2}:
            layer.valid = False
            layer.issues.append(f"Valor Z inválido em gpkg_geometry_columns: {layer.z}.")
        if layer.m not in {0, 1, 2}:
            layer.valid = False
            layer.issues.append(f"Valor M inválido em gpkg_geometry_columns: {layer.m}.")

        if layer.table_exists:
            columns = self._column_names(connection, layer.table_name)
            layer.geometry_column_exists = layer.geometry_column in columns
            if not layer.geometry_column_exists:
                layer.valid = False
                layer.issues.append(
                    f"A coluna geométrica '{layer.geometry_column}' não existe na tabela."
                )

        layer.srs_exists = layer.srs_id in srs_ids
        if not layer.srs_exists:
            layer.valid = False
            layer.issues.append(
                f"O SRS {layer.srs_id} não existe em gpkg_spatial_ref_sys."
            )

    @staticmethod
    def _column_names(connection: sqlite3.Connection, table_name: str) -> set[str]:
        quoted = GeoPackageValidator._quote_identifier(table_name)
        return {
            str(row[1])
            for row in connection.execute(f"PRAGMA table_info({quoted})").fetchall()
        }

    @staticmethod
    def _quote_identifier(identifier: str) -> str:
        return '"' + identifier.replace('"', '""') + '"'

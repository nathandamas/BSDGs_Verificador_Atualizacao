from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable

from .constants import DATABASE_SCHEMA_VERSION
from .models import FileScanResult, ScanSummary
from .paths import database_path

class InventoryDB:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        """Abre uma conexão transacional e garante seu fechamento no Windows."""
        connection = self._connect()

        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS scan_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    mode TEXT NOT NULL,
                    outcome TEXT NOT NULL DEFAULT 'EM EXECUÇÃO',
                    total_bsdgs INTEGER NOT NULL DEFAULT 0,
                    scanned_bsdgs INTEGER NOT NULL DEFAULT 0,
                    missing_bsdgs INTEGER NOT NULL DEFAULT 0,
                    total_files INTEGER NOT NULL DEFAULT 0,
                    new_files INTEGER NOT NULL DEFAULT 0,
                    modified_files INTEGER NOT NULL DEFAULT 0,
                    unchanged_files INTEGER NOT NULL DEFAULT 0,
                    removed_files INTEGER NOT NULL DEFAULT 0,
                    valid_files INTEGER NOT NULL DEFAULT 0,
                    invalid_files INTEGER NOT NULL DEFAULT 0,
                    online_only_files INTEGER NOT NULL DEFAULT 0,
                    inaccessible_files INTEGER NOT NULL DEFAULT 0,
                    summary_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS bsdgs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_id TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    local_path TEXT NOT NULL DEFAULT '',
                    enabled INTEGER NOT NULL DEFAULT 0,
                    recursive INTEGER NOT NULL DEFAULT 1,
                    last_scan_at TEXT,
                    last_status TEXT,
                    last_message TEXT
                );

                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bsdg_id INTEGER NOT NULL REFERENCES bsdgs(id) ON DELETE CASCADE,
                    relative_path TEXT NOT NULL,
                    absolute_path TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL DEFAULT 0,
                    mtime_ns INTEGER NOT NULL DEFAULT 0,
                    modified_iso TEXT NOT NULL DEFAULT '',
                    sha256 TEXT NOT NULL DEFAULT '',
                    change_status TEXT NOT NULL,
                    availability_status TEXT NOT NULL,
                    validation_status TEXT NOT NULL,
                    display_status TEXT NOT NULL,
                    one_drive_attributes INTEGER NOT NULL DEFAULT 0,
                    message TEXT NOT NULL DEFAULT '',
                    validation_json TEXT NOT NULL DEFAULT '{}',
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    last_seen_run_id INTEGER REFERENCES scan_runs(id),
                    removed_at TEXT,
                    UNIQUE (bsdg_id, relative_path)
                );

                CREATE TABLE IF NOT EXISTS layers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
                    table_name TEXT NOT NULL,
                    data_type TEXT NOT NULL,
                    identifier TEXT,
                    description TEXT,
                    geometry_column TEXT,
                    geometry_type TEXT,
                    srs_id INTEGER,
                    z INTEGER,
                    m INTEGER,
                    feature_count INTEGER,
                    table_exists INTEGER NOT NULL DEFAULT 0,
                    geometry_column_exists INTEGER,
                    srs_exists INTEGER,
                    valid INTEGER NOT NULL DEFAULT 1,
                    issues TEXT NOT NULL DEFAULT '',
                    warnings TEXT NOT NULL DEFAULT ''
                );

                CREATE INDEX IF NOT EXISTS idx_files_status ON files(display_status);
                CREATE INDEX IF NOT EXISTS idx_files_last_run ON files(last_seen_run_id);
                CREATE INDEX IF NOT EXISTS idx_layers_file ON layers(file_id);
                """
            )
            connection.execute(f"PRAGMA user_version = {DATABASE_SCHEMA_VERSION}")

    def start_run(self, started_at: str, mode: str) -> int:
        with self._connection() as connection:
            cursor = connection.execute(
                "INSERT INTO scan_runs(started_at, mode) VALUES (?, ?)",
                (started_at, mode),
            )
            return int(cursor.lastrowid)

    def finish_run(self, summary: ScanSummary) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                UPDATE scan_runs
                SET completed_at = ?, outcome = ?, total_bsdgs = ?, scanned_bsdgs = ?,
                    missing_bsdgs = ?, total_files = ?, new_files = ?, modified_files = ?,
                    unchanged_files = ?, removed_files = ?, valid_files = ?, invalid_files = ?,
                    online_only_files = ?, inaccessible_files = ?, summary_json = ?
                WHERE id = ?
                """,
                (
                    summary.completed_at,
                    summary.outcome,
                    summary.total_bsdgs,
                    summary.scanned_bsdgs,
                    summary.missing_bsdgs,
                    summary.total_files,
                    summary.new_files,
                    summary.modified_files,
                    summary.unchanged_files,
                    summary.removed_files,
                    summary.valid_files,
                    summary.invalid_files,
                    summary.online_only_files,
                    summary.inaccessible_files,
                    json.dumps(summary.to_dict(), ensure_ascii=False),
                    summary.run_id,
                ),
            )

    def upsert_bsdg(
        self,
        config_id: str,
        name: str,
        local_path: str,
        enabled: bool,
        recursive: bool,
        last_scan_at: str,
        status: str,
        message: str,
    ) -> int:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO bsdgs(config_id, name, local_path, enabled, recursive, last_scan_at, last_status, last_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(config_id) DO UPDATE SET
                    name = excluded.name,
                    local_path = excluded.local_path,
                    enabled = excluded.enabled,
                    recursive = excluded.recursive,
                    last_scan_at = excluded.last_scan_at,
                    last_status = excluded.last_status,
                    last_message = excluded.last_message
                """,
                (
                    config_id,
                    name,
                    local_path,
                    int(enabled),
                    int(recursive),
                    last_scan_at,
                    status,
                    message,
                ),
            )
            row = connection.execute(
                "SELECT id FROM bsdgs WHERE config_id = ?", (config_id,)
            ).fetchone()
            return int(row["id"])

    def update_bsdg_status(self, config_id: str, status: str, message: str, scan_at: str) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                UPDATE bsdgs
                SET last_status = ?, last_message = ?, last_scan_at = ?
                WHERE config_id = ?
                """,
                (status, message, scan_at, config_id),
            )

    def get_previous_file(self, bsdg_db_id: int, relative_path: str) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT * FROM files
                WHERE bsdg_id = ? AND relative_path = ? AND removed_at IS NULL
                """,
                (bsdg_db_id, relative_path),
            ).fetchone()
            return dict(row) if row else None

    def upsert_file(self, bsdg_db_id: int, result: FileScanResult, run_id: int, seen_at: str) -> int:
        validation_json = json.dumps(result.validation.to_dict(), ensure_ascii=False)
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO files(
                    bsdg_id, relative_path, absolute_path, file_name, category,
                    size_bytes, mtime_ns, modified_iso, sha256, change_status,
                    availability_status, validation_status, display_status,
                    one_drive_attributes, message, validation_json,
                    first_seen_at, last_seen_at, last_seen_run_id, removed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                ON CONFLICT(bsdg_id, relative_path) DO UPDATE SET
                    absolute_path = excluded.absolute_path,
                    file_name = excluded.file_name,
                    category = excluded.category,
                    size_bytes = excluded.size_bytes,
                    mtime_ns = excluded.mtime_ns,
                    modified_iso = excluded.modified_iso,
                    sha256 = excluded.sha256,
                    change_status = excluded.change_status,
                    availability_status = excluded.availability_status,
                    validation_status = excluded.validation_status,
                    display_status = excluded.display_status,
                    one_drive_attributes = excluded.one_drive_attributes,
                    message = excluded.message,
                    validation_json = excluded.validation_json,
                    last_seen_at = excluded.last_seen_at,
                    last_seen_run_id = excluded.last_seen_run_id,
                    removed_at = NULL
                """,
                (
                    bsdg_db_id,
                    result.relative_path,
                    result.absolute_path,
                    result.file_name,
                    result.category,
                    result.size_bytes,
                    result.mtime_ns,
                    result.modified_iso,
                    result.sha256,
                    result.change_status.value,
                    result.availability_status.value,
                    result.validation.status.value,
                    result.display_status,
                    result.one_drive_attributes,
                    result.message,
                    validation_json,
                    seen_at,
                    seen_at,
                    run_id,
                ),
            )
            row = connection.execute(
                "SELECT id FROM files WHERE bsdg_id = ? AND relative_path = ?",
                (bsdg_db_id, result.relative_path),
            ).fetchone()
            file_id = int(row["id"])
            connection.execute("DELETE FROM layers WHERE file_id = ?", (file_id,))
            for layer in result.validation.layers:
                connection.execute(
                    """
                    INSERT INTO layers(
                        file_id, table_name, data_type, identifier, description,
                        geometry_column, geometry_type, srs_id, z, m, feature_count,
                        table_exists, geometry_column_exists, srs_exists, valid,
                        issues, warnings
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        file_id,
                        layer.table_name,
                        layer.data_type,
                        layer.identifier,
                        layer.description,
                        layer.geometry_column,
                        layer.geometry_type,
                        layer.srs_id,
                        layer.z,
                        layer.m,
                        layer.feature_count,
                        int(layer.table_exists),
                        None if layer.geometry_column_exists is None else int(layer.geometry_column_exists),
                        None if layer.srs_exists is None else int(layer.srs_exists),
                        int(layer.valid),
                        " | ".join(layer.issues),
                        " | ".join(layer.warnings),
                    ),
                )
            return file_id

    def mark_removed_files(
        self,
        bsdg_db_id: int,
        seen_relative_paths: Iterable[str],
        run_id: int,
        removed_at: str,
    ) -> int:
        seen = set(seen_relative_paths)
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT id, relative_path FROM files WHERE bsdg_id = ? AND removed_at IS NULL",
                (bsdg_db_id,),
            ).fetchall()
            removed_ids = [int(row["id"]) for row in rows if row["relative_path"] not in seen]
            for file_id in removed_ids:
                connection.execute(
                    """
                    UPDATE files
                    SET change_status = 'REMOVIDO', display_status = 'REMOVIDO',
                        removed_at = ?, last_seen_run_id = ?
                    WHERE id = ?
                    """,
                    (removed_at, run_id, file_id),
                )
            return len(removed_ids)

    def latest_run(self) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM scan_runs ORDER BY id DESC LIMIT 1"
            ).fetchone()
            return dict(row) if row else None

    def dashboard_stats(self) -> dict[str, Any]:
        with self._connection() as connection:
            bsdg = connection.execute(
                """
                SELECT COUNT(*) total,
                       SUM(CASE WHEN enabled = 1 THEN 1 ELSE 0 END) enabled,
                       SUM(CASE WHEN last_status = 'PASTA NÃO ENCONTRADA' THEN 1 ELSE 0 END) missing
                FROM bsdgs
                """
            ).fetchone()
            current = connection.execute(
                "SELECT COUNT(*) total_files FROM files WHERE removed_at IS NULL"
            ).fetchone()
            return {
                "total_bsdgs": int(bsdg["total"] or 0),
                "enabled_bsdgs": int(bsdg["enabled"] or 0),
                "missing_bsdgs": int(bsdg["missing"] or 0),
                "total_files": int(current["total_files"] or 0),
            }

    def list_files(self, limit: int = 5000) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT f.*, b.name AS bsdg_name
                FROM files f
                JOIN bsdgs b ON b.id = f.bsdg_id
                ORDER BY f.last_seen_at DESC, b.name, f.relative_path
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    def list_files_for_run(self, run_id: int) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT f.*, b.name AS bsdg_name
                FROM files f
                JOIN bsdgs b ON b.id = f.bsdg_id
                WHERE f.last_seen_run_id = ?
                ORDER BY b.name, f.relative_path
                """,
                (run_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def list_layers_for_run(self, run_id: int) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT b.name AS bsdg_name, f.relative_path, f.file_name,
                       l.*
                FROM layers l
                JOIN files f ON f.id = l.file_id
                JOIN bsdgs b ON b.id = f.bsdg_id
                WHERE f.last_seen_run_id = ?
                ORDER BY b.name, f.relative_path, l.table_name
                """,
                (run_id,),
            ).fetchall()
            return [dict(row) for row in rows]

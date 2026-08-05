from __future__ import annotations

import json
import logging
import threading
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from .config import ConfigManager
from .gpkg_validator import GeoPackageValidator
from .inventory import InventoryDB
from .models import (
    AppConfig,
    AvailabilityStatus,
    BsdgConfig,
    BsdgScanSummary,
    ChangeStatus,
    FileScanResult,
    ScanSummary,
    ValidationResult,
    ValidationStatus,
)
from .onedrive import inspect_file_availability
from .reports import ReportWriter
from .scanner import (
    calculate_sha256,
    category_from_relative_path,
    datetime_iso_from_ns,
    discover_gpkg_files,
)

LOGGER = logging.getLogger(__name__)
ProgressCallback = Callable[[dict[str, Any]], None]


class VerificationService:
    def __init__(
        self,
        config_manager: ConfigManager | None = None,
        inventory: InventoryDB | None = None,
        report_writer: ReportWriter | None = None,
    ) -> None:
        self.config_manager = config_manager or ConfigManager()
        self.inventory = inventory or InventoryDB()
        self.report_writer = report_writer or ReportWriter()

    def run_scan(
        self,
        selected_bsdg_ids: set[str] | None = None,
        mode: str = "MANUAL",
        progress_callback: ProgressCallback | None = None,
        cancel_event: threading.Event | None = None,
        log_path: str = "",
        report_output_dir: str | Path | None = None,
    ) -> ScanSummary:
        config = self.config_manager.load()
        candidates = [item for item in config.bsdgs if item.enabled]
        if selected_bsdg_ids is not None:
            candidates = [item for item in candidates if item.id in selected_bsdg_ids]

        started = datetime.now().astimezone()
        started_iso = started.isoformat(timespec="seconds")
        run_id = self.inventory.start_run(started_iso, mode)
        LOGGER.info("Iniciando varredura %s. BSDGs selecionadas: %s", run_id, len(candidates))

        bsdg_summaries: list[BsdgScanSummary] = []
        work_items: list[tuple[BsdgConfig, int, Path, Path, dict[str, Any] | None]] = []
        seen_by_bsdg: dict[int, set[str]] = {}
        bsdg_db_ids: dict[str, int] = {}

        for bsdg in candidates:
            root = Path(bsdg.local_path).expanduser() if bsdg.local_path else Path()
            folder_exists = bool(bsdg.local_path) and root.exists() and root.is_dir()
            status = "DISPONÍVEL" if folder_exists else "PASTA NÃO ENCONTRADA"
            message = "" if folder_exists else "A pasta local não foi configurada ou não está acessível."
            db_id = self.inventory.upsert_bsdg(
                bsdg.id,
                bsdg.name,
                bsdg.local_path,
                bsdg.enabled,
                bsdg.recursive,
                started_iso,
                status,
                message,
            )
            bsdg_db_ids[bsdg.id] = db_id
            seen_by_bsdg[db_id] = set()
            summary = BsdgScanSummary(
                bsdg_id=bsdg.id,
                bsdg_name=bsdg.name,
                root_path=bsdg.local_path,
                enabled=bsdg.enabled,
                folder_exists=folder_exists,
                status=status,
                message=message,
            )
            bsdg_summaries.append(summary)
            if not folder_exists:
                continue

            files = discover_gpkg_files(root, recursive=bsdg.recursive)
            summary.discovered_files = len(files)
            if not files:
                summary.status = "ATENÇÃO: NENHUM GPKG LOCALIZADO"
                summary.message = (
                    "A pasta existe, mas nenhum arquivo .gpkg foi localizado. "
                    "Confirme se 'Subpastas' está marcado como Sim e, no OneDrive, "
                    "marque a pasta monitorada como 'Sempre manter neste dispositivo'."
                )
                LOGGER.warning("%s: %s", bsdg.name, summary.message)
            for path in files:
                relative_path = path.relative_to(root)
                previous = self.inventory.get_previous_file(db_id, str(relative_path))
                work_items.append((bsdg, db_id, root, path, previous))

        total_work = len(work_items)
        if progress_callback:
            progress_callback({"current": 0, "total": total_work, "message": "Arquivos localizados."})

        results: list[FileScanResult] = []
        errors: list[str] = []
        processed = 0

        with ThreadPoolExecutor(max_workers=config.scan.max_workers, thread_name_prefix="gpkg") as executor:
            future_map: dict[Future[FileScanResult], tuple[BsdgConfig, int, Path]] = {}
            for bsdg, db_id, root, path, previous in work_items:
                if cancel_event and cancel_event.is_set():
                    break
                future = executor.submit(self._process_file, config, bsdg, root, path, previous)
                future_map[future] = (bsdg, db_id, path)

            for future in as_completed(future_map):
                bsdg, db_id, path = future_map[future]
                if cancel_event and cancel_event.is_set():
                    break
                try:
                    result = future.result()
                    results.append(result)
                    seen_by_bsdg[db_id].add(result.relative_path)
                    self.inventory.upsert_file(db_id, result, run_id, datetime.now().astimezone().isoformat(timespec="seconds"))
                except Exception as exc:  # proteção do lote; detalhes seguem no log
                    LOGGER.exception("Falha inesperada ao processar %s", path)
                    errors.append(f"{path}: {exc}")
                processed += 1
                if progress_callback:
                    progress_callback(
                        {
                            "current": processed,
                            "total": total_work,
                            "message": f"Verificado: {path.name}",
                            "bsdg": bsdg.name,
                            "file": str(path),
                        }
                    )

        removed_total = 0
        completed_iso = datetime.now().astimezone().isoformat(timespec="seconds")
        for bsdg in candidates:
            db_id = bsdg_db_ids[bsdg.id]
            summary = next(item for item in bsdg_summaries if item.bsdg_id == bsdg.id)
            if not summary.folder_exists:
                continue
            removed = self.inventory.mark_removed_files(
                db_id,
                seen_by_bsdg[db_id],
                run_id,
                completed_iso,
            )
            summary.removed_files = removed
            removed_total += removed
            final_status = (
                "ATENÇÃO: NENHUM GPKG LOCALIZADO"
                if summary.discovered_files == 0
                else "VERIFICAÇÃO CONCLUÍDA"
            )
            final_message = summary.message or f"{summary.discovered_files} arquivo(s) localizado(s)."
            self.inventory.update_bsdg_status(
                bsdg.id,
                final_status,
                final_message,
                completed_iso,
            )

        summary = self._build_summary(
            run_id=run_id,
            started_at=started_iso,
            completed_at=completed_iso,
            mode=mode,
            candidates=candidates,
            bsdg_summaries=bsdg_summaries,
            results=results,
            removed_total=removed_total,
            errors=errors,
            log_path=log_path,
            cancelled=bool(cancel_event and cancel_event.is_set()),
        )

        self.inventory.finish_run(summary)
        file_rows = self.inventory.list_files_for_run(run_id)
        layer_rows = self.inventory.list_layers_for_run(run_id)
        report_writer = (
            ReportWriter(Path(report_output_dir))
            if report_output_dir is not None
            else self.report_writer
        )
        report_paths = report_writer.write(
            summary,
            file_rows,
            layer_rows,
            csv_enabled=config.reports.csv_enabled,
            json_enabled=config.reports.json_enabled,
        )
        summary.report_paths = [str(path) for path in report_paths]
        self.inventory.finish_run(summary)
        LOGGER.info("Varredura %s concluída: %s", run_id, summary.outcome)
        return summary

    @staticmethod
    def _process_file(
        config: AppConfig,
        bsdg: BsdgConfig,
        root: Path,
        path: Path,
        previous: dict[str, Any] | None,
    ) -> FileScanResult:
        relative = path.relative_to(root)
        availability = inspect_file_availability(path)

        try:
            stat_result = path.stat()
            size_bytes = int(stat_result.st_size)
            mtime_ns = int(stat_result.st_mtime_ns)
            modified_iso = datetime_iso_from_ns(mtime_ns)
        except OSError as exc:
            validation = ValidationResult(
                status=ValidationStatus.ERROR,
                is_sqlite=False,
                is_geopackage=False,
                issues=["Não foi possível consultar o arquivo."],
                error_message=str(exc),
            )
            return FileScanResult(
                bsdg_id=bsdg.id,
                bsdg_name=bsdg.name,
                root_path=str(root),
                absolute_path=str(path),
                relative_path=str(relative),
                file_name=path.name,
                category=category_from_relative_path(relative),
                size_bytes=0,
                mtime_ns=0,
                modified_iso="",
                sha256="",
                change_status=ChangeStatus.UNKNOWN,
                availability_status=AvailabilityStatus.INACCESSIBLE,
                validation=validation,
                one_drive_attributes=availability.attributes,
                message=availability.message or str(exc),
            )

        if previous is None:
            change_status = ChangeStatus.NEW
        elif int(previous.get("size_bytes", -1)) != size_bytes or int(previous.get("mtime_ns", -1)) != mtime_ns:
            change_status = ChangeStatus.MODIFIED
        else:
            change_status = ChangeStatus.UNCHANGED

        if availability.status in {AvailabilityStatus.ONLINE_ONLY, AvailabilityStatus.PARTIAL}:
            validation = ValidationResult(
                status=ValidationStatus.NOT_VALIDATED,
                is_sqlite=False,
                is_geopackage=False,
                file_size=size_bytes,
                warnings=["Validação não executada para evitar o download automático do arquivo."],
            )
            return FileScanResult(
                bsdg_id=bsdg.id,
                bsdg_name=bsdg.name,
                root_path=str(root),
                absolute_path=str(path),
                relative_path=str(relative),
                file_name=path.name,
                category=category_from_relative_path(relative),
                size_bytes=size_bytes,
                mtime_ns=mtime_ns,
                modified_iso=modified_iso,
                sha256=str(previous.get("sha256", "")) if previous else "",
                change_status=change_status,
                availability_status=availability.status,
                validation=validation,
                one_drive_attributes=availability.attributes,
                message=availability.message,
            )

        validation: ValidationResult
        should_validate = (
            previous is None
            or change_status != ChangeStatus.UNCHANGED
            or config.scan.validate_unchanged
        )
        if should_validate:
            validator = GeoPackageValidator(
                run_quick_check=config.scan.run_quick_check,
                count_features=config.scan.count_features,
                timeout_seconds=config.scan.sqlite_timeout_seconds,
            )
            validation = validator.validate(path)
        else:
            try:
                validation = ValidationResult.from_dict(
                    json.loads(str(previous.get("validation_json", "{}")))
                )
                if validation.status in {ValidationStatus.VALID, ValidationStatus.REUSED}:
                    validation.status = ValidationStatus.REUSED
            except (ValueError, TypeError, json.JSONDecodeError):
                validation = ValidationResult(
                    status=ValidationStatus.NOT_VALIDATED,
                    is_sqlite=False,
                    is_geopackage=False,
                    warnings=["Não foi possível reutilizar a validação anterior."],
                )

        sha256 = str(previous.get("sha256", "")) if previous else ""
        hash_mode = config.scan.hash_mode.lower()
        should_hash = hash_mode == "always" or (
            hash_mode == "changed" and change_status in {ChangeStatus.NEW, ChangeStatus.MODIFIED}
        )
        if should_hash:
            try:
                sha256 = calculate_sha256(path)
            except (PermissionError, OSError) as exc:
                validation.warnings.append(f"Não foi possível calcular SHA-256: {exc}")

        return FileScanResult(
            bsdg_id=bsdg.id,
            bsdg_name=bsdg.name,
            root_path=str(root),
            absolute_path=str(path),
            relative_path=str(relative),
            file_name=path.name,
            category=category_from_relative_path(relative),
            size_bytes=size_bytes,
            mtime_ns=mtime_ns,
            modified_iso=modified_iso,
            sha256=sha256,
            change_status=change_status,
            availability_status=availability.status,
            validation=validation,
            one_drive_attributes=availability.attributes,
            message=availability.message,
        )

    @staticmethod
    def _build_summary(
        run_id: int,
        started_at: str,
        completed_at: str,
        mode: str,
        candidates: list[BsdgConfig],
        bsdg_summaries: list[BsdgScanSummary],
        results: list[FileScanResult],
        removed_total: int,
        errors: list[str],
        log_path: str,
        cancelled: bool,
    ) -> ScanSummary:
        outcome = "CANCELADA" if cancelled else ("CONCLUÍDA COM ALERTAS" if errors else "CONCLUÍDA")
        return ScanSummary(
            run_id=run_id,
            started_at=started_at,
            completed_at=completed_at,
            mode=mode,
            outcome=outcome,
            total_bsdgs=len(candidates),
            scanned_bsdgs=sum(item.folder_exists for item in bsdg_summaries),
            missing_bsdgs=sum(not item.folder_exists for item in bsdg_summaries),
            total_files=len(results),
            new_files=sum(item.change_status == ChangeStatus.NEW for item in results),
            modified_files=sum(item.change_status == ChangeStatus.MODIFIED for item in results),
            unchanged_files=sum(item.change_status == ChangeStatus.UNCHANGED for item in results),
            removed_files=removed_total,
            valid_files=sum(item.validation.status in {ValidationStatus.VALID, ValidationStatus.REUSED} for item in results),
            invalid_files=sum(item.validation.status in {ValidationStatus.INVALID, ValidationStatus.ERROR} for item in results),
            online_only_files=sum(item.availability_status in {AvailabilityStatus.ONLINE_ONLY, AvailabilityStatus.PARTIAL} for item in results),
            inaccessible_files=sum(item.availability_status == AvailabilityStatus.INACCESSIBLE for item in results),
            bsdg_summaries=bsdg_summaries,
            log_path=log_path,
            errors=errors,
        )

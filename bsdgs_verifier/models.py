from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class ChangeStatus(str, Enum):
    NEW = "NOVO"
    MODIFIED = "MODIFICADO"
    UNCHANGED = "SEM ALTERAÇÃO"
    REMOVED = "REMOVIDO"
    UNKNOWN = "NÃO CLASSIFICADO"


class AvailabilityStatus(str, Enum):
    LOCAL = "DISPONÍVEL LOCALMENTE"
    ALWAYS_AVAILABLE = "SEMPRE DISPONÍVEL"
    ONLINE_ONLY = "SOMENTE NA NUVEM"
    PARTIAL = "PARCIALMENTE DISPONÍVEL"
    INACCESSIBLE = "INACESSÍVEL"
    UNKNOWN = "DESCONHECIDO"


class ValidationStatus(str, Enum):
    VALID = "VÁLIDO"
    INVALID = "INVÁLIDO"
    NOT_VALIDATED = "NÃO VALIDADO"
    REUSED = "VALIDAÇÃO REUTILIZADA"
    ERROR = "ERRO DE LEITURA"


@dataclass(slots=True)
class BsdgConfig:
    id: str
    name: str
    local_path: str = ""
    enabled: bool = False
    recursive: bool = True
    notes: str = ""
    needs_name_confirmation: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BsdgConfig":
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            local_path=str(data.get("local_path", "")),
            enabled=bool(data.get("enabled", False)),
            recursive=bool(data.get("recursive", True)),
            notes=str(data.get("notes", "")),
            needs_name_confirmation=bool(data.get("needs_name_confirmation", False)),
        )


@dataclass(slots=True)
class ScheduleConfig:
    enabled: bool = False
    day: str = "FRI"
    time: str = "18:00"
    scan_all_enabled: bool = True
    notify_after_run: bool = True
    reports_output_dir: str = ""
    logs_output_dir: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScheduleConfig":
        return cls(
            enabled=bool(data.get("enabled", False)),
            day=str(data.get("day", "FRI")).upper(),
            time=str(data.get("time", "18:00")),
            scan_all_enabled=bool(data.get("scan_all_enabled", True)),
            notify_after_run=bool(data.get("notify_after_run", True)),
            reports_output_dir=str(data.get("reports_output_dir", "")),
            logs_output_dir=str(data.get("logs_output_dir", "")),
        )


@dataclass(slots=True)
class ScanSettings:
    max_workers: int = 2
    hash_mode: str = "changed"  # never | changed | always
    validate_unchanged: bool = False
    run_quick_check: bool = True
    count_features: bool = False
    sqlite_timeout_seconds: int = 10

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScanSettings":
        return cls(
            max_workers=max(1, min(8, int(data.get("max_workers", 2)))),
            hash_mode=str(data.get("hash_mode", "changed")),
            validate_unchanged=bool(data.get("validate_unchanged", False)),
            run_quick_check=bool(data.get("run_quick_check", True)),
            count_features=bool(data.get("count_features", False)),
            sqlite_timeout_seconds=max(1, int(data.get("sqlite_timeout_seconds", 10))),
        )


@dataclass(slots=True)
class ReportSettings:
    csv_enabled: bool = True
    json_enabled: bool = True
    log_enabled: bool = True
    reports_output_dir: str = ""
    logs_output_dir: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReportSettings":
        return cls(
            csv_enabled=bool(data.get("csv_enabled", True)),
            json_enabled=bool(data.get("json_enabled", True)),
            log_enabled=bool(data.get("log_enabled", True)),
            reports_output_dir=str(data.get("reports_output_dir", "")),
            logs_output_dir=str(data.get("logs_output_dir", "")),
        )


@dataclass(slots=True)
class AppConfig:
    version: int
    bsdgs: list[BsdgConfig]
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    scan: ScanSettings = field(default_factory=ScanSettings)
    reports: ReportSettings = field(default_factory=ReportSettings)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppConfig":
        return cls(
            version=int(data.get("version", 1)),
            bsdgs=[BsdgConfig.from_dict(item) for item in data.get("bsdgs", [])],
            schedule=ScheduleConfig.from_dict(data.get("schedule", {})),
            scan=ScanSettings.from_dict(data.get("scan", {})),
            reports=ReportSettings.from_dict(data.get("reports", {})),
        )


@dataclass(slots=True)
class LayerValidation:
    table_name: str
    data_type: str
    identifier: str | None = None
    description: str | None = None
    geometry_column: str | None = None
    geometry_type: str | None = None
    srs_id: int | None = None
    z: int | None = None
    m: int | None = None
    feature_count: int | None = None
    table_exists: bool = False
    geometry_column_exists: bool | None = None
    srs_exists: bool | None = None
    valid: bool = True
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LayerValidation":
        return cls(**data)


@dataclass(slots=True)
class ValidationResult:
    status: ValidationStatus
    is_sqlite: bool
    is_geopackage: bool
    quick_check_ok: bool | None = None
    file_size: int = 0
    layer_count: int = 0
    feature_layer_count: int = 0
    tile_layer_count: int = 0
    attribute_layer_count: int = 0
    layers: list[LayerValidation] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ValidationResult":
        payload = dict(data)
        payload["status"] = ValidationStatus(payload.get("status", ValidationStatus.NOT_VALIDATED.value))
        payload["layers"] = [LayerValidation.from_dict(item) for item in payload.get("layers", [])]
        return cls(**payload)


@dataclass(slots=True)
class FileScanResult:
    bsdg_id: str
    bsdg_name: str
    root_path: str
    absolute_path: str
    relative_path: str
    file_name: str
    category: str
    size_bytes: int
    mtime_ns: int
    modified_iso: str
    sha256: str
    change_status: ChangeStatus
    availability_status: AvailabilityStatus
    validation: ValidationResult
    one_drive_attributes: int = 0
    message: str = ""

    @property
    def display_status(self) -> str:
        if self.availability_status in {AvailabilityStatus.ONLINE_ONLY, AvailabilityStatus.PARTIAL}:
            return self.availability_status.value
        if self.availability_status == AvailabilityStatus.INACCESSIBLE:
            return AvailabilityStatus.INACCESSIBLE.value
        if self.validation.status in {ValidationStatus.INVALID, ValidationStatus.ERROR}:
            return self.validation.status.value
        return self.change_status.value

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["change_status"] = self.change_status.value
        data["availability_status"] = self.availability_status.value
        data["validation"] = self.validation.to_dict()
        data["display_status"] = self.display_status
        return data


@dataclass(slots=True)
class BsdgScanSummary:
    bsdg_id: str
    bsdg_name: str
    root_path: str
    enabled: bool
    folder_exists: bool
    discovered_files: int = 0
    removed_files: int = 0
    status: str = ""
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ScanSummary:
    run_id: int
    started_at: str
    completed_at: str
    mode: str
    outcome: str
    total_bsdgs: int
    scanned_bsdgs: int
    missing_bsdgs: int
    total_files: int
    new_files: int
    modified_files: int
    unchanged_files: int
    removed_files: int
    valid_files: int
    invalid_files: int
    online_only_files: int
    inaccessible_files: int
    bsdg_summaries: list[BsdgScanSummary] = field(default_factory=list)
    report_paths: list[str] = field(default_factory=list)
    log_path: str = ""
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

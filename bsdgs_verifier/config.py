from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Iterable

from .constants import CONFIG_VERSION
from .models import AppConfig, BsdgConfig
from .paths import config_path, default_litoral_path


DEFAULT_BSDG_NAMES: list[tuple[str, bool]] = [
    ("BSDG_AdaptaUCs", False),
    ("BSDG_ANA", False),
    ("BSDG_Baias", False),
    ("BSDG_CEP", False),
    ("BSDG_ComunidadesNoMapa", False),
    ("BSDG_FGB", False),
    ("BSDG_Guaraguacu", False),
    ("BSDG_ICNT_Wetscape", False),
    ("BSDG_Jacarei", False),
    ("BSDG_Jornadas", False),
    ("BSDG_Lancinha", False),
    ("BSDG_Litoral", False),
    ("BSDG_MARBRASIL", False),
    ("BSDG_NGI-Norte", False),
    ("BSDG_NGI-Sul", False),
    ("BSDG_Paranagua", False),
    ("BDG_PRAD_Litoral", False),
    ("BSDG_TAC-Mangue", False),
    ("BSDG_Internacionalização", False),

]


LEGACY_BSDG_NAME_REPLACEMENTS = {
    "BSDG_ComunidadesN… (confirmar nome completo)": "BSDG_ComunidadesNoMapa",
    "BSDG_Internacionaliza… (confirmar nome completo)": "BSDG_Internacionalização",
}


def _stable_id(name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-").lower()
    return slug or uuid.uuid4().hex


def default_config() -> AppConfig:
    litoral_path = default_litoral_path()
    items: list[BsdgConfig] = []
    for name, needs_confirmation in DEFAULT_BSDG_NAMES:
        is_litoral = name == "BSDG_Litoral"
        items.append(
            BsdgConfig(
                id=_stable_id(name),
                name=name,
                local_path=str(litoral_path) if is_litoral else "",
                enabled=is_litoral,
                recursive=True,
                notes=(
                    "Caminho inicial informado para a prova de conceito."
                    if is_litoral
                    else ""
                ),
                needs_name_confirmation=needs_confirmation,
            )
        )
    return AppConfig(version=CONFIG_VERSION, bsdgs=items)


class ConfigManager:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or config_path()

    def load(self) -> AppConfig:
        if not self.path.exists():
            config = default_config()
            self.save(config)
            return config
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            config = AppConfig.from_dict(data)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            backup = self.path.with_suffix(".json.invalido")
            try:
                self.path.replace(backup)
            except OSError:
                pass
            config = default_config()
            self.save(config)
        migrated = self._migrate(config)
        self._normalize(config)
        if migrated:
            self.save(config)
        return config

    def save(self, config: AppConfig) -> None:
        self._normalize(config)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(config.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp.replace(self.path)

    @staticmethod
    def _migrate(config: AppConfig) -> bool:
        changed = config.version != CONFIG_VERSION
        for item in config.bsdgs:
            replacement = LEGACY_BSDG_NAME_REPLACEMENTS.get(item.name)
            if replacement is None and item.name.startswith("BSDG_ComunidadesN"):
                replacement = "BSDG_ComunidadesNoMapa"
            if replacement is None and item.name.startswith("BSDG_Internacionaliza"):
                replacement = "BSDG_Internacionalização"
            if replacement and item.name != replacement:
                item.name = replacement
                item.needs_name_confirmation = False
                changed = True
        return changed

    @staticmethod
    def _normalize(config: AppConfig) -> None:
        config.version = CONFIG_VERSION
        seen: set[str] = set()
        for item in config.bsdgs:
            if not item.id or item.id in seen:
                item.id = f"{_stable_id(item.name)}-{uuid.uuid4().hex[:8]}"
            seen.add(item.id)
            item.local_path = str(Path(item.local_path).expanduser()) if item.local_path else ""
        config.reports.reports_output_dir = (
            str(Path(config.reports.reports_output_dir).expanduser())
            if config.reports.reports_output_dir
            else ""
        )
        config.reports.logs_output_dir = (
            str(Path(config.reports.logs_output_dir).expanduser())
            if config.reports.logs_output_dir
            else ""
        )
        config.schedule.reports_output_dir = (
            str(Path(config.schedule.reports_output_dir).expanduser())
            if config.schedule.reports_output_dir
            else ""
        )
        config.schedule.logs_output_dir = (
            str(Path(config.schedule.logs_output_dir).expanduser())
            if config.schedule.logs_output_dir
            else ""
        )

    def replace_bsdgs(self, config: AppConfig, bsdgs: Iterable[BsdgConfig]) -> None:
        config.bsdgs = list(bsdgs)
        self.save(config)

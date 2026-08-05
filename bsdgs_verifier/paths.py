from __future__ import annotations

import os
import sys
from pathlib import Path

from .constants import APP_SLUG


def resource_path(relative: str | Path) -> Path:
    """Resolve recursos tanto no código-fonte quanto no EXE one-file do PyInstaller."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base / Path(relative)


def app_data_dir() -> Path:
    override = os.environ.get("BSDGS_VERIFIER_HOME")
    if override:
        base = Path(override).expanduser()
    elif os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / APP_SLUG
    else:
        base = Path.home() / ".local" / "share" / APP_SLUG
    base.mkdir(parents=True, exist_ok=True)
    return base


def config_dir() -> Path:
    path = app_data_dir() / "config"
    path.mkdir(parents=True, exist_ok=True)
    return path


def database_dir() -> Path:
    path = app_data_dir() / "database"
    path.mkdir(parents=True, exist_ok=True)
    return path


def reports_dir() -> Path:
    path = app_data_dir() / "reports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def logs_dir() -> Path:
    path = app_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    return config_dir() / "bsdgs.json"


def database_path() -> Path:
    return database_dir() / "inventario_bsdgs.sqlite"


def default_litoral_path() -> Path:
    return (
        Path.home()
        / "ufpr.br"
        / "Banco de Dados Geográficos do LAGEAMB - BDG_Litoral"
        / "dadosGeoespaciais"
        / "geopackage"
    )

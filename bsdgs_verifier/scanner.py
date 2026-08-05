from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

LOGGER = logging.getLogger(__name__)


def discover_gpkg_files(root: Path, recursive: bool = True) -> list[Path]:
    """Localiza GeoPackages sem exigir que o Windows hidrate o conteúdo do arquivo.

    A enumeração usa ``os.walk``/``os.scandir`` e compara a extensão sem
    diferenciar maiúsculas e minúsculas. O caminho é incluído mesmo quando o
    arquivo é um placeholder do OneDrive; a disponibilidade local será avaliada
    posteriormente pelo módulo ``onedrive``.
    """
    if not root.exists() or not root.is_dir():
        return []

    files: list[Path] = []

    def on_walk_error(error: OSError) -> None:
        LOGGER.warning("Não foi possível percorrer uma pasta sincronizada: %s", error)

    if recursive:
        for current_root, _dirs, names in os.walk(root, onerror=on_walk_error):
            current = Path(current_root)
            for name in names:
                if Path(name).suffix.casefold() == ".gpkg":
                    files.append(current / name)
    else:
        try:
            with os.scandir(root) as entries:
                for entry in entries:
                    if entry.name.casefold().endswith(".gpkg"):
                        files.append(Path(entry.path))
        except OSError as exc:
            LOGGER.warning("Não foi possível listar a pasta %s: %s", root, exc)

    unique = {str(path).casefold(): path for path in files}
    return sorted(unique.values(), key=lambda item: str(item).casefold())


def calculate_sha256(path: Path, chunk_size: int = 4 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def category_from_relative_path(relative_path: Path) -> str:
    if len(relative_path.parts) > 1:
        return relative_path.parts[0]
    stem = relative_path.stem
    return stem.split("_", 1)[0] if "_" in stem else "Sem categoria"


def datetime_iso_from_ns(timestamp_ns: int) -> str:
    return datetime.fromtimestamp(timestamp_ns / 1_000_000_000, tz=timezone.utc).astimezone().isoformat(timespec="seconds")

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .constants import (
    FILE_ATTRIBUTE_OFFLINE,
    FILE_ATTRIBUTE_PINNED,
    FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS,
    FILE_ATTRIBUTE_RECALL_ON_OPEN,
)
from .models import AvailabilityStatus


@dataclass(slots=True)
class OneDriveInspection:
    status: AvailabilityStatus
    attributes: int = 0
    message: str = ""


def inspect_file_availability(path: Path) -> OneDriveInspection:
    try:
        stat_result = path.stat()
    except PermissionError as exc:
        return OneDriveInspection(
            AvailabilityStatus.INACCESSIBLE,
            message=f"Sem permissão para consultar o arquivo: {exc}",
        )
    except OSError as exc:
        return OneDriveInspection(
            AvailabilityStatus.INACCESSIBLE,
            message=f"Não foi possível consultar o arquivo: {exc}",
        )

    attributes = int(getattr(stat_result, "st_file_attributes", 0))
    if os.name != "nt":
        return OneDriveInspection(AvailabilityStatus.LOCAL, attributes)

    if attributes & FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS:
        return OneDriveInspection(
            AvailabilityStatus.ONLINE_ONLY,
            attributes,
            "O conteúdo será recuperado da nuvem quando for acessado.",
        )
    if attributes & FILE_ATTRIBUTE_OFFLINE:
        return OneDriveInspection(
            AvailabilityStatus.ONLINE_ONLY,
            attributes,
            "O arquivo está marcado como offline/somente na nuvem.",
        )
    if attributes & FILE_ATTRIBUTE_RECALL_ON_OPEN:
        return OneDriveInspection(
            AvailabilityStatus.PARTIAL,
            attributes,
            "O arquivo não está integralmente materializado localmente.",
        )
    if attributes & FILE_ATTRIBUTE_PINNED:
        return OneDriveInspection(AvailabilityStatus.ALWAYS_AVAILABLE, attributes)
    return OneDriveInspection(AvailabilityStatus.LOCAL, attributes)

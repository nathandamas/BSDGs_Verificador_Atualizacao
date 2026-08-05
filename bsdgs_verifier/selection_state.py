from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .paths import app_data_dir


STATE_FILE_NAME = "selection_state.json"


@dataclass(slots=True)
class SelectionState:
    """Estado persistente da seleção feita na interface gráfica.

    ``selected_bsdg_id`` representa a BSDG atualmente selecionada pelo usuário.
    ``scheduled_bsdg_id`` registra a BSDG efetivamente vinculada à tarefa do
    Agendador de Tarefas do Windows. Os dois valores são separados porque o
    usuário pode mudar a seleção atual sem reinstalar imediatamente a tarefa.
    """

    selected_bsdg_id: str = ""
    scheduled_bsdg_id: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SelectionState":
        return cls(
            selected_bsdg_id=str(data.get("selected_bsdg_id", "")),
            scheduled_bsdg_id=str(data.get("scheduled_bsdg_id", "")),
        )


class SelectionStateManager:
    """Lê e grava o estado de seleção em um pequeno arquivo JSON local."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (app_data_dir() / STATE_FILE_NAME)

    def load(self) -> SelectionState:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return SelectionState()
            return SelectionState.from_dict(data)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return SelectionState()

    def save(self, state: SelectionState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary_path.write_text(
            json.dumps(asdict(state), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temporary_path, self.path)

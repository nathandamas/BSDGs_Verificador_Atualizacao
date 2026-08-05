from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .constants import DAY_NAMES_BY_CODE, TASK_NAME


@dataclass(slots=True)
class SchedulerResult:
    success: bool
    message: str
    raw_output: str = ""


class WindowsScheduler:
    def __init__(self, task_name: str = TASK_NAME) -> None:
        self.task_name = task_name

    @staticmethod
    def is_supported() -> bool:
        return os.name == "nt"

    def install_weekly(
        self,
        day_code: str,
        time_hhmm: str,
        selected_bsdg_id: str | None = None,
    ) -> SchedulerResult:
        if not self.is_supported():
            return SchedulerResult(False, "O agendamento automático está disponível somente no Windows.")
        if day_code not in DAY_NAMES_BY_CODE:
            return SchedulerResult(False, f"Dia da semana inválido: {day_code}")
        if not self._valid_time(time_hhmm):
            return SchedulerResult(False, f"Horário inválido: {time_hhmm}")

        task_run = self._task_run_command(selected_bsdg_id)
        command = [
            "schtasks",
            "/Create",
            "/TN",
            self.task_name,
            "/TR",
            task_run,
            "/SC",
            "WEEKLY",
            "/D",
            day_code,
            "/ST",
            time_hhmm,
            "/IT",
            "/RL",
            "LIMITED",
            "/F",
        ]
        return self._run(command, "Agendamento semanal instalado com sucesso.")

    def remove(self) -> SchedulerResult:
        if not self.is_supported():
            return SchedulerResult(False, "O Agendador de Tarefas não está disponível neste sistema.")
        return self._run(
            ["schtasks", "/Delete", "/TN", self.task_name, "/F"],
            "Agendamento removido com sucesso.",
        )

    def query(self) -> SchedulerResult:
        if not self.is_supported():
            return SchedulerResult(False, "O Agendador de Tarefas não está disponível neste sistema.")
        return self._run(
            ["schtasks", "/Query", "/TN", self.task_name, "/FO", "LIST", "/V"],
            "Agendamento localizado.",
        )

    def _task_run_command(self, selected_bsdg_id: str | None = None) -> str:
        command_parts: list[str] = []
        executable = Path(sys.executable).resolve()
        command_parts.append(str(executable))

        if not getattr(sys, "frozen", False):
            project_root = Path(__file__).resolve().parents[1]
            command_parts.append(str(project_root / "main.py"))

        # --scan-all-silent mantém o comportamento sem interface, usa os
        # diretórios de saída do agendamento e define o modo como AGENDADA.
        command_parts.append("--scan-all-silent")
        if selected_bsdg_id:
            command_parts.extend(["--scan-bsdg", selected_bsdg_id])

        return subprocess.list2cmdline(command_parts)

    @staticmethod
    def _valid_time(value: str) -> bool:
        try:
            hour_text, minute_text = value.split(":", 1)
            hour = int(hour_text)
            minute = int(minute_text)
            return 0 <= hour <= 23 and 0 <= minute <= 59
        except (ValueError, AttributeError):
            return False

    @staticmethod
    def _run(command: list[str], success_message: str) -> SchedulerResult:
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="mbcs" if os.name == "nt" else "utf-8",
                errors="replace",
                check=False,
                creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0),
            )
        except OSError as exc:
            return SchedulerResult(False, f"Não foi possível executar o Agendador de Tarefas: {exc}")

        output = "\n".join(part for part in [completed.stdout.strip(), completed.stderr.strip()] if part)
        if completed.returncode == 0:
            return SchedulerResult(True, success_message, output)
        return SchedulerResult(
            False,
            "O Windows não conseguiu concluir a operação de agendamento. "
            "Consulte os detalhes técnicos ou execute a aplicação com uma conta autorizada.",
            output,
        )

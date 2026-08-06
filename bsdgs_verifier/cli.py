from __future__ import annotations

import argparse
import json
import logging
import platform
import sys
import traceback
from datetime import datetime
from pathlib import Path

from .config import ConfigManager
from .logging_setup import configure_logging
from .scheduler import WindowsScheduler
from .service import VerificationService
from .paths import logs_dir, reports_dir

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="BSDGs — Verificador de Atualização")
    parser.add_argument("--scan-all-silent", action="store_true", help="Executa todas as BSDGs ativas sem abrir a interface.")
    parser.add_argument("--scan-bsdg", action="append", default=[], help="Nome ou identificador de uma BSDG ativa a verificar.")
    parser.add_argument("--install-schedule", action="store_true", help="Instala o agendamento semanal.")
    parser.add_argument("--remove-schedule", action="store_true", help="Remove o agendamento semanal.")
    parser.add_argument("--day", default="FRI", help="Dia do agendamento: MON..SUN.")
    parser.add_argument("--time", default="18:00", help="Horário HH:MM.")
    parser.add_argument("--show-data-dir", action="store_true", help="Mostra a pasta de dados da aplicação.")
    parser.add_argument(
        "--self-test-file",
        default="",
        help="Executa um teste de inicialização completa e grava o resultado em JSON.",
    )
    return parser


def _run_self_test(output_file: str) -> int:
    path = Path(output_file).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {
        "timestamp": datetime.now().astimezone().isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "executable": sys.executable,
        "frozen": bool(getattr(sys, "frozen", False)),
    }
    app = None
    try:
        from .deferred_gui import DeferredApplication

        app = DeferredApplication(start_hidden=True)
        completed = app.wait_for_startup(timeout_seconds=25.0)
        app.update_idletasks()

        payload.update(
            {
                "startup_complete": app.startup_complete,
                "startup_error": str(app.startup_error) if app.startup_error else "",
                "state": app.state(),
                "mapped": bool(app.winfo_ismapped()),
                "viewable": bool(app.winfo_viewable()),
                "window_id": int(app.winfo_id()),
                "geometry": app.winfo_geometry(),
            }
        )

        if not completed:
            if app.startup_error is not None:
                raise RuntimeError(
                    f"Falha na inicialização adiada: {app.startup_error}"
                )
            raise TimeoutError(
                "A inicialização adiada não terminou dentro de 25 segundos."
            )

        payload["status"] = "OK"
        payload["message"] = (
            "A interface e o inventário local foram inicializados com sucesso."
        )
        return_code = 0
    except BaseException as error:
        payload["status"] = "ERROR"
        payload["message"] = str(error)
        payload["traceback"] = "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )
        return_code = 1
    finally:
        if app is not None:
            try:
                app.destroy()
            except Exception:
                pass
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return return_code


def run_cli(args: argparse.Namespace) -> int:
    if args.self_test_file:
        return _run_self_test(args.self_test_file)

    if args.show_data_dir:
        from .paths import app_data_dir

        print(app_data_dir())
        return 0

    if args.install_schedule:
        result = WindowsScheduler().install_weekly(args.day.upper(), args.time)
        print(result.message)
        if result.raw_output:
            print(result.raw_output)
        return 0 if result.success else 1

    if args.remove_schedule:
        result = WindowsScheduler().remove()
        print(result.message)
        if result.raw_output:
            print(result.raw_output)
        return 0 if result.success else 1

    if args.scan_all_silent or args.scan_bsdg:
        config = ConfigManager().load()
        if args.scan_all_silent:
            configured_logs = (
                Path(config.schedule.logs_output_dir)
                if config.schedule.logs_output_dir
                else logs_dir()
            )
            configured_reports = (
                Path(config.schedule.reports_output_dir)
                if config.schedule.reports_output_dir
                else reports_dir()
            )
        else:
            configured_logs = Path(config.reports.logs_output_dir) if config.reports.logs_output_dir else logs_dir()
            configured_reports = Path(config.reports.reports_output_dir) if config.reports.reports_output_dir else reports_dir()
        configured_logs.mkdir(parents=True, exist_ok=True)
        configured_reports.mkdir(parents=True, exist_ok=True)
        log_path = configure_logging(
            console=not args.scan_all_silent,
            explicit_path=configured_logs / f"verificacao_{datetime.now():%Y%m%d_%H%M%S}.log",
        )
        selected_ids: set[str] | None = None
        if args.scan_bsdg:
            requested = {value.casefold() for value in args.scan_bsdg}
            selected_ids = {
                item.id
                for item in config.bsdgs
                if item.id.casefold() in requested or item.name.casefold() in requested
            }
            if not selected_ids:
                print("Nenhuma BSDG correspondente foi localizada.", file=sys.stderr)
                return 2
        summary = VerificationService().run_scan(
            selected_bsdg_ids=selected_ids,
            mode="AGENDADA" if args.scan_all_silent else "CLI",
            log_path=str(log_path),
            report_output_dir=configured_reports,
        )
        if not args.scan_all_silent:
            print(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2))
        return 0 if summary.outcome != "CANCELADA" else 3

    return -1

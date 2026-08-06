from __future__ import annotations

import os
import sys
import tempfile
import traceback
from datetime import datetime
from pathlib import Path

from bsdgs_verifier.cli import build_parser, run_cli
from bsdgs_verifier.instance_lock import SingleInstanceGuard


def _startup_log_path() -> Path:
    """Retorna um caminho gravável mesmo quando a configuração falha cedo."""
    try:
        from bsdgs_verifier.paths import app_data_dir

        return app_data_dir() / "startup_error.log"
    except Exception:
        return Path(tempfile.gettempdir()) / "BSDGs_Verificador_Atualizacao_startup_error.log"


def _record_startup_failure(error: BaseException) -> Path:
    path = _startup_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    details = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    payload = (
        f"Data/hora: {datetime.now().astimezone().isoformat()}\n"
        f"Executável: {sys.executable}\n"
        f"Python congelado: {bool(getattr(sys, 'frozen', False))}\n"
        f"Plataforma: {sys.platform}\n\n"
        f"{details}"
    )
    try:
        path.write_text(payload, encoding="utf-8")
    except OSError:
        fallback = Path(tempfile.gettempdir()) / "BSDGs_Verificador_Atualizacao_startup_error.log"
        fallback.write_text(payload, encoding="utf-8")
        path = fallback
    return path


def _show_native_message(title: str, message: str, *, error: bool = False) -> None:
    if os.name == "nt":
        try:
            import ctypes

            icon_flag = 0x10 if error else 0x40
            ctypes.windll.user32.MessageBoxW(0, message, title, icon_flag)
            return
        except Exception:
            pass
    try:
        print(f"{title}\n{message}", file=sys.stderr if error else sys.stdout)
    except Exception:
        pass


def _show_native_startup_error(log_path: Path) -> None:
    _show_native_message(
        "Falha ao iniciar o aplicativo",
        "O BSDGs — Verificador de Atualização não conseguiu iniciar.\n\n"
        "Foi criado um registro técnico em:\n"
        f"{log_path}\n\n"
        "Envie esse arquivo ao responsável pelo aplicativo.",
        error=True,
    )


def main() -> int:
    try:
        parser = build_parser()
        args = parser.parse_args()

        cli_result = run_cli(args)
        if cli_result >= 0:
            return cli_result

        # O bloqueio de instância é aplicado somente à interface. As execuções
        # silenciosas/agendadas continuam sendo tratadas pela CLI.
        instance_guard = SingleInstanceGuard()
        if not instance_guard.acquire():
            _show_native_message(
                "Aplicativo já em execução",
                "O BSDGs — Verificador de Atualização já está aberto neste computador.\n\n"
                "Localize a janela existente na barra de tarefas ou encerre o processo "
                "pelo Gerenciador de Tarefas antes de iniciar uma nova instância.",
            )
            return 0

        from bsdgs_verifier.deferred_gui import DeferredApplication

        app = DeferredApplication()
        app.mainloop()
        return 0

    except BaseException as error:
        log_path = _record_startup_failure(error)
        _show_native_startup_error(log_path)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import queue
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from .config import ConfigManager
from .constants import APP_NAME, APP_VERSION
from .enhanced_gui import EnhancedApplication
from .inventory import InventoryDB
from .paths import app_data_dir
from .scheduler import WindowsScheduler
from .service import VerificationService
from .theme import BACKGROUND, choose_font_family


class DeferredApplication(EnhancedApplication):
    """Interface que é apresentada antes da inicialização do inventário SQLite.

    A versão anterior construía ConfigManager, InventoryDB, VerificationService,
    toda a interface e o painel de resultados antes de entrar no ``mainloop``.
    Em alguns computadores Windows, o processo permanecia ativo sem mapear uma
    janela. Esta classe cria e exibe primeiro a estrutura visual; o inventário é
    inicializado depois, em uma thread separada.
    """

    def __init__(self, *, start_hidden: bool = False) -> None:
        self.start_hidden = start_hidden
        self.startup_complete = False
        self.startup_error: BaseException | None = None
        self._startup_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self._startup_thread: threading.Thread | None = None

        # Estado adicional da interface v1.3.1.
        from .selection_state import SelectionStateManager

        self.selection_state_manager = SelectionStateManager()
        self.selection_state = self.selection_state_manager.load()
        self._updating_bsdg_tree = False
        self._active_scan_bsdg_names: list[str] = []

        # Chama diretamente Tk.__init__, evitando o construtor síncrono e pesado
        # de Application/EnhancedApplication.
        tk.Tk.__init__(self)
        self._trace_startup("Tk criado")

        self.title(f"{APP_NAME} — v{APP_VERSION}")
        self.geometry("1360x920")
        self.minsize(900, 650)
        self.configure(background=BACKGROUND)

        self.config_manager = ConfigManager()
        self._trace_startup("carregando configuração")
        self.config_data = self.config_manager.load()
        self._trace_startup("configuração carregada")

        # Estes componentes serão criados depois que a janela estiver visível.
        self.inventory: InventoryDB | None = None
        self.service: VerificationService | None = None
        self.scheduler = WindowsScheduler()

        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.cancel_event = threading.Event()
        self.scan_thread: threading.Thread | None = None
        self.last_summary = None
        self.log_path: Path | None = None

        self.font_family = choose_font_family(self)
        self._asset_images: dict[str, tk.PhotoImage] = {}

        self._trace_startup("configurando identidade visual")
        self._configure_style()
        self._load_assets()
        self._build_menu()
        self._build_ui()
        self._install_selection_ui()
        self._trace_startup("estrutura visual construída")

        self._set_startup_controls(enabled=False)
        self.status_var.set("Inicializando inventário local...")

        if self.start_hidden:
            self.withdraw()
        else:
            self.after_idle(self._present_main_window)

        # A thread só começa depois que o mainloop/update já pode processar a
        # apresentação da janela.
        self.after(120, self._start_deferred_initialization)
        self.after(100, self._poll_startup_queue)
        self.after(150, self._poll_events)

    # ------------------------------------------------------------------
    # Diagnóstico e apresentação da janela
    # ------------------------------------------------------------------
    def _trace_startup(self, message: str) -> None:
        try:
            path = app_data_dir() / "startup_trace.log"
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as stream:
                stream.write(
                    f"{datetime.now().astimezone().isoformat()} | "
                    f"PID={__import__('os').getpid()} | {message}\n"
                )
        except Exception:
            pass

    def _present_main_window(self) -> None:
        try:
            self.update_idletasks()

            screen_width = max(800, self.winfo_screenwidth())
            screen_height = max(600, self.winfo_screenheight())
            window_width = min(1360, max(900, screen_width - 80))
            window_height = min(920, max(650, screen_height - 120))
            x = max(0, (screen_width - window_width) // 2)
            y = max(0, (screen_height - window_height) // 2)

            self.geometry(f"{window_width}x{window_height}+{x}+{y}")
            self.state("normal")
            self.deiconify()
            self.lift()

            try:
                self.attributes("-topmost", True)
                self.after(900, lambda: self.attributes("-topmost", False))
            except tk.TclError:
                pass

            try:
                self.focus_force()
            except tk.TclError:
                pass

            self.update_idletasks()
            self._trace_startup(
                "janela apresentada | "
                f"state={self.state()} | "
                f"mapped={self.winfo_ismapped()} | "
                f"viewable={self.winfo_viewable()} | "
                f"id={self.winfo_id()} | "
                f"geometry={self.winfo_geometry()} | "
                f"screen={screen_width}x{screen_height}"
            )
        except BaseException as error:
            self.startup_error = error
            self._trace_startup(
                "erro ao apresentar janela | "
                + "".join(traceback.format_exception_only(type(error), error)).strip()
            )
            raise

    # ------------------------------------------------------------------
    # Inicialização adiada
    # ------------------------------------------------------------------
    def _start_deferred_initialization(self) -> None:
        if self._startup_thread and self._startup_thread.is_alive():
            return

        self._trace_startup("iniciando thread do inventário")

        def worker() -> None:
            try:
                inventory = InventoryDB()
                service = VerificationService(self.config_manager, inventory)
                self._startup_queue.put(("ready", (inventory, service)))
            except BaseException as error:
                self._startup_queue.put(("error", error))

        self._startup_thread = threading.Thread(
            target=worker,
            name="BSDGsStartup",
            daemon=True,
        )
        self._startup_thread.start()

    def _poll_startup_queue(self) -> None:
        if self.startup_complete or self.startup_error is not None:
            return

        try:
            event, payload = self._startup_queue.get_nowait()
        except queue.Empty:
            self.after(100, self._poll_startup_queue)
            return

        if event == "ready":
            inventory, service = payload  # type: ignore[misc]
            self.inventory = inventory
            self.service = service
            self._complete_deferred_initialization()
            return

        self._handle_deferred_initialization_error(payload)

    def _complete_deferred_initialization(self) -> None:
        try:
            self._trace_startup("inventário inicializado; atualizando painel")
            self._refresh_all()
            self._refresh_selection_context()
            self.startup_complete = True
            self.status_var.set("Pronto.")
            self._set_startup_controls(enabled=True)
            self._trace_startup("inicialização concluída")
        except BaseException as error:
            self._handle_deferred_initialization_error(error)

    def _handle_deferred_initialization_error(self, error: object) -> None:
        if isinstance(error, BaseException):
            exception = error
        else:
            exception = RuntimeError(str(error))

        self.startup_error = exception
        self.status_var.set("Falha ao inicializar o inventário local.")
        self._set_startup_controls(enabled=False)

        trace = "".join(
            traceback.format_exception(
                type(exception),
                exception,
                exception.__traceback__,
            )
        )
        self._trace_startup("falha na inicialização adiada\n" + trace)

        if not self.start_hidden:
            messagebox.showerror(
                "Falha ao inicializar o inventário",
                "A janela foi aberta, mas o inventário local não pôde ser "
                "inicializado.\n\n"
                "Consulte o arquivo:\n"
                f"{app_data_dir() / 'startup_trace.log'}",
                parent=self,
            )

    def _set_startup_controls(self, *, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        try:
            self.scan_all_button.configure(state=state)
        except Exception:
            pass

        # O botão de verificação individual não possui referência própria na
        # classe-base. Ele é localizado pelo texto.
        for widget in self._walk_widgets(self):
            if isinstance(widget, ttk.Button):
                try:
                    if widget.cget("text") == "Verificar BSDG selecionada":
                        widget.configure(state=state)
                except tk.TclError:
                    continue

    def wait_for_startup(self, timeout_seconds: float = 20.0) -> bool:
        """Processa a fila Tk até a inicialização terminar ou expirar."""
        deadline = time.monotonic() + timeout_seconds
        while (
            not self.startup_complete
            and self.startup_error is None
            and time.monotonic() < deadline
        ):
            self.update()
            time.sleep(0.05)
        return self.startup_complete and self.startup_error is None

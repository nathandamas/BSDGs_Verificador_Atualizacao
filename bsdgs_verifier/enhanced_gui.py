from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .constants import APP_NAME, DAY_CODES, DAY_NAMES_BY_CODE
from .gui import Application
from .paths import logs_dir, reports_dir
from .selection_state import SelectionStateManager
from .theme import (
    BACKGROUND,
    BORDER,
    ERROR,
    PRIMARY,
    PRIMARY_DARK,
    PRIMARY_LIGHT,
    PRIMARY_PALE,
    SURFACE,
    TEXT,
    TEXT_MUTED,
    WARNING_FG,
)


class EnhancedApplication(Application):
    """Interface v1.3.1 com seleção persistente e explícita de BSDG.

    A classe herda a interface consolidada da versão 1.3.0 e acrescenta a
    indicação da BSDG selecionada sem duplicar o arquivo ``gui.py``. Isso reduz
    o risco de divergência entre a identidade visual existente e as melhorias.
    """

    def __init__(self) -> None:
        self.selection_state_manager = SelectionStateManager()
        self.selection_state = self.selection_state_manager.load()
        self._updating_bsdg_tree = False
        self._active_scan_bsdg_names: list[str] = []
        super().__init__()
        self._install_selection_ui()
        self._refresh_all()

    # ------------------------------------------------------------------
    # Construção complementar da interface
    # ------------------------------------------------------------------
    def _install_selection_ui(self) -> None:
        self._configure_bsdg_check_column()
        self._add_home_selection_indicator()
        self._add_schedule_selection_field()
        self._add_results_context_bar()
        self.bsdg_tree.bind("<<TreeviewSelect>>", self._on_bsdg_selection_changed, add="+")

    def _configure_bsdg_check_column(self) -> None:
        columns = ("selected", "name", "path", "enabled", "recursive", "status")
        self.bsdg_tree.configure(columns=columns, displaycolumns=columns)
        headings = {
            "selected": "",
            "name": "BSDG",
            "path": "Pasta local sincronizada",
            "enabled": "Monitorar",
            "recursive": "Subpastas",
            "status": "Situação",
        }
        widths = {
            "selected": 46,
            "name": 200,
            "path": 500,
            "enabled": 85,
            "recursive": 85,
            "status": 175,
        }
        for key in columns:
            self.bsdg_tree.heading(key, text=headings[key])
            self.bsdg_tree.column(
                key,
                width=widths[key],
                anchor="center" if key == "selected" else "w",
                stretch=key in {"name", "path", "status"},
            )

    def _add_home_selection_indicator(self) -> None:
        actions = self.scan_all_button.master
        self.home_selected_bsdg_var = tk.StringVar(value="BSDG selecionada: nenhuma")
        indicator = tk.Frame(
            actions,
            bg=PRIMARY_PALE,
            highlightbackground=PRIMARY_LIGHT,
            highlightthickness=1,
        )
        indicator.pack(side="left", fill="x", expand=True, padx=(14, 10), pady=1)
        tk.Label(
            indicator,
            textvariable=self.home_selected_bsdg_var,
            bg=PRIMARY_PALE,
            fg=PRIMARY_DARK,
            font=(self.font_family, 9, "bold"),
            anchor="w",
            padx=12,
            pady=7,
        ).pack(fill="x", expand=True)

    def _add_schedule_selection_field(self) -> None:
        logs_entry = self._find_entry_for_variable(self.schedule_logs_dir_var)
        if logs_entry is None:
            return
        panel = logs_entry.master

        # Na versão 1.3.0, os botões ficam na linha 6. A nova linha 6 passa a
        # apresentar a BSDG selecionada, e os botões são deslocados para a 7.
        for widget in panel.grid_slaves(row=6):
            widget.grid_configure(row=7)

        self.schedule_selected_bsdg_var = tk.StringVar(value="Nenhuma BSDG selecionada")
        tk.Label(
            panel,
            text="BSDG selecionada",
            bg=SURFACE,
            fg=TEXT,
            font=(self.font_family, 9, "bold"),
        ).grid(row=6, column=0, sticky="w", pady=6)
        ttk.Entry(
            panel,
            textvariable=self.schedule_selected_bsdg_var,
            width=58,
            state="readonly",
        ).grid(row=6, column=1, sticky="ew", padx=(12, 8), pady=4)
        ttk.Button(
            panel,
            text="Selecionar...",
            style="Neutral.TButton",
            command=self._open_bsdg_selection_tab,
        ).grid(row=6, column=2, sticky="e", pady=4)

    def _add_results_context_bar(self) -> None:
        tree_outer = self.result_tree.master.master
        context_outer = self._surface(self.results_tab, padding=10)
        context_outer.pack(fill="x", pady=(0, 12), before=tree_outer)
        context = context_outer.inner  # type: ignore[attr-defined]
        self.results_context_var = tk.StringVar(value="")
        tk.Label(
            context,
            textvariable=self.results_context_var,
            bg=SURFACE,
            fg=PRIMARY_DARK,
            font=(self.font_family, 8, "bold"),
            anchor="w",
            justify="left",
            wraplength=1250,
        ).pack(fill="x", anchor="w")

    def _walk_widgets(self, parent: tk.Misc):
        for child in parent.winfo_children():
            yield child
            yield from self._walk_widgets(child)

    def _find_entry_for_variable(self, variable: tk.Variable) -> ttk.Entry | None:
        variable_name = str(variable)
        for widget in self._walk_widgets(self.schedule_tab):
            if isinstance(widget, ttk.Entry):
                try:
                    if str(widget.cget("textvariable")) == variable_name:
                        return widget
                except tk.TclError:
                    continue
        return None

    # ------------------------------------------------------------------
    # Seleção e persistência
    # ------------------------------------------------------------------
    def _valid_bsdg_ids(self) -> set[str]:
        return {item.id for item in self.config_data.bsdgs}

    def _ensure_selected_bsdg_id(self) -> str:
        valid_ids = self._valid_bsdg_ids()
        selected_id = self.selection_state.selected_bsdg_id
        if selected_id in valid_ids:
            return selected_id

        candidate = next((item for item in self.config_data.bsdgs if item.enabled), None)
        if candidate is None and self.config_data.bsdgs:
            candidate = self.config_data.bsdgs[0]
        selected_id = candidate.id if candidate else ""
        self.selection_state.selected_bsdg_id = selected_id
        self.selection_state_manager.save(self.selection_state)
        return selected_id

    def _bsdg_by_id(self, bsdg_id: str):
        return next((item for item in self.config_data.bsdgs if item.id == bsdg_id), None)

    def _current_selected_bsdg(self):
        return self._bsdg_by_id(self._ensure_selected_bsdg_id())

    def _scheduled_bsdg_name(self) -> str:
        item = self._bsdg_by_id(self.selection_state.scheduled_bsdg_id)
        if item is not None:
            return item.name
        if self.config_data.schedule.enabled:
            return "não registrada no agendamento atual; reinstale o agendamento"
        current = self._current_selected_bsdg()
        return current.name if current else "nenhuma"

    def _on_bsdg_selection_changed(self, _event: tk.Event | None = None) -> None:
        if self._updating_bsdg_tree:
            return
        selection = self.bsdg_tree.selection()
        if not selection:
            return
        selected_id = selection[0]
        if selected_id not in self._valid_bsdg_ids():
            return
        if self.selection_state.selected_bsdg_id != selected_id:
            self.selection_state.selected_bsdg_id = selected_id
            self.selection_state_manager.save(self.selection_state)
        self._refresh_bsdgs()
        self._refresh_selection_context()
        self._refresh_dashboard()

    def _open_bsdg_selection_tab(self) -> None:
        self.notebook.select(self.bsdg_tab)
        selected_id = self._ensure_selected_bsdg_id()
        if selected_id and self.bsdg_tree.exists(selected_id):
            self.bsdg_tree.selection_set(selected_id)
            self.bsdg_tree.focus(selected_id)
            self.bsdg_tree.see(selected_id)

    def _refresh_bsdgs(self) -> None:
        # Durante Application.__init__, a tabela ainda possui as cinco colunas
        # originais. Nesse primeiro ciclo, usa-se o comportamento-base.
        if not hasattr(self, "bsdg_tree") or "selected" not in tuple(self.bsdg_tree["columns"]):
            super()._refresh_bsdgs()
            return

        selected_id = self._ensure_selected_bsdg_id()
        self._updating_bsdg_tree = True
        try:
            for item_id in self.bsdg_tree.get_children():
                self.bsdg_tree.delete(item_id)
            for bsdg in self.config_data.bsdgs:
                if not bsdg.local_path:
                    status = "Não configurada"
                    tag = "unconfigured"
                elif Path(bsdg.local_path).is_dir():
                    status = "Disponível"
                    tag = "available"
                else:
                    status = "Pasta não encontrada"
                    tag = "missing"
                if bsdg.needs_name_confirmation:
                    status += " | nome a confirmar"
                self.bsdg_tree.insert(
                    "",
                    "end",
                    iid=bsdg.id,
                    tags=(tag,),
                    values=(
                        "☑" if bsdg.id == selected_id else "☐",
                        bsdg.name,
                        bsdg.local_path or "—",
                        "Sim" if bsdg.enabled else "Não",
                        "Sim" if bsdg.recursive else "Não",
                        status,
                    ),
                )
            if selected_id and self.bsdg_tree.exists(selected_id):
                self.bsdg_tree.selection_set(selected_id)
                self.bsdg_tree.focus(selected_id)
                self.bsdg_tree.see(selected_id)
        finally:
            self._updating_bsdg_tree = False

    def _refresh_selection_context(self) -> None:
        selected = self._current_selected_bsdg()
        selected_name = selected.name if selected else "nenhuma"

        if hasattr(self, "home_selected_bsdg_var"):
            self.home_selected_bsdg_var.set(f"BSDG selecionada: {selected_name}")
        if hasattr(self, "schedule_selected_bsdg_var"):
            self.schedule_selected_bsdg_var.set(selected_name)
        if hasattr(self, "results_context_var"):
            self.results_context_var.set(
                f"BSDG selecionada: {selected_name}   |   "
                f"Relatórios: {self._configured_reports_directory()}   |   "
                f"Logs: {self._configured_logs_directory()}"
            )

    def _refresh_all(self) -> None:
        super()._refresh_all()
        if hasattr(self, "home_selected_bsdg_var"):
            self._refresh_selection_context()

    def _refresh_dashboard(self) -> None:
        super()._refresh_dashboard()
        if not hasattr(self, "selection_state"):
            return

        latest = self.inventory.latest_run()
        if latest:
            payload = self._latest_run_payload()
            summaries = payload.get("bsdg_summaries", [])
            names = []
            if isinstance(summaries, list):
                names = [
                    str(item.get("bsdg_name", ""))
                    for item in summaries
                    if isinstance(item, dict) and item.get("bsdg_name")
                ]
            report_paths = payload.get("report_paths", [])
            report_folder = ""
            if isinstance(report_paths, list) and report_paths:
                report_folder = str(Path(str(report_paths[0])).expanduser().parent)
            log_value = str(payload.get("log_path", "") or "")
            log_folder = str(Path(log_value).expanduser().parent) if log_value else ""

            details = self.last_run_var.get()
            if names:
                details += f"\nBSDG(s): {', '.join(dict.fromkeys(names))}"
            if report_folder:
                details += f"\nRelatórios: {report_folder}"
            if log_folder:
                details += f"\nLogs: {log_folder}"
            self.last_run_var.set(details)

        current = self._current_selected_bsdg()
        current_name = current.name if current else "nenhuma"
        if self.config_data.schedule.enabled:
            day = DAY_NAMES_BY_CODE.get(self.config_data.schedule.day, self.config_data.schedule.day)
            reports_path = self.config_data.schedule.reports_output_dir or str(reports_dir())
            logs_path = self.config_data.schedule.logs_output_dir or str(logs_dir())
            self.next_run_var.set(
                f"Agendamento configurado: {day}, às {self.config_data.schedule.time}.\n"
                f"BSDG selecionada: {self._scheduled_bsdg_name()}\n"
                f"Relatórios: {reports_path}\nLogs: {logs_path}"
            )
        else:
            self.next_run_var.set(
                "Agendamento não instalado.\n"
                f"BSDG selecionada para o próximo agendamento: {current_name}"
            )

    # ------------------------------------------------------------------
    # Verificação manual e diretórios de saída
    # ------------------------------------------------------------------
    def _start_scan(self, selected_ids: set[str] | None) -> None:
        if selected_ids:
            names = [item.name for item in self.config_data.bsdgs if item.id in selected_ids]
        else:
            names = [item.name for item in self.config_data.bsdgs if item.enabled]
        self._active_scan_bsdg_names = names
        super()._start_scan(selected_ids)

    def _ask_output_locations(self) -> tuple[Path, Path] | None:
        window = tk.Toplevel(self)
        window.title(f"Pastas de saída — {APP_NAME}")
        window.transient(self)
        window.resizable(False, False)
        window.configure(bg=SURFACE)
        window.grab_set()

        icon = self._asset_images.get("app_icon")
        if icon is not None:
            try:
                window.iconphoto(True, icon)
            except tk.TclError:
                pass

        result: dict[str, Path] = {}
        reports_var = tk.StringVar(value=str(self._configured_reports_directory()))
        logs_var = tk.StringVar(value=str(self._configured_logs_directory()))
        target_text = ", ".join(self._active_scan_bsdg_names) or "Nenhuma BSDG monitorada"

        header = tk.Frame(window, bg=PRIMARY_PALE, padx=22, pady=16)
        header.pack(fill="x")
        tk.Label(
            header,
            text="Escolha onde salvar os resultados desta verificação",
            bg=PRIMARY_PALE,
            fg=PRIMARY_DARK,
            font=(self.font_family, 13, "bold"),
        ).pack(anchor="w")
        tk.Label(
            header,
            text=(
                "As pastas selecionadas serão usadas após a confirmação e ficarão "
                "preenchidas como padrão na próxima execução."
            ),
            bg=PRIMARY_PALE,
            fg=TEXT,
            font=(self.font_family, 9),
            justify="left",
            wraplength=680,
        ).pack(anchor="w", pady=(5, 0))

        content = tk.Frame(window, bg=SURFACE, padx=22, pady=20)
        content.pack(fill="both", expand=True)
        content.grid_columnconfigure(1, weight=1)

        def add_path_row(row: int, label: str, variable: tk.StringVar, title: str) -> None:
            tk.Label(
                content,
                text=label,
                bg=SURFACE,
                fg=TEXT,
                font=(self.font_family, 9, "bold"),
            ).grid(row=row, column=0, sticky="w", pady=8)
            ttk.Entry(content, textvariable=variable, width=68).grid(
                row=row, column=1, sticky="ew", padx=(12, 8), pady=8
            )

            def browse() -> None:
                initial = variable.get().strip()
                folder = filedialog.askdirectory(
                    title=title,
                    initialdir=initial if initial and Path(initial).exists() else str(Path.home()),
                    parent=window,
                )
                if folder:
                    variable.set(folder)

            ttk.Button(content, text="Selecionar...", style="Neutral.TButton", command=browse).grid(
                row=row, column=2, sticky="e", pady=8
            )

        add_path_row(0, "Pasta dos relatórios", reports_var, "Selecionar pasta para os relatórios")
        add_path_row(1, "Pasta dos logs", logs_var, "Selecionar pasta para os logs")

        tk.Label(
            content,
            text="BSDG(s) desta verificação",
            bg=SURFACE,
            fg=TEXT,
            font=(self.font_family, 9, "bold"),
        ).grid(row=2, column=0, sticky="w", pady=8)
        target_var = tk.StringVar(value=target_text)
        ttk.Entry(content, textvariable=target_var, width=68, state="readonly").grid(
            row=2, column=1, columnspan=2, sticky="ew", padx=(12, 0), pady=8
        )

        tk.Label(
            content,
            text="O programa criará as pastas quando necessário e verificará se há permissão de gravação.",
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=(self.font_family, 8),
            justify="left",
        ).grid(row=3, column=0, columnspan=3, sticky="w", pady=(4, 14))

        buttons = tk.Frame(content, bg=SURFACE)
        buttons.grid(row=4, column=0, columnspan=3, sticky="ew")

        def confirm() -> None:
            report_path = Path(reports_var.get().strip()).expanduser()
            log_path = Path(logs_var.get().strip()).expanduser()
            if not self._validate_output_directory(report_path, "os relatórios"):
                return
            if not self._validate_output_directory(log_path, "os logs"):
                return
            self.config_data.reports.reports_output_dir = str(report_path)
            self.config_data.reports.logs_output_dir = str(log_path)
            self.config_manager.save(self.config_data)
            self.schedule_reports_dir_var.set(str(report_path))
            self.schedule_logs_dir_var.set(str(log_path))
            result["reports"] = report_path
            result["logs"] = log_path
            self._refresh_selection_context()
            window.destroy()

        ttk.Button(buttons, text="Cancelar", style="Neutral.TButton", command=window.destroy).pack(side="right")
        ttk.Button(
            buttons,
            text="Confirmar e iniciar",
            style="Primary.TButton",
            command=confirm,
        ).pack(side="right", padx=(0, 8))

        window.protocol("WM_DELETE_WINDOW", window.destroy)
        window.update_idletasks()
        x = self.winfo_rootx() + max(0, (self.winfo_width() - window.winfo_width()) // 2)
        y = self.winfo_rooty() + max(0, (self.winfo_height() - window.winfo_height()) // 2)
        window.geometry(f"+{x}+{y}")
        self.wait_window(window)

        if "reports" not in result or "logs" not in result:
            return None
        return result["reports"], result["logs"]

    def _scan_finished(self, summary: object) -> None:
        self.last_summary = summary
        self.scan_all_button.configure(state="normal")
        self.cancel_button.configure(state="disabled")
        self.status_var.set("Verificação concluída.")
        self.progress.configure(value=self.progress["maximum"])
        self._refresh_all()

        data = summary.to_dict()  # type: ignore[attr-defined]
        summaries = data.get("bsdg_summaries", [])
        bsdg_names = [
            str(item.get("bsdg_name", ""))
            for item in summaries
            if isinstance(item, dict) and item.get("bsdg_name")
        ]
        bsdg_text = ", ".join(dict.fromkeys(bsdg_names)) or "não identificada"
        report_folder = (
            str(Path(data["report_paths"][0]).parent)
            if data.get("report_paths")
            else "nenhum relatório gerado"
        )
        log_path = str(data.get("log_path", "") or "não informado")

        text = (
            f"Execução: {data['run_id']}\n"
            f"Resultado: {data['outcome']}\n"
            f"BSDG(s): {bsdg_text}\n"
            f"BSDGs verificadas: {data['scanned_bsdgs']} | indisponíveis: {data['missing_bsdgs']}\n"
            f"Arquivos: {data['total_files']} | novos: {data['new_files']} | modificados: {data['modified_files']}\n"
            f"Sem alteração: {data['unchanged_files']} | removidos: {data['removed_files']}\n"
            f"Válidos: {data['valid_files']} | inválidos/erro: {data['invalid_files']}\n"
            f"Somente na nuvem: {data['online_only_files']} | inacessíveis: {data['inaccessible_files']}\n"
            f"Pasta dos relatórios: {report_folder}\n"
            f"Log: {log_path}"
        )
        attention_items = [
            item for item in summaries if isinstance(item, dict) and item.get("message")
        ]
        if attention_items:
            text += "\n\nAtenções:\n" + "\n".join(
                f"- {item.get('bsdg_name')}: {item.get('message')}"
                for item in attention_items
            )
        self._set_summary_text(text)
        self._refresh_selection_context()

        if data["total_files"] == 0 and data["scanned_bsdgs"] > 0:
            messagebox.showwarning(
                "Verificação concluída sem arquivos",
                text
                + "\n\nO programa executou a varredura, mas não encontrou GeoPackages. "
                "Verifique a opção Subpastas e a disponibilidade local no OneDrive.",
            )
        else:
            messagebox.showinfo("Verificação concluída", text)

    # ------------------------------------------------------------------
    # Agendamento vinculado a uma BSDG
    # ------------------------------------------------------------------
    def _install_schedule(self) -> None:
        selected = self._current_selected_bsdg()
        if selected is None:
            self.notebook.select(self.bsdg_tab)
            messagebox.showerror(
                "BSDG obrigatória",
                "Selecione uma BSDG na aba 'BSDGs monitoradas' antes de instalar o agendamento.",
                parent=self,
            )
            return

        if not selected.enabled:
            if not messagebox.askyesno(
                "BSDG desativada",
                f"'{selected.name}' não está marcada para monitoramento. Ativar e usar no agendamento?",
                parent=self,
            ):
                return
            selected.enabled = True

        try:
            hour = int(self.hour_var.get())
            minute = int(self.minute_var.get())
            if not 0 <= hour <= 23 or not 0 <= minute <= 59:
                raise ValueError
            time_value = f"{hour:02d}:{minute:02d}"
        except ValueError:
            messagebox.showerror("Horário inválido", "Informe hora e minuto válidos.", parent=self)
            return

        report_path = Path(self.schedule_reports_dir_var.get().strip()).expanduser()
        log_path = Path(self.schedule_logs_dir_var.get().strip()).expanduser()
        if not self._validate_output_directory(report_path, "relatórios"):
            return
        if not self._validate_output_directory(log_path, "logs"):
            return

        day_code = DAY_CODES[self.day_var.get()]
        self.config_data.schedule.reports_output_dir = str(report_path)
        self.config_data.schedule.logs_output_dir = str(log_path)
        self.config_data.schedule.day = day_code
        self.config_data.schedule.time = time_value
        self.config_manager.save(self.config_data)

        result = self.scheduler.install_weekly(
            day_code,
            time_value,
            selected_bsdg_id=selected.id,
        )
        details = (
            f"{result.message}\n"
            f"BSDG selecionada: {selected.name}\n"
            f"Relatórios: {report_path}\n"
            f"Logs: {log_path}"
            + (f"\n{result.raw_output}" if result.raw_output else "")
        )
        self.schedule_status_var.set(details)
        if result.success:
            self.config_data.schedule.enabled = True
            self.schedule_enabled_var.set(True)
            self.config_manager.save(self.config_data)
            self.selection_state.scheduled_bsdg_id = selected.id
            self.selection_state_manager.save(self.selection_state)
            self._refresh_dashboard()
            self._refresh_selection_context()
            messagebox.showinfo("Agendamento", details, parent=self)
        else:
            messagebox.showerror("Agendamento", details, parent=self)

    def _remove_schedule(self) -> None:
        result = self.scheduler.remove()
        scheduled_name = self._scheduled_bsdg_name()
        details = (
            f"{result.message}\nBSDG do agendamento: {scheduled_name}"
            + (f"\n{result.raw_output}" if result.raw_output else "")
        )
        self.schedule_status_var.set(details)
        if result.success:
            self.config_data.schedule.enabled = False
            self.schedule_enabled_var.set(False)
            self.config_manager.save(self.config_data)
            self.selection_state.scheduled_bsdg_id = ""
            self.selection_state_manager.save(self.selection_state)
            self._refresh_dashboard()
            messagebox.showinfo("Agendamento", details, parent=self)
        else:
            messagebox.showerror("Agendamento", details, parent=self)

    def _query_schedule(self) -> None:
        result = self.scheduler.query()
        details = (
            f"{result.message}\n"
            f"BSDG selecionada: {self._scheduled_bsdg_name()}\n"
            f"Relatórios: {self.schedule_reports_dir_var.get()}\n"
            f"Logs: {self.schedule_logs_dir_var.get()}"
            + (f"\n{result.raw_output}" if result.raw_output else "")
        )
        self.schedule_status_var.set(details)
        messagebox.showinfo("Consulta do agendamento", details, parent=self)

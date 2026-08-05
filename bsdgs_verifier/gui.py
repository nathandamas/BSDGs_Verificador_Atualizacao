from __future__ import annotations

import json
import os
import queue
import threading
import uuid
import webbrowser
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from .config import ConfigManager
from .constants import (
    APP_NAME,
    APP_VERSION,
    DAY_CODES,
    DAY_NAMES_BY_CODE,
    DEVELOPER_GITHUB_URL,
    DEVELOPER_NAME,
    LAGEAMB_SITE_URL,
    LOCAL_OPERATION_NOTICE,
)
from .inventory import InventoryDB
from .logging_setup import configure_logging
from .models import BsdgConfig
from .paths import app_data_dir, logs_dir, reports_dir, resource_path
from .scheduler import WindowsScheduler
from .service import VerificationService
from .theme import (
    BACKGROUND,
    BORDER,
    ERROR,
    PRIMARY,
    PRIMARY_DARK,
    PRIMARY_LIGHT,
    PRIMARY_PALE,
    SUCCESS,
    SURFACE,
    TEXT,
    TEXT_MUTED,
    WARNING_BG,
    WARNING_FG,
    choose_font_family,
    configure_ttk_style,
)


class Application(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} — v{APP_VERSION}")
        self.geometry("1360x920")
        self.minsize(1100, 800)
        self.configure(background=BACKGROUND)

        self.config_manager = ConfigManager()
        self.config_data = self.config_manager.load()
        self.inventory = InventoryDB()
        self.service = VerificationService(self.config_manager, self.inventory)
        self.scheduler = WindowsScheduler()
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.cancel_event = threading.Event()
        self.scan_thread: threading.Thread | None = None
        self.last_summary = None
        self.log_path: Path | None = None

        self.font_family = choose_font_family(self)
        self._asset_images: dict[str, tk.PhotoImage] = {}
        self._configure_style()
        self._load_assets()
        self._build_menu()
        self._build_ui()
        self._refresh_all()
        self.after(150, self._poll_events)

    def _configure_style(self) -> None:
        self.style = configure_ttk_style(self, self.font_family)

    def _load_assets(self) -> None:
        asset_map = {
            "header_bg": "assets/contours_header.png",
            "panel_bg": "assets/contours_panel.png",
            "logo_header": "assets/lageamb_logo_header.png",
            "logo_about": "assets/lageamb_logo_about.png",
            "app_icon": "assets/app_icon.png",
        }
        for key, relative in asset_map.items():
            try:
                self._asset_images[key] = tk.PhotoImage(file=str(resource_path(relative)))
            except (tk.TclError, OSError):
                continue

        icon = self._asset_images.get("app_icon")
        if icon is not None:
            try:
                self.iconphoto(True, icon)
            except tk.TclError:
                pass

    def _build_menu(self) -> None:
        menu_bar = tk.Menu(
            self,
            font=(self.font_family, 9),
            background=SURFACE,
            foreground=TEXT,
            activebackground=PRIMARY_LIGHT,
            activeforeground=PRIMARY_DARK,
            tearoff=False,
        )

        file_menu = tk.Menu(menu_bar, tearoff=False, font=(self.font_family, 9))
        file_menu.add_command(label="Abrir pasta da aplicação", command=lambda: self._open_path(app_data_dir()))
        file_menu.add_separator()
        file_menu.add_command(label="Sair", command=self.destroy)
        menu_bar.add_cascade(label="Arquivo", menu=file_menu)

        help_menu = tk.Menu(menu_bar, tearoff=False, font=(self.font_family, 9))
        help_menu.add_command(label="Como usar...", command=self._show_how_to_use)
        help_menu.add_command(label="Site do LAGEAMB", command=self._open_lageamb_site)
        help_menu.add_command(label="GitHub do desenvolvedor", command=self._open_developer_github)
        help_menu.add_separator()
        help_menu.add_command(label="Sobre...", command=self._show_about)
        menu_bar.add_cascade(label="Ajuda", menu=help_menu)
        self.configure(menu=menu_bar)

    def _build_ui(self) -> None:
        self._build_brand_header()
        self._build_local_notice()

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=18, pady=(12, 10))

        self.home_tab = ttk.Frame(self.notebook, padding=16, style="App.TFrame")
        self.bsdg_tab = ttk.Frame(self.notebook, padding=16, style="App.TFrame")
        self.schedule_tab = ttk.Frame(self.notebook, padding=16, style="App.TFrame")
        self.results_tab = ttk.Frame(self.notebook, padding=16, style="App.TFrame")
        self.notebook.add(self.home_tab, text="  Início  ")
        self.notebook.add(self.bsdg_tab, text="  BSDGs monitoradas  ")
        self.notebook.add(self.schedule_tab, text="  Agendamento  ")
        self.notebook.add(self.results_tab, text="  Resultados e logs  ")

        self._build_home_tab()
        self._build_bsdg_tab()
        self._build_schedule_tab()
        self._build_results_tab()

        self._build_status_bar()
        self._build_footer()

    def _build_brand_header(self) -> None:
        canvas = tk.Canvas(self, height=122, bg=SURFACE, highlightthickness=0)
        canvas.pack(fill="x")
        self.header_canvas = canvas

        bg = self._asset_images.get("header_bg")
        if bg is not None:
            canvas.create_image(0, 0, image=bg, anchor="nw")

        logo = self._asset_images.get("logo_header")
        if logo is not None:
            canvas.create_image(24, 13, image=logo, anchor="nw")
        else:
            canvas.create_text(
                28,
                48,
                text="LAGEAMB",
                anchor="w",
                font=(self.font_family, 26, "bold"),
                fill=PRIMARY,
            )

        self.header_title_id = canvas.create_text(
            620,
            34,
            text=APP_NAME,
            anchor="w",
            font=(self.font_family, 21, "bold"),
            fill=TEXT,
        )
        canvas.create_text(
            620,
            65,
            text="Inventário e validação periódica de GeoPackages sincronizados pelo SharePoint/OneDrive",
            anchor="w",
            font=(self.font_family, 10),
            fill=TEXT_MUTED,
        )

    def _resize_header(self, event: tk.Event) -> None:
        return None

    def _build_local_notice(self) -> None:
        strip = tk.Frame(self, bg=PRIMARY_PALE, highlightbackground="#C9DDBB", highlightthickness=1)
        strip.pack(fill="x", padx=18, pady=(10, 0))

        tk.Frame(strip, bg=PRIMARY, width=7).pack(side="left", fill="y")
        tk.Label(
            strip,
            text="EXECUÇÃO LOCAL",
            bg=PRIMARY_LIGHT,
            fg=PRIMARY_DARK,
            font=(self.font_family, 9, "bold"),
            padx=10,
            pady=5,
        ).pack(side="left", padx=(12, 10), pady=8)
        tk.Label(
            strip,
            text=LOCAL_OPERATION_NOTICE + " Mantenha as pastas e os arquivos disponíveis localmente.",
            bg=PRIMARY_PALE,
            fg=TEXT,
            anchor="w",
            justify="left",
            font=(self.font_family, 9),
            wraplength=1050,
        ).pack(side="left", fill="x", expand=True, pady=8)
        ttk.Button(strip, text="Como usar", style="Secondary.TButton", command=self._show_how_to_use).pack(
            side="right", padx=12, pady=7
        )

    def _build_status_bar(self) -> None:
        status_frame = tk.Frame(self, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        status_frame.pack(fill="x", padx=18, pady=(0, 8))

        self.progress = ttk.Progressbar(status_frame, mode="determinate", style="Green.Horizontal.TProgressbar")
        self.progress.pack(side="left", fill="x", expand=True, padx=(12, 10), pady=9)
        self.status_var = tk.StringVar(value="Pronto.")
        tk.Label(
            status_frame,
            textvariable=self.status_var,
            bg=SURFACE,
            fg=TEXT_MUTED,
            width=48,
            anchor="w",
            font=(self.font_family, 9),
        ).pack(side="left", padx=(0, 12))

    def _build_footer(self) -> None:
        footer = tk.Frame(self, bg=PRIMARY_DARK)
        footer.pack(fill="x")
        tk.Label(
            footer,
            text="LAGEAMB — Laboratório de Geoprocessamento e Estudos Ambientais | Universidade Federal do Paraná",
            bg=PRIMARY_DARK,
            fg="white",
            font=(self.font_family, 8),
            padx=18,
            pady=7,
        ).pack(side="left")
        tk.Label(
            footer,
            text=f"{APP_NAME} · v{APP_VERSION}",
            bg=PRIMARY_DARK,
            fg="#EAF3E1",
            font=(self.font_family, 8, "bold"),
            padx=18,
            pady=7,
        ).pack(side="right")

    def _section_intro(self, parent: tk.Misc, title: str, description: str) -> None:
        frame = tk.Frame(parent, bg=BACKGROUND)
        frame.pack(fill="x", pady=(0, 12))
        tk.Label(
            frame,
            text=title,
            bg=BACKGROUND,
            fg=TEXT,
            font=(self.font_family, 15, "bold"),
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            frame,
            text=description,
            bg=BACKGROUND,
            fg=TEXT_MUTED,
            font=(self.font_family, 9),
            anchor="w",
            justify="left",
            wraplength=1120,
        ).pack(anchor="w", pady=(3, 0))

    def _surface(self, parent: tk.Misc, *, padding: int = 14) -> tk.Frame:
        outer = tk.Frame(parent, bg=BORDER)
        inner = tk.Frame(outer, bg=SURFACE, padx=padding, pady=padding)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        outer.inner = inner  # type: ignore[attr-defined]
        return outer

    def _metric_card(self, parent: tk.Misc, key: str, caption: str, detail: str) -> tk.Frame:
        outer = tk.Frame(parent, bg=BORDER)
        inner = tk.Frame(outer, bg=SURFACE)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        tk.Frame(inner, bg=PRIMARY, height=5).pack(fill="x")

        var = tk.StringVar(value="0")
        self.metric_vars[key] = var
        tk.Label(
            inner,
            textvariable=var,
            bg=SURFACE,
            fg=PRIMARY_DARK,
            font=(self.font_family, 24, "bold"),
            anchor="w",
        ).pack(anchor="w", padx=14, pady=(12, 0))
        tk.Label(
            inner,
            text=caption,
            bg=SURFACE,
            fg=TEXT,
            font=(self.font_family, 9, "bold"),
            anchor="w",
        ).pack(anchor="w", padx=14, pady=(1, 0))
        tk.Label(
            inner,
            text=detail,
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=(self.font_family, 8),
            anchor="w",
            justify="left",
            wraplength=230,
        ).pack(anchor="w", padx=14, pady=(4, 13))
        return outer

    def _build_home_tab(self) -> None:
        self._section_intro(
            self.home_tab,
            "Painel de monitoramento",
            "Acompanhe a disponibilidade das BSDGs, o inventário de GeoPackages e a situação da última verificação.",
        )

        metrics = tk.Frame(self.home_tab, bg=BACKGROUND)
        metrics.pack(fill="x")
        self.metric_vars: dict[str, tk.StringVar] = {}
        cards = [
            ("total_bsdgs", "BSDGs cadastradas", "Catálogo local configurado nesta instalação."),
            ("enabled_bsdgs", "BSDGs monitoradas", "Pastas habilitadas para a próxima varredura."),
            ("missing_bsdgs", "Pastas indisponíveis", "Entradas que exigem sincronização ou ajuste do caminho."),
            ("total_files", "GeoPackages inventariados", "Arquivos registrados no inventário local."),
        ]
        for column, (key, caption, detail) in enumerate(cards):
            metrics.grid_columnconfigure(column, weight=1, uniform="metrics")
            card = self._metric_card(metrics, key, caption, detail)
            card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 6, 0))

        status_grid = tk.Frame(self.home_tab, bg=BACKGROUND)
        status_grid.pack(fill="x", pady=(14, 0))
        status_grid.grid_columnconfigure(0, weight=1, uniform="status")
        status_grid.grid_columnconfigure(1, weight=1, uniform="status")

        last_outer = self._surface(status_grid, padding=14)
        last_outer.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        last = last_outer.inner  # type: ignore[attr-defined]
        tk.Label(last, text="ÚLTIMA VERIFICAÇÃO", bg=SURFACE, fg=PRIMARY_DARK, font=(self.font_family, 8, "bold")).pack(anchor="w")
        self.last_run_var = tk.StringVar(value="Nenhuma verificação registrada.")
        tk.Label(
            last,
            textvariable=self.last_run_var,
            bg=SURFACE,
            fg=TEXT,
            font=(self.font_family, 9),
            justify="left",
            wraplength=520,
        ).pack(anchor="w", pady=(6, 0))

        next_outer = self._surface(status_grid, padding=14)
        next_outer.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        next_card = next_outer.inner  # type: ignore[attr-defined]
        tk.Label(next_card, text="AGENDAMENTO", bg=SURFACE, fg=PRIMARY_DARK, font=(self.font_family, 8, "bold")).pack(anchor="w")
        self.next_run_var = tk.StringVar(value="Agendamento não instalado.")
        tk.Label(
            next_card,
            textvariable=self.next_run_var,
            bg=SURFACE,
            fg=TEXT,
            font=(self.font_family, 9),
            justify="left",
            wraplength=520,
        ).pack(anchor="w", pady=(6, 0))

        actions_outer = self._surface(self.home_tab, padding=12)
        actions_outer.pack(fill="x", pady=(14, 0))
        actions = actions_outer.inner  # type: ignore[attr-defined]
        self.scan_all_button = ttk.Button(
            actions, text="Verificar todas agora", style="Primary.TButton", command=self._start_scan_all
        )
        self.scan_all_button.pack(side="left")
        ttk.Button(
            actions,
            text="Verificar BSDG selecionada",
            style="Secondary.TButton",
            command=self._start_scan_selected,
        ).pack(side="left", padx=8)
        self.cancel_button = ttk.Button(
            actions, text="Cancelar", style="Danger.TButton", command=self._cancel_scan, state="disabled"
        )
        self.cancel_button.pack(side="left")
        ttk.Button(
            actions,
            text="Abrir pasta da aplicação",
            style="Neutral.TButton",
            command=lambda: self._open_path(app_data_dir()),
        ).pack(side="right")

        summary_outer = self._surface(self.home_tab, padding=0)
        summary_outer.pack(fill="both", expand=True, pady=(14, 0))
        summary = summary_outer.inner  # type: ignore[attr-defined]
        heading = tk.Frame(summary, bg=PRIMARY_PALE)
        heading.pack(fill="x")
        tk.Label(
            heading,
            text="Resumo da última execução",
            bg=PRIMARY_PALE,
            fg=PRIMARY_DARK,
            font=(self.font_family, 10, "bold"),
            padx=14,
            pady=9,
        ).pack(side="left")
        self.summary_text = tk.Text(
            summary,
            height=5,
            wrap="word",
            state="disabled",
            font=("Consolas", 9),
            bg=SURFACE,
            fg=TEXT,
            relief="flat",
            padx=14,
            pady=12,
            highlightthickness=0,
        )
        self.summary_text.pack(fill="both", expand=True)

    def _build_bsdg_tab(self) -> None:
        self._section_intro(
            self.bsdg_tab,
            "BSDGs monitoradas",
            "Associe cada BSDG à pasta sincronizada pelo OneDrive e defina quais entradas serão percorridas recursivamente.",
        )

        tree_outer = self._surface(self.bsdg_tab, padding=0)
        tree_outer.pack(fill="both", expand=True)
        tree_frame = tree_outer.inner  # type: ignore[attr-defined]

        columns = ("name", "path", "enabled", "recursive", "status")
        self.bsdg_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        headings = {
            "name": "BSDG",
            "path": "Pasta local sincronizada",
            "enabled": "Monitorar",
            "recursive": "Subpastas",
            "status": "Situação",
        }
        widths = {"name": 200, "path": 520, "enabled": 85, "recursive": 85, "status": 175}
        for key in columns:
            self.bsdg_tree.heading(key, text=headings[key])
            self.bsdg_tree.column(key, width=widths[key], anchor="w", stretch=key in {"name", "path", "status"})

        yscroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.bsdg_tree.yview)
        xscroll = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.bsdg_tree.xview)
        self.bsdg_tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.bsdg_tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        self.bsdg_tree.bind("<Double-1>", lambda _event: self._select_bsdg_folder())
        self.bsdg_tree.tag_configure("available", background="#F8FCF5")
        self.bsdg_tree.tag_configure("missing", background="#FFF3F3", foreground=ERROR)
        self.bsdg_tree.tag_configure("unconfigured", background="#FFF9E8", foreground=WARNING_FG)

        buttons_outer = self._surface(self.bsdg_tab, padding=10)
        buttons_outer.pack(fill="x", pady=(12, 0))
        buttons = buttons_outer.inner  # type: ignore[attr-defined]
        ttk.Button(buttons, text="Adicionar BSDG", style="Primary.TButton", command=self._add_bsdg).pack(side="left")
        ttk.Button(buttons, text="Renomear", style="Neutral.TButton", command=self._rename_bsdg).pack(side="left", padx=5)
        ttk.Button(buttons, text="Selecionar pasta", style="Secondary.TButton", command=self._select_bsdg_folder).pack(side="left", padx=5)
        ttk.Button(buttons, text="Ativar/Desativar", style="Neutral.TButton", command=self._toggle_bsdg).pack(side="left", padx=5)
        ttk.Button(buttons, text="Subpastas: Sim/Não", style="Neutral.TButton", command=self._toggle_recursive).pack(side="left", padx=5)
        ttk.Button(buttons, text="Remover", style="Danger.TButton", command=self._remove_bsdg).pack(side="right")

    def _build_schedule_tab(self) -> None:
        self._section_intro(
            self.schedule_tab,
            "Agendamento semanal",
            "Configure a execução automática pelo Agendador de Tarefas do Windows, incluindo as pastas de saída dos relatórios e logs.",
        )

        layout = tk.Frame(self.schedule_tab, bg=BACKGROUND)
        layout.pack(fill="both", expand=True)
        layout.grid_columnconfigure(0, weight=3, uniform="schedule")
        layout.grid_columnconfigure(1, weight=2, uniform="schedule")

        config_outer = self._surface(layout, padding=18)
        config_outer.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        panel = config_outer.inner  # type: ignore[attr-defined]
        panel.grid_columnconfigure(1, weight=1)

        tk.Label(panel, text="CONFIGURAÇÃO DA TAREFA", bg=SURFACE, fg=PRIMARY_DARK, font=(self.font_family, 9, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 14)
        )

        self.schedule_enabled_var = tk.BooleanVar(value=self.config_data.schedule.enabled)
        check = ttk.Checkbutton(panel, text="Ativar verificação semanal", variable=self.schedule_enabled_var)
        check.grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 14))

        tk.Label(panel, text="Dia da semana", bg=SURFACE, fg=TEXT, font=(self.font_family, 9, "bold")).grid(
            row=2, column=0, sticky="w", pady=6
        )
        self.day_var = tk.StringVar(value=DAY_NAMES_BY_CODE.get(self.config_data.schedule.day, "Sexta-feira"))
        self.day_combo = ttk.Combobox(panel, textvariable=self.day_var, values=list(DAY_CODES), state="readonly", width=24)
        self.day_combo.grid(row=2, column=1, sticky="w", padx=(12, 0))

        tk.Label(panel, text="Horário", bg=SURFACE, fg=TEXT, font=(self.font_family, 9, "bold")).grid(
            row=3, column=0, sticky="w", pady=6
        )
        hour, minute = self.config_data.schedule.time.split(":", 1)
        self.hour_var = tk.StringVar(value=hour)
        self.minute_var = tk.StringVar(value=minute)
        time_frame = tk.Frame(panel, bg=SURFACE)
        time_frame.grid(row=3, column=1, sticky="w", padx=(12, 0))
        ttk.Spinbox(time_frame, from_=0, to=23, textvariable=self.hour_var, width=4, format="%02.0f").pack(side="left")
        tk.Label(time_frame, text=":", bg=SURFACE, fg=TEXT, font=(self.font_family, 11, "bold")).pack(side="left", padx=5)
        ttk.Spinbox(time_frame, from_=0, to=59, textvariable=self.minute_var, width=4, format="%02.0f").pack(side="left")

        default_reports = self.config_data.schedule.reports_output_dir or self.config_data.reports.reports_output_dir or str(reports_dir())
        default_logs = self.config_data.schedule.logs_output_dir or self.config_data.reports.logs_output_dir or str(logs_dir())
        self.schedule_reports_dir_var = tk.StringVar(value=default_reports)
        self.schedule_logs_dir_var = tk.StringVar(value=default_logs)

        tk.Label(panel, text="Pasta dos relatórios", bg=SURFACE, fg=TEXT, font=(self.font_family, 9, "bold")).grid(
            row=4, column=0, sticky="w", pady=6
        )
        ttk.Entry(panel, textvariable=self.schedule_reports_dir_var, width=58).grid(
            row=4, column=1, sticky="ew", padx=(12, 8), pady=4
        )
        ttk.Button(panel, text="Selecionar...", style="Neutral.TButton", command=self._browse_schedule_reports_dir).grid(
            row=4, column=2, sticky="e", pady=4
        )

        tk.Label(panel, text="Pasta dos logs", bg=SURFACE, fg=TEXT, font=(self.font_family, 9, "bold")).grid(
            row=5, column=0, sticky="w", pady=6
        )
        ttk.Entry(panel, textvariable=self.schedule_logs_dir_var, width=58).grid(
            row=5, column=1, sticky="ew", padx=(12, 8), pady=4
        )
        ttk.Button(panel, text="Selecionar...", style="Neutral.TButton", command=self._browse_schedule_logs_dir).grid(
            row=5, column=2, sticky="e", pady=4
        )

        button_frame = tk.Frame(panel, bg=SURFACE)
        button_frame.grid(row=6, column=0, columnspan=3, sticky="w", pady=(20, 0))
        ttk.Button(
            button_frame,
            text="Salvar e instalar agendamento",
            style="Primary.TButton",
            command=self._install_schedule,
        ).pack(side="left")
        ttk.Button(
            button_frame, text="Remover agendamento", style="Danger.TButton", command=self._remove_schedule
        ).pack(side="left", padx=8)
        ttk.Button(
            button_frame, text="Consultar no Windows", style="Neutral.TButton", command=self._query_schedule
        ).pack(side="left")

        info_outer = self._surface(layout, padding=18)
        info_outer.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        info = info_outer.inner  # type: ignore[attr-defined]
        tk.Label(info, text="COMO FUNCIONA", bg=SURFACE, fg=PRIMARY_DARK, font=(self.font_family, 9, "bold")).pack(anchor="w")
        explanation = (
            "• O Windows inicia o verificador no dia e horário definidos.\n\n"
            "• Os relatórios e logs são gravados nas pastas escolhidas nesta tela.\n\n"
            "• O usuário deve estar conectado e o OneDrive precisa estar disponível.\n\n"
            "• O aplicativo não acessa o SharePoint diretamente; ele lê as pastas sincronizadas no computador.\n\n"
            "• Cada computador precisa instalar seu próprio agendamento."
        )
        tk.Label(
            info,
            text=explanation,
            bg=SURFACE,
            fg=TEXT,
            font=(self.font_family, 9),
            justify="left",
            wraplength=400,
        ).pack(anchor="w", pady=(12, 0))

        status_outer = self._surface(self.schedule_tab, padding=14)
        status_outer.pack(fill="x", pady=(14, 0))
        status_inner = status_outer.inner  # type: ignore[attr-defined]
        tk.Label(
            status_inner,
            text="STATUS DO AGENDAMENTO",
            bg=SURFACE,
            fg=PRIMARY_DARK,
            font=(self.font_family, 8, "bold"),
        ).pack(anchor="w")
        self.schedule_status_var = tk.StringVar(value="")
        tk.Label(
            status_inner,
            textvariable=self.schedule_status_var,
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=(self.font_family, 9),
            justify="left",
            wraplength=1100,
        ).pack(fill="x", anchor="w", pady=(6, 0))

    def _build_results_tab(self) -> None:
        self._section_intro(
            self.results_tab,
            "Resultados e registros",
            "Consulte os GeoPackages inventariados, seus estados de atualização e a validação estrutural das camadas.",
        )

        toolbar_outer = self._surface(self.results_tab, padding=10)
        toolbar_outer.pack(fill="x", pady=(0, 12))
        toolbar = toolbar_outer.inner  # type: ignore[attr-defined]
        ttk.Button(toolbar, text="Atualizar tabela", style="Primary.TButton", command=self._refresh_results).pack(side="left")
        ttk.Button(toolbar, text="Abrir relatórios", style="Secondary.TButton", command=self._open_reports_directory).pack(side="left", padx=5)
        ttk.Button(toolbar, text="Abrir logs", style="Neutral.TButton", command=self._open_logs_directory).pack(side="left", padx=5)
        ttk.Button(toolbar, text="Abrir arquivo selecionado", style="Neutral.TButton", command=self._open_selected_file).pack(side="left", padx=5)

        tree_outer = self._surface(self.results_tab, padding=0)
        tree_outer.pack(fill="both", expand=True)
        tree_frame = tree_outer.inner  # type: ignore[attr-defined]

        columns = ("bsdg", "category", "file", "status", "validation", "geometry", "srid", "modified", "size")
        self.result_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        headings = {
            "bsdg": "BSDG",
            "category": "Categoria",
            "file": "Arquivo",
            "status": "Situação",
            "validation": "Validação",
            "geometry": "Geometria(s)",
            "srid": "SRID(s)",
            "modified": "Modificado em",
            "size": "Tamanho",
        }
        widths = {
            "bsdg": 135,
            "category": 105,
            "file": 240,
            "status": 130,
            "validation": 120,
            "geometry": 140,
            "srid": 80,
            "modified": 150,
            "size": 80,
        }
        for key in columns:
            self.result_tree.heading(key, text=headings[key])
            self.result_tree.column(key, width=widths[key], anchor="w", stretch=key in {"bsdg", "file", "geometry"})

        yscroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.result_tree.yview)
        xscroll = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.result_tree.xview)
        self.result_tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.result_tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        self.result_tree.bind("<Double-1>", lambda _event: self._open_selected_file())
        self.result_tree.tag_configure("valid", background="#F6FBF2")
        self.result_tree.tag_configure("warning", background="#FFF9E8")
        self.result_tree.tag_configure("invalid", background="#FFF1F1", foreground=ERROR)

    def _refresh_all(self) -> None:
        self.config_data = self.config_manager.load()
        self._refresh_bsdgs()
        self._refresh_dashboard()
        self._refresh_results()

    def _refresh_dashboard(self) -> None:
        stats = self.inventory.dashboard_stats()
        # O catálogo e a disponibilidade das pastas vêm da configuração atual;
        # o SQLite fornece a quantidade de GeoPackages já inventariados.
        stats["total_bsdgs"] = len(self.config_data.bsdgs)
        stats["enabled_bsdgs"] = sum(item.enabled for item in self.config_data.bsdgs)
        stats["missing_bsdgs"] = sum(
            item.enabled and (not item.local_path or not Path(item.local_path).is_dir())
            for item in self.config_data.bsdgs
        )
        for key, var in self.metric_vars.items():
            var.set(str(stats.get(key, 0)))

        latest = self.inventory.latest_run()
        if latest:
            run_datetime = self._format_run_datetime(latest.get("completed_at") or latest.get("started_at"))
            self.last_run_var.set(
                f"Última execução: {run_datetime} | "
                f"Resultado: {latest.get('outcome')} | Arquivos: {latest.get('total_files')}"
            )
        else:
            self.last_run_var.set("Nenhuma verificação registrada.")

        if self.config_data.schedule.enabled:
            day = DAY_NAMES_BY_CODE.get(self.config_data.schedule.day, self.config_data.schedule.day)
            reports_path = self.config_data.schedule.reports_output_dir or str(reports_dir())
            logs_path = self.config_data.schedule.logs_output_dir or str(logs_dir())
            self.next_run_var.set(
                f"Agendamento configurado: {day}, às {self.config_data.schedule.time}. "
                f"Relatórios: {reports_path} | Logs: {logs_path}"
            )
        else:
            self.next_run_var.set("Agendamento não instalado.")

    def _refresh_bsdgs(self) -> None:
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
                    bsdg.name,
                    bsdg.local_path or "—",
                    "Sim" if bsdg.enabled else "Não",
                    "Sim" if bsdg.recursive else "Não",
                    status,
                ),
            )

    def _refresh_results(self) -> None:
        for item_id in self.result_tree.get_children():
            self.result_tree.delete(item_id)
        for row in self.inventory.list_files(limit=5000):
            validation = {}
            try:
                validation = json.loads(row.get("validation_json") or "{}")
            except Exception:
                pass
            geometries = sorted(
                {
                    layer.get("geometry_type")
                    for layer in validation.get("layers", [])
                    if layer.get("geometry_type")
                }
            )
            srids = sorted(
                {
                    str(layer.get("srs_id"))
                    for layer in validation.get("layers", [])
                    if layer.get("srs_id") is not None
                }
            )
            validation_status = str(row.get("validation_status", ""))
            display_status = str(row.get("display_status", ""))
            comparable = f"{validation_status} {display_status}".upper()
            if any(token in comparable for token in ("INVÁL", "INVALID", "ERRO", "INACESS")):
                tag = "invalid"
            elif any(token in comparable for token in ("NUVEM", "ATENÇÃO", "REMOVID")):
                tag = "warning"
            else:
                tag = "valid"
            self.result_tree.insert(
                "",
                "end",
                iid=str(row["id"]),
                tags=(tag,),
                values=(
                    row.get("bsdg_name", ""),
                    row.get("category", ""),
                    row.get("file_name", ""),
                    display_status,
                    validation_status,
                    ", ".join(geometries),
                    ", ".join(srids),
                    row.get("modified_iso", ""),
                    self._format_size(int(row.get("size_bytes", 0))),
                ),
            )

    def _configured_reports_directory(self) -> Path:
        value = self.config_data.reports.reports_output_dir
        return Path(value).expanduser() if value else reports_dir()

    def _configured_logs_directory(self) -> Path:
        value = self.config_data.reports.logs_output_dir
        return Path(value).expanduser() if value else logs_dir()

    def _latest_run_payload(self) -> dict[str, object]:
        latest = self.inventory.latest_run()
        if not latest:
            return {}
        try:
            return json.loads(latest.get("summary_json") or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}

    def _open_reports_directory(self) -> None:
        payload = self._latest_run_payload()
        report_paths = payload.get("report_paths", [])
        if isinstance(report_paths, list) and report_paths:
            path = Path(str(report_paths[0])).expanduser().parent
        else:
            path = self._configured_reports_directory()
        path.mkdir(parents=True, exist_ok=True)
        self._open_path(path)

    def _open_logs_directory(self) -> None:
        payload = self._latest_run_payload()
        latest_log = payload.get("log_path", "")
        if latest_log:
            path = Path(str(latest_log)).expanduser().parent
        else:
            path = self._configured_logs_directory()
        path.mkdir(parents=True, exist_ok=True)
        self._open_path(path)

    def _browse_schedule_reports_dir(self) -> None:
        initial = self.schedule_reports_dir_var.get().strip() or str(self._configured_reports_directory())
        folder = filedialog.askdirectory(
            title="Selecionar pasta para os relatórios agendados",
            initialdir=initial if Path(initial).exists() else str(Path.home()),
            parent=self,
        )
        if folder:
            self.schedule_reports_dir_var.set(folder)

    def _browse_schedule_logs_dir(self) -> None:
        initial = self.schedule_logs_dir_var.get().strip() or str(self._configured_logs_directory())
        folder = filedialog.askdirectory(
            title="Selecionar pasta para os logs agendados",
            initialdir=initial if Path(initial).exists() else str(Path.home()),
            parent=self,
        )
        if folder:
            self.schedule_logs_dir_var.set(folder)

    def _validate_output_directory(self, path: Path, label: str) -> bool:
        if not str(path).strip() or str(path) == ".":
            messagebox.showerror(
                "Pasta de saída obrigatória",
                f"Selecione uma pasta válida para {label}.",
                parent=self,
            )
            return False
        try:
            path.mkdir(parents=True, exist_ok=True)
            test_path = path / ".bsdgs_verificador_teste_escrita.tmp"
            test_path.write_text("teste", encoding="utf-8")
            test_path.unlink(missing_ok=True)
            return True
        except OSError as exc:
            messagebox.showerror(
                "Pasta sem permissão de gravação",
                f"Não foi possível usar a pasta escolhida para {label}:\n\n{path}\n\n"
                f"Escolha outra pasta com permissão de gravação.\n\nDetalhe: {exc}",
                parent=self,
            )
            return False

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
            text="As pastas selecionadas serão usadas somente após sua confirmação e ficarão preenchidas como padrão na próxima execução.",
            bg=PRIMARY_PALE,
            fg=TEXT,
            font=(self.font_family, 9),
            justify="left",
            wraplength=680,
        ).pack(anchor="w", pady=(5, 0))

        content = tk.Frame(window, bg=SURFACE, padx=22, pady=20)
        content.pack(fill="both", expand=True)
        content.grid_columnconfigure(1, weight=1)

        tk.Label(content, text="Pasta dos relatórios", bg=SURFACE, fg=TEXT, font=(self.font_family, 9, "bold")).grid(
            row=0, column=0, sticky="w", pady=8
        )
        ttk.Entry(content, textvariable=reports_var, width=68).grid(row=0, column=1, sticky="ew", padx=(12, 8), pady=8)

        def browse_reports() -> None:
            initial = reports_var.get().strip()
            folder = filedialog.askdirectory(
                title="Selecionar pasta para os relatórios",
                initialdir=initial if initial and Path(initial).exists() else str(Path.home()),
                parent=window,
            )
            if folder:
                reports_var.set(folder)

        ttk.Button(content, text="Selecionar...", style="Neutral.TButton", command=browse_reports).grid(
            row=0, column=2, sticky="e", pady=8
        )

        tk.Label(content, text="Pasta dos logs", bg=SURFACE, fg=TEXT, font=(self.font_family, 9, "bold")).grid(
            row=1, column=0, sticky="w", pady=8
        )
        ttk.Entry(content, textvariable=logs_var, width=68).grid(row=1, column=1, sticky="ew", padx=(12, 8), pady=8)

        def browse_logs() -> None:
            initial = logs_var.get().strip()
            folder = filedialog.askdirectory(
                title="Selecionar pasta para os logs",
                initialdir=initial if initial and Path(initial).exists() else str(Path.home()),
                parent=window,
            )
            if folder:
                logs_var.set(folder)

        ttk.Button(content, text="Selecionar...", style="Neutral.TButton", command=browse_logs).grid(
            row=1, column=2, sticky="e", pady=8
        )

        tk.Label(
            content,
            text="O programa criará as pastas quando necessário e verificará se há permissão de gravação.",
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=(self.font_family, 8),
            justify="left",
        ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(4, 14))

        buttons = tk.Frame(content, bg=SURFACE)
        buttons.grid(row=3, column=0, columnspan=3, sticky="ew")

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
            if hasattr(self, "schedule_reports_dir_var"):
                self.schedule_reports_dir_var.set(str(report_path))
            if hasattr(self, "schedule_logs_dir_var"):
                self.schedule_logs_dir_var.set(str(log_path))
            result["reports"] = report_path
            result["logs"] = log_path
            window.destroy()

        ttk.Button(buttons, text="Cancelar", style="Neutral.TButton", command=window.destroy).pack(side="right")
        ttk.Button(buttons, text="Confirmar e iniciar", style="Primary.TButton", command=confirm).pack(side="right", padx=(0, 8))

        window.protocol("WM_DELETE_WINDOW", window.destroy)
        window.update_idletasks()
        x = self.winfo_rootx() + max(0, (self.winfo_width() - window.winfo_width()) // 2)
        y = self.winfo_rooty() + max(0, (self.winfo_height() - window.winfo_height()) // 2)
        window.geometry(f"+{x}+{y}")
        self.wait_window(window)

        if "reports" not in result or "logs" not in result:
            return None
        return result["reports"], result["logs"]

    @staticmethod
    def _format_run_datetime(value: object) -> str:
        if not value:
            return "data e hora indisponíveis"
        text = str(value)
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.astimezone()
            offset = parsed.utcoffset()
            if offset is None:
                utc_label = "UTC"
            else:
                total_minutes = int(offset.total_seconds() // 60)
                sign = "+" if total_minutes >= 0 else "-"
                absolute_minutes = abs(total_minutes)
                hours, minutes = divmod(absolute_minutes, 60)
                utc_label = f"UTC{sign}{hours:02d}:{minutes:02d}"
            return f"{parsed:%d/%m/%Y às %H:%M:%S} ({utc_label})"
        except (ValueError, TypeError):
            return text

    def _start_scan_all(self) -> None:
        self._start_scan(None)

    def _start_scan_selected(self) -> None:
        selection = self.bsdg_tree.selection()
        if not selection:
            self.notebook.select(self.bsdg_tab)
            messagebox.showinfo("Selecionar BSDG", "Selecione uma BSDG na tabela e tente novamente.")
            return
        selected = next((item for item in self.config_data.bsdgs if item.id == selection[0]), None)
        if selected and not selected.enabled:
            if not messagebox.askyesno(
                "BSDG desativada",
                f"'{selected.name}' não está marcada para monitoramento. Ativar e verificar agora?",
            ):
                return
            selected.enabled = True
            self.config_manager.save(self.config_data)
            self._refresh_bsdgs()
        self._start_scan({selection[0]})

    def _start_scan(self, selected_ids: set[str] | None) -> None:
        if self.scan_thread and self.scan_thread.is_alive():
            messagebox.showinfo("Verificação em andamento", "Aguarde a conclusão da verificação atual.")
            return

        output_locations = self._ask_output_locations()
        if output_locations is None:
            self.status_var.set("Verificação cancelada antes do início.")
            return
        report_output_dir, log_output_dir = output_locations

        self.cancel_event.clear()
        self.progress.configure(value=0, maximum=1)
        self.status_var.set("Preparando a varredura...")
        self.scan_all_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.log_path = configure_logging(
            console=False,
            explicit_path=log_output_dir / f"verificacao_{datetime.now():%Y%m%d_%H%M%S}.log",
        )

        def worker() -> None:
            try:
                summary = self.service.run_scan(
                    selected_bsdg_ids=selected_ids,
                    mode="MANUAL",
                    progress_callback=lambda payload: self.events.put(("progress", payload)),
                    cancel_event=self.cancel_event,
                    log_path=str(self.log_path),
                    report_output_dir=report_output_dir,
                )
                self.events.put(("done", summary))
            except Exception as exc:
                self.events.put(("error", exc))

        self.scan_thread = threading.Thread(target=worker, daemon=True)
        self.scan_thread.start()

    def _cancel_scan(self) -> None:
        self.cancel_event.set()
        self.status_var.set("Cancelamento solicitado; concluindo a operação atual...")

    def _poll_events(self) -> None:
        try:
            while True:
                event, payload = self.events.get_nowait()
                if event == "progress":
                    data = payload  # type: ignore[assignment]
                    total = max(1, int(data.get("total", 1)))
                    current = int(data.get("current", 0))
                    self.progress.configure(maximum=total, value=current)
                    self.status_var.set(str(data.get("message", "Verificando...")))
                elif event == "done":
                    self._scan_finished(payload)
                elif event == "error":
                    self._scan_failed(payload)
        except queue.Empty:
            pass
        self.after(150, self._poll_events)

    def _scan_finished(self, summary: object) -> None:
        self.last_summary = summary
        self.scan_all_button.configure(state="normal")
        self.cancel_button.configure(state="disabled")
        self.status_var.set("Verificação concluída.")
        self.progress.configure(value=self.progress["maximum"])
        self._refresh_all()
        data = summary.to_dict()  # type: ignore[attr-defined]
        text = (
            f"Execução: {data['run_id']}\n"
            f"Resultado: {data['outcome']}\n"
            f"BSDGs verificadas: {data['scanned_bsdgs']} | indisponíveis: {data['missing_bsdgs']}\n"
            f"Arquivos: {data['total_files']} | novos: {data['new_files']} | modificados: {data['modified_files']}\n"
            f"Sem alteração: {data['unchanged_files']} | removidos: {data['removed_files']}\n"
            f"Válidos: {data['valid_files']} | inválidos/erro: {data['invalid_files']}\n"
            f"Somente na nuvem: {data['online_only_files']} | inacessíveis: {data['inaccessible_files']}\n"
            f"Relatórios: {len(data['report_paths'])}"
            + (f" | Pasta: {Path(data['report_paths'][0]).parent}" if data['report_paths'] else "")
            + "\n"
            f"Log: {data['log_path']}"
        )
        attention_items = [
            item for item in data.get("bsdg_summaries", [])
            if item.get("message")
        ]
        if attention_items:
            text += "\n\nAtenções:\n" + "\n".join(
                f"- {item.get('bsdg_name')}: {item.get('message')}"
                for item in attention_items
            )
        self._set_summary_text(text)
        if data["total_files"] == 0 and data["scanned_bsdgs"] > 0:
            messagebox.showwarning(
                "Verificação concluída sem arquivos",
                text
                + "\n\nO programa executou a varredura, mas não encontrou GeoPackages. "
                "Verifique a opção Subpastas e a disponibilidade local no OneDrive.",
            )
        else:
            messagebox.showinfo("Verificação concluída", text)

    def _scan_failed(self, error: object) -> None:
        self.scan_all_button.configure(state="normal")
        self.cancel_button.configure(state="disabled")
        self.status_var.set("A verificação não pôde ser concluída.")
        messagebox.showerror(
            "Não foi possível concluir",
            "Ocorreu um erro inesperado. Nenhum conhecimento técnico é necessário para continuar.\n\n"
            f"Consulte o log em:\n{self.log_path}\n\nDetalhe: {error}",
        )

    def _set_summary_text(self, text: str) -> None:
        self.summary_text.configure(state="normal")
        self.summary_text.delete("1.0", "end")
        self.summary_text.insert("1.0", text)
        self.summary_text.configure(state="disabled")

    def _selected_bsdg(self) -> BsdgConfig | None:
        selection = self.bsdg_tree.selection()
        if not selection:
            messagebox.showinfo("Selecionar BSDG", "Selecione uma BSDG na tabela.")
            return None
        return next((item for item in self.config_data.bsdgs if item.id == selection[0]), None)

    def _add_bsdg(self) -> None:
        name = simpledialog.askstring("Adicionar BSDG", "Nome da BSDG:", parent=self)
        if not name:
            return
        folder = filedialog.askdirectory(title="Selecione a pasta local da BSDG")
        item = BsdgConfig(id=f"bsdg-{uuid.uuid4().hex[:12]}", name=name.strip(), local_path=folder, enabled=bool(folder))
        self.config_data.bsdgs.append(item)
        self.config_manager.save(self.config_data)
        self._refresh_bsdgs()

    def _rename_bsdg(self) -> None:
        item = self._selected_bsdg()
        if not item:
            return
        name = simpledialog.askstring("Renomear BSDG", "Novo nome:", initialvalue=item.name, parent=self)
        if not name:
            return
        item.name = name.strip()
        item.needs_name_confirmation = False
        self.config_manager.save(self.config_data)
        self._refresh_bsdgs()

    def _select_bsdg_folder(self) -> None:
        item = self._selected_bsdg()
        if not item:
            return
        folder = filedialog.askdirectory(
            title=f"Selecionar pasta de {item.name}",
            initialdir=item.local_path if item.local_path and Path(item.local_path).exists() else str(Path.home()),
        )
        if not folder:
            return
        item.local_path = folder
        item.enabled = True
        self.config_manager.save(self.config_data)
        self._refresh_bsdgs()
        self._refresh_dashboard()

    def _toggle_bsdg(self) -> None:
        item = self._selected_bsdg()
        if not item:
            return
        item.enabled = not item.enabled
        self.config_manager.save(self.config_data)
        self._refresh_bsdgs()
        self._refresh_dashboard()

    def _toggle_recursive(self) -> None:
        item = self._selected_bsdg()
        if not item:
            return
        item.recursive = not item.recursive
        self.config_manager.save(self.config_data)
        self._refresh_bsdgs()

    def _remove_bsdg(self) -> None:
        item = self._selected_bsdg()
        if not item:
            return
        if not messagebox.askyesno("Remover BSDG", f"Remover '{item.name}' do catálogo local?\n\nO conteúdo no SharePoint não será alterado."):
            return
        self.config_data.bsdgs = [entry for entry in self.config_data.bsdgs if entry.id != item.id]
        self.config_manager.save(self.config_data)
        self._refresh_bsdgs()
        self._refresh_dashboard()

    def _install_schedule(self) -> None:
        try:
            hour = int(self.hour_var.get())
            minute = int(self.minute_var.get())
            time_value = f"{hour:02d}:{minute:02d}"
        except ValueError:
            messagebox.showerror("Horário inválido", "Informe hora e minuto válidos.")
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

        result = self.scheduler.install_weekly(day_code, time_value)
        details = (
            f"{result.message}\nRelatórios: {report_path}\nLogs: {log_path}"
            + (f"\n{result.raw_output}" if result.raw_output else "")
        )
        self.schedule_status_var.set(details)
        if result.success:
            self.config_data.schedule.enabled = True
            self.schedule_enabled_var.set(True)
            self.config_manager.save(self.config_data)
            self._refresh_dashboard()
            messagebox.showinfo("Agendamento", details)
        else:
            messagebox.showerror("Agendamento", details)

    def _remove_schedule(self) -> None:
        result = self.scheduler.remove()
        self.schedule_status_var.set(result.message + (f"\n{result.raw_output}" if result.raw_output else ""))
        if result.success:
            self.config_data.schedule.enabled = False
            self.schedule_enabled_var.set(False)
            self.config_manager.save(self.config_data)
            self._refresh_dashboard()
            messagebox.showinfo("Agendamento", result.message)
        else:
            messagebox.showerror("Agendamento", result.message + (f"\n\n{result.raw_output}" if result.raw_output else ""))

    def _query_schedule(self) -> None:
        result = self.scheduler.query()
        self.schedule_status_var.set(result.message + (f"\n{result.raw_output}" if result.raw_output else ""))
        messagebox.showinfo("Consulta do agendamento", result.message + (f"\n\n{result.raw_output}" if result.raw_output else ""))

    def _create_branded_dialog(self, title: str, *, width: int = 760, height: int = 125) -> tuple[tk.Toplevel, tk.Frame]:
        window = tk.Toplevel(self)
        window.title(f"{title} — {APP_NAME}")
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

        header = tk.Canvas(window, width=width, height=height, bg=SURFACE, highlightthickness=0)
        header.pack(fill="x")
        bg = self._asset_images.get("header_bg")
        if bg is not None:
            header.create_image(0, 0, image=bg, anchor="nw")
        logo = self._asset_images.get("logo_about")
        if logo is not None:
            header.create_image(22, 18, image=logo, anchor="nw")

        content = tk.Frame(window, bg=SURFACE, padx=26, pady=20)
        content.pack(fill="both", expand=True)
        tk.Label(
            content,
            text=APP_NAME,
            bg=SURFACE,
            fg=TEXT,
            font=(self.font_family, 18, "bold"),
        ).pack(anchor="w")
        tk.Label(
            content,
            text=f"Versão {APP_VERSION}",
            bg=PRIMARY_LIGHT,
            fg=PRIMARY_DARK,
            font=(self.font_family, 9, "bold"),
            padx=10,
            pady=4,
        ).pack(anchor="w", pady=(6, 14))
        return window, content

    def _finalize_dialog(self, window: tk.Toplevel, content: tk.Frame) -> None:
        buttons = tk.Frame(content, bg=SURFACE)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Site do LAGEAMB", style="Secondary.TButton", command=self._open_lageamb_site).pack(side="left")
        ttk.Button(buttons, text="GitHub", style="Neutral.TButton", command=self._open_developer_github).pack(side="left", padx=7)
        ttk.Button(buttons, text="Fechar", style="Primary.TButton", command=window.destroy).pack(side="right")

        window.update_idletasks()
        x = self.winfo_rootx() + max(0, (self.winfo_width() - window.winfo_width()) // 2)
        y = self.winfo_rooty() + max(0, (self.winfo_height() - window.winfo_height()) // 2)
        window.geometry(f"+{x}+{y}")

    def _show_how_to_use(self) -> None:
        window, content = self._create_branded_dialog("Como usar")

        intro = (
            "Guia rápido para uso local do verificador. Esta aplicação funciona somente com pastas já "
            "sincronizadas pelo OneDrive/SharePoint neste computador."
        )
        tk.Label(
            content,
            text=intro,
            bg=SURFACE,
            fg=TEXT,
            font=(self.font_family, 9),
            wraplength=640,
            justify="left",
        ).pack(anchor="w")

        divider = tk.Frame(content, bg=BORDER, height=1)
        divider.pack(fill="x", pady=16)

        steps_outer = tk.Frame(content, bg=BORDER)
        steps_outer.pack(fill="both", expand=True)
        steps_inner = tk.Frame(steps_outer, bg=PRIMARY_PALE)
        steps_inner.pack(fill="both", expand=True, padx=1, pady=1)

        text_frame = tk.Frame(steps_inner, bg=PRIMARY_PALE)
        text_frame.pack(fill="both", expand=True)
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical")
        text_widget = tk.Text(
            text_frame,
            wrap="word",
            yscrollcommand=scrollbar.set,
            font=(self.font_family, 9),
            bg=PRIMARY_PALE,
            fg=TEXT,
            relief="flat",
            highlightthickness=0,
            padx=14,
            pady=14,
            width=78,
            height=18,
        )
        scrollbar.config(command=text_widget.yview)
        scrollbar.pack(side="right", fill="y")
        text_widget.pack(side="left", fill="both", expand=True)

        instructions = (
            "1. Confirme a sincronização local\n"
            "Abra o OneDrive/Explorador de Arquivos e verifique se as pastas das BSDGs e os arquivos .gpkg estão disponíveis localmente nesta máquina.\n\n"
            "2. Cadastre ou revise as BSDGs monitoradas\n"
            "Na aba 'BSDGs monitoradas', confira se cada BSDG aponta para a pasta correta. Use 'Selecionar pasta' quando necessário.\n\n"
            "3. Defina se a verificação deve entrar em subpastas\n"
            "Se os GeoPackages estiverem dentro de subpastas da BSDG, deixe a opção 'Subpastas' ativada para aquela entrada.\n\n"
            "4. Execute a primeira varredura manual\n"
            "Na aba 'Início', clique em 'Verificar todas agora' para testar o funcionamento do sistema. Você também pode verificar apenas uma BSDG selecionada.\n\n"
            "5. Acompanhe o progresso e o resumo\n"
            "Durante a execução, observe a barra de progresso e o resumo da última execução. Ao final, o programa informa quantos arquivos foram encontrados, validados e sinalizados.\n\n"
            "6. Consulte os resultados detalhados\n"
            "Na aba 'Resultados e logs', veja a situação de cada arquivo, a validação estrutural, os tipos de geometria detectados e os SRIDs encontrados.\n\n"
            "7. Abra relatórios e logs quando necessário\n"
            "Use os botões 'Abrir relatórios' e 'Abrir logs' para acessar os arquivos gerados em cada verificação.\n\n"
            "8. Instale o agendamento semanal\n"
            "Na aba 'Agendamento', escolha o dia, o horário e as pastas de saída dos relatórios e logs. Depois clique em 'Salvar e instalar agendamento'. O Windows executará o programa automaticamente neste computador.\n\n"
            "9. Entenda as limitações\n"
            "O programa não acessa o SharePoint diretamente. Ele lê somente o que estiver sincronizado no seu computador. Arquivos apenas na nuvem podem ser sinalizados e não serão validados completamente.\n\n"
            "10. Boas práticas de uso\n"
            "Mantenha o OneDrive ativo, verifique periodicamente a disponibilidade local dos arquivos e rode uma verificação manual sempre que fizer grandes atualizações nas pastas monitoradas."
        )
        text_widget.insert("1.0", instructions)
        text_widget.configure(state="disabled")

        self._finalize_dialog(window, content)

    def _show_about(self) -> None:
        window, content = self._create_branded_dialog("Sobre")

        description = (
            "Aplicação desktop para inventário e validação estrutural de GeoPackages vinculados às "
            "Bases de Dados Geográficos do LAGEAMB.\n\n"
            + LOCAL_OPERATION_NOTICE
            + " Para a validação completa, os arquivos precisam estar disponíveis no dispositivo."
        )
        tk.Label(
            content,
            text=description,
            bg=SURFACE,
            fg=TEXT,
            font=(self.font_family, 9),
            wraplength=640,
            justify="left",
        ).pack(anchor="w")

        divider = tk.Frame(content, bg=BORDER, height=1)
        divider.pack(fill="x", pady=16)

        details = f"Desenvolvimento: {DEVELOPER_NAME}"
        tk.Label(
            content,
            text=details,
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=(self.font_family, 9),
            justify="left",
        ).pack(anchor="w")

        links = tk.Frame(content, bg=SURFACE)
        links.pack(fill="x", pady=(14, 18))
        lageamb_link = tk.Label(
            links,
            text=LAGEAMB_SITE_URL,
            bg=SURFACE,
            fg=PRIMARY_DARK,
            cursor="hand2",
            font=(self.font_family, 9, "underline"),
        )
        lageamb_link.pack(anchor="w")
        lageamb_link.bind("<Button-1>", lambda _event: self._open_lageamb_site())

        github_link = tk.Label(
            links,
            text=DEVELOPER_GITHUB_URL,
            bg=SURFACE,
            fg=PRIMARY_DARK,
            cursor="hand2",
            font=(self.font_family, 9, "underline"),
        )
        github_link.pack(anchor="w", pady=(4, 0))
        github_link.bind("<Button-1>", lambda _event: self._open_developer_github())

        self._finalize_dialog(window, content)

    @staticmethod
    def _open_lageamb_site() -> None:
        webbrowser.open(LAGEAMB_SITE_URL)

    @staticmethod
    def _open_developer_github() -> None:
        webbrowser.open(DEVELOPER_GITHUB_URL)

    def _open_selected_file(self) -> None:
        selection = self.result_tree.selection()
        if not selection:
            messagebox.showinfo("Selecionar arquivo", "Selecione um arquivo na tabela.")
            return
        row_id = selection[0]
        row = next((item for item in self.inventory.list_files(limit=5000) if str(item["id"]) == row_id), None)
        if not row:
            return
        self._open_path(Path(row["absolute_path"]).parent)

    @staticmethod
    def _open_path(path: Path) -> None:
        path = Path(path)
        try:
            if os.name == "nt":
                os.startfile(path)  # type: ignore[attr-defined]
            else:
                webbrowser.open(path.as_uri())
        except OSError as exc:
            messagebox.showerror("Não foi possível abrir", f"Caminho: {path}\n\n{exc}")

    @staticmethod
    def _format_size(size: int) -> str:
        value = float(size)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if value < 1024 or unit == "TB":
                return f"{value:.1f} {unit}"
            value /= 1024
        return f"{size} B"

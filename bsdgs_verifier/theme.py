from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont, ttk

# Paleta extraída da identidade visual fornecida pelo LAGEAMB/GeoLitoral.
PRIMARY = "#7DB34E"
PRIMARY_DARK = "#4F7F2E"
PRIMARY_DARKER = "#365B20"
PRIMARY_LIGHT = "#EAF3E1"
PRIMARY_PALE = "#F3F8EE"
BACKGROUND = "#F4F7F2"
SURFACE = "#FFFFFF"
SURFACE_ALT = "#F8FAF7"
TEXT = "#30343A"
TEXT_MUTED = "#6B7076"
BORDER = "#D8E0D3"
BORDER_STRONG = "#B8C8AE"
WARNING_BG = "#FFF5D6"
WARNING_FG = "#6A4B00"
ERROR = "#B23A3A"
SUCCESS = "#3F7F35"
INFO = "#356F8A"


def choose_font_family(root: tk.Misc) -> str:
    """Seleciona a fonte institucional quando instalada, com fallback seguro."""
    available = {name.casefold(): name for name in tkfont.families(root)}
    for candidate in ("Montserrat Alternates", "Montserrat", "Segoe UI"):
        if candidate.casefold() in available:
            return available[candidate.casefold()]
    return "TkDefaultFont"


def configure_ttk_style(root: tk.Misc, family: str) -> ttk.Style:
    style = ttk.Style(root)
    try:
        # O tema clam permite controlar cores com consistência no Windows.
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(".", font=(family, 10), background=BACKGROUND, foreground=TEXT)
    style.configure("App.TFrame", background=BACKGROUND)
    style.configure("Surface.TFrame", background=SURFACE)
    style.configure("Header.TFrame", background=SURFACE)

    style.configure("Title.TLabel", font=(family, 20, "bold"), background=SURFACE, foreground=TEXT)
    style.configure("SectionTitle.TLabel", font=(family, 14, "bold"), background=BACKGROUND, foreground=TEXT)
    style.configure("CardTitle.TLabel", font=(family, 11, "bold"), background=SURFACE, foreground=TEXT)
    style.configure("Subtitle.TLabel", font=(family, 10), background=SURFACE, foreground=TEXT_MUTED)
    style.configure("Body.TLabel", font=(family, 10), background=BACKGROUND, foreground=TEXT)
    style.configure("Muted.TLabel", font=(family, 9), background=BACKGROUND, foreground=TEXT_MUTED)
    style.configure("SurfaceBody.TLabel", font=(family, 10), background=SURFACE, foreground=TEXT)
    style.configure("SurfaceMuted.TLabel", font=(family, 9), background=SURFACE, foreground=TEXT_MUTED)
    style.configure("Metric.TLabel", font=(family, 24, "bold"), background=SURFACE, foreground=PRIMARY_DARK)
    style.configure("MetricCaption.TLabel", font=(family, 9), background=SURFACE, foreground=TEXT_MUTED)
    style.configure("Badge.TLabel", font=(family, 8, "bold"), background=PRIMARY_LIGHT, foreground=PRIMARY_DARK)

    style.configure(
        "Primary.TButton",
        font=(family, 10, "bold"),
        padding=(14, 8),
        background=PRIMARY,
        foreground="white",
        bordercolor=PRIMARY,
        lightcolor=PRIMARY,
        darkcolor=PRIMARY,
        relief="flat",
    )
    style.map(
        "Primary.TButton",
        background=[("disabled", "#B7C8A8"), ("pressed", PRIMARY_DARKER), ("active", PRIMARY_DARK)],
        foreground=[("disabled", "#F4F4F4"), ("!disabled", "white")],
    )

    style.configure(
        "Secondary.TButton",
        font=(family, 10, "bold"),
        padding=(12, 7),
        background=SURFACE,
        foreground=PRIMARY_DARK,
        bordercolor=PRIMARY,
        lightcolor=SURFACE,
        darkcolor=SURFACE,
        relief="solid",
    )
    style.map(
        "Secondary.TButton",
        background=[("pressed", PRIMARY_LIGHT), ("active", PRIMARY_PALE)],
        foreground=[("!disabled", PRIMARY_DARK)],
    )

    style.configure(
        "Neutral.TButton",
        font=(family, 9),
        padding=(10, 6),
        background="#EEF1EC",
        foreground=TEXT,
        bordercolor=BORDER,
        lightcolor="#EEF1EC",
        darkcolor="#EEF1EC",
    )
    style.map("Neutral.TButton", background=[("active", "#E4E9E1"), ("pressed", "#DCE3D7")])

    style.configure(
        "Danger.TButton",
        font=(family, 9, "bold"),
        padding=(10, 6),
        background=SURFACE,
        foreground=ERROR,
        bordercolor="#D7A6A6",
        lightcolor=SURFACE,
        darkcolor=SURFACE,
    )
    style.map("Danger.TButton", background=[("active", "#FFF0F0"), ("pressed", "#FADDDD")])

    style.configure("TNotebook", background=BACKGROUND, borderwidth=0, tabmargins=(0, 0, 0, 0))
    style.configure(
        "TNotebook.Tab",
        font=(family, 10, "bold"),
        padding=(18, 9),
        background="#E8EDE5",
        foreground=TEXT_MUTED,
        borderwidth=0,
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", PRIMARY), ("active", PRIMARY_LIGHT)],
        foreground=[("selected", "white"), ("active", PRIMARY_DARK)],
        expand=[("selected", (0, 0, 0, 2))],
    )

    style.configure(
        "Treeview",
        font=(family, 9),
        rowheight=30,
        background=SURFACE,
        fieldbackground=SURFACE,
        foreground=TEXT,
        bordercolor=BORDER,
        lightcolor=BORDER,
        darkcolor=BORDER,
    )
    style.map("Treeview", background=[("selected", PRIMARY_LIGHT)], foreground=[("selected", TEXT)])
    style.configure(
        "Treeview.Heading",
        font=(family, 9, "bold"),
        padding=(8, 7),
        background=PRIMARY_DARK,
        foreground="white",
        bordercolor=PRIMARY_DARK,
        relief="flat",
    )
    style.map("Treeview.Heading", background=[("active", PRIMARY)])

    style.configure(
        "Green.Horizontal.TProgressbar",
        troughcolor="#E1E7DD",
        background=PRIMARY,
        bordercolor="#E1E7DD",
        lightcolor=PRIMARY,
        darkcolor=PRIMARY,
    )

    style.configure("TLabelframe", background=BACKGROUND, bordercolor=BORDER, relief="solid", borderwidth=1)
    style.configure("TLabelframe.Label", font=(family, 10, "bold"), background=BACKGROUND, foreground=PRIMARY_DARK)

    style.configure("TCheckbutton", background=BACKGROUND, foreground=TEXT)
    style.map("TCheckbutton", background=[("active", BACKGROUND)])
    style.configure("TRadiobutton", background=BACKGROUND, foreground=TEXT)
    style.map("TRadiobutton", background=[("active", BACKGROUND)])

    style.configure("TEntry", padding=(6, 5), fieldbackground=SURFACE, bordercolor=BORDER_STRONG)
    style.configure("TCombobox", padding=(6, 5), fieldbackground=SURFACE, bordercolor=BORDER_STRONG)
    style.configure("TSpinbox", padding=(6, 5), fieldbackground=SURFACE, bordercolor=BORDER_STRONG)

    return style

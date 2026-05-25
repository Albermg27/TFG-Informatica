import tkinter as tk
from tkinter import ttk

from gui import theme

def configurar_estilos_ttk() -> None:
    style = ttk.Style()
    style.theme_use("clam")
    style.configure(
        "TCombobox",
        fieldbackground=theme.BG_CARD,
        background=theme.BG_CARD,
        foreground=theme.TEXT,
        arrowcolor=theme.SUBTEXT,
        padding=6,
    )
    style.configure(
        "Vertical.TScrollbar",
        troughcolor=theme.BG_APP,
        background=theme.BORDER,
        arrowcolor=theme.SUBTEXT,
    )


def bind_mousewheel(canvas: tk.Canvas) -> None:
    def _scroll(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _bind(_event):
        canvas.bind_all("<MouseWheel>", _scroll)

    def _unbind(_event):
        canvas.unbind_all("<MouseWheel>")

    canvas.bind("<Enter>", _bind)
    canvas.bind("<Leave>", _unbind)


class ScrollableFrame:
    def __init__(self, parent, bg=None, padx=0, pady=0, min_height: int = 0):
        self.bg = bg or theme.BG_APP
        self.outer = tk.Frame(parent, bg=self.bg)
        self.outer.pack(fill="both", expand=True, padx=padx, pady=pady)

        self.canvas = tk.Canvas(self.outer, bg=self.bg, highlightthickness=0, bd=0)
        if min_height > 0:
            self.canvas.configure(height=min_height)
        self.scrollbar = ttk.Scrollbar(
            self.outer, orient="vertical", command=self.canvas.yview
        )
        self.inner = tk.Frame(self.canvas, bg=self.bg)

        self.inner.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self._window_id = self.canvas.create_window(
            (0, 0), window=self.inner, anchor="nw"
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self._window_id, width=e.width),
        )
        bind_mousewheel(self.canvas)

    @property
    def frame(self) -> tk.Frame:
        return self.inner


def page_header(parent, titulo: str, subtitulo: str = "") -> tk.Frame:
    header = tk.Frame(parent, bg=theme.BG_APP)
    header.pack(fill="x", padx=24, pady=(20, 8))

    row = tk.Frame(header, bg=theme.BG_APP)
    row.pack(fill="x")

    text_col = tk.Frame(row, bg=theme.BG_APP)
    text_col.pack(side="left", fill="x", expand=True)

    tk.Label(
        text_col, text=titulo, font=theme.FONT_TITLE, bg=theme.BG_APP, fg=theme.TEXT
    ).pack(anchor="w")
    if subtitulo:
        tk.Label(
            text_col,
            text=subtitulo,
            font=theme.FONT_BODY,
            bg=theme.BG_APP,
            fg=theme.SUBTEXT,
        ).pack(anchor="w", pady=(4, 0))

    acciones = tk.Frame(row, bg=theme.BG_APP)
    acciones.pack(side="right", padx=(12, 0), anchor="n")
    header._acciones = acciones  # type: ignore[attr-defined]
    return header


def section_card(parent, titulo: str | None = None, expand=True) -> tk.Frame:
    wrapper = tk.Frame(parent, bg=theme.BG_APP)
    wrapper.pack(fill="both", expand=expand, padx=24, pady=(0, 16))

    card = tk.Frame(
        wrapper,
        bg=theme.BG_CARD,
        highlightthickness=1,
        highlightbackground=theme.BORDER,
    )
    card.pack(fill="both", expand=True)

    if titulo:
        tk.Label(
            card,
            text=titulo,
            font=theme.FONT_SUBHEADING,
            bg=theme.BG_CARD,
            fg=theme.TEXT,
        ).pack(anchor="w", padx=20, pady=(16, 8))

    body = tk.Frame(card, bg=theme.BG_CARD)
    body.pack(fill="both", expand=True, padx=20, pady=(0, 16))
    return body


def stat_card(parent, titulo: str, valor, icono: str, color: str) -> tk.Frame:
    card = tk.Frame(
        parent,
        bg=theme.BG_CARD,
        highlightthickness=1,
        highlightbackground=theme.BORDER,
        padx=16,
        pady=14,
    )
    card.pack(side="left", fill="x", expand=True, padx=(0, 12))

    row = tk.Frame(card, bg=theme.BG_CARD)
    row.pack(fill="both", expand=True)

    icon_frame = tk.Frame(row, bg=color, width=48, height=48)
    icon_frame.pack(side="left", padx=(0, 14))
    icon_frame.pack_propagate(False)
    tk.Label(
        icon_frame, text=icono, font=theme.FONT_ICON, bg=color, fg="white"
    ).place(relx=0.5, rely=0.5, anchor="center")

    col = tk.Frame(row, bg=theme.BG_CARD)
    col.pack(side="left", fill="both", expand=True)
    tk.Label(
        col, text=titulo, font=theme.FONT_SMALL, bg=theme.BG_CARD, fg=theme.SUBTEXT
    ).pack(anchor="w")
    tk.Label(
        col, text=str(valor), font=theme.FONT_STAT, bg=theme.BG_CARD, fg=theme.TEXT
    ).pack(anchor="w")
    return card


def action_card(parent, titulo: str, icono: str, color: str, comando) -> tk.Frame:
    card = tk.Frame(
        parent,
        bg=theme.BG_CARD,
        padx=20,
        pady=18,
        highlightthickness=1,
        highlightbackground=theme.BORDER,
        cursor="hand2",
    )
    card.pack(side="left", padx=(0, 12))

    tk.Label(card, text=icono, font=theme.FONT_ICON, bg=theme.BG_CARD, fg=color).pack()
    tk.Label(
        card,
        text=titulo,
        font=theme.FONT_BODY_BOLD,
        bg=theme.BG_CARD,
        fg=theme.TEXT,
    ).pack(pady=(8, 0))

    def _click(_event=None):
        comando()

    card.bind("<Button-1>", _click)
    for child in card.winfo_children():
        child.bind("<Button-1>", _click)
    card.bind("<Enter>", lambda e: card.configure(bg=theme.BG_CARD_ALT))
    card.bind("<Leave>", lambda e: card.configure(bg=theme.BG_CARD))
    return card


def primary_button(parent, text: str, command, **kwargs) -> tk.Button:
    defaults = dict(
        bg=theme.PRIMARY,
        fg="white",
        activebackground=theme.PRIMARY_DARK,
        activeforeground="white",
        font=theme.FONT_BODY_BOLD,
        relief="flat",
        cursor="hand2",
        padx=16,
        pady=10,
        bd=0,
    )
    defaults.update(kwargs)
    btn = tk.Button(parent, text=text, command=command, **defaults)
    return btn


def secondary_button(parent, text: str, command, **kwargs) -> tk.Button:
    defaults = dict(
        bg=theme.BG_CARD,
        fg=theme.TEXT,
        activebackground=theme.BG_HOVER,
        font=theme.FONT_BODY,
        relief="flat",
        highlightthickness=1,
        highlightbackground=theme.BORDER,
        cursor="hand2",
        padx=14,
        pady=8,
        bd=0,
    )
    defaults.update(kwargs)
    return tk.Button(parent, text=text, command=command, **defaults)


def modal_actions(
    window,
    on_submit,
    submit_text: str = "Guardar",
    on_cancel=None,
    cancel_text: str = "Cancelar",
    show_cancel: bool = True,
    **submit_kwargs,
) -> tk.Frame:
    footer = tk.Frame(window, bg=theme.BG_APP)
    footer.pack(side="bottom", fill="x", padx=16, pady=16)

    cancel_cmd = on_cancel if on_cancel is not None else window.destroy
    if show_cancel:
        secondary_button(footer, cancel_text, cancel_cmd).pack(side="right", padx=(0, 8))
    primary_button(footer, submit_text, on_submit, **submit_kwargs).pack(side="right")
    return footer


def filter_chip(parent, texto: str, activo: bool, color: str, comando) -> tk.Frame:
    bg = color if activo else theme.BG_CARD
    fg = "white" if activo else theme.TEXT
    borde = color if activo else theme.BORDER

    chip = tk.Frame(
        parent,
        bg=bg,
        highlightthickness=1,
        highlightbackground=borde,
        padx=14,
        pady=8,
        cursor="hand2",
    )
    chip.pack(side="left", padx=(0, 8))

    lbl = tk.Label(chip, text=texto, bg=bg, fg=fg, font=theme.FONT_SMALL)
    lbl.pack()

    def _click(_event=None):
        comando()

    chip.bind("<Button-1>", _click)
    lbl.bind("<Button-1>", _click)
    return chip


def badge(parent, texto: str, bg_color: str, fg_color=theme.TEXT) -> tk.Label:
    return tk.Label(
        parent,
        text=texto,
        bg=bg_color,
        fg=fg_color,
        padx=10,
        pady=4,
        font=theme.FONT_CAPTION,
    )


def crear_modal_scrollable(ctx, titulo: str, ancho=480, alto=560):
    win = tk.Toplevel(ctx.root)
    win.title(titulo)
    win.configure(bg=theme.BG_APP)
    win.geometry(f"{ancho}x{alto}")
    win.minsize(ancho, alto)
    win.transient(ctx.root)
    win.grab_set()

    win.update_idletasks()
    x = (win.winfo_screenwidth() // 2) - (ancho // 2)
    y = (win.winfo_screenheight() // 2) - (alto // 2)
    win.geometry(f"+{x}+{y}")

    scroll = ScrollableFrame(win, bg=theme.BG_APP, padx=0, pady=0)
    scroll.outer.pack(fill="both", expand=True)
    return win, scroll.frame


def campo_entrada(parent, label: str, ejemplo: str = "") -> tk.Entry:
    frame = tk.Frame(parent, bg=theme.BG_CARD)
    frame.pack(fill="x", pady=6)
    tk.Label(
        frame, text=label, font=theme.FONT_SMALL, bg=theme.BG_CARD, fg=theme.SUBTEXT
    ).pack(anchor="w")
    entry = tk.Entry(
        frame,
        font=theme.FONT_BODY,
        relief="flat",
        highlightthickness=1,
        highlightbackground=theme.BORDER,
        highlightcolor=theme.BORDER_FOCUS,
    )
    entry.pack(fill="x", ipady=8, pady=(4, 0))
    if ejemplo:
        entry.insert(0, ejemplo)
        entry.config(fg=theme.SUBTEXT)

        def clear_hint(event):
            if entry.get() == ejemplo:
                entry.delete(0, "end")
                entry.config(fg=theme.TEXT)

        entry.bind("<FocusIn>", clear_hint)
    return entry


def campo_select(parent, label: str, valores: list) -> ttk.Combobox:
    frame = tk.Frame(parent, bg=theme.BG_CARD)
    frame.pack(fill="x", pady=6)
    tk.Label(
        frame, text=label, font=theme.FONT_SMALL, bg=theme.BG_CARD, fg=theme.SUBTEXT
    ).pack(anchor="w")
    combo = ttk.Combobox(frame, values=valores, state="readonly", font=theme.FONT_BODY)
    combo.pack(fill="x", ipady=4, pady=(4, 0))
    if valores:
        combo.current(0)
    return combo

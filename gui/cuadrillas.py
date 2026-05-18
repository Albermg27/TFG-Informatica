import tkinter as tk
from tkinter import ttk

from estado_dinamico import C, M
from gui import theme
from gui.context import AppContext
from gui.helpers import etiqueta_material, id_desde_etiqueta, opciones_catalogo
from gui.widgets import ScrollableFrame, modal_actions, page_header, section_card
from modelos import nombre_material


_cuadrillas_frame: tk.Frame | None = None


def _estado_visual(estado):
    mapa = {
        "DESPLAZANDOSE": ("🚚 Desplazándose", theme.PRIMARY),
        "TRABAJANDO": ("🔧 Trabajando", theme.SUCCESS),
        "LIBRE": ("🟡 Libre", theme.WARNING),
        "INACTIVA": ("🏁 Finalizada", theme.DANGER),
    }
    return mapa.get(estado, ("⚪ Desconocido", theme.SUBTEXT))


def _popup_agregar_material(ctx: AppContext, cuadrilla):
    win = tk.Toplevel(ctx.root)
    win.title(f"Añadir material — Cuadrilla {cuadrilla.id}")
    win.configure(bg=theme.BG_APP)
    win.geometry("420x340")
    win.minsize(420, 340)
    win.transient(ctx.root)
    win.grab_set()

    card = tk.Frame(
        win,
        bg=theme.BG_CARD,
        padx=24,
        pady=20,
        highlightthickness=1,
        highlightbackground=theme.BORDER,
    )
    card.pack(fill="both", expand=True, padx=16, pady=(16, 0))

    tk.Label(
        card,
        text="Añadir material a cuadrilla",
        font=theme.FONT_SUBHEADING,
        bg=theme.BG_CARD,
        fg=theme.TEXT,
    ).pack(anchor="w")

    tk.Label(card, text="Material", font=theme.FONT_SMALL, bg=theme.BG_CARD, fg=theme.SUBTEXT).pack(
        anchor="w", pady=(16, 4)
    )
    combo = ttk.Combobox(card, values=opciones_catalogo(), state="readonly")
    combo.pack(fill="x", ipady=4)
    if combo["values"]:
        combo.current(0)

    tk.Label(card, text="Cantidad", font=theme.FONT_SMALL, bg=theme.BG_CARD, fg=theme.SUBTEXT).pack(
        anchor="w", pady=(12, 4)
    )
    entry_cant = tk.Entry(
        card,
        font=theme.FONT_BODY,
        relief="flat",
        highlightthickness=1,
        highlightbackground=theme.BORDER,
    )
    entry_cant.pack(fill="x", ipady=6)

    msg = tk.Label(card, text="", bg=theme.BG_CARD, fg=theme.DANGER, font=theme.FONT_SMALL)
    msg.pack(pady=(8, 0))

    def guardar():
        m_id = id_desde_etiqueta(combo.get())
        if m_id is None:
            msg.config(text="Selecciona un material válido")
            return
        try:
            cant = int(entry_cant.get())
            if cant <= 0:
                raise ValueError
        except ValueError:
            msg.config(text="Introduce una cantidad entera mayor que 0")
            return
        material = M.get(m_id)
        if not material:
            msg.config(text="Material no encontrado")
            return
        if material.cantidad_disponible < cant:
            msg.config(
                text=f"Stock insuficiente (disponible: {material.cantidad_disponible})"
            )
            return
        material.cantidad_disponible -= cant
        cuadrilla.materiales[m_id] = cuadrilla.materiales.get(m_id, 0) + cant
        win.destroy()
        _render_cuadrillas()

    modal_actions(win, guardar, submit_text="Añadir material")
    win.bind("<Return>", lambda _e: guardar())


def _popup_consumir_material(ctx: AppContext, cuadrilla):
    win = tk.Toplevel(ctx.root)
    win.title(f"Consumir material — Cuadrilla {cuadrilla.id}")
    win.configure(bg=theme.BG_APP)
    win.geometry("420x340")
    win.minsize(420, 340)
    win.transient(ctx.root)
    win.grab_set()

    card = tk.Frame(
        win,
        bg=theme.BG_CARD,
        padx=24,
        pady=20,
        highlightthickness=1,
        highlightbackground=theme.BORDER,
    )
    card.pack(fill="both", expand=True, padx=16, pady=(16, 0))

    tk.Label(
        card,
        text="Consumir material",
        font=theme.FONT_SUBHEADING,
        bg=theme.BG_CARD,
        fg=theme.TEXT,
    ).pack(anchor="w")

    opciones = [etiqueta_material(m_id) for m_id in sorted(cuadrilla.materiales.keys())]
    if not opciones:
        tk.Label(
            card,
            text="Esta cuadrilla no tiene materiales asignados",
            bg=theme.BG_CARD,
            fg=theme.SUBTEXT,
            font=theme.FONT_BODY,
        ).pack(pady=20)
        modal_actions(win, win.destroy, submit_text="Cerrar", show_cancel=False)
        return

    tk.Label(card, text="Material", font=theme.FONT_SMALL, bg=theme.BG_CARD, fg=theme.SUBTEXT).pack(
        anchor="w", pady=(16, 4)
    )
    combo = ttk.Combobox(card, values=opciones, state="readonly")
    combo.pack(fill="x", ipady=4)
    combo.current(0)

    tk.Label(card, text="Cantidad", font=theme.FONT_SMALL, bg=theme.BG_CARD, fg=theme.SUBTEXT).pack(
        anchor="w", pady=(12, 4)
    )
    entry_cant = tk.Entry(
        card,
        font=theme.FONT_BODY,
        relief="flat",
        highlightthickness=1,
        highlightbackground=theme.BORDER,
    )
    entry_cant.pack(fill="x", ipady=6)

    msg = tk.Label(card, text="", bg=theme.BG_CARD, fg=theme.DANGER, font=theme.FONT_SMALL)
    msg.pack(pady=(8, 0))

    def consumir():
        m_id = id_desde_etiqueta(combo.get())
        if m_id is None:
            msg.config(text="Selecciona un material")
            return
        try:
            cant = int(entry_cant.get())
        except ValueError:
            msg.config(text="Cantidad inválida")
            return
        actual = cuadrilla.materiales.get(m_id, 0)
        if cant > actual:
            msg.config(text="No puedes consumir más de lo disponible")
            return
        nueva = actual - cant
        if nueva == 0:
            del cuadrilla.materiales[m_id]
        else:
            cuadrilla.materiales[m_id] = nueva
        win.destroy()
        _render_cuadrillas()

    modal_actions(win, consumir, submit_text="Confirmar consumo")
    win.bind("<Return>", lambda _e: consumir())


def _render_cuadrillas():
    global _cuadrillas_frame
    if _cuadrillas_frame is None:
        return

    for w in _cuadrillas_frame.winfo_children():
        w.destroy()

    if not C:
        tk.Label(
            _cuadrillas_frame,
            text="No hay cuadrillas activas.\nInicializa el sistema dinámico primero.",
            bg=theme.BG_CARD,
            fg=theme.SUBTEXT,
            font=theme.FONT_BODY,
            pady=40,
        ).pack()
        return

    scroll = ScrollableFrame(_cuadrillas_frame, bg=theme.BG_CARD)
    grid = scroll.frame
    cols = 2
    for col in range(cols):
        grid.grid_columnconfigure(col, weight=1)

    for i, c in enumerate(C):
        r, col = divmod(i, cols)
        estado_txt, color = _estado_visual(c.estado.name)

        card = tk.Frame(
            grid,
            bg=theme.BG_CARD_ALT,
            highlightthickness=1,
            highlightbackground=theme.BORDER,
            padx=16,
            pady=14,
        )
        card.grid(row=r, column=col, padx=8, pady=8, sticky="nsew")

        tk.Label(
            card,
            text=f"Cuadrilla {c.id}",
            font=theme.FONT_SUBHEADING,
            bg=theme.BG_CARD_ALT,
            fg=theme.TEXT,
        ).pack(anchor="w")
        tk.Label(
            card,
            text=estado_txt,
            font=theme.FONT_BODY_BOLD,
            bg=theme.BG_CARD_ALT,
            fg=color,
        ).pack(anchor="w", pady=(4, 10))

        mat_frame = tk.Frame(card, bg=theme.BG_CARD_ALT)
        mat_frame.pack(anchor="w", fill="x", pady=(0, 12))
        if c.materiales:
            for m_id, cantidad in c.materiales.items():
                chip = tk.Frame(mat_frame, bg=theme.BG_HOVER, padx=8, pady=4)
                chip.pack(anchor="w", pady=2)
                tk.Label(
                    chip,
                    text=f"{nombre_material(m_id, M)}  ×{cantidad}",
                    font=theme.FONT_SMALL,
                    bg=theme.BG_HOVER,
                    fg=theme.TEXT,
                ).pack()
        else:
            tk.Label(
                mat_frame,
                text="Sin materiales",
                bg=theme.BG_CARD_ALT,
                fg=theme.SUBTEXT,
                font=theme.FONT_SMALL,
            ).pack(anchor="w")

        acciones = tk.Frame(card, bg=theme.BG_CARD_ALT)
        acciones.pack(fill="x")
        tk.Button(
            acciones,
            text="➕ Añadir",
            command=lambda cuad=c: _popup_agregar_material(_ctx_ref, cuad),
            bg=theme.SUCCESS,
            fg="white",
            relief="flat",
            font=theme.FONT_SMALL,
            padx=10,
            pady=6,
            cursor="hand2",
            bd=0,
        ).pack(side="left", padx=(0, 6))
        tk.Button(
            acciones,
            text="➖ Consumir",
            command=lambda cuad=c: _popup_consumir_material(_ctx_ref, cuad),
            bg=theme.BG_CARD,
            fg=theme.TEXT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=theme.BORDER,
            font=theme.FONT_SMALL,
            padx=10,
            pady=6,
            cursor="hand2",
            bd=0,
        ).pack(side="left")


_ctx_ref: AppContext | None = None


def mostrar(ctx: AppContext) -> None:
    global _cuadrillas_frame, _ctx_ref
    _ctx_ref = ctx
    ctx.limpiar()

    page_header(
        ctx.content,
        "Gestión de cuadrillas",
        "Consulta el estado y gestiona los materiales de cada cuadrilla",
    )

    body = section_card(ctx.content, "Cuadrillas en sistema")
    _cuadrillas_frame = body
    _render_cuadrillas()

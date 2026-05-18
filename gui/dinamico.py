import tkinter as tk
from tkinter import ttk

from estado_dinamico import C, D, M, ULTIMO_RESULTADO_ASIGNACION, V
from gui import theme
from gui.context import AppContext
from gui.helpers import (
    etiqueta_material,
    id_desde_etiqueta,
    materiales_necesarios_texto,
    materiales_texto,
    opciones_catalogo,
)
from gui.widgets import (
    ScrollableFrame,
    action_card,
    campo_entrada,
    campo_select,
    crear_modal_scrollable,
    page_header,
    primary_button,
    section_card,
    stat_card,
)
from modelos import TipoVisita, Visita
from sistema_dinamico import (
    actualizar_stock,
    agregar_visita,
    asignacion_inicial_dinamica,
    cambiar_estado_cuadrilla,
    terminar_sistema,
)

_estado_frame: tk.Frame | None = None
_ctx_ref: AppContext | None = None


def _leer_tiempo(entry):
    try:
        return float(entry.get())
    except (TypeError, ValueError):
        return None


def _texto_ubicacion_cuadrilla(c):
    if getattr(c, "visita_actual", None):
        v = c.visita_actual
        return f"{v.nombre} ({v.latitud:.3f}, {v.longitud:.3f})"
    return f"Nodo {c.posicion}"


def _estado_visual(estado):
    mapa = {
        "DESPLAZANDOSE": ("🚚 Desplazándose", theme.PRIMARY),
        "TRABAJANDO": ("🔧 Trabajando", theme.SUCCESS),
        "LIBRE": ("🟡 Libre", theme.WARNING),
        "INACTIVA": ("🏁 Jornada finalizada", theme.DANGER),
    }
    return mapa.get(estado, ("⚪ Desconocido", theme.SUBTEXT))


def _texto_historial(cuadrilla):
    if not cuadrilla.historial and not cuadrilla.ruta:
        return "Sin movimientos"
    return " → ".join(
        h.nombre if hasattr(h, "nombre") else str(h) for h in cuadrilla.ruta
    )


def render_estado():
    global _estado_frame
    if _estado_frame is None:
        return

    for w in _estado_frame.winfo_children():
        w.destroy()

    stats = tk.Frame(_estado_frame, bg=theme.BG_CARD)
    stats.pack(fill="x", pady=(0, 12))
    stat_card(stats, "Visitas pendientes", len(V), "📋", theme.PRIMARY)
    stat_card(stats, "Cuadrillas activas", len(C), "👷", theme.SUCCESS)

    if ULTIMO_RESULTADO_ASIGNACION:
        res = ULTIMO_RESULTADO_ASIGNACION
        ok = res.get("ok", False)
        banner_bg = theme.SUCCESS_LIGHT if ok else theme.WARNING_LIGHT
        banner_fg = theme.SUCCESS if ok else theme.WARNING
        tk.Label(
            _estado_frame,
            text=res.get("mensaje", ""),
            bg=banner_bg,
            fg=banner_fg,
            font=theme.FONT_BODY_BOLD,
            wraplength=900,
            justify="left",
            padx=14,
            pady=10,
        ).pack(fill="x", pady=(0, 12))

    if not C:
        tk.Label(
            _estado_frame,
            text="Inicializa la jornada para ver el estado de las cuadrillas",
            bg=theme.BG_CARD,
            fg=theme.SUBTEXT,
            font=theme.FONT_BODY,
            pady=30,
        ).pack()
        return

    scroll = ScrollableFrame(_estado_frame, bg=theme.BG_CARD)
    grid = scroll.frame
    cols = 2
    for col in range(cols):
        grid.grid_columnconfigure(col, weight=1)

    for i, c in enumerate(C):
        r, col = divmod(i, cols)
        titulo, color_estado = _estado_visual(c.estado.name)

        card = tk.Frame(
            grid,
            bg=theme.BG_CARD_ALT,
            highlightthickness=1,
            highlightbackground=theme.BORDER,
            padx=14,
            pady=12,
        )
        card.grid(row=r, column=col, padx=8, pady=8, sticky="nsew")

        tk.Label(
            card,
            text=f"Cuadrilla {c.id}",
            bg=theme.BG_CARD_ALT,
            fg=theme.TEXT,
            font=theme.FONT_BODY_BOLD,
        ).pack(anchor="w")
        tk.Label(
            card,
            text=titulo,
            bg=theme.BG_CARD_ALT,
            fg=color_estado,
            font=theme.FONT_SMALL,
        ).pack(anchor="w", pady=(2, 6))

        for linea in (
            f"📍 {_texto_ubicacion_cuadrilla(c)}",
            f"⏱ Tiempo acumulado: {c.tiempo_acumulado:.1f} min",
            f"🧭 Ruta: {_texto_historial(c)}",
            f"📦 Materiales:\n{materiales_texto(c.materiales)}",
        ):
            tk.Label(
                card,
                text=linea,
                bg=theme.BG_CARD_ALT,
                fg=theme.SUBTEXT,
                font=theme.FONT_SMALL,
                justify="left",
                wraplength=340,
            ).pack(anchor="w", pady=(0, 2))

        if c.estado.name == "DESPLAZANDOSE":
            tk.Label(
                card,
                text=f"Trayecto estimado: {D[c.posicion][c.visita_actual.id]:.1f} min",
                bg=theme.BG_CARD_ALT,
                fg=theme.TEXT_SECONDARY,
                font=theme.FONT_CAPTION,
            ).pack(anchor="w", pady=(6, 0))

        elif c.estado.name == "TRABAJANDO":
            tk.Label(
                card,
                text=f"Trabajo estimado: {c.visita_actual.duracion} min",
                bg=theme.BG_CARD_ALT,
                fg=theme.TEXT_SECONDARY,
                font=theme.FONT_CAPTION,
            ).pack(anchor="w", pady=(6, 0))
            if c.visita_actual.materiales_necesarios:
                tk.Label(
                    card,
                    text=(
                        "Materiales de la visita:\n"
                        f"{materiales_necesarios_texto(c.visita_actual.materiales_necesarios)}"
                    ),
                    bg=theme.BG_CARD_ALT,
                    fg=theme.TEXT_SECONDARY,
                    font=theme.FONT_CAPTION,
                    justify="left",
                    wraplength=340,
                ).pack(anchor="w", pady=(4, 0))

        acciones = tk.Frame(card, bg=theme.BG_CARD_ALT)
        acciones.pack(fill="x", pady=(10, 0))

        if c.estado.name == "DESPLAZANDOSE":

            entry = tk.Entry(
                acciones,
                width=6,
                font=theme.FONT_BODY,
                relief="flat",
                highlightthickness=1,
                highlightbackground=theme.BORDER,
            )
            entry.pack(side="left")
            tk.Label(
                acciones,
                text="min reales",
                bg=theme.BG_CARD_ALT,
                fg=theme.SUBTEXT,
                font=theme.FONT_CAPTION,
            ).pack(side="left", padx=6)

            def llegada(cuad=c, e=entry):
                tiempo = _leer_tiempo(e)
                if tiempo is not None:
                    cambiar_estado_cuadrilla(cuad.id, tiempo)
                    render_estado()

            tk.Button(
                acciones,
                text="✔ Llegada",
                bg=theme.PRIMARY,
                fg="white",
                relief="flat",
                font=theme.FONT_CAPTION,
                padx=8,
                pady=4,
                cursor="hand2",
                bd=0,
                command=llegada,
            ).pack(side="right")

        elif c.estado.name == "TRABAJANDO":
            entry = tk.Entry(
                acciones,
                width=6,
                font=theme.FONT_BODY,
                relief="flat",
                highlightthickness=1,
                highlightbackground=theme.BORDER,
            )
            entry.pack(side="left")

            def fin(cuad=c, e=entry):
                tiempo = _leer_tiempo(e)
                if tiempo is not None:
                    cambiar_estado_cuadrilla(cuad.id, tiempo)
                    render_estado()

            tk.Button(
                acciones,
                text="🏁 Finalizar",
                bg=theme.SUCCESS,
                fg="white",
                relief="flat",
                font=theme.FONT_CAPTION,
                padx=8,
                pady=4,
                cursor="hand2",
                bd=0,
                command=fin,
            ).pack(side="right")


def _refrescar_inicializar():
    asignacion_inicial_dinamica()
    render_estado()


def _terminar_sistema_gui():
    terminar_sistema()
    render_estado()


def _formulario_visita():
    win, parent = crear_modal_scrollable(_ctx_ref, "Nueva visita", 520, 640)

    card = tk.Frame(
        parent,
        bg=theme.BG_CARD,
        padx=24,
        pady=20,
        highlightthickness=1,
        highlightbackground=theme.BORDER,
    )
    card.pack(fill="x", padx=16, pady=16)

    tk.Label(
        card,
        text="Nueva visita",
        font=theme.FONT_HEADING,
        bg=theme.BG_CARD,
        fg=theme.SUCCESS,
    ).pack(anchor="w")
    tk.Label(
        card,
        text="Registrar una visita urgente en el sistema dinámico",
        font=theme.FONT_BODY,
        bg=theme.BG_CARD,
        fg=theme.SUBTEXT,
    ).pack(anchor="w", pady=(4, 16))

    e_nombre = campo_entrada(card, "Cliente / nombre")
    combo_tipo = campo_select(card, "Tipo", ["instalacion", "tecnica", "incidencia"])
    e_prioridad = campo_entrada(card, "Prioridad (1-10)", "5")
    e_lat = campo_entrada(card, "Latitud", "40.4168")
    e_lon = campo_entrada(card, "Longitud", "-3.7038")

    tk.Label(
        card,
        text="Materiales necesarios (no restan del almacén)",
        font=theme.FONT_SMALL,
        bg=theme.BG_CARD,
        fg=theme.SUBTEXT,
    ).pack(anchor="w", pady=(16, 4))

    materiales_visita: dict[int, int] = {}
    lista_frame = tk.Frame(card, bg=theme.BG_CARD)
    lista_frame.pack(fill="x", pady=(0, 8))

    picker = tk.Frame(card, bg=theme.BG_CARD)
    picker.pack(fill="x")
    mat_var = tk.StringVar()
    mat_combo = ttk.Combobox(
        picker, textvariable=mat_var, values=opciones_catalogo(), state="readonly"
    )
    mat_combo.pack(side="left", fill="x", expand=True, ipady=4)
    if mat_combo["values"]:
        mat_combo.current(0)

    e_mat_cant = tk.Entry(
        picker,
        width=6,
        font=theme.FONT_BODY,
        relief="flat",
        highlightthickness=1,
        highlightbackground=theme.BORDER,
    )
    e_mat_cant.pack(side="left", padx=(8, 0), ipady=6)
    e_mat_cant.insert(0, "1")

    mat_msg = tk.Label(card, text="", bg=theme.BG_CARD, fg=theme.DANGER, font=theme.FONT_SMALL)

    def _render_materiales_visita():
        for w in lista_frame.winfo_children():
            w.destroy()
        if not materiales_visita:
            tk.Label(
                lista_frame,
                text="Ningún material añadido",
                bg=theme.BG_CARD,
                fg=theme.SUBTEXT,
                font=theme.FONT_CAPTION,
            ).pack(anchor="w")
            return
        for m_id, cant in sorted(materiales_visita.items()):
            row = tk.Frame(lista_frame, bg=theme.BG_HOVER, padx=8, pady=4)
            row.pack(fill="x", pady=2)
            tk.Label(
                row,
                text=f"{etiqueta_material(m_id)}  ×{cant}",
                bg=theme.BG_HOVER,
                fg=theme.TEXT,
                font=theme.FONT_SMALL,
            ).pack(side="left")

            def quitar(mid=m_id):
                materiales_visita.pop(mid, None)
                _render_materiales_visita()

            tk.Button(
                row,
                text="✕",
                command=quitar,
                bg=theme.BG_HOVER,
                fg=theme.DANGER,
                relief="flat",
                font=theme.FONT_SMALL,
                cursor="hand2",
                bd=0,
            ).pack(side="right")

    def _anadir_material_visita():
        mat_msg.config(text="")
        m_id = id_desde_etiqueta(mat_var.get())
        if m_id is None or m_id not in M:
            mat_msg.config(text="Selecciona un material válido")
            return
        try:
            cant = int(e_mat_cant.get())
            if cant <= 0:
                raise ValueError
        except ValueError:
            mat_msg.config(text="Cantidad inválida")
            return
        materiales_visita[m_id] = materiales_visita.get(m_id, 0) + cant
        e_mat_cant.delete(0, "end")
        e_mat_cant.insert(0, "1")
        _render_materiales_visita()

    tk.Button(
        picker,
        text="Añadir",
        command=_anadir_material_visita,
        bg=theme.PRIMARY,
        fg="white",
        relief="flat",
        font=theme.FONT_SMALL,
        padx=10,
        pady=6,
        cursor="hand2",
        bd=0,
    ).pack(side="left", padx=(8, 0))
    mat_msg.pack(anchor="w", pady=(4, 0))
    _render_materiales_visita()

    msg = tk.Label(card, text="", bg=theme.BG_CARD, fg=theme.DANGER, font=theme.FONT_SMALL)
    msg.pack(pady=(8, 0))

    def crear():
        try:
            nombre = e_nombre.get().strip()
            if not nombre:
                raise ValueError
            visita = Visita(
                tipo=TipoVisita(combo_tipo.get().strip().lower()),
                prioridad=int(e_prioridad.get()),
                materiales_visita=dict(materiales_visita),
                nombre=nombre,
                latitud=float(e_lat.get()),
                longitud=float(e_lon.get()),
            )
            agregar_visita(visita)
            render_estado()
            win.destroy()
        except (ValueError, KeyError):
            msg.config(text="Revisa los datos introducidos")

    primary_button(card, "Crear visita", crear, bg=theme.SUCCESS, activebackground="#15803d").pack(
        fill="x", pady=(16, 0)
    )


def _formulario_stock():
    win, parent = crear_modal_scrollable(_ctx_ref, "Actualizar stock", 420, 380)

    card = tk.Frame(
        parent,
        bg=theme.BG_CARD,
        padx=24,
        pady=20,
        highlightthickness=1,
        highlightbackground=theme.BORDER,
    )
    card.pack(fill="x", padx=16, pady=16)

    tk.Label(
        card,
        text="Actualizar stock",
        font=theme.FONT_HEADING,
        bg=theme.BG_CARD,
        fg=theme.WARNING,
    ).pack(anchor="w")
    tk.Label(
        card,
        text="Incrementar material disponible en almacén",
        font=theme.FONT_BODY,
        bg=theme.BG_CARD,
        fg=theme.SUBTEXT,
    ).pack(anchor="w", pady=(4, 16))

    tk.Label(card, text="Material", font=theme.FONT_SMALL, bg=theme.BG_CARD, fg=theme.SUBTEXT).pack(
        anchor="w"
    )
    mat_var = tk.StringVar()
    mat_combo = ttk.Combobox(
        card, textvariable=mat_var, values=opciones_catalogo(), state="readonly"
    )
    mat_combo.pack(fill="x", ipady=4, pady=(4, 12))
    if mat_combo["values"]:
        mat_combo.current(0)

    e_cant = campo_entrada(card, "Cantidad a añadir")
    msg = tk.Label(card, text="", bg=theme.BG_CARD, fg=theme.DANGER, font=theme.FONT_SMALL)
    msg.pack(pady=(8, 0))

    def aplicar():
        try:
            m_id = id_desde_etiqueta(mat_var.get())
            if m_id is None:
                msg.config(text="Selecciona un material")
                return
            if not actualizar_stock(m_id, int(e_cant.get())):
                msg.config(text="Material no encontrado")
                return
            render_estado()
            win.destroy()
        except ValueError:
            msg.config(text="Valores inválidos")

    primary_button(
        card, "Actualizar", aplicar, bg=theme.WARNING, activebackground="#b45309"
    ).pack(fill="x", pady=(16, 0))


def mostrar(ctx: AppContext) -> None:
    global _estado_frame, _ctx_ref
    _ctx_ref = ctx
    ctx.limpiar()

    page_header(
        ctx.content,
        "Sistema dinámico",
        "Simulación en tiempo real del estado de las cuadrillas",
    )

    acciones = tk.Frame(ctx.content, bg=theme.BG_APP)
    acciones.pack(fill="x", padx=24, pady=(0, 8))
    action_card(acciones, "Inicializar jornada", "▶", theme.PRIMARY, _refrescar_inicializar)
    action_card(acciones, "Añadir visita", "➕", theme.SUCCESS, _formulario_visita)
    action_card(acciones, "Actualizar stock", "📦", theme.WARNING, _formulario_stock)
    action_card(acciones, "Finalizar jornada", "⏹", theme.DANGER, _terminar_sistema_gui)

    body = section_card(ctx.content, "Estado en tiempo real")
    _estado_frame = body
    render_estado()

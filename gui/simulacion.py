import tkinter as tk
from tkinter import ttk

from database.repository import get_instancias_db
from gui import theme
from gui.context import AppContext
from gui.widgets import ScrollableFrame, page_header, section_card
from modelos import EstadoCuadrilla, nombre_material
from simulacion.motor import MotorSimulacion

_ctx_ref: AppContext | None = None
_motor_inst: MotorSimulacion | None = None
_loop_id: str | None = None

_kpi_frame: tk.Frame | None = None
_crew_inner: tk.Frame | None = None
_crew_scroll: ScrollableFrame | None = None
_log_inner: tk.Frame | None = None
_log_scroll: ScrollableFrame | None = None
_materiales_inner: tk.Frame | None = None
_materiales_scroll: ScrollableFrame | None = None
_pagina_scroll: ScrollableFrame | None = None
_ultimo_evento_lbl: tk.Label | None = None
_reloj_lbl: tk.Label | None = None
_instancia_var: tk.IntVar | None = None
_vel_var: tk.DoubleVar | None = None
_estado_lbl: tk.Label | None = None
_instancias_meta: list = []
_log_rendered: int = 0
_pantalla_activa: bool = False
_refresh_after_id: str | None = None
_kpi_valores: list[tk.Label] = []
_crew_panel_widgets: list[dict] = []
_cola_frame: tk.Frame | None = None
_last_cola_count: int = -1
_mat_stock_labels: dict[int, tk.Label] = {}
_mat_cuad_labels: list[tk.Label] = []
_mat_pend_label: tk.Label | None = None
UI_REFRESH_MS = 150

ALTURA_PANEL_CUADRILLAS = 480
ALTURA_PANEL_EVENTOS = 480
ALTURA_PANEL_MATERIALES = 300

ESTADO_TEXTO = {
    "LIBRE": ("Libre — esperando asignación", theme.WARNING),
    "DESPLAZANDOSE": ("En desplazamiento", theme.PRIMARY),
    "TRABAJANDO": ("Trabajando en visita", theme.SUCCESS),
    "INACTIVA": ("Jornada finalizada", theme.DANGER),
}

EVENTO_ICONO = {
    "sistema": ("⚙", theme.BG_HOVER),
    "asignacion": ("📌", theme.PRIMARY_LIGHT),
    "llegada": ("🚚", theme.PRIMARY_LIGHT),
    "fin_visita": ("✅", theme.SUCCESS_LIGHT),
    "visita_nueva": ("➕", theme.WARNING_LIGHT),
    "stock": ("📦", theme.WARNING_LIGHT),
}


def _widget_vivo(widget) -> bool:
    if widget is None:
        return False
    try:
        return bool(widget.winfo_exists())
    except tk.TclError:
        return False


def _on_motor_evento():
    """Callback del motor: agrupa actualizaciones para no bloquear la UI."""
    global _refresh_after_id
    if not _pantalla_activa or _ctx_ref is None:
        return
    if _refresh_after_id:
        _ctx_ref.root.after_cancel(_refresh_after_id)
    _refresh_after_id = _ctx_ref.root.after(UI_REFRESH_MS, _ejecutar_refresh_pendiente)


def _ejecutar_refresh_pendiente():
    global _refresh_after_id
    _refresh_after_id = None
    _refrescar_por_evento_seguro()


def _get_motor() -> MotorSimulacion:
    global _motor_inst
    if _motor_inst is None:
        _motor_inst = MotorSimulacion(on_actualizar=_on_motor_evento)
    return _motor_inst


def al_salir():
    """Detiene la simulación al cambiar de pantalla (evita errores de widgets destruidos)."""
    global _pantalla_activa
    global _kpi_frame, _crew_inner, _crew_scroll, _log_inner, _log_scroll
    global _materiales_inner, _materiales_scroll
    global _ultimo_evento_lbl, _reloj_lbl, _estado_lbl, _refresh_after_id
    global _kpi_valores, _crew_panel_widgets, _cola_frame, _last_cola_count
    global _mat_stock_labels, _mat_cuad_labels, _mat_pend_label

    _pantalla_activa = False
    if _refresh_after_id and _ctx_ref:
        _ctx_ref.root.after_cancel(_refresh_after_id)
    _refresh_after_id = None
    _detener_loop()
    if _motor_inst is not None:
        _motor_inst.pausar()
    _kpi_frame = None
    _crew_inner = None
    _crew_scroll = None
    _log_inner = None
    _log_scroll = None
    _materiales_inner = None
    _materiales_scroll = None
    _pagina_scroll = None
    _ultimo_evento_lbl = None
    _reloj_lbl = None
    _estado_lbl = None
    _kpi_valores = []
    _crew_panel_widgets = []
    _cola_frame = None
    _last_cola_count = -1
    _mat_stock_labels = {}
    _mat_cuad_labels = []
    _mat_pend_label = None


def _detener_loop():
    global _loop_id
    if _ctx_ref and _loop_id:
        _ctx_ref.root.after_cancel(_loop_id)
        _loop_id = None


def _loop_simulacion():
    global _loop_id
    if not _pantalla_activa or not _widget_vivo(_crew_inner):
        _detener_loop()
        return
    m = _get_motor()
    if m.activa and not m.pausada:
        m.tick(0.05)
    if _ctx_ref and _pantalla_activa:
        _loop_id = _ctx_ref.root.after(50, _loop_simulacion)


def _seccion_cuerpo(parent, titulo: str, row: int, column: int, columnspan: int = 1, rowspan: int = 1):
    """Bloque con título para usar dentro de un grid (sin pack conflictivo)."""
    marco = tk.Frame(
        parent,
        bg=theme.BG_CARD,
        highlightthickness=1,
        highlightbackground=theme.BORDER,
    )
    marco.grid(
        row=row,
        column=column,
        columnspan=columnspan,
        rowspan=rowspan,
        sticky="nsew",
        padx=(0, 8) if column < 2 else 0,
        pady=(0, 8),
    )
    marco.grid_rowconfigure(1, weight=1)
    marco.grid_columnconfigure(0, weight=1)
    tk.Label(
        marco,
        text=titulo,
        font=theme.FONT_SUBHEADING,
        bg=theme.BG_CARD,
        fg=theme.TEXT,
    ).grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 6))
    cuerpo = tk.Frame(marco, bg=theme.BG_CARD)
    cuerpo.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 10))
    cuerpo.grid_rowconfigure(0, weight=1)
    cuerpo.grid_columnconfigure(0, weight=1)
    return cuerpo


def _actualizar_scroll(scroll: ScrollableFrame | None):
    if scroll is None:
        return
    scroll.canvas.update_idletasks()
    scroll.canvas.configure(scrollregion=scroll.canvas.bbox("all"))


def _texto_ubicacion(m, c) -> str:
    lat, lon = m.posicion_cuadrilla(c)
    if c.estado == EstadoCuadrilla.TRABAJANDO and c.visita_actual:
        return f"{c.visita_actual.nombre}  ·  ({lat:.4f}, {lon:.4f})"
    if c.estado == EstadoCuadrilla.DESPLAZANDOSE and c.visita_actual:
        origen = m.COORDS.get(c.posicion, m.COORDS.get(m.almacen_id, (0, 0)))
        return f"Hacia {c.visita_actual.nombre}  ·  ({lat:.4f}, {lon:.4f})"
    nodo = c.posicion
    if nodo in m.COORDS and nodo == m.almacen_id:
        return f"Almacén  ·  ({lat:.4f}, {lon:.4f})"
    return f"Nodo {nodo}  ·  ({lat:.4f}, {lon:.4f})"


def _texto_ruta(c) -> str:
    if not c.ruta:
        return "Sin visitas en ruta"
    return " → ".join(v.nombre for v in c.ruta)


def _texto_historial(c) -> str:
    if not c.historial:
        return "Sin visitas completadas"
    partes = []
    for visita, t_ini, t_fin in c.historial[-4:]:
        partes.append(f"{visita.nombre} ({t_ini:.0f}–{t_fin:.0f} min)")
    return " · ".join(partes)


def _actualizar_reloj():
    if not _widget_vivo(_reloj_lbl):
        return
    m = _get_motor()
    activas = sum(1 for c in m.C if c.estado != EstadoCuadrilla.INACTIVA)
    libres = sum(1 for c in m.C if c.estado == EstadoCuadrilla.LIBRE)
    _reloj_lbl.config(
        text=(
            f"Reloj simulación: {m.tiempo:.0f} min  ·  "
            f"Jornada máx.: {m.J} min  ·  "
            f"Cuadrillas activas: {activas}  ·  Libres: {libres}"
        )
    )


def _kpi_valores_texto():
    k = _get_motor().metricas.resumen()
    return [
        f"{k['tiempo_simulado']} min",
        f"{k['tiempo_total_real']} min",
        f"{k['tiempo_total_esperado']} min",
        f"{k['tiempo_medio_visita']} min",
        f"{k['distancia_total_km']} km",
        f"{k['desviacion_media_pct']} %",
        str(k["visitas_completadas"]),
        str(k["visitas_pendientes"]),
    ]


def _construir_kpis():
    global _kpi_valores
    if not _widget_vivo(_kpi_frame):
        return
    for w in _kpi_frame.winfo_children():
        w.destroy()
    _kpi_valores = []
    titulos = [
        "Tiempo simulado",
        "Tiempo real total",
        "Tiempo esperado",
        "Tiempo medio / visita",
        "Distancia recorrida",
        "Desviación media",
        "Visitas completadas",
        "Visitas pendientes",
    ]
    for i in range(4):
        _kpi_frame.grid_columnconfigure(i, weight=1, uniform="kpi")
    valores = _kpi_valores_texto()
    for i, tit in enumerate(titulos):
        celda = tk.Frame(
            _kpi_frame,
            bg=theme.BG_CARD_ALT,
            highlightthickness=1,
            highlightbackground=theme.BORDER,
            padx=14,
            pady=12,
        )
        celda.grid(row=i // 4, column=i % 4, padx=6, pady=6, sticky="nsew")
        tk.Label(celda, text=tit, font=theme.FONT_CAPTION, bg=theme.BG_CARD_ALT, fg=theme.SUBTEXT).pack(
            anchor="w"
        )
        lbl_val = tk.Label(
            celda, text=valores[i], font=theme.FONT_SUBHEADING, bg=theme.BG_CARD_ALT, fg=theme.TEXT
        )
        lbl_val.pack(anchor="w", pady=(4, 0))
        _kpi_valores.append(lbl_val)


def _actualizar_kpis():
    if not _kpi_valores or not _widget_vivo(_kpi_frame):
        _construir_kpis()
        return
    for lbl, val in zip(_kpi_valores, _kpi_valores_texto()):
        lbl.config(text=val)


def _texto_fase(m, c) -> str:
    if not c.visita_actual:
        return "—"
    if c.estado == EstadoCuadrilla.DESPLAZANDOSE:
        return f"Viaje: {c.tiempo_estimado_viaje:.0f} min (t={c.sim_tiempo_fase:.0f})"
    if c.estado == EstadoCuadrilla.TRABAJANDO:
        return f"Trabajo: {c.visita_actual.duracion} min (t={c.sim_tiempo_fase:.0f})"
    return f"{c.visita_actual.nombre} (P{c.visita_actual.prioridad})"


def _construir_cuadrillas():
    global _crew_panel_widgets, _cola_frame, _last_cola_count
    if not _widget_vivo(_crew_inner):
        return
    for w in _crew_inner.winfo_children():
        w.destroy()
    _crew_panel_widgets = []
    _cola_frame = None
    _last_cola_count = -1

    m = _get_motor()
    if not m.C:
        tk.Label(
            _crew_inner,
            text="Carga una instancia para ver las cuadrillas",
            bg=theme.BG_CARD,
            fg=theme.SUBTEXT,
            font=theme.FONT_BODY,
            pady=24,
        ).pack()
        return

    cards_host = tk.Frame(_crew_inner, bg=theme.BG_CARD)
    cards_host.pack(fill="x")

    for i, c in enumerate(m.C):
        color = m.color_cuadrilla(i)
        card = tk.Frame(
            cards_host,
            bg=theme.BG_CARD_ALT,
            highlightthickness=1,
            highlightbackground=theme.BORDER,
            padx=12,
            pady=10,
        )
        card.pack(fill="x", pady=5)
        cab = tk.Frame(card, bg=theme.BG_CARD_ALT)
        cab.pack(fill="x")
        tk.Label(cab, text="●", fg=color, bg=theme.BG_CARD_ALT, font=theme.FONT_SUBHEADING).pack(
            side="left"
        )
        tk.Label(
            cab,
            text=f"Cuadrilla {c.id}",
            font=theme.FONT_BODY_BOLD,
            bg=theme.BG_CARD_ALT,
            fg=theme.TEXT,
        ).pack(side="left", padx=(6, 0))
        lbl_estado = tk.Label(cab, text="", font=theme.FONT_SMALL, bg=theme.BG_CARD_ALT, fg=theme.TEXT)
        lbl_estado.pack(side="right")

        def _lbl(parent):
            return tk.Label(
                parent,
                text="",
                font=theme.FONT_SMALL,
                bg=theme.BG_CARD_ALT,
                fg=theme.SUBTEXT,
                wraplength=420,
                justify="left",
                anchor="w",
            )

        lbl_ubi = _lbl(card)
        lbl_ubi.pack(fill="x", pady=2)
        lbl_visita = _lbl(card)
        lbl_visita.pack(fill="x", pady=2)
        lbl_ruta = _lbl(card)
        lbl_ruta.pack(fill="x", pady=2)
        lbl_hist = _lbl(card)
        lbl_hist.pack(fill="x", pady=2)

        _crew_panel_widgets.append(
            {
                "estado": lbl_estado,
                "ubicacion": lbl_ubi,
                "visita": lbl_visita,
                "ruta": lbl_ruta,
                "historial": lbl_hist,
            }
        )

    _cola_frame = tk.Frame(_crew_inner, bg=theme.BG_CARD)
    _cola_frame.pack(fill="x", pady=(8, 0))
    _actualizar_cuadrillas()
    _actualizar_cola_visitas(forzar=True)


def _actualizar_cuadrillas():
    if not _crew_panel_widgets or not _widget_vivo(_crew_inner):
        _construir_cuadrillas()
        return
    m = _get_motor()
    for i, c in enumerate(m.C):
        if i >= len(_crew_panel_widgets):
            break
        w = _crew_panel_widgets[i]
        estado_txt, estado_col = ESTADO_TEXTO.get(c.estado.name, ("?", theme.SUBTEXT))
        w["estado"].config(text=estado_txt, fg=estado_col)
        w["ubicacion"].config(text=f"📍 {_texto_ubicacion(m, c)}")
        w["visita"].config(text=f"Visita: {_texto_fase(m, c)}")
        w["ruta"].config(text=f"Ruta: {_texto_ruta(c)}")
        w["historial"].config(text=f"Hist.: {_texto_historial(c)}")
    _actualizar_cola_visitas()


def _actualizar_cola_visitas(forzar: bool = False):
    global _last_cola_count
    if not _widget_vivo(_cola_frame):
        return
    m = _get_motor()
    n = len(m.V)
    if not forzar and n == _last_cola_count:
        return
    _last_cola_count = n
    for w in _cola_frame.winfo_children():
        w.destroy()
    if not n:
        return
    tk.Label(
        _cola_frame,
        text=f"Cola de visitas ({n})",
        font=theme.FONT_BODY_BOLD,
        bg=theme.BG_CARD,
        fg=theme.TEXT,
    ).pack(anchor="w", pady=(0, 6))
    for v in sorted(m.V, key=lambda x: -x.prioridad)[:6]:
        conf = theme.TIPO_VISITA.get(v.tipo.value, theme.TIPO_VISITA["TODAS"])
        tk.Label(
            _cola_frame,
            text=f"{conf['icono']} {v.nombre} · P{v.prioridad} · {v.duracion} min",
            font=theme.FONT_CAPTION,
            bg=theme.BG_CARD,
            fg=theme.SUBTEXT,
            wraplength=420,
            justify="left",
        ).pack(anchor="w", pady=1)


def _refrescar_cuadrillas():
    _actualizar_cuadrillas()
    _actualizar_scroll(_crew_scroll)


def _texto_materiales_cuadrilla(m, c) -> str:
    if not c.materiales:
        return "Ninguno"
    return ", ".join(
        f"{nombre_material(mid, m.M)} ×{cant}" for mid, cant in sorted(c.materiales.items())
    )


def _construir_materiales():
    global _mat_stock_labels, _mat_cuad_labels, _mat_pend_label
    if not _widget_vivo(_materiales_inner):
        return
    for w in _materiales_inner.winfo_children():
        w.destroy()
    _mat_stock_labels = {}
    _mat_cuad_labels = []
    _mat_pend_label = None

    m = _get_motor()
    if not m.M:
        tk.Label(
            _materiales_inner,
            text="Carga una instancia para ver el inventario",
            bg=theme.BG_CARD,
            fg=theme.SUBTEXT,
            font=theme.FONT_BODY,
            pady=16,
        ).pack()
        return

    tk.Label(
        _materiales_inner,
        text="Almacén central",
        font=theme.FONT_BODY_BOLD,
        bg=theme.BG_CARD,
        fg=theme.TEXT,
    ).pack(anchor="w", pady=(0, 6))

    grid_alm = tk.Frame(_materiales_inner, bg=theme.BG_CARD)
    grid_alm.pack(fill="x", pady=(0, 10))
    for col in range(4):
        grid_alm.grid_columnconfigure(col, weight=1)

    for i, (mid, mat) in enumerate(sorted(m.M.items(), key=lambda x: m.M[x[0]].nombre)):
        chip = tk.Frame(grid_alm, bg=theme.BG_CARD_ALT, padx=8, pady=6)
        chip.grid(row=i // 4, column=i % 4, padx=3, pady=3, sticky="ew")
        tk.Label(chip, text=mat.nombre, font=theme.FONT_CAPTION, bg=theme.BG_CARD_ALT, fg=theme.TEXT).pack(
            anchor="w"
        )
        lbl_stock = tk.Label(chip, text="", font=theme.FONT_SMALL, bg=theme.BG_CARD_ALT, fg=theme.TEXT)
        lbl_stock.pack(anchor="w")
        _mat_stock_labels[mid] = lbl_stock

    tk.Label(
        _materiales_inner,
        text="Por cuadrilla",
        font=theme.FONT_BODY_BOLD,
        bg=theme.BG_CARD,
        fg=theme.TEXT,
    ).pack(anchor="w", pady=(4, 6))

    for c in m.C:
        lbl = tk.Label(
            _materiales_inner,
            text="",
            font=theme.FONT_SMALL,
            bg=theme.BG_CARD,
            fg=theme.SUBTEXT,
            wraplength=900,
            justify="left",
            anchor="w",
        )
        lbl.pack(anchor="w", pady=2)
        _mat_cuad_labels.append(lbl)

    _mat_pend_label = tk.Label(_materiales_inner, text="", font=theme.FONT_CAPTION, bg=theme.BG_CARD, fg=theme.SUBTEXT)
    _mat_pend_label.pack(anchor="w", pady=(8, 0))
    _actualizar_materiales()


def _actualizar_materiales():
    if not _mat_stock_labels or not _widget_vivo(_materiales_inner):
        _construir_materiales()
        return
    m = _get_motor()
    for mid, lbl in _mat_stock_labels.items():
        mat = m.M.get(mid)
        if mat:
            ok = mat.cantidad_disponible > 0
            lbl.config(
                text=f"Stock: {mat.cantidad_disponible}",
                fg=theme.SUCCESS if ok else theme.DANGER,
            )
    for i, c in enumerate(m.C):
        if i < len(_mat_cuad_labels):
            _mat_cuad_labels[i].config(text=f"● Cuadrilla {c.id}: {_texto_materiales_cuadrilla(m, c)}")
    if _mat_pend_label:
        pend = len(m.V)
        _mat_pend_label.config(text=f"Visitas en cola: {pend}" if pend else "")


def _refrescar_materiales():
    _actualizar_materiales()
    _actualizar_scroll(_materiales_scroll)


def _fila_evento(parent, ev):
    icono, bg = EVENTO_ICONO.get(ev.tipo, ("•", theme.BG_CARD_ALT))
    row = tk.Frame(parent, bg=bg, padx=10, pady=6)
    row.pack(fill="x", pady=2)
    tk.Label(row, text=f"{ev.tiempo:6.0f}", font=theme.FONT_CAPTION, bg=bg, fg=theme.SUBTEXT, width=8, anchor="w").pack(
        side="left"
    )
    tk.Label(row, text=icono, font=theme.FONT_BODY, bg=bg, fg=theme.TEXT, width=2).pack(side="left")
    tk.Label(
        row,
        text=ev.mensaje,
        font=theme.FONT_SMALL,
        bg=bg,
        fg=theme.TEXT,
        wraplength=380,
        justify="left",
        anchor="w",
    ).pack(side="left", fill="x", expand=True)
    if ev.cuadrilla_id is not None:
        tk.Label(row, text=f"C{ev.cuadrilla_id}", font=theme.FONT_CAPTION, bg=bg, fg=theme.SUBTEXT).pack(
            side="right", padx=(4, 0)
        )


def _actualizar_ultimo_evento():
    if not _widget_vivo(_ultimo_evento_lbl):
        return
    m = _get_motor()
    if m.eventos:
        ev = m.eventos[-1]
        icono, bg = EVENTO_ICONO.get(ev.tipo, ("•", theme.BG_HOVER))
        _ultimo_evento_lbl.config(
            text=f"Último evento  [{ev.tiempo:.0f} min]  {icono}  {ev.mensaje}",
            bg=bg,
            fg=theme.TEXT,
        )
    else:
        _ultimo_evento_lbl.config(text="Último evento: —", bg=theme.BG_CARD_ALT, fg=theme.SUBTEXT)


def _anadir_eventos_nuevos():
    global _log_rendered
    if not _widget_vivo(_log_inner):
        return
    m = _get_motor()
    nuevos = m.eventos[_log_rendered:]
    if not nuevos and _log_rendered == 0 and not m.eventos:
        if not _log_inner.winfo_children():
            tk.Label(
                _log_inner,
                text="Los eventos aparecerán al iniciar la simulación",
                bg=theme.BG_CARD,
                fg=theme.SUBTEXT,
                font=theme.FONT_BODY,
                pady=20,
            ).pack()
        return
    if _log_rendered == 0 and _log_inner.winfo_children():
        for w in _log_inner.winfo_children():
            w.destroy()
    for ev in nuevos:
        _fila_evento(_log_inner, ev)
    _log_rendered = len(m.eventos)
    _actualizar_scroll(_log_scroll)


def _reset_log():
    global _log_rendered
    _log_rendered = 0
    if _widget_vivo(_log_inner):
        for w in _log_inner.winfo_children():
            w.destroy()


def _actualizar_estado_toolbar():
    if not _widget_vivo(_estado_lbl):
        return
    m = _get_motor()
    if m.finalizada:
        txt, col = "Jornada completada", theme.SUCCESS
    elif m.activa and not m.pausada:
        txt, col = f"En ejecución · {m.velocidad:.1f}×", theme.PRIMARY
    elif m.pausada:
        txt, col = "Pausada", theme.WARNING
    else:
        txt, col = "Lista", theme.SUBTEXT
    _estado_lbl.config(text=txt, fg=col)


def _refrescar_por_evento_seguro():
    if not _pantalla_activa or not _widget_vivo(_crew_inner):
        al_salir()
        return
    _refrescar_por_evento()


def _refrescar_por_evento():
    """Actualización ligera: solo cambia textos, sin reconstruir paneles."""
    m = _get_motor()
    tipo = m.eventos[-1].tipo if m.eventos else ""

    _anadir_eventos_nuevos()
    _actualizar_ultimo_evento()
    _actualizar_reloj()
    _actualizar_estado_toolbar()
    _actualizar_kpis()
    _refrescar_cuadrillas()

    if tipo in ("stock", "fin_visita", "sistema"):
        _refrescar_materiales()
    elif tipo == "visita_nueva" and _mat_pend_label and _widget_vivo(_mat_pend_label):
        _mat_pend_label.config(text=f"Visitas en cola: {len(m.V)}")


def _refrescar_completo():
    """Reconstruye paneles (carga / reinicio)."""
    _reset_log()
    _construir_kpis()
    _construir_cuadrillas()
    _construir_materiales()
    _anadir_eventos_nuevos()
    _actualizar_ultimo_evento()
    _actualizar_reloj()
    _actualizar_estado_toolbar()


def _refrescar_vista():
    _refrescar_completo()


def _cargar_instancia():
    m = _get_motor()
    iid = _instancia_var.get() if _instancia_var else 1
    m.cargar_instancia(iid, semilla=iid * 17)
    _refrescar_completo()


def _iniciar():
    m = _get_motor()
    if m.instancia_id is None:
        _cargar_instancia()
    m.velocidad = _vel_var.get() if _vel_var else 2.0
    m.iniciar()
    _detener_loop()
    _loop_simulacion()
    _actualizar_estado_toolbar()


def _pausar():
    m = _get_motor()
    if m.pausada:
        m.reanudar()
    else:
        m.pausar()
    _actualizar_estado_toolbar()


def _reiniciar():
    _detener_loop()
    _get_motor().detener()
    _cargar_instancia()


def _on_vel_change(*_):
    m = _get_motor()
    if _vel_var:
        m.velocidad = _vel_var.get()


def mostrar(ctx: AppContext) -> None:
    global _ctx_ref, _kpi_frame, _crew_inner, _crew_scroll, _log_inner, _log_scroll
    global _materiales_inner, _materiales_scroll, _pagina_scroll
    global _ultimo_evento_lbl, _reloj_lbl, _instancia_var, _vel_var, _estado_lbl, _instancias_meta
    global _pantalla_activa, _log_rendered

    al_salir()
    _ctx_ref = ctx
    ctx.limpiar()
    _log_rendered = 0

    page_header(
        ctx.content,
        "Simulación",
        "Monitor en tiempo real: cuadrillas, rutas, eventos e indicadores de calidad",
    )

    _instancias_meta = get_instancias_db()
    _instancia_var = tk.IntVar(value=_instancias_meta[0].id if _instancias_meta else 1)
    _vel_var = tk.DoubleVar(value=2.0)
    _vel_var.trace_add("write", _on_vel_change)

    controles = tk.Frame(ctx.content, bg=theme.BG_APP)
    controles.pack(fill="x", padx=24, pady=(0, 4))

    toolbar = tk.Frame(controles, bg=theme.BG_APP)
    toolbar.pack(fill="x", pady=(0, 6))

    tk.Label(toolbar, text="Instancia", bg=theme.BG_APP, fg=theme.SUBTEXT, font=theme.FONT_SMALL).pack(
        side="left", padx=(0, 8)
    )
    nombres = [f"{i.id}. {i.nombre}" for i in _instancias_meta] or ["1. (sin datos — ejecuta seed)"]
    combo = ttk.Combobox(toolbar, width=40, state="readonly", values=nombres)
    combo.pack(side="left")
    if nombres:
        combo.current(0)

    desc_lbl = tk.Label(
        controles,
        text="",
        bg=theme.BG_APP,
        fg=theme.SUBTEXT,
        font=theme.FONT_SMALL,
        wraplength=1100,
        justify="left",
    )
    desc_lbl.pack(fill="x", pady=(0, 6))

    def _actualizar_desc():
        idx = combo.current()
        if 0 <= idx < len(_instancias_meta):
            inst = _instancias_meta[idx]
            desc_lbl.config(
                text=f"{inst.descripcion or ''} · Jornada: {inst.jornada_minutos} min"
            )

    def _on_instancia_elegida(_e=None):
        idx = combo.current()
        if 0 <= idx < len(_instancias_meta):
            _instancia_var.set(_instancias_meta[idx].id)
        _actualizar_desc()

    combo.bind("<<ComboboxSelected>>", _on_instancia_elegida)
    _actualizar_desc()

    for texto, cmd, bg, fg in (
        ("Cargar", _cargar_instancia, theme.BG_CARD, theme.TEXT),
        ("▶ Iniciar", _iniciar, theme.SUCCESS, "white"),
        ("⏸ Pausar", _pausar, theme.WARNING, "white"),
        ("↺ Reiniciar", _reiniciar, theme.BG_CARD, theme.TEXT),
    ):
        tk.Button(
            toolbar,
            text=texto,
            command=cmd,
            bg=bg,
            fg=fg,
            relief="flat",
            padx=12,
            pady=6,
            cursor="hand2",
        ).pack(side="left", padx=4)

    tk.Label(toolbar, text="Velocidad", bg=theme.BG_APP, fg=theme.SUBTEXT, font=theme.FONT_SMALL).pack(
        side="left", padx=(12, 6)
    )
    ttk.Scale(toolbar, from_=0.5, to=15, variable=_vel_var, orient="horizontal", length=100).pack(
        side="left"
    )
    _estado_lbl = tk.Label(toolbar, text="Lista", bg=theme.BG_APP, fg=theme.SUBTEXT, font=theme.FONT_BODY_BOLD)
    _estado_lbl.pack(side="right", padx=8)

    global _pagina_scroll
    _pagina_scroll = ScrollableFrame(ctx.content, bg=theme.BG_APP)
    _pagina_scroll.outer.pack(fill="both", expand=True)
    pagina = _pagina_scroll.frame

    _reloj_lbl = tk.Label(
        pagina,
        text="Reloj simulación: 0 min",
        bg=theme.BG_APP,
        fg=theme.TEXT,
        font=theme.FONT_BODY_BOLD,
    )
    _reloj_lbl.pack(fill="x", pady=(4, 10))

    kpi_wrap = section_card(pagina, "Indicadores de calidad", expand=False)
    kpi_wrap.pack(fill="x", pady=(0, 10))
    _kpi_frame = tk.Frame(kpi_wrap, bg=theme.BG_CARD)
    _kpi_frame.pack(fill="x", padx=12, pady=12)
    for i in range(4):
        _kpi_frame.grid_columnconfigure(i, weight=1, uniform="kpi")
    for i in range(2):
        _kpi_frame.grid_rowconfigure(i, weight=1)

    _ultimo_evento_lbl = tk.Label(
        pagina,
        text="Último evento: —",
        bg=theme.BG_CARD_ALT,
        fg=theme.SUBTEXT,
        font=theme.FONT_BODY_BOLD,
        anchor="w",
        padx=14,
        pady=10,
        wraplength=1100,
        justify="left",
    )
    _ultimo_evento_lbl.pack(fill="x", pady=(0, 10))

    cuerpo = tk.Frame(pagina, bg=theme.BG_APP)
    cuerpo.pack(fill="x", pady=(0, 16))
    cuerpo.grid_columnconfigure(0, weight=3, minsize=420)
    cuerpo.grid_columnconfigure(1, weight=2, minsize=320)
    cuerpo.grid_rowconfigure(0, minsize=ALTURA_PANEL_CUADRILLAS + 48)
    cuerpo.grid_rowconfigure(1, minsize=ALTURA_PANEL_MATERIALES + 48)

    crew_body = _seccion_cuerpo(cuerpo, "Estado cuadrillas", row=0, column=0)
    _crew_scroll = ScrollableFrame(crew_body, bg=theme.BG_CARD, min_height=ALTURA_PANEL_CUADRILLAS)
    _crew_inner = _crew_scroll.frame

    log_body = _seccion_cuerpo(cuerpo, "Eventos en tiempo real", row=0, column=1)
    _log_scroll = ScrollableFrame(log_body, bg=theme.BG_CARD, min_height=ALTURA_PANEL_EVENTOS)
    _log_inner = _log_scroll.frame

    mat_body = _seccion_cuerpo(
        cuerpo, "Estado materiales", row=1, column=0, columnspan=2
    )
    _materiales_scroll = ScrollableFrame(
        mat_body, bg=theme.BG_CARD, min_height=ALTURA_PANEL_MATERIALES
    )
    _materiales_inner = _materiales_scroll.frame

    _pantalla_activa = True

    if _instancias_meta:
        _get_motor().cargar_instancia(_instancias_meta[0].id)
    _refrescar_completo()

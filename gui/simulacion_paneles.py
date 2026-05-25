from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING

from gui import theme
from gui.helpers import widget_vivo
from gui.widgets import ScrollableFrame, section_card
from modelos import EstadoCuadrilla, nombre_material

if TYPE_CHECKING:
    from gui.simulacion_vista import SimulacionView

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
    "cancelacion": ("✕", theme.DANGER_LIGHT),
    "stock": ("📦", theme.WARNING_LIGHT),
}


def actualizar_scroll(scroll: ScrollableFrame | None) -> None:
    if scroll is None:
        return
    scroll.canvas.update_idletasks()
    scroll.canvas.configure(scrollregion=scroll.canvas.bbox("all"))


def seccion_cuerpo(parent, titulo: str, row: int, column: int, columnspan: int = 1, rowspan: int = 1):
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


def texto_ubicacion(v: SimulacionView, c) -> str:
    m = v.motor
    lat, lon = m.posicion_cuadrilla(c)
    if c.estado == EstadoCuadrilla.TRABAJANDO and c.visita_actual:
        return f"{c.visita_actual.nombre}  ·  ({lat:.4f}, {lon:.4f})"
    if c.estado == EstadoCuadrilla.DESPLAZANDOSE and c.visita_actual:
        return f"Hacia {c.visita_actual.nombre}  ·  ({lat:.4f}, {lon:.4f})"
    nodo = c.posicion
    if nodo in m.COORDS and nodo == m.almacen_id:
        return f"Almacén  ·  ({lat:.4f}, {lon:.4f})"
    return f"Nodo {nodo}  ·  ({lat:.4f}, {lon:.4f})"


def texto_ruta(c) -> str:
    if not c.ruta:
        return "Sin visitas en ruta"
    return " → ".join(x.nombre for x in c.ruta)


def texto_historial(c) -> str:
    if not c.historial:
        return "Sin visitas completadas"
    partes = []
    for visita, t_ini, t_fin in c.historial[-4:]:
        partes.append(f"{visita.nombre} ({t_ini:.0f}–{t_fin:.0f} min)")
    return " · ".join(partes)


def texto_fase(v: SimulacionView, c) -> str:
    if not c.visita_actual:
        return "—"
    if c.estado == EstadoCuadrilla.DESPLAZANDOSE:
        return f"Viaje: {c.tiempo_estimado_viaje:.0f} min (t={c.sim_tiempo_fase:.0f})"
    if c.estado == EstadoCuadrilla.TRABAJANDO:
        return f"Trabajo: {c.visita_actual.duracion} min (t={c.sim_tiempo_fase:.0f})"
    return f"{c.visita_actual.nombre} (P{c.visita_actual.prioridad})"


def kpi_valores_texto(v: SimulacionView) -> list[str]:
    m = v.motor
    k = m.metricas.resumen(jornada=m.J)
    return [
        f"{k['distancia_total_km']} km",
        str(k["visitas_completadas"]),
        str(k["visitas_pendientes"]),
        str(k["visitas_generadas"]),
        str(k["visitas_canceladas"]),
    ]


def construir_kpis(v: SimulacionView) -> None:
    if not widget_vivo(v.kpi_frame):
        return
    for w in v.kpi_frame.winfo_children():
        w.destroy()
    v.kpi_valores = []
    titulos = [
        "Distancia recorrida",
        "Visitas completadas",
        "Visitas pendientes",
        "Urgentes generadas",
        "Canceladas",
    ]
    for i in range(5):
        v.kpi_frame.grid_columnconfigure(i, weight=1, uniform="kpi")
    valores = kpi_valores_texto(v)
    for i, tit in enumerate(titulos):
        celda = tk.Frame(
            v.kpi_frame,
            bg=theme.BG_CARD_ALT,
            highlightthickness=1,
            highlightbackground=theme.BORDER,
            padx=14,
            pady=12,
        )
        celda.grid(row=i // 5, column=i % 5, padx=6, pady=6, sticky="nsew")
        tk.Label(celda, text=tit, font=theme.FONT_CAPTION, bg=theme.BG_CARD_ALT, fg=theme.SUBTEXT).pack(
            anchor="w"
        )
        lbl_val = tk.Label(
            celda, text=valores[i], font=theme.FONT_SUBHEADING, bg=theme.BG_CARD_ALT, fg=theme.TEXT
        )
        lbl_val.pack(anchor="w", pady=(4, 0))
        v.kpi_valores.append(lbl_val)


def actualizar_kpis(v: SimulacionView) -> None:
    if not v.kpi_valores or not widget_vivo(v.kpi_frame):
        construir_kpis(v)
        return
    for lbl, val in zip(v.kpi_valores, kpi_valores_texto(v)):
        lbl.config(text=val)


def construir_cuadrillas(v: SimulacionView) -> None:
    if not widget_vivo(v.crew_inner):
        return
    for w in v.crew_inner.winfo_children():
        w.destroy()
    v.crew_panel_widgets = []
    v.cola_frame = None
    v.last_cola_count = -1

    m = v.motor
    if not m.C:
        tk.Label(
            v.crew_inner,
            text="Carga una instancia para ver las cuadrillas",
            bg=theme.BG_CARD,
            fg=theme.SUBTEXT,
            font=theme.FONT_BODY,
            pady=24,
        ).pack()
        return

    cards_host = tk.Frame(v.crew_inner, bg=theme.BG_CARD)
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

        v.crew_panel_widgets.append(
            {
                "estado": lbl_estado,
                "ubicacion": lbl_ubi,
                "visita": lbl_visita,
                "ruta": lbl_ruta,
                "historial": lbl_hist,
            }
        )

    v.cola_frame = tk.Frame(v.crew_inner, bg=theme.BG_CARD)
    v.cola_frame.pack(fill="x", pady=(8, 0))
    actualizar_cuadrillas(v)
    actualizar_cola_visitas(v, forzar=True)


def actualizar_cuadrillas(v: SimulacionView) -> None:
    if not v.crew_panel_widgets or not widget_vivo(v.crew_inner):
        construir_cuadrillas(v)
        return
    m = v.motor
    for i, c in enumerate(m.C):
        if i >= len(v.crew_panel_widgets):
            break
        w = v.crew_panel_widgets[i]
        estado_txt, estado_col = ESTADO_TEXTO.get(c.estado.name, ("?", theme.SUBTEXT))
        w["estado"].config(text=estado_txt, fg=estado_col)
        w["ubicacion"].config(text=f"📍 {texto_ubicacion(v, c)}")
        w["visita"].config(text=f"Visita: {texto_fase(v, c)}")
        w["ruta"].config(text=f"Ruta: {texto_ruta(c)}")
        w["historial"].config(text=f"Hist.: {texto_historial(c)}")
    actualizar_cola_visitas(v)


def actualizar_cola_visitas(v: SimulacionView, forzar: bool = False) -> None:
    if not widget_vivo(v.cola_frame):
        return
    m = v.motor
    n = len(m.V)
    if not forzar and n == v.last_cola_count:
        return
    v.last_cola_count = n
    for w in v.cola_frame.winfo_children():
        w.destroy()
    if not n:
        return
    tk.Label(
        v.cola_frame,
        text=f"Cola de visitas ({n})",
        font=theme.FONT_BODY_BOLD,
        bg=theme.BG_CARD,
        fg=theme.TEXT,
    ).pack(anchor="w", pady=(0, 6))
    for vis in sorted(m.V, key=lambda x: -x.prioridad)[:6]:
        conf = theme.TIPO_VISITA.get(vis.tipo.value, theme.TIPO_VISITA["TODAS"])
        tk.Label(
            v.cola_frame,
            text=f"{conf['icono']} {vis.nombre} · P{vis.prioridad} · {vis.duracion} min",
            font=theme.FONT_CAPTION,
            bg=theme.BG_CARD,
            fg=theme.SUBTEXT,
            wraplength=420,
            justify="left",
        ).pack(anchor="w", pady=1)


def refrescar_cuadrillas(v: SimulacionView) -> None:
    actualizar_cuadrillas(v)
    actualizar_scroll(v.crew_scroll)


def texto_materiales_cuadrilla(v: SimulacionView, c) -> str:
    m = v.motor
    if not c.materiales:
        return "Ninguno"
    return ", ".join(
        f"{nombre_material(mid, m.M)} ×{cant}" for mid, cant in sorted(c.materiales.items())
    )


def construir_materiales(v: SimulacionView) -> None:
    if not widget_vivo(v.materiales_inner):
        return
    for w in v.materiales_inner.winfo_children():
        w.destroy()
    v.mat_stock_labels = {}
    v.mat_cuad_labels = []
    v.mat_pend_label = None

    m = v.motor
    if not m.M:
        tk.Label(
            v.materiales_inner,
            text="Carga una instancia para ver el inventario",
            bg=theme.BG_CARD,
            fg=theme.SUBTEXT,
            font=theme.FONT_BODY,
            pady=16,
        ).pack()
        return

    tk.Label(
        v.materiales_inner,
        text="Almacén central",
        font=theme.FONT_BODY_BOLD,
        bg=theme.BG_CARD,
        fg=theme.TEXT,
    ).pack(anchor="w", pady=(0, 6))

    grid_alm = tk.Frame(v.materiales_inner, bg=theme.BG_CARD)
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
        v.mat_stock_labels[mid] = lbl_stock

    tk.Label(
        v.materiales_inner,
        text="Por cuadrilla",
        font=theme.FONT_BODY_BOLD,
        bg=theme.BG_CARD,
        fg=theme.TEXT,
    ).pack(anchor="w", pady=(4, 6))

    for c in m.C:
        lbl = tk.Label(
            v.materiales_inner,
            text="",
            font=theme.FONT_SMALL,
            bg=theme.BG_CARD,
            fg=theme.SUBTEXT,
            wraplength=900,
            justify="left",
            anchor="w",
        )
        lbl.pack(anchor="w", pady=2)
        v.mat_cuad_labels.append(lbl)

    v.mat_pend_label = tk.Label(
        v.materiales_inner, text="", font=theme.FONT_CAPTION, bg=theme.BG_CARD, fg=theme.SUBTEXT
    )
    v.mat_pend_label.pack(anchor="w", pady=(8, 0))
    actualizar_materiales(v)


def actualizar_materiales(v: SimulacionView) -> None:
    if not v.mat_stock_labels or not widget_vivo(v.materiales_inner):
        construir_materiales(v)
        return
    m = v.motor
    for mid, lbl in v.mat_stock_labels.items():
        mat = m.M.get(mid)
        if mat:
            ok = mat.cantidad_disponible > 0
            lbl.config(
                text=f"Stock: {mat.cantidad_disponible}",
                fg=theme.SUCCESS if ok else theme.DANGER,
            )
    for i, c in enumerate(m.C):
        if i < len(v.mat_cuad_labels):
            v.mat_cuad_labels[i].config(text=f"● Cuadrilla {c.id}: {texto_materiales_cuadrilla(v, c)}")
    if v.mat_pend_label:
        pend = len(m.V)
        v.mat_pend_label.config(text=f"Visitas en cola: {pend}" if pend else "")


def refrescar_materiales(v: SimulacionView) -> None:
    actualizar_materiales(v)
    actualizar_scroll(v.materiales_scroll)


def fila_evento(parent, ev) -> None:
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


def actualizar_ultimo_evento(v: SimulacionView) -> None:
    if not widget_vivo(v.ultimo_evento_lbl):
        return
    m = v.motor
    if m.eventos:
        ev = m.eventos[-1]
        icono, bg = EVENTO_ICONO.get(ev.tipo, ("•", theme.BG_HOVER))
        v.ultimo_evento_lbl.config(
            text=f"Último evento  [{ev.tiempo:.0f} min]  {icono}  {ev.mensaje}",
            bg=bg,
            fg=theme.TEXT,
        )
    else:
        v.ultimo_evento_lbl.config(text="Último evento: —", bg=theme.BG_CARD_ALT, fg=theme.SUBTEXT)


def anadir_eventos_nuevos(v: SimulacionView) -> None:
    if not widget_vivo(v.log_inner):
        return
    m = v.motor
    nuevos = m.eventos[v.log_rendered:]
    if not nuevos and v.log_rendered == 0 and not m.eventos:
        if not v.log_inner.winfo_children():
            tk.Label(
                v.log_inner,
                text="Los eventos aparecerán al iniciar la simulación",
                bg=theme.BG_CARD,
                fg=theme.SUBTEXT,
                font=theme.FONT_BODY,
                pady=20,
            ).pack()
        return
    if v.log_rendered == 0 and v.log_inner.winfo_children():
        for w in v.log_inner.winfo_children():
            w.destroy()
    for ev in nuevos:
        fila_evento(v.log_inner, ev)
    v.log_rendered = len(m.eventos)
    actualizar_scroll(v.log_scroll)


def reset_log(v: SimulacionView) -> None:
    v.log_rendered = 0
    if widget_vivo(v.log_inner):
        for w in v.log_inner.winfo_children():
            w.destroy()


def construir_layout_pagina(v: SimulacionView, pagina: tk.Frame) -> None:
    v.reloj_lbl = tk.Label(
        pagina,
        text="Reloj simulación: 0 min",
        bg=theme.BG_APP,
        fg=theme.TEXT,
        font=theme.FONT_BODY_BOLD,
    )
    v.reloj_lbl.pack(fill="x", pady=(4, 10))

    kpi_wrap = section_card(pagina, "Indicadores de calidad", expand=False)
    kpi_wrap.pack(fill="x", pady=(0, 10))
    v.kpi_frame = tk.Frame(kpi_wrap, bg=theme.BG_CARD)
    v.kpi_frame.pack(fill="x", padx=12, pady=12)
    for i in range(5):
        v.kpi_frame.grid_columnconfigure(i, weight=1, uniform="kpi")
    for i in range(2):
        v.kpi_frame.grid_rowconfigure(i, weight=1)

    v.ultimo_evento_lbl = tk.Label(
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
    v.ultimo_evento_lbl.pack(fill="x", pady=(0, 10))

    cuerpo = tk.Frame(pagina, bg=theme.BG_APP)
    cuerpo.pack(fill="x", pady=(0, 16))
    cuerpo.grid_columnconfigure(0, weight=3, minsize=420)
    cuerpo.grid_columnconfigure(1, weight=2, minsize=320)
    cuerpo.grid_rowconfigure(0, minsize=ALTURA_PANEL_CUADRILLAS + 48)
    cuerpo.grid_rowconfigure(1, minsize=ALTURA_PANEL_MATERIALES + 48)

    crew_body = seccion_cuerpo(cuerpo, "Estado cuadrillas", row=0, column=0)
    v.crew_scroll = ScrollableFrame(crew_body, bg=theme.BG_CARD, min_height=ALTURA_PANEL_CUADRILLAS)
    v.crew_inner = v.crew_scroll.frame

    log_body = seccion_cuerpo(cuerpo, "Eventos en tiempo real", row=0, column=1)
    v.log_scroll = ScrollableFrame(log_body, bg=theme.BG_CARD, min_height=ALTURA_PANEL_EVENTOS)
    v.log_inner = v.log_scroll.frame

    mat_body = seccion_cuerpo(cuerpo, "Estado materiales", row=1, column=0, columnspan=2)
    v.materiales_scroll = ScrollableFrame(
        mat_body, bg=theme.BG_CARD, min_height=ALTURA_PANEL_MATERIALES
    )
    v.materiales_inner = v.materiales_scroll.frame

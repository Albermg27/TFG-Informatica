from __future__ import annotations

import tkinter as tk

from gui import theme
from simulacion.metricas import (
    formatear_lista_canceladas,
    formatear_lista_pendientes,
    formatear_ruta_cuadrilla,
)
from simulacion.resultados_casos import ETIQUETAS_METRICA, METRICAS_DESTACADAS


def tarjeta_metrica(parent, titulo: str, valor, bg=theme.BG_CARD_ALT) -> tk.Frame:
    card = tk.Frame(
        parent,
        bg=bg,
        highlightthickness=1,
        highlightbackground=theme.BORDER,
        padx=12,
        pady=10,
    )
    tk.Label(card, text=titulo, font=theme.FONT_CAPTION, bg=bg, fg=theme.SUBTEXT).pack(anchor="w")
    tk.Label(card, text=str(valor), font=theme.FONT_STAT, bg=bg, fg=theme.TEXT).pack(
        anchor="w", pady=(4, 0)
    )
    return card


def panel_metricas(parent, titulo: str, resumen: dict | None) -> tk.Frame:
    marco = tk.Frame(parent, bg=theme.BG_CARD)
    tk.Label(
        marco,
        text=titulo,
        font=theme.FONT_SUBHEADING,
        bg=theme.BG_CARD,
        fg=theme.TEXT,
    ).pack(anchor="w", padx=4, pady=(0, 8))

    grid = tk.Frame(marco, bg=theme.BG_CARD)
    grid.pack(fill="x")

    if not resumen:
        tk.Label(
            grid,
            text="Sin datos",
            bg=theme.BG_CARD,
            fg=theme.SUBTEXT,
            font=theme.FONT_BODY,
        ).pack(anchor="w", padx=8, pady=12)
        return marco

    for i, campo in enumerate(METRICAS_DESTACADAS):
        if campo not in resumen:
            continue
        card = tarjeta_metrica(
            grid,
            ETIQUETAS_METRICA.get(campo, campo),
            resumen.get(campo, "—"),
        )
        card.grid(row=i // 2, column=i % 2, padx=6, pady=6, sticky="nsew")
        grid.grid_columnconfigure(i % 2, weight=1)

    return marco


def _fmt_delta_tabla(delta) -> str:
    if not isinstance(delta, (int, float)):
        return str(delta)
    d = round(float(delta), 2)
    if d == int(d):
        return f"{int(d):+d}"
    return f"{d:+.2f}"


def _fmt_valor_tabla(val) -> str:
    if isinstance(val, float):
        return f"{val:.2f}"
    return str(val)


def panel_tabla_comparativa(parent, filas: list[dict]) -> tk.Frame:
    marco = tk.Frame(
        parent,
        bg=theme.BG_CARD,
        highlightthickness=1,
        highlightbackground=theme.BORDER,
    )
    tk.Label(
        marco,
        text="Planificación (estimado)  vs  Ejecución simulada (real)",
        font=theme.FONT_SUBHEADING,
        bg=theme.BG_CARD,
        fg=theme.TEXT,
    ).pack(anchor="w", padx=14, pady=(12, 8))

    header = tk.Frame(marco, bg=theme.BG_HOVER)
    header.pack(fill="x", padx=12, pady=(0, 4))
    ancho_col0 = 26
    columnas = ("Indicador de Calidad", "Planificación", "Sistema real", "Diferencia", "% vs plan")
    for i, col in enumerate(columnas):
        tk.Label(
            header,
            text=col,
            font=theme.FONT_CAPTION,
            bg=theme.BG_HOVER,
            fg=theme.TEXT,
            width=ancho_col0 if i == 0 else 14,
            anchor="w",
        ).grid(row=0, column=i, padx=8, pady=6, sticky="w")
        header.grid_columnconfigure(i, weight=1)

    body = tk.Frame(marco, bg=theme.BG_CARD)
    body.pack(fill="x", padx=12, pady=(0, 12))

    for row_i, fila in enumerate(filas):
        bg = theme.BG_CARD if row_i % 2 == 0 else theme.BG_CARD_ALT
        row = tk.Frame(body, bg=bg)
        row.pack(fill="x")
        delta = fila.get("delta", 0)
        pct = fila.get("pct", 0)
        es_seccion = fila.get("es_seccion", False)
        if es_seccion or not isinstance(delta, (int, float)):
            color_delta = theme.TEXT
        else:
            color_delta = theme.DANGER if delta > 0 else theme.SUCCESS if delta < 0 else theme.TEXT
            if fila["metrica"] == "Visitas atendidas":
                color_delta = theme.SUCCESS if delta >= 0 else theme.DANGER

        if es_seccion:
            valores = (fila["metrica"], "—", "—", "—", "—")
        else:
            valores = (
                fila["metrica"],
                _fmt_valor_tabla(fila["plan"]),
                _fmt_valor_tabla(fila["real"]),
                _fmt_delta_tabla(delta),
                f"{pct:+.1f}%" if isinstance(pct, (int, float)) else pct,
            )
        for col_i, val in enumerate(valores):
            fg = theme.SUBTEXT if es_seccion else (color_delta if col_i >= 3 else theme.TEXT)
            font = (
                theme.FONT_BODY_BOLD
                if es_seccion and col_i == 0
                else (theme.FONT_SMALL if col_i else theme.FONT_BODY_BOLD)
            )
            tk.Label(
                row,
                text=str(val),
                font=font,
                bg=bg,
                fg=fg,
                width=ancho_col0 if col_i == 0 else 14,
                anchor="w",
            ).grid(row=0, column=col_i, padx=8, pady=5, sticky="w")
            row.grid_columnconfigure(col_i, weight=1)

    return marco


def resumen_visitas(
    parent, plan: dict, dinamico: dict, *, es_media: bool = False
) -> tk.Frame:
    marco = tk.Frame(parent, bg=theme.BG_APP)
    marco.pack(fill="x", pady=(0, 10))
    vp = plan.get("visitas_completadas", 0)
    vd = dinamico.get("visitas_completadas", 0)
    tarjeta_metrica(marco, "Visitas planificadas", vp, theme.PRIMARY_LIGHT).pack(
        side="left", fill="x", expand=True, padx=(0, 6)
    )
    etiqueta_real = "Media Visitas reales" if es_media else "Visitas reales"
    tarjeta_metrica(marco, etiqueta_real, vd, theme.SUCCESS_LIGHT).pack(
        side="left", fill="x", expand=True, padx=6
    )
    tarjeta_metrica(
        marco,
        "Diferencia de visitas",
        vd - vp,
        theme.DANGER_LIGHT if vd < vp else theme.SUCCESS_LIGHT,
    ).pack(side="left", fill="x", expand=True, padx=(6, 0))
    return marco


def panel_cronologia(
    parent,
    titulo: str,
    cronologia: dict[int, list[dict]] | None,
    jornada_minutos: int = 0,
    pendientes: list[str] | None = None,
    canceladas: list[str] | None = None,
    es_media: bool = False,
) -> tk.Frame:
    marco = tk.Frame(
        parent,
        bg=theme.BG_CARD_ALT,
        highlightthickness=1,
        highlightbackground=theme.BORDER,
        padx=12,
        pady=10,
    )
    tk.Label(
        marco,
        text=titulo,
        font=theme.FONT_BODY_BOLD,
        bg=theme.BG_CARD_ALT,
        fg=theme.TEXT,
    ).pack(anchor="w", pady=(0, 4))

    if not cronologia:
        tk.Label(
            marco,
            text="No disponible en esta vista (use iteración concreta o plan por instancia).",
            bg=theme.BG_CARD_ALT,
            fg=theme.SUBTEXT,
            font=theme.FONT_SMALL,
            wraplength=480,
            justify="left",
        ).pack(anchor="w")
        return marco

    if jornada_minutos:
        nota = (
            f"Tiempos en minutos (jornada planificada 0–{int(jornada_minutos)}; "
            f"las asignadas pueden acabar después)"
        )
        if es_media:
            nota += " · Valores medios por visita entre repeticiones"
        tk.Label(
            marco,
            text=nota,
            font=theme.FONT_CAPTION,
            bg=theme.BG_CARD_ALT,
            fg=theme.SUBTEXT,
            wraplength=480,
            justify="left",
        ).pack(anchor="w", pady=(0, 8))

    cont = tk.Frame(marco, bg=theme.BG_CARD_ALT)
    cont.pack(fill="both", expand=True)

    for cid in sorted(cronologia):
        tramos = cronologia.get(cid) or []
        cuad = tk.Frame(
            cont,
            bg=theme.BG_CARD,
            highlightthickness=1,
            highlightbackground=theme.BORDER,
            padx=8,
            pady=6,
        )
        cuad.pack(fill="x", pady=(0, 8))
        tk.Label(
            cuad,
            text=f"Cuadrilla {cid}",
            font=theme.FONT_BODY_BOLD,
            bg=theme.BG_CARD,
            fg=theme.TEXT,
        ).pack(anchor="w", pady=(0, 4))
        tk.Label(
            cuad,
            text=formatear_ruta_cuadrilla(tramos),
            font=theme.FONT_SMALL,
            bg=theme.BG_CARD,
            fg=theme.TEXT,
            justify="left",
            anchor="w",
            wraplength=460,
        ).pack(anchor="w")

    if cronologia is not None:
        pend = tk.Frame(
            marco,
            bg=theme.BG_CARD,
            highlightthickness=1,
            highlightbackground=theme.BORDER,
            padx=8,
            pady=6,
        )
        pend.pack(fill="x", pady=(4, 0))
        tk.Label(
            pend,
            text=formatear_lista_pendientes(pendientes),
            font=theme.FONT_SMALL,
            bg=theme.BG_CARD,
            fg=theme.TEXT,
            justify="left",
            anchor="w",
            wraplength=460,
        ).pack(anchor="w")
        if canceladas is not None:
            tk.Label(
                pend,
                text=formatear_lista_canceladas(canceladas),
                font=theme.FONT_SMALL,
                bg=theme.BG_CARD,
                fg=theme.TEXT,
                justify="left",
                anchor="w",
                wraplength=460,
            ).pack(anchor="w", pady=(6, 0))

    return marco


def panel_rutas(parent, titulo: str, rutas: dict | None, **kwargs) -> tk.Frame:
    cronologia = kwargs.get("cronologia")
    jornada = kwargs.get("jornada_minutos", 0)
    pendientes = kwargs.get("pendientes")
    canceladas = kwargs.get("canceladas")
    es_media = kwargs.get("es_media", False)
    return panel_cronologia(
        parent,
        titulo,
        cronologia,
        jornada,
        pendientes=pendientes,
        canceladas=canceladas,
        es_media=es_media,
    )

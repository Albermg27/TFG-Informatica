import tkinter as tk
from collections import Counter

from estado_dinamico import M, V_HISTORICO
from modelos import nombre_material
from gui import theme
from gui.context import AppContext
from gui.widgets import (
    ScrollableFrame,
    badge,
    filter_chip,
    page_header,
    section_card,
    stat_card,
)


def _calcular_stats(visitas):
    total = len(visitas)
    conteo = Counter(v.tipo.value for v in visitas)
    return total, conteo


def mostrar(ctx: AppContext) -> None:
    ctx.limpiar()
    total, conteo = _calcular_stats(V_HISTORICO)

    page_header(
        ctx.content,
        "Dashboard de Visitas",
        "Gestión y monitorización de visitas registradas en el sistema",
    )

    stats_row = tk.Frame(ctx.content, bg=theme.BG_APP)
    stats_row.pack(fill="x", padx=24, pady=(0, 12))

    conf_todas = theme.TIPO_VISITA["TODAS"]
    stat_card(stats_row, "Total visitas", total, conf_todas["icono"], conf_todas["color"])
    for tipo, n in conteo.items():
        conf = theme.TIPO_VISITA.get(tipo, conf_todas)
        stat_card(stats_row, tipo.title(), n, conf["icono"], conf["color"])

    filtro_frame = tk.Frame(ctx.content, bg=theme.BG_APP)
    filtro_frame.pack(fill="x", padx=24, pady=(8, 4))
    tk.Label(
        filtro_frame,
        text="Filtrar por tipo",
        bg=theme.BG_APP,
        fg=theme.SUBTEXT,
        font=theme.FONT_BODY_BOLD,
    ).pack(side="left", padx=(0, 12))

    chips_frame = tk.Frame(filtro_frame, bg=theme.BG_APP)
    chips_frame.pack(side="left", fill="x", expand=True)

    lista_body = section_card(ctx.content, "Listado de visitas")
    scroll = ScrollableFrame(lista_body, bg=theme.BG_CARD)
    inner = scroll.frame

    def render_filtros():
        for w in chips_frame.winfo_children():
            w.destroy()
        tipos = ["TODAS"] + sorted(set(v.tipo.value for v in V_HISTORICO))
        for t in tipos:
            conf = theme.TIPO_VISITA.get(t, theme.TIPO_VISITA["TODAS"])
            activo = ctx.filtro_tipo.get() == t
            texto = f"{conf['icono']}  {t.title()}"
            filter_chip(
                chips_frame,
                texto,
                activo,
                conf["color"],
                lambda valor=t: set_filtro(valor),
            )

    def set_filtro(valor):
        ctx.filtro_tipo.set(valor)
        render_filtros()
        render_lista()

    def render_lista():
        for w in inner.winfo_children():
            w.destroy()

        filtro = ctx.filtro_tipo.get()
        datos = V_HISTORICO if filtro == "TODAS" else [
            v for v in V_HISTORICO if v.tipo.value == filtro
        ]

        if not datos:
            tk.Label(
                inner,
                text="No hay visitas que mostrar con este filtro",
                bg=theme.BG_CARD,
                fg=theme.SUBTEXT,
                font=theme.FONT_BODY,
                pady=40,
            ).pack()
            return

        cols = 3
        for c in range(cols):
            inner.grid_columnconfigure(c, weight=1)

        for i, v in enumerate(datos):
            r, c = divmod(i, cols)
            conf = theme.TIPO_VISITA.get(v.tipo.value, theme.TIPO_VISITA["TODAS"])

            card = tk.Frame(
                inner,
                bg=theme.BG_CARD_ALT,
                highlightthickness=1,
                highlightbackground=theme.BORDER,
                padx=16,
                pady=14,
            )
            card.grid(row=r, column=c, padx=8, pady=8, sticky="nsew")

            top = tk.Frame(card, bg=theme.BG_CARD_ALT)
            top.pack(fill="x")
            tk.Label(
                top,
                text=f"{conf['icono']}  {v.nombre}",
                bg=theme.BG_CARD_ALT,
                fg=theme.TEXT,
                font=theme.FONT_SUBHEADING,
            ).pack(side="left", anchor="w")

            badge_row = tk.Frame(card, bg=theme.BG_CARD_ALT)
            badge_row.pack(fill="x", pady=(10, 8))
            badge(badge_row, v.tipo.value.upper(), conf["bg"]).pack(side="left")
            badge(
                badge_row,
                f"Prioridad {v.prioridad}",
                theme.BG_HOVER,
                theme.SUBTEXT,
            ).pack(side="right")

            meta = tk.Frame(card, bg=theme.BG_CARD_ALT)
            meta.pack(fill="x", pady=(0, 8))
            tk.Label(
                meta,
                text=f"⏱  {v.duracion} min",
                bg=theme.BG_CARD_ALT,
                fg=theme.TEXT_SECONDARY,
                font=theme.FONT_SMALL,
            ).pack(anchor="w")
            tk.Label(
                meta,
                text=f"📍  {v.latitud:.4f}, {v.longitud:.4f}",
                bg=theme.BG_CARD_ALT,
                fg=theme.SUBTEXT,
                font=theme.FONT_SMALL,
            ).pack(anchor="w", pady=(2, 0))

            tk.Label(
                card,
                text="Materiales",
                bg=theme.BG_CARD_ALT,
                fg=theme.TEXT,
                font=theme.FONT_SMALL,
            ).pack(anchor="w")
            if v.materiales_necesarios:
                for m_id, cantidad in sorted(v.materiales_necesarios.items()):
                    tk.Label(
                        card,
                        text=f"  • {nombre_material(m_id, M)}  ×{cantidad}",
                        bg=theme.BG_CARD_ALT,
                        fg=theme.TEXT_SECONDARY,
                        font=theme.FONT_CAPTION,
                    ).pack(anchor="w")
            else:
                tk.Label(
                    card,
                    text="  • Sin materiales",
                    bg=theme.BG_CARD_ALT,
                    fg=theme.SUBTEXT,
                    font=theme.FONT_CAPTION,
                ).pack(anchor="w")

    render_filtros()
    render_lista()

import tkinter as tk
import webbrowser

from backend_ui import ejecutar_planificacion_gui, obtener_cuadrillas
from gui import theme
from gui.context import AppContext
from gui.widgets import (
    ScrollableFrame,
    page_header,
    primary_button,
    secondary_button,
)
from ui_utils import texto_cuadrilla_resumen


def generar_planificacion(ctx: AppContext) -> None:
    ejecutar_planificacion_gui()
    mostrar(ctx)


def mostrar(ctx: AppContext) -> None:
    ctx.limpiar()

    header = page_header(
        ctx.content,
        "Planificación de cuadrillas",
        "Genera rutas óptimas (plan estático de referencia). En Simulación se compara con el modelo dinámico.",
    )
    acciones = header._acciones
    primary_button(
        acciones,
        "  Generar planificación  ",
        lambda: generar_planificacion(ctx),
    ).pack(side="left", padx=(0, 8))
    secondary_button(
        acciones,
        "🗺  Abrir mapa",
        lambda: webbrowser.open("mapa.html"),
    ).pack(side="left")

    main = tk.Frame(ctx.content, bg=theme.BG_APP)
    main.pack(fill="both", expand=True, padx=24, pady=(8, 20))

    left_panel = tk.Frame(
        main,
        bg=theme.BG_CARD,
        highlightthickness=1,
        highlightbackground=theme.BORDER,
    )
    left_panel.pack(side="left", fill="both", expand=True, padx=(0, 12))

    tk.Label(
        left_panel,
        text="Cuadrillas planificadas",
        font=theme.FONT_SUBHEADING,
        bg=theme.BG_CARD,
        fg=theme.TEXT,
    ).pack(anchor="w", padx=16, pady=(14, 8))

    lista_scroll = ScrollableFrame(left_panel, bg=theme.BG_CARD, padx=8, pady=0)
    lista_inner = lista_scroll.frame

    right_panel = tk.Frame(
        main,
        bg=theme.BG_CARD,
        width=380,
        highlightthickness=1,
        highlightbackground=theme.BORDER,
    )
    right_panel.pack(side="right", fill="y")
    right_panel.pack_propagate(False)

    detalle_inner = tk.Frame(right_panel, bg=theme.BG_CARD)
    detalle_inner.pack(fill="both", expand=True, padx=16, pady=16)

    cuadrillas = obtener_cuadrillas()

    def render_detalle(c):
        for w in detalle_inner.winfo_children():
            w.destroy()

        tk.Label(
            detalle_inner,
            text=f"Cuadrilla {c.id}",
            font=theme.FONT_HEADING,
            bg=theme.BG_CARD,
            fg=theme.TEXT,
        ).pack(anchor="w")

        resumen = tk.Frame(
            detalle_inner,
            bg=theme.PRIMARY_LIGHT,
            padx=12,
            pady=10,
        )
        resumen.pack(fill="x", pady=(12, 16))
        tk.Label(
            resumen,
            text=texto_cuadrilla_resumen(c),
            bg=theme.PRIMARY_LIGHT,
            fg=theme.TEXT,
            font=theme.FONT_BODY,
            justify="left",
        ).pack(anchor="w")

        tk.Label(
            detalle_inner,
            text="Ruta completa",
            font=theme.FONT_SUBHEADING,
            bg=theme.BG_CARD,
            fg=theme.TEXT,
        ).pack(anchor="w", pady=(0, 8))

        ruta_scroll = ScrollableFrame(detalle_inner, bg=theme.BG_CARD)
        ruta_frame = ruta_scroll.frame

        for i, v in enumerate(c.ruta, 1):
            item = tk.Frame(
                ruta_frame,
                bg=theme.BG_CARD_ALT,
                highlightthickness=1,
                highlightbackground=theme.BORDER,
                padx=10,
                pady=8,
            )
            item.pack(fill="x", pady=4)
            tk.Label(
                item,
                text=f"{i}. {v.nombre}",
                bg=theme.BG_CARD_ALT,
                fg=theme.TEXT,
                font=theme.FONT_BODY_BOLD,
            ).pack(anchor="w")
            tk.Label(
                item,
                text=f"{v.tipo.value}  ·  📍 {v.latitud:.4f}, {v.longitud:.4f}",
                bg=theme.BG_CARD_ALT,
                fg=theme.SUBTEXT,
                font=theme.FONT_SMALL,
            ).pack(anchor="w", pady=(2, 0))

    def render_vacio_detalle():
        for w in detalle_inner.winfo_children():
            w.destroy()
        tk.Label(
            detalle_inner,
            text="Selecciona una cuadrilla\npara ver el detalle de su ruta",
            bg=theme.BG_CARD,
            fg=theme.SUBTEXT,
            font=theme.FONT_BODY,
            justify="center",
        ).pack(expand=True)

    if not cuadrillas:
        tk.Label(
            lista_inner,
            text="Aún no hay planificación.\nPulsa «Generar planificación» para calcular rutas.",
            bg=theme.BG_CARD,
            fg=theme.SUBTEXT,
            font=theme.FONT_BODY,
            justify="center",
            pady=60,
        ).pack(fill="x")
        render_vacio_detalle()
        return

    for c in cuadrillas:
        card = tk.Frame(
            lista_inner,
            bg=theme.BG_CARD_ALT,
            highlightthickness=1,
            highlightbackground=theme.BORDER,
            padx=14,
            pady=12,
        )
        card.pack(fill="x", padx=8, pady=6)

        tk.Label(
            card,
            text=f"Cuadrilla {c.id}",
            bg=theme.BG_CARD_ALT,
            fg=theme.TEXT,
            font=theme.FONT_BODY_BOLD,
        ).pack(anchor="w")
        tk.Label(
            card,
            text=texto_cuadrilla_resumen(c).replace("\n", "  ·  "),
            bg=theme.BG_CARD_ALT,
            fg=theme.SUBTEXT,
            font=theme.FONT_SMALL,
            wraplength=400,
            justify="left",
        ).pack(anchor="w", pady=(4, 8))

        secondary_button(
            card,
            "Ver detalle →",
            lambda cuad=c: render_detalle(cuad),
        ).pack(anchor="e")

    render_vacio_detalle()

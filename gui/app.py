import tkinter as tk

from sistema_dinamico import inicializar_sistema

from gui import theme
from gui.context import AppContext
from gui.widgets import configurar_estilos_ttk
from gui import visitas, cuadrillas, materiales, planificacion, dinamico, simulacion

PANTALLAS = {
    "visitas": visitas.mostrar,
    "cuadrillas": cuadrillas.mostrar,
    "materiales": materiales.mostrar,
    "planificacion": planificacion.mostrar,
    "dinamico": dinamico.mostrar,
    "simulacion": simulacion.mostrar,
}


def _crear_sidebar(ctx: AppContext, menu: tk.Frame) -> None:
    brand = tk.Frame(menu, bg=theme.BG_MENU)
    brand.pack(fill="x", pady=(24, 20), padx=16)

    tk.Label(
        brand,
        text="⚡ Planificador",
        font=(theme.FONT_FAMILY, 15, "bold"),
        bg=theme.BG_MENU,
        fg="white",
    ).pack(anchor="w")
    tk.Label(
        brand,
        text="Gestión de cuadrillas",
        font=theme.FONT_SMALL,
        bg=theme.BG_MENU,
        fg="#94a3b8",
    ).pack(anchor="w", pady=(2, 0))

    tk.Frame(menu, bg="#334155", height=1).pack(fill="x", padx=16, pady=(0, 12))

    for titulo, icono, clave in theme.NAV_ITEMS:
        item = tk.Frame(menu, bg=theme.BG_MENU, cursor="hand2")
        item.pack(fill="x", padx=8, pady=2)
        ctx.registrar_nav(clave, item)

        inner = tk.Frame(item, bg=theme.BG_MENU)
        inner.pack(fill="x", padx=12, pady=12)

        tk.Label(
            inner,
            text=icono,
            font=(theme.FONT_FAMILY, 14),
            bg=theme.BG_MENU,
            fg="#cbd5e1",
        ).pack(side="left", padx=(0, 10))

        tk.Label(
            inner,
            text=titulo,
            font=theme.FONT_BODY,
            bg=theme.BG_MENU,
            fg="#cbd5e1",
        ).pack(side="left")

        def navegar(k=clave, cmd=PANTALLAS[clave]):
            if k != "simulacion":
                simulacion.al_salir()
            ctx.marcar_nav_activo(k)
            cmd(ctx)

        item.bind("<Button-1>", lambda e, n=navegar: n())
        for child in item.winfo_children():
            child.bind("<Button-1>", lambda e, n=navegar: n())
            for sub in child.winfo_children():
                sub.bind("<Button-1>", lambda e, n=navegar: n())

    footer = tk.Frame(menu, bg=theme.BG_MENU)
    footer.pack(side="bottom", fill="x", pady=16, padx=16)
    tk.Label(
        footer,
        text="TFG · Sistema de planificación",
        font=theme.FONT_CAPTION,
        bg=theme.BG_MENU,
        fg="#475569",
    ).pack(anchor="w")


def run_app() -> None:
    root = tk.Tk()
    root.title("Planificador de Cuadrillas")
    root.geometry("1280x760")
    root.minsize(1024, 640)
    root.configure(bg=theme.BG_APP)

    configurar_estilos_ttk()

    ctx = AppContext(root)

    menu = tk.Frame(root, bg=theme.BG_MENU, width=240)
    menu.pack(side="left", fill="y")
    menu.pack_propagate(False)

    content = tk.Frame(root, bg=theme.BG_APP)
    content.pack(side="right", expand=True, fill="both")

    ctx.set_frames(menu, content)
    _crear_sidebar(ctx, menu)

    inicializar_sistema()
    ctx.marcar_nav_activo("visitas")
    visitas.mostrar(ctx)

    root.mainloop()

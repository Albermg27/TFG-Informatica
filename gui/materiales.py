import tkinter as tk
from tkinter import ttk

from estado_dinamico import M
from gui import theme
from gui.context import AppContext
from gui.helpers import id_desde_etiqueta, opciones_catalogo
from gui.widgets import (
    ScrollableFrame,
    action_card,
    campo_entrada,
    modal_actions,
    page_header,
    section_card,
)
from modelos import Material


class MaterialesView:
    def __init__(self) -> None:
        self.ctx: AppContext | None = None
        self.materiales_frame: tk.Frame | None = None

    def render_materiales(self) -> None:
        if self.materiales_frame is None:
            return

        for w in self.materiales_frame.winfo_children():
            w.destroy()

        if not M:
            tk.Label(
                self.materiales_frame,
                text="No hay materiales registrados.\nAñade el primero con el botón superior.",
                bg=theme.BG_CARD,
                fg=theme.SUBTEXT,
                font=theme.FONT_BODY,
                pady=40,
            ).pack()
            return

        scroll = ScrollableFrame(self.materiales_frame, bg=theme.BG_CARD)
        grid = scroll.frame
        cols = 3
        for col in range(cols):
            grid.grid_columnconfigure(col, weight=1)

        for i, (m_id, material) in enumerate(sorted(M.items())):
            r, c = divmod(i, cols)
            stock_ok = material.cantidad_disponible > 0
            accent = theme.SUCCESS if stock_ok else theme.DANGER

            card = tk.Frame(
                grid,
                bg=theme.BG_CARD_ALT,
                highlightthickness=1,
                highlightbackground=theme.BORDER,
                padx=16,
                pady=14,
            )
            card.grid(row=r, column=c, padx=8, pady=8, sticky="nsew")

            tk.Label(
                card,
                text="📦",
                font=theme.FONT_ICON,
                bg=theme.BG_CARD_ALT,
                fg=accent,
            ).pack(anchor="w")
            tk.Label(
                card,
                text=material.nombre,
                font=theme.FONT_SUBHEADING,
                bg=theme.BG_CARD_ALT,
                fg=theme.TEXT,
            ).pack(anchor="w", pady=(4, 0))
            tk.Label(
                card,
                text=f"ID {m_id}",
                font=theme.FONT_CAPTION,
                bg=theme.BG_CARD_ALT,
                fg=theme.SUBTEXT,
            ).pack(anchor="w")

            stock_row = tk.Frame(card, bg=theme.BG_CARD_ALT)
            stock_row.pack(anchor="w", pady=(10, 0))
            tk.Label(
                stock_row,
                text="Stock disponible",
                font=theme.FONT_SMALL,
                bg=theme.BG_CARD_ALT,
                fg=theme.SUBTEXT,
            ).pack(side="left")
            tk.Label(
                stock_row,
                text=f"  {material.cantidad_disponible}",
                font=theme.FONT_BODY_BOLD,
                bg=theme.BG_CARD_ALT,
                fg=accent,
            ).pack(side="left")

    def popup_add_material(self) -> None:
        win = tk.Toplevel(self.ctx.root)
        win.title("Añadir material")
        win.configure(bg=theme.BG_APP)
        win.geometry("420x360")
        win.minsize(420, 360)
        win.transient(self.ctx.root)
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
            text="Nuevo material",
            font=theme.FONT_SUBHEADING,
            bg=theme.BG_CARD,
            fg=theme.TEXT,
        ).pack(anchor="w")

        e_nombre = campo_entrada(card, "Nombre del material")
        e_cant = campo_entrada(card, "Cantidad inicial", "0")
        msg = tk.Label(card, text="", bg=theme.BG_CARD, fg=theme.DANGER, font=theme.FONT_SMALL)
        msg.pack(pady=(8, 0))

        def guardar():
            try:
                nombre = e_nombre.get().strip()
                cant = int(e_cant.get())
                if not nombre:
                    raise ValueError
            except ValueError:
                msg.config(text="Introduce nombre y cantidad válidos")
                return
            nuevo_id = max(M.keys(), default=0) + 1
            M[nuevo_id] = Material(nuevo_id, nombre, cant)
            win.destroy()
            self.render_materiales()

        modal_actions(win, guardar, submit_text="Guardar material")
        win.bind("<Return>", lambda _e: guardar())

    def popup_edit_material(self) -> None:
        win = tk.Toplevel(self.ctx.root)
        win.title("Editar material")
        win.configure(bg=theme.BG_APP)
        win.geometry("420x360")
        win.minsize(420, 360)
        win.transient(self.ctx.root)
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

        tk.Label(card, text="Editar stock", font=theme.FONT_SUBHEADING, bg=theme.BG_CARD, fg=theme.TEXT).pack(
            anchor="w"
        )
        tk.Label(card, text="Material", font=theme.FONT_SMALL, bg=theme.BG_CARD, fg=theme.SUBTEXT).pack(
            anchor="w", pady=(16, 4)
        )
        var = tk.StringVar()
        combo = ttk.Combobox(card, textvariable=var, values=opciones_catalogo(), state="readonly")
        combo.pack(fill="x", ipady=4)
        e_cant = campo_entrada(card, "Nueva cantidad")
        msg = tk.Label(card, text="", bg=theme.BG_CARD, fg=theme.DANGER, font=theme.FONT_SMALL)
        msg.pack(pady=(8, 0))

        def guardar():
            m_id = id_desde_etiqueta(var.get())
            if m_id is None or m_id not in M:
                msg.config(text="Selecciona un material válido")
                return
            try:
                M[m_id].cantidad_disponible = int(e_cant.get())
            except ValueError:
                msg.config(text="Cantidad inválida")
                return
            win.destroy()
            self.render_materiales()

        modal_actions(win, guardar, submit_text="Guardar cambios")
        win.bind("<Return>", lambda _e: guardar())

    def popup_delete_material(self) -> None:
        win = tk.Toplevel(self.ctx.root)
        win.title("Eliminar material")
        win.configure(bg=theme.BG_APP)
        win.geometry("420x260")
        win.transient(self.ctx.root)
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
            text="Eliminar material",
            font=theme.FONT_SUBHEADING,
            bg=theme.BG_CARD,
            fg=theme.DANGER,
        ).pack(anchor="w")

        tk.Label(card, text="Material", font=theme.FONT_SMALL, bg=theme.BG_CARD, fg=theme.SUBTEXT).pack(
            anchor="w", pady=(16, 4)
        )
        var = tk.StringVar()
        combo = ttk.Combobox(card, textvariable=var, values=opciones_catalogo(), state="readonly")
        combo.pack(fill="x", ipady=4)

        def eliminar():
            m_id = id_desde_etiqueta(var.get())
            if m_id is None:
                return
            if m_id in M:
                del M[m_id]
            win.destroy()
            self.render_materiales()

        modal_actions(
            win,
            eliminar,
            submit_text="Eliminar",
            bg=theme.DANGER,
            activebackground="#b91c1c",
        )

    def mostrar(self, ctx: AppContext) -> None:
        self.ctx = ctx
        ctx.limpiar()

        page_header(
            ctx.content,
            "Gestión de materiales",
            "Catálogo global de materiales y stock en almacén",
        )

        acciones = tk.Frame(ctx.content, bg=theme.BG_APP)
        acciones.pack(fill="x", padx=24, pady=(0, 8))
        action_card(acciones, "Añadir stock", "➕", theme.SUCCESS, self.popup_add_material)
        action_card(acciones, "Editar stock", "✏️", theme.PRIMARY, self.popup_edit_material)
        action_card(acciones, "Eliminar stock", "🗑", theme.DANGER, self.popup_delete_material)

        body = section_card(ctx.content, "Inventario")
        self.materiales_frame = body
        self.render_materiales()


_vista: MaterialesView | None = None


def obtener_vista() -> MaterialesView:
    global _vista
    if _vista is None:
        _vista = MaterialesView()
    return _vista


def mostrar(ctx: AppContext) -> None:
    obtener_vista().mostrar(ctx)

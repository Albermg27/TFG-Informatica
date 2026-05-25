from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

from database.repository import get_instancias_db
from gui import theme
from gui.context import AppContext
from gui.helpers import widget_vivo

if TYPE_CHECKING:
    from gui.simulacion_vista import SimulacionView


def construir_controles(v: SimulacionView, ctx: AppContext) -> None:
    v.instancias_meta = get_instancias_db()
    v.instancia_var = tk.IntVar(value=v.instancias_meta[0].id if v.instancias_meta else 1)
    v.vel_var = tk.DoubleVar(value=2.0)
    v.vel_var.trace_add("write", lambda *_: on_vel_change(v))

    controles = tk.Frame(ctx.content, bg=theme.BG_APP)
    controles.pack(fill="x", padx=24, pady=(0, 4))

    toolbar = tk.Frame(controles, bg=theme.BG_APP)
    toolbar.pack(fill="x", pady=(0, 6))

    tk.Label(toolbar, text="Instancia", bg=theme.BG_APP, fg=theme.SUBTEXT, font=theme.FONT_SMALL).pack(
        side="left", padx=(0, 8)
    )
    nombres = [f"{i.id}. {i.nombre}" for i in v.instancias_meta] or ["1. (sin datos — ejecuta seed)"]
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
        if 0 <= idx < len(v.instancias_meta):
            inst = v.instancias_meta[idx]
            desc_lbl.config(
                text=f"{inst.descripcion or ''} · Jornada: {inst.jornada_minutos} min"
            )

    def _on_instancia_elegida(_e=None):
        idx = combo.current()
        if 0 <= idx < len(v.instancias_meta):
            v.instancia_var.set(v.instancias_meta[idx].id)
        _actualizar_desc()

    combo.bind("<<ComboboxSelected>>", _on_instancia_elegida)
    _actualizar_desc()

    for texto, cmd, bg, fg in (
        ("Cargar", lambda: cargar_instancia(v), theme.BG_CARD, theme.TEXT),
        ("▶ Iniciar", lambda: iniciar(v), theme.SUCCESS, "white"),
        ("⏸ Pausar", lambda: pausar(v), theme.WARNING, "white"),
        ("↺ Reiniciar", lambda: reiniciar(v), theme.BG_CARD, theme.TEXT),
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
    ttk.Scale(toolbar, from_=0.5, to=15, variable=v.vel_var, orient="horizontal", length=100).pack(
        side="left"
    )
    v.estado_lbl = tk.Label(
        toolbar, text="Lista", bg=theme.BG_APP, fg=theme.SUBTEXT, font=theme.FONT_BODY_BOLD
    )
    v.estado_lbl.pack(side="right", padx=8)


def on_vel_change(v: SimulacionView) -> None:
    if v.vel_var:
        v.motor.velocidad = v.vel_var.get()


def cargar_instancia(v: SimulacionView) -> None:
    iid = v.instancia_var.get() if v.instancia_var else 1
    v.motor.cargar_instancia(iid, semilla=iid * 17)
    v.refrescar_completo()


def iniciar(v: SimulacionView) -> None:
    if v.motor.instancia_id is None:
        cargar_instancia(v)
    v.motor.velocidad = v.vel_var.get() if v.vel_var else 2.0
    v.motor.iniciar()
    v.detener_loop()
    v.loop_simulacion()
    actualizar_estado_toolbar(v)


def pausar(v: SimulacionView) -> None:
    if v.motor.pausada:
        v.motor.reanudar()
    else:
        v.motor.pausar()
    actualizar_estado_toolbar(v)


def reiniciar(v: SimulacionView) -> None:
    v.detener_loop()
    v.motor.detener()
    cargar_instancia(v)


def actualizar_estado_toolbar(v: SimulacionView) -> None:
    if not widget_vivo(v.estado_lbl):
        return
    m = v.motor
    if m.finalizada:
        txt, col = "Jornada completada", theme.SUCCESS
    elif m.activa and not m.pausada:
        txt, col = f"En ejecución · {m.velocidad:.1f}×", theme.PRIMARY
    elif m.pausada:
        txt, col = "Pausada", theme.WARNING
    else:
        txt, col = "Lista", theme.SUBTEXT
    v.estado_lbl.config(text=txt, fg=col)


def actualizar_reloj(v: SimulacionView) -> None:
    if not widget_vivo(v.reloj_lbl):
        return
    from modelos import EstadoCuadrilla

    m = v.motor
    activas = sum(1 for c in m.C if c.estado != EstadoCuadrilla.INACTIVA)
    libres = sum(1 for c in m.C if c.estado == EstadoCuadrilla.LIBRE)
    v.reloj_lbl.config(
        text=(
            f"Reloj simulación: {m.tiempo:.0f} min  ·  "
            f"Jornada máx.: {m.J} min  ·  "
            f"Cuadrillas activas: {activas}  ·  Libres: {libres}"
        )
    )

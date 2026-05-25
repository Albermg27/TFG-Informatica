from __future__ import annotations

import tkinter as tk

from gui import theme
from gui.context import AppContext
from gui.helpers import widget_vivo
from gui import simulacion_controles as controles
from gui import simulacion_paneles as paneles
from gui.widgets import ScrollableFrame, page_header
from simulacion.motor import MotorSimulacion


class SimulacionView:
    UI_REFRESH_MS = paneles.UI_REFRESH_MS

    def __init__(self) -> None:
        self.ctx: AppContext | None = None
        self._motor: MotorSimulacion | None = None
        self.loop_id: str | None = None
        self.refresh_after_id: str | None = None
        self.pantalla_activa: bool = False
        self.log_rendered: int = 0
        self.last_cola_count: int = -1
        self.instancias_meta: list = []

        self.kpi_frame: tk.Frame | None = None
        self.crew_inner: tk.Frame | None = None
        self.crew_scroll: ScrollableFrame | None = None
        self.log_inner: tk.Frame | None = None
        self.log_scroll: ScrollableFrame | None = None
        self.materiales_inner: tk.Frame | None = None
        self.materiales_scroll: ScrollableFrame | None = None
        self.pagina_scroll: ScrollableFrame | None = None
        self.ultimo_evento_lbl: tk.Label | None = None
        self.reloj_lbl: tk.Label | None = None
        self.instancia_var: tk.IntVar | None = None
        self.vel_var: tk.DoubleVar | None = None
        self.estado_lbl: tk.Label | None = None
        self.kpi_valores: list[tk.Label] = []
        self.crew_panel_widgets: list[dict] = []
        self.cola_frame: tk.Frame | None = None
        self.mat_stock_labels: dict[int, tk.Label] = {}
        self.mat_cuad_labels: list[tk.Label] = []
        self.mat_pend_label: tk.Label | None = None

    @property
    def motor(self) -> MotorSimulacion:
        if self._motor is None:
            self._motor = MotorSimulacion(on_actualizar=self._on_motor_evento)
        return self._motor

    def salir(self) -> None:
        self.pantalla_activa = False
        if self.refresh_after_id and self.ctx:
            self.ctx.root.after_cancel(self.refresh_after_id)
        self.refresh_after_id = None
        self.detener_loop()
        if self._motor is not None:
            self._motor.pausar()
        self._limpiar_refs()

    def _limpiar_refs(self) -> None:
        self.kpi_frame = None
        self.crew_inner = None
        self.crew_scroll = None
        self.log_inner = None
        self.log_scroll = None
        self.materiales_inner = None
        self.materiales_scroll = None
        self.pagina_scroll = None
        self.ultimo_evento_lbl = None
        self.reloj_lbl = None
        self.estado_lbl = None
        self.kpi_valores = []
        self.crew_panel_widgets = []
        self.cola_frame = None
        self.last_cola_count = -1
        self.mat_stock_labels = {}
        self.mat_cuad_labels = []
        self.mat_pend_label = None

    def detener_loop(self) -> None:
        if self.ctx and self.loop_id:
            self.ctx.root.after_cancel(self.loop_id)
            self.loop_id = None

    def loop_simulacion(self) -> None:
        if not self.pantalla_activa or not widget_vivo(self.crew_inner):
            self.detener_loop()
            return
        m = self.motor
        if m.activa and not m.pausada:
            m.tick(0.05)
        if self.ctx and self.pantalla_activa:
            self.loop_id = self.ctx.root.after(50, self.loop_simulacion)

    def _on_motor_evento(self) -> None:
        if not self.pantalla_activa or self.ctx is None:
            return
        if self.refresh_after_id:
            self.ctx.root.after_cancel(self.refresh_after_id)
        self.refresh_after_id = self.ctx.root.after(
            self.UI_REFRESH_MS, self._ejecutar_refresh_pendiente
        )

    def _ejecutar_refresh_pendiente(self) -> None:
        self.refresh_after_id = None
        self._refrescar_por_evento_seguro()

    def _refrescar_por_evento_seguro(self) -> None:
        if not self.pantalla_activa or not widget_vivo(self.crew_inner):
            self.salir()
            return
        self.refrescar_por_evento()

    def refrescar_por_evento(self) -> None:
        m = self.motor
        tipo = m.eventos[-1].tipo if m.eventos else ""

        paneles.anadir_eventos_nuevos(self)
        paneles.actualizar_ultimo_evento(self)
        controles.actualizar_reloj(self)
        controles.actualizar_estado_toolbar(self)
        paneles.actualizar_kpis(self)
        paneles.refrescar_cuadrillas(self)

        if tipo in ("stock", "fin_visita", "sistema", "cancelacion"):
            paneles.refrescar_materiales(self)
        elif tipo == "visita_nueva" and self.mat_pend_label and widget_vivo(self.mat_pend_label):
            self.mat_pend_label.config(text=f"Visitas en cola: {len(m.V)}")

    def refrescar_completo(self) -> None:
        paneles.reset_log(self)
        paneles.construir_kpis(self)
        paneles.construir_cuadrillas(self)
        paneles.construir_materiales(self)
        paneles.anadir_eventos_nuevos(self)
        paneles.actualizar_ultimo_evento(self)
        controles.actualizar_reloj(self)
        controles.actualizar_estado_toolbar(self)

    def mostrar(self, ctx: AppContext) -> None:
        self.salir()
        self.ctx = ctx
        ctx.limpiar()
        self.log_rendered = 0

        page_header(
            ctx.content,
            "Simulación",
            "Monitor en tiempo real: cuadrillas, rutas, eventos e indicadores de calidad",
        )

        controles.construir_controles(self, ctx)

        self.pagina_scroll = ScrollableFrame(ctx.content, bg=theme.BG_APP)
        self.pagina_scroll.outer.pack(fill="both", expand=True)
        pagina = self.pagina_scroll.frame

        paneles.construir_layout_pagina(self, pagina)

        self.pantalla_activa = True

        if self.instancias_meta:
            self.motor.cargar_instancia(self.instancias_meta[0].id)
        self.refrescar_completo()


_vista: SimulacionView | None = None


def obtener_vista() -> SimulacionView:
    global _vista
    if _vista is None:
        _vista = SimulacionView()
    return _vista

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from gui import theme
from gui import estadisticas_paneles as paneles
from gui.context import AppContext
from gui.helpers import widget_vivo
from gui.widgets import ScrollableFrame, page_header, primary_button, secondary_button
from osrm_client import OSRMError
from simulacion.metricas import guardar_informe_casos_prueba

RUTA_INFORME_TXT = Path("informe_casos_prueba.txt")
from simulacion.resultados_casos import (
    hay_resultados,
    lista_instancias,
    obtener_resultados,
    seleccionar_vista,
)


class EstadisticasController:
    def __init__(self) -> None:
        self.ctx: AppContext | None = None
        self.modo_var: tk.StringVar | None = None
        self.instancia_var: tk.IntVar | None = None
        self.repeticion_var: tk.IntVar | None = None
        self.estado_lbl: tk.Label | None = None
        self.contenido_inner: tk.Frame | None = None
        self.combo_rep: ttk.Combobox | None = None
        self.combo_inst: ttk.Combobox | None = None
        self.combo_modo: ttk.Combobox | None = None
        self._modo_key_by_label: dict[str, str] = {}
        self.ejecutando: bool = False
        self._inst_map: dict[str, int] = {}

    def _modo_actual(self) -> str:
        if self.combo_modo is not None:
            return self._modo_key_by_label.get(self.combo_modo.get(), "instancia")
        if self.modo_var is not None:
            return self.modo_var.get()
        return "instancia"

    def set_estado(self, texto: str, color=None) -> None:
        if widget_vivo(self.estado_lbl):
            self.estado_lbl.config(text=texto, fg=color or theme.SUBTEXT)

    def actualizar_vista(self) -> None:
        if not widget_vivo(self.contenido_inner):
            return

        for w in self.contenido_inner.winfo_children():
            w.destroy()

        datos = obtener_resultados()
        if not datos:
            tk.Label(
                self.contenido_inner,
                text="No hay resultados. Ejecuta la batería de casos de prueba.",
                bg=theme.BG_APP,
                fg=theme.SUBTEXT,
                font=theme.FONT_BODY,
                pady=40,
            ).pack()
            return

        modo = self._modo_actual()
        if self.modo_var is not None:
            self.modo_var.set(modo)
        inst_id = self.instancia_var.get() if self.instancia_var else 1
        rep = self.repeticion_var.get() if self.repeticion_var else 1

        if modo == "iteracion":
            vista = seleccionar_vista(datos, "iteracion", inst_id, rep)
        elif modo == "instancia":
            vista = seleccionar_vista(datos, "instancia", inst_id)
        else:
            vista = seleccionar_vista(datos, "global")

        if vista is None:
            tk.Label(
                self.contenido_inner,
                text="Selección no válida.",
                bg=theme.BG_APP,
                fg=theme.DANGER,
                font=theme.FONT_BODY,
            ).pack(pady=20)
            return

        cab = tk.Frame(self.contenido_inner, bg=theme.BG_APP)
        cab.pack(fill="x", pady=(0, 12))
        tk.Label(
            cab,
            text=vista["titulo"],
            font=theme.FONT_HEADING,
            bg=theme.BG_APP,
            fg=theme.TEXT,
        ).pack(anchor="w")
        if vista.get("subtitulo"):
            tk.Label(
                cab,
                text=vista["subtitulo"],
                font=theme.FONT_BODY,
                bg=theme.BG_APP,
                fg=theme.SUBTEXT,
                wraplength=900,
                justify="left",
            ).pack(anchor="w", pady=(4, 0))

        paneles.resumen_visitas(
            self.contenido_inner,
            vista["estatico"],
            vista["dinamico"],
            es_media=vista.get("es_vista_media", False),
        )

        filas = vista.get("filas") or []
        if filas:
            paneles.panel_tabla_comparativa(self.contenido_inner, filas).pack(fill="x", pady=(0, 12))

        if vista.get("cronologia_estatico") or vista.get("cronologia_dinamico"):
            rutas_row = tk.Frame(self.contenido_inner, bg=theme.BG_APP)
            rutas_row.pack(fill="x")
            rutas_row.grid_columnconfigure(0, weight=1)
            rutas_row.grid_columnconfigure(1, weight=1)

            jornada = vista.get("jornada_minutos", 0)
            paneles.panel_rutas(
                rutas_row,
                "Rutas plan estático",
                vista.get("rutas_estatico"),
                cronologia=vista.get("cronologia_estatico"),
                jornada_minutos=jornada,
                pendientes=vista.get("pendientes_estatico"),
            ).grid(row=0, column=0, sticky="nsew", padx=(0, 8))
            es_media = vista.get("cronologia_es_media", False)
            if vista.get("cronologia_dinamico"):
                titulo_dyn = (
                    "Rutas dinámico (media de ejecuciones)"
                    if es_media
                    else "Rutas dinámico (completadas)"
                )
            else:
                titulo_dyn = "Rutas dinámico"
            paneles.panel_rutas(
                rutas_row,
                titulo_dyn,
                vista.get("rutas_dinamico"),
                cronologia=vista.get("cronologia_dinamico"),
                jornada_minutos=jornada,
                pendientes=vista.get("pendientes_dinamico"),
                canceladas=vista.get("canceladas_dinamico"),
                es_media=es_media,
            ).grid(row=0, column=1, sticky="nsew", padx=(8, 0))

    def on_modo_change(self, *_args) -> None:
        if self.combo_rep is None or self.modo_var is None:
            return
        modo = self._modo_actual()
        if self.modo_var is not None:
            self.modo_var.set(modo)
        es_global = modo == "global"
        es_iter = modo == "iteracion"
        if self.combo_inst is not None:
            self.combo_inst.configure(state="disabled" if es_global else "readonly")
        self.combo_rep.configure(state="readonly" if es_iter else "disabled")
        self.actualizar_vista()

    def refrescar_filtros(self) -> None:
        d = obtener_resultados()
        items = lista_instancias(d) if d else [(i, f"Instancia {i:02d}") for i in range(1, 11)]
        self._inst_map = {f"{i}. {n}": i for i, n in items}
        self.combo_inst["values"] = list(self._inst_map.keys())
        if self._inst_map:
            self.combo_inst.current(0)
            self.instancia_var.set(list(self._inst_map.values())[0])
        if d and self.combo_rep is not None:
            n = d.get("repeticiones", 5)
            self.combo_rep["values"] = [str(i) for i in range(1, n + 1)]
            self.combo_rep.current(0)
            self.repeticion_var.set(1)

    def ejecutar_bateria(self) -> None:
        if self.ejecutando or self.ctx is None:
            return

        self.ejecutando = True
        self.set_estado("Ejecutando batería (OSRM, espere…)…", theme.WARNING)

        def _progreso(hecho: int, total: int, instancia_id: int, repeticion: int):
            def _upd():
                fase = "plan estático" if repeticion == 0 else f"dinámico rep. {repeticion}"
                self.set_estado(f"Progreso: {hecho}/{total} · inst. {instancia_id} · {fase}", theme.WARNING)

            self.ctx.root.after(0, _upd)

        def _run():
            try:
                path = guardar_informe_casos_prueba(RUTA_INFORME_TXT, on_progreso=_progreso)

                def _ok():
                    self.set_estado(f"Listo · informe: {path.resolve()}", theme.SUCCESS)
                    self.refrescar_filtros()
                    self.on_modo_change()

                self.ctx.root.after(0, _ok)
            except OSRMError as exc:

                def _err_osrm():
                    self.set_estado("Error OSRM — batería abortada", theme.DANGER)
                    messagebox.showerror(
                        "Error OSRM",
                        f"La batería se ha detenido porque OSRM no respondió correctamente.\n\n{exc}",
                    )

                self.ctx.root.after(0, _err_osrm)
            except Exception as exc:

                def _err():
                    self.set_estado("Error en la batería", theme.DANGER)
                    messagebox.showerror("Error", str(exc))

                self.ctx.root.after(0, _err)
            finally:
                self.ejecutando = False

        threading.Thread(target=_run, daemon=True).start()

    def mostrar(self, ctx: AppContext) -> None:
        self.ctx = ctx
        ctx.limpiar()

        page_header(
            ctx.content,
            "Estadísticas de casos de prueba",
            "Plan vs simulación"
        )

        toolbar = tk.Frame(ctx.content, bg=theme.BG_APP)
        toolbar.pack(fill="x", padx=24, pady=(0, 8))

        filtros = tk.Frame(toolbar, bg=theme.BG_APP)
        filtros.pack(fill="x", pady=(0, 8))

        tk.Label(filtros, text="Vista", bg=theme.BG_APP, fg=theme.SUBTEXT, font=theme.FONT_SMALL).pack(
            side="left", padx=(0, 6)
        )
        self.modo_var = tk.StringVar(value="instancia")
        modo_labels = {
            "iteracion": "Iteración concreta",
            "instancia": "Media instancia",
            "global": "Global",
        }
        self._modo_key_by_label = {v: k for k, v in modo_labels.items()}
        self.combo_modo = ttk.Combobox(
            filtros,
            state="readonly",
            width=22,
            values=list(modo_labels.values()),
        )
        self.combo_modo.pack(side="left", padx=(0, 16))
        self.combo_modo.set(modo_labels["instancia"])

        tk.Label(
            filtros, text="Instancia", bg=theme.BG_APP, fg=theme.SUBTEXT, font=theme.FONT_SMALL
        ).pack(side="left", padx=(0, 6))

        datos_ini = obtener_resultados()
        inst_list = lista_instancias(datos_ini) if datos_ini else [(i, f"Instancia {i:02d}") for i in range(1, 11)]
        self.instancia_var = tk.IntVar(value=inst_list[0][0] if inst_list else 1)

        self.combo_inst = ttk.Combobox(filtros, width=36, state="readonly")
        self.combo_inst.pack(side="left", padx=(0, 16))

        def _on_inst_sel(_e=None):
            sel = self.combo_inst.get()
            if sel in self._inst_map:
                self.instancia_var.set(self._inst_map[sel])
            self.actualizar_vista()

        self.combo_inst.bind("<<ComboboxSelected>>", _on_inst_sel)

        tk.Label(
            filtros, text="Iteración", bg=theme.BG_APP, fg=theme.SUBTEXT, font=theme.FONT_SMALL
        ).pack(side="left", padx=(0, 6))
        self.repeticion_var = tk.IntVar(value=1)
        n_rep = datos_ini.get("repeticiones", 5) if datos_ini else 5
        self.combo_rep = ttk.Combobox(
            filtros,
            width=6,
            state="readonly",
            values=[str(i) for i in range(1, n_rep + 1)],
        )
        self.combo_rep.pack(side="left")
        self.combo_rep.current(0)

        def _on_rep_sel(_e=None):
            try:
                self.repeticion_var.set(int(self.combo_rep.get()))
            except ValueError:
                pass
            if self._modo_actual() == "iteracion":
                self.actualizar_vista()

        self.combo_rep.bind("<<ComboboxSelected>>", _on_rep_sel)

        def _on_modo_sel(_e=None):
            label = self.combo_modo.get()
            self.modo_var.set(self._modo_key_by_label.get(label, "instancia"))
            self.on_modo_change()

        self.combo_modo.bind("<<ComboboxSelected>>", _on_modo_sel)

        acciones = tk.Frame(toolbar, bg=theme.BG_APP)
        acciones.pack(fill="x")

        primary_button(acciones, "Ejecutar", self.ejecutar_bateria).pack(side="left", padx=(0, 8))

        secondary_button(acciones, "Actualizar vista", self.actualizar_vista).pack(side="left")

        self.estado_lbl = tk.Label(
            acciones,
            text="Sin datos" if not hay_resultados() else "Resultados cargados",
            bg=theme.BG_APP,
            fg=theme.SUCCESS if hay_resultados() else theme.SUBTEXT,
            font=theme.FONT_BODY_BOLD,
        )
        self.estado_lbl.pack(side="right", padx=8)

        scroll = ScrollableFrame(ctx.content, bg=theme.BG_APP)
        scroll.outer.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self.contenido_inner = scroll.frame

        self.refrescar_filtros()
        self.on_modo_change()
        self.actualizar_vista()


_controller: EstadisticasController | None = None


def obtener_controller() -> EstadisticasController:
    global _controller
    if _controller is None:
        _controller = EstadisticasController()
    return _controller

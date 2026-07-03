from __future__ import annotations

import copy
import random
from dataclasses import dataclass
from typing import Callable

from datos import enlazar_visita_matriz, cargar_datos_instancia, matriz_km_osrm_desde_coords
from modelos import EstadoCuadrilla, TipoVisita, Visita, consumir_materiales_cuadrilla
from postprocessing import postprocesar
from preprocessing import preprocesar
from simulacion.config_instancia import perfil_simulacion
from simulacion.estrategias_asignacion import (
    ESTRATEGIA_ALEATORIA,
    ESTRATEGIA_MILP,
    etiqueta_estrategia,
    medidor_tiempos_asignacion,
    normalizar_estrategia,
    resolver_asignacion,
)
from simulacion.guion_eventos import (
    GuionEventos,
    PASO_MINUTOS_DEFECTO,
    MAX_PASOS_DEFECTO,
    generar_guion_eventos,
    semilla_factores,
)
from simulacion.plan_estatico import preparar_cuadrillas_segun_plan
from simulacion.metricas import (
    IndicadoresCalidad,
    cerrar_servicio_dinamico,
    cerrar_viaje_dinamico,
    cronologia_cuadrillas,
    iniciar_tramo_dinamico,
    nombres_visitas_pendientes,
    rutas_desde_cuadrillas,
    tiempos_finales_cuadrillas,
)


@dataclass
class EventoSim:
    tiempo: float
    tipo: str
    mensaje: str
    cuadrilla_id: int | None = None


class MotorSimulacion:
    COLORES_CUADRILLA = ["#2563eb", "#16a34a", "#d97706", "#7c3aed", "#db2777"]

    def __init__(self, on_actualizar: Callable | None = None):
        self.on_actualizar = on_actualizar
        self.instancia_id: int | None = None
        self.V: list = []
        self.C: list = []
        self.M: dict = {}
        self.D: dict = {}
        self.COORDS: dict = {}
        self.K: dict = {}
        self.J = 1000
        self.almacen_id = 1
        self.tiempo = 0.0
        self.velocidad = 2.0
        self.activa = False
        self.pausada = False
        self.finalizada = False
        self.eventos: list[EventoSim] = []
        self.metricas = IndicadoresCalidad()
        self._rng_factores = random.Random()
        self._visitas_iniciales = 0
        self._next_visita_seq = 10000
        self._urgente_num = 0
        self._perfil = perfil_simulacion(1)
        self.estrategia_asignacion = ESTRATEGIA_MILP
        self._oleada_random = 0
        self._semilla_base = 0
        self._guion: GuionEventos | None = None
        self._guion_cursor_urg = 0
        self._guion_cursor_canc = 0

    def cargar_instancia(
        self,
        instancia_id: int,
        semilla: int | None = None,
        estrategia_asignacion: str = ESTRATEGIA_MILP,
        guion_eventos: GuionEventos | None = None,
    ):
        self.detener()
        self.instancia_id = instancia_id
        self.estrategia_asignacion = normalizar_estrategia(estrategia_asignacion)
        if semilla is not None:
            self._semilla_base = int(semilla)
        else:
            self._semilla_base = int(instancia_id * 7919)
        self._rng_factores.seed(semilla_factores(self._semilla_base))
        if guion_eventos is None:
            guion_eventos = generar_guion_eventos(
                instancia_id,
                self._semilla_base,
            )
        self._guion = guion_eventos

        V, C, M, params, D, coords, K = cargar_datos_instancia(instancia_id)
        self.V = copy.deepcopy(V)
        self.C = copy.deepcopy(C)
        self.M = copy.deepcopy(M)
        self.D = copy.deepcopy(D)
        self.COORDS = copy.deepcopy(coords)
        self.K = copy.deepcopy(K)
        self.J = params["J"]
        self.almacen_id = params["almacen_id"]

        self._perfil = perfil_simulacion(instancia_id)
        self._plan_estatico = preparar_cuadrillas_segun_plan(
            self.C,
            self.M,
            instancia_id,
            buffer_stock=self._perfil.extra_stock_plan_pct,
            silent=True,
            estrategia=self.estrategia_asignacion,
            semilla_aleatoria=semilla,
        )
        for c in self.C:
            c.posicion = self.almacen_id
            c.reset_dinamico()
            c.sim_progreso = 0.0
            c.sim_duracion_fase = 0.0
            c.sim_tiempo_fase = 0.0
            c.tiempo_acumulado = 0.0

        self.tiempo = 0.0
        self.finalizada = False
        self.eventos.clear()
        self.metricas.reset()
        self._visitas_iniciales = len(self.V)
        self._urgente_num = 0
        self._oleada_random = 0
        self._guion_cursor_urg = 0
        self._guion_cursor_canc = 0
        self.metricas.visitas_pendientes = len(self.V)
        self._log(
            "sistema",
            f"Instancia {instancia_id} cargada · {len(self.V)} visitas · jornada {self.J} min · "
            f"estrategia {etiqueta_estrategia(self.estrategia_asignacion)}",
        )

    def iniciar(self):
        if self.instancia_id is None:
            return
        medidor_tiempos_asignacion.reiniciar()
        self.pausada = False
        self.activa = True
        self.finalizada = False
        self._aplicar_asignacion_inicial_plan()
        self._asignar_cola_pendiente()
        self._log("sistema", "Simulación iniciada — misma 1.ª asignación que el plan estático")
        self._notificar()

    def detener(self):
        self.activa = False
        self.pausada = False

    def pausar(self):
        self.pausada = True

    def reanudar(self):
        if not self.finalizada:
            self.pausada = False

    def jornada_activa(self) -> bool:
        return not self.finalizada and self.tiempo < self.J

    def _cuadrillas_ocupadas(self) -> bool:
        return any(
            c.estado in (EstadoCuadrilla.DESPLAZANDOSE, EstadoCuadrilla.TRABAJANDO)
            for c in self.C
        )

    def _finalizar_jornada(self):
        if self.finalizada:
            return
        if self._cuadrillas_ocupadas():
            return
        self.finalizada = True
        self.activa = False
        self.pausada = True
        for c in self.C:
            if c.estado != EstadoCuadrilla.INACTIVA:
                c.estado = EstadoCuadrilla.INACTIVA
            c.visita_actual = None
            c.sim_progreso = 0.0
            c.sim_tiempo_fase = 0.0
            c.tiempo_jornada = min(c.tiempo_jornada, float(self.J))
        msg = f"Fin de jornada ({self.J} min)"
        if self.tiempo > self.J:
            msg += f" — última actividad a {self.tiempo:.0f} min"
        self._log("sistema", msg)

    def reiniciar(self):
        if self.instancia_id:
            self.cargar_instancia(self.instancia_id)

    def simular_hasta_fin(
        self,
        paso_minutos: float = PASO_MINUTOS_DEFECTO,
        max_pasos: int = MAX_PASOS_DEFECTO,
    ) -> dict:
        if self.instancia_id is None:
            return self.metricas.resumen(jornada=self.J)
        self.velocidad = 1.0
        self.iniciar()
        pasos = 0
        while not self.finalizada and pasos < max_pasos:
            self.tick(paso_minutos)
            pasos += 1
        if not self.finalizada:
            self._finalizar_jornada()
        resumen = self.metricas.resumen(jornada=self.J)
        resumen["modo"] = "dinamico"
        resumen["estrategia"] = self.estrategia_asignacion
        resumen["estrategia_etiqueta"] = etiqueta_estrategia(self.estrategia_asignacion)
        resumen["rutas"] = rutas_desde_cuadrillas(self.C)
        resumen["tiempos_cuadrillas"] = tiempos_finales_cuadrillas(self.C)
        resumen["cronologia_cuadrillas"] = cronologia_cuadrillas(self.C)
        resumen["pendientes_nombres"] = nombres_visitas_pendientes(self.V)
        resumen.update(medidor_tiempos_asignacion.resumen())
        return resumen

    def tick(self, dt_real: float = 0.05):
        if not self.activa or self.pausada or self.finalizada:
            return

        dt_aplicado = dt_real * self.velocidad
        if dt_aplicado <= 0:
            return

        self.tiempo += dt_aplicado

        self._avanzar_tiempos_jornada(dt_aplicado)
        self._avanzar_fases(dt_aplicado)

        if self.jornada_activa():
            self._aplicar_eventos_guion()
            if self.V and any(c.estado == EstadoCuadrilla.LIBRE for c in self.C):
                self._asignar_cola_pendiente()

        if self.tiempo >= self.J:
            if self._todas_inactivas():
                self._finalizar_jornada()
        elif self._todas_inactivas() and not self.V:
            self.finalizada = True
            self.activa = False
            self.pausada = True
            self._log("sistema", "Jornada finalizada — todas las cuadrillas inactivas")

        self.metricas.visitas_pendientes = len(self.V)

    def _todas_inactivas(self):
        return self.C and all(c.estado == EstadoCuadrilla.INACTIVA for c in self.C)

    def _aplicar_eventos_guion(self):
        if not self.jornada_activa() or self._guion is None:
            return
        urgentes = self._guion.urgentes
        while self._guion_cursor_urg < len(urgentes):
            ev = urgentes[self._guion_cursor_urg]
            if ev.tiempo > self.tiempo:
                break
            self._aplicar_visita_urgente_guion(ev)
            self._guion_cursor_urg += 1

        cancelaciones = self._guion.cancelaciones
        while self._guion_cursor_canc < len(cancelaciones):
            ev = cancelaciones[self._guion_cursor_canc]
            if ev.tiempo > self.tiempo:
                break
            self._aplicar_cancelacion_guion(ev)
            self._guion_cursor_canc += 1

    def _factor_viaje_real(self) -> float:
        p = self._perfil
        return self._rng_factores.uniform(p.factor_viaje_min, p.factor_viaje_max)

    def _factor_trabajo_real(self) -> float:
        p = self._perfil
        return self._rng_factores.uniform(p.factor_trabajo_min, p.factor_trabajo_max)

    def _aplicar_visita_urgente_guion(self, ev):
        if not self.COORDS:
            return
        self._next_visita_seq += 1
        self._urgente_num = ev.numero_urgente
        visita = Visita(
            tipo=ev.tipo,
            prioridad=ev.prioridad,
            nombre=f"Urgente {ev.numero_urgente}",
            latitud=ev.latitud,
            longitud=ev.longitud,
            id=self._next_visita_seq,
        )
        visita.materiales_necesarios = dict(ev.materiales_necesarios)
        enlazar_visita_matriz(self.D, self.COORDS, visita)
        self.K = matriz_km_osrm_desde_coords(
            self.COORDS,
            contexto=f"urgente id={visita.id}",
        )
        self.V.append(visita)
        self.metricas.visitas_generadas += 1
        self.metricas.visitas_pendientes = len(self.V)
        est_viaje = self.D.get(self.almacen_id, {}).get(visita.id, 0)
        self._log(
            "visita_nueva",
            f"Nueva visita: {visita.nombre} ({ev.tipo.value}, {visita.duracion} min, "
            f"viaje est. {est_viaje:.0f} min)",
            None,
        )
        self._asignar_cola_pendiente()

    def _aplicar_cancelacion_guion(self, ev):
        visita = next((v for v in self.V if v.id == ev.visita_id), None)
        if visita is None or visita.tipo == TipoVisita.ALMACEN:
            candidatas = sorted(
                (
                    v for v in self.V
                    if v.tipo != TipoVisita.ALMACEN and not self._es_visita_urgente(v)
                ),
                key=lambda v: v.id,
            )
            if not candidatas:
                return
            visita = candidatas[0]
        self.V.remove(visita)
        visita.cancelada = True
        self.metricas.registrar_cancelacion(visita.nombre)
        self.metricas.visitas_pendientes = len(self.V)
        self._log(
            "cancelacion",
            f"Visita cancelada: {visita.nombre} ({visita.tipo.value}, P{visita.prioridad})",
            None,
        )

    def _es_visita_urgente(self, visita) -> bool:
        return visita.nombre.startswith("Urgente")

    def _asignar_cola_pendiente(self) -> None:
        if not self.jornada_activa() or not self.V:
            return
        max_iter = len(self.V) + len(self.C) + 1
        for _ in range(max_iter):
            if not any(c.estado == EstadoCuadrilla.LIBRE for c in self.C):
                return
            antes = len(self.V)
            self._ejecutar_asignacion()
            if len(self.V) == antes:
                return

    def _avanzar_tiempos_jornada(self, dt: float):
        for c in self.C:
            if c.estado == EstadoCuadrilla.INACTIVA:
                continue
            if c.tiempo_jornada < self.J:
                c.tiempo_jornada = min(float(self.J), c.tiempo_jornada + dt)

    def _avanzar_fases(self, dt: float):
        for c in self.C:
            if c.estado in (EstadoCuadrilla.INACTIVA, EstadoCuadrilla.LIBRE):
                continue
            c.sim_tiempo_fase += dt
            if c.sim_duracion_fase > 0:
                c.sim_progreso = min(1.0, c.sim_tiempo_fase / c.sim_duracion_fase)

            if c.estado == EstadoCuadrilla.DESPLAZANDOSE:
                if c.sim_tiempo_fase >= c.sim_duracion_fase:
                    self._completar_desplazamiento(c)
            elif c.estado == EstadoCuadrilla.TRABAJANDO:
                if c.sim_tiempo_fase >= c.sim_duracion_fase:
                    self._completar_trabajo(c)

    def _completar_desplazamiento(self, c):
        if not c.visita_actual:
            return
        real = c.sim_duracion_fase
        km = self.K.get(c.posicion, {}).get(c.visita_actual.id, 0.0)
        self.metricas.registrar_desplazamiento(km)
        c.completar_desplazamiento(real)
        cerrar_viaje_dinamico(c)
        c.sim_progreso = 0.0
        c.sim_tiempo_fase = 0.0
        est_trab = c.visita_actual.duracion
        c.sim_duracion_fase = est_trab * self._factor_trabajo_real()
        self._log(
            "llegada",
            f"C{c.id} llegó a {c.visita_actual.nombre} ({real:.1f} min)",
            c.id,
        )

    def _completar_trabajo(self, c):
        if not c.visita_actual:
            return
        real = c.sim_duracion_fase
        consumir_materiales_cuadrilla(c, c.visita_actual)
        c.finalizar_trabajo(real, self.J)
        cerrar_servicio_dinamico(c)
        c.posicion = c.historial[-1][0].id if c.historial else self.almacen_id
        c.sim_progreso = 0.0
        c.sim_tiempo_fase = 0.0
        self.metricas.visitas_completadas += 1
        exceso = " (tras fin de jornada)" if c.tiempo_acumulado > self.J else ""
        self._log(
            "fin_visita",
            f"C{c.id} finalizó {c.historial[-1][0].nombre} ({real:.1f} min, "
            f"t={c.tiempo_acumulado:.0f}){exceso}",
            c.id,
        )
        if self.jornada_activa():
            self._asignar_cola_pendiente()

    def _aplicar_asignaciones(self, asignaciones_ok: list, origen: str = "dinamico"):
        if not asignaciones_ok:
            return
        self.V, self.C = postprocesar(asignaciones_ok, self.V, self.C, self.M, self.D, True)
        for visita, c in asignaciones_ok:
            est = c.tiempo_estimado_viaje
            iniciar_tramo_dinamico(c, visita)
            c.sim_duracion_fase = est * self._factor_viaje_real()
            c.sim_tiempo_fase = 0.0
            c.sim_progreso = 0.0
        for v, c in asignaciones_ok:
            self._log(
                "asignacion",
                f"Asignada {v.nombre} → Cuadrilla {c.id} "
                f"(viaje est. {c.tiempo_estimado_viaje:.1f} min, real×{self._perfil.factor_viaje_max:.2f})",
                c.id,
                notify=False,
            )
        self._log("sistema", f"Asignación ({origen}): {len(asignaciones_ok)} visitas", notify=False)
        self._notificar()

    def _aplicar_asignacion_inicial_plan(self):
        if not self.jornada_activa():
            return
        oleada = getattr(self._plan_estatico, "primera_oleada", None) or []
        if not oleada:
            self._ejecutar_asignacion()
            return

        asignaciones_ok = []
        for visita_id, cid in oleada:
            visita = next((v for v in self.V if v.id == visita_id), None)
            cuadrilla = next((c for c in self.C if c.id == cid), None)
            if visita is None or cuadrilla is None:
                continue
            if cuadrilla.estado != EstadoCuadrilla.LIBRE:
                continue
            leg = self.D.get(cuadrilla.posicion, {}).get(visita.id, float("inf"))
            if leg == float("inf"):
                continue
            if cuadrilla.tiempo_acumulado + leg + visita.duracion > self.J:
                continue
            asignaciones_ok.append((visita, cuadrilla))

        self._aplicar_asignaciones(asignaciones_ok, origen="plan inicial")

    def _ejecutar_asignacion(self):
        if not self.jornada_activa():
            return
        urgentes = [v for v in self.V if self._es_visita_urgente(v)]
        colas: list[tuple[list, str]] = [(urgentes, "urgente")] if urgentes else []
        colas.append((self.V, "replanificación"))

        for cola, origen in colas:
            if not cola:
                continue
            V_est, C_est, F = preprocesar(cola, self.C, self.M, self.J, self.D, modo="dinamico")
            if not C_est or not V_est:
                continue
            rng = (
                random.Random(self._semilla_base * 1_000_003 + self._oleada_random)
                if self.estrategia_asignacion == ESTRATEGIA_ALEATORIA
                else None
            )
            asignaciones = resolver_asignacion(
                V_est,
                C_est,
                self.D,
                F,
                self.M,
                self.J,
                "dinamico",
                estrategia=self.estrategia_asignacion,
                rng=rng,
            )
            if not asignaciones:
                self._oleada_random += 1
                continue
            asignaciones_ok = []
            for visita, c in asignaciones:
                leg = self.D.get(c.posicion, {}).get(visita.id, float("inf"))
                if c.tiempo_acumulado + leg + visita.duracion > self.J:
                    continue
                asignaciones_ok.append((visita, c))
            if asignaciones_ok:
                self._aplicar_asignaciones(asignaciones_ok, origen=origen)
                self._oleada_random += 1
                return
            self._oleada_random += 1

    def posicion_cuadrilla(self, c) -> tuple[float, float]:
        if c.estado == EstadoCuadrilla.DESPLAZANDOSE and c.visita_actual:
            origen = self.COORDS.get(c.posicion, self.COORDS.get(self.almacen_id))
            dest = self.COORDS[c.visita_actual.id]
            t = c.sim_progreso
            return (
                origen[0] + t * (dest[0] - origen[0]),
                origen[1] + t * (dest[1] - origen[1]),
            )
        if c.estado == EstadoCuadrilla.TRABAJANDO and c.visita_actual:
            return self.COORDS[c.visita_actual.id]
        return self.COORDS.get(c.posicion, self.COORDS.get(self.almacen_id, (40.54, -3.64)))

    def color_cuadrilla(self, idx: int) -> str:
        return self.COLORES_CUADRILLA[idx % len(self.COLORES_CUADRILLA)]

    def _log(self, tipo: str, mensaje: str, cuadrilla_id: int | None = None, notify: bool = True):
        ev = EventoSim(self.tiempo, tipo, mensaje, cuadrilla_id)
        self.eventos.append(ev)
        self.metricas.eventos_totales += 1
        if len(self.eventos) > 200:
            self.eventos = self.eventos[-200:]
        if notify:
            self._notificar()

    def _notificar(self):
        if self.on_actualizar:
            self.on_actualizar()

from __future__ import annotations

import copy
import math
import random
from dataclasses import dataclass
from typing import Callable

from datos import enlazar_visita_matriz, cargar_datos_instancia, matriz_km_osrm_desde_coords
from modelos import EstadoCuadrilla, TipoVisita, Visita, consumir_materiales_cuadrilla
from postprocessing import postprocesar
from preprocessing import preprocesar
from model import asignar_visitas
from simulacion.config_instancia import (
    MADRID_CENTRO,
    MADRID_LAT_MAX,
    MADRID_LAT_MIN,
    MADRID_LON_MAX,
    MADRID_LON_MIN,
    coordenada_en_zona,
    perfil_simulacion,
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
        self.M_big = 1000
        self.almacen_id = 1
        self.tiempo = 0.0
        self.velocidad = 2.0
        self.activa = False
        self.pausada = False
        self.finalizada = False
        self.eventos: list[EventoSim] = []
        self.metricas = IndicadoresCalidad()
        self._rng = random.Random()
        self._visitas_iniciales = 0
        self._next_visita_seq = 10000
        self._urgente_num = 0
        self._perfil = perfil_simulacion(1)

    def cargar_instancia(self, instancia_id: int, semilla: int | None = None):
        self.detener()
        self.instancia_id = instancia_id
        if semilla is not None:
            self._rng.seed(semilla)
        else:
            self._rng.seed(instancia_id * 7919)

        V, C, M, params, D, coords, K = cargar_datos_instancia(instancia_id)
        self.V = copy.deepcopy(V)
        self.C = copy.deepcopy(C)
        self.M = copy.deepcopy(M)
        self.D = copy.deepcopy(D)
        self.COORDS = copy.deepcopy(coords)
        self.K = copy.deepcopy(K)
        self.J = params["J"]
        self.M_big = params["M_big"]
        self.almacen_id = params["almacen_id"]

        self._perfil = perfil_simulacion(instancia_id)
        self._plan_estatico = preparar_cuadrillas_segun_plan(
            self.C,
            self.M,
            instancia_id,
            buffer_stock=self._perfil.extra_stock_plan_pct,
            silent=True,
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
        self.metricas.visitas_pendientes = len(self.V)
        self._log("sistema", f"Instancia {instancia_id} cargada · {len(self.V)} visitas · jornada {self.J} min")

    def iniciar(self):
        if self.instancia_id is None:
            return
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

    def simular_hasta_fin(self, paso_minutos: float = 10.0, max_pasos: int = 5000) -> dict:
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
        resumen["rutas"] = rutas_desde_cuadrillas(self.C)
        resumen["tiempos_cuadrillas"] = tiempos_finales_cuadrillas(self.C)
        resumen["cronologia_cuadrillas"] = cronologia_cuadrillas(self.C)
        resumen["pendientes_nombres"] = nombres_visitas_pendientes(self.V)
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
            self._eventos_aleatorios(dt_aplicado)
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

    def _eventos_aleatorios(self, dt_minutos: float):
        if not self.jornada_activa():
            return
        prob = self._perfil.prob_visitas_por_minuto * dt_minutos
        if prob > 0 and self._rng.random() < prob:
            self._generar_visita_urgente()
        prob_cancelacion = self._perfil.prob_cancelaciones_por_minuto * dt_minutos
        if prob_cancelacion > 0 and self._rng.random() < prob_cancelacion:
            self._generar_cancelacion_visita()

    def _factor_viaje_real(self) -> float:
        p = self._perfil
        return self._rng.uniform(p.factor_viaje_min, p.factor_viaje_max)

    def _factor_trabajo_real(self) -> float:
        p = self._perfil
        return self._rng.uniform(p.factor_trabajo_min, p.factor_trabajo_max)

    def _coords_visita_urgente(self) -> tuple[float, float]:
        p = self._perfil
        amp = 0.006 + p.dispersion_visitas * 0.045
        modo = p.modo_coords_urgente

        if modo == "dispersa_madrid":
            return (
                self._rng.uniform(MADRID_LAT_MIN, MADRID_LAT_MAX),
                self._rng.uniform(MADRID_LON_MIN, MADRID_LON_MAX),
            )

        if modo == "periferia_madrid":
            clat, clon = MADRID_CENTRO
            ang = self._rng.uniform(0, 2 * math.pi)
            r = p.radio_urgente_grados + self._rng.uniform(0.05, 0.10)
            return (clat + r * math.cos(ang), clon + r * math.sin(ang) * 0.85)

        if modo == "cluster" and p.centro_urgente_lat is not None and p.centro_urgente_lon is not None:
            r = p.radio_urgente_grados
            return (
                p.centro_urgente_lat + self._rng.uniform(-r, r),
                p.centro_urgente_lon + self._rng.uniform(-r, r),
            )

        if modo == "cerca_almacen":
            base = self.COORDS.get(self.almacen_id) or next(iter(self.COORDS.values()), MADRID_CENTRO)
            return (
                base[0] + self._rng.uniform(-amp, amp),
                base[1] + self._rng.uniform(-amp, amp),
            )

        if modo == "zona_plan" and p.zona_urgente:
            candidatas = [
                c for c in self.COORDS.values()
                if coordenada_en_zona(c[0], c[1], p.zona_urgente)
            ]
            if candidatas:
                base_lat, base_lon = self._rng.choice(candidatas)
                r = p.radio_urgente_grados
                return (
                    base_lat + self._rng.uniform(-r, r),
                    base_lon + self._rng.uniform(-r, r),
                )

        base_lat, base_lon = self._rng.choice(list(self.COORDS.values()))
        return (
            base_lat + self._rng.uniform(-amp, amp),
            base_lon + self._rng.uniform(-amp, amp),
        )

    def _generar_visita_urgente(self):
        if not self.COORDS:
            return
        tipos = [TipoVisita.TECNICA, TipoVisita.INCIDENCIA, TipoVisita.INSTALACION]
        p = self._perfil
        tipo = self._rng.choices(
            tipos,
            weights=[p.peso_tecnica, p.peso_incidencia, p.peso_instalacion],
            k=1,
        )[0]
        lat, lon = self._coords_visita_urgente()
        self._next_visita_seq += 1
        self._urgente_num += 1
        visita = Visita(
            tipo=tipo,
            prioridad=self._rng.randint(6, 10),
            nombre=f"Urgente {self._urgente_num}",
            latitud=lat,
            longitud=lon,
            id=self._next_visita_seq,
        )
        if tipo == TipoVisita.INCIDENCIA and self._rng.random() < 0.70:
            visita.materiales_necesarios = {}
        elif self._rng.random() < 0.30 and self.M:
            mid = self._rng.choice(list(self.M.keys()))
            visita.materiales_necesarios = {mid: 1}
        enlazar_visita_matriz(
            self.D,
            self.COORDS,
            visita,
            factor_tiempo=p.factor_atasco_matriz,
        )
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
            f"Nueva visita: {visita.nombre} ({tipo.value}, {visita.duracion} min, "
            f"viaje est. {est_viaje:.0f} min)",
            None,
        )
        self._asignar_cola_pendiente()

    def _generar_cancelacion_visita(self):
        candidatas = [v for v in self.V if v.tipo != TipoVisita.ALMACEN]
        if not candidatas:
            return

        no_urgentes = [v for v in candidatas if not self._es_visita_urgente(v)]
        if no_urgentes and self._rng.random() < 0.75:
            candidatas = no_urgentes

        visita = self._rng.choice(candidatas)
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
            V_est, C_est = preprocesar(cola, self.C, self.M, self.J, self.D, modo="dinamico")
            if not C_est or not V_est:
                continue
            asignaciones = asignar_visitas(
                V_est, C_est, self.D, self.M_big, self.M, self.J, "dinamico"
            )
            if not asignaciones:
                continue
            asignaciones_ok = []
            for visita, c in asignaciones:
                leg = self.D.get(c.posicion, {}).get(visita.id, float("inf"))
                if c.tiempo_acumulado + leg + visita.duracion > self.J:
                    continue
                asignaciones_ok.append((visita, c))
            if asignaciones_ok:
                self._aplicar_asignaciones(asignaciones_ok, origen=origen)
                return

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

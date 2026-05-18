from __future__ import annotations

import copy
import random
from dataclasses import dataclass
from typing import Callable

from datos import actualizar_matriz_distancias, cargar_datos_instancia, id_almacen, _haversine_km
from modelos import EstadoCuadrilla, TipoVisita, Visita, consumir_materiales_cuadrilla
from postprocessing import postprocesar
from preprocessing import preprocesar
from model import asignar_visitas
from simulacion.metricas import IndicadoresCalidad


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

    def cargar_instancia(self, instancia_id: int, semilla: int | None = None):
        self.detener()
        self.instancia_id = instancia_id
        if semilla is not None:
            self._rng.seed(semilla)
        else:
            self._rng.seed(instancia_id * 7919)

        V, C, M, params, D, coords = cargar_datos_instancia(instancia_id)
        self.V = copy.deepcopy(V)
        self.C = copy.deepcopy(C)
        self.M = copy.deepcopy(M)
        self.D = copy.deepcopy(D)
        self.COORDS = copy.deepcopy(coords)
        self.J = params["J"]
        self.M_big = params["M_big"]
        self.almacen_id = params["almacen_id"]

        self._ajustar_stock_almacen()
        for c in self.C:
            c.posicion = self.almacen_id
            c.reset_dinamico()
            c.sim_progreso = 0.0
            c.sim_duracion_fase = 0.0
            c.sim_tiempo_fase = 0.0

        self.tiempo = 0.0
        self.finalizada = False
        self.eventos.clear()
        self.metricas.reset()
        self._visitas_iniciales = len(self.V)
        self.metricas.visitas_pendientes = len(self.V)
        self._log("sistema", f"Instancia {instancia_id} cargada · {len(self.V)} visitas · jornada {self.J} min")

    def _ajustar_stock_almacen(self):
        for c in self.C:
            for m_id, cant in c.materiales.items():
                mat = self.M.get(m_id)
                if mat:
                    mat.cantidad_disponible = max(0, mat.cantidad_disponible - cant)

    def iniciar(self):
        if self.instancia_id is None:
            return
        self.pausada = False
        self.activa = True
        self.finalizada = False
        self._ejecutar_asignacion()
        self._log("sistema", "Simulación iniciada — asignación inicial")
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

    def _finalizar_jornada(self):
        if self.finalizada:
            return
        self.tiempo = min(self.tiempo, float(self.J))
        self.metricas.tiempo_simulado = self.tiempo
        self.finalizada = True
        self.activa = False
        self.pausada = True
        for c in self.C:
            if c.estado != EstadoCuadrilla.INACTIVA:
                c.estado = EstadoCuadrilla.INACTIVA
            c.visita_actual = None
            c.sim_progreso = 0.0
            c.sim_tiempo_fase = 0.0
        self._log("sistema", f"Fin de jornada laboral ({self.J} min) — simulación pausada")

    def reiniciar(self):
        if self.instancia_id:
            self.cargar_instancia(self.instancia_id)

    def tick(self, dt_real: float = 0.05):
        if not self.activa or self.pausada or self.finalizada:
            return

        if self.tiempo >= self.J:
            self._finalizar_jornada()
            return

        dt = dt_real * self.velocidad
        dt_aplicado = min(dt, self.J - self.tiempo)
        if dt_aplicado <= 0:
            self._finalizar_jornada()
            return

        self.tiempo += dt_aplicado
        self.metricas.tiempo_simulado = self.tiempo

        self._avanzar_fases(dt_aplicado)

        if self.tiempo < self.J:
            self._eventos_aleatorios()

        if self.tiempo >= self.J:
            self._finalizar_jornada()
        elif self._todas_inactivas() and not self.V:
            self.finalizada = True
            self.activa = False
            self.pausada = True
            self._log("sistema", "Jornada finalizada — todas las cuadrillas inactivas")

        self.metricas.visitas_pendientes = len(self.V)

    def _todas_inactivas(self):
        return self.C and all(c.estado == EstadoCuadrilla.INACTIVA for c in self.C)

    def _eventos_aleatorios(self):
        if not self.jornada_activa():
            return
        if self._rng.random() < 0.002 * min(self.velocidad, 5):
            self._generar_visita_urgente()
        if self._rng.random() < 0.0015 * min(self.velocidad, 5) and self.M:
            self._entrada_material()

    def _generar_visita_urgente(self):
        if not self.COORDS:
            return
        tipos = [TipoVisita.TECNICA, TipoVisita.INCIDENCIA, TipoVisita.INSTALACION]
        tipo = self._rng.choice(tipos)
        lat, lon = self._rng.choice(list(self.COORDS.values()))
        lat += self._rng.uniform(-0.01, 0.01)
        lon += self._rng.uniform(-0.01, 0.01)
        self._next_visita_seq += 1
        visita = Visita(
            tipo=tipo,
            prioridad=self._rng.randint(6, 10),
            nombre=f"Urgente #{self._next_visita_seq}",
            latitud=lat,
            longitud=lon,
            id=self._next_visita_seq,
        )
        if self.M:
            mid = self._rng.choice(list(self.M.keys()))
            visita.materiales_necesarios = {mid: self._rng.randint(1, 2)}
        actualizar_matriz_distancias(self.D, self.COORDS, visita)
        self.V.append(visita)
        self.metricas.visitas_generadas += 1
        self.metricas.visitas_pendientes = len(self.V)
        self._log("visita_nueva", f"Nueva visita: {visita.nombre} ({tipo.value})", None)
        if any(c.estado == EstadoCuadrilla.LIBRE for c in self.C):
            self._ejecutar_asignacion()

    def _entrada_material(self):
        mid = self._rng.choice(list(self.M.keys()))
        cant = self._rng.randint(2, 8)
        self.M[mid].cantidad_disponible += cant
        nombre = self.M[mid].nombre
        self._log("stock", f"Entrada almacén: +{cant} × {nombre}")

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
        real = c.sim_duracion_fase
        est = c.tiempo_estimado_viaje
        origen = self.COORDS.get(c.posicion, self.COORDS.get(self.almacen_id))
        dest = self.COORDS[c.visita_actual.id]
        km = _haversine_km(origen[0], origen[1], dest[0], dest[1])
        self.metricas.registrar_viaje(est, real, km)
        c.completar_desplazamiento(real)
        c.sim_progreso = 0.0
        c.sim_tiempo_fase = 0.0
        est_trab = c.visita_actual.duracion
        c.sim_duracion_fase = est_trab * self._rng.uniform(0.88, 1.12)
        self._log(
            "llegada",
            f"C{c.id} llegó a {c.visita_actual.nombre} ({real:.1f} min, est. {est:.1f})",
            c.id,
        )

    def _completar_trabajo(self, c):
        real = c.sim_duracion_fase
        est = c.visita_actual.duracion
        self.metricas.registrar_trabajo(est, real)
        if c.visita_actual:
            consumir_materiales_cuadrilla(c, c.visita_actual)
        c.finalizar_trabajo(real, self.J)
        c.posicion = c.historial[-1][0].id if c.historial else self.almacen_id
        c.sim_progreso = 0.0
        c.sim_tiempo_fase = 0.0
        self.metricas.visitas_completadas += 1
        self._log(
            "fin_visita",
            f"C{c.id} finalizó {c.historial[-1][0].nombre} ({real:.1f} min)",
            c.id,
        )
        if self.V:
            self._ejecutar_asignacion()

    def _ejecutar_asignacion(self):
        if not self.jornada_activa():
            return
        V_est, C_est = preprocesar(self.V, self.C, self.M, self.J, self.D, modo="dinamico")
        if not C_est or not V_est:
            return
        asignaciones = asignar_visitas(
            V_est, C_est, self.D, self.M_big, self.M, self.J, "dinamico"
        )
        if not asignaciones:
            return
        self.V, self.C = postprocesar(asignaciones, self.V, self.C, self.M, self.D, True)
        for _, c in asignaciones:
            est = c.tiempo_estimado_viaje
            c.sim_duracion_fase = est * self._rng.uniform(0.82, 1.18)
            c.sim_tiempo_fase = 0.0
            c.sim_progreso = 0.0
        for v, c in asignaciones:
            self._log(
                "asignacion",
                f"Asignada {v.nombre} → Cuadrilla {c.id} (viaje est. {c.tiempo_estimado_viaje:.1f} min)",
                c.id,
                notify=False,
            )
        if asignaciones:
            self._notificar()

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

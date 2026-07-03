from __future__ import annotations

import random
import time
from dataclasses import dataclass, field

from model import _par_factible, asignar_visitas


@dataclass
class MedidorTiemposAsignacion:
    _tiempos_s: list[float] = field(default_factory=list)

    def reiniciar(self) -> None:
        self._tiempos_s.clear()

    def registrar(self, duracion_s: float) -> None:
        self._tiempos_s.append(duracion_s)

    def resumen(self) -> dict:
        if not self._tiempos_s:
            return {
                "resoluciones_asignacion": 0,
                "tiempo_asignacion_total_s": 0.0,
                "tiempo_asignacion_medio_ms": 0.0,
            }
        total = sum(self._tiempos_s)
        n = len(self._tiempos_s)
        return {
            "resoluciones_asignacion": n,
            "tiempo_asignacion_total_s": round(total, 4),
            "tiempo_asignacion_medio_ms": round(total / n * 1000.0, 2),
        }


medidor_tiempos_asignacion = MedidorTiemposAsignacion()

ESTRATEGIA_MILP = "milp"
ESTRATEGIA_CERCANA = "cercana"
ESTRATEGIA_ALEATORIA = "aleatoria"
ESTRATEGIA_PRIORIDAD = "prioridad"

ESTRATEGIAS_DISPONIBLES = (
    ESTRATEGIA_MILP,
    ESTRATEGIA_CERCANA,
    ESTRATEGIA_ALEATORIA,
    ESTRATEGIA_PRIORIDAD,
)

ETIQUETAS_ESTRATEGIA = {
    ESTRATEGIA_MILP: "MILP (propuesta)",
    ESTRATEGIA_CERCANA: "Cuadrilla mas cercana",
    ESTRATEGIA_ALEATORIA: "Asignacion aleatoria factible",
    ESTRATEGIA_PRIORIDAD: "Solo prioridad (sin distancia)",
}


def normalizar_estrategia(estrategia: str | None) -> str:
    if estrategia in ESTRATEGIAS_DISPONIBLES:
        return str(estrategia)
    return ESTRATEGIA_MILP


def etiqueta_estrategia(estrategia: str | None) -> str:
    key = normalizar_estrategia(estrategia)
    return ETIQUETAS_ESTRATEGIA.get(key, key)


def _viaje_estimado(cuadrilla, visita, D: dict) -> float:
    return D.get(cuadrilla.posicion, {}).get(visita.id, float("inf"))


def _asignar_cercana(V, C, D, materiales, J, modo):
    asignaciones: list[tuple] = []
    visitas_no_asignadas = list(V)
    for cuadrilla in sorted(C, key=lambda c: c.id):
        candidatas = [
            visita
            for visita in visitas_no_asignadas
            if _par_factible(visita, cuadrilla, D, J, modo, materiales)
        ]
        if not candidatas:
            continue
        visita = min(
            candidatas,
            key=lambda v: (
                _viaje_estimado(cuadrilla, v, D),
                -int(getattr(v, "prioridad", 0)),
                str(getattr(v, "nombre", "")),
                int(getattr(v, "id", 0)),
            ),
        )
        asignaciones.append((visita, cuadrilla))
        visitas_no_asignadas.remove(visita)
    return asignaciones


def _asignar_aleatoria(V, C, D, materiales, J, modo, rng: random.Random | None = None):
    rng_local = rng or random.Random(0)
    visitas = list(V)
    cuadrillas = list(C)
    rng_local.shuffle(visitas)
    cuadrillas_libres = set(cuadrillas)
    asignaciones: list[tuple] = []

    for visita in visitas:
        candidatas = [
            c
            for c in sorted(cuadrillas_libres, key=lambda x: x.id)
            if _par_factible(visita, c, D, J, modo, materiales)
        ]
        if not candidatas:
            continue
        elegida = rng_local.choice(candidatas)
        asignaciones.append((visita, elegida))
        cuadrillas_libres.remove(elegida)
        if not cuadrillas_libres:
            break
    return asignaciones


def _asignar_prioridad(V, C, D, materiales, J, modo):
    visitas_ordenadas = sorted(
        list(V),
        key=lambda v: (
            -int(getattr(v, "prioridad", 0)),
            str(getattr(v, "nombre", "")),
            int(getattr(v, "id", 0)),
        ),
    )
    cuadrillas_libres = list(sorted(C, key=lambda c: c.id))
    asignaciones: list[tuple] = []

    for visita in visitas_ordenadas:
        idx_factible = None
        for idx, cuadrilla in enumerate(cuadrillas_libres):
            if _par_factible(visita, cuadrilla, D, J, modo, materiales):
                idx_factible = idx
                break
        if idx_factible is None:
            continue
        cuadrilla = cuadrillas_libres.pop(idx_factible)
        asignaciones.append((visita, cuadrilla))
        if not cuadrillas_libres:
            break
    return asignaciones


def resolver_asignacion(
    V,
    C,
    D,
    F,
    materiales,
    J,
    modo,
    estrategia: str | None = None,
    rng: random.Random | None = None,
):
    t0 = time.perf_counter()
    try:
        estrategia_key = normalizar_estrategia(estrategia)
        if estrategia_key == ESTRATEGIA_MILP:
            return asignar_visitas(V, C, D, F)
        if estrategia_key == ESTRATEGIA_CERCANA:
            return _asignar_cercana(V, C, D, materiales, J, modo)
        if estrategia_key == ESTRATEGIA_ALEATORIA:
            return _asignar_aleatoria(V, C, D, materiales, J, modo, rng=rng)
        if estrategia_key == ESTRATEGIA_PRIORIDAD:
            return _asignar_prioridad(V, C, D, materiales, J, modo)
        return asignar_visitas(V, C, D, F)
    finally:
        medidor_tiempos_asignacion.registrar(time.perf_counter() - t0)

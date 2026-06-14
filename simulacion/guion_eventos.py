from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from datos import cargar_datos_instancia
from modelos import TipoVisita
from simulacion.config_instancia import (
    MADRID_CENTRO,
    MADRID_LAT_MAX,
    MADRID_LAT_MIN,
    MADRID_LON_MAX,
    MADRID_LON_MIN,
    coordenada_en_zona,
    perfil_simulacion,
)

PASO_MINUTOS_DEFECTO = 10.0
MAX_PASOS_DEFECTO = 5000
_SEMILLA_OFFSET_FACTORES = 500_009


@dataclass(frozen=True)
class EventoUrgenteGuion:
    paso: int
    tiempo: float
    tipo: TipoVisita
    prioridad: int
    latitud: float
    longitud: float
    materiales_necesarios: dict[int, int]
    numero_urgente: int


@dataclass(frozen=True)
class EventoCancelacionGuion:
    paso: int
    tiempo: float
    visita_id: int


@dataclass
class GuionEventos:
    instancia_id: int
    semilla: int
    paso_minutos: float
    urgentes: tuple[EventoUrgenteGuion, ...]
    cancelaciones: tuple[EventoCancelacionGuion, ...]
    _por_paso: dict[int, tuple[list[EventoUrgenteGuion], list[EventoCancelacionGuion]]] = field(
        repr=False, default_factory=dict, compare=False
    )

    def __post_init__(self):
        por_paso: dict[int, tuple[list[EventoUrgenteGuion], list[EventoCancelacionGuion]]] = {}
        for ev in self.urgentes:
            urg, canc = por_paso.get(ev.paso, ([], []))
            urg.append(ev)
            por_paso[ev.paso] = (urg, canc)
        for ev in self.cancelaciones:
            urg, canc = por_paso.get(ev.paso, ([], []))
            canc.append(ev)
            por_paso[ev.paso] = (urg, canc)
        object.__setattr__(self, "_por_paso", por_paso)

    def eventos_en_paso(
        self, paso: int
    ) -> tuple[list[EventoUrgenteGuion], list[EventoCancelacionGuion]]:
        return self._por_paso.get(paso, ([], []))


def semilla_factores(semilla: int) -> int:
    return int(semilla) + _SEMILLA_OFFSET_FACTORES


def _coords_visita_urgente(
    rng: random.Random,
    perfil,
    coords: dict,
    almacen_id: int,
) -> tuple[float, float]:
    amp = 0.006 + perfil.dispersion_visitas * 0.045
    modo = perfil.modo_coords_urgente

    if modo == "dispersa_madrid":
        return (
            rng.uniform(MADRID_LAT_MIN, MADRID_LAT_MAX),
            rng.uniform(MADRID_LON_MIN, MADRID_LON_MAX),
        )

    if modo == "periferia_madrid":
        clat, clon = MADRID_CENTRO
        ang = rng.uniform(0, 2 * math.pi)
        r = perfil.radio_urgente_grados + rng.uniform(0.05, 0.10)
        return (clat + r * math.cos(ang), clon + r * math.sin(ang) * 0.85)

    if modo == "cluster" and perfil.centro_urgente_lat is not None and perfil.centro_urgente_lon is not None:
        r = perfil.radio_urgente_grados
        return (
            perfil.centro_urgente_lat + rng.uniform(-r, r),
            perfil.centro_urgente_lon + rng.uniform(-r, r),
        )

    if modo == "cerca_almacen":
        base = coords.get(almacen_id) or next(iter(coords.values()), MADRID_CENTRO)
        return (
            base[0] + rng.uniform(-amp, amp),
            base[1] + rng.uniform(-amp, amp),
        )

    if modo == "zona_plan" and perfil.zona_urgente:
        candidatas = [
            c for c in coords.values()
            if coordenada_en_zona(c[0], c[1], perfil.zona_urgente)
        ]
        if candidatas:
            base_lat, base_lon = rng.choice(candidatas)
            r = perfil.radio_urgente_grados
            return (
                base_lat + rng.uniform(-r, r),
                base_lon + rng.uniform(-r, r),
            )

    base_lat, base_lon = rng.choice(list(coords.values()))
    return (
        base_lat + rng.uniform(-amp, amp),
        base_lon + rng.uniform(-amp, amp),
    )


def _especificar_urgente(
    rng: random.Random,
    perfil,
    coords: dict,
    materiales: dict,
    almacen_id: int,
    numero_urgente: int,
) -> EventoUrgenteGuion:
    tipos = [TipoVisita.TECNICA, TipoVisita.INCIDENCIA, TipoVisita.INSTALACION]
    tipo = rng.choices(
        tipos,
        weights=[perfil.peso_tecnica, perfil.peso_incidencia, perfil.peso_instalacion],
        k=1,
    )[0]
    lat, lon = _coords_visita_urgente(rng, perfil, coords, almacen_id)
    materiales_necesarios: dict[int, int] = {}
    if tipo == TipoVisita.INCIDENCIA and rng.random() < 0.70:
        materiales_necesarios = {}
    elif rng.random() < 0.30 and materiales:
        mid = rng.choice(list(materiales.keys()))
        materiales_necesarios = {mid: 1}
    return EventoUrgenteGuion(
        paso=0,
        tiempo=0.0,
        tipo=tipo,
        prioridad=rng.randint(6, 10),
        latitud=lat,
        longitud=lon,
        materiales_necesarios=materiales_necesarios,
        numero_urgente=numero_urgente,
    )


def generar_guion_eventos(
    instancia_id: int,
    semilla: int,
    paso_minutos: float = PASO_MINUTOS_DEFECTO,
    max_pasos: int = MAX_PASOS_DEFECTO,
) -> GuionEventos:
    V, _C, M, params, _D, coords, _K = cargar_datos_instancia(instancia_id)
    perfil = perfil_simulacion(instancia_id)
    jornada = params["J"]
    almacen_id = params["almacen_id"]

    visitas_cancelables = [
        v.id for v in V if v.tipo != TipoVisita.ALMACEN
    ]

    rng = random.Random(semilla)
    urgentes: list[EventoUrgenteGuion] = []
    cancelaciones: list[EventoCancelacionGuion] = []
    numero_urgente = 0

    for paso in range(max_pasos):
        tiempo = (paso + 1) * paso_minutos
        if tiempo > jornada:
            break

        prob = perfil.prob_visitas_por_minuto * paso_minutos
        if prob > 0 and rng.random() < prob:
            numero_urgente += 1
            spec = _especificar_urgente(
                rng, perfil, coords, M, almacen_id, numero_urgente
            )
            urgentes.append(
                EventoUrgenteGuion(
                    paso=paso,
                    tiempo=tiempo,
                    tipo=spec.tipo,
                    prioridad=spec.prioridad,
                    latitud=spec.latitud,
                    longitud=spec.longitud,
                    materiales_necesarios=dict(spec.materiales_necesarios),
                    numero_urgente=spec.numero_urgente,
                )
            )

        prob_cancelacion = perfil.prob_cancelaciones_por_minuto * paso_minutos
        if prob_cancelacion > 0 and rng.random() < prob_cancelacion and visitas_cancelables:
            visita_id = rng.choice(visitas_cancelables)
            visitas_cancelables.remove(visita_id)
            cancelaciones.append(
                EventoCancelacionGuion(paso=paso, tiempo=tiempo, visita_id=visita_id)
            )

    return GuionEventos(
        instancia_id=instancia_id,
        semilla=semilla,
        paso_minutos=paso_minutos,
        urgentes=tuple(urgentes),
        cancelaciones=tuple(cancelaciones),
    )

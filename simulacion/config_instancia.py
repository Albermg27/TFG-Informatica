from dataclasses import dataclass
from typing import Literal

from database.catalogo_visitas import (
    MADRID_CENTRO,
    MADRID_LAT_MAX,
    MADRID_LAT_MIN,
    MADRID_LON_MAX,
    MADRID_LON_MIN,
    CONFIG_VISITAS_INSTANCIA,
    ConfigVisitasInstancia,
    config_visitas_instancia,
    coordenada_en_zona,
)

ModoCoordsUrgente = Literal[
    "cerca_cliente",
    "dispersa_madrid",
    "cluster",
    "periferia_madrid",
    "zona_plan",
    "cerca_almacen",
]

__all__ = [
    "MADRID_CENTRO",
    "MADRID_LAT_MAX",
    "MADRID_LAT_MIN",
    "MADRID_LON_MAX",
    "MADRID_LON_MIN",
    "CONFIG_VISITAS_INSTANCIA",
    "ConfigVisitasInstancia",
    "config_visitas_instancia",
    "coordenada_en_zona",
    "PerfilSimulacionInstancia",
    "PERFILES_SIMULACION",
    "perfil_simulacion",
]


@dataclass(frozen=True)
class PerfilSimulacionInstancia:
    prob_visitas_por_minuto: float
    etiqueta_eventos: str
    descripcion: str
    prob_cancelaciones_por_minuto: float = 0.0007
    extra_stock_plan_pct: float = 0.15
    factor_viaje_min: float = 1.05
    factor_viaje_max: float = 1.25
    factor_trabajo_min: float = 1.03
    factor_trabajo_max: float = 1.18
    dispersion_visitas: float = 0.35
    peso_incidencia: float = 0.70
    peso_tecnica: float = 0.15
    peso_instalacion: float = 0.15
    modo_coords_urgente: ModoCoordsUrgente = "cerca_cliente"
    centro_urgente_lat: float | None = None
    centro_urgente_lon: float | None = None
    radio_urgente_grados: float = 0.012
    zona_urgente: str | None = None


PERFILES_SIMULACION: dict[int, PerfilSimulacionInstancia] = {
    1: PerfilSimulacionInstancia(
        0.0,
        "Referencia sin dinámica",
        "Solo plan inicial; visitas repartidas por Madrid; sin urgentes.",
        prob_cancelaciones_por_minuto=0.0004,
        extra_stock_plan_pct=0.12,
        factor_viaje_min=1.04,
        factor_viaje_max=1.14,
        factor_trabajo_min=1.02,
        factor_trabajo_max=1.10,
        dispersion_visitas=0.0,
        modo_coords_urgente="cerca_cliente",
    ),
    2: PerfilSimulacionInstancia(
        0.007,
        "Alta demanda concentrada",
        "Urgentes cerca del clúster centro; desvíos moderados en viaje y servicio.",
        prob_cancelaciones_por_minuto=0.0009,
        extra_stock_plan_pct=0.14,
        factor_viaje_min=1.06,
        factor_viaje_max=1.22,
        factor_trabajo_min=1.05,
        factor_trabajo_max=1.20,
        dispersion_visitas=0.12,
        modo_coords_urgente="cluster",
        centro_urgente_lat=40.4200,
        centro_urgente_lon=-3.7050,
        radio_urgente_grados=0.010,
    ),
    3: PerfilSimulacionInstancia(
        0.0018,
        "Zona norte",
        "Urgentes en el norte de Madrid; trayectos algo más largos.",
        prob_cancelaciones_por_minuto=0.0006,
        extra_stock_plan_pct=0.11,
        factor_viaje_min=1.05,
        factor_viaje_max=1.20,
        dispersion_visitas=0.35,
        modo_coords_urgente="zona_plan",
        zona_urgente="norte",
        radio_urgente_grados=0.018,
    ),
    4: PerfilSimulacionInstancia(
        0.0015,
        "Stock ajustado",
        "Pocas urgentes dispersas; el estrés viene del material planificado.",
        prob_cancelaciones_por_minuto=0.0010,
        extra_stock_plan_pct=0.05,
        factor_viaje_min=1.05,
        factor_viaje_max=1.18,
        dispersion_visitas=0.55,
        modo_coords_urgente="dispersa_madrid",
    ),
    5: PerfilSimulacionInstancia(
        0.0045,
        "Pico incidencias",
        "Urgentes incidencias repartidas por la ciudad; ritmo real más lento.",
        prob_cancelaciones_por_minuto=0.0008,
        extra_stock_plan_pct=0.16,
        factor_viaje_min=1.08,
        factor_viaje_max=1.28,
        factor_trabajo_min=1.08,
        factor_trabajo_max=1.25,
        dispersion_visitas=0.45,
        peso_incidencia=0.82,
        peso_tecnica=0.10,
        peso_instalacion=0.08,
        modo_coords_urgente="dispersa_madrid",
    ),
    6: PerfilSimulacionInstancia(
        0.0028,
        "Instalaciones",
        "Urgentes de instalación cerca de clientes del plan (zonas este/sur).",
        prob_cancelaciones_por_minuto=0.0012,
        extra_stock_plan_pct=0.17,
        factor_viaje_min=1.07,
        factor_viaje_max=1.26,
        factor_trabajo_min=1.10,
        factor_trabajo_max=1.30,
        dispersion_visitas=0.30,
        peso_incidencia=0.35,
        peso_tecnica=0.15,
        peso_instalacion=0.50,
        modo_coords_urgente="zona_plan",
        zona_urgente="este",
        radio_urgente_grados=0.022,
    ),
    7: PerfilSimulacionInstancia(
        0.0,
        "Jornada ligera",
        "Sin urgentes; pocas visitas dispersas; leve sobrecoste.",
        prob_cancelaciones_por_minuto=0.0003,
        extra_stock_plan_pct=0.10,
        factor_viaje_min=1.03,
        factor_viaje_max=1.12,
        factor_trabajo_min=1.02,
        factor_trabajo_max=1.08,
        dispersion_visitas=0.0,
        modo_coords_urgente="cerca_cliente",
    ),
    8: PerfilSimulacionInstancia(
        0.0032,
        "Periferia dispersa",
        "Urgentes en el anillo periférico de Madrid; viajes largos.",
        prob_cancelaciones_por_minuto=0.0007,
        extra_stock_plan_pct=0.13,
        factor_viaje_min=1.12,
        factor_viaje_max=1.38,
        factor_trabajo_min=1.05,
        factor_trabajo_max=1.22,
        dispersion_visitas=0.90,
        modo_coords_urgente="periferia_madrid",
        radio_urgente_grados=0.025,
    ),
    9: PerfilSimulacionInstancia(
        0.0095,
        "Saturación",
        "Muchas urgentes cerca del almacén logístico; cola y desvíos altos.",
        prob_cancelaciones_por_minuto=0.0014,
        extra_stock_plan_pct=0.16,
        factor_viaje_min=1.15,
        factor_viaje_max=1.42,
        factor_trabajo_min=1.10,
        factor_trabajo_max=1.32,
        dispersion_visitas=0.35,
        peso_incidencia=0.65,
        modo_coords_urgente="cerca_almacen",
        radio_urgente_grados=0.015,
    ),
    10: PerfilSimulacionInstancia(
        0.0038,
        "Balanceada realista",
        "Urgentes equilibradas en toda la ciudad; mix de tipos y dispersión media.",
        prob_cancelaciones_por_minuto=0.0008,
        extra_stock_plan_pct=0.15,
        factor_viaje_min=1.06,
        factor_viaje_max=1.24,
        factor_trabajo_min=1.05,
        factor_trabajo_max=1.20,
        dispersion_visitas=0.50,
        modo_coords_urgente="dispersa_madrid",
    ),
}

_PERFIL_DEFECTO = PerfilSimulacionInstancia(
    0.0025,
    "Por defecto",
    "Ritmo medio de urgentes y desvíos moderados.",
    prob_cancelaciones_por_minuto=0.0007,
    factor_viaje_min=1.06,
    factor_viaje_max=1.22,
    modo_coords_urgente="cerca_cliente",
)


def perfil_simulacion(instancia_id: int) -> PerfilSimulacionInstancia:
    return PERFILES_SIMULACION.get(instancia_id, _PERFIL_DEFECTO)

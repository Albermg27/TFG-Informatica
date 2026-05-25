from dataclasses import dataclass
from typing import Literal

ModoSeleccionVisitas = Literal[
    "dispersa",
    "concentrada",
    "zona",
    "tipo",
    "periferia",
    "saturacion",
    "ligera",
    "balanceada",
]

MADRID_LAT_MIN = 40.345
MADRID_LAT_MAX = 40.525
MADRID_LON_MIN = -3.855
MADRID_LON_MAX = -3.535
MADRID_CENTRO = (40.4168, -3.7038)


@dataclass(frozen=True)
class ConfigVisitasInstancia:
    modo: ModoSeleccionVisitas
    max_clientes: int
    zona: str | None = None
    centro_lat: float | None = None
    centro_lon: float | None = None
    radio_grados: float = 0.028
    tipo_predominante: str | None = None
    paso_disperso: int = 2


CONFIG_VISITAS_INSTANCIA: dict[int, ConfigVisitasInstancia] = {
    1: ConfigVisitasInstancia("dispersa", 28, paso_disperso=2),
    2: ConfigVisitasInstancia(
        "concentrada", 32, centro_lat=40.4200, centro_lon=-3.7050, radio_grados=0.020
    ),
    3: ConfigVisitasInstancia("zona", 26, zona="norte"),
    4: ConfigVisitasInstancia("dispersa", 22, paso_disperso=3),
    5: ConfigVisitasInstancia("tipo", 30, tipo_predominante="incidencia"),
    6: ConfigVisitasInstancia("tipo", 32, tipo_predominante="instalacion"),
    7: ConfigVisitasInstancia("ligera", 14),
    8: ConfigVisitasInstancia("periferia", 28),
    9: ConfigVisitasInstancia("saturacion", 44),
    10: ConfigVisitasInstancia("balanceada", 30),
}


def config_visitas_instancia(instancia_id: int) -> ConfigVisitasInstancia:
    return CONFIG_VISITAS_INSTANCIA.get(
        instancia_id,
        ConfigVisitasInstancia("dispersa", 24, paso_disperso=2),
    )


def coordenada_en_zona(lat: float, lon: float, zona: str) -> bool:
    if zona == "norte":
        return lat > 40.44
    if zona == "sur":
        return lat < 40.39
    if zona == "este":
        return lon > -3.66
    if zona == "oeste":
        return lon < -3.72
    if zona == "centro":
        return 40.39 <= lat <= 40.44 and -3.72 <= lon <= -3.66
    if zona == "periferia":
        clat, clon = MADRID_CENTRO
        return ((lat - clat) ** 2 + (lon - clon) ** 2) ** 0.5 > 0.055
    return True

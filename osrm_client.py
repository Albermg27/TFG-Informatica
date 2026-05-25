from __future__ import annotations

import threading
import time
from typing import Sequence

import requests

OSRM_TABLE_URL = (
    "http://router.project-osrm.org/table/v1/driving/{coords}?annotations=duration,distance"
)
INTERVALO_MINIMO_SEG = 1.2
TIMEOUT_SEG = 60
MAX_PUNTOS_TABLA = 100


class OSRMError(Exception):
    pass


class OSRMClient:

    def __init__(self, intervalo_min: float = INTERVALO_MINIMO_SEG):
        self._intervalo = max(0.0, float(intervalo_min))
        self._lock = threading.Lock()
        self._ultima_peticion = 0.0

    def _esperar_turno(self) -> None:
        with self._lock:
            ahora = time.monotonic()
            espera = self._intervalo - (ahora - self._ultima_peticion)
            if espera > 0:
                time.sleep(espera)
            self._ultima_peticion = time.monotonic()

    def _tabla_osrm_raw(
        self,
        puntos_lon_lat: Sequence[tuple[float, float]],
        *,
        contexto: str = "",
    ) -> tuple[list[list[float]], list[list[float]]]:
        n = len(puntos_lon_lat)
        if n == 0:
            return [], []
        if n > MAX_PUNTOS_TABLA:
            raise OSRMError(
                f"Demasiados puntos para una tabla OSRM ({n} > {MAX_PUNTOS_TABLA})"
                + (f" · {contexto}" if contexto else "")
            )

        coords = ";".join(f"{lon},{lat}" for lon, lat in puntos_lon_lat)
        url = OSRM_TABLE_URL.format(coords=coords)
        self._esperar_turno()

        try:
            r = requests.get(url, timeout=TIMEOUT_SEG)
            r.raise_for_status()
            data = r.json()
        except requests.RequestException as exc:
            msg = f"OSRM no disponible: {exc}"
            if contexto:
                msg = f"{msg} ({contexto})"
            raise OSRMError(msg) from exc
        except ValueError as exc:
            raise OSRMError(f"Respuesta OSRM inválida ({contexto})") from exc

        code = data.get("code")
        if code and code != "Ok":
            raise OSRMError(
                f"OSRM respondió con código '{code}'"
                + (f" · {contexto}" if contexto else "")
            )

        durations = data.get("durations")
        distances = data.get("distances")
        if not durations or len(durations) != n:
            raise OSRMError(
                f"Matriz de duraciones incompleta (esperados {n} filas)"
                + (f" · {contexto}" if contexto else "")
            )
        if not distances or len(distances) != n:
            raise OSRMError(
                f"Matriz de distancias incompleta (esperados {n} filas)"
                + (f" · {contexto}" if contexto else "")
            )

        for i, fila in enumerate(durations):
            if fila is None or len(fila) != n:
                raise OSRMError(
                    f"Fila {i} de duraciones inválida en OSRM"
                    + (f" · {contexto}" if contexto else "")
                )
            dist_fila = distances[i]
            if dist_fila is None or len(dist_fila) != n:
                raise OSRMError(
                    f"Fila {i} de distancias inválida en OSRM"
                    + (f" · {contexto}" if contexto else "")
                )
            for j, d in enumerate(fila):
                if d is None or dist_fila[j] is None:
                    raise OSRMError(
                        f"Sin ruta OSRM entre puntos {i} y {j}"
                        + (f" · {contexto}" if contexto else "")
                    )

        return durations, distances

    def tabla_duraciones_seg(
        self,
        puntos_lon_lat: Sequence[tuple[float, float]],
        *,
        contexto: str = "",
    ) -> list[list[float]]:
        durations, _ = self._tabla_osrm_raw(puntos_lon_lat, contexto=contexto)
        return durations

    def tabla_distancias_km(
        self,
        puntos_lon_lat: Sequence[tuple[float, float]],
        *,
        contexto: str = "",
    ) -> list[list[float]]:
        _, distances_m = self._tabla_osrm_raw(puntos_lon_lat, contexto=contexto)
        return [[round(m / 1000.0, 2) for m in fila] for fila in distances_m]

    def tabla_minutos(
        self,
        puntos_lon_lat: Sequence[tuple[float, float]],
        *,
        contexto: str = "",
    ) -> list[list[float]]:
        seg, _ = self._tabla_osrm_raw(puntos_lon_lat, contexto=contexto)
        return [[round(s / 60, 1) for s in fila] for fila in seg]

    def distancia_km(
        self,
        lon1: float,
        lat1: float,
        lon2: float,
        lat2: float,
        *,
        contexto: str = "par puntual",
    ) -> float:
        km = self.tabla_distancias_km([(lon1, lat1), (lon2, lat2)], contexto=contexto)
        return km[0][1]


_cliente_simulacion: OSRMClient | None = None


def cliente_osrm_simulacion() -> OSRMClient:
    global _cliente_simulacion
    if _cliente_simulacion is None:
        _cliente_simulacion = OSRMClient()
    return _cliente_simulacion


def reiniciar_cliente_osrm_simulacion() -> None:
    global _cliente_simulacion
    _cliente_simulacion = None

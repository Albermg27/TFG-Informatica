from modelos import Visita, Cuadrilla, Material, EstadoCuadrilla, TipoVisita
from database.session import SessionLocal
from database.models import VisitaDB, VisitaMaterialDB

from database.repository import (
    get_materiales_cuadrilla_db,
    get_materiales_db,
    get_visitas_db,
    get_cuadrillas_db
)

import copy

from database.constants import INSTANCIA_OPERATIVA_ID
from osrm_client import cliente_osrm_simulacion


def distancia_osrm_km(lat1: float, lon1: float, lat2: float, lon2: float, *, contexto: str = "") -> float:
    return cliente_osrm_simulacion().distancia_km(
        lon1, lat1, lon2, lat2, contexto=contexto or "distancia tramo"
    )


def id_almacen(visitas):
    for v in visitas:
        if v.tipo == TipoVisita.ALMACEN:
            return v.id
    return visitas[0].id if visitas else 1


def _matriz_desde_tabla_osrm(visitas, *, contexto: str) -> dict:
    if not visitas:
        return {}
    ids = [v.id for v in visitas]
    puntos = [(v.longitud, v.latitud) for v in visitas]
    mins = cliente_osrm_simulacion().tabla_minutos(puntos, contexto=contexto)
    D = {}
    for i, id_i in enumerate(ids):
        D[id_i] = {}
        for j, id_j in enumerate(ids):
            D[id_i][id_j] = mins[i][j]
    return D


def crear_matriz_distancias_osrm(visitas, *, contexto: str = "matriz instancia") -> dict:
    return _matriz_desde_tabla_osrm(visitas, contexto=contexto)


def matriz_km_osrm_desde_coords(coords: dict, *, contexto: str = "matriz km") -> dict:
    if not coords:
        return {}
    nodos = sorted(coords.keys())
    puntos = [(coords[n][1], coords[n][0]) for n in nodos]
    km = cliente_osrm_simulacion().tabla_distancias_km(puntos, contexto=contexto)
    K: dict = {}
    for i, id_i in enumerate(nodos):
        K[id_i] = {nodos[j]: km[i][j] for j in range(len(nodos))}
    return K


def crear_matriz_distancias(visitas, *, contexto: str = "planificación"):
    return crear_matriz_distancias_osrm(visitas, contexto=contexto)


def coords_desde_visitas(visitas):
    return {v.id: (v.latitud, v.longitud) for v in visitas}


def enlazar_visita_matriz(D, coords, visita, factor_tiempo: float = 1.0):
    nid = visita.id
    coords[nid] = (visita.latitud, visita.longitud)
    D[nid] = {}
    nodos = sorted(set(D.keys()) | set(coords.keys()))
    idx = {oid: i for i, oid in enumerate(nodos)}
    i_n = idx[nid]

    lon_lat = [(coords[oid][1], coords[oid][0]) for oid in nodos]
    mins = cliente_osrm_simulacion().tabla_minutos(
        lon_lat,
        contexto=f"visita id={nid}",
    )
    for oid in nodos:
        if oid == nid:
            D[nid][nid] = 0.0
            continue
        base = mins[i_n][idx[oid]]
        dur = round(base * factor_tiempo, 1)
        D[nid][oid] = dur
        if oid not in D:
            D[oid] = {}
        D[oid][nid] = dur
    return D


def actualizar_matriz_distancias(D, coords, nueva_visita, factor_tiempo: float = 1.0):
    return enlazar_visita_matriz(D, coords, nueva_visita, factor_tiempo=factor_tiempo)


_cache_matriz_instancia: dict[int, tuple[dict, dict, dict]] = {}


def limpiar_cache_matriz_instancia() -> None:
    _cache_matriz_instancia.clear()


def cargar_materiales(instancia_id: int = INSTANCIA_OPERATIVA_ID):
    materiales_db = get_materiales_db(instancia_id)

    materiales = {}
    for m in materiales_db:
        materiales[m.id] = Material(m.id, m.nombre, m.stock)

    return materiales


def cargar_cuadrillas(instancia_id: int = INSTANCIA_OPERATIVA_ID, almacen_id: int | None = None):
    cuadrillas_db = get_cuadrillas_db(instancia_id)

    C = []

    for cdb in cuadrillas_db:
        materiales = get_materiales_cuadrilla_db(instancia_id, cdb.id)

        mat_dict = {m.id: cm.cantidad for cm, m in materiales}

        c = Cuadrilla(
            id=cdb.id,
            estado=EstadoCuadrilla.LIBRE,
            materiales=mat_dict,
        )

        if almacen_id is not None:
            c.posicion = almacen_id
        c.tiempo_acumulado = 0

        C.append(c)

    return C


def cargar_visitas(instancia_id: int = INSTANCIA_OPERATIVA_ID):
    db = SessionLocal()

    visitas_db = (
        db.query(VisitaDB)
        .filter(VisitaDB.instancia_id == instancia_id)
        .order_by(VisitaDB.id)
        .all()
    )

    V0 = []

    for vdb in visitas_db:

        materiales = db.query(VisitaMaterialDB)\
            .filter(VisitaMaterialDB.visita_id == vdb.id)\
            .all()

        v = Visita(
            tipo=TipoVisita(vdb.tipo),
            prioridad=vdb.prioridad,
            nombre=vdb.nombre,
            latitud=vdb.latitud,
            longitud=vdb.longitud,
            id=vdb.id,
        )

        if vdb.duracion is not None:
            v.duracion = vdb.duracion

        v.materiales_necesarios = {
            m.material_id: m.cantidad for m in materiales
        }

        V0.append(v)

    db.close()
    return V0


def cargar_datos(instancia_id: int = INSTANCIA_OPERATIVA_ID):

    materiales = cargar_materiales(instancia_id)
    V0 = cargar_visitas(instancia_id)
    almacen_id = id_almacen(V0)
    C = cargar_cuadrillas(instancia_id, almacen_id)

    from database.repository import get_instancia_db

    inst = get_instancia_db(instancia_id)
    jornada = inst.jornada_minutos if inst else 1000

    params = {"J": jornada, "M_big": 1000, "instancia_id": instancia_id, "almacen_id": almacen_id}

    coords = coords_desde_visitas(V0)
    D = crear_matriz_distancias_osrm(
        V0, contexto=f"instancia {instancia_id} (carga operativa)"
    )
    K = matriz_km_osrm_desde_coords(
        coords, contexto=f"instancia {instancia_id} (km operativa)"
    )

    V = [v for v in V0 if v.id != almacen_id]

    return V, C, materiales, params, D, coords, K


def cargar_datos_instancia(instancia_id: int):
    if instancia_id in _cache_matriz_instancia:
        D_cached, coords_cached, K_cached = _cache_matriz_instancia[instancia_id]
        materiales = cargar_materiales(instancia_id)
        V0 = cargar_visitas(instancia_id)
        almacen_id = id_almacen(V0)
        C = cargar_cuadrillas(instancia_id, almacen_id)
        from database.repository import get_instancia_db

        inst = get_instancia_db(instancia_id)
        jornada = inst.jornada_minutos if inst else 1000
        params = {
            "J": jornada,
            "M_big": 1000,
            "instancia_id": instancia_id,
            "almacen_id": almacen_id,
        }
        V = [v for v in V0 if v.id != almacen_id]
        return (
            V,
            C,
            materiales,
            params,
            copy.deepcopy(D_cached),
            copy.deepcopy(coords_cached),
            copy.deepcopy(K_cached),
        )

    materiales = cargar_materiales(instancia_id)
    V0 = cargar_visitas(instancia_id)
    almacen_id = id_almacen(V0)
    C = cargar_cuadrillas(instancia_id, almacen_id)

    from database.repository import get_instancia_db

    inst = get_instancia_db(instancia_id)
    jornada = inst.jornada_minutos if inst else 1000

    params = {"J": jornada, "M_big": 1000, "instancia_id": instancia_id, "almacen_id": almacen_id}

    coords = coords_desde_visitas(V0)
    D = crear_matriz_distancias_osrm(
        V0, contexto=f"instancia {instancia_id} (carga inicial)"
    )
    K = matriz_km_osrm_desde_coords(
        coords, contexto=f"instancia {instancia_id} (km inicial)"
    )
    _cache_matriz_instancia[instancia_id] = (
        copy.deepcopy(D),
        copy.deepcopy(coords),
        copy.deepcopy(K),
    )

    V = [v for v in V0 if v.id != almacen_id]

    return V, C, materiales, params, D, coords, K

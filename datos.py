from modelos import Visita, Cuadrilla, Material, EstadoCuadrilla, TipoVisita
from database.session import SessionLocal
from database.models import VisitaDB, VisitaMaterialDB

from database.repository import (
    get_materiales_db,
    get_visitas_db,
    get_cuadrillas_db
)

import requests

def crear_matriz_distancias(visitas):
    coords = ";".join(f"{v.longitud},{v.latitud}" for v in visitas)
    url = f"http://router.project-osrm.org/table/v1/driving/{coords}?annotations=duration"
    
    D = {}
    try:
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()
        durations = data['durations']
        for i, row in enumerate(durations):
            D[i] = {}
            for j, dur in enumerate(row):
                D[i][j] = round(dur / 60, 1)
    except:
        print("Error al obtener la matriz de OSRM")
        for i in range(len(visitas)):
            D[i] = {j: float('inf') for j in range(len(visitas))}
    return D

def actualizar_matriz_distancias(D, visitas, nueva_visita):
    nuevo_idx = len(visitas) - 1

    D[nuevo_idx] = {}

    for i, v in enumerate(visitas):
        if v is nueva_visita:
            continue

        coords = f"{nueva_visita.longitud},{nueva_visita.latitud};{v.longitud},{v.latitud}"
        url = f"http://router.project-osrm.org/table/v1/driving/{coords}?annotations=duration"

        try:
            r = requests.get(url)
            data = r.json()
            dur = data["durations"][0][1] / 60

            D[nuevo_idx][i] = round(dur, 1)
            D[i][nuevo_idx] = round(dur, 1)

        except:
            D[nuevo_idx][i] = float("inf")
            D[i][nuevo_idx] = float("inf")

    return D

def cargar_materiales():
    materiales_db = get_materiales_db()

    materiales = {}
    for m in materiales_db:
        materiales[m.id] = Material(m.id, m.stock)

    return materiales

def cargar_cuadrillas():
    cuadrillas_db = get_cuadrillas_db()

    C = []
    for cdb in cuadrillas_db:
        c = Cuadrilla(cdb.id, EstadoCuadrilla.LIBRE)
        c.posicion = 0
        c.tiempo_acumulado = 0
        C.append(c)

    return C

def cargar_visitas():
    db = SessionLocal()

    visitas_db = db.query(VisitaDB).all()

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
            longitud=vdb.longitud
        )

        v.materiales_necesarios = {
            m.material_id: m.cantidad for m in materiales
        }

        V0.append(v)

    db.close()
    return V0

def cargar_datos():

    print("Cargando datos")

    materiales = cargar_materiales()
    C = cargar_cuadrillas()
    V0 = cargar_visitas()

    params = {
        "J": 1000,
        "M_big": 1000,
    }

    D = crear_matriz_distancias(V0)

    V = V0[1:]

    return V, C, materiales, params, D
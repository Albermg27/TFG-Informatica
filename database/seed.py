from sqlalchemy.orm import Session

from database.constants import INSTANCIA_OPERATIVA_ID
from modelos import TipoVisita
from .session import SessionLocal
from .models import (
    CuadrillaMaterialDB,
    InstanciaSimulacionDB,
    VisitaDB,
    MaterialDB,
    VisitaMaterialDB,
    CuadrillaDB,
)

visitas_base = [
    (TipoVisita.ALMACEN, 0, {}, "Almacén", 40.5409, -3.6420),
    (TipoVisita.INSTALACION, 10, {"Panel Solar": 6, "Batería": 2, "Estructura soporte": 1, "Conectores": 2}, "Cliente A", 40.4179, -3.7102),
    (TipoVisita.TECNICA, 5, {"Conectores": 1}, "Cliente B", 40.4225, -3.7128),
    (TipoVisita.INCIDENCIA, 9, {"Batería": 2, "Inversor": 1, "Conectores": 1}, "Cliente C", 40.4261, -3.7055),
    (TipoVisita.INSTALACION, 8, {"Panel Solar": 5, "Estructura soporte": 1, "Cable": 1}, "Cliente D", 40.4302, -3.6998),
    (TipoVisita.TECNICA, 4, {"Conectores": 1}, "Cliente E", 40.4339, -3.7067),
    (TipoVisita.INCIDENCIA, 10, {"Batería": 3, "Inversor": 1, "Conectores": 2}, "Cliente F", 40.4380, -3.7132),
    (TipoVisita.INSTALACION, 7, {"Panel Solar": 4, "Inversor": 1, "Cable": 1, "Cuadro eléctrico": 1}, "Cliente G", 40.4415, -3.7180),
    (TipoVisita.TECNICA, 3, {"Conectores": 1}, "Cliente H", 40.4448, -3.7109),
    (TipoVisita.INCIDENCIA, 6, {"Inversor": 2, "Conectores": 1}, "Cliente I", 40.4482, -3.7035),
    (TipoVisita.INSTALACION, 9, {"Panel Solar": 7, "Estructura soporte": 1, "Fusibles": 1}, "Cliente J", 40.4520, -3.6978),
    (TipoVisita.TECNICA, 6, {"Conectores": 1}, "Cliente K", 40.4561, -3.7089),
    (TipoVisita.INCIDENCIA, 8, {"Batería": 2, "Inversor": 1}, "Cliente L", 40.4590, -3.7155),
    (TipoVisita.INSTALACION, 9, {"Panel Solar": 5, "Cable": 2, "Cuadro eléctrico": 1}, "Cliente M", 40.4625, -3.7012),
    (TipoVisita.TECNICA, 4, {"Conectores": 1}, "Cliente N", 40.4658, -3.6945),
    (TipoVisita.INCIDENCIA, 7, {"Inversor": 2, "Conectores": 1}, "Cliente O", 40.4692, -3.7060),
    (TipoVisita.INSTALACION, 10, {"Panel Solar": 6, "Batería": 2, "Fusibles": 1}, "Cliente P", 40.4720, -3.7130),
    (TipoVisita.TECNICA, 5, {"Conectores": 1}, "Cliente Q", 40.4745, -3.7200),
    (TipoVisita.INCIDENCIA, 6, {"Batería": 3, "Inversor": 1}, "Cliente R", 40.4770, -3.7085),
    (TipoVisita.INSTALACION, 8, {"Panel Solar": 5, "Estructura soporte": 1, "Cuadro eléctrico": 1}, "Cliente S", 40.4795, -3.6990),
    (TipoVisita.TECNICA, 3, {"Conectores": 1}, "Cliente T", 40.4820, -3.7110),
    (TipoVisita.TECNICA, 5, {"Conectores": 1}, "Cliente U", 40.5450, -3.6350),
    (TipoVisita.INCIDENCIA, 8, {"Batería": 2, "Inversor": 1}, "Cliente V", 40.5475, -3.6600),
    (TipoVisita.INSTALACION, 9, {"Panel Solar": 7, "Cable": 2}, "Cliente W", 40.5500, -3.6355),
    (TipoVisita.TECNICA, 4, {"Conectores": 1}, "Cliente X", 40.5525, -3.6650),
    (TipoVisita.INCIDENCIA, 7, {"Inversor": 2, "Conectores": 1}, "Cliente Y", 40.5550, -3.6325),
    (TipoVisita.INSTALACION, 10, {"Panel Solar": 6, "Batería": 2, "Fusibles": 1}, "Cliente Z", 40.5575, -3.6675),
]

materiales_base = [
    ("Panel Solar", 35),
    ("Batería", 18),
    ("Inversor", 12),
    ("Cable", 20),
    ("Estructura soporte", 15),
    ("Conectores", 25),
    ("Fusibles", 10),
    ("Cuadro eléctrico", 14),
]

cuadrilla_materiales_base = {
    1: {"Panel Solar": 4, "Cable": 10, "Conectores": 15, "Fusibles": 5},
    2: {"Panel Solar": 6, "Estructura soporte": 4, "Cuadro eléctrico": 3, "Cable": 8},
    3: {"Batería": 5, "Inversor": 3, "Conectores": 10, "Cable": 6},
}

INSTANCIA_OPERATIVA_META = (
    "Dataset operativo",
    "Todas las visitas para planificación, dashboard y sistema dinámico.",
    1000,
    1.00,
)

INSTANCIAS_META = [
    ("Instancia 01 — Operativa base", "Escenario de referencia con carga media.", 1000, 1.00, 14),
    ("Instancia 02 — Alta demanda", "Más visitas urgentes y jornada extendida.", 1200, 0.95, 16),
    ("Instancia 03 — Zona norte", "Clientes desplazados al norte.", 1000, 1.02, 12),
    ("Instancia 04 — Stock reducido", "Menos material en almacén y cuadrillas.", 900, 0.85, 13),
    ("Instancia 05 — Pico incidencias", "Predominan averías e incidencias.", 1000, 1.00, 15),
    ("Instancia 06 — Instalaciones", "Muchas instalaciones grandes.", 1100, 0.98, 14),
    ("Instancia 07 — Ligera", "Pocas visitas, jornada corta.", 800, 1.05, 9),
    ("Instancia 08 — Periferia", "Coordenadas más dispersas.", 1000, 1.00, 13),
    ("Instancia 09 — Saturación", "Máxima carga de visitas.", 1300, 0.90, 18),
    ("Instancia 10 — Balanceada", "Mix equilibrado de tipos.", 1000, 1.00, 14),
]


def clasificar_duracion(tipo):
    if tipo is None:
        return 0
    if tipo.value == "instalacion":
        return 180
    if tipo.value == "tecnica":
        return 60
    if tipo.value == "incidencia":
        return 90
    return 0


def _visitas_completas():
    return [
        (tipo, prioridad, dict(mats), nombre, lat, lon)
        for tipo, prioridad, mats, nombre, lat, lon in visitas_base
    ]


def _visitas_para_instancia(idx: int, max_visitas: int):
    seleccion = visitas_base[: max_visitas + 1]
    lat_off = (idx - 5) * 0.003
    lon_off = (idx - 5) * 0.002
    resultado = []
    for tipo, prioridad, mats, nombre, lat, lon in seleccion:
        prio = prioridad
        if tipo == TipoVisita.INCIDENCIA and idx == 5:
            prio = min(10, prioridad + 1)
        if tipo == TipoVisita.INSTALACION and idx == 6:
            prio = min(10, prioridad + 1)
        resultado.append(
            (tipo, prio, dict(mats), nombre, lat + lat_off, lon + lon_off)
        )
    return resultado


def _stock_factor(idx: int, factor_global: float):
    if idx == 4:
        return factor_global * 0.65
    if idx == 9:
        return factor_global * 1.15
    return factor_global


def seed_instancia(db: Session, instancia_id: int, meta, completa: bool = False):
    if completa:
        nombre, descripcion, jornada, factor_stock = meta
    else:
        nombre, descripcion, jornada, factor_stock, max_visitas = meta

    db.add(
        InstanciaSimulacionDB(
            id=instancia_id,
            nombre=nombre,
            descripcion=descripcion,
            jornada_minutos=jornada,
        )
    )
    db.flush()

    material_map = {}
    f_stock = _stock_factor(instancia_id, factor_stock)
    for nom, stock in materiales_base:
        m = MaterialDB(
            instancia_id=instancia_id,
            nombre=nom,
            stock=max(1, int(stock * f_stock)),
        )
        db.add(m)
        db.flush()
        material_map[nom] = m.id

    visitas = _visitas_completas() if completa else _visitas_para_instancia(instancia_id, max_visitas)
    for tipo, prioridad, materiales_req, nom, lat, lon in visitas:
        visita = VisitaDB(
            instancia_id=instancia_id,
            tipo=None if tipo is None else tipo.value,
            prioridad=prioridad,
            nombre=nom,
            latitud=lat,
            longitud=lon,
            duracion=clasificar_duracion(tipo),
        )
        db.add(visita)
        db.flush()

        for nombre_mat, cantidad in materiales_req.items():
            db.add(
                VisitaMaterialDB(
                    visita_id=visita.id,
                    material_id=material_map[nombre_mat],
                    cantidad=cantidad,
                )
            )

    for cid, materiales in cuadrilla_materiales_base.items():
        factor_c = 0.75 if instancia_id == 4 else 1.0
        for nombre_mat, cantidad in materiales.items():
            db.add(
                CuadrillaMaterialDB(
                    instancia_id=instancia_id,
                    cuadrilla_id=cid,
                    material_id=material_map[nombre_mat],
                    cantidad=max(1, int(cantidad * factor_c)),
                )
            )
        db.add(
            CuadrillaDB(
                instancia_id=instancia_id,
                id=cid,
                nombre=f"Cuadrilla {cid}",
            )
        )


def seed():
    db: Session = SessionLocal()

    db.query(CuadrillaMaterialDB).delete()
    db.query(VisitaMaterialDB).delete()
    db.query(VisitaDB).delete()
    db.query(CuadrillaDB).delete()
    db.query(MaterialDB).delete()
    db.query(InstanciaSimulacionDB).delete()
    db.commit()

    print("Insertando dataset operativo (GUI)...")
    seed_instancia(db, INSTANCIA_OPERATIVA_ID, INSTANCIA_OPERATIVA_META, completa=True)
    print(f"  · Instancia {INSTANCIA_OPERATIVA_ID}: {INSTANCIA_OPERATIVA_META[0]}")

    print("Insertando 10 instancias de simulación...")
    for i, meta in enumerate(INSTANCIAS_META, start=1):
        seed_instancia(db, i, meta)
        print(f"  · Instancia {i}: {meta[0]}")

    db.commit()
    db.close()
    print("SEED COMPLETADO (1 operativa + 10 instancias de simulación)")


if __name__ == "__main__":
    seed()

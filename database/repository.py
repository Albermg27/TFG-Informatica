from database.constants import INSTANCIA_OPERATIVA_ID
from database.session import SessionLocal
from database.models import (
    CuadrillaMaterialDB,
    InstanciaSimulacionDB,
    MaterialDB,
    VisitaDB,
    CuadrillaDB,
    VisitaMaterialDB,
)


def get_instancias_db():
    db = SessionLocal()
    instancias = (
        db.query(InstanciaSimulacionDB)
        .filter(InstanciaSimulacionDB.id >= 1)
        .order_by(InstanciaSimulacionDB.id)
        .all()
    )
    db.close()
    return instancias


def get_instancia_db(instancia_id: int):
    db = SessionLocal()
    instancia = (
        db.query(InstanciaSimulacionDB)
        .filter(InstanciaSimulacionDB.id == instancia_id)
        .first()
    )
    db.close()
    return instancia


def get_materiales_db(instancia_id: int = INSTANCIA_OPERATIVA_ID):
    db = SessionLocal()
    materiales = (
        db.query(MaterialDB)
        .filter(MaterialDB.instancia_id == instancia_id)
        .order_by(MaterialDB.id)
        .all()
    )
    db.close()
    return materiales


def get_visitas_db(instancia_id: int = INSTANCIA_OPERATIVA_ID):
    db = SessionLocal()
    visitas = (
        db.query(VisitaDB)
        .filter(VisitaDB.instancia_id == instancia_id)
        .order_by(VisitaDB.id)
        .all()
    )
    db.close()
    return visitas


def get_cuadrillas_db(instancia_id: int = INSTANCIA_OPERATIVA_ID):
    db = SessionLocal()
    cuadrillas = (
        db.query(CuadrillaDB)
        .filter(CuadrillaDB.instancia_id == instancia_id)
        .order_by(CuadrillaDB.id)
        .all()
    )
    db.close()
    return cuadrillas


def get_materiales_visita_db(visita_id: int):
    db = SessionLocal()

    resultados = (
        db.query(VisitaMaterialDB, MaterialDB)
        .join(MaterialDB, VisitaMaterialDB.material_id == MaterialDB.id)
        .filter(VisitaMaterialDB.visita_id == visita_id)
        .all()
    )

    db.close()
    return resultados


def get_materiales_cuadrilla_db(instancia_id: int, cuadrilla_id: int):
    db = SessionLocal()

    resultados = (
        db.query(CuadrillaMaterialDB, MaterialDB)
        .join(MaterialDB, CuadrillaMaterialDB.material_id == MaterialDB.id)
        .filter(
            CuadrillaMaterialDB.instancia_id == instancia_id,
            CuadrillaMaterialDB.cuadrilla_id == cuadrilla_id,
        )
        .all()
    )

    db.close()
    return resultados

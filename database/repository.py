from database.session import SessionLocal
from database.models import CuadrillaMaterialDB, MaterialDB, VisitaDB, CuadrillaDB, VisitaMaterialDB

def get_materiales_db():
    db = SessionLocal()
    materiales = db.query(MaterialDB).all()
    db.close()
    return materiales

def get_visitas_db():
    db = SessionLocal()
    visitas = db.query(VisitaDB).all()
    db.close()
    return visitas

def get_cuadrillas_db():
    db = SessionLocal()
    cuadrillas = db.query(CuadrillaDB).all()
    db.close()
    return cuadrillas

def get_materiales_visita_db(visita_id: int):
    db = SessionLocal()
    
    resultados = (
        db.query(VisitaMaterialDB, MaterialDB)
        .join(MaterialDB, VisitaMaterialDB.material_id == MaterialDB.nombre)
        .filter(VisitaMaterialDB.visita_id == visita_id)
        .all()
    )
    
    db.close()
    return resultados

def get_materiales_cuadrilla_db(cuadrilla_id: int):
    db = SessionLocal()

    resultados = (
        db.query(CuadrillaMaterialDB, MaterialDB)
        .join(MaterialDB, CuadrillaMaterialDB.material_id == MaterialDB.id)
        .filter(CuadrillaMaterialDB.cuadrilla_id == cuadrilla_id)
        .all()
    )

    db.close()
    return resultados
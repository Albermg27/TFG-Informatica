from database.session import SessionLocal
from database.models import MaterialDB, VisitaDB, CuadrillaDB

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
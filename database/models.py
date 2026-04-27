from sqlalchemy import Column, Integer, String, Float
from .session import Base


class VisitaDB(Base):
    __tablename__ = "visitas"

    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String)
    prioridad = Column(Integer)
    nombre = Column(String)

    latitud = Column(Float)
    longitud = Column(Float)

    duracion = Column(Integer)

class MaterialDB(Base):
    __tablename__ = "materiales"

    id = Column(Integer, primary_key=True)
    stock = Column(Integer)

class VisitaMaterialDB(Base):
    __tablename__ = "visita_material"

    visita_id = Column(Integer, primary_key=True)
    material_id = Column(Integer, primary_key=True)
    cantidad = Column(Integer)

class CuadrillaDB(Base):
    __tablename__ = "cuadrillas"

    id = Column(Integer, primary_key=True)
    nombre = Column(String)
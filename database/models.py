from sqlalchemy import Column, Integer, String, Float, ForeignKey
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

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String, unique=True, nullable=False)
    stock = Column(Integer, nullable=False, default=0)

class VisitaMaterialDB(Base):
    __tablename__ = "visita_material"

    visita_id = Column(Integer, ForeignKey("visitas.id"), primary_key=True)
    material_id = Column(Integer, ForeignKey("materiales.id"), primary_key=True)
    cantidad = Column(Integer, nullable=False)

class CuadrillaDB(Base):
    __tablename__ = "cuadrillas"

    id = Column(Integer, primary_key=True)
    nombre = Column(String)

class CuadrillaMaterialDB(Base):
    __tablename__ = "cuadrilla_material"

    cuadrilla_id = Column(Integer, ForeignKey("cuadrillas.id"), primary_key=True)
    material_id = Column(Integer, ForeignKey("materiales.id"), primary_key=True)
    cantidad = Column(Integer, nullable=False)
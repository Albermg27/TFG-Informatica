from sqlalchemy.orm import Session

from modelos import TipoVisita
from .session import SessionLocal
from .models import VisitaDB, MaterialDB, VisitaMaterialDB, CuadrillaDB

visitas_data = [
        (TipoVisita.ALMACEN, 0, {}, "Almacén", 40.5409, -3.6420),

        (TipoVisita.INSTALACION, 10, {1:6, 2:2, 4:1, 6:2}, "Cliente A", 40.4179, -3.7102),
        (TipoVisita.TECNICA, 5, {6:1}, "Cliente B", 40.4225, -3.7128),
        (TipoVisita.INCIDENCIA, 9, {2:2, 3:1, 6:1}, "Cliente C", 40.4261, -3.7055),
        (TipoVisita.INSTALACION, 8, {1:5, 4:1, 5:1}, "Cliente D", 40.4302, -3.6998),
        (TipoVisita.TECNICA, 4, {6:1}, "Cliente E", 40.4339, -3.7067),
        (TipoVisita.INCIDENCIA, 10, {2:3, 3:1, 6:2}, "Cliente F", 40.4380, -3.7132),
        (TipoVisita.INSTALACION, 7, {1:4, 3:1, 5:1, 8:1}, "Cliente G", 40.4415, -3.7180),
        (TipoVisita.TECNICA, 3, {6:1}, "Cliente H", 40.4448, -3.7109),
        (TipoVisita.INCIDENCIA, 6, {3:2, 6:1}, "Cliente I", 40.4482, -3.7035),
        (TipoVisita.INSTALACION, 9, {1:7, 4:1, 7:1}, "Cliente J", 40.4520, -3.6978),
        (TipoVisita.TECNICA, 6, {6:1}, "Cliente K", 40.4561, -3.7089),
        (TipoVisita.INCIDENCIA, 8, {2:2, 3:1}, "Cliente L", 40.4590, -3.7155),
        (TipoVisita.INSTALACION, 9, {1:5, 5:2, 8:1}, "Cliente M", 40.4625, -3.7012),
        (TipoVisita.TECNICA, 4, {6:1}, "Cliente N", 40.4658, -3.6945),
        (TipoVisita.INCIDENCIA, 7, {3:2, 6:1}, "Cliente O", 40.4692, -3.7060),
        (TipoVisita.INSTALACION, 10, {1:6, 2:2, 7:1}, "Cliente P", 40.4720, -3.7130),
        (TipoVisita.TECNICA, 5, {6:1}, "Cliente Q", 40.4745, -3.7200),
        (TipoVisita.INCIDENCIA, 6, {2:3, 3:1}, "Cliente R", 40.4770, -3.7085),
        (TipoVisita.INSTALACION, 8, {1:5, 4:1, 8:1}, "Cliente S", 40.4795, -3.6990),
        (TipoVisita.TECNICA, 3, {6:1}, "Cliente T", 40.4820, -3.7110),
        (TipoVisita.TECNICA, 5, {6:1}, "Cliente U", 40.5450, -3.6350),
        (TipoVisita.INCIDENCIA, 8, {2:2, 3:1}, "Cliente V", 40.5475, -3.6600),
        (TipoVisita.INSTALACION, 9, {1:7, 5:2}, "Cliente W", 40.5500, -3.6355),
        (TipoVisita.TECNICA, 4, {6:1}, "Cliente X", 40.5525, -3.6650),
        (TipoVisita.INCIDENCIA, 7, {3:2, 6:1}, "Cliente Y", 40.5550, -3.6325),
        (TipoVisita.INSTALACION, 10, {1:6, 2:2, 7:1}, "Cliente Z", 40.5575, -3.6675),
    ]

cuadrillas_data = [
    (1, "Cuadrilla 1"),
    (2, "Cuadrilla 2"),
    (3, "Cuadrilla 3"),
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

def seed():
    db: Session = SessionLocal()

    db.query(VisitaMaterialDB).delete()
    db.query(VisitaDB).delete()
    db.query(CuadrillaDB).delete()
    db.query(MaterialDB).delete()

    db.commit()
    db: Session = SessionLocal()

    print("Insertando materiales...")

    materiales_data = {
        1: 35, 2: 18, 3: 12, 4: 20,
        5: 15, 6: 25, 7: 10, 8: 14
    }

    for mat_id, stock in materiales_data.items():
        db.add(MaterialDB(
            id=mat_id,
            stock=stock
        ))

    print("Insertando visitas...")

    visita_id = 1

    for tipo, prioridad, materiales_req, nombre, lat, lon in visitas_data:

        visita = VisitaDB(
            id=visita_id,
            tipo=None if tipo is None else tipo.value,
            prioridad=prioridad,
            nombre=nombre,
            latitud=lat,
            longitud=lon,
            duracion=clasificar_duracion(tipo)
        )

        db.add(visita)

        for material_id, cantidad in materiales_req.items():
            db.add(VisitaMaterialDB(
                visita_id=visita_id,
                material_id=material_id,
                cantidad=cantidad
            ))

        visita_id += 1    


    print("Insertando cuadrillas...")

    for cid, nombre in cuadrillas_data:
        db.add(CuadrillaDB(
            id=cid,
            nombre=nombre
        ))

    db.commit()
    db.close()
    print("SEED COMPLETADO")


if __name__ == "__main__":
    seed()
from sqlalchemy.orm import Session

from modelos import TipoVisita
from .session import SessionLocal
from .models import CuadrillaMaterialDB, VisitaDB, MaterialDB, VisitaMaterialDB, CuadrillaDB

visitas_data = [
    (TipoVisita.ALMACEN, 0, {}, "Almacén", 40.5409, -3.6420),

    (TipoVisita.INSTALACION, 10, {
        "Panel Solar": 6,
        "Batería": 2,
        "Estructura soporte": 1,
        "Conectores": 2
    }, "Cliente A", 40.4179, -3.7102),

    (TipoVisita.TECNICA, 5, {
        "Conectores": 1
    }, "Cliente B", 40.4225, -3.7128),

    (TipoVisita.INCIDENCIA, 9, {
        "Batería": 2,
        "Inversor": 1,
        "Conectores": 1
    }, "Cliente C", 40.4261, -3.7055),

    (TipoVisita.INSTALACION, 8, {
        "Panel Solar": 5,
        "Estructura soporte": 1,
        "Cable": 1
    }, "Cliente D", 40.4302, -3.6998),

    (TipoVisita.TECNICA, 4, {
        "Conectores": 1
    }, "Cliente E", 40.4339, -3.7067),

    (TipoVisita.INCIDENCIA, 10, {
        "Batería": 3,
        "Inversor": 1,
        "Conectores": 2
    }, "Cliente F", 40.4380, -3.7132),

    (TipoVisita.INSTALACION, 7, {
        "Panel Solar": 4,
        "Inversor": 1,
        "Cable": 1,
        "Cuadro eléctrico": 1
    }, "Cliente G", 40.4415, -3.7180),

    (TipoVisita.TECNICA, 3, {
        "Conectores": 1
    }, "Cliente H", 40.4448, -3.7109),

    (TipoVisita.INCIDENCIA, 6, {
        "Inversor": 2,
        "Conectores": 1
    }, "Cliente I", 40.4482, -3.7035),

    (TipoVisita.INSTALACION, 9, {
        "Panel Solar": 7,
        "Estructura soporte": 1,
        "Fusibles": 1
    }, "Cliente J", 40.4520, -3.6978),

    (TipoVisita.TECNICA, 6, {
        "Conectores": 1
    }, "Cliente K", 40.4561, -3.7089),

    (TipoVisita.INCIDENCIA, 8, {
        "Batería": 2,
        "Inversor": 1
    }, "Cliente L", 40.4590, -3.7155),

    (TipoVisita.INSTALACION, 9, {
        "Panel Solar": 5,
        "Cable": 2,
        "Cuadro eléctrico": 1
    }, "Cliente M", 40.4625, -3.7012),

    (TipoVisita.TECNICA, 4, {
        "Conectores": 1
    }, "Cliente N", 40.4658, -3.6945),

    (TipoVisita.INCIDENCIA, 7, {
        "Inversor": 2,
        "Conectores": 1
    }, "Cliente O", 40.4692, -3.7060),

    (TipoVisita.INSTALACION, 10, {
        "Panel Solar": 6,
        "Batería": 2,
        "Fusibles": 1
    }, "Cliente P", 40.4720, -3.7130),

    (TipoVisita.TECNICA, 5, {
        "Conectores": 1
    }, "Cliente Q", 40.4745, -3.7200),

    (TipoVisita.INCIDENCIA, 6, {
        "Batería": 3,
        "Inversor": 1
    }, "Cliente R", 40.4770, -3.7085),

    (TipoVisita.INSTALACION, 8, {
        "Panel Solar": 5,
        "Estructura soporte": 1,
        "Cuadro eléctrico": 1
    }, "Cliente S", 40.4795, -3.6990),

    (TipoVisita.TECNICA, 3, {
        "Conectores": 1
    }, "Cliente T", 40.4820, -3.7110),

    (TipoVisita.TECNICA, 5, {
        "Conectores": 1
    }, "Cliente U", 40.5450, -3.6350),

    (TipoVisita.INCIDENCIA, 8, {
        "Batería": 2,
        "Inversor": 1
    }, "Cliente V", 40.5475, -3.6600),

    (TipoVisita.INSTALACION, 9, {
        "Panel Solar": 7,
        "Cable": 2
    }, "Cliente W", 40.5500, -3.6355),

    (TipoVisita.TECNICA, 4, {
        "Conectores": 1
    }, "Cliente X", 40.5525, -3.6650),

    (TipoVisita.INCIDENCIA, 7, {
        "Inversor": 2,
        "Conectores": 1
    }, "Cliente Y", 40.5550, -3.6325),

    (TipoVisita.INSTALACION, 10, {
        "Panel Solar": 6,
        "Batería": 2,
        "Fusibles": 1
    }, "Cliente Z", 40.5575, -3.6675),
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

    materiales_data = [
        ("Panel Solar", 35),
        ("Batería", 18),
        ("Inversor", 12),
        ("Cable", 20),
        ("Estructura soporte", 15),
        ("Conectores", 25),
        ("Fusibles", 10),
        ("Cuadro eléctrico", 14)
    ]

    for nombre, stock in materiales_data:
        db.add(MaterialDB(
            nombre=nombre,
            stock=stock
        ))

    db.commit()

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

    material_map = {}
    for m in db.query(MaterialDB).all():
        material_map[m.nombre] = m.id

    cuadrilla_materiales = {
        1: {
            "Panel Solar": 4,
            "Cable": 10,
            "Conectores": 15,
            "Fusibles": 5
        },
        2: {
            "Panel Solar": 6,
            "Estructura soporte": 4,
            "Cuadro eléctrico": 3,
            "Cable": 8
        },
        3: {
            "Batería": 5,
            "Inversor": 3,
            "Conectores": 10,
            "Cable": 6
        }
    }

    print("Insertando materiales en cuadrillas...")

    material_map = {m.nombre: m.id for m in db.query(MaterialDB).all()}

    cuadrilla_materiales = {
        1: {
            "Panel Solar": 4,
            "Cable": 10,
            "Conectores": 15,
            "Fusibles": 5
        },
        2: {
            "Panel Solar": 6,
            "Estructura soporte": 4,
            "Cuadro eléctrico": 3,
            "Cable": 8
        },
        3: {
            "Batería": 5,
            "Inversor": 3,
            "Conectores": 10,
            "Cable": 6
        }
    }

    for cid, materiales in cuadrilla_materiales.items():
        for nombre, cantidad in materiales.items():

            db.add(CuadrillaMaterialDB(
                cuadrilla_id=cid,
                material_id=material_map[nombre],
                cantidad=cantidad
            ))

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
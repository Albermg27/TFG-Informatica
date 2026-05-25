from math import sqrt

from sqlalchemy.orm import Session

from database.constants import INSTANCIA_OPERATIVA_ID
from modelos import TipoVisita
from database.catalogo_visitas import (
    MADRID_CENTRO,
    ConfigVisitasInstancia,
    config_visitas_instancia,
    coordenada_en_zona,
)
from .session import SessionLocal
from .models import (
    CuadrillaMaterialDB,
    InstanciaSimulacionDB,
    VisitaDB,
    MaterialDB,
    VisitaMaterialDB,
    CuadrillaDB,
)


def _letra_visita(n: int) -> str:
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _aplicar_nombres_visitas(catalogo):
    resultado = []
    n_cliente = 0
    for tipo, prioridad, mats, _nombre, lat, lon, zona in catalogo:
        if tipo == TipoVisita.ALMACEN:
            nombre = "Almacén"
        else:
            n_cliente += 1
            nombre = f"Visita {_letra_visita(n_cliente)}"
        resultado.append((tipo, prioridad, mats, nombre, lat, lon, zona))
    return resultado


# (tipo, prioridad, materiales, _, lat, lon, zona) — el nombre se asigna al cargar
# Catálogo repartido por Madrid: centro, norte, sur, este, oeste y periferia.
_catalogo_datos = [
    (TipoVisita.ALMACEN, 0, {}, "Almacén Coslada", 40.4550, -3.5350, "este"),
    # —— Centro ——
    (TipoVisita.INSTALACION, 9, {"Panel Solar": 6, "Batería": 2, "Estructura soporte": 1}, "Sol — Gran Vía", 40.4200, -3.7050, "centro"),
    (TipoVisita.TECNICA, 5, {"Conectores": 1}, "Malasaña", 40.4265, -3.7040, "centro"),
    (TipoVisita.INCIDENCIA, 8, {"Inversor": 1, "Conectores": 1}, "Chueca", 40.4220, -3.6980, "centro"),
    (TipoVisita.INSTALACION, 7, {"Panel Solar": 4, "Cable": 2}, "Lavapiés", 40.4085, -3.7020, "centro"),
    (TipoVisita.TECNICA, 4, {"Conectores": 1}, "Ópera", 40.4180, -3.7110, "centro"),
    (TipoVisita.INCIDENCIA, 9, {"Batería": 2, "Inversor": 1}, "Atocha", 40.4060, -3.6890, "centro"),
    (TipoVisita.INSTALACION, 8, {"Panel Solar": 5, "Cuadro eléctrico": 1}, "Justicia", 40.4150, -3.6950, "centro"),
    (TipoVisita.TECNICA, 6, {"Conectores": 1}, "Salesas", 40.4240, -3.6920, "centro"),
    # —— Norte ——
    (TipoVisita.INSTALACION, 10, {"Panel Solar": 7, "Batería": 2, "Fusibles": 1}, "Chamartín", 40.4620, -3.6820, "norte"),
    (TipoVisita.INCIDENCIA, 7, {"Inversor": 2, "Conectores": 1}, "Tetuán", 40.4660, -3.7020, "norte"),
    (TipoVisita.TECNICA, 5, {"Conectores": 1}, "Cuatro Caminos", 40.4490, -3.7080, "norte"),
    (TipoVisita.INSTALACION, 8, {"Panel Solar": 5, "Estructura soporte": 1}, "Nuevos Ministerios", 40.4455, -3.6920, "norte"),
    (TipoVisita.INCIDENCIA, 6, {"Batería": 3, "Inversor": 1}, "Fuencarral N.", 40.4920, -3.7080, "norte"),
    (TipoVisita.TECNICA, 4, {"Conectores": 1}, "Hortaleza", 40.4750, -3.6420, "norte"),
    (TipoVisita.INSTALACION, 9, {"Panel Solar": 6, "Cable": 2}, "Pío XII", 40.4580, -3.6750, "norte"),
    (TipoVisita.INCIDENCIA, 8, {"Inversor": 1, "Conectores": 2}, "Plaza Castilla", 40.4665, -3.6890, "norte"),
    (TipoVisita.INSTALACION, 7, {"Panel Solar": 4, "Batería": 1}, "Mirasierra", 40.4880, -3.7180, "norte"),
    (TipoVisita.TECNICA, 5, {"Conectores": 1}, "Valdeacederas", 40.4780, -3.6950, "norte"),
    (TipoVisita.INSTALACION, 8, {"Panel Solar": 5, "Cable": 1}, "Bellas Vistas", 40.4520, -3.7150, "norte"),
    (TipoVisita.INCIDENCIA, 7, {"Batería": 2, "Inversor": 1}, "Valverde", 40.4700, -3.6850, "norte"),
    (TipoVisita.TECNICA, 4, {"Conectores": 1}, "La Paz", 40.4560, -3.6780, "norte"),
    (TipoVisita.INSTALACION, 9, {"Panel Solar": 6, "Fusibles": 1}, "Colombia", 40.4640, -3.6680, "norte"),
    (TipoVisita.INCIDENCIA, 6, {"Inversor": 1, "Conectores": 2}, "Conde Casal", 40.4380, -3.6680, "norte"),
    (TipoVisita.INSTALACION, 7, {"Panel Solar": 4, "Batería": 1}, "Prosperidad", 40.4440, -3.6580, "norte"),
    (TipoVisita.TECNICA, 5, {"Conectores": 1}, "Simancas", 40.4520, -3.6480, "norte"),
    (TipoVisita.INCIDENCIA, 8, {"Batería": 2}, "Quintana", 40.4380, -3.6380, "norte"),
    (TipoVisita.INSTALACION, 10, {"Panel Solar": 7, "Cuadro eléctrico": 1}, "Pinar del Rey", 40.4620, -3.6480, "norte"),
    # —— Sur ——
    (TipoVisita.INSTALACION, 9, {"Panel Solar": 6, "Estructura soporte": 1, "Cable": 1}, "Usera", 40.3850, -3.7080, "sur"),
    (TipoVisita.INCIDENCIA, 10, {"Batería": 2, "Inversor": 1, "Conectores": 1}, "Carabanchel", 40.3780, -3.7380, "sur"),
    (TipoVisita.TECNICA, 4, {"Conectores": 1}, "Villaverde Alto", 40.3520, -3.7120, "sur"),
    (TipoVisita.INSTALACION, 8, {"Panel Solar": 5, "Fusibles": 1}, "Puente Vallecas", 40.3920, -3.6580, "sur"),
    (TipoVisita.INCIDENCIA, 7, {"Inversor": 2}, "Arganzuela", 40.3980, -3.7180, "sur"),
    (TipoVisita.TECNICA, 6, {"Conectores": 1}, "Legazpi", 40.3910, -3.6920, "sur"),
    (TipoVisita.INSTALACION, 10, {"Panel Solar": 7, "Batería": 2, "Cuadro eléctrico": 1}, "Delicias", 40.4020, -3.6950, "sur"),
    (TipoVisita.INCIDENCIA, 6, {"Batería": 2, "Conectores": 1}, "Orcasitas", 40.3680, -3.7280, "sur"),
    (TipoVisita.INSTALACION, 7, {"Panel Solar": 4, "Cable": 2}, "Butarque", 40.3620, -3.7450, "sur"),
    (TipoVisita.TECNICA, 5, {"Conectores": 1}, "San Fermín", 40.3750, -3.6980, "sur"),
    # —— Este ——
    (TipoVisita.INSTALACION, 8, {"Panel Solar": 5, "Inversor": 1}, "Retiro", 40.4080, -3.6820, "este"),
    (TipoVisita.INCIDENCIA, 9, {"Batería": 2, "Inversor": 1}, "Pacífico", 40.4020, -3.6720, "este"),
    (TipoVisita.TECNICA, 4, {"Conectores": 1}, "Adelfas", 40.4050, -3.6680, "este"),
    (TipoVisita.INSTALACION, 9, {"Panel Solar": 6, "Cable": 2}, "Moratalaz", 40.4080, -3.6420, "este"),
    (TipoVisita.INCIDENCIA, 7, {"Inversor": 2, "Conectores": 1}, "Ciudad Lineal", 40.4480, -3.6480, "este"),
    (TipoVisita.TECNICA, 5, {"Conectores": 1}, "Ventas", 40.4280, -3.6620, "este"),
    (TipoVisita.INSTALACION, 10, {"Panel Solar": 7, "Batería": 2}, "Vicálvaro", 40.4020, -3.6080, "este"),
    (TipoVisita.INCIDENCIA, 8, {"Batería": 3, "Inversor": 1}, "San Blas", 40.4320, -3.6150, "este"),
    (TipoVisita.INSTALACION, 7, {"Panel Solar": 4, "Estructura soporte": 1}, "Canillejas", 40.4400, -3.6250, "este"),
    (TipoVisita.TECNICA, 6, {"Conectores": 1}, "El Cañaveral", 40.3920, -3.5850, "este"),
    # —— Oeste ——
    (TipoVisita.INSTALACION, 9, {"Panel Solar": 6, "Cuadro eléctrico": 1}, "Moncloa", 40.4350, -3.7180, "oeste"),
    (TipoVisita.INCIDENCIA, 8, {"Inversor": 1, "Conectores": 2}, "Argüelles", 40.4280, -3.7280, "oeste"),
    (TipoVisita.TECNICA, 5, {"Conectores": 1}, "Ciudad Universitaria", 40.4420, -3.7280, "oeste"),
    (TipoVisita.INSTALACION, 7, {"Panel Solar": 5, "Cable": 1}, "Latina — Aluche", 40.3880, -3.7620, "oeste"),
    (TipoVisita.INCIDENCIA, 6, {"Batería": 2, "Inversor": 1}, "Casa de Campo", 40.4180, -3.7520, "oeste"),
    (TipoVisita.TECNICA, 4, {"Conectores": 1}, "Príncipe Pío", 40.4200, -3.7180, "oeste"),
    (TipoVisita.INSTALACION, 8, {"Panel Solar": 5, "Fusibles": 1}, "Cuatro Vientos", 40.3780, -3.7780, "oeste"),
    (TipoVisita.INCIDENCIA, 9, {"Batería": 2, "Conectores": 1}, "Carabanchel Alto", 40.3720, -3.7520, "oeste"),
    (TipoVisita.INSTALACION, 10, {"Panel Solar": 6, "Batería": 2}, "Los Cármenes", 40.3960, -3.7420, "oeste"),
    (TipoVisita.TECNICA, 5, {"Conectores": 1}, "Lucero", 40.4020, -3.7680, "oeste"),
    # —— Periferia (anillo exterior) ——
    (TipoVisita.INSTALACION, 9, {"Panel Solar": 7, "Cable": 2}, "Barajas", 40.4720, -3.5680, "periferia"),
    (TipoVisita.INCIDENCIA, 8, {"Inversor": 2, "Conectores": 1}, "Aeropuerto T4", 40.4910, -3.5730, "periferia"),
    (TipoVisita.TECNICA, 5, {"Conectores": 1}, "Vallecas Villa", 40.3820, -3.6180, "periferia"),
    (TipoVisita.INSTALACION, 10, {"Panel Solar": 6, "Batería": 2, "Fusibles": 1}, "Ensanche Vallecas", 40.3880, -3.6020, "periferia"),
    (TipoVisita.INCIDENCIA, 7, {"Batería": 3, "Inversor": 1}, "Villa de Vallecas", 40.3680, -3.6280, "periferia"),
    (TipoVisita.INSTALACION, 8, {"Panel Solar": 5, "Estructura soporte": 1}, "Fuencarral S.", 40.4980, -3.7280, "periferia"),
    (TipoVisita.TECNICA, 4, {"Conectores": 1}, "Peñagrande", 40.4780, -3.7380, "periferia"),
    (TipoVisita.INCIDENCIA, 9, {"Inversor": 2}, "Villaverde Bajo", 40.3480, -3.6980, "periferia"),
    (TipoVisita.INSTALACION, 7, {"Panel Solar": 4, "Cable": 2}, "Getafe límite", 40.3480, -3.7380, "periferia"),
    (TipoVisita.TECNICA, 6, {"Conectores": 1}, "Las Rozas límite", 40.5180, -3.7980, "periferia"),
]

visitas_base = _aplicar_nombres_visitas(_catalogo_datos)

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
    ("Instancia 01 — Dispersa Madrid", "Visitas repartidas por toda la ciudad.", 1000, 1.00, 28),
    ("Instancia 02 — Clúster centro", "Clientes concentrados en el centro.", 1200, 0.95, 32),
    ("Instancia 03 — Zona norte", "Solo clientes al norte de Madrid.", 1000, 1.02, 26),
    ("Instancia 04 — Stock reducido", "Menos visitas dispersas y menos material.", 900, 0.85, 22),
    ("Instancia 05 — Pico incidencias", "Mayoría incidencias repartidas.", 1000, 1.00, 30),
    ("Instancia 06 — Instalaciones", "Predominan instalaciones grandes.", 1100, 0.98, 32),
    ("Instancia 07 — Ligera", "Pocas visitas, jornada corta.", 800, 1.05, 14),
    ("Instancia 08 — Periferia", "Clientes en el anillo exterior.", 1000, 1.00, 28),
    ("Instancia 09 — Saturación", "Casi todo el catálogo de clientes.", 1300, 0.90, 44),
    ("Instancia 10 — Balanceada", "Mix equilibrado por zonas y tipos.", 1000, 1.00, 30),
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


def _dist_grados(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    return sqrt((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2)


def _clientes_catalogo():
    return list(visitas_base[1:])


def _tupla_visita_sin_zona(entry):
    tipo, prioridad, mats, nombre, lat, lon, _zona = entry
    return (tipo, prioridad, mats, nombre, lat, lon)


def _indices_seleccion(cfg: ConfigVisitasInstancia) -> list[int]:
    clientes = _clientes_catalogo()
    n = len(clientes)
    max_c = min(cfg.max_clientes, n)

    if cfg.modo == "saturacion":
        return list(range(1, max_c + 1))

    if cfg.modo == "ligera":
        paso = max(2, n // max_c)
        return [1 + i * paso for i in range(max_c) if 1 + i * paso <= n]

    if cfg.modo == "dispersa":
        paso = max(1, cfg.paso_disperso)
        idxs = list(range(0, n, paso))[:max_c]
        return [i + 1 for i in idxs]

    if cfg.modo == "zona" and cfg.zona:
        idxs = [i + 1 for i, v in enumerate(clientes) if v[6] == cfg.zona]
        if len(idxs) < max_c:
            vistos = set(idxs)
            for i, v in enumerate(clientes):
                idx = i + 1
                if idx not in vistos and coordenada_en_zona(v[4], v[5], cfg.zona):
                    idxs.append(idx)
                    vistos.add(idx)
                if len(idxs) >= max_c:
                    break
        return idxs[:max_c]

    if cfg.modo == "tipo" and cfg.tipo_predominante:
        tipo_obj = {
            "incidencia": TipoVisita.INCIDENCIA,
            "instalacion": TipoVisita.INSTALACION,
            "tecnica": TipoVisita.TECNICA,
        }.get(cfg.tipo_predominante)
        idxs = [i + 1 for i, v in enumerate(clientes) if v[0] == tipo_obj]
        if len(idxs) < max_c:
            resto = [i + 1 for i, v in enumerate(clientes) if v[0] != tipo_obj]
            idxs = idxs + resto[: max_c - len(idxs)]
        return idxs[:max_c]

    if cfg.modo == "concentrada":
        clat = cfg.centro_lat if cfg.centro_lat is not None else MADRID_CENTRO[0]
        clon = cfg.centro_lon if cfg.centro_lon is not None else MADRID_CENTRO[1]
        orden = sorted(
            range(n),
            key=lambda i: _dist_grados(clientes[i][4], clientes[i][5], clat, clon),
        )
        return [i + 1 for i in orden[:max_c]]

    if cfg.modo == "periferia":
        clat, clon = MADRID_CENTRO
        orden = sorted(
            range(n),
            key=lambda i: -_dist_grados(clientes[i][4], clientes[i][5], clat, clon),
        )
        preferidos = [i + 1 for i in orden if clientes[i][6] == "periferia"]
        if len(preferidos) >= max_c:
            return preferidos[:max_c]
        vistos = set(preferidos)
        for i in orden:
            idx = i + 1
            if idx not in vistos:
                preferidos.append(idx)
                vistos.add(idx)
            if len(preferidos) >= max_c:
                break
        return preferidos[:max_c]

    if cfg.modo == "balanceada":
        zonas = ("centro", "norte", "sur", "este", "oeste", "periferia")
        por_zona: dict[str, list[int]] = {z: [] for z in zonas}
        for i, v in enumerate(clientes):
            por_zona.setdefault(v[6], []).append(i + 1)
        cuota = max(1, max_c // len(zonas))
        seleccion: list[int] = []
        for z in zonas:
            seleccion.extend(por_zona.get(z, [])[:cuota])
        if len(seleccion) < max_c:
            restantes = [i + 1 for i in range(n) if (i + 1) not in seleccion]
            seleccion.extend(restantes[: max_c - len(seleccion)])
        return seleccion[:max_c]

    return list(range(1, max_c + 1))


def _visitas_completas():
    return [_tupla_visita_sin_zona(v) for v in visitas_base]


def _visitas_para_instancia(instancia_id: int):
    cfg = config_visitas_instancia(instancia_id)
    indices = _indices_seleccion(cfg)
    almacen = _tupla_visita_sin_zona(visitas_base[0])
    resultado = [almacen]
    clientes = _clientes_catalogo()
    for idx in indices:
        if 1 <= idx <= len(clientes):
            entry = clientes[idx - 1]
            tipo, prioridad, mats, nombre, lat, lon, _z = entry
            prio = prioridad
            if instancia_id == 5 and tipo == TipoVisita.INCIDENCIA:
                prio = min(10, prioridad + 1)
            if instancia_id == 6 and tipo == TipoVisita.INSTALACION:
                prio = min(10, prioridad + 1)
            resultado.append((tipo, prio, dict(mats), nombre, lat, lon))
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
        nombre, descripcion, jornada, factor_stock, _max_visitas = meta

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

    visitas = _visitas_completas() if completa else _visitas_para_instancia(instancia_id)
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
        n = len(_visitas_para_instancia(i))
        print(f"  · Instancia {i}: {meta[0]} ({n} visitas)")

    db.commit()
    db.close()
    print("SEED COMPLETADO (1 operativa + 10 instancias de simulación)")


if __name__ == "__main__":
    seed()

from __future__ import annotations

from modelos import Visita


def consolidar_stock_cuadrillas_en_almacen(cuadrillas, catalogo_materiales) -> None:
    for c in cuadrillas:
        for m_id, cant in list(c.materiales.items()):
            mat = catalogo_materiales.get(m_id)
            if mat is not None:
                mat.cantidad_disponible += cant
        c.materiales = {}


def calcular_stock_desde_plan(
    visitas_por_cuadrilla: dict[int, list[Visita]],
    buffer_pct: float = 0.15,
) -> dict[int, dict[int, int]]:
    stock: dict[int, dict[int, int]] = {}
    factor = 1.0 + max(0.0, buffer_pct)
    for cid, visitas in visitas_por_cuadrilla.items():
        necesidades: dict[int, int] = {}
        for visita in visitas:
            for m_id, cant in visita.materiales_necesarios.items():
                necesidades[m_id] = necesidades.get(m_id, 0) + cant
        stock[cid] = {
            m_id: max(1, int(cant * factor)) if cant > 0 else 0
            for m_id, cant in necesidades.items()
        }
    return stock


def aplicar_stock_inicial_cuadrillas(
    cuadrillas,
    stock_por_cuadrilla: dict[int, dict[int, int]],
    catalogo_materiales,
) -> None:
    consolidar_stock_cuadrillas_en_almacen(cuadrillas, catalogo_materiales)
    for c in cuadrillas:
        c.materiales = dict(stock_por_cuadrilla.get(c.id, {}))
        for m_id, cant in c.materiales.items():
            mat = catalogo_materiales.get(m_id)
            if mat is not None:
                mat.cantidad_disponible = max(0, mat.cantidad_disponible - cant)

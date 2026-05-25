from __future__ import annotations

import copy
from dataclasses import dataclass

from datos import cargar_datos_instancia
from model import asignar_visitas
from modelos import EstadoCuadrilla, Visita
from preprocessing import preprocesar
from simulacion.config_instancia import perfil_simulacion
from simulacion.inventario import (
    aplicar_stock_inicial_cuadrillas,
    calcular_stock_desde_plan,
    consolidar_stock_cuadrillas_en_almacen,
)


@dataclass
class ResultadoPlanEstatico:
    metricas: dict
    rutas: dict[int, list[str]]
    visitas_por_cuadrilla: dict[int, list[Visita]]
    stock_inicial: dict[int, dict[int, int]]
    primera_oleada: list[tuple[int, int]]


def _metricas_desde_plan(
    visitas_completadas: int,
    visitas_pendientes: int,
    distancia_km: float,
    J: int,
    rutas: dict[int, list[str]],
    stock_inicial: dict[int, dict[int, int]],
    tiempos_cuadrillas: dict[int, float],
    cronologia_cuadrillas: dict[int, list[dict]],
    pendientes_nombres: list[str],
) -> dict:
    return {
        "jornada_minutos": J,
        "distancia_total_km": round(distancia_km, 2),
        "visitas_completadas": visitas_completadas,
        "visitas_pendientes": visitas_pendientes,
        "pendientes_nombres": pendientes_nombres,
        "visitas_generadas": 0,
        "visitas_canceladas": 0,
        "canceladas_nombres": [],
        "eventos_totales": 0,
        "tiempos_cuadrillas": tiempos_cuadrillas,
        "cronologia_cuadrillas": cronologia_cuadrillas,
        "modo": "estatico",
        "rutas": rutas,
        "stock_inicial_cuadrillas": stock_inicial,
    }


def _ejecutar_planificacion(
    V: list,
    C: list,
    M: dict,
    params: dict,
    D: dict,
    coords: dict,
    K: dict,
) -> tuple[
    dict[int, list[str]],
    dict[int, list[Visita]],
    list[tuple[int, int]],
    float,
    float,
    int,
    list,
]:
    J = params["J"]
    M_big = params["M_big"]
    almacen_id = params["almacen_id"]

    rutas: dict[int, list[str]] = {c.id: [] for c in C}
    visitas_por_cuadrilla: dict[int, list[Visita]] = {c.id: [] for c in C}
    V_pendientes = list(V)

    for c in C:
        c.posicion = almacen_id
        c.tiempo_acumulado = 0.0
        c.estado = EstadoCuadrilla.LIBRE

    tiempo_esperado_acum = 0.0
    distancia_km = 0.0
    visitas_plan = 0
    primera_oleada: list[tuple[int, int]] = []
    oleada_inicial_hecha = False

    while V_pendientes:
        V_est, C_est = preprocesar(V_pendientes, C, M, J, D, modo="estatico")
        if not C_est or not V_est:
            break

        asignaciones = asignar_visitas(V_est, C_est, D, M_big, M, J, "estatico")
        if not asignaciones:
            break

        if not oleada_inicial_hecha:
            for visita, cuadrilla in asignaciones:
                primera_oleada.append((visita.id, cuadrilla.id))
            oleada_inicial_hecha = True

        from simulacion.metricas import registrar_tramo_estimado

        for visita, cuadrilla in asignaciones:
            pos = cuadrilla.posicion
            leg = D.get(pos, {}).get(visita.id, 0.0)
            if leg == float("inf"):
                leg = 0.0
            if cuadrilla.tiempo_acumulado + leg + visita.duracion > J:
                continue

            registrar_tramo_estimado(cuadrilla, visita, leg, visita.duracion)
            duracion_total = leg + visita.duracion
            tiempo_esperado_acum += duracion_total
            visitas_plan += 1
            rutas[cuadrilla.id].append(visita.nombre)
            visitas_por_cuadrilla[cuadrilla.id].append(visita)

            if pos in K and visita.id in K.get(pos, {}):
                distancia_km += K[pos][visita.id]

            for m_id, cantidad in visita.materiales_necesarios.items():
                mat = M.get(m_id)
                if mat is not None:
                    mat.consumir(cantidad)

            cuadrilla.posicion = visita.id
            cuadrilla.estado = EstadoCuadrilla.LIBRE
            visita.asignada = True
            if visita in V_pendientes:
                V_pendientes.remove(visita)

    tiempo_max = max((c.tiempo_acumulado for c in C), default=0.0)
    return (
        rutas,
        visitas_por_cuadrilla,
        primera_oleada,
        tiempo_max,
        tiempo_esperado_acum,
        distancia_km,
        visitas_plan,
        V_pendientes,
    )


def planificar_instancia(
    instancia_id: int,
    silent: bool = True,
    buffer_stock: float | None = None,
) -> ResultadoPlanEstatico:
    if silent:
        import sys
        from io import StringIO

        _out, sys.stdout = sys.stdout, StringIO()
        try:
            V, C, M, params, D, coords, K = cargar_datos_instancia(instancia_id)
        finally:
            sys.stdout = _out
    else:
        V, C, M, params, D, coords, K = cargar_datos_instancia(instancia_id)

    perfil = perfil_simulacion(instancia_id)
    if buffer_stock is None:
        buffer_stock = perfil.extra_stock_plan_pct

    V = copy.deepcopy(V)
    C = copy.deepcopy(C)
    M = copy.deepcopy(M)
    J = params["J"]

    consolidar_stock_cuadrillas_en_almacen(C, M)

    rutas, visitas_por_cuadrilla, primera_oleada, t_max, t_esp, dist, n_plan, V_rest = (
        _ejecutar_planificacion(V, C, M, params, D, coords, K)
    )

    stock = calcular_stock_desde_plan(visitas_por_cuadrilla, buffer_stock)

    from simulacion.metricas import (
        cronologia_cuadrillas,
        nombres_visitas_pendientes,
        tiempos_finales_cuadrillas,
    )

    metricas = _metricas_desde_plan(
        n_plan,
        len(V_rest),
        dist,
        J,
        rutas,
        stock,
        tiempos_finales_cuadrillas(C),
        cronologia_cuadrillas(C),
        nombres_visitas_pendientes(V_rest),
    )

    return ResultadoPlanEstatico(
        metricas=metricas,
        rutas=rutas,
        visitas_por_cuadrilla=visitas_por_cuadrilla,
        stock_inicial=stock,
        primera_oleada=primera_oleada,
    )


def preparar_cuadrillas_segun_plan(
    cuadrillas,
    catalogo_materiales,
    instancia_id: int,
    buffer_stock: float | None = None,
    silent: bool = True,
) -> ResultadoPlanEstatico:
    plan = planificar_instancia(instancia_id, silent=silent, buffer_stock=buffer_stock)
    aplicar_stock_inicial_cuadrillas(cuadrillas, plan.stock_inicial, catalogo_materiales)
    return plan


def evaluar_planificacion_estatica(instancia_id: int, silent: bool = True) -> dict:
    return planificar_instancia(instancia_id, silent=silent).metricas

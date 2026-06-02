from model import _par_factible
from modelos import EstadoCuadrilla

LIMITE_VISITAS_PRIORIDAD = 10


def obtener_cuadrillas_libres(cuadrillas):
    return [c for c in cuadrillas if c.estado == EstadoCuadrilla.LIBRE]


def eliminar_visitas_imposibles_global(V, C, D, J, M, modo="estatico"):

    V_filtradas = []

    for v in V:
        posible = False

        for c in C:
            if c.posicion not in D or v.id not in D[c.posicion]:
                continue
            tiempo = c.tiempo_acumulado + D[c.posicion][v.id] + v.duracion
            if tiempo > J:
                continue

            if modo == "dinamico":
                mat_ok = v.es_factible_cuadrilla(c)
            else:
                mat_ok = v.es_factible_stock_global(M)

            if mat_ok:
                posible = True
                break

        if posible:
            V_filtradas.append(v)

    return V_filtradas


def filtrar_cuadrillas_operativas(V, C, D, J, M, modo="estatico"):
    return [
        c
        for c in C
        if any(_par_factible(v, c, D, J, modo, M) for v in V)
    ]


def filtrar_por_prioridad(V, limite=LIMITE_VISITAS_PRIORIDAD):
    if len(V) <= limite:
        return V
    return sorted(V, key=lambda v: (-v.prioridad, v.nombre))[:limite]


def preprocesar(V, C, M, J, D, modo="estatico"):

    C_estrella = obtener_cuadrillas_libres(C)

    V_estrella = eliminar_visitas_imposibles_global(V, C_estrella, D, J, M, modo)

    C_estrella = filtrar_cuadrillas_operativas(V_estrella, C_estrella, D, J, M, modo)

    V_estrella = eliminar_visitas_imposibles_global(V_estrella, C_estrella, D, J, M, modo)

    V_estrella = filtrar_por_prioridad(V_estrella)

    C_estrella = filtrar_cuadrillas_operativas(V_estrella, C_estrella, D, J, M, modo)

    return V_estrella, C_estrella

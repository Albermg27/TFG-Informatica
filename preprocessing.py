from modelos import EstadoCuadrilla

def filtrar_por_materiales(V_estrella, materiales):
    V_final = []

    for v in V_estrella:
        if v.es_factible_materiales(materiales):
            V_final.append(v)

    return V_final

def obtener_cuadrillas_libres(cuadrillas):
    return [
        c for c in cuadrillas if c.estado == EstadoCuadrilla.LIBRE
    ]

def filtrar_por_tiempo(V, C_estrella, D, J):

    V_estrella = []

    for v in V:
        factible = False

        for c in C_estrella:

            tiempo_total = v.duracion + D[c.posicion][v.id]

            if (c.tiempo_acumulado + tiempo_total) <= J:
                factible = True
                break

        if factible:
            V_estrella.append(v)

    return V_estrella

def filtrar_por_prioridad(V, max_visitas_modelo=10):
    V_ordenadas = sorted(V, key=lambda v: v.prioridad, reverse=True)
    return V_ordenadas[:max_visitas_modelo]


def preprocesar(V, C, M, J, D):

    C_estrella = obtener_cuadrillas_libres(C)

    V_estrella = filtrar_por_tiempo(V, C_estrella, D, J)

    V_estrella = filtrar_por_materiales(V_estrella, M)

    V_estrella = filtrar_por_prioridad(V_estrella, 10)

    if not V_estrella:
        for c in C_estrella:
            c.estado = EstadoCuadrilla.INACTIVA

    return V_estrella, C_estrella
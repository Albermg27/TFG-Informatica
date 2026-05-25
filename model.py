from gurobipy import Model, GRB, quicksum

def _par_factible(v, cuadrilla, D, J, modo, materiales):
    if cuadrilla.posicion not in D or v.id not in D[cuadrilla.posicion]:
        return False
    if cuadrilla.tiempo_acumulado + D[cuadrilla.posicion][v.id] + v.duracion > J:
        return False
    if modo == "dinamico":
        return v.es_factible_cuadrilla(cuadrilla)
    return v.es_factible_stock_global(materiales)


def asignar_visitas(V, C, D, M_big, materiales, J, modo):

    if not V or not C:
        return []

    model = Model("Asignacion_de_Visitas")
    model.Params.OutputFlag = 0

    #Variables
    x = {}
    pares_factibles = []

    for i, v in enumerate(V):
        for c, cuadrilla in enumerate(C):
            x[i, c] = model.addVar(lb=0, vtype=GRB.BINARY, name=f"x_{i}_{c}")
            if _par_factible(v, cuadrilla, D, J, modo, materiales):
                pares_factibles.append((i, c))

    if not pares_factibles:
        return []

    for i, c in x:
        if (i, c) not in pares_factibles:
            model.addConstr(x[i, c] == 0)

    # Funcion objetivo
    coste_viaje = quicksum(
        D[C[c].posicion][V[i].id] * x[i, c]
        for i, c in pares_factibles
    )
    model.setObjective(coste_viaje, GRB.MINIMIZE)


    # Restricciones (s.a)

    n_visitas, n_cuadrillas = len(V), len(C)
    

    # Restricción de asignación de Cuadrilla (|V| > |C|)
    if n_visitas > n_cuadrillas:
        for c in range(n_cuadrillas):
            model.addConstr(quicksum(x[i, c] for i in range(n_visitas)) == 1)
        for i in range(n_visitas):
            model.addConstr(quicksum(x[i, c] for c in range(n_cuadrillas)) <= 1)

    # Restricción de asignación de Visita (|C| > |V|)
    elif n_visitas < n_cuadrillas:
        for i in range(n_visitas):
            model.addConstr(quicksum(x[i, c] for c in range(n_cuadrillas)) == 1)
        for c in range(n_cuadrillas):
            model.addConstr(quicksum(x[i, c] for i in range(n_visitas)) <= 1)

    # Restricción de asignación de Cuadrilla y Visita (|V| = |C|)
    else:
        for i in range(n_visitas):
            model.addConstr(quicksum(x[i, c] for c in range(n_cuadrillas)) == 1)
        for c in range(n_cuadrillas):
            model.addConstr(quicksum(x[i, c] for i in range(n_visitas)) == 1)

    # Restricción de disponibilidad global de materiales
    if modo == "estatico":
        for m_id, material in materiales.items():
            model.addConstr(
                quicksum(
                    v.materiales_necesarios.get(m_id, 0) * x[i, c_idx]
                    for i, v in enumerate(V)
                    for c_idx in range(len(C))
                ) <= material.cantidad_disponible
            )

    # Restricción de disponibilidad individual de materiales
    if modo == "dinamico":
        for c_idx, cuadrilla in enumerate(C):
            for m_id in materiales.keys():
                model.addConstr(
                    quicksum(
                        v.materiales_necesarios.get(m_id, 0) * x[i, c_idx]
                        for i, v in enumerate(V)
                    ) <= cuadrilla.materiales.get(m_id, 0)
                )

    # Restricción de jornada laboral
    for i, v in enumerate(V):
        for c_idx, cuadrilla in enumerate(C):
            if cuadrilla.posicion not in D or v.id not in D[cuadrilla.posicion]:
                continue
            model.addConstr(
                cuadrilla.tiempo_acumulado
                + D[cuadrilla.posicion][v.id]
                + v.duracion
                <= J + M_big * (1 - x[i, c_idx])
            )

    # Optimización del problema
    model.optimize()

    # Resultados
    asignaciones = []

    if model.status in (GRB.OPTIMAL, GRB.SUBOPTIMAL):
        for i, v in enumerate(V):
            for c, cuadrilla in enumerate(C):
                if x[i, c].X > 0.5:
                    asignaciones.append((v, cuadrilla))

    return asignaciones
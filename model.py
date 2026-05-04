from gurobipy import Model, GRB, quicksum

def asignar_visitas(V, C, D, M_big, materiales, J, modo):
    
    model = Model("Asignacion_de_Visitas")
    model.Params.OutputFlag = 0

    #Variables
    x = {}
    for i, v in enumerate(V):
        for c, cuadrilla in enumerate(C):
            x[i, c] = model.addVar(lb=0, vtype=GRB.BINARY, name=f"x_{i}_{c}")

    # Funcion objetivo

    distancia_total = quicksum(
        D[cuadrilla.posicion][v.id] * x[i, c]
        for i, v in enumerate(V)
        for c, cuadrilla in enumerate(C)
    )

    visitas_asignadas = quicksum(
        x[i, c]
        for i in range(len(V))
        for c in range(len(C))
    )

    model.setObjective(
        distancia_total - 1000 * visitas_asignadas,
        GRB.MINIMIZE
    )

    # Restricciones (s.a)
    
    # Restricción de asignación única de visita
    for i in range(len(V)): model.addConstr(quicksum(x[i, c] for c in range(len(C))) <= 1)

    # Restricción de asignación única de cuadrilla
    for c in range(len(C)): model.addConstr(quicksum(x[i, c] for i in range(len(V))) <= 1)

    # Restricción de disponibilidad global de materiales

    if modo == "estatico":
        for m_id, stock in materiales.items():
            model.addConstr(
                quicksum(
                    v.materiales_necesarios.get(m_id, 0) * x[i, c]
                    for i, v in enumerate(V)
                    for c in range(len(C))
                ) <= stock.cantidad_disponible
            )

    if modo == "dinamico":
        for c, cuadrilla in enumerate(C):
            for m_id in materiales.keys():
                model.addConstr(
                    quicksum(
                        v.materiales_necesarios.get(m_id, 0) * x[i, c]
                        for i, v in enumerate(V)
                    ) <= cuadrilla.materiales.get(m_id, 0)
                )

    # Restricción de jornada laboral global
    for i, v in enumerate(V):
        for c, cuadrilla in enumerate(C):
            model.addConstr(
                cuadrilla.tiempo_acumulado + D[cuadrilla.posicion][v.id] + v.duracion <= J + M_big * (1 - x[i, c])
            )

   
    # Optimización del problema
    model.optimize()

    # Resultados
    asignaciones = []

    if model.status == GRB.OPTIMAL:
        for i, v in enumerate(V): 
            for c, cuadrilla in enumerate(C):
                if x[i, c].X > 0.5:
                    asignaciones.append((v, cuadrilla))

    return asignaciones
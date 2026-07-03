from gurobipy import Model, GRB, quicksum

def _par_factible(v, cuadrilla, D, J, modo, materiales):
    if cuadrilla.posicion not in D or v.id not in D[cuadrilla.posicion]:
        return False
    if cuadrilla.tiempo_acumulado + D[cuadrilla.posicion][v.id] + v.duracion > J:
        return False
    if modo == "dinamico":
        return v.es_factible_cuadrilla(cuadrilla)
    return v.es_factible_stock_global(materiales)


def asignar_visitas(V, C, D, F):

    if not V or not C or not F:
        return []

    n_visitas, n_cuadrillas = len(V), len(C)

    N = max(n_visitas, n_cuadrillas)

    model = Model("Asignacion_de_Visitas")
    model.Params.OutputFlag = 0

    # Variables
    x = {}
    for i in range(N):
        for c in range(N):
            x[i, c] = model.addVar(vtype=GRB.BINARY, name=f"x_{i}_{c}")

    # Pares reales no factibles quedan prohibidos (x_ic = 0 para (i,c) no en F)
    for i in range(n_visitas):
        for c in range(n_cuadrillas):
            if (i, c) not in F:
                model.addConstr(x[i, c] == 0)

    # Funcion objetivo
    coste_viaje = quicksum(
        D[C[c].posicion][V[i].id] * x[i, c]
        for (i, c) in F
    )
    model.setObjective(coste_viaje, GRB.MINIMIZE)

    # Restricciones de asignacion (un unico conjunto de igualdades):
    for i in range(N):
        model.addConstr(quicksum(x[i, c] for c in range(N)) == 1)
    for c in range(N):
        model.addConstr(quicksum(x[i, c] for i in range(N)) == 1)

    # Optimización del problema
    model.optimize()

    # Resultados
    asignaciones = []

    if model.status in (GRB.OPTIMAL, GRB.SUBOPTIMAL):
        for (i, c) in F:
            if x[i, c].X > 0.5:
                asignaciones.append((V[i], C[c]))

    return asignaciones
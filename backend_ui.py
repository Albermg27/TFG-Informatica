import copy

from datos import cargar_datos
from sistema_estatico import ejecutar_sistema_estatico

DATA = {
    "V": None,
    "C": None,
    "M": None,
    "params": None,
    "D": None,
    "COORDS": None,
    "resultado_generado": False,
}

PLAN_RESULTADO = {
    "cuadrillas": None,
    "log": None,
}


def cargar_visitas_gui():
    if DATA["V"] is None:
        V, C, M, params, D, coords, _K = cargar_datos()
        DATA["V"] = V
        DATA["C"] = C
        DATA["M"] = M
        DATA["params"] = params
        DATA["D"] = D
        DATA["COORDS"] = coords

    return DATA["V"]


def ejecutar_planificacion_gui():
    if DATA["V"] is None:
        cargar_visitas_gui()

    V = copy.deepcopy(DATA["V"])
    C = copy.deepcopy(DATA["C"])
    M = copy.deepcopy(DATA["M"])
    D = copy.deepcopy(DATA["D"])
    params = copy.deepcopy(DATA["params"])

    resultado, C_final = ejecutar_sistema_estatico(V, C, M, params, D)

    PLAN_RESULTADO["cuadrillas"] = C_final
    PLAN_RESULTADO["log"] = resultado
    DATA["resultado_generado"] = True
    return resultado


def obtener_cuadrillas():
    return PLAN_RESULTADO["cuadrillas"] or DATA["C"]
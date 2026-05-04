from datos import cargar_datos
from sistema_estatico import ejecutar_sistema_estatico

DATA = {
    "V": None,
    "C": None,
    "M": None,
    "params": None,
    "D": None,
    "resultado_generado": False
}

def cargar_visitas_gui():
    if DATA["V"] is None:
        print("Cargando datos (solo una vez)")
        V, C, M, params, D = cargar_datos()
        DATA["V"] = V
        DATA["C"] = C
        DATA["M"] = M
        DATA["params"] = params
        DATA["D"] = D

    return DATA["V"]

def ejecutar_planificacion_gui():
    if DATA["V"] is None:
        cargar_visitas_gui()

    resultado, C_final = ejecutar_sistema_estatico(
        DATA["V"],
        DATA["C"],
        DATA["M"],
        DATA["params"],
        DATA["D"]
    )

    DATA["C"] = C_final
    DATA["resultado_generado"] = True
    return resultado

def obtener_cuadrillas():
    return DATA["C"]
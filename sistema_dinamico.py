from datos import actualizar_matriz_distancias
from preprocessing import preprocesar
from model import asignar_visitas
from postprocessing import postprocesar
from modelos import EstadoCuadrilla, Visita
from resultado import visualizar_rutas
from backend_ui import DATA
from estado_dinamico import V, C, M, D, J, M_big, INICIALIZADO

import copy

def inicializar_sistema():
    global INICIALIZADO, J, M_big

    if INICIALIZADO:
        return

    if DATA["V"] is None:
        from backend_ui import cargar_visitas_gui
        cargar_visitas_gui()

    print("Inicializando sistema dinámico desde DATA (COPIA PROFUNDA)...")

    # 🧹 limpiar estado dinámico
    V.clear()
    C.clear()
    M.clear()
    D.clear()

    V.extend(copy.deepcopy(DATA["V"]))
    C.extend(copy.deepcopy(DATA["C"]))
    M.update(copy.deepcopy(DATA["M"]))
    D.update(copy.deepcopy(DATA["D"]))

    # parámetros
    J = copy.deepcopy(DATA["params"]["J"])
    M_big = copy.deepcopy(DATA["params"]["M_big"])

    INICIALIZADO = True

    asignacion_inicial_dinamica()

def asignacion_inicial_dinamica():
    global V, C

    print("▶ Asignación inicial dinámica")

    # 🔴 Resetear estado de cuadrillas
    for c in C:
        c.reset_dinamico()

    V_estrella, C_estrella = preprocesar(V, C, M, J, D)

    if not V_estrella or not C_estrella:
        return

    asignaciones = asignar_visitas(V_estrella, C_estrella, D, M_big, M, J, "estatico")

    V[:], C[:] = postprocesar(asignaciones, V, C, M, D, True)

def ejecutar_asignacion():
    global V, C

    V_estrella, C_estrella = preprocesar(V, C, M, J, D)

    if not V_estrella or not C_estrella:
        return

    asignaciones = asignar_visitas(
        V_estrella, C_estrella, D, M_big, M, J, "estatico"
    )

    V, C = postprocesar(asignaciones, V, C, M, D, True)


def agregar_visita(visita: Visita):
    V.append(visita)
    actualizar_matriz_distancias(D, V, visita)

    if any(c.estado == EstadoCuadrilla.LIBRE for c in C):
        ejecutar_asignacion()


def actualizar_stock(id_mat, cantidad):
    if id_mat in M:
        M[id_mat].cantidad_disponible += cantidad
        return True
    return False


def cambiar_estado_cuadrilla(id_c, tiempo_real=None):
    cuadrilla = next((c for c in C if c.id == id_c), None)
    if not cuadrilla:
        return "no_existe"

    if cuadrilla.estado == EstadoCuadrilla.DESPLAZANDOSE:
        cuadrilla.completar_desplazamiento(tiempo_real)

    elif cuadrilla.estado == EstadoCuadrilla.TRABAJANDO:
        cuadrilla.finalizar_trabajo(tiempo_real, J)

        if V:
            ejecutar_asignacion()

    return "ok"


def terminar_sistema():
    visualizar_rutas(C, V)
from datos import actualizar_matriz_distancias
from preprocessing import preprocesar
from model import asignar_visitas
from postprocessing import postprocesar
from modelos import EstadoCuadrilla, Visita, consumir_materiales_cuadrilla
from resultado import visualizar_rutas
from backend_ui import DATA
import estado_dinamico as estado
from estado_dinamico import (
    V, C, M, D, COORDS, J, V_HISTORICO, M_big, INICIALIZADO
)

import copy

def inicializar_sistema():
    global INICIALIZADO, J, M_big

    if INICIALIZADO:
        return

    if DATA["V"] is None:
        from backend_ui import cargar_visitas_gui
        cargar_visitas_gui()

    print("Inicializando sistema dinámico desde DATA (COPIA PROFUNDA)...")

    V.clear()
    C.clear()
    M.clear()
    D.clear()
    COORDS.clear()
    V_HISTORICO.clear()
    
    V.extend(copy.deepcopy(DATA["V"]))
    C.extend(copy.deepcopy(DATA["C"]))
    M.update(copy.deepcopy(DATA["M"]))
    D.update(copy.deepcopy(DATA["D"]))
    if DATA["COORDS"] is not None:
        COORDS.update(copy.deepcopy(DATA["COORDS"]))
    V_HISTORICO.extend(copy.deepcopy(V))

    J = copy.deepcopy(DATA["params"]["J"])
    M_big = copy.deepcopy(DATA["params"]["M_big"])

    _ajustar_stock_almacen_por_cuadrillas()
    INICIALIZADO = True


def _ajustar_stock_almacen_por_cuadrillas():
    for cuadrilla in C:
        for m_id, cantidad in cuadrilla.materiales.items():
            material = M.get(m_id)
            if material is not None:
                material.cantidad_disponible = max(
                    0, material.cantidad_disponible - cantidad
                )


def _registrar_resultado_asignacion(estado_resultado, mensaje, asignaciones=None):
    estado.ULTIMO_RESULTADO_ASIGNACION = {
        "ok": estado_resultado == "ok",
        "estado": estado_resultado,
        "mensaje": mensaje,
        "asignaciones": asignaciones or [],
        "pendientes": len(V),
    }
    print(mensaje)
    estado.notificar_evento(estado_resultado, mensaje)


def _ejecutar_asignacion_interna():
    global V, C

    V_estrella, C_estrella = preprocesar(V, C, M, J, D, modo="dinamico")

    if not C_estrella:
        _registrar_resultado_asignacion(
            "sin_cuadrillas",
            "No hay cuadrillas libres para asignar.",
        )
        return V, C

    if not V_estrella:
        _registrar_resultado_asignacion(
            "sin_visitas_factibles",
            f"Hay {len(C_estrella)} cuadrilla(s) libre(s), pero ninguna visita pendiente "
            f"es factible (materiales o tiempo). {len(V)} visita(s) siguen en cola.",
        )
        return V, C

    asignaciones = asignar_visitas(
        V_estrella, C_estrella, D, M_big, M, J, "dinamico"
    )

    if not asignaciones:
        _registrar_resultado_asignacion(
            "sin_asignacion",
            f"No se pudo asignar ninguna visita ({len(V_estrella)} candidatas, "
            f"{len(C_estrella)} cuadrillas libres). Revisa stock en cuadrillas.",
        )
        return V, C

    V, C = postprocesar(asignaciones, V, C, M, D, True)
    nombres = ", ".join(f"C{c.id}->{v.nombre}" for v, c in asignaciones)
    _registrar_resultado_asignacion(
        "ok",
        f"Asignadas {len(asignaciones)} visita(s): {nombres}",
        asignaciones,
    )
    return V, C


def asignacion_inicial_dinamica():
    global V, C

    print("Asignación inicial dinámica")

    for c in C:
        c.reset_dinamico()

    V[:], C[:] = _ejecutar_asignacion_interna()


def ejecutar_asignacion():
    global V, C
    V[:], C[:] = _ejecutar_asignacion_interna()


def agregar_visita(visita: Visita):
    V.append(visita)
    V_HISTORICO.append(copy.deepcopy(visita))
    actualizar_matriz_distancias(D, COORDS, visita)

    if any(c.estado == EstadoCuadrilla.LIBRE for c in C):
        ejecutar_asignacion()


def _cancelar_visita_en_cuadrilla(id_visita: int) -> str | None:
    for cuadrilla in C:
        visita = getattr(cuadrilla, "visita_actual", None)
        if not visita or visita.id != id_visita:
            continue

        if cuadrilla.estado == EstadoCuadrilla.TRABAJANDO:
            return "en_trabajo"

        if cuadrilla.estado != EstadoCuadrilla.DESPLAZANDOSE:
            return "no_cancelable"

        nombre = visita.nombre
        visita.cancelada = True
        if visita in cuadrilla.ruta:
            cuadrilla.ruta.remove(visita)
        cuadrilla.visita_actual = None
        cuadrilla.tiempo_estimado_viaje = 0
        cuadrilla.tiempo_desplazamiento = 0
        cuadrilla.tiempo_trabajo = 0
        cuadrilla.estado = (
            EstadoCuadrilla.INACTIVA
            if cuadrilla.tiempo_acumulado >= J
            else EstadoCuadrilla.LIBRE
        )
        _registrar_resultado_asignacion(
            "cancelacion",
            f"Cancelada {nombre} mientras la cuadrilla {cuadrilla.id} iba de camino.",
        )
        return "ok"
    return None


def cancelar_visita(id_visita: int) -> str:
    visita = next((v for v in V if v.id == id_visita), None)
    if visita is not None:
        V.remove(visita)
        visita.cancelada = True
        mensaje = f"Cancelada {visita.nombre}. Quedan {len(V)} visita(s) pendientes."
        if any(c.estado == EstadoCuadrilla.LIBRE for c in C) and V:
            ejecutar_asignacion()
        _registrar_resultado_asignacion("cancelacion", mensaje)
        return "ok"

    estado_cancelacion = _cancelar_visita_en_cuadrilla(id_visita)
    if estado_cancelacion == "ok":
        if any(c.estado == EstadoCuadrilla.LIBRE for c in C) and V:
            ejecutar_asignacion()
        _registrar_resultado_asignacion(
            "cancelacion",
            "Visita cancelada. Se ha actualizado la cola de trabajo.",
        )
        return "ok"
    if estado_cancelacion == "en_trabajo":
        _registrar_resultado_asignacion(
            "no_cancelable",
            "No se puede cancelar una visita que ya está en ejecución.",
        )
        return "en_trabajo"
    if estado_cancelacion == "no_cancelable":
        _registrar_resultado_asignacion(
            "no_cancelable",
            "La visita seleccionada no se puede cancelar en su estado actual.",
        )
        return "no_cancelable"

    _registrar_resultado_asignacion(
        "no_existe",
        "No se encontró la visita seleccionada para cancelar.",
    )
    return "no_existe"


def cambiar_estado_cuadrilla(id_c, tiempo_real=None):
    cuadrilla = next((c for c in C if c.id == id_c), None)
    if not cuadrilla:
        return "no_existe"

    if cuadrilla.estado == EstadoCuadrilla.DESPLAZANDOSE:
        cuadrilla.completar_desplazamiento(tiempo_real)

    elif cuadrilla.estado == EstadoCuadrilla.TRABAJANDO:
        if cuadrilla.visita_actual:
            consumir_materiales_cuadrilla(cuadrilla, cuadrilla.visita_actual)
        cuadrilla.finalizar_trabajo(tiempo_real, J)

        if V:
            ejecutar_asignacion()

    return "ok"


def terminar_sistema():
    visualizar_rutas(C, V)
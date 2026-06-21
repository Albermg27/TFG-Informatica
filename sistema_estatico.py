from modelos import EstadoCuadrilla
from preprocessing import preprocesar
from model import asignar_visitas
from postprocessing import postprocesar
from resultado import visualizar_rutas

def sistema_terminado(C):
    return all(c.estado == EstadoCuadrilla.INACTIVA for c in C)

def _hay_cuadrillas_libres(C):
    return any(c.estado == EstadoCuadrilla.LIBRE for c in C)


def _cuadrillas_ocupadas(C):
    return any(
        c.estado in (EstadoCuadrilla.DESPLAZANDOSE, EstadoCuadrilla.TRABAJANDO)
        for c in C
    )


def _finalizar_planificacion(C, J, tiempo, max_simulacion, log):
    while _cuadrillas_ocupadas(C) and tiempo < max_simulacion:
        for c in C:
            c.actualizar_estado(J, tiempo)
        tiempo += 1

    if _cuadrillas_ocupadas(C):
        log.append("Parada: límite de simulación alcanzado con cuadrillas ocupadas")

    for c in C:
        if c.estado != EstadoCuadrilla.INACTIVA:
            c.estado = EstadoCuadrilla.INACTIVA
        c.visita_actual = None

    return tiempo


def ejecutar_sistema_estatico(V, C, M, params, D):
    log = []
    log.append("Inicio Sistema")

    J = params["J"]
    M_big = params["M_big"]

    tiempo = 0
    max_simulacion = J * len(C) * 4 + len(V) * 500

    while V and not sistema_terminado(C):
        if tiempo >= max_simulacion:
            log.append("Parada: límite de simulación alcanzado")
            break

        while not _hay_cuadrillas_libres(C) and not sistema_terminado(C):
            for c in C:
                c.actualizar_estado(J, tiempo)
            tiempo += 1
            if tiempo >= max_simulacion:
                break

        if sistema_terminado(C):
            break

        if not _hay_cuadrillas_libres(C):
            continue

        V_estrella, C_estrella = preprocesar(V, C, M, J, D, modo="estatico")

        if not C_estrella:
            tiempo += 1
            continue

        if not V_estrella:
            nombres = ", ".join(v.nombre for v in V[:8])
            if len(V) > 8:
                nombres += f"… (+{len(V) - 8})"
            log.append(
                f"t={tiempo}: hay cuadrillas libres pero ninguna visita factible "
                f"({len(V)} pendientes: {nombres})"
            )
            break

        asignaciones = asignar_visitas(V_estrella, C_estrella, D, M_big, M, J, "estatico")

        if not asignaciones:
            log.append(
                f"t={tiempo}: el modelo no pudo asignar visitas "
                f"({len(V_estrella)} candidatas, {len(C_estrella)} cuadrillas libres)"
            )
            break

        V, C = postprocesar(asignaciones, V, C, M, D, False)

        tiempo += 1

    if V:
        log.append(f"Visitas no asignadas al final: {len(V)}")
        for v in V:
            log.append(f"  - {v.nombre} (id {v.id})")

    _finalizar_planificacion(C, J, tiempo, max_simulacion, log)

    log.append("Fin de la jornada")

    for c in C:
        log.append(str(c))

    return "\n".join(log), C
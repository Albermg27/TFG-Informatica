from modelos import EstadoCuadrilla
from preprocessing import preprocesar
from model import asignar_visitas
from postprocessing import postprocesar
from datos import cargar_datos
from resultado import visualizar_rutas

def sistema_terminado(C):
    return all(c.estado == EstadoCuadrilla.INACTIVA for c in C)

def main():
    print("Inicio Sistema")

    V, C, M, params, D = cargar_datos()

    J = params["J"]
    M_big = params["M_big"]

    tiempo = 0

    while V and not sistema_terminado(C):

        for c in C:
            c.actualizar_estado(J, tiempo)

        if not any(c.estado == EstadoCuadrilla.LIBRE for c in C):
            tiempo += 1
            continue

        V_estrella, C_estrella = preprocesar(V, C, M, J, D)

        if not C_estrella or not V_estrella:
            tiempo += 1
            continue


        asignaciones = asignar_visitas(V_estrella, C_estrella, D, M_big ,M, J)

        V, C = postprocesar(asignaciones, V, C, M, D, False)

        tiempo += 1

    print("Fin de la jornada")

    for c in C:
        print(c)
    
    visualizar_rutas(C, V)

if __name__ == "__main__":
    main()
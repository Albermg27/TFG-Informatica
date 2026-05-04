from modelos import EstadoCuadrilla, Visita
from preprocessing import preprocesar
from model import asignar_visitas
from postprocessing import postprocesar
from datos import actualizar_matriz_distancias, cargar_datos
from resultado import visualizar_rutas

def sistema_terminado(C):
    return all(c.estado == EstadoCuadrilla.INACTIVA for c in C)

def hay_cuadrillas_libres(C):
    return any(c.estado == EstadoCuadrilla.LIBRE for c in C)

def crear_visita_interactiva():
    tipo = input("Tipo (instalacion/tecnica/incidencia): ")
    prioridad = int(input("Prioridad: "))
    nombre = input("Nombre: ")
    lat = float(input("Latitud: "))
    lon = float(input("Longitud: "))

    return Visita(tipo=tipo, prioridad=prioridad, nombre=nombre, latitud=lat, longitud=lon)

def actualizar_stock(M):
    print("STOCK")
    for m in M.values():
        print(f"Material {m.id} -> stock: {m.cantidad_disponible}")

    id_mat = int(input("Material a actualizar: "))
    cantidad = int(input("Cantidad a añadir: "))

    if id_mat in M:
        M[id_mat].cantidad_disponible += cantidad
        print("Stock actualizado")
    else:
        print("No existe ese material")
        
def ejecutar_asignacion(V, C, M, D, M_big, J):
    V_estrella, C_estrella = preprocesar(V, C, M, J, D)

    if not V_estrella or not C_estrella:
        return V, C

    asignaciones = asignar_visitas(V_estrella, C_estrella, D, M_big, M, J, "estatico")

    return postprocesar(asignaciones, V, C, M, D, True)

def cambiar_estado_cuadrilla(C, V, M, D, M_big, J):

    print("CUADRILLAS")
    for c in C:
        print(f"{c.id} -> {c.estado.name}")

    id_c = int(input("ID cuadrilla: "))

    cuadrilla = next((c for c in C if c.id == id_c), None)

    if not cuadrilla:
        print("No existe esa cuadrilla")

    # Desplazandose -> Trabajando
    if cuadrilla.estado == EstadoCuadrilla.DESPLAZANDOSE:

        visita = cuadrilla.visita_actual
        print(f"\nTiempo estimado viaje: {D[cuadrilla.posicion][visita.id]:.1f}")

        t_real = float(input("Tiempo real: "))
        cuadrilla.completar_desplazamiento(t_real)


    # Trabajando -> Libre -> Asignación
    elif cuadrilla.estado == EstadoCuadrilla.TRABAJANDO:

        print(f"\nDuración estimada: {cuadrilla.visita_actual.duracion}")
        t_real = float(input("Tiempo real: "))

        cuadrilla.finalizar_trabajo(t_real, J)

        if V:
            V, C = ejecutar_asignacion(V, C, M, D, M_big, J)


    # Inactiva
    else:
        print("Cuadrilla inactiva")
    return V, C

def main():
    print("Inicio Sistema")

    V, C, M, params, D = cargar_datos()

    J = params["J"]
    M_big = params["M_big"]

    if hay_cuadrillas_libres(C) and V:
        V, C = ejecutar_asignacion(V, C, M, D, M_big, J)

    while True:

        print("\nEstado Visitas")
        for c in C:
            print(c)

        print("\nVisitas pendientes:", len(V))

        print("\nMENU")
        print("1. Añadir visita")
        print("2. Actualizar stock material")
        print("3. Cambiar estado de cuadrilla")
        print("4. Salir")

        op = input("> ")

        # Añadir Visita
        if op == "1":
            visita = crear_visita_interactiva()
            V.append(visita)
            actualizar_matriz_distancias(D, V, visita)

            print("Visita añadida")

            if hay_cuadrillas_libres(C) and V:
                V, C = ejecutar_asignacion(V, C, M, D, M_big, J)

        # Actualizar stock
        elif op == "2":
            actualizar_stock(M)
            if hay_cuadrillas_libres(C) and V:
                V, C = ejecutar_asignacion(V, C, M, D, M_big, J)

        # Cambiar Estado
        elif op == "3":
            cambiar_estado_cuadrilla(C, V, M, D, M_big, J)

        # Salir
        elif op == "4":
            break

        if sistema_terminado(C):
            print("Fin de la jornada")
            break

    for c in C:
        print(c)

    visualizar_rutas(C, V)

if __name__ == "__main__":
    main()
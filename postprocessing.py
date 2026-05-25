def postprocesar(asignaciones, V, C, materiales, D, dinamic):
    visitas_realizadas = []

    for visita, cuadrilla in asignaciones:
        
        if not dinamic:
            for m_id, cantidad in visita.materiales_necesarios.items():
                materiales[m_id].consumir(cantidad)

        visita.asignada = True
        visitas_realizadas.append(visita)

        tiempo_estimado_viaje = D[cuadrilla.posicion][visita.id]
        if(dinamic):
            cuadrilla.iniciar_desplazamiento_dinamico(visita, tiempo_estimado_viaje)
        else:
            cuadrilla.iniciar_desplazamiento(visita, tiempo_estimado_viaje)

    for v in visitas_realizadas:
        if v in V:
            V.remove(v)

    return V, C
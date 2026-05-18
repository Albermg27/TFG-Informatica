def texto_visita(v, catalogo=None):
    if catalogo:
        from modelos import nombre_material
        materiales = ", ".join(
            f"{nombre_material(m_id, catalogo)} x{cant}"
            for m_id, cant in v.materiales_necesarios.items()
        ) or "Ninguno"
    else:
        materiales = ", ".join(
            f"#{m_id} x{cant}" for m_id, cant in v.materiales_necesarios.items()
        ) or "Ninguno"

    return (
        f"ID: {v.id}\n"
        f"Tipo: {v.tipo.value}\n"
        f"Nombre: {v.nombre}\n"
        f"Ubicación: ({v.latitud:.4f}, {v.longitud:.4f})\n"
        f"Duración: {v.duracion} min\n"
        f"Prioridad: {v.prioridad}\n"
        f"Materiales: {materiales}"
    )


def texto_cuadrilla_resumen(c):
    return (
        f"Cuadrilla {c.id}\n"
        f"Estado: {c.estado.name}\n"
        f"Tiempo acumulado: {c.tiempo_acumulado:.2f} min\n"
        f"Nº visitas: {len(c.ruta)}"
    )


def texto_cuadrilla_detalle(c):
    texto = "=== RESUMEN CUADRILLA ===\n\n"
    texto += f"ID: {c.id}\n"
    texto += f"Estado final: {c.estado.name}\n"
    texto += f"Tiempo total: {c.tiempo_acumulado:.2f}\n\n"

    texto += "=== RUTA REALIZADA ===\n"
    for i, v in enumerate(c.ruta, 1):
        texto += f"\n{i}. Visita {v.id} - {v.nombre}\n"
        texto += f"   Tipo: {v.tipo.value}\n"
        texto += f"   Duración: {v.duracion} min\n"

    texto += "\n=== HISTORIAL TEMPORAL ===\n"
    for visita, ini, fin in c.historial:
        texto += f"Visita {visita.id} -> {ini} - {fin}\n"

    return texto
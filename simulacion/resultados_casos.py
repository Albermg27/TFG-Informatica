from __future__ import annotations



from simulacion.metricas import (
    REPETICIONES_POR_INSTANCIA,
    _comparar_estatico_dinamico,
    _desviacion_estandar,
    _promediar_comparaciones,
    _promediar_resumenes,
)



_ultimos_resultados: dict | None = None



ETIQUETAS_METRICA = {

    "jornada_minutos": "Jornada (min)",

    "distancia_total_km": "Distancia (km)",

    "visitas_completadas": "Visitas completadas",

    "visitas_pendientes": "Visitas pendientes",

    "visitas_generadas": "Visitas generadas",

    "visitas_canceladas": "Visitas canceladas",

    "eventos_totales": "Eventos",

}



FILAS_COMPARATIVAS = [

    ("visitas_completadas", "Visitas atendidas"),

    ("visitas_pendientes", "Visitas pendientes"),

    ("visitas_generadas", "Urgentes generadas"),

    ("visitas_canceladas", "Visitas canceladas"),

    ("distancia_total_km", "Distancia (km)"),

]



METRICAS_DESTACADAS = [

    "visitas_completadas",

    "visitas_pendientes",

    "visitas_generadas",

    "visitas_canceladas",

    "distancia_total_km",

]





def guardar_resultados(datos: dict) -> None:

    global _ultimos_resultados

    _ultimos_resultados = datos





def obtener_resultados() -> dict | None:

    return _ultimos_resultados





def hay_resultados() -> bool:

    return _ultimos_resultados is not None and bool(_ultimos_resultados.get("instancias"))





def _bloque_instancia(datos: dict, instancia_id: int) -> dict | None:

    for bloque in datos.get("instancias", []):

        if bloque["instancia"].id == instancia_id:

            return bloque

    return None





def _redondear_valor(val, decimales: int = 2):
    if isinstance(val, float):
        return round(val, decimales)
    return val


def _delta_y_pct(vp, vd) -> tuple[float | int, float]:
    if isinstance(vp, (int, float)) and isinstance(vd, (int, float)):
        delta = round(float(vd) - float(vp), 2)
        pct = round((delta / vp) * 100, 1) if vp else (100.0 if vd else 0.0)
        return delta, pct
    return 0, 0.0


def _fila_comparativa(campo: str, plan: dict, dinamico: dict) -> dict:

    vp = plan.get(campo, 0)

    vd = dinamico.get(campo, 0)

    delta, pct = _delta_y_pct(vp, vd)

    return {
        "plan": _redondear_valor(vp) if isinstance(vp, float) else vp,
        "real": _redondear_valor(vd) if isinstance(vd, float) else vd,
        "delta": delta,
        "pct": pct,
    }





def _filas_tiempos_cuadrillas(plan: dict, dinamico: dict) -> list[dict]:
    tp = plan.get("tiempos_cuadrillas") or {}
    td = dinamico.get("tiempos_cuadrillas") or {}
    ids = sorted(set(tp) | set(td))
    if not ids:
        return []
    filas: list[dict] = [
        {
            "metrica": "Tiempos cuadrillas (min)",
            "plan": "—",
            "real": "—",
            "delta": "—",
            "pct": "—",
            "es_seccion": True,
        }
    ]
    for cid in ids:
        vp = tp.get(cid, 0)
        vd = td.get(cid, 0)
        delta, pct = _delta_y_pct(vp, vd)
        filas.append(
            {
                "metrica": f"  Cuadrilla {cid}",
                "plan": _redondear_valor(vp),
                "real": _redondear_valor(vd),
                "delta": delta,
                "pct": pct,
            }
        )
    return filas


def filas_comparativas(plan: dict, dinamico: dict) -> list[dict]:
    filas = [
        {"metrica": etiqueta, **_fila_comparativa(campo, plan, dinamico)}
        for campo, etiqueta in FILAS_COMPARATIVAS
        if campo in plan or campo in dinamico
    ]
    filas.extend(_filas_tiempos_cuadrillas(plan, dinamico))
    return filas





def seleccionar_vista(

    datos: dict,

    modo: str,

    instancia_id: int | None = None,

    repeticion: int | None = None,

) -> dict | None:

    if modo == "global":

        est = datos["media_global_estatico"]

        dyn = datos["media_global_dinamico"]

        comp = _comparar_estatico_dinamico(est, dyn)

        return {

            "titulo": "Resumen global (todas las instancias)",

            "subtitulo": "",

            "estatico": est,

            "dinamico": dyn,

            "comparacion": comp,

            "rutas_estatico": None,

            "rutas_dinamico": None,

            "cronologia_estatico": None,

            "cronologia_dinamico": None,

            "jornada_minutos": est.get("jornada_minutos", 0),

            "filas": filas_comparativas(est, dyn),

        }



    if instancia_id is None:

        return None



    bloque = _bloque_instancia(datos, instancia_id)

    if bloque is None:

        return None



    inst = bloque["instancia"]

    plan = bloque["plan_estatico"]

    if modo == "instancia":
        reps = bloque["repeticiones"]
        n = len(reps)
        dinamicos = [r["dinamico"] for r in reps]
        dyn = _promediar_resumenes(dinamicos)
        comp = _promediar_comparaciones([r["comparacion"] for r in reps])
        variabilidad = {}
        if n >= 2:
            variabilidad = {
                "visitas_completadas": _desviacion_estandar(
                    dinamicos, "visitas_completadas"
                ),
                "distancia_total_km": _desviacion_estandar(
                    dinamicos, "distancia_total_km"
                ),
            }

        return {
            "titulo": f"Media instancia {inst.id}: {inst.nombre}",
            "subtitulo": f"",
            "estatico": plan,
            "dinamico": dyn,
            "comparacion": comp,
            "rutas_estatico": None,
            "rutas_dinamico": None,
            "cronologia_estatico": None,
            "cronologia_dinamico": None,
            "es_vista_media": True,
            "pendientes_estatico": None,
            "pendientes_dinamico": None,
            "jornada_minutos": plan.get("jornada_minutos", 0),
            "variabilidad": variabilidad,
            "n_repeticiones": n,
            "filas": filas_comparativas(plan, dyn),
        }



    if modo == "iteracion":

        if repeticion is None:

            return None

        rep_data = next(

            (r for r in bloque["repeticiones"] if r["repeticion"] == repeticion),

            None,

        )

        if rep_data is None:

            return None

        dyn = rep_data["dinamico"]

        return {

            "titulo": f"Instancia {inst.id} · Ejecución {repeticion}/{datos.get('repeticiones', 5)}",

            "subtitulo": "",

            "estatico": plan,

            "dinamico": dyn,

            "comparacion": rep_data["comparacion"],

            "rutas_estatico": plan.get("rutas"),

            "rutas_dinamico": dyn.get("rutas"),

            "cronologia_estatico": plan.get("cronologia_cuadrillas"),

            "cronologia_dinamico": dyn.get("cronologia_cuadrillas"),

            "pendientes_estatico": plan.get("pendientes_nombres"),

            "pendientes_dinamico": dyn.get("pendientes_nombres"),

            "canceladas_dinamico": dyn.get("canceladas_nombres"),

            "cronologia_es_media": False,

            "jornada_minutos": plan.get("jornada_minutos", 0),

            "filas": filas_comparativas(plan, dyn),

        }



    return None





def lista_instancias(datos: dict) -> list[tuple[int, str]]:

    return [(b["instancia"].id, b["instancia"].nombre) for b in datos.get("instancias", [])]



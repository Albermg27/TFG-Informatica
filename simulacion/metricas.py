from __future__ import annotations

import copy
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from statistics import mean, pstdev

from database.repository import get_cuadrillas_db, get_instancias_db, get_visitas_db
from database.seed import INSTANCIAS_META
from simulacion.config_instancia import perfil_simulacion
from simulacion.plan_estatico import evaluar_planificacion_estatica

REPETICIONES_POR_INSTANCIA = 5
IDS_INSTANCIAS_PRUEBA = range(1, 11)

CAMPOS_RESUMEN = [
    "jornada_minutos",
    "distancia_total_km",
    "visitas_completadas",
    "visitas_pendientes",
    "visitas_generadas",
    "visitas_canceladas",
    "eventos_totales",
]

GLOSARIO_METRICAS = [
    (
        "Planificación (estimado)",
        "Plan total con tiempos y distancias estimados, sin urgentes. La 1.ª asignación de "
        "la simulación coincide con la del plan.",
    ),
    (
        "Sistema real (simulado)",
        "Ejecución con la misma 1.ª asignación, tiempos de viaje/trabajo normalmente "
        "superiores al estimado, urgentes según perfil y replanificación.",
    ),
    (
        "Jornada laboral",
        "Límite máximo de minutos de la jornada configurada en la instancia.",
    ),
    (
        "Distancia recorrida",
        "Kilómetros acumulados en desplazamientos (distancia por carretera OSRM entre origen y destino).",
    ),
    (
        "Visitas completadas / pendientes",
        "Atendidas vs. cola final (incluye urgentes no servidas en dinámico).",
    ),
    (
        "Visitas generadas",
        "Urgentes creadas en dinámico (Urgente 1, Urgente 2, …); 0 en plan estático.",
    ),
    (
        "Visitas canceladas",
        "Visitas pendientes retiradas durante la simulación por cancelación del cliente o de la operación.",
    ),
    (
        "Tiempos cuadrillas",
        "Minuto de jornada en que cada cuadrilla terminó su última visita asignada (no el reloj "
        "global de fin de jornada). 0 si no atendió ninguna.",
    ),
    (
        "Diferencia (dinámico − estático)",
        "Diferencia por ejecución: positivo en km indica más desplazamiento; en visitas "
        "completadas negativo indica menos servicio que el plan inicial.",
    ),
]

CAMPOS_ENTEROS = frozenset(
    {
        "jornada_minutos",
        "visitas_completadas",
        "visitas_pendientes",
        "visitas_generadas",
        "visitas_canceladas",
        "eventos_totales",
    }
)


def _redondear_metrica(valor) -> int | float:
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, int):
        return valor
    try:
        x = float(valor)
    except (TypeError, ValueError):
        return valor
    r = round(x, 2)
    if r == int(r):
        return int(r)
    return r


def _fmt_metrica(valor) -> str:
    if isinstance(valor, bool):
        return str(valor)
    if isinstance(valor, int) and not isinstance(valor, bool):
        return str(valor)
    try:
        x = float(valor)
    except (TypeError, ValueError):
        return str(valor)
    r = round(x, 2)
    if r == int(r):
        return str(int(r))
    return f"{r:.2f}"


def _fmt_delta(valor) -> str:
    try:
        x = float(valor)
    except (TypeError, ValueError):
        return str(valor)
    r = round(x, 2)
    if r == int(r):
        return f"{int(r):+d}"
    return f"{r:+.2f}"


class IndicadoresCalidad:
    def __init__(self):
        self.reset()

    def reset(self):
        self.visitas_completadas = 0
        self.visitas_pendientes = 0
        self.visitas_generadas = 0
        self.visitas_canceladas = 0
        self.eventos_totales = 0
        self.distancia_total_km = 0.0
        self.visitas_canceladas_nombres: list[str] = []

    def registrar_desplazamiento(self, distancia_km: float):
        self.distancia_total_km += distancia_km

    def registrar_cancelacion(self, nombre_visita: str):
        self.visitas_canceladas += 1
        self.visitas_canceladas_nombres.append(nombre_visita)

    def resumen(self, jornada: int | None = None) -> dict:
        return {
            "jornada_minutos": int(jornada) if jornada is not None else 0,
            "distancia_total_km": _redondear_metrica(self.distancia_total_km),
            "visitas_completadas": int(self.visitas_completadas),
            "visitas_pendientes": int(self.visitas_pendientes),
            "visitas_generadas": int(self.visitas_generadas),
            "visitas_canceladas": int(self.visitas_canceladas),
            "eventos_totales": int(self.eventos_totales),
            "canceladas_nombres": list(self.visitas_canceladas_nombres),
        }


def _tramo_tiempo(inicio: float, fin: float) -> dict:
    return {
        "inicio": _redondear_metrica(inicio),
        "fin": _redondear_metrica(fin),
        "min": _redondear_metrica(max(0.0, fin - inicio)),
    }


def registrar_tramo_estimado(cuadrilla, visita, leg_min: float, serv_min: float) -> None:
    t0 = cuadrilla.tiempo_acumulado
    leg = max(0.0, float(leg_min))
    serv = max(0.0, float(serv_min))
    cuadrilla.linea_tiempo.append(
        {
            "visita": visita.nombre,
            "visita_id": visita.id,
            "viaje": _tramo_tiempo(t0, t0 + leg),
            "servicio": _tramo_tiempo(t0 + leg, t0 + leg + serv),
        }
    )
    cuadrilla.tiempo_acumulado += leg + serv


def iniciar_tramo_dinamico(cuadrilla, visita) -> None:
    cuadrilla._tramo_actual = {
        "visita": visita.nombre,
        "visita_id": visita.id,
        "t_viaje_ini": cuadrilla.tiempo_acumulado,
    }


def cerrar_viaje_dinamico(cuadrilla) -> None:
    tramo = cuadrilla._tramo_actual
    if not tramo:
        return
    t_fin = cuadrilla.tiempo_acumulado
    tramo["viaje"] = _tramo_tiempo(tramo["t_viaje_ini"], t_fin)
    tramo["t_serv_ini"] = t_fin


def cerrar_servicio_dinamico(cuadrilla) -> None:
    tramo = cuadrilla._tramo_actual
    if not tramo or "t_serv_ini" not in tramo:
        return
    t_fin = cuadrilla.tiempo_acumulado
    cuadrilla.linea_tiempo.append(
        {
            "visita": tramo["visita"],
            "visita_id": tramo["visita_id"],
            "viaje": tramo["viaje"],
            "servicio": _tramo_tiempo(tramo["t_serv_ini"], t_fin),
        }
    )
    cuadrilla._tramo_actual = None


def cronologia_cuadrillas(cuadrillas) -> dict[int, list[dict]]:
    return {c.id: list(c.linea_tiempo) for c in sorted(cuadrillas, key=lambda x: x.id)}


def tiempos_finales_cuadrillas(cuadrillas) -> dict[int, float]:
    tiempos: dict[int, float] = {}
    for c in sorted(cuadrillas, key=lambda x: x.id):
        if c.linea_tiempo:
            tiempos[c.id] = c.linea_tiempo[-1]["servicio"]["fin"]
        elif c.historial:
            tiempos[c.id] = _redondear_metrica(c.historial[-1][2])
        elif c.tiempo_acumulado > 0:
            tiempos[c.id] = _redondear_metrica(c.tiempo_acumulado)
        else:
            tiempos[c.id] = 0
    return tiempos


def _promediar_tiempos_cuadrillas(resumenes: list[dict]) -> dict[int, float]:
    ids: set[int] = set()
    for r in resumenes:
        ids.update(r.get("tiempos_cuadrillas", {}))
    if not ids:
        return {}
    return {
        cid: _redondear_metrica(
            mean([x.get("tiempos_cuadrillas", {}).get(cid, 0) for x in resumenes])
        )
        for cid in sorted(ids)
    }


def _media_tramo_tiempo(inicios: list[float], fines: list[float]) -> dict:
    ini = _redondear_metrica(mean(inicios))
    fin = _redondear_metrica(mean(fines))
    return {"inicio": ini, "fin": fin, "min": _redondear_metrica(max(0.0, fin - ini))}


def _promediar_cronologia_cuadrillas(resumenes: list[dict]) -> dict[int, list[dict]]:
    cronologias = [r.get("cronologia_cuadrillas") or {} for r in resumenes]
    if not cronologias:
        return {}

    cids: set[int] = set()
    for cron in cronologias:
        cids.update(cron.keys())

    resultado: dict[int, list[dict]] = {}
    for cid in sorted(cids):
        por_visita: dict[str, list[dict]] = {}
        for cron in cronologias:
            for tramo in cron.get(cid, []):
                por_visita.setdefault(tramo["visita"], []).append(tramo)

        tramos_media: list[dict] = []
        for nombre, lista in por_visita.items():
            viaje_ini = [t["viaje"]["inicio"] for t in lista]
            viaje_fin = [t["viaje"]["fin"] for t in lista]
            serv_fin = [t["servicio"]["fin"] for t in lista]
            viaje = _media_tramo_tiempo(viaje_ini, viaje_fin)
            servicio = _media_tramo_tiempo(viaje_fin, serv_fin)
            tramos_media.append(
                {
                    "visita": nombre,
                    "visita_id": lista[0].get("visita_id"),
                    "viaje": viaje,
                    "servicio": servicio,
                }
            )
        tramos_media.sort(key=lambda t: t["viaje"]["inicio"])
        resultado[cid] = tramos_media
    return resultado


def _promediar_pendientes_nombres(resumenes: list[dict]) -> list[str]:
    from collections import Counter

    if not resumenes:
        return []
    conteo = Counter()
    for r in resumenes:
        for nombre in r.get("pendientes_nombres") or []:
            conteo[nombre] += 1
    n = len(resumenes)
    umbral = max(1, (n + 1) // 2)
    candidatos = [nombre for nombre, c in conteo.items() if c >= umbral]
    if not candidatos:
        candidatos = [nombre for nombre, _ in conteo.most_common()]

    def _clave(nombre: str):
        return (0 if nombre.startswith("Urgente") else 1, -conteo[nombre], nombre)

    return sorted(candidatos, key=_clave)


def _promediar_canceladas_nombres(resumenes: list[dict]) -> list[str]:
    from collections import Counter

    conteo = Counter()
    for r in resumenes:
        for nombre in r.get("canceladas_nombres") or []:
            conteo[nombre] += 1
    return [nombre for nombre, _ in conteo.most_common()]


def _rutas_desde_cronologia(cronologia: dict[int, list[dict]]) -> dict[int, list[str]]:
    return {cid: [t["visita"] for t in tramos] for cid, tramos in sorted(cronologia.items())}


def rutas_desde_cuadrillas(cuadrillas) -> dict[int, list[str]]:
    resultado: dict[int, list[str]] = {}
    for c in sorted(cuadrillas, key=lambda x: x.id):
        if c.linea_tiempo:
            resultado[c.id] = [t["visita"] for t in c.linea_tiempo]
        else:
            resultado[c.id] = [visita.nombre for visita, _t0, _t1 in c.historial]
    return resultado


def formatear_visita_ruta(tramo: dict) -> str:
    viaje = tramo["viaje"]
    servicio = tramo["servicio"]
    return (
        f"{tramo['visita']} (Inicio desplazamiento: {_fmt_metrica(viaje['inicio'])}, "
        f"Llegada: {_fmt_metrica(viaje['fin'])}, "
        f"Fin servicio: {_fmt_metrica(servicio['fin'])})"
    )


def nombres_visitas_pendientes(visitas) -> list[str]:
    def _clave(v):
        return (0 if str(v.nombre).startswith("Urgente") else 1, v.nombre)

    return [v.nombre for v in sorted(visitas, key=_clave)]


def formatear_lista_pendientes(nombres: list[str] | None) -> str:
    if not nombres:
        return "Pendientes:\n(ninguna)"
    return "Pendientes:\n" + ", ".join(nombres)


def formatear_lista_canceladas(nombres: list[str] | None) -> str:
    if not nombres:
        return "Canceladas:\n(ninguna)"
    return "Canceladas:\n" + ", ".join(nombres)


def formatear_ruta_cuadrilla(tramos: list[dict]) -> str:
    if not tramos:
        return "Ruta:\n(sin visitas)"
    lineas = ["Ruta:"]
    for tramo in tramos:
        lineas.append(f"{formatear_visita_ruta(tramo)},")
    return "\n".join(lineas)


def formatear_cronologia_texto(
    cronologia: dict[int, list[dict]], prefijo: str = "  ", jornada: int | None = None
) -> str:
    if not cronologia:
        return f"{prefijo}(sin cronología)"
    lineas = []
    if jornada:
        lineas.append(
            f"{prefijo}Tiempos en minutos (jornada planificada 0–{jornada}; "
            f"las asignadas pueden terminar después)"
        )
    for cid in sorted(cronologia):
        tramos = cronologia[cid]
        lineas.append(f"{prefijo}Cuadrilla {cid}:")
        for ln in formatear_ruta_cuadrilla(tramos).splitlines():
            lineas.append(f"{prefijo}  {ln}")
    return "\n".join(lineas)


def rutas_plan_desde_cuadrillas(rutas_por_id: dict[int, list[str]]) -> dict[int, list[str]]:
    return {cid: list(nombres) for cid, nombres in sorted(rutas_por_id.items())}


def _semilla_ejecucion(instancia_id: int, repeticion: int) -> int:
    return instancia_id * 17 + repeticion * 1009


def _meta_seed_instancia(instancia_id: int) -> tuple | None:
    if 1 <= instancia_id <= len(INSTANCIAS_META):
        return INSTANCIAS_META[instancia_id - 1]
    return None


def _texto_instancia(inst) -> list[str]:
    lineas = [
        f"ID: {inst.id}",
        f"Nombre: {inst.nombre}",
        f"Descripción: {inst.descripcion or '(sin descripción)'}",
        f"Jornada laboral: {inst.jornada_minutos} min",
    ]
    visitas = get_visitas_db(inst.id)
    cuadrillas = get_cuadrillas_db(inst.id)
    n_clientes = max(0, len(visitas) - 1)
    lineas.append(f"Visitas en dataset: {len(visitas)} ({n_clientes} clientes + almacén)")
    lineas.append(f"Cuadrillas: {len(cuadrillas)}")

    meta = _meta_seed_instancia(inst.id)
    if meta and len(meta) >= 5:
        _nombre, desc_seed, jornada_seed, factor_stock, max_visitas = meta[:5]
        lineas.append(f"Parámetros de diseño (seed): jornada {jornada_seed} min, "
                      f"factor stock {factor_stock:.2f}, hasta {max_visitas} clientes iniciales")
        if desc_seed and desc_seed != (inst.descripcion or ""):
            lineas.append(f"Notas del escenario: {desc_seed}")

    perfil = perfil_simulacion(inst.id)
    lineas.append(f"Perfil: {perfil.etiqueta_eventos}")
    lineas.append(perfil.descripcion)
    lineas.append(
        f"Parámetros: urgentes ≈ {perfil.prob_visitas_por_minuto * 60:.2f}/h "
        f"({perfil.prob_visitas_por_minuto * 100:.2f} %/min sim.) · "
        f"cancelaciones ≈ {perfil.prob_cancelaciones_por_minuto * 60:.2f}/h "
        f"({perfil.prob_cancelaciones_por_minuto * 100:.2f} %/min sim.) · "
        f"viaje {perfil.factor_viaje_min:.2f}–{perfil.factor_viaje_max:.2f}× · "
        f"trabajo {perfil.factor_trabajo_min:.2f}–{perfil.factor_trabajo_max:.2f}× · "
        f"dispersión {perfil.dispersion_visitas * 100:.2f}%"
    )
    return lineas


def _promediar_comparaciones(comparaciones: list[dict]) -> dict:
    if not comparaciones:
        return {}
    resultado = {}
    enteros_comp = {
        "delta_visitas_completadas",
        "delta_visitas_pendientes",
        "delta_visitas_generadas",
        "delta_visitas_canceladas",
        "visitas_estatico",
        "visitas_dinamico",
    }
    for clave in comparaciones[0]:
        valores = [c[clave] for c in comparaciones]
        if clave in enteros_comp:
            resultado[clave] = int(round(mean(valores)))
        else:
            resultado[clave] = _redondear_metrica(mean(valores))
    return resultado


def _promediar_resumenes(resumenes: list[dict]) -> dict:
    if not resumenes:
        return {k: 0 for k in CAMPOS_RESUMEN}
    resultado = {}
    for campo in CAMPOS_RESUMEN:
        valores = [r[campo] for r in resumenes]
        if campo in CAMPOS_ENTEROS:
            resultado[campo] = int(round(mean(valores)))
        else:
            resultado[campo] = _redondear_metrica(mean(valores))
    resultado["tiempos_cuadrillas"] = _promediar_tiempos_cuadrillas(resumenes)
    resultado["cronologia_cuadrillas"] = _promediar_cronologia_cuadrillas(resumenes)
    resultado["pendientes_nombres"] = _promediar_pendientes_nombres(resumenes)
    resultado["canceladas_nombres"] = _promediar_canceladas_nombres(resumenes)
    resultado["rutas"] = _rutas_desde_cronologia(resultado["cronologia_cuadrillas"])
    if resumenes:
        resultado["jornada_minutos"] = resumenes[0].get("jornada_minutos", resultado.get("jornada_minutos", 0))
        resultado["modo"] = resumenes[0].get("modo", "dinamico")
    return resultado


def _comparar_estatico_dinamico(estatico: dict, dinamico: dict) -> dict:
    def _delta(campo: str):
        return _redondear_metrica(dinamico.get(campo, 0) - estatico.get(campo, 0))

    vc_est = estatico.get("visitas_completadas", 0) or 1
    vc_dyn = int(dinamico.get("visitas_completadas", 0))
    return {
        "delta_visitas_completadas": int(
            dinamico.get("visitas_completadas", 0) - estatico.get("visitas_completadas", 0)
        ),
        "delta_visitas_pendientes": int(
            dinamico.get("visitas_pendientes", 0) - estatico.get("visitas_pendientes", 0)
        ),
        "delta_visitas_generadas": int(
            dinamico.get("visitas_generadas", 0) - estatico.get("visitas_generadas", 0)
        ),
        "delta_visitas_canceladas": int(
            dinamico.get("visitas_canceladas", 0) - estatico.get("visitas_canceladas", 0)
        ),
        "visitas_estatico": int(estatico.get("visitas_completadas", 0)),
        "visitas_dinamico": vc_dyn,
        "delta_distancia_km": _delta("distancia_total_km"),
        "ratio_visitas_vs_plan": _redondear_metrica(vc_dyn / vc_est) if vc_est else 0,
    }


def _formatear_comparacion(comp: dict, prefijo: str = "  ") -> str:
    ve = comp.get("visitas_estatico", 0)
    vd = comp.get("visitas_dinamico", 0)
    lineas = [
        f"{prefijo}Visitas atendidas — plan estático: {_fmt_metrica(ve)}  |  "
        f"simulación dinámica: {_fmt_metrica(vd)}  "
        f"(Diferencia {_fmt_delta(comp['delta_visitas_completadas'])})",
        f"{prefijo}Diferencia de Visitas pendientes: {_fmt_delta(comp['delta_visitas_pendientes'])}",
        f"{prefijo}Diferencia de Visitas generadas (solo dinámico): "
        f"{_fmt_delta(comp['delta_visitas_generadas'])}",
        f"{prefijo}Diferencia de Visitas canceladas: "
        f"{_fmt_delta(comp['delta_visitas_canceladas'])}",
        f"{prefijo}Diferencia de Distancia (km): {_fmt_delta(comp['delta_distancia_km'])}",
        f"{prefijo}Ratio visitas dinámico/plan: "
        f"{_fmt_metrica(comp['ratio_visitas_vs_plan'])}",
    ]
    return "\n".join(lineas)


def _formatear_rutas(
    rutas: dict[int, list[str]] | None,
    cronologia: dict[int, list[dict]] | None = None,
    prefijo: str = "  ",
    jornada: int | None = None,
) -> str:
    if cronologia:
        return formatear_cronologia_texto(cronologia, prefijo=prefijo, jornada=jornada)
    if not rutas:
        return f"{prefijo}(sin rutas)"
    lineas = []
    for cid, nombres in sorted(rutas.items()):
        secuencia = " → ".join(nombres) if nombres else "(vacía)"
        lineas.append(f"{prefijo}Cuadrilla {cid}: {secuencia}")
    return "\n".join(lineas)


def _formatear_resumen(resumen: dict, prefijo: str = "  ", titulo_modo: str | None = None) -> str:
    if titulo_modo:
        prefijo = prefijo
    etiquetas = {
        "jornada_minutos": "Jornada laboral (min)",
        "distancia_total_km": "Distancia recorrida (km)",
        "visitas_completadas": "Visitas completadas",
        "visitas_pendientes": "Visitas pendientes",
        "visitas_generadas": "Visitas generadas (dinámicas)",
        "visitas_canceladas": "Visitas canceladas",
        "eventos_totales": "Eventos totales",
    }
    lineas = []
    if titulo_modo:
        lineas.append(f"{prefijo}[{titulo_modo}]")
    for campo in CAMPOS_RESUMEN:
        valor = resumen.get(campo, 0)
        lineas.append(f"{prefijo}{etiquetas[campo]}: {_fmt_metrica(valor)}")
    tiempos = resumen.get("tiempos_cuadrillas") or {}
    if tiempos:
        lineas.append(f"{prefijo}Tiempos cuadrillas (fin última visita, min):")
        for cid in sorted(tiempos):
            lineas.append(f"{prefijo}  Cuadrilla {cid}: {_fmt_metrica(tiempos[cid])}")
    return "\n".join(lineas)


def _desviacion_estandar(resumenes: list[dict], campo: str) -> float:
    valores = [r[campo] for r in resumenes]
    if len(valores) < 2:
        return 0.0
    return _redondear_metrica(pstdev(valores))


def ejecutar_bateria_casos_prueba(
    repeticiones: int = REPETICIONES_POR_INSTANCIA,
    on_progreso: Callable[[int, int, int, int], None] | None = None,
) -> dict:
    from datos import limpiar_cache_matriz_instancia
    from osrm_client import reiniciar_cliente_osrm_simulacion
    from simulacion.motor import MotorSimulacion

    limpiar_cache_matriz_instancia()
    reiniciar_cliente_osrm_simulacion()

    instancias = [
        i for i in get_instancias_db() if i.id in IDS_INSTANCIAS_PRUEBA
    ]
    instancias.sort(key=lambda x: x.id)

    motor = MotorSimulacion(on_actualizar=None)
    resultados_instancia: list[dict] = []
    todos_dinamicos: list[dict] = []
    todos_estaticos: list[dict] = []
    total_pasos = len(instancias) * (repeticiones + 1)
    ejecutadas = 0

    for inst in instancias:
        if on_progreso:
            ejecutadas += 1
            on_progreso(ejecutadas, total_pasos, inst.id, 0)

        try:
            plan_estatico = copy.deepcopy(
                evaluar_planificacion_estatica(inst.id, silent=True)
            )
        except Exception as exc:
            from osrm_client import OSRMError

            if isinstance(exc, OSRMError):
                raise OSRMError(f"Instancia {inst.id} (plan estático): {exc}") from exc
            raise
        todos_estaticos.append(plan_estatico)

        repeticiones_data: list[dict] = []
        for rep in range(1, repeticiones + 1):
            semilla = _semilla_ejecucion(inst.id, rep)
            try:
                motor.cargar_instancia(inst.id, semilla=semilla)
                dinamico = copy.deepcopy(motor.simular_hasta_fin())
            except Exception as exc:
                from osrm_client import OSRMError

                if isinstance(exc, OSRMError):
                    raise OSRMError(
                        f"Instancia {inst.id}, repetición {rep}: {exc}"
                    ) from exc
                raise
            comparacion = _comparar_estatico_dinamico(plan_estatico, dinamico)
            repeticiones_data.append(
                {
                    "repeticion": rep,
                    "semilla": semilla,
                    "estatico": plan_estatico,
                    "dinamico": dinamico,
                    "comparacion": comparacion,
                }
            )
            todos_dinamicos.append(dinamico)
            ejecutadas += 1
            if on_progreso:
                on_progreso(ejecutadas, total_pasos, inst.id, rep)

        media_dyn = _promediar_resumenes([r["dinamico"] for r in repeticiones_data])
        media_comp = _promediar_comparaciones([r["comparacion"] for r in repeticiones_data])
        resultados_instancia.append(
            {
                "instancia": inst,
                "plan_estatico": plan_estatico,
                "repeticiones": repeticiones_data,
                "media_dinamico": media_dyn,
                "media_comparacion": media_comp,
            }
        )

    return {
        "fecha": datetime.now(),
        "repeticiones": repeticiones,
        "instancias": resultados_instancia,
        "media_global_estatico": _promediar_resumenes(todos_estaticos),
        "media_global_dinamico": _promediar_resumenes(todos_dinamicos),
        "total_ejecuciones_dinamicas": len(todos_dinamicos),
        "total_planes_estaticos": len(todos_estaticos),
    }


def generar_informe_txt(datos: dict) -> str:
    lineas: list[str] = []
    fecha = datos["fecha"]
    rep = datos["repeticiones"]
    n_inst = len(datos["instancias"])
    n_dyn = datos["total_ejecuciones_dinamicas"]

    lineas.extend(
        [
            "=" * 72,
            "INFORME DE CASOS DE PRUEBA — PLAN ESTÁTICO vs SIMULACIÓN DINÁMICA",
            "=" * 72,
            f"Generado: {fecha.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Configuración: {n_inst} instancias · {rep} repeticiones dinámicas · "
            f"1 plan estático por instancia",
            f"Total ejecuciones dinámicas: {n_dyn}",
            "",
            "Por instancia se calcula primero un plan estático (como Planificación: rutas "
            "con tiempos estimados, sin eventos). Después se simula la jornada dinámica con "
            "replanificación, tiempos reales, visitas urgentes y cancelaciones según el perfil del caso.",
            "Tiempos de desplazamiento (plan y simulación): matriz OSRM por carretera; "
            "cada visita urgente nueva consulta OSRM (peticiones espaciadas). Si OSRM falla, "
            "la batería se aborta.",
            "No se simulan entradas de material al almacén; las cuadrillas inician con más stock.",
            "",
        ]
    )

    lineas.append("-" * 72)
    lineas.append("GLOSARIO DE MÉTRICAS")
    lineas.append("-" * 72)
    for titulo, explicacion in GLOSARIO_METRICAS:
        lineas.append(f"\n• {titulo}")
        lineas.append(f"  {explicacion}")
    lineas.append("")

    for bloque in datos["instancias"]:
        inst = bloque["instancia"]
        lineas.append("=" * 72)
        lineas.append(f"INSTANCIA {inst.id}: {inst.nombre}")
        lineas.append("=" * 72)
        lineas.extend(_texto_instancia(inst))
        lineas.append("")

        plan = bloque["plan_estatico"]
        lineas.append("--- Plan estático (referencia, una vez por instancia) ---")
        lineas.append(_formatear_resumen(plan))
        stock = plan.get("stock_inicial_cuadrillas", {})
        if stock:
            lineas.append("  Material inicial por cuadrilla (plan + margen):")
            for cid in sorted(stock):
                items = ", ".join(f"id{m}×{q}" for m, q in sorted(stock[cid].items()))
                lineas.append(f"    Cuadrilla {cid}: {items or '(sin material)'}")
        lineas.append("  Cronología planificada (viaje + servicio):")
        lineas.append(
            _formatear_rutas(
                plan.get("rutas"),
                plan.get("cronologia_cuadrillas"),
                prefijo="    ",
                jornada=plan.get("jornada_minutos"),
            )
        )
        lineas.append(
            "    "
            + formatear_lista_pendientes(plan.get("pendientes_nombres")).replace("\n", "\n    ")
        )
        lineas.append("")

        for rep_data in bloque["repeticiones"]:
            r = rep_data["repeticion"]
            s = rep_data["semilla"]
            dyn = rep_data["dinamico"]
            lineas.append(f"--- Ejecución dinámica {r}/{rep} (semilla {s}) ---")
            lineas.append(_formatear_resumen(dyn))
            lineas.append("  Cronología ejecutada (viaje + servicio):")
            lineas.append(
                _formatear_rutas(
                    dyn.get("rutas"),
                    dyn.get("cronologia_cuadrillas"),
                    prefijo="    ",
                    jornada=dyn.get("jornada_minutos") or plan.get("jornada_minutos"),
                )
            )
            lineas.append(
                "    "
                + formatear_lista_pendientes(dyn.get("pendientes_nombres")).replace(
                    "\n", "\n    "
                )
            )
            lineas.append(
                "    "
                + formatear_lista_canceladas(dyn.get("canceladas_nombres")).replace(
                    "\n", "\n    "
                )
            )
            lineas.append("")
            lineas.append("  Comparación frente al plan estático:")
            lineas.append(_formatear_comparacion(rep_data["comparacion"], prefijo="    "))
            lineas.append("")

        reps = bloque["repeticiones"]
        lineas.append(f"--- Media dinámica instancia {inst.id} ({len(reps)} ejecuciones) ---")
        lineas.append(_formatear_resumen(bloque["media_dinamico"]))
        media_dyn = bloque["media_dinamico"]
        lineas.append("")
        lineas.append("  Cronología media ejecutada (viaje + servicio, media por visita):")
        lineas.append(
            _formatear_rutas(
                media_dyn.get("rutas"),
                media_dyn.get("cronologia_cuadrillas"),
                prefijo="    ",
                jornada=media_dyn.get("jornada_minutos") or plan.get("jornada_minutos"),
            )
        )
        lineas.append(
            "    "
            + formatear_lista_pendientes(media_dyn.get("pendientes_nombres")).replace(
                "\n", "\n    "
            )
        )
        lineas.append(
            "    "
            + formatear_lista_canceladas(media_dyn.get("canceladas_nombres")).replace(
                "\n", "\n    "
            )
        )
        lineas.append("")
        lineas.append("  Media de comparación (dinámico − estático):")
        lineas.append(_formatear_comparacion(bloque["media_comparacion"], prefijo="    "))
        if len(reps) >= 2:
            lineas.append("")
            lineas.append("  Desviación típica en dinámico (entre ejecuciones):")
            for campo in ("visitas_completadas", "distancia_total_km"):
                sigma = _desviacion_estandar([x["dinamico"] for x in reps], campo)
                lineas.append(f"    {campo}: σ = {_fmt_metrica(sigma)}")
        lineas.append("")

    lineas.append("=" * 72)
    lineas.append("RESUMEN GLOBAL")
    lineas.append("=" * 72)
    lineas.append("Plan estático (media entre instancias):")
    lineas.append(_formatear_resumen(datos["media_global_estatico"], prefijo="  "))
    lineas.append("")
    lineas.append(f"Simulación dinámica (media de {n_dyn} ejecuciones):")
    lineas.append(_formatear_resumen(datos["media_global_dinamico"], prefijo="  "))
    comp_global = _comparar_estatico_dinamico(
        datos["media_global_estatico"], datos["media_global_dinamico"]
    )
    lineas.append("")
    lineas.append("Comparación global (dinámico − estático):")
    lineas.append(_formatear_comparacion(comp_global, prefijo="  "))
    lineas.append("")
    lineas.append("=" * 72)
    lineas.append("Fin del informe")
    lineas.append("=" * 72)

    return "\n".join(lineas)


def guardar_informe_casos_prueba(
    ruta: str | Path,
    on_progreso: Callable[[int, int, int, int], None] | None = None,
) -> Path:
    from simulacion.resultados_casos import guardar_resultados

    datos = ejecutar_bateria_casos_prueba(on_progreso=on_progreso)
    guardar_resultados(datos)
    texto = generar_informe_txt(datos)
    path = Path(ruta)
    path.write_text(texto, encoding="utf-8")
    return path

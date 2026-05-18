class IndicadoresCalidad:
    def __init__(self):
        self.reset()

    def reset(self):
        self.tiempo_simulado = 0.0
        self.visitas_completadas = 0
        self.visitas_pendientes = 0
        self.visitas_generadas = 0
        self.eventos_totales = 0
        self.distancia_total_km = 0.0
        self.tiempo_viaje_real = 0.0
        self.tiempo_viaje_estimado = 0.0
        self.tiempo_trabajo_real = 0.0
        self.tiempo_trabajo_estimado = 0.0
        self.desviaciones_viaje = []
        self.desviaciones_trabajo = []

    def registrar_viaje(self, estimado: float, real: float, distancia_km: float):
        self.tiempo_viaje_estimado += estimado
        self.tiempo_viaje_real += real
        self.distancia_total_km += distancia_km
        if estimado > 0:
            self.desviaciones_viaje.append((real - estimado) / estimado)

    def registrar_trabajo(self, estimado: float, real: float):
        self.tiempo_trabajo_estimado += estimado
        self.tiempo_trabajo_real += real
        if estimado > 0:
            self.desviaciones_trabajo.append((real - estimado) / estimado)

    @property
    def tiempo_total_real(self):
        return self.tiempo_viaje_real + self.tiempo_trabajo_real

    @property
    def tiempo_total_esperado(self):
        return self.tiempo_viaje_estimado + self.tiempo_trabajo_estimado

    @property
    def tiempo_medio_visita(self):
        if self.visitas_completadas == 0:
            return 0.0
        return self.tiempo_total_real / self.visitas_completadas

    @property
    def desviacion_media_pct(self):
        todas = self.desviaciones_viaje + self.desviaciones_trabajo
        if not todas:
            return 0.0
        return sum(todas) / len(todas) * 100

    def resumen(self) -> dict:
        return {
            "tiempo_simulado": round(self.tiempo_simulado, 1),
            "tiempo_total_real": round(self.tiempo_total_real, 1),
            "tiempo_total_esperado": round(self.tiempo_total_esperado, 1),
            "tiempo_medio_visita": round(self.tiempo_medio_visita, 1),
            "distancia_total_km": round(self.distancia_total_km, 2),
            "visitas_completadas": self.visitas_completadas,
            "visitas_pendientes": self.visitas_pendientes,
            "visitas_generadas": self.visitas_generadas,
            "desviacion_media_pct": round(self.desviacion_media_pct, 1),
            "eventos_totales": self.eventos_totales,
        }

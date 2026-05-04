from enum import Enum

class EstadoCuadrilla(Enum):
    LIBRE = "Libre"
    DESPLAZANDOSE = "Desplazandose"
    TRABAJANDO = "Trabajando"
    INACTIVA = "Inactiva"

class TipoVisita(Enum):
    INSTALACION = "instalacion"
    TECNICA = "tecnica"
    INCIDENCIA = "incidencia"
    ALMACEN = "almacen"

class Material:
    def __init__(self, id, cantidad_disponible):
        self.id = id
        self.cantidad_disponible = cantidad_disponible
    
    def consumir(self, cantidad):
        if self.cantidad_disponible >= cantidad:
            self.cantidad_disponible -= cantidad
            return True
        return False

    def __str__(self):
        return f"Material({self.id}, stock={self.cantidad_disponible})"

class Visita:

    _next_id = 0

    def __init__(self, tipo=TipoVisita, prioridad=0, materiales_visita={}, nombre="", latitud=0.0, longitud=0.0):
        self.id = self._next_id
        Visita._next_id += 1
        self.tipo = tipo
        self.prioridad = prioridad
        self.nombre = nombre
        self.latitud = latitud
        self.longitud = longitud
        self.duracion = self.clasificar_visita(tipo)
        self.materiales_necesarios = materiales_visita
        self.asignada = False
    
    def es_factible_materiales(self, materiales):
        for material, cantidad in self.materiales_necesarios.items():
            if materiales[material].cantidad_disponible < cantidad:
                return False
        return True

    def clasificar_visita(self, tipo):
        if tipo == TipoVisita.INSTALACION:
            return 180
        elif tipo == TipoVisita.TECNICA:
            return 60
        elif tipo == TipoVisita.INCIDENCIA:
            return 90
    
    def __str__(self):
        return (
            f"Visita {self.id} | dur={self.duracion} | asignada={self.asignada}"
        )
    
class Cuadrilla:
    def __init__(self, id, estado="Libre", materiales=None):
        self.id = id
        self.ruta = []
        self.estado = estado
        self.posicion = None
        self.tiempo_acumulado = 0
        self.visita_actual = None
        self.historial = []
        self.tiempo_inicio_visita = None
        self.tiempo_desplazamiento = 0
        self.tiempo_trabajo = 0
        self.tiempo_estimado_viaje = 0
        self.materiales = materiales or {}
    
    def iniciar_desplazamiento(self, visita, tiempo_viaje):
        self.visita_actual = visita
        self.tiempo_desplazamiento = tiempo_viaje
        self.tiempo_trabajo = visita.duracion
        self.tiempo_acumulado += tiempo_viaje+ visita.duracion
        self.tiempo_restante = tiempo_viaje
        self.ruta.append(visita)
        self.estado = EstadoCuadrilla.DESPLAZANDOSE

    def iniciar_desplazamiento_dinamico(self, visita, tiempo_estimado):
        self.visita_actual = visita
        self.estado = EstadoCuadrilla.DESPLAZANDOSE
        self.tiempo_estimado_viaje = tiempo_estimado
        self.tiempo_trabajo = visita.duracion
        self.ruta.append(visita)

    def iniciar_trabajo(self, tiempo_actual):
        self.estado = EstadoCuadrilla.TRABAJANDO
        self.tiempo_inicio_visita = tiempo_actual

    def completar_desplazamiento(self, tiempo_real):
        self.tiempo_acumulado += tiempo_real
        self.iniciar_trabajo(self.tiempo_acumulado)
        self.estado = EstadoCuadrilla.TRABAJANDO
    
    def finalizar_trabajo(self, tiempo_real, J):
        self.tiempo_acumulado += tiempo_real
        visita = self.visita_actual
        t_ini = self.tiempo_inicio_visita
        t_fin = self.tiempo_acumulado
        self.historial.append((visita, t_ini, t_fin))
        self.tiempo_inicio_visita = None

        if self.tiempo_acumulado >= J:
            self.estado = EstadoCuadrilla.INACTIVA
        else:
            self.estado = EstadoCuadrilla.LIBRE

    def __str__(self):
        visita = self.visita_actual.id if self.visita_actual else None
        ruta_ids = [v.id for v in self.ruta]

        return (
            f"Cuadrilla {self.id} | estado={self.estado.name} | "
            f"pos={self.posicion} | t_acum={self.tiempo_acumulado:.1f} | "
            f"visita_actual={visita} | ruta={ruta_ids}"
        )
    
    def actualizar_estado(self, J, tiempo_actual):

        if self.estado == EstadoCuadrilla.DESPLAZANDOSE:
            self.tiempo_desplazamiento -= 1

            if self.tiempo_desplazamiento <= 0:
                self.iniciar_trabajo(tiempo_actual)

        elif self.estado == EstadoCuadrilla.TRABAJANDO:
            self.tiempo_trabajo -= 1

            if self.tiempo_trabajo <= 0:

                visita = self.visita_actual
                self.historial.append(
                    (visita, self.tiempo_inicio_visita, tiempo_actual)
                )

                self.posicion = visita.id
                self.visita_actual = None

                if self.tiempo_acumulado >= J:
                    self.estado = EstadoCuadrilla.INACTIVA
                else:
                    self.estado = EstadoCuadrilla.LIBRE

    def consumir_materiales_cuadrilla(cuadrilla, visita):
        for m_id, cantidad in visita.materiales_necesarios.items():
            cuadrilla.materiales[m_id] -= cantidad

    def reset_dinamico(self):
        self.estado = EstadoCuadrilla.LIBRE
        self.ruta_actual = []
        self.tiempo_restante = 0
        self.visita_actual = None

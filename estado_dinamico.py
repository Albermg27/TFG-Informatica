from dataclasses import dataclass

V = []
C = []
M = {}
D = {}
COORDS = {}
J = 0
M_big = 0
INICIALIZADO = False

V_HISTORICO = []

ULTIMO_RESULTADO_ASIGNACION = None


@dataclass
class EventoDinamico:
    tipo: str
    mensaje: str
    cuadrilla_id: int | None = None


EVENTOS: list[EventoDinamico] = []
_observers: list = []


def notificar_evento(tipo: str, mensaje: str, cuadrilla_id: int | None = None) -> None:
    EVENTOS.append(EventoDinamico(tipo, mensaje, cuadrilla_id))
    if len(EVENTOS) > 120:
        del EVENTOS[:-120]
    for callback in list(_observers):
        try:
            callback()
        except Exception:
            pass


def suscribir_eventos(callback) -> None:
    if callback not in _observers:
        _observers.append(callback)


def desuscribir_eventos(callback) -> None:
    if callback in _observers:
        _observers.remove(callback)


def limpiar_eventos() -> None:
    EVENTOS.clear()

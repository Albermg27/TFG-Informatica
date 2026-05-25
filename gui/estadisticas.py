from gui.context import AppContext
from gui.estadisticas_controller import obtener_controller


def mostrar(ctx: AppContext) -> None:
    obtener_controller().mostrar(ctx)

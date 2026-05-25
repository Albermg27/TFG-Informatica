from gui.context import AppContext
from gui.simulacion_vista import obtener_vista


def al_salir() -> None:
    obtener_vista().salir()


def mostrar(ctx: AppContext) -> None:
    obtener_vista().mostrar(ctx)

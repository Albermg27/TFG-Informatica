import re
import tkinter as tk

from modelos import nombre_material
from estado_dinamico import M
from gui import theme


def widget_vivo(widget) -> bool:
    if widget is None:
        return False
    try:
        return bool(widget.winfo_exists())
    except tk.TclError:
        return False


def estado_cuadrilla_visual(estado: str) -> tuple[str, str]:
    mapa = {
        "DESPLAZANDOSE": ("🚚 Desplazándose", theme.PRIMARY),
        "TRABAJANDO": ("🔧 Trabajando", theme.SUCCESS),
        "LIBRE": ("🟡 Libre", theme.WARNING),
        "INACTIVA": ("🏁 Jornada finalizada", theme.DANGER),
    }
    return mapa.get(estado, ("⚪ Desconocido", theme.SUBTEXT))


def etiqueta_material(m_id, catalogo=None):
    catalogo = catalogo or M
    return f"{nombre_material(m_id, catalogo)} (id {m_id})"


def id_desde_etiqueta(texto):
    coincidencia = re.search(r"\(id (\d+)\)\s*$", texto or "")
    return int(coincidencia.group(1)) if coincidencia else None


def opciones_catalogo(catalogo=None):
    catalogo = catalogo or M
    return [etiqueta_material(m_id, catalogo) for m_id in sorted(catalogo.keys())]


def materiales_texto(materiales, catalogo=None):
    catalogo = catalogo or M
    if not materiales:
        return "Sin materiales asignados"
    partes = [
        f"• {etiqueta_material(m_id, catalogo)} x{cantidad}"
        for m_id, cantidad in materiales.items()
    ]
    return "\n".join(partes)


def materiales_necesarios_texto(materiales, catalogo=None):
    catalogo = catalogo or M
    if not materiales:
        return "Sin materiales requeridos"
    partes = [
        f"• {etiqueta_material(m_id, catalogo)} x{cantidad}"
        for m_id, cantidad in materiales.items()
    ]
    return "\n".join(partes)

import re

from modelos import nombre_material
from estado_dinamico import M


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

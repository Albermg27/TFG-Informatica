BG_APP = "#f1f5f9"
BG_MENU = "#0f172a"
BG_CARD = "#ffffff"
BG_CARD_ALT = "#f8fafc"
BG_HOVER = "#e2e8f0"
PRIMARY = "#2563eb"
PRIMARY_DARK = "#1d4ed8"
PRIMARY_LIGHT = "#dbeafe"
SUCCESS = "#16a34a"
SUCCESS_LIGHT = "#dcfce7"
WARNING = "#d97706"
WARNING_LIGHT = "#fef3c7"
DANGER = "#dc2626"
DANGER_LIGHT = "#fee2e2"
TEXT = "#0f172a"
TEXT_SECONDARY = "#475569"
SUBTEXT = "#64748b"
BORDER = "#e2e8f0"
BORDER_FOCUS = "#93c5fd"

FONT_FAMILY = "Segoe UI"
FONT_TITLE = (FONT_FAMILY, 22, "bold")
FONT_HEADING = (FONT_FAMILY, 18, "bold")
FONT_SUBHEADING = (FONT_FAMILY, 13, "bold")
FONT_BODY = (FONT_FAMILY, 10)
FONT_BODY_BOLD = (FONT_FAMILY, 10, "bold")
FONT_SMALL = (FONT_FAMILY, 9)
FONT_CAPTION = (FONT_FAMILY, 8)
FONT_STAT = (FONT_FAMILY, 24, "bold")
FONT_ICON = (FONT_FAMILY, 26)

TIPO_VISITA = {
    "instalacion": {"icono": "🏗", "color": "#2563eb", "bg": "#dbeafe"},
    "tecnica": {"icono": "🔧", "color": "#16a34a", "bg": "#dcfce7"},
    "incidencia": {"icono": "⚠", "color": "#dc2626", "bg": "#fee2e2"},
    "almacen": {"icono": "📦", "color": "#64748b", "bg": "#f1f5f9"},
    "TODAS": {"icono": "📊", "color": PRIMARY, "bg": PRIMARY_LIGHT},
}

NAV_ITEMS = [
    ("Visitas", "📋", "visitas"),
    ("Cuadrillas", "👷", "cuadrillas"),
    ("Materiales", "📦", "materiales"),
    ("Planificación", "🗺", "planificacion"),
    ("Sistema Dinámico", "⚡", "dinamico"),
    ("Simulación", "🧪", "simulacion"),
]

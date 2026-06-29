import customtkinter as ctk


def apply_theme() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("green")


# Colores de conexión
CONN_COLORS = {
    "connected": "#22C55E",
    "disconnected": "#EF4444",
}

# Paleta general
COLORS = {
    "warning": "#F59E0B",
    "surface": "#2B2B2B",
    "border": "#3F3F3F",
    "disconnected": "#EF4444",
    "connected": "#22C55E",
    "nav_hover": "#2e2e2e",
    "nav_active": "#2e2e2e",
    "accent": "#22C55E",
    "badge_error": "#EF4444",
    "fault": "#EF4444",
    "unknown": "#6B7280",
}

# Fuentes
FONT_TITLE = ("Roboto", 16, "bold")
FONT_NORMAL = ("Roboto", 13)
FONT_SMALL = ("Roboto", 11)
FONT_MONO = ("Courier New", 11)

# Constantes de layout
SIDEBAR_WIDTH = 200
TOPBAR_HEIGHT = 48
STATUSBAR_HEIGHT = 28

# Colores adicionales
BG_SIDEBAR = ("gray90", "#1c1c1c")
BG_TOPBAR = ("gray95", "#151515")
BG_STATUSBAR = ("gray90", "#1c1c1c")
DIVIDER = ("gray75", "#2e2e2e")

# Items de navegación
NAV_ITEMS = [
    ("dht11", "DHT11", "Panel de lecturas DHT11"),
    ("arduinos", "Arduinos", "Gestor de placas Arduino"),
    ("exportar", "Exportar", "Exportar datos históricos"),
    ("ayuda", "Ayuda", "Ayuda del sistema"),
]

NAV_BOTTOM_ITEMS = [
    ("ajustes", "Ajustes", "Configuración general"),
]

# Fuente para el logo
FONT_LOGO = ("Roboto", 20, "bold")

import customtkinter as ctk


def apply_theme() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("green")


# Colores de estado FSM
FSM_COLORS = {
    "Idle": "#6B7280",
    "Monitoring": "#22C55E",
    "Irrigating": "#3B82F6",
    "Fault": "#EF4444",
}

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
}

# Fuentes
FONT_TITLE = ("Roboto", 16, "bold")
FONT_NORMAL = ("Roboto", 13)
FONT_SMALL = ("Roboto", 11)
FONT_MONO = ("Courier New", 11)

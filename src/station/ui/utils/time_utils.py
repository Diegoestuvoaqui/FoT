from __future__ import annotations

from datetime import datetime, timedelta


def ms_to_hms(ms: int | float) -> str:
    """
    Convierte milisegundos de duración a HH:MM:SS.
    Útil si 'ts' es tiempo transcurrido, no timestamp.
    """
    total_seconds = int(ms / 1000)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def ms_timestamp_to_local(ts_ms: int | float) -> str:
    """
    Convierte un timestamp en milisegundos (epoch) a hora local HH:MM:SS.
    Útil si 'ts' es el tiempo absoluto del sistema Arduino.
    """
    dt = datetime.fromtimestamp(ts_ms / 1000.0)
    return dt.strftime("%H:%M:%S")


def ms_timestamp_to_full(ts_ms: int | float) -> str:
    """
    Convierte timestamp en ms a fecha y hora completa.
    """
    dt = datetime.fromtimestamp(ts_ms / 1000.0)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_elapsed(ms: int | float) -> str:
    """
    Formatea duración de forma legible: '2h 15m 30s' o '45s'.
    """
    td = timedelta(milliseconds=int(ms))
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")
    return " ".join(parts)

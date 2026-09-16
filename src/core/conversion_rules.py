"""Reglas de decisión de la conversión: puras, sin Tk ni threads.

Extraídas de `ConverterView` (candidato 2 del reporte de arquitectura): antes
vivían como líneas sueltas dentro de los métodos de la vista, mezcladas con
la construcción de widgets. Aquí quedan aisladas para poder testearlas sin
levantar CustomTkinter.
"""

import os
from typing import Dict, Optional


def resolve_output_dir(settings: dict) -> str:
    """Carpeta de destino de la descarga: la configurada por el usuario, o
    `~/Downloads` si todavía no eligió ninguna."""
    return settings.get("download_path") or os.path.expanduser("~/Downloads")


def resolve_max_height(
    fmt: str, quality_heights: Dict[str, Optional[int]], selected_label: str
) -> Optional[int]:
    """Tope de resolución a pedirle a `Downloader`. Solo aplica a MP4 -- un
    MP3 no tiene pista de video que limitar."""
    if fmt != "mp4":
        return None
    return quality_heights.get(selected_label)


def build_quality_options(
    heights: list, best_label: str
) -> Dict[str, Optional[int]]:
    """Mapa de etiqueta visible -> altura real, a partir de las resoluciones
    que `QualityProbe` encontró para un video. `best_label` (p.ej. "Mejor
    calidad") siempre está primero y no tiene una altura fija (`None`)."""
    options: Dict[str, Optional[int]] = {best_label: None}
    for height in heights:
        options[f"{height}p"] = height
    return options

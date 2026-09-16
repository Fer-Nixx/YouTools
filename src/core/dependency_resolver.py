"""Localiza binarios externos (ffmpeg/ffprobe) sin importar el SO ni si la
app corre desde código fuente o ya empaquetada con PyInstaller.

Candidato "DependencyResolver" del reporte de arquitectura multiplataforma:
antes, `downloader.py` preguntaba `shutil.which("ffmpeg")` -- y repetía el
nombre del binario -- en 5 lugares distintos, con un mensaje de error
escrito solo para macOS. Acá queda un único lugar que sabe responder "¿dónde
está esto?" y "¿qué le digo al usuario si no está?".

`resolve_binary_path` y `missing_ffmpeg_message` son puras (el seam que se
testea sin tocar el sistema real); `find_ffmpeg`/`find_ffprobe` son el
wrapper delgado que sí lee `sys`/`shutil` de verdad.
"""

import shutil
import sys
from pathlib import Path
from typing import Optional


def resolve_binary_path(
    bundled_exists: bool,
    bundled_path: Optional[str],
    which_result: Optional[str],
) -> Optional[str]:
    """Decide qué ruta usar para un binario externo, dado lo que ya se
    averiguó afuera (sin tocar disco ni el SO acá adentro).

    Prioridad: un binario empaquetado junto al ejecutable (si existe en
    disco) gana sobre el que encuentre el PATH del sistema -- así, el día
    que se empaquete ffmpeg junto al `.exe`/`.app`, no hace falta tocar
    ningún llamador.
    """
    if bundled_exists and bundled_path:
        return bundled_path
    return which_result


def missing_ffmpeg_message(platform: str) -> str:
    """Instrucciones para instalar ffmpeg, correctas para el SO actual --
    reemplaza el mensaje que antes asumía siempre macOS/Homebrew."""
    if platform == "darwin":
        return "Falta ffmpeg, necesario para convertir/fusionar el archivo. Instálalo con: brew install ffmpeg"
    if platform == "win32":
        return (
            "Falta ffmpeg, necesario para convertir/fusionar el archivo. "
            "Descárgalo desde https://ffmpeg.org/download.html y agrégalo al PATH del sistema."
        )
    return (
        "Falta ffmpeg, necesario para convertir/fusionar el archivo. "
        "Instálalo con el gestor de paquetes de tu sistema."
    )


def _bundled_dir() -> Optional[Path]:
    """Carpeta donde viviría un binario empaquetado junto al ejecutable, si
    la app corre congelada (PyInstaller). `None` si corre desde código
    fuente -- ahí no tiene sentido buscar nada "junto al ejecutable"."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return None


def _find(name: str) -> Optional[Path]:
    filename = f"{name}.exe" if sys.platform == "win32" else name
    bundled_dir = _bundled_dir()
    bundled_candidate = bundled_dir / filename if bundled_dir else None

    resolved = resolve_binary_path(
        bundled_exists=bundled_candidate is not None and bundled_candidate.exists(),
        bundled_path=str(bundled_candidate) if bundled_candidate else None,
        which_result=shutil.which(name),
    )
    return Path(resolved) if resolved else None


def find_ffmpeg() -> Optional[Path]:
    return _find("ffmpeg")


def find_ffprobe() -> Optional[Path]:
    return _find("ffprobe")

"""Resuelve dónde vive la configuración de la app y dónde buscar recursos
empaquetados, sin importar el SO ni si la app corre desde código fuente o ya
empaquetada con PyInstaller.

Candidato "AppPaths" del reporte de arquitectura multiplataforma: antes,
`settings_manager.py` asumía directo la convención de macOS/Linux
(`~/.youtools`), que no es idiomática en Windows (ahí lo esperable es
`%APPDATA%`, no un dotfolder en el home).

`resolve_config_dir` y `resolve_resource_dir` son puras (el seam que se
testea sin tocar `sys.platform`/`Path.home()`/variables de entorno reales);
`config_dir`/`resource_path` son el wrapper delgado que sí los lee de
verdad.
"""

import os
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Optional


def resolve_config_dir(platform: str, home: str, appdata: Optional[str]) -> str:
    """Decide dónde debería vivir `settings.json`, dado el SO, el home del
    usuario y (en Windows) `%APPDATA%` -- ya averiguados afuera.

    Se arma con `PureWindowsPath`/`PurePosixPath` (no con `Path` real) para
    que el resultado use las barras correctas del SO que describe
    `platform`, sin depender de en qué SO esté corriendo el código que
    llama a esta función.
    """
    if platform == "win32":
        # Sin el dotfolder de Unix: en Windows la carpeta se llama
        # "YouTools" tal cual, sea que viva dentro de %APPDATA% o (en el
        # caso raro de que falte esa variable) directo en el home.
        base = appdata if appdata else home
        return str(PureWindowsPath(base) / "YouTools")
    return str(PurePosixPath(home) / ".youtools")


def resolve_resource_dir(frozen: bool, meipass: Optional[str], source_root: str) -> str:
    """Decide dónde buscar un recurso empaquetado (una fuente, un ícono, un
    binario vendorizado), dado si la app corre congelada (PyInstaller) y
    dónde -- ya averiguado afuera.

    Corriendo desde código fuente, siempre gana `source_root`, sin importar
    lo que diga `meipass` (defensivo: esa variable no debería existir ahí).
    """
    if frozen and meipass:
        return meipass
    return source_root


def config_dir() -> Path:
    return Path(resolve_config_dir(sys.platform, str(Path.home()), os.environ.get("APPDATA")))


def resource_path(*parts: str) -> Path:
    """Ruta a un recurso empaquetado junto al código (fuentes, íconos,
    binarios vendorizados). Sin llamador real todavía -- ver el aviso en la
    conversación: se construye ahora, testeada, para que agregar un recurso
    empaquetado más adelante (ej. el .ttf de Inter) no requiera tocar esta
    lógica de resolución."""
    frozen = getattr(sys, "frozen", False)
    meipass = getattr(sys, "_MEIPASS", None)
    # De `src/core/app_paths.py` a la raíz del proyecto: subir 3 niveles
    # (core -> src -> raíz).
    source_root = str(Path(__file__).resolve().parents[2])
    base = resolve_resource_dir(frozen, meipass, source_root)
    return Path(base, *parts)

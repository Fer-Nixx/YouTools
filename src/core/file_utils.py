"""Utilidades del sistema de archivos: revelar el archivo descargado."""

import os
import subprocess
import sys


def reveal_in_file_manager(path: str) -> None:
    """Abre el explorador de archivos del SO mostrando/seleccionando `path`."""
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", "-R", path], check=False)
        elif sys.platform == "win32":
            subprocess.run(["explorer", "/select,", path], check=False)
        else:
            subprocess.run(["xdg-open", os.path.dirname(path)], check=False)
    except Exception:
        pass

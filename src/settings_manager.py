"""Persistencia simple de configuración de usuario (idioma, carpeta, tema).

Se guarda fuera del repositorio -- en `~/.youtools` en macOS/Linux, en
`%APPDATA%/YouTools` en Windows (ver `core.app_paths`) -- para que la
configuración sobreviva entre ejecuciones sin ensuciar el proyecto.
"""

import json

from .config import DEFAULT_DOWNLOAD_PATH
from .core.app_paths import config_dir

CONFIG_DIR = config_dir()
CONFIG_FILE = CONFIG_DIR / "settings.json"

DEFAULTS = {
    "language": "Español",
    "download_path": DEFAULT_DOWNLOAD_PATH,
    "appearance": "System",  # "System" | "Light" | "Dark"
    "onboarded": False,
}


def load_settings() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {**DEFAULTS, **data}
        except (json.JSONDecodeError, OSError):
            pass
    return dict(DEFAULTS)


def save_settings(settings: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)

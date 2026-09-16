"""Configuración global de YouTools: paleta de colores, tipografía y constantes.

Todos los valores aquí provienen del Manual de Identidad Visual del PRD. No
introducir colores fuera de esta paleta en las vistas/componentes.
"""

import os
from pathlib import Path
import tkinter.font as tkfont

APP_NAME = "YouTools"

# --- Paleta de colores oficial ---
COLORS = {
    "shadow_grey": "#1C1C21",
    "mahogany_red": "#B31919",
    "tiger_orange": "#F18805",
    "canary_yellow": "#F0F757",
    # Variantes auxiliares derivadas para superficies/texto en cada tema.
    # customtkinter acepta tuplas (light, dark) en casi todos los `*_color`.
    "surface_light": "#F5F5F7",
    "surface_dark": "#1C1C21",
    "card_light": "#FFFFFF",
    "card_dark": "#26262D",
    "text_light": "#1C1C21",
    "text_dark": "#F5F5F7",
    "text_muted_light": "#6E6E76",
    "text_muted_dark": "#8A8A93",
    # Variante "un poco más llamativa" del muted, para la marca de agua del
    # footer: sigue siendo un gris neutro (no rompe la regla de discreción
    # del manual) pero con más contraste que el muted estándar.
    "text_muted_light_strong": "#48484F",
    "text_muted_dark_strong": "#B8B8C0",
    "border_light": "#E2E2E6",
    "border_dark": "#33333B",
}

# --- Tipografía ---
FONT_FAMILY_PREFERRED = "Inter"
FONT_FALLBACKS = ["SF Pro Display", "Helvetica Neue", "Segoe UI", "Arial"]


def resolve_font_family() -> str:
    """Devuelve 'Inter' si está instalada en el sistema; si no, un fallback razonable."""
    try:
        available = set(tkfont.families())
    except Exception:
        return FONT_FALLBACKS[-1]
    if FONT_FAMILY_PREFERRED in available:
        return FONT_FAMILY_PREFERRED
    for fallback in FONT_FALLBACKS:
        if fallback in available:
            return fallback
    return "Arial"


class Fonts:
    """Se inicializa una única vez que existe una instancia de Tk (App.__init__)."""

    family = "Arial"
    TITLE = None
    SUBTITLE = None
    SECTION = None
    BODY = None
    BODY_MEDIUM = None
    SMALL = None
    BUTTON = None

    @classmethod
    def init(cls) -> None:
        cls.family = resolve_font_family()
        cls.TITLE = (cls.family, 28, "bold")
        cls.SUBTITLE = (cls.family, 18, "bold")
        cls.SECTION = (cls.family, 15, "bold")
        cls.BODY = (cls.family, 13, "normal")
        cls.BODY_MEDIUM = (cls.family, 13, "normal")
        cls.SMALL = (cls.family, 11, "normal")
        cls.BUTTON = (cls.family, 14, "bold")


LANGUAGES = ["Español", "English"]

# La carpeta de descargas debe llamarse siempre "youtools" (requisito del
# usuario, reservado para una funcionalidad futura que depende de ese nombre
# fijo). Sea cual sea la carpeta que el usuario elija en el diálogo del
# sistema, se usa/crea una subcarpeta "youtools" dentro de ella.
REQUIRED_DOWNLOAD_FOLDER_NAME = "youtools"
DEFAULT_DOWNLOAD_PATH = str(Path.home() / "Downloads" / REQUIRED_DOWNLOAD_FOLDER_NAME)


def ensure_youtools_folder(chosen_path: str) -> str:
    """Garantiza que la ruta termine en una carpeta llamada "youtools".

    Si el usuario ya seleccionó una carpeta que se llama así (sin importar
    mayúsculas/minúsculas), se respeta tal cual; si no, se le agrega una
    subcarpeta "youtools" al final. Solo normaliza el string -- no toca el
    disco (para eso ver `create_youtools_folder`).
    """
    if not chosen_path:
        return chosen_path
    normalized = os.path.normpath(chosen_path)
    if os.path.basename(normalized).lower() == REQUIRED_DOWNLOAD_FOLDER_NAME:
        return normalized
    return os.path.join(normalized, REQUIRED_DOWNLOAD_FOLDER_NAME)


def create_youtools_folder(chosen_path: str) -> tuple:
    """Normaliza la ruta con `ensure_youtools_folder` y crea la carpeta en
    disco si todavía no existe.

    El diálogo nativo del sistema (`filedialog.askdirectory`) solo deja
    elegir carpetas que ya existen, así que la subcarpeta "youtools" nunca
    existe todavía la primera vez -- hay que crearla. Pero crearla puede
    fallar por motivos fuera de nuestro control (permisos denegados, la
    carpeta padre vive en un volumen de solo lectura o ya se desmontó, un
    nombre de archivo con el mismo nombre ya existe ahí, etc.), así que esto
    nunca deja escapar la excepción -- la UI debe poder seguir funcionando
    con la carpeta anterior en vez de crashear a mitad de un cambio de ajuste.

    Devuelve (ruta_normalizada, mensaje_de_error). `mensaje_de_error` es
    `None` si todo salió bien; si no, la ruta pedida no se pudo crear y el
    llamador debe avisar al usuario y no guardar el cambio.
    """
    normalized = ensure_youtools_folder(chosen_path)
    if not normalized:
        return normalized, None
    try:
        os.makedirs(normalized, exist_ok=True)
    except NotADirectoryError:
        return normalized, "Ya existe un archivo con ese nombre en esa ubicación."
    except PermissionError:
        return normalized, "No hay permiso para crear carpetas en esa ubicación."
    except OSError as exc:
        return normalized, f"No se pudo crear la carpeta ahí: {exc.strerror or exc}"
    return normalized, None

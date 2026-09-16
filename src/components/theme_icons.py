"""Íconos minimalistas para el selector de apariencia (Sistema/Claro/Oscuro).

Mismo enfoque que `social_icons.py`: glifos monocromos dibujados en runtime
con Pillow (supersampling 4x + downsample LANCZOS para bordes suaves) en vez
de depender de assets binarios externos o de emoji (que renderizan a color y
con estilo inconsistente entre sistemas, rompiendo la paleta minimalista).
"""

import customtkinter as ctk
from PIL import Image, ImageDraw

_SIZE = 15
_SCALE = 4


def _base_image():
    return Image.new("RGBA", (_SIZE * _SCALE, _SIZE * _SCALE), (0, 0, 0, 0))


def _downsample(img: Image.Image) -> Image.Image:
    return img.resize((_SIZE, _SIZE), Image.LANCZOS)


def _hex_to_rgba(color_hex: str, alpha: int = 255) -> tuple:
    color_hex = color_hex.lstrip("#")
    r, g, b = (int(color_hex[i : i + 2], 16) for i in (0, 2, 4))
    return (r, g, b, alpha)


def _sun_glyph(rgba) -> Image.Image:
    """Sol: círculo relleno + 8 rayos cortos alrededor."""
    img = _base_image()
    draw = ImageDraw.Draw(img)
    s = _SIZE * _SCALE
    cx, cy = s / 2, s / 2
    r_core = s * 0.20
    r_ray_in = s * 0.30
    r_ray_out = s * 0.44
    width = max(1, int(s * 0.07))

    draw.ellipse((cx - r_core, cy - r_core, cx + r_core, cy + r_core), fill=rgba)

    import math
    for i in range(8):
        angle = math.radians(i * 45)
        x1 = cx + r_ray_in * math.cos(angle)
        y1 = cy + r_ray_in * math.sin(angle)
        x2 = cx + r_ray_out * math.cos(angle)
        y2 = cy + r_ray_out * math.sin(angle)
        draw.line((x1, y1, x2, y2), fill=rgba, width=width)

    return _downsample(img)


def _moon_glyph(rgba) -> Image.Image:
    """Luna: círculo completo con otro círculo desplazado recortado en
    transparente, la silueta clásica de media luna (creciente)."""
    img = _base_image()
    draw = ImageDraw.Draw(img)
    s = _SIZE * _SCALE
    r = s * 0.34
    cx, cy = s * 0.46, s / 2

    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=rgba)
    # Círculo de recorte desplazado hacia arriba-derecha: lo que queda fuera
    # de la intersección es la "uña" de luna creciente.
    cut_r = r * 0.92
    cut_cx, cut_cy = cx + r * 0.62, cy - r * 0.28
    draw.ellipse(
        (cut_cx - cut_r, cut_cy - cut_r, cut_cx + cut_r, cut_cy + cut_r),
        fill=(0, 0, 0, 0),
    )

    return _downsample(img)


def _monitor_glyph(rgba) -> Image.Image:
    """Monitor/PC: pantalla redondeada + base -- para "Sistema" (sigue lo
    que diga el sistema operativo)."""
    img = _base_image()
    draw = ImageDraw.Draw(img)
    s = _SIZE * _SCALE

    screen_left, screen_right = s * 0.12, s * 0.88
    screen_top, screen_bottom = s * 0.14, s * 0.62
    draw.rounded_rectangle(
        (screen_left, screen_top, screen_right, screen_bottom),
        radius=s * 0.08, outline=rgba, width=max(1, int(s * 0.075)),
    )

    # Base: un tallo corto + un pie horizontal.
    stem_w = s * 0.09
    draw.rectangle(
        (s / 2 - stem_w / 2, screen_bottom, s / 2 + stem_w / 2, s * 0.78), fill=rgba,
    )
    foot_w = s * 0.34
    draw.rounded_rectangle(
        (s / 2 - foot_w / 2, s * 0.78, s / 2 + foot_w / 2, s * 0.86),
        radius=s * 0.03, fill=rgba,
    )

    return _downsample(img)


_GLYPHS = {"system": _monitor_glyph, "light": _sun_glyph, "dark": _moon_glyph}


def make_theme_icon_pair(name: str, off_color_hex: str, on_color_hex: str) -> tuple:
    """Devuelve `(CTkImage_apagado, CTkImage_encendido)` para "system",
    "light" o "dark", en los dos colores que puede tomar el chip del toggle
    de apariencia (apagado/muted, encendido/Shadow Grey)."""
    glyph_fn = _GLYPHS[name]
    off_img = glyph_fn(_hex_to_rgba(off_color_hex))
    on_img = glyph_fn(_hex_to_rgba(on_color_hex))
    return (
        ctk.CTkImage(light_image=off_img, dark_image=off_img, size=(_SIZE, _SIZE)),
        ctk.CTkImage(light_image=on_img, dark_image=on_img, size=(_SIZE, _SIZE)),
    )

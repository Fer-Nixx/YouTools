"""Ícono de marca de YouTools: una caja de herramientas minimalista.

Mismo enfoque que `social_icons.py`/`theme_icons.py`: un glifo monocromo
dibujado en runtime con Pillow (supersampling 4x + downsample LANCZOS) en
vez de un asset binario o un emoji -- consistencia visual con el resto de
la identidad de marca.
"""

import customtkinter as ctk
from PIL import Image, ImageDraw

_SIZE = 26  # escala junto con el texto de la marca en sidebar.py (22->26pt)
_SCALE = 4


def _base_image():
    return Image.new("RGBA", (_SIZE * _SCALE, _SIZE * _SCALE), (0, 0, 0, 0))


def _downsample(img: Image.Image) -> Image.Image:
    return img.resize((_SIZE, _SIZE), Image.LANCZOS)


def _hex_to_rgba(color_hex: str, alpha: int = 255) -> tuple:
    color_hex = color_hex.lstrip("#")
    r, g, b = (int(color_hex[i : i + 2], 16) for i in (0, 2, 4))
    return (r, g, b, alpha)


def _toolbox_glyph(rgba, line_w_factor: float) -> Image.Image:
    """Caja de herramientas: cuerpo redondeado, asa en arco, y una línea con
    un broche central marcando la tapa -- la silueta clásica del ícono
    "toolbox" que se ve en librerías como Feather/Lucide, dibujada a mano
    para no sumar una dependencia nueva solo por un ícono."""
    img = _base_image()
    draw = ImageDraw.Draw(img)
    s = _SIZE * _SCALE

    body_left, body_right = s * 0.08, s * 0.92
    body_top, body_bottom = s * 0.42, s * 0.86
    line_w = max(2, int(s * line_w_factor))

    # Asa: un arco (mitad superior de una píldora) que sale del cuerpo.
    handle_left, handle_right = s * 0.30, s * 0.70
    handle_top = s * 0.12
    draw.arc(
        (handle_left, handle_top, handle_right, body_top + s * 0.10),
        start=180, end=360, fill=rgba, width=line_w,
    )

    # Cuerpo: rectángulo redondeado con borde (no relleno) para que se lea
    # como una caja hueca, no un bloque sólido.
    draw.rounded_rectangle(
        (body_left, body_top, body_right, body_bottom),
        radius=s * 0.09, outline=rgba, width=line_w,
    )

    # Línea divisoria tapa/cuerpo, a un tercio de la altura de la caja.
    divider_y = body_top + (body_bottom - body_top) * 0.32
    draw.line((body_left, divider_y, body_right, divider_y), fill=rgba, width=line_w)

    # Broche central sobre la línea divisoria.
    latch_w, latch_h = s * 0.16, s * 0.14
    cx = s / 2
    draw.rounded_rectangle(
        (cx - latch_w / 2, divider_y - latch_h / 2, cx + latch_w / 2, divider_y + latch_h / 2),
        radius=s * 0.03, fill=rgba,
    )

    return img


def make_brand_icon(color_hex: str, line_w_factor: float = 0.09) -> ctk.CTkImage:
    """Devuelve el ícono de caja de herramientas en un color concreto (ya
    resuelto para el modo de apariencia activo -- mismo criterio que
    `theme_icons.py`, sin variante automática light/dark en el CTkImage).

    `line_w_factor` controla el grosor del trazo -- pensado para poder
    igualarlo al grosor de un texto en negrita de al lado (ver
    `sidebar.py`), no quedar más fino y leerse como un ícono aparte en vez
    de parte del mismo logo.

    La imagen final se recorta a su contenido real (sin el margen
    transparente del lienzo completo) para que, puesto con
    `compound="left"` junto al texto, quede pegado a él en vez de con un
    hueco de por medio.
    """
    img = _toolbox_glyph(_hex_to_rgba(color_hex), line_w_factor)
    bbox = img.getbbox()
    if bbox:
        pad = _SIZE * _SCALE * 0.015  # margen mínimo, no cero, para no cortar el trazo
        left, top, right, bottom = bbox
        left = max(0, left - pad)
        top = max(0, top - pad)
        right = min(img.width, right + pad)
        bottom = min(img.height, bottom + pad)
        img = img.crop((int(left), int(top), int(right), int(bottom)))

    final_w = max(1, round(img.width / _SCALE))
    final_h = max(1, round(img.height / _SCALE))
    img = img.resize((final_w, final_h), Image.LANCZOS)
    return ctk.CTkImage(light_image=img, dark_image=img, size=(final_w, final_h))

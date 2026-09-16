"""Iconos sociales minimalistas (GitHub/LinkedIn) generados en runtime con Pillow.

Se generan como glifos simples y discretos (opacidad baja, color neutro) en
vez de depender de assets binarios externos, cumpliendo el requisito de un
footer de marca de agua que no distraiga de la experiencia principal.

Sin fondo: son solo el ícono flotando (fg_color="transparent" en el botón que
los usa). El "breathing pulse" periférico se logra variando el canal alfa de
la propia imagen -- no el color del botón -- porque un botón sin fondo no
tiene ningún rectángulo de color que animar sin reintroducir el fondo que se
pidió quitar.
"""

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont

# Un poco más de opacidad que antes (pedido explícito del usuario para que
# se noten más), sin llegar a colores de marca: siguen siendo grises neutros.
# El alpha (4to valor) es la opacidad BASE al 100% del pulso; los frames
# intermedios del pulso escalan este valor hacia abajo.
_NEUTRAL_DARK = (170, 170, 178, 235)   # gris neutro, para modo oscuro
_NEUTRAL_LIGHT = (90, 90, 98, 235)     # gris neutro, para modo claro
_SIZE = 34  # un poco más grandes (pedido explícito del usuario)


def _load_font(size: int):
    for name in ("Arial Bold.ttf", "Arial.ttf", "ArialMT.ttf", "Helvetica.ttc"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _base_image(scale: int = 4):
    # Se dibuja a varias veces el tamaño final y se reduce con Image.LANCZOS
    # al terminar (supersampling): así los bordes curvos quedan suaves en
    # vez de dentados, ya que ImageDraw no antialiasea sus formas.
    return Image.new("RGBA", (_SIZE * scale, _SIZE * scale), (0, 0, 0, 0))


def _downsample(img: Image.Image) -> Image.Image:
    return img.resize((_SIZE, _SIZE), Image.LANCZOS)


# Silueta exacta del ícono oficial "mark-github" de Octicons (GitHub, MIT
# License) -- el mismo glifo que GitHub usa en su propio header y favicon.
# La silueta anterior (óvalo + orejas + patas dibujados a mano) no se parecía
# al logo real. En vez de aproximar la forma a ojo, se tomó el path SVG
# oficial (viewBox 16x16) y se aplanaron sus curvas bézier/arcos a un
# polígono de 201 puntos con la librería `svg.path` -- un paso único hecho
# una sola vez para generar esta constante, no una dependencia del proyecto
# (no aparece en requirements.txt; el polígono ya resuelto es lo único que
# queda acá).
_GITHUB_MARK_POINTS_16 = [
    (8.0, 0.0), (6.39, 0.16), (4.89, 0.63), (3.53, 1.37), (2.34, 2.34), (1.37, 3.53), (0.63, 4.89),
    (0.16, 6.39), (0.0, 8.0), (0.1, 9.3), (0.41, 10.53), (0.89, 11.68), (1.54, 12.73), (2.34, 13.66),
    (3.27, 14.45), (4.32, 15.1), (5.47, 15.59), (5.61, 15.6), (5.72, 15.59), (5.82, 15.56), (5.89, 15.51),
    (5.95, 15.44), (5.99, 15.37), (6.01, 15.29), (6.02, 15.21), (6.02, 15.12), (6.02, 14.99), (6.02, 14.83),
    (6.01, 14.64), (6.01, 14.44), (6.01, 14.21), (6.01, 13.97), (6.01, 13.72), (5.32, 13.8), (4.76, 13.79),
    (4.32, 13.7), (3.97, 13.56), (3.71, 13.37), (3.53, 13.17), (3.4, 12.96), (3.32, 12.78), (3.27, 12.67),
    (3.2, 12.53), (3.11, 12.37), (3.0, 12.2), (2.89, 12.03), (2.76, 11.87), (2.63, 11.74), (2.5, 11.65),
    (2.39, 11.58), (2.29, 11.51), (2.2, 11.42), (2.14, 11.33), (2.12, 11.25), (2.17, 11.19), (2.29, 11.14),
    (2.49, 11.12), (2.72, 11.14), (2.93, 11.21), (3.12, 11.31), (3.29, 11.44), (3.43, 11.57), (3.55, 11.71),
    (3.65, 11.84), (3.72, 11.94), (4.01, 12.32), (4.32, 12.58), (4.65, 12.74), (4.98, 12.8), (5.3, 12.8),
    (5.59, 12.76), (5.85, 12.68), (6.05, 12.6), (6.08, 12.41), (6.13, 12.24), (6.18, 12.09), (6.25, 11.95),
    (6.32, 11.82), (6.39, 11.71), (6.47, 11.61), (6.56, 11.53), (5.89, 11.43), (5.24, 11.26), (4.63, 11.0),
    (4.07, 10.63), (3.6, 10.12), (3.24, 9.46), (3.0, 8.62), (2.92, 7.58), (2.93, 7.26), (2.98, 6.96),
    (3.04, 6.67), (3.14, 6.39), (3.26, 6.13), (3.4, 5.88), (3.56, 5.65), (3.74, 5.43), (3.7, 5.33),
    (3.66, 5.17), (3.61, 4.96), (3.58, 4.71), (3.58, 4.41), (3.61, 4.08), (3.69, 3.71), (3.82, 3.31),
    (3.85, 3.3), (3.95, 3.29), (4.11, 3.3), (4.35, 3.33), (4.65, 3.42), (5.03, 3.57), (5.49, 3.8),
    (6.02, 4.13), (6.26, 4.07), (6.51, 4.01), (6.75, 3.97), (7.01, 3.93), (7.26, 3.9), (7.51, 3.88),
    (7.77, 3.86), (8.02, 3.86), (8.27, 3.86), (8.53, 3.88), (8.78, 3.9), (9.03, 3.93), (9.29, 3.97),
    (9.53, 4.01), (9.78, 4.07), (10.02, 4.13), (10.55, 3.8), (11.01, 3.56), (11.39, 3.41), (11.69, 3.33),
    (11.93, 3.3), (12.09, 3.29), (12.19, 3.3), (12.22, 3.31), (12.35, 3.71), (12.43, 4.08), (12.46, 4.41),
    (12.46, 4.71), (12.43, 4.96), (12.38, 5.17), (12.34, 5.33), (12.3, 5.43), (12.48, 5.65), (12.64, 5.88),
    (12.78, 6.12), (12.9, 6.38), (13.0, 6.66), (13.06, 6.95), (13.11, 7.26), (13.12, 7.58), (13.04, 8.62),
    (12.8, 9.46), (12.43, 10.13), (11.96, 10.63), (11.41, 11.0), (10.79, 11.26), (10.14, 11.43), (9.47, 11.53),
    (9.58, 11.63), (9.68, 11.76), (9.77, 11.91), (9.85, 12.08), (9.92, 12.28), (9.97, 12.5), (10.0, 12.74),
    (10.01, 13.01), (10.01, 13.4), (10.01, 13.77), (10.01, 14.11), (10.0, 14.41), (10.0, 14.68), (10.0, 14.9),
    (10.0, 15.08), (10.0, 15.21), (10.01, 15.29), (10.03, 15.37), (10.07, 15.44), (10.12, 15.51), (10.2, 15.56),
    (10.3, 15.59), (10.41, 15.61), (10.55, 15.59), (11.7, 15.1), (12.75, 14.44), (13.69, 13.62), (14.5, 12.67),
    (15.14, 11.61), (15.61, 10.45), (15.9, 9.24), (16.0, 8.0), (15.84, 6.39), (15.37, 4.89), (14.63, 3.53),
    (13.66, 2.34), (12.47, 1.37), (11.11, 0.63), (9.61, 0.16), (8.0, 0.0),
]


def _github_glyph(rgba) -> Image.Image:
    """Silueta exacta del logo de GitHub (ver `_GITHUB_MARK_POINTS_16`),
    escalada y centrada con un margen chico."""
    scale = 4
    img = _base_image(scale)
    draw = ImageDraw.Draw(img)
    s = _SIZE * scale
    margin = s * 0.06
    span = s - 2 * margin

    points = [(margin + x / 16 * span, margin + y / 16 * span) for x, y in _GITHUB_MARK_POINTS_16]
    draw.polygon(points, fill=rgba)

    return _downsample(img)


def _linkedin_glyph(rgba) -> Image.Image:
    """Insignia cuadrada con esquinas redondeadas y el texto "in" en
    negativo (recortado, no dibujado encima) -- la silueta real del logo de
    LinkedIn, solo que en el tono neutro y discreto que pide el manual en
    vez del azul de marca de LinkedIn."""
    scale = 4
    img = _base_image(scale)
    draw = ImageDraw.Draw(img)
    s = _SIZE * scale
    margin = s * 0.06

    draw.rounded_rectangle((margin, margin, s - margin, s - margin), radius=s * 0.22, fill=rgba)

    font = _load_font(int(s * 0.5))
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).text((s / 2, s / 2 + s * 0.02), "in", font=font, fill=255, anchor="mm")
    img.paste((0, 0, 0, 0), (0, 0), mask)

    return _downsample(img)


def _coffee_glyph(rgba) -> Image.Image:
    """Taza de café con asa y vapor -- la silueta genérica que representa
    "Buy Me a Coffee" (su propio ícono combina dos "C" en el asa y el vapor,
    pero al ser una marca mucho menos rígida que el logo de GitHub, una
    taza clásica con asa + vapor ya se lee de inmediato como lo que es)."""
    scale = 4
    img = _base_image(scale)
    draw = ImageDraw.Draw(img)
    s = _SIZE * scale
    line_w = max(2, int(s * 0.06))

    # Cuerpo: trapecio (más angosto abajo, como una taza real) vía polígono.
    cup_top_y, cup_bottom_y = s * 0.42, s * 0.82
    cup_top_l, cup_top_r = s * 0.22, s * 0.68
    cup_bottom_l, cup_bottom_r = s * 0.27, s * 0.63
    draw.line((cup_top_l, cup_top_y, cup_bottom_l, cup_bottom_y), fill=rgba, width=line_w)
    draw.line((cup_top_r, cup_top_y, cup_bottom_r, cup_bottom_y), fill=rgba, width=line_w)
    draw.arc(
        (cup_bottom_l - s * 0.02, cup_bottom_y - s * 0.10, cup_bottom_r + s * 0.02, cup_bottom_y + s * 0.06),
        start=20, end=160, fill=rgba, width=line_w,
    )
    draw.line((cup_top_l, cup_top_y, cup_top_r, cup_top_y), fill=rgba, width=line_w)

    # Asa: un arco "C" saliendo del lado derecho de la taza.
    handle_l, handle_r = cup_top_r - s * 0.03, cup_top_r + s * 0.20
    handle_t, handle_b = cup_top_y + s * 0.04, cup_top_y + s * 0.28
    draw.arc((handle_l, handle_t, handle_r, handle_b), start=300, end=240, fill=rgba, width=line_w)

    # Vapor: dos trazos ondulados arriba de la taza (dos arcos en "s").
    for dx in (-s * 0.09, s * 0.09):
        cx = s * 0.45 + dx
        draw.arc((cx - s * 0.05, s * 0.10, cx + s * 0.05, s * 0.22), start=200, end=20, fill=rgba, width=max(2, line_w - 1))
        draw.arc((cx - s * 0.05, s * 0.20, cx + s * 0.05, s * 0.32), start=20, end=200, fill=rgba, width=max(2, line_w - 1))

    return _downsample(img)


def make_social_icons() -> dict:
    """Devuelve CTkImage listas para usar en botones, con variante light/dark."""
    return {
        "github": ctk.CTkImage(
            light_image=_github_glyph(_NEUTRAL_LIGHT),
            dark_image=_github_glyph(_NEUTRAL_DARK),
            size=(_SIZE, _SIZE),
        ),
        "linkedin": ctk.CTkImage(
            light_image=_linkedin_glyph(_NEUTRAL_LIGHT),
            dark_image=_linkedin_glyph(_NEUTRAL_DARK),
            size=(_SIZE, _SIZE),
        ),
        "coffee": ctk.CTkImage(
            light_image=_coffee_glyph(_NEUTRAL_LIGHT),
            dark_image=_coffee_glyph(_NEUTRAL_DARK),
            size=(_SIZE, _SIZE),
        ),
    }


def _with_alpha(rgba: tuple, factor: float) -> tuple:
    r, g, b, a = rgba
    return (r, g, b, round(a * factor))


def make_social_icon_pulse_frames(name: str, steps: int = 10, min_factor: float = 0.55) -> list:
    """Pre-renderiza `steps` variantes de un ícono con distinta opacidad, de
    `min_factor` a 1.0 y de vuelta -- los frames de un "breathing pulse" que
    anima el canal alfa de la imagen en sí, no el fondo del botón (que no
    existe: el botón es `fg_color="transparent"`).

    Devuelve una lista de CTkImage lista para ciclar con `.configure(image=)`.
    """
    glyph_fn = {"github": _github_glyph, "linkedin": _linkedin_glyph, "coffee": _coffee_glyph}[name]
    frames = []
    for i in range(steps):
        # Onda triangular 0..1..0 a lo largo de los steps, para un loop suave.
        phase = i / (steps - 1)
        wave = 1 - abs(2 * phase - 1)  # 0 -> 1 -> 0
        factor = min_factor + (1 - min_factor) * wave
        frames.append(
            ctk.CTkImage(
                light_image=glyph_fn(_with_alpha(_NEUTRAL_LIGHT, factor)),
                dark_image=glyph_fn(_with_alpha(_NEUTRAL_DARK, factor)),
                size=(_SIZE, _SIZE),
            )
        )
    return frames

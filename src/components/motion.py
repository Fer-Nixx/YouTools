"""Utilidades de animación compartidas (pulido de interacción).

CustomTkinter/Tkinter no tienen transiciones CSS, WAAPI ni un compositor con
easing nativo: la única forma de animar algo sin bloquear la UI es
recalcular un valor a mano en varios pasos discretos con `.after()`. Este
módulo centraliza ese patrón (antes vivía duplicado dentro de
`AnimatedFormatToggle`) para que cualquier botón/etiqueta de la app pueda
usarlo igual.

Traducción de las reglas de la skill de animación a lo que Tkinter puede
sostener con fluidez:
- Sin "transition: all" ni curvas inventadas: una sola curva ease-out
  reutilizada (`ease_out`), la misma familia que pide la skill para
  hover/color cuando se anima en pasos discretos en vez de con un motor de
  interpolación continuo.
- Nunca ease-in en UI: todas las curvas de aquí son ease-out.
- Duraciones cortas (140-180ms) para hover, porque el hover ocurre decenas
  de veces por sesión ("tens of times/day" -> rápido y sutil, o nada).
- Las transiciones parten siempre del valor actual (se lee `cget(...)` en
  vivo antes de animar), no del valor lógico "de reposo": si el usuario
  vuelve a pasar el mouse a mitad de una animación, esta se retoma desde
  donde está en pantalla en vez de saltar. Es el equivalente en Tkinter a
  "las transiciones (no keyframes) retoman desde el valor actual".

Límite conocido: como no hay verdadero canal alfa en Tkinter, "opacidad" se
simula interpolando el color hacia/desde el color de fondo real detrás del
widget (ver `TextFade`). Y como cada paso de la animación fija un color hex
concreto (no una tupla claro/oscuro), un widget recién animado deja de
seguir automáticamente un cambio de tema hasta que se reconstruya -- mismo
límite que ya asumía `AnimatedFormatToggle`, aceptable porque las vistas de
esta app se reconstruyen por completo al cambiar de pantalla o de tema.
"""

from typing import Callable, Optional, Tuple, Union

import customtkinter as ctk
from ..config import COLORS

ColorLike = Union[str, Tuple[str, str]]


def lerp_color(start: str, end: str, t: float) -> str:
    """Interpola linealmente entre dos colores hex ('#RRGGBB').
    Si alguno es "transparent", usa el otro directamente.

    Cada canal se acota a [0, 255] después de mezclar (no `t` antes): un
    spring con overshoot (`spring_ease` con damping < 1.0) devuelve a
    propósito un `t` fuera de [0, 1] cerca del final para dar sensación de
    peso, y sin este clamp por canal un valor fuera de 0-255 rompería el
    formato hex. Acotar por canal en vez de acotar `t` deja que el
    overshoot SÍ se note (el color se satura en su límite y vuelve) en vez
    de simplemente desaparecer."""
    if start == "transparent":
        return end
    if end == "transparent":
        return start
    start_rgb = tuple(int(start.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
    end_rgb = tuple(int(end.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
    mixed = (max(0, min(255, round(s + (e - s) * t))) for s, e in zip(start_rgb, end_rgb))
    return "#{:02x}{:02x}{:02x}".format(*mixed)


def ease_out(t: float) -> float:
    """Ease-out cuadrático: arranca rápido y se asienta suave. Es la curva
    que pide la skill para hover/cambios de color en vez de un paso lineal
    (que se siente mecánico) o ease-in (prohibido en UI: retrasa el
    instante que el usuario ya está mirando)."""
    return 1 - (1 - t) ** 2


def spring_ease(t: float, damping: float = 0.8, stiffness: float = 1.2) -> float:
    """Spring damped: simula la física de un resorte táctil para interacciones
    que se sienten con peso real, no lineales.

    Parámetros (Apple-style):
    - damping: 0.0–1.0. 1.0 = sin overshoot (critically damped, suave).
               < 1.0 = overshoot suave (más "juguetón", más peso).
    - stiffness: controla qué tan rápido viaja el spring. Mayor = snappier.

    Ejemplo: damping=0.8, stiffness=1.2 = un poco de bounce con respuesta rápida.

    BUG CORREGIDO (no repetir): la versión anterior calculaba
    `base_progress = t ** exponente`, que con damping=1.0 se reduce
    exactamente a `t²` -- una curva EASE-IN pura (arranca lento, acelera al
    final), lo opuesto de lo que pide la skill de animación para una entrada
    ("Never ease-in on UI"). En la práctica esto hacía que, por ejemplo, la
    vista del conversor se quedara pegada casi invisible junto al borde
    derecho durante la mayor parte de la transición y apareciera de golpe
    en el último tramo -- el "pantallazo vacío antes de que cargue" que
    reportó el usuario. La forma correcta de una curva ease-out (con o sin
    resorte) es `1 - (1-t) ** exponente`, la misma familia que `ease_out()`
    arriba, no `t ** exponente`. Además, el `min(1.0, ...)` de la versión
    anterior recortaba cualquier overshoot real, así que el "efecto resorte"
    pedido tampoco se sentía nunca -- se quita ese clamp: un spring de
    verdad se pasa un poco de su destino y vuelve.
    """
    if damping >= 1.0:
        # Critically damped: ease-out cuadrático puro, sin rebote -- igual
        # que `ease_out()`. Es el caso de `ViewTransition` y el hover de
        # `ToolCard`: una posición o un color no deberían "pasarse" de su
        # destino.
        return 1.0 - (1.0 - t) ** 2.0

    # damping < 1.0: curva "ease-out-back" (la misma familia que usan las
    # librerías de animación para un resorte con rebote) -- se acerca a 1.0
    # más rápido que el caso crítico y lo sobrepasa un poco antes de volver,
    # en vez de solo desacelerar. `c1` escala qué tan pronunciado es ese
    # rebote: a menos damping, más "energía" sobrante y más rebote.
    c1 = (1.0 - damping) * 6.0 * stiffness / 1.2
    c3 = c1 + 1.0
    ts = t - 1.0
    return 1.0 + c3 * ts**3 + c1 * ts**2


def resolve_for_mode(color: ColorLike) -> str:
    """Convierte un color (hex plano, o tupla (claro, oscuro)) al hex que
    corresponde al modo de apariencia activo ahora mismo."""
    if isinstance(color, str):
        return color
    light, dark = color
    return dark if ctk.get_appearance_mode() == "Dark" else light


def _effective_color(widget, color: ColorLike) -> str:
    """Como `resolve_for_mode`, pero resuelve "transparent" al color de
    fondo real que hay detrás del widget -- mismo criterio que usa
    customtkinter internamente (`ctk_button.py:_on_leave`) para decidir a
    qué color volver cuando `fg_color` es "transparent"."""
    hexed = resolve_for_mode(color)
    if hexed == "transparent":
        return resolve_for_mode(widget.cget("bg_color"))
    return hexed


class StepAnimator:
    """Corre una animación por pasos con `.after()`: dueño único del loop y
    de la guarda "el widget se destruyó a mitad de camino" que antes vivía
    copiada en `ColorTransition`, `TextFade`, `ViewTransition`,
    `AnimatedFormatToggle` y `ToolCard` (candidato 1 del reporte de
    arquitectura).

    No sabe nada de colores, easing ni curvas -- eso lo sigue decidiendo el
    llamador en `on_step`. Reutilizable: una misma instancia cancela su
    propia corrida anterior cada vez que se llama `run()` de nuevo, igual
    que ya hacía cada clase con su `self._job`.

    `IconPulse` (loop infinito de "respiración", sin curva ni fin) queda
    fuera a propósito: es un único caso de uso con una forma distinta, y
    forzarlo en este mismo driver sería un seam hipotético.
    """

    def __init__(self, widget):
        self._widget = widget
        self._job = None

    def run(
        self,
        steps: int,
        duration_ms: int,
        on_step: Callable[[int], None],
        on_done: Optional[Callable[[], None]] = None,
    ) -> None:
        """Llama `on_step(i)` para `i` en `0..steps` (ambos incluidos),
        espaciados por `max(1, duration_ms // steps)` ms -- misma fórmula
        que usaban las cinco clases antes de converger acá. Si el widget se
        destruye a mitad de camino, deja de llamar `on_step`/`on_done`."""
        if self._job is not None:
            self._widget.after_cancel(self._job)
            self._job = None

        delay = max(1, duration_ms // steps)

        def step(i=0):
            if not self._widget.winfo_exists():
                self._job = None
                return
            on_step(i)
            if i < steps:
                self._job = self._widget.after(delay, step, i + 1)
            else:
                self._job = None
                if on_done:
                    on_done()

        step()


class ColorTransition:
    """Reemplaza el cambio de color instantáneo de hover/leave de
    customtkinter por una transición corta y sutil.

    El widget debe crearse con `hover=False` (los CTkButton) para que
    customtkinter no compita por el mismo color -- ver `attach_hover`.
    """

    DURATION_MS = 150
    STEPS = 8

    def __init__(self, widget, base_color: ColorLike, hover_color: ColorLike):
        self._widget = widget
        self._base = base_color
        self._hover = hover_color
        self._animator = StepAnimator(widget)

        targets = [
            t
            for t in (
                getattr(widget, "_canvas", None),
                getattr(widget, "_text_label", None),
                getattr(widget, "_image_label", None),
            )
            if t is not None
        ] or [widget]

        for target in targets:
            target.bind("<Enter>", self._on_enter, add="+")
            target.bind("<Leave>", self._on_leave, add="+")

    def retarget(self, base_color: ColorLike, hover_color: ColorLike) -> None:
        """Actualiza los colores base/hover en caliente (p.ej. cuando un
        botón de navegación pasa a ser el activo): la transición en curso,
        si hay una, sigue viva y toma los colores nuevos desde el próximo
        hover/leave."""
        self._base = base_color
        self._hover = hover_color

    def _on_enter(self, _event=None):
        self._animate_to(self._hover)

    def _on_leave(self, _event=None):
        self._animate_to(self._base)

    def _animate_to(self, target_color: ColorLike) -> None:
        start_hex = _effective_color(self._widget, self._widget.cget("fg_color"))
        end_hex = _effective_color(self._widget, target_color)

        def on_step(i):
            t = ease_out(i / self.STEPS)
            self._widget.configure(fg_color=lerp_color(start_hex, end_hex, t))

        def on_done():
            self._widget.configure(fg_color=end_hex)

        # La guarda de "widget destruido a mitad de camino" (típico: el
        # mouse sale de un botón del sidebar justo cuando se navega a otra
        # pantalla) vive en `StepAnimator`, no acá.
        self._animator.run(self.STEPS, self.DURATION_MS, on_step, on_done)


def attach_hover(widget, base_color: ColorLike, hover_color: ColorLike) -> ColorTransition:
    """Engancha una transición de color suave de hover a un widget que se
    construyó con `hover=False`. Devuelve el `ColorTransition` por si el
    llamador necesita retocar los colores después (`.retarget(...)`)."""
    return ColorTransition(widget, base_color, hover_color)


class TextFade:
    """Funde el texto de un CTkLabel al cambiar de contenido.

    Tkinter no tiene canal alfa real, así que "opacidad" se simula
    interpolando el COLOR del texto: se apaga hacia el color de fondo real
    (queda invisible sin dejar de ocupar su lugar), se cambia el texto, y se
    enciende desde ahí hacia el color final. Pensado para feedback de
    estado ocasional (no docenas de veces por sesión), así que la duración
    total (~180-200ms) es la de un cambio de estado normal, no la de un
    hover.
    """

    OUT_MS = 90
    IN_MS = 110
    STEPS = 6

    def __init__(self, label, bg_resolver: Callable[[], str]):
        self._label = label
        self._bg_resolver = bg_resolver
        self._animator = StepAnimator(label)

    def to(self, text: str, color: ColorLike) -> None:
        bg_hex = self._bg_resolver()
        current_hex = resolve_for_mode(self._label.cget("text_color"))
        target_hex = resolve_for_mode(color)
        same_text = self._label.cget("text") == text

        def fade(start: str, end: str, duration: int, on_done: Optional[Callable] = None):
            def on_step(i):
                t = ease_out(i / self.STEPS)
                self._label.configure(text_color=lerp_color(start, end, t))

            def fade_done():
                self._label.configure(text_color=end)
                if on_done:
                    on_done()

            # Misma guarda que en ColorTransition (ahora en `StepAnimator`):
            # si la vista ya se destruyó (p.ej. el usuario navegó a otra
            # pantalla a mitad de una descarga), no tocar el label.
            self._animator.run(self.STEPS, duration, on_step, fade_done)

        if same_text:
            # Solo cambia el color (p.ej. de error a normal con el mismo
            # texto): un único fundido directo, sin pasar por el fondo, así
            # no hay un parpadeo de por medio que nadie pidió.
            fade(current_hex, target_hex, self.IN_MS)
            return

        def swap_and_fade_in():
            self._label.configure(text=text)
            fade(bg_hex, target_hex, self.IN_MS)

        fade(current_hex, bg_hex, self.OUT_MS, on_done=swap_and_fade_in)


class IconPulse:
    """Animación "breathing" infinita para un ícono SIN fondo (botón
    `fg_color="transparent"`): en vez de animar el color de un rectángulo de
    fondo -- que no existe, y crearlo de nuevo sería reintroducir el fondo
    que se quitó a propósito -- cicla entre frames pre-renderizados de la
    propia imagen a distinta opacidad (canal alfa real de la imagen).

    Uso: `IconPulse(button, frames)`, donde `frames` viene de
    `social_icons.make_social_icon_pulse_frames(...)`.
    """

    def __init__(self, button, frames: list, cycle_ms: int = 12000):
        self._button = button
        self._frames = frames
        self._cycle_ms = cycle_ms
        self._job = None
        self._start()

    def _start(self):
        steps = len(self._frames)
        delay_ms = max(1, self._cycle_ms // steps)

        def step(i=0):
            if not self._button.winfo_exists():
                self._job = None
                return
            self._button.configure(image=self._frames[i % steps])
            self._job = self._button.after(delay_ms, step, i + 1)

        step()

    def stop(self):
        if self._job is not None:
            self._button.after_cancel(self._job)
            self._job = None


class ViewTransition:
    """Transición de vista estilo Apple: el panel de CONTENIDO se desliza
    desde fuera de pantalla hasta su lugar -- el sidebar se queda fijo y
    nunca se cubre, igual que en Ajustes del Sistema en macOS (el panel
    izquierdo no se mueve cuando cambia lo que muestra el panel derecho).

    `view_widget` debe ser hijo de un contenedor que YA esté en `grid()` en
    la columna de contenido de la app (ver `App._content` en `app.py`), no
    de la ventana completa -- así la animación no necesita saber nada del
    ancho del sidebar ni del tamaño de la ventana: siempre trabaja en
    coordenadas relativas (`relx`, 0.0 a 1.0) al contenedor.

    Historial de bugs de esta clase (para no repetirlos):
    - Una versión posicionaba la vista con
      `place(x=0, ..., relwidth=1, relheight=1)` relativo a TODA la
      ventana de la app -- cubría también la columna del sidebar (`place`
      no respeta celdas de grid, dibuja encima de lo que haya ahí). Al
      abrir el conversor, el sidebar desaparecía y no había forma de
      volver atrás.
    - La corrección de eso acotaba la animación al área de contenido a
      mano (con `content_x`/`window_width` como parámetros) y, al
      terminar, cambiaba el widget de `.place()` a `.grid()` para que
      siguiera el resize de la ventana. Confirmado con capturas en cámara
      lenta (comparando cada frame real, no solo a velocidad normal): ese
      cambio de gestor de geometría -- de `place` a `grid`, sin importar
      si se llama `place_forget()` antes o no -- hace que el widget
      desaparezca por completo durante un frame real en esta combinación
      de Tk/customtkinter en macOS. Era el "segundo parpadeo, después de
      cargar bien" que se reportó.

    La solución de fondo (esta versión): el widget NUNCA cambia de gestor
    de geometría. Vive en `place()` desde que se crea hasta que se destruye,
    animado o quieto, dentro de un contenedor que sí está en `grid()` y que
    responde al resize por su cuenta -- `relwidth=1, relheight=1` hace que
    la vista siempre ocupe el 100% de ese contenedor.
    """

    DURATION_MS = 300
    STEPS = 20

    def __init__(self, view_widget):
        self._view = view_widget
        self._animator = StepAnimator(view_widget)

    def animate_in(self):
        """Anima la vista entrante desde la derecha, en coordenadas
        relativas al contenedor (`relx` 1.0 -> 0.0). Nunca cambia de gestor
        de geometría: sigue en `place()` una vez terminada la animación."""

        def on_step(i):
            t = spring_ease(i / self.STEPS, damping=1.0, stiffness=1.2)
            # relx=1.0 -> completamente fuera del contenedor, a la derecha.
            # relx=0.0 -> posición final, alineada con el contenedor.
            relx = 1.0 - t
            self._view.place(relx=relx, rely=0, relwidth=1.0, relheight=1.0)

        def on_done():
            self._view.place(relx=0, rely=0, relwidth=1.0, relheight=1.0)

        self._view.place(relx=1.0, rely=0, relwidth=1.0, relheight=1.0)
        self._animator.run(self.STEPS, self.DURATION_MS, on_step, on_done)

"""Componentes de botones reutilizables que respetan la identidad visual de YouTools."""

import customtkinter as ctk

from ..config import COLORS, Fonts
from .motion import StepAnimator, attach_hover, ease_out, spring_ease, lerp_color

_CTA_HOVER = "#D8DE4E"


class CTAButton(ctk.CTkButton):
    """Botón de acción principal.

    Regla de contraste crítica del manual: fondo Canary Yellow -> texto
    Shadow Grey, nunca texto blanco sobre amarillo.

    El hover funde el color en ~150ms en vez del cambio instantáneo por
    defecto de customtkinter (`hover=False` apaga ese mecanismo interno
    para que no compita con la transición propia -- ver `motion.py`).
    """

    def __init__(self, master, text: str, command=None, width=240, height=48, font=None, **kwargs):
        super().__init__(
            master,
            text=text,
            command=command,
            width=width,
            height=height,
            corner_radius=height // 2,
            fg_color=COLORS["canary_yellow"],
            hover=False,
            text_color=COLORS["shadow_grey"],
            font=font or Fonts.BUTTON,
            **kwargs,
        )
        attach_hover(self, COLORS["canary_yellow"], _CTA_HOVER)


class SegmentedToggle(ctk.CTkSegmentedButton):
    """Toggle suave para elegir formato (MP3 / MP4), acentuado en Tiger Orange.

    CTkSegmentedButton usa un único `text_color` para todos los segmentos (no
    hay texto distinto por segmento seleccionado/no seleccionado). Por eso se
    fija texto Shadow Grey de forma constante y un fondo claro constante para
    el segmento inactivo: así se cumple la combinación permitida por el
    manual (Tiger Orange + Shadow Grey) en el segmento activo, y se mantiene
    contraste AA en el inactivo, en ambos temas.
    """

    def __init__(self, master, values, command=None, **kwargs):
        super().__init__(
            master,
            values=values,
            command=command,
            selected_color=COLORS["tiger_orange"],
            selected_hover_color=COLORS["tiger_orange"],
            unselected_color=COLORS["surface_light"],
            unselected_hover_color="#D5D5DA",
            text_color=COLORS["shadow_grey"],
            font=Fonts.BODY,
            corner_radius=18,
            height=40,
            **kwargs,
        )


class AnimatedFormatToggle(ctk.CTkFrame):
    """Selector de formato grande y centrado (MP3/MP4).

    Cada opción es su propio "chip": el seleccionado se pinta Tiger Orange
    (con texto Shadow Grey encima, la combinación que exige el manual) y el
    resto queda en el color base, para que sea evidente cuál está activo.
    Al cambiar de opción ambos chips funden su color en paralelo, dando
    sensación de deslizamiento.

    Nota: una versión anterior dibujaba una "píldora" de color aparte, por
    debajo de dos etiquetas de texto superpuestas con fg_color="transparent".
    CustomTkinter no compone esa transparencia como una capa real entre
    widgets hermanos (cada widget pinta un rectángulo opaco propio), así que
    la píldora quedaba completamente tapada por las etiquetas y no se podía
    distinguir qué formato estaba seleccionado. Aquí el color y el texto
    viven en el mismo widget (cada chip es su propio CTkLabel con fg_color
    animado), así que no hay nada que lo pueda tapar.

    El fondo "apagado" también depende del tema: antes estaba fijo en un gris
    claro, así que en modo oscuro aparecía como un bloque blanco flotando
    sobre el resto de la UI oscura. Como el color se anima manualmente (no es
    un color estático de customtkinter), se resuelve una sola vez contra el
    modo de apariencia activo al construir el widget.
    """

    _OFF_LIGHT = COLORS["surface_light"]
    _OFF_DARK = "#2A2A31"  # mismo tono que el resto de campos/menús en oscuro
    _ON_COLOR = COLORS["tiger_orange"]

    def __init__(
        self, master, values=("MP3", "MP4"), command=None,
        width=300, height=56, font=None, icons=None, fluid=False, **kwargs
    ):
        """
        icons: opcional, lista alineada con `values` de tuplas
            `(imagen_apagada, imagen_encendida)` (CTkImage) o `None` para esa
            opción. Cuando se da, cada chip muestra el ícono a la izquierda
            del texto (`compound="left"`) y cambia de variante junto con el
            color de texto -- la misma apagada/Shadow Grey que ya usa el
            texto, para que el ícono nunca quede con contraste pobre.
        fluid: si es True, el toggle no se queda en `width` para siempre --
            se estira para ocupar el ancho real de su contenedor (colocarlo
            con `.grid(sticky="ew")`, no `.pack()`) y recalcula el ancho de
            cada chip cada vez que ese contenedor cambia de tamaño. Pensado
            para un toggle que debe sentirse "protagonista" dentro de una
            tarjeta (llenarla), no un control chico flotando en el medio con
            espacio vacío alrededor -- el MP3/MP4 del conversor sigue fijo
            (`fluid=False`, el default) porque ahí sí se quiere un tamaño
            constante y centrado.
        """
        # El método de dibujo global de la app ("font_shapes", ver App.__init__)
        # ya maneja bien tanto los radios grandes (píldoras completas, como
        # esta) como el antialiasing, así que no hace falta forzar un método
        # distinto aquí.
        super().__init__(
            master, height=height, corner_radius=height // 2,
            fg_color=(self._OFF_LIGHT, self._OFF_DARK),
            **kwargs,
        )
        self._fluid = fluid
        if not fluid:
            self.configure(width=width)
            self.grid_propagate(False)

        # Resuelto una sola vez: esta vista se reconstruye por completo al
        # navegar, así que no hace falta escuchar cambios de tema en vivo.
        is_dark = ctk.get_appearance_mode() == "Dark"
        self._off_color = self._OFF_DARK if is_dark else self._OFF_LIGHT
        # Shadow Grey (texto oscuro) tiene buen contraste sobre el fondo
        # apagado en modo claro, pero sobre el fondo oscuro (#2A2A31) queda
        # casi ilegible. El chip seleccionado siempre usa Shadow Grey sobre
        # Tiger Orange (combinación obligatoria del manual); el apagado usa
        # el texto claro del tema en modo oscuro.
        self._off_text_color = COLORS["text_dark"] if is_dark else COLORS["shadow_grey"]

        self._values = list(values)
        self._icons = list(icons) if icons is not None else [None] * len(self._values)
        self._command = command
        self._current_index = 0
        self._pad = 5
        self._segment_width = int((width - 2 * self._pad) / len(self._values))
        self._chip_height = height - 2 * self._pad
        self._animator = StepAnimator(self)
        self._font = font or Fonts.BUTTON

        self._chips = []
        for i, value in enumerate(self._values):
            icon_pair = self._icons[i]
            # CTkLabel no tiene un espaciado configurable entre imagen y
            # texto en `compound="left"`; un espacio en blanco al inicio del
            # texto es el truco simple para que no queden pegados.
            label_text = f" {value}" if icon_pair else value
            chip = ctk.CTkLabel(
                self, text=label_text, font=self._font,
                width=self._segment_width, height=self._chip_height,
                corner_radius=int(self._chip_height // 2),
                fg_color=self._off_color,
                text_color=self._off_text_color,
                image=icon_pair[0] if icon_pair else None,
                compound="left" if icon_pair else "none",
            )
            chip.place(x=self._pad + i * self._segment_width, y=self._pad)
            chip.configure(cursor="pointinghand")
            chip.bind("<Button-1>", lambda e, idx=i: self._select(idx))
            inner_label = getattr(chip, "_label", None)
            if inner_label is not None:
                inner_label.bind("<Button-1>", lambda e, idx=i: self._select(idx))
            self._chips.append(chip)

        first_icon = self._icons[0]
        self._chips[0].configure(
            fg_color=self._ON_COLOR, text_color=COLORS["shadow_grey"],
            image=first_icon[1] if first_icon else None,
        )

        if self._fluid:
            self._last_width = width
            self.bind("<Configure>", self._on_resize)

    def _on_resize(self, event) -> None:
        """Recalcula el ancho de cada chip cuando el contenedor real cambia
        de tamaño -- lo que hace que el toggle "fluid" de verdad llene su
        tarjeta en vez de quedarse en el ancho que tenía al construirse."""
        new_width = event.width
        if new_width <= 1 or new_width == self._last_width:
            return
        self._last_width = new_width
        self._segment_width = int((new_width - 2 * self._pad) / len(self._values))
        for i, chip in enumerate(self._chips):
            chip.configure(width=self._segment_width)
            chip.place(x=self._pad + i * self._segment_width, y=self._pad)

    def get(self) -> str:
        return self._values[self._current_index]

    def set(self, value: str) -> None:
        """Fija el valor sin animar (para el estado inicial o un reset)."""
        if value not in self._values:
            return
        self._current_index = self._values.index(value)
        for i, chip in enumerate(self._chips):
            selected = i == self._current_index
            icon_pair = self._icons[i]
            chip.configure(
                fg_color=self._ON_COLOR if selected else self._off_color,
                text_color=COLORS["shadow_grey"] if selected else self._off_text_color,
                image=(icon_pair[1] if selected else icon_pair[0]) if icon_pair else None,
            )

    def _select(self, index: int) -> None:
        if index == self._current_index:
            return
        self._animate_to(index)
        if self._command:
            self._command(self._values[index])

    # Cambiar de formato es un toggle de preferencia que se toca decenas de
    # veces por sesión, no una acción rara -- se mantiene corto y sutil
    # (~150ms, ease-out) en vez de una animación "de evento" más larga.
    _DURATION_MS = 150
    _STEPS = 8

    def _animate_to(self, index: int) -> None:
        old_index = self._current_index
        self._current_index = index

        # El color de texto cambia de una vez (no se anima junto al fondo):
        # en un fundido tan corto, una breve transición de contraste
        # imperfecto es preferible a la complejidad de interpolar dos
        # colores de texto además del fondo. El ícono (si hay) cambia de
        # variante en el mismo instante, por la misma razón.
        old_icon = self._icons[old_index]
        new_icon = self._icons[index]
        self._chips[old_index].configure(
            text_color=self._off_text_color, image=old_icon[0] if old_icon else None,
        )
        self._chips[index].configure(
            text_color=COLORS["shadow_grey"], image=new_icon[1] if new_icon else None,
        )

        def on_step(i):
            # Spring physics: damping=0.8 (suave overshoot), stiffness=1.2 (responsivo).
            # Se siente como un botón táctil real con peso, no lineal.
            t = spring_ease(i / self._STEPS, damping=0.8, stiffness=1.2)
            self._chips[old_index].configure(fg_color=lerp_color(self._ON_COLOR, self._off_color, t))
            self._chips[index].configure(fg_color=lerp_color(self._off_color, self._ON_COLOR, t))

        def on_done():
            self._chips[old_index].configure(fg_color=self._off_color)
            self._chips[index].configure(fg_color=self._ON_COLOR)

        self._animator.run(self._STEPS, self._DURATION_MS, on_step, on_done)

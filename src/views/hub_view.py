"""Pantalla 2: Hub principal de herramientas (Fase 2 del PRD)."""

import customtkinter as ctk

from ..config import COLORS, Fonts
from ..components.motion import StepAnimator, spring_ease, lerp_color, resolve_for_mode


class ToolCard(ctk.CTkFrame):
    def __init__(self, master, title, description, tag_text, active, on_click=None):
        super().__init__(
            master, corner_radius=20, height=160,
            fg_color=(COLORS["card_light"], COLORS["card_dark"]),
            border_width=1,
            border_color=(COLORS["border_light"], COLORS["border_dark"]),
        )
        self.grid_propagate(False)
        self._active = active
        self._animator = StepAnimator(self)

        # Hover minimalista: la tarjeta activa se "eleva" con un fondo
        # apenas más claro/oscuro que el resto (según tema) en vez de un
        # borde de color llamativo -- un acento naranja saturado en cada
        # tarjeta competía con el resto de la UI y no leía como "elevación",
        # solo como ruido. Este es el mismo lenguaje que usa macOS para filas
        # seleccionables: un cambio de superficie sutil, no de color.
        self._base_fg = (COLORS["card_light"], COLORS["card_dark"])
        self._hover_fg = (COLORS["surface_light"], "#2E2E36")
        if active:
            self.bind("<Enter>", self._on_hover_enter, add="+")
            self.bind("<Leave>", self._on_hover_leave, add="+")

        tag_color = COLORS["tiger_orange"] if active else ("#D5D5DA", "#38383F")
        tag_text_color = (
            COLORS["shadow_grey"]
            if active
            else (COLORS["text_muted_light"], COLORS["text_muted_dark"])
        )

        tag_label = ctk.CTkLabel(
            self, text=tag_text, font=Fonts.SMALL, corner_radius=10,
            fg_color=tag_color, text_color=tag_text_color,
            width=70, height=22,
        )
        tag_label.place(x=18, y=16)

        title_color = (
            (COLORS["text_light"], COLORS["text_dark"])
            if active
            else (COLORS["text_muted_light"], COLORS["text_muted_dark"])
        )

        # Título y descripción se anclan al borde INFERIOR de la tarjeta (en
        # vez de a una coordenada fija cerca del top) para que el espacio
        # sobrante quede siempre arriba, entre la etiqueta y el texto, y no
        # como un vacío al fondo. Así toda tarjeta se ve intencional sin
        # importar si la descripción tiene una o dos líneas -- o ninguna, en
        # las tarjetas "fantasma" que todavía no tienen descripción real.
        text_block = ctk.CTkFrame(self, fg_color="transparent")
        text_block.place(x=18, rely=1.0, y=-18, anchor="sw")

        title_label = ctk.CTkLabel(
            text_block, text=title, font=Fonts.SECTION, text_color=title_color, anchor="w",
        )
        title_label.pack(anchor="w")

        desc_label = None
        if description:
            desc_label = ctk.CTkLabel(
                text_block, text=description, font=Fonts.SMALL, anchor="w", justify="left",
                wraplength=260,
                text_color=(COLORS["text_muted_light"], COLORS["text_muted_dark"]),
            )
            desc_label.pack(anchor="w", pady=(4, 0))

        # Las etiquetas están superpuestas sobre el frame con `.place()` y
        # cubren la mayor parte del área visible de la tarjeta. CTkLabel.bind()
        # solo enlaza su canvas de fondo; el texto en sí lo pinta un
        # tkinter.Label interno (`._label`) que queda encima y se queda sin
        # el evento. Por eso hay que enlazar el clic también a ese label
        # interno, o un clic sobre el texto visible no dispara nada.
        if active and on_click:
            self.configure(cursor="pointinghand")
            clickable = [self, tag_label, text_block, title_label]
            if desc_label is not None:
                clickable.append(desc_label)
            for widget in clickable:
                widget.bind("<Button-1>", lambda e: on_click())
                widget.bind("<Enter>", self._on_hover_enter, add="+")
                widget.bind("<Leave>", self._on_hover_leave, add="+")
                inner_label = getattr(widget, "_label", None)
                if inner_label is not None:
                    inner_label.bind("<Button-1>", lambda e: on_click())
                    inner_label.bind("<Enter>", self._on_hover_enter, add="+")
                    inner_label.bind("<Leave>", self._on_hover_leave, add="+")

    def _animate_fg(self, start: tuple, end: tuple) -> None:
        start_hex = resolve_for_mode(start)
        end_hex = resolve_for_mode(end)
        steps = 8

        def on_step(i):
            t = spring_ease(i / steps, damping=1.0, stiffness=1.2)
            self.configure(fg_color=lerp_color(start_hex, end_hex, t))

        def on_done():
            self.configure(fg_color=end_hex)

        self._animator.run(steps, 130, on_step, on_done)

    def _on_hover_enter(self, _event=None):
        if self._active:
            self._animate_fg(self._base_fg, self._hover_fg)

    def _on_hover_leave(self, _event=None):
        if self._active:
            self._animate_fg(self._hover_fg, self._base_fg)


class HubView(ctk.CTkFrame):
    def __init__(self, master, i18n, on_open_converter):
        super().__init__(master, fg_color=(COLORS["surface_light"], COLORS["shadow_grey"]))
        self.i18n = i18n

        # 2 columnas: con 4 tarjetas en total, 2x2 se ve completo y
        # balanceado.
        self.grid_columnconfigure((0, 1), weight=1, uniform="cards")

        ctk.CTkLabel(
            self, text=self.i18n.t("hub.title"), font=Fonts.TITLE,
            text_color=(COLORS["text_light"], COLORS["text_dark"]),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=36, pady=(32, 20))

        # Tres tarjetas "en desarrollo" idénticas, genéricas y SIN
        # descripción -- antes había tres herramientas específicas de
        # relleno (Video Downloader, Video Editor, Audio Extractor) sin que
        # ninguna estuviera decidida de verdad, y después una sola con una
        # descripción tipo "todavía no decidimos cuál será" que tampoco
        # convencía: ponerle una descripción a algo que ni siquiera existe
        # es más ruido que información. Solo la etiqueta "Próximamente" ya
        # deja claro el estado.
        cards = [
            (
                self.i18n.t("hub.youtube_converter"),
                self.i18n.t("hub.youtube_converter_desc"),
                self.i18n.t("hub.card_active_tag"),
                True,
                on_open_converter,
            ),
        ]
        for _ in range(3):
            cards.append((self.i18n.t("hub.tool_in_development"), "", self.i18n.t("hub.card_soon_tag"), False, None))

        for idx, (title, desc, tag, active, cb) in enumerate(cards):
            row, col = divmod(idx, 2)
            card = ToolCard(self, title, desc, tag, active, cb)
            card.grid(row=row + 1, column=col, padx=16, pady=16, sticky="nsew")

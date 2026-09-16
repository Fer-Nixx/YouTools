"""Pantalla 3: YouTube Converter, el MVP operativo (Fase 3 del PRD)."""

import customtkinter as ctk

from ..config import COLORS, Fonts
from ..components.buttons import CTAButton, AnimatedFormatToggle
from ..components.motion import TextFade, attach_hover, resolve_for_mode
from ..core.conversion_rules import build_quality_options, resolve_max_height, resolve_output_dir
from ..core.downloader import Downloader, QualityProbe, is_valid_youtube_url
from ..core.file_utils import reveal_in_file_manager


class ConverterView(ctk.CTkFrame):
    def __init__(self, master, i18n, settings: dict):
        super().__init__(master, fg_color=(COLORS["surface_light"], COLORS["shadow_grey"]))
        self.i18n = i18n
        self.settings = settings
        self.downloader = Downloader(self._on_progress, self._on_finished)
        self.quality_probe = QualityProbe(self._on_qualities_found)

        self._quality_heights = {}  # label visible -> altura en px (None = mejor disponible)
        self._last_filepath = None
        self._cancelling = False

        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text=self.i18n.t("converter.title"), font=Fonts.TITLE,
            text_color=(COLORS["text_light"], COLORS["text_dark"]),
        ).grid(row=0, column=0, sticky="w", padx=36, pady=(32, 4))

        # Subtítulo de contexto: qué hace la herramienta, de un vistazo, sin
        # tener que inferirlo del formulario. Un escalón más grande que el
        # cuerpo estándar (15 en vez de 13): bajo un título de 28, un
        # subtítulo del mismo tamaño que cualquier etiqueta secundaria se
        # perdía y dejaba la cabecera de la pantalla sintiéndose vacía.
        # `height` explícito y por encima de lo que pide la fuente (18px de
        # linespace medido para 15pt) a propósito: el alto por defecto de
        # CTkLabel (28px) ya alcanza de sobra, pero un margen extra no
        # cuesta nada y descarta de plano cualquier recorte de los
        # descendentes (g, y) contra el borde del canvas del label.
        ctk.CTkLabel(
            self, text=self.i18n.t("converter.subtitle"), font=(Fonts.family, 15, "normal"),
            text_color=(COLORS["text_muted_light"], COLORS["text_muted_dark"]), height=34,
        ).grid(row=1, column=0, sticky="nw", padx=36, pady=(0, 20))

        self.card = ctk.CTkFrame(
            self, corner_radius=24,
            fg_color=(COLORS["card_light"], COLORS["card_dark"]),
            border_width=1,
            border_color=(COLORS["border_light"], COLORS["border_dark"]),
        )
        self.card.grid(row=2, column=0, padx=36, pady=(0, 32), sticky="nsew")
        # La card ahora ocupa todo el espacio vertical restante (antes era
        # "new": alto natural, pegada arriba, dejando un vacío enorme abajo
        # en pantallas grandes -- se sentía como una herramienta flotando
        # dentro de una pantalla que no era suya). Solo esta fila (la de la
        # card) recibe el peso extra -- el título y el subtítulo mantienen
        # su alto natural.
        self.grid_rowconfigure(2, weight=1)
        self.card.grid_columnconfigure(0, weight=1)

        # El contenido real vive en un bloque interno que se centra
        # verticalmente dentro de la card expandida (spacers con weight=1
        # arriba y abajo, ver filas 0 y 2), en vez de quedar pegado al
        # borde superior con un hueco vacío debajo.
        self.card.grid_rowconfigure(0, weight=1)
        self.card.grid_rowconfigure(2, weight=1)
        body = ctk.CTkFrame(self.card, fg_color="transparent")
        body.grid(row=1, column=0, sticky="ew")
        body.grid_columnconfigure(0, weight=1)

        # --- URL ---
        # Antes el placeholder hacía las dos cosas a la vez (instrucción +
        # ejemplo), y como el placeholder desaparece apenas se hace foco en
        # el campo, la instrucción se iba con él. Ahora hay un label fijo
        # arriba que no se mueve, y el placeholder pasa a ser un ejemplo de
        # URL con forma real -- una que a simple vista se lee como un link
        # de YouTube cualquiera, con la marca escondida en el ID del video.
        #
        # OJO: CTkEntry no activa el placeholder si se le pasa un
        # `textvariable` (lo comprobamos por separado: con textvariable el
        # placeholder simplemente no aparece, sin importar el color). Por
        # eso el valor se lee directo del widget con `.get()` en vez de
        # enlazarlo a un StringVar.
        url_section = ctk.CTkFrame(body, fg_color="transparent")
        url_section.grid(row=0, column=0, sticky="ew", padx=36, pady=(32, 20))
        url_section.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            url_section, text=self.i18n.t("converter.url_label"), font=(Fonts.family, 14, "normal"),
            text_color=(COLORS["text_light"], COLORS["text_dark"]), anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        self.url_entry = ctk.CTkEntry(
            url_section,
            placeholder_text="https://www.youtube.com/watch?v=YouT00ls2026",
            height=56, corner_radius=16, font=(Fonts.family, 15, "normal"),
            fg_color=(COLORS["surface_light"], "#2A2A31"),
            border_color=(COLORS["border_light"], COLORS["border_dark"]),
            text_color=(COLORS["text_light"], COLORS["text_dark"]),
            placeholder_text_color=(COLORS["text_muted_light"], COLORS["text_muted_dark"]),
        )
        self.url_entry.grid(row=1, column=0, sticky="ew")

        # --- Formato: grande, centrado, con animación al cambiar ---
        # Sin texto explicativo debajo del título: MP3/MP4 ya lo dice todo
        # para cualquiera que sepa qué es un enlace de YouTube -- deletrear
        # "MP3 es solo audio" trataba al usuario de menos, y esa etiqueta
        # era la parte más "de manual" de toda la pantalla.
        format_section = ctk.CTkFrame(body, fg_color="transparent")
        format_section.grid(row=1, column=0, sticky="ew", padx=28, pady=(8, 28))

        ctk.CTkLabel(
            format_section, text=self.i18n.t("converter.format_label"), font=(Fonts.family, 17, "bold"),
            text_color=(COLORS["text_light"], COLORS["text_dark"]), height=32,
        ).pack(pady=(0, 14))

        self.format_toggle = AnimatedFormatToggle(
            format_section, values=["MP3", "MP4"], command=self._on_format_change,
            width=320, height=60, font=(Fonts.family, 16, "bold"),
        )
        self.format_toggle.set("MP3")
        self.format_toggle.pack()

        # --- Calidad (solo visible para MP4) ---
        # Rediseñada como UNA SOLA cápsula minimalista (antes eran dos
        # piezas sueltas -- un dropdown con su propio marco y un botón con
        # borde propio -- que además se camuflaban contra la card blanca en
        # modo claro por no tener casi contraste con el fondo). Ahora todo
        # comparte el mismo fondo sin bordes internos, así que se lee como
        # una sola superficie con dos zonas de acción, no como controles
        # sueltos flotando.
        _PILL_BG = (COLORS["surface_light"], "#2A2A31")

        self.quality_row = ctk.CTkFrame(body, fg_color="transparent")
        self.quality_row.grid(row=2, column=0, pady=(0, 20))  # sin sticky: centrado

        quality_pill = ctk.CTkFrame(
            self.quality_row, corner_radius=24, fg_color=_PILL_BG,
            border_width=1, border_color=(COLORS["border_light"], COLORS["border_dark"]),
        )
        quality_pill.pack()

        pill_inner = ctk.CTkFrame(quality_pill, fg_color="transparent")
        pill_inner.pack(padx=8, pady=8)

        ctk.CTkLabel(
            pill_inner, text=self.i18n.t("converter.quality_label"), font=(Fonts.family, 13, "normal"),
            text_color=(COLORS["text_muted_light"], COLORS["text_muted_dark"]),
        ).pack(side="left", padx=(16, 12))

        self.quality_var = ctk.StringVar(value=self.i18n.t("converter.quality_best"))
        self.quality_menu = ctk.CTkOptionMenu(
            pill_inner, values=[self.i18n.t("converter.quality_best")],
            variable=self.quality_var, width=180, height=40, corner_radius=20,
            fg_color=_PILL_BG,
            button_color=COLORS["tiger_orange"], button_hover_color=COLORS["tiger_orange"],
            text_color=(COLORS["text_light"], COLORS["text_dark"]),
            dropdown_fg_color=_PILL_BG,
            dropdown_text_color=(COLORS["text_light"], COLORS["text_dark"]),
            dropdown_hover_color=(COLORS["border_light"], "#33333B"),
            font=(Fonts.family, 13, "normal"),
        )
        self.quality_menu.pack(side="left")

        # Separador sutil entre el valor y la acción -- una línea de 1px,
        # no otro marco con su propio fondo, para no romper la cápsula.
        # OJO: sin `height` explícito, CTkFrame cae en su alto por defecto
        # (~200px) y con `fill="y"` eso infla TODA la cápsula a esa altura
        # -- hay que fijarlo al alto real de sus vecinos (40px).
        ctk.CTkFrame(
            pill_inner, width=1, height=40,
            fg_color=(COLORS["border_light"], COLORS["border_dark"]),
        ).pack(side="left", padx=14)

        # Texto en Tiger Orange (no gris): es una acción, no una etiqueta,
        # y en la card blanca un botón "fantasma" gris quedaba casi
        # invisible -- el acento de marca lo hace notorio sin agregar un
        # borde ni una caja propia que rompa la cápsula.
        self.probe_button = ctk.CTkButton(
            pill_inner, text=self.i18n.t("converter.quality_probe_button"),
            height=40, corner_radius=20,
            fg_color=_PILL_BG, hover=False,
            text_color=COLORS["tiger_orange"],
            font=(Fonts.family, 14, "normal"),
            command=self._probe_qualities,
        )
        self.probe_button.pack(side="left", padx=(0, 6))
        attach_hover(self.probe_button, _PILL_BG, (COLORS["border_light"], "#33333B"))
        self.quality_row.grid_remove()  # oculto hasta que se elija MP4

        # --- Botón de acción ---
        self.action_button = CTAButton(
            body, text=self.i18n.t("converter.action_button"),
            command=self._start_download, width=340, height=52,
            font=(Fonts.family, 16, "bold"),
        )
        self.action_button.grid(row=3, column=0, pady=(8, 16))

        self.status_label = ctk.CTkLabel(
            body, text=self.i18n.t("converter.status_idle"), font=(Fonts.family, 12, "normal"),
            text_color=(COLORS["text_muted_light"], COLORS["text_muted_dark"]),
        )
        self.status_label.grid(row=4, column=0, pady=(0, 12))
        # El texto de estado ("Esperando un enlace...", "¡Listo!", etc.) se
        # funde en vez de cambiar de golpe: Tkinter no tiene canal alfa, así
        # que TextFade simula la opacidad interpolando el color del texto
        # hacia/desde el color real de la card detrás de él.
        self._status_fade = TextFade(
            self.status_label,
            bg_resolver=lambda: resolve_for_mode((COLORS["card_light"], COLORS["card_dark"])),
        )

        # Barra de progreso: aparece solo cuando inicia la descarga.
        self.progress = ctk.CTkProgressBar(
            body, progress_color=COLORS["tiger_orange"],
            fg_color=(COLORS["border_light"], "#2A2A31"),
            height=8, corner_radius=4,
        )
        self.progress.set(0)
        self.progress.grid(row=5, column=0, sticky="ew", padx=28, pady=(0, 12))
        self.progress.grid_remove()

        # --- Botón de cancelar: aparece junto con la barra de progreso.
        # Crítico para descargas en 4K, que pueden tardar varios minutos y
        # antes no tenían forma de interrumpirse a mitad de proceso.
        self.cancel_button = ctk.CTkButton(
            body, text=self.i18n.t("converter.cancel_button"),
            width=140, height=36, corner_radius=12,
            fg_color="transparent", border_width=1, hover=False,
            border_color=COLORS["mahogany_red"],
            text_color=COLORS["mahogany_red"],
            font=Fonts.BODY_MEDIUM,
            command=self._cancel_download,
        )
        self.cancel_button.grid(row=6, column=0, pady=(0, 16))
        self.cancel_button.grid_remove()
        attach_hover(self.cancel_button, "transparent", (COLORS["surface_light"], "#2A2A31"))

        # --- Panel de éxito: ruta + acciones (oculto hasta terminar) ---
        self.success_row = ctk.CTkFrame(body, fg_color="transparent")
        self.success_row.grid(row=7, column=0, padx=28, pady=(0, 12), sticky="ew")

        self.path_label = ctk.CTkLabel(
            self.success_row, text="", font=(Fonts.family, 12, "normal"), justify="center",
            wraplength=440,
            text_color=(COLORS["text_muted_light"], COLORS["text_muted_dark"]),
        )
        self.path_label.pack(pady=(0, 16))

        buttons_row = ctk.CTkFrame(self.success_row, fg_color="transparent")
        buttons_row.pack()

        show_folder_button = ctk.CTkButton(
            buttons_row, text=self.i18n.t("converter.show_folder"),
            width=160, height=44, corner_radius=14,
            fg_color="transparent", border_width=1, hover=False,
            border_color=(COLORS["border_light"], COLORS["border_dark"]),
            text_color=(COLORS["text_light"], COLORS["text_dark"]),
            font=(Fonts.family, 14, "normal"),
            command=self._open_folder,
        )
        show_folder_button.pack(side="left", padx=(0, 12))
        attach_hover(show_folder_button, "transparent", (COLORS["surface_light"], "#28282F"))

        CTAButton(
            buttons_row, text=self.i18n.t("converter.download_another"),
            command=self._reset, width=200, height=44,
            font=(Fonts.family, 14, "bold"),
        ).pack(side="left")

        self.success_row.grid_remove()

    # --- Formato / calidad ---

    def _on_format_change(self, value):
        if value == "MP4":
            self.quality_row.grid()
        else:
            self.quality_row.grid_remove()

    def _probe_qualities(self):
        url = self.url_entry.get().strip()
        if not is_valid_youtube_url(url):
            self._set_status(self.i18n.t("converter.invalid_url"), error=True)
            return
        self.probe_button.configure(state="disabled")
        self._set_status(self.i18n.t("converter.quality_probing"))
        self.quality_probe.start(url)

    def _on_qualities_found(self, heights, error):
        self.after(0, self._apply_qualities, heights, error)

    def _apply_qualities(self, heights, error):
        # `QualityProbe` hace la consulta de red en un hilo aparte y llega acá
        # vía `.after(0, ...)`, que puede tardar varios segundos. Si el
        # usuario navega a otra pantalla mientras tanto, `_clear()` destruye
        # esta vista, pero el `.after()` ya programado igual se ejecuta -- sin
        # esta guarda, cualquier línea de acá abajo revienta con
        # `TclError: invalid command name` porque el widget ya no existe.
        if not self.winfo_exists():
            return
        self.probe_button.configure(state="normal")
        best_label = self.i18n.t("converter.quality_best")
        self._quality_heights = {best_label: None}

        if error:
            self._set_status(f"{self.i18n.t('converter.status_error')}: {error}", error=True)
        elif not heights:
            self._set_status(self.i18n.t("converter.quality_none_found"))
        else:
            self._quality_heights = build_quality_options(heights, best_label)
            self._set_status(self.i18n.t("converter.quality_found"))

        labels = list(self._quality_heights.keys())
        self.quality_menu.configure(values=labels)
        self.quality_var.set(labels[0] if labels else best_label)

    # --- Descarga ---

    def _start_download(self):
        url = self.url_entry.get().strip()
        if not is_valid_youtube_url(url):
            self._set_status(self.i18n.t("converter.invalid_url"), error=True)
            return

        fmt = self.format_toggle.get().lower()
        output_dir = resolve_output_dir(self.settings)
        max_height = resolve_max_height(fmt, self._quality_heights, self.quality_var.get())

        self._cancelling = False
        self.action_button.configure(state="disabled")
        self.probe_button.configure(state="disabled")
        self._lock_url_entry()
        self.success_row.grid_remove()
        self.progress.grid()
        self.progress.set(0)
        self.cancel_button.configure(state="normal", text=self.i18n.t("converter.cancel_button"))
        self.cancel_button.grid()
        self._set_status(self.i18n.t("converter.status_downloading"))

        self.downloader.start(url, fmt, output_dir, max_height=max_height)

    def _cancel_download(self):
        """Corta la descarga/transcodeo en curso. El resultado final llega
        igual por `_on_finished`, así que aquí solo se da feedback inmediato
        (deshabilitar el botón) para que no parezca que no hizo nada."""
        self._cancelling = True
        self.cancel_button.configure(state="disabled", text=self.i18n.t("converter.cancelling"))
        self.downloader.cancel()

    def _on_progress(self, pct: float, stage: str):
        self.after(0, self._apply_progress, pct, stage)

    def _apply_progress(self, pct: float, stage: str):
        # Mismo riesgo que en `_apply_qualities`: `Downloader` corre en un
        # hilo aparte y reporta progreso durante minutos en un 4K; si el
        # usuario navega afuera antes de que termine, esta vista ya está
        # destruida cuando el próximo progreso llega.
        if not self.winfo_exists():
            return
        if stage == "transcoding":
            # La resolución pedida solo existía en un códec que QuickTime no
            # reproduce (típico por encima de 1080p); se está recodificando
            # a H.264/AAC. Puede tardar, así que se avisa y se usa una barra
            # indeterminada en vez de una que parezca trabada en 100%.
            if self.progress.cget("mode") != "indeterminate":
                self.progress.configure(mode="indeterminate")
                self.progress.start()
            if not self._cancelling:
                self._set_status(self.i18n.t("converter.status_transcoding"))
            return

        if self.progress.cget("mode") == "indeterminate":
            self.progress.stop()
            self.progress.configure(mode="determinate")
        self.progress.set(pct)

    def _on_finished(self, result):
        self.after(0, self._apply_finished, result)

    def _apply_finished(self, result):
        # Mismo riesgo: el resultado final de una descarga/transcodeo largo
        # puede llegar mucho después de que el usuario haya navegado afuera
        # y esta vista ya esté destruida.
        if not self.winfo_exists():
            return
        self.action_button.configure(state="normal")
        self.probe_button.configure(state="normal")
        if self.progress.cget("mode") == "indeterminate":
            # Si terminó justo tras una recodificación, hay que detener el
            # bucle interno de animación antes de ocultar la barra.
            self.progress.stop()
            self.progress.configure(mode="determinate")
        self.progress.grid_remove()
        self.cancel_button.grid_remove()
        self._cancelling = False

        if result.success:
            self._last_filepath = result.filepath
            self._set_status(self.i18n.t("converter.status_done"))
            self.path_label.configure(
                text=f"{self.i18n.t('converter.saved_at')} {result.filepath}"
            )
            self.success_row.grid()
            # El enlace se queda bloqueado -- con el look "deshabilitado" --
            # mientras el panel de éxito está a la vista: ese enlace es el
            # que generó el archivo ya entregado, no uno nuevo a medio
            # escribir. Se reactiva recién en `_reset()`, con "Descargar
            # otro archivo".
        else:
            # Error o cancelación: no hay panel de éxito ni botón propio
            # para reactivar el campo, así que se reactiva de una para que
            # el usuario pueda corregir el enlace o reintentar.
            self._unlock_url_entry()
            if result.cancelled:
                self._set_status(self.i18n.t("converter.status_cancelled"))
            else:
                self._set_status(f"{self.i18n.t('converter.status_error')}: {result.error}", error=True)

    def _open_folder(self):
        if self._last_filepath:
            reveal_in_file_manager(self._last_filepath)

    def _lock_url_entry(self) -> None:
        """Bloquea el campo de enlace y lo pinta con el color muted de la
        paleta -- el mismo que ya usa el placeholder -- para que se lea como
        deshabilitado de un vistazo, no solo al intentar tocarlo."""
        self.url_entry.configure(
            state="disabled",
            text_color=(COLORS["text_muted_light"], COLORS["text_muted_dark"]),
        )

    def _unlock_url_entry(self) -> None:
        """Reactiva el campo y restaura su color de texto normal."""
        self.url_entry.configure(
            state="normal",
            text_color=(COLORS["text_light"], COLORS["text_dark"]),
        )

    def _reset(self):
        """Vuelve la pantalla a su estado por defecto (URL, formato y calidad)."""
        self._unlock_url_entry()
        self.url_entry.delete(0, "end")
        self._last_filepath = None
        self.path_label.configure(text="")
        self.success_row.grid_remove()
        self.progress.grid_remove()
        self.progress.set(0)
        self.cancel_button.grid_remove()

        # Formato y calidad vuelven al estado inicial: no arrastrar la
        # resolución/formato del video anterior a la siguiente descarga.
        self.format_toggle.set("MP3")
        self.quality_row.grid_remove()
        best_label = self.i18n.t("converter.quality_best")
        self._quality_heights = {}
        self.quality_menu.configure(values=[best_label])
        self.quality_var.set(best_label)

        self.action_button.configure(state="normal")
        self.probe_button.configure(state="normal")

        self._set_status(self.i18n.t("converter.status_idle"))
        self.url_entry.focus_set()

    def _set_status(self, text: str, error: bool = False):
        color = COLORS["mahogany_red"] if error else (COLORS["text_muted_light"], COLORS["text_muted_dark"])
        self._status_fade.to(text, color)

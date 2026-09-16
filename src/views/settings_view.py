"""Pantalla de Configuraciones: tema, idioma y carpeta de descargas.

Rediseñada como grupos separados al estilo de Ajustes del Sistema en macOS
(Apariencia / Idioma / Almacenamiento como secciones propias, cada una con
su etiqueta pequeña en mayúsculas y su propia tarjeta) en vez de una única
tarjeta larga con todo apretado -- separar por tema hace que cada ajuste se
lea de un vistazo, sin tener que escanear una lista plana.
"""

import os
from tkinter import filedialog

import customtkinter as ctk

from ..config import COLORS, Fonts, LANGUAGES, create_youtools_folder
from ..components.buttons import AnimatedFormatToggle, CTAButton
from ..components.motion import TextFade, resolve_for_mode
from ..components.theme_icons import make_theme_icon_pair


def _truncate_path(path: str, max_chars: int = 54) -> str:
    """Trunca una ruta larga desde el INICIO con "…/" (como hace Finder en
    la barra de título) en vez de envolverla en varias líneas -- una ruta de
    archivo se lee de derecha a izquierda para saber "dónde está" (el nombre
    de la carpeta final importa más que el disco/usuario del principio)."""
    if len(path) <= max_chars:
        return path
    return "…/" + path[-(max_chars - 2):].split("/", 1)[-1]


class _SectionCard(ctk.CTkFrame):
    """Un grupo de ajustes: etiqueta pequeña en mayúsculas + tarjeta propia.

    Corner radius más chico (16px, contra los 24px de antes) a propósito:
    varias tarjetas chicas y apretadas leen mejor "minimalista" con esquinas
    más discretas que con el mismo radio grande que una única tarjeta grande.
    """

    def __init__(self, master, label_text: str):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text=label_text.upper(), font=(Fonts.family, 11, "bold"),
            text_color=(COLORS["text_muted_light"], COLORS["text_muted_dark"]),
        ).grid(row=0, column=0, sticky="w", padx=4, pady=(0, 8))

        self.body = ctk.CTkFrame(
            self, corner_radius=16,
            fg_color=(COLORS["card_light"], COLORS["card_dark"]),
            border_width=1,
            border_color=(COLORS["border_light"], COLORS["border_dark"]),
        )
        self.body.grid(row=1, column=0, sticky="ew")
        self.body.grid_columnconfigure(1, weight=1)


class SettingsView(ctk.CTkFrame):
    def __init__(self, master, i18n, settings: dict, on_change, on_language_change=None):
        super().__init__(master, fg_color=(COLORS["surface_light"], COLORS["shadow_grey"]))
        self.i18n = i18n
        self.settings = settings
        self.on_change = on_change
        # Callback aparte para idioma: dispara la transición de "pestañeo"
        # que reconstruye la pantalla activa con los textos ya traducidos.
        self.on_language_change_cb = on_language_change or on_change

        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text=self.i18n.t("settings.title"), font=Fonts.TITLE,
            text_color=(COLORS["text_light"], COLORS["text_dark"]),
        ).grid(row=0, column=0, sticky="w", padx=36, pady=(32, 24))

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.grid(row=1, column=0, sticky="new", padx=36)
        content.grid_columnconfigure(0, weight=1)

        # --- Apariencia + Idioma: lado a lado, compactas ---
        # Antes cada una era una tarjeta de ancho completo con el control
        # empujado al borde derecho (`sticky="e"`) -- dejaba un hueco vacío
        # enorme a la izquierda, ya que ninguna de las dos tiene más
        # contenido que un solo control. Al ponerlas una junto a otra y
        # centrar el control dentro de cada una, se usa el ancho disponible
        # en vez de desperdiciarlo. La sección de Almacenamiento (mucho más
        # contenido: ruta + botón + advertencia) se queda exactamente igual.
        top_row = ctk.CTkFrame(content, fg_color="transparent")
        top_row.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        top_row.grid_columnconfigure((0, 1), weight=1, uniform="settings_top")

        appearance_section = _SectionCard(top_row, self.i18n.t("settings.theme_label"))
        appearance_section.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self._theme_map = {
            self.i18n.t("settings.theme_system"): "System",
            self.i18n.t("settings.theme_light"): "Light",
            self.i18n.t("settings.theme_dark"): "Dark",
        }
        reverse_theme = {v: k for k, v in self._theme_map.items()}

        # CTkSegmentedButton solo admite un único text_color para todos los
        # segmentos a la vez, así que el segmento seleccionado (Tiger Orange)
        # y el fondo apagado no pueden tener cada uno su propio contraste
        # correcto en modo oscuro. AnimatedFormatToggle sí lo permite (cada
        # segmento es su propio widget) y ya resuelve el fondo apagado según
        # el tema activo, así que se reutiliza aquí en vez del segmented
        # button nativo.
        #
        # Un ícono por opción (monitor/sol/luna) hace que "Sistema/Claro/
        # Oscuro" se reconozca de un vistazo sin tener que leer el texto --
        # los mismos dos colores que ya usa el chip (apagado/muted y
        # Shadow Grey cuando está seleccionado), para que el ícono nunca
        # quede con peor contraste que el texto de al lado.
        off_icon_color = resolve_for_mode((COLORS["shadow_grey"], COLORS["text_dark"]))
        theme_icons = [
            make_theme_icon_pair(key, off_icon_color, COLORS["shadow_grey"])
            for key in ("system", "light", "dark")
        ]
        # `fluid=True`: el toggle deja de ser un control chico centrado con
        # mucho aire alrededor y pasa a ESTIRARSE hasta llenar la tarjeta
        # (se recalcula solo con cada resize -- ver `_on_resize` en
        # `AnimatedFormatToggle`), para que tome el protagonismo de la
        # cápsula en vez de sentirse encapsulado dentro de ella.
        self.theme_toggle = AnimatedFormatToggle(
            appearance_section.body, values=list(self._theme_map.keys()),
            command=self._on_theme_change, width=250, height=44, font=Fonts.BODY_MEDIUM,
            icons=theme_icons, fluid=True,
        )
        self.theme_toggle.set(reverse_theme.get(self.settings.get("appearance", "System")))
        self.theme_toggle.grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=16)
        appearance_section.body.grid_columnconfigure(0, weight=1)

        language_section = _SectionCard(top_row, self.i18n.t("settings.language_label"))
        language_section.grid(row=0, column=1, sticky="ew", padx=(10, 0))

        # Mismo criterio acá: sin `width` fijo y con `sticky="ew"`, el
        # dropdown ocupa todo el ancho real de su tarjeta en vez de quedar
        # como una isla angosta en el medio de un espacio mucho más grande.
        self.language_var = ctk.StringVar(value=self.settings.get("language", "Español"))
        ctk.CTkOptionMenu(
            language_section.body, values=LANGUAGES, variable=self.language_var,
            height=44,
            fg_color=(COLORS["surface_light"], "#2A2A31"),
            button_color=COLORS["tiger_orange"], button_hover_color=COLORS["tiger_orange"],
            text_color=(COLORS["text_light"], COLORS["text_dark"]),
            dropdown_fg_color=(COLORS["surface_light"], "#2A2A31"),
            dropdown_text_color=(COLORS["text_light"], COLORS["text_dark"]),
            dropdown_hover_color=(COLORS["border_light"], "#33333B"),
            font=Fonts.BODY_MEDIUM,
            command=self._on_language_change,
        ).grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=16)
        language_section.body.grid_columnconfigure(0, weight=1)

        # --- Sección: Almacenamiento (sin cambios) ---
        storage_section = _SectionCard(content, self.i18n.t("settings.folder_label"))
        storage_section.grid(row=1, column=0, sticky="ew")
        storage_section.body.grid_columnconfigure(0, weight=1)

        # "Path chip": la ruta actual en un bloque con fondo propio y fuente
        # monoespaciada (se lee como una ruta de archivo, no como texto
        # normal) en vez de un CTkLabel suelto -- así queda claro que es un
        # valor, no una descripción.
        path_row = ctk.CTkFrame(storage_section.body, fg_color="transparent")
        path_row.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(20, 0))
        path_row.grid_columnconfigure(0, weight=1)

        current_path = self.settings.get("download_path", os.path.expanduser("~/Downloads/YouTools"))
        path_chip = ctk.CTkFrame(
            path_row, corner_radius=10,
            fg_color=(COLORS["surface_light"], "#1F1F25"),
        )
        path_chip.grid(row=0, column=0, sticky="ew")
        path_chip.grid_columnconfigure(0, weight=1)

        self.path_label = ctk.CTkLabel(
            path_chip, text=_truncate_path(current_path), font=("Menlo", 11),
            text_color=(COLORS["text_muted_light_strong"], COLORS["text_muted_dark_strong"]),
            anchor="w", justify="left",
        )
        self.path_label.grid(row=0, column=0, sticky="ew", padx=14, pady=10)

        # Canary Yellow (no Tiger Orange, que ya domina esta pantalla en el
        # toggle de apariencia y la flecha del dropdown de idioma): un color
        # distinto de la paleta para que "Cambiar carpeta" no se lea como
        # una variación más del mismo acento, sino como su propia acción
        # notoria. Reutiliza `CTAButton` -- ya resuelve el contraste
        # obligatorio del manual (texto Shadow Grey sobre Canary Yellow).
        folder_button = CTAButton(
            path_row, text=self.i18n.t("settings.folder_button"),
            command=self._choose_folder, width=140, height=36, font=Fonts.SMALL,
        )
        folder_button.grid(row=0, column=1, sticky="e", padx=(12, 0))

        # Advertencia sutil: informativa, no alarmante -- tono muted, sin
        # color de estado (rojo/naranja) porque no es un error, es solo
        # contexto sobre una restricción del sistema. El mismo label se
        # reutiliza para mostrar un error puntual (en Mahogany Red) si crear
        # la carpeta falla, y vuelve solo a este texto neutro después.
        self._folder_note_default = f"ⓘ  {self.i18n.t('settings.folder_warning')}"
        self.folder_note = ctk.CTkLabel(
            storage_section.body,
            text=self._folder_note_default,
            font=(Fonts.family, 11),
            text_color=(COLORS["text_muted_light"], COLORS["text_muted_dark"]),
            anchor="w", justify="left", wraplength=500,
        )
        self.folder_note.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=(8, 18))
        self._folder_note_fade = TextFade(
            self.folder_note,
            bg_resolver=lambda: resolve_for_mode((COLORS["card_light"], COLORS["card_dark"])),
        )

    def _on_theme_change(self, label):
        mode = self._theme_map[label]
        self.settings["appearance"] = mode
        ctk.set_appearance_mode(mode)
        self.on_change(self.settings)

    def _on_language_change(self, value):
        self.settings["language"] = value
        self.i18n.set_language(value)
        self.on_language_change_cb(self.settings)

    def _choose_folder(self):
        current = self.settings.get("download_path", "")
        # Abrir el diálogo un nivel arriba de la carpeta "youtools" actual
        # (no dentro de ella), para que el usuario elija dónde vivirá la
        # carpeta, no renombrarla desde adentro.
        initial = (
            os.path.dirname(current)
            if os.path.basename(current).lower() == "youtools" and os.path.dirname(current)
            else os.path.expanduser("~")
        )
        chosen = filedialog.askdirectory(initialdir=initial)
        if not chosen:
            return

        # La carpeta de descargas siempre debe llamarse "youtools": es un
        # requisito fijo, así que cualquier carpeta elegida se normaliza a
        # `<elegida>/youtools` en vez de dejar que el usuario la deje con
        # otro nombre. `create_youtools_folder` además crea la carpeta en
        # disco (el diálogo del sistema solo deja elegir carpetas que ya
        # existen, y "youtools" normalmente no existe todavía ahí) sin
        # lanzar una excepción si el sistema no lo permite.
        normalized, error = create_youtools_folder(chosen)
        if error:
            self._folder_note_fade.to(f"⚠️  {error}", COLORS["mahogany_red"])
            return

        self.settings["download_path"] = normalized
        self.path_label.configure(text=_truncate_path(normalized))
        self.on_change(self.settings)
        # Confirmar el cambio y, después de un momento, volver a la nota
        # neutra -- mismo patrón de feedback transitorio que el estado del
        # conversor, para no dejar un mensaje de éxito pegado indefinidamente.
        self._folder_note_fade.to("✓  Carpeta actualizada", (COLORS["text_muted_light"], COLORS["text_muted_dark"]))
        self.after(2500, lambda: self._folder_note_fade.to(
            self._folder_note_default, (COLORS["text_muted_light"], COLORS["text_muted_dark"])
        ))

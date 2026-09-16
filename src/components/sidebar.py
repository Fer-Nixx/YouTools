"""Sidebar fijo: navegación (Tools/Settings) + marca de agua del creador (Fase 2)."""

import webbrowser

import customtkinter as ctk

from ..config import COLORS, Fonts
from .motion import attach_hover, resolve_for_mode, IconPulse
from .social_icons import make_social_icons, make_social_icon_pulse_frames
from .brand_icon import make_brand_icon
from .tooltip import Tooltip

GITHUB_URL = "https://github.com/Fer-Nixx"
LINKEDIN_URL = "https://www.linkedin.com/in/fernandocontrerasrojas"
BUYMEACOFFEE_URL = "https://buymeacoffee.com/fernixx"

# Ancho fijo del sidebar. Exportado (en vez de quedar hardcodeado solo acá)
# porque `App._show_converter` lo necesita para saber dónde termina el
# sidebar y así no animar la transición de vista por encima suyo.
SIDEBAR_WIDTH = 220


class Sidebar(ctk.CTkFrame):
    """Barra lateral fija, consistente en todas las pantallas post-instalación."""

    def __init__(self, master, i18n, on_navigate, active: str = "tools"):
        super().__init__(
            master,
            width=SIDEBAR_WIDTH,
            corner_radius=0,
            fg_color=(COLORS["surface_light"], COLORS["shadow_grey"]),
        )
        self.grid_propagate(False)
        self.grid_rowconfigure(2, weight=1)

        self.i18n = i18n
        self.on_navigate = on_navigate
        self._icons = make_social_icons()

        # --- Marca: clickeable, lleva a Herramientas ---
        # Antes era un CTkLabel suelto -- de tan parecido a un título de
        # pantalla, era natural probar a hacerle clic esperando volver al
        # inicio (como el logo de cualquier app/sitio), y no pasaba nada.
        # Ahora es un botón real: ícono de caja de herramientas + texto más
        # grande, navegación directa a Herramientas. Sin hover -- es un
        # logo, no un ítem de navegación más; se mantiene quieto y solo
        # responde al clic, sin el ruido visual de un resalte.
        # Un poco más grande que antes (pedido explícito), pero
        # `line_w_factor` sigue igual: es relativo al tamaño del propio
        # ícono, así que el grosor del trazo escala junto con todo lo demás
        # y se mantiene la misma proporción ícono/texto de antes.
        brand_icon = make_brand_icon(
            resolve_for_mode((COLORS["text_light"], COLORS["text_dark"])), line_w_factor=0.15
        )
        brand_button = ctk.CTkButton(
            self, text="YouTools", image=brand_icon, compound="left",
            font=(Fonts.family, 26, "bold"), anchor="w",
            fg_color="transparent", hover=False, border_width=0,
            text_color=(COLORS["text_light"], COLORS["text_dark"]),
            command=lambda: self.on_navigate("tools"),
        )
        brand_button.grid(row=0, column=0, padx=16, pady=(24, 20), sticky="w")

        # --- Navegación ---
        nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        nav_frame.grid(row=1, column=0, sticky="new", padx=12)
        nav_frame.grid_columnconfigure(0, weight=1)

        self._nav_transitions = {}
        self._nav_buttons = {
            "tools": self._make_nav_button(nav_frame, self.i18n.t("hub.nav_tools"), "tools", 0),
            "settings": self._make_nav_button(nav_frame, self.i18n.t("hub.nav_settings"), "settings", 1),
        }
        self.set_active(active)

        # --- Footer: marca de agua del creador + redes ---
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="sew", padx=20, pady=18)

        icons_row = ctk.CTkFrame(footer, fg_color="transparent")
        icons_row.pack(anchor="w", pady=(0, 8))

        # Logos sociales sin fondo: solo el ícono flotando. `fg_color=None`
        # (usado antes) NO significa "sin color" en customtkinter -- activa
        # el color por defecto del tema del botón (visible, un gris/azul de
        # sistema), que es justo el fondo que el usuario seguía viendo.
        # `fg_color="transparent"` es lo que realmente hace que el botón se
        # pinte con el color real del padre detrás, sin ningún rectángulo.
        # Cada ícono lleva un tooltip con el nombre de la red -- sin texto
        # al lado, un ícono suelto no siempre deja claro a dónde lleva de
        # un vistazo (sobre todo el de café, que no todos reconocen).
        github_button = ctk.CTkButton(
            icons_row, image=self._icons["github"], text="", width=34, height=34,
            fg_color="transparent", hover=False, border_width=0,
            command=lambda: webbrowser.open(GITHUB_URL),
        )
        github_button.pack(side="left", padx=(0, 6))
        IconPulse(github_button, make_social_icon_pulse_frames("github"), cycle_ms=12000)
        Tooltip(github_button, "GitHub")

        linkedin_button = ctk.CTkButton(
            icons_row, image=self._icons["linkedin"], text="", width=34, height=34,
            fg_color="transparent", hover=False, border_width=0,
            command=lambda: webbrowser.open(LINKEDIN_URL),
        )
        linkedin_button.pack(side="left", padx=(0, 6))
        IconPulse(linkedin_button, make_social_icon_pulse_frames("linkedin"), cycle_ms=12000)
        Tooltip(linkedin_button, "LinkedIn")

        coffee_button = ctk.CTkButton(
            icons_row, image=self._icons["coffee"], text="", width=34, height=34,
            fg_color="transparent", hover=False, border_width=0,
            command=lambda: webbrowser.open(BUYMEACOFFEE_URL),
        )
        coffee_button.pack(side="left")
        IconPulse(coffee_button, make_social_icon_pulse_frames("coffee"), cycle_ms=12000)
        Tooltip(coffee_button, "Buy Me a Coffee")

        # Marca de agua con año © 2026 en una línea (8pt para que quepa sin cortes)
        ctk.CTkLabel(
            footer, text=self.i18n.t("footer.credit"),
            font=(Fonts.family, 8, "bold"), justify="left",
            text_color=(COLORS["text_muted_light_strong"], COLORS["text_muted_dark_strong"]),
        ).pack(anchor="w")

    def _make_nav_button(self, parent, text, key, row):
        btn = ctk.CTkButton(
            parent, text=text, anchor="w", font=Fonts.BODY_MEDIUM,
            height=38, corner_radius=10,
            fg_color="transparent",
            text_color=(COLORS["text_light"], COLORS["text_dark"]),
            hover=False,
            command=lambda: self.on_navigate(key),
        )
        btn.grid(row=row, column=0, sticky="ew", pady=3)
        # "hover=False" apaga el cambio de color instantáneo de
        # customtkinter; `set_active()` retoca los colores de esta
        # transición cada vez que este botón pasa a activo/inactivo.
        self._nav_transitions[key] = attach_hover(
            btn, "transparent", (COLORS["surface_light"], "#28282F")
        )
        return btn

    def set_active(self, key: str) -> None:
        for name, btn in self._nav_buttons.items():
            transition = self._nav_transitions[name]
            if name == key:
                base, hover = COLORS["tiger_orange"], COLORS["tiger_orange"]
                btn.configure(fg_color=base, text_color=COLORS["shadow_grey"])
            else:
                base, hover = "transparent", (COLORS["surface_light"], "#28282F")
                btn.configure(fg_color=base, text_color=(COLORS["text_light"], COLORS["text_dark"]))
            transition.retarget(base, hover)

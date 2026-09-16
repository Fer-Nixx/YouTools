"""Pantalla 1: Instalador / Configuración inicial (Fase 2 del PRD)."""

import os
from tkinter import filedialog

import customtkinter as ctk

from ..config import COLORS, Fonts, LANGUAGES, create_youtools_folder
from ..components.buttons import CTAButton
from ..components.motion import attach_hover


class SetupView(ctk.CTkFrame):
    def __init__(self, master, i18n, settings: dict, on_complete):
        super().__init__(master, fg_color=(COLORS["surface_light"], COLORS["shadow_grey"]))
        self.i18n = i18n
        self.settings = settings
        self.on_complete = on_complete

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        card = ctk.CTkFrame(
            self, corner_radius=24, width=460, height=440,
            fg_color=(COLORS["card_light"], COLORS["card_dark"]),
            border_width=1,
            border_color=(COLORS["border_light"], COLORS["border_dark"]),
        )
        card.grid(row=0, column=0)
        card.grid_propagate(False)

        ctk.CTkLabel(
            card, text=self.i18n.t("setup.title"), font=Fonts.TITLE,
            text_color=(COLORS["text_light"], COLORS["text_dark"]),
        ).pack(pady=(40, 6), padx=40)

        ctk.CTkLabel(
            card, text=self.i18n.t("setup.subtitle"), font=Fonts.BODY,
            text_color=(COLORS["text_muted_light"], COLORS["text_muted_dark"]),
        ).pack(pady=(0, 32))

        # --- Selector de idioma ---
        ctk.CTkLabel(
            card, text=self.i18n.t("setup.language_label"), font=Fonts.BODY_MEDIUM,
            text_color=(COLORS["text_light"], COLORS["text_dark"]),
        ).pack(anchor="w", padx=40)

        self.language_var = ctk.StringVar(value=self.settings.get("language", "Español"))
        ctk.CTkOptionMenu(
            card, values=LANGUAGES, variable=self.language_var,
            width=380, height=40, corner_radius=12,
            fg_color=(COLORS["surface_light"], "#2A2A31"),
            button_color=COLORS["tiger_orange"],
            button_hover_color=COLORS["tiger_orange"],
            text_color=(COLORS["text_light"], COLORS["text_dark"]),
            dropdown_fg_color=(COLORS["surface_light"], "#2A2A31"),
            dropdown_text_color=(COLORS["text_light"], COLORS["text_dark"]),
            dropdown_hover_color=(COLORS["border_light"], "#33333B"),
            font=Fonts.BODY,
        ).pack(pady=(6, 22), padx=40)

        # --- Selector de carpeta ---
        ctk.CTkLabel(
            card, text=self.i18n.t("setup.folder_label"), font=Fonts.BODY_MEDIUM,
            text_color=(COLORS["text_light"], COLORS["text_dark"]),
        ).pack(anchor="w", padx=40)

        folder_row = ctk.CTkFrame(card, fg_color="transparent")
        folder_row.pack(fill="x", padx=40, pady=(6, 30))

        self.folder_var = ctk.StringVar(value=self.settings.get("download_path", ""))
        ctk.CTkLabel(
            folder_row, textvariable=self.folder_var, font=Fonts.SMALL,
            text_color=(COLORS["text_muted_light"], COLORS["text_muted_dark"]),
            anchor="w", width=260,
        ).pack(side="left", fill="x", expand=True)

        folder_button = ctk.CTkButton(
            folder_row, text=self.i18n.t("setup.folder_button"),
            width=120, height=34, corner_radius=10,
            fg_color="transparent", border_width=1, hover=False,
            border_color=(COLORS["border_light"], COLORS["border_dark"]),
            text_color=(COLORS["text_light"], COLORS["text_dark"]),
            font=Fonts.SMALL,
            command=self._choose_folder,
        )
        folder_button.pack(side="right")
        attach_hover(folder_button, "transparent", (COLORS["surface_light"], "#28282F"))

        # --- Botón de instalación ---
        CTAButton(
            card, text=self.i18n.t("setup.install_button"),
            command=self._install, width=380,
        ).pack(pady=(0, 36))

    def _choose_folder(self):
        chosen = filedialog.askdirectory(
            initialdir=self.folder_var.get() or os.path.expanduser("~")
        )
        if not chosen:
            return
        # La carpeta de descargas siempre debe llamarse "youtools"; se crea
        # en disco de una vez (el diálogo del sistema solo deja elegir
        # carpetas que ya existen, y "youtools" normalmente no existe
        # todavía ahí) sin dejar que un permiso denegado rompa el instalador.
        normalized, error = create_youtools_folder(chosen)
        if error:
            self.folder_var.set(f"⚠️ {error}")
            return
        self.folder_var.set(normalized)

    def _install(self):
        self.settings["language"] = self.language_var.get()
        self.settings["download_path"] = self.folder_var.get() or self.settings["download_path"]
        self.settings["onboarded"] = True
        self.i18n.set_language(self.settings["language"])
        self.on_complete(self.settings)

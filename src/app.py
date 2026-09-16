"""Clase principal de la aplicación: ventana raíz, temas y navegación (Fase 1-2)."""

import customtkinter as ctk

from .config import APP_NAME, COLORS, Fonts
from .i18n import I18n
from .settings_manager import load_settings, save_settings
from .components.sidebar import Sidebar
from .components.motion import ViewTransition
from .views.setup_view import SetupView
from .views.hub_view import HubView
from .views.converter_view import ConverterView
from .views.settings_view import SettingsView


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # El fondo por defecto de la ventana raíz de customtkinter es el que
        # trae el tema ("gray14" en modo oscuro, un tono distinto del
        # `shadow_grey` que usa el resto de la app) -- asoma cada vez que la
        # columna de contenido queda momentáneamente vacía, entre destruir la
        # vista anterior y terminar de construir la nueva. Como el conversor
        # es la vista con más widgets (la más lenta de construir), ese
        # instante se nota ahí como un "pantallazo negro". Fijar el fondo de
        # la ventana al mismo color que usan las vistas elimina el salto de
        # color aunque ese instante vacío exista.
        self.configure(fg_color=(COLORS["surface_light"], COLORS["shadow_grey"]))

        # No se fuerza `preferred_drawing_method`: se deja el default nativo
        # de customtkinter en macOS ("polygon_shapes").
        #
        # Historial de esta línea (para no repetir el mismo experimento):
        # - "circle_shapes" (probado antes) dibuja las esquinas con
        #   `create_oval` crudo de Tk, SIN antialiasing -- se veían
        #   pixeladas/dentadas todas las tarjetas, chips y botones
        #   redondeados de la app.
        # - "font_shapes" (probado después, buscando antialiasing real vía
        #   `create_aa_circle`) renderiza artefactos graves en esta
        #   combinación de Tk/customtkinter -- marcas en forma de corchete
        #   en cada esquina -- mucho peor que el aliasing que buscaba
        #   arreglar.
        # - "polygon_shapes" (el default) resultó tener el mejor
        #   antialiasing de los tres en la práctica (confirmado con capturas
        #   ampliadas de esquinas reales). El único caso donde antes se veían
        #   puntas con este método era un radio de píldora completa
        #   (corner_radius = height/2); `AnimatedFormatToggle` fuerza
        #   `overwrite_preferred_drawing_method="circle_shapes"` puntualmente
        #   solo ahí en vez de aplicar un método peor a toda la app.

        Fonts.init()

        self.settings = load_settings()
        ctk.set_appearance_mode(self.settings.get("appearance", "System"))

        self.i18n = I18n(self.settings.get("language", "Español"))

        self.title(APP_NAME)
        self.geometry("980x760")
        # Alto mínimo medido contra el estado más exigente del conversor
        # (formato MP4 + selector de calidad visible + panel de éxito con
        # una ruta larga de 2 líneas): ese contenido pide ~726px reales sin
        # contar la barra de título del SO. Con 560 (el valor anterior), esa
        # pantalla se recortaba por abajo y "Ver carpeta"/"Descargar otro
        # archivo" quedaban fuera del área visible de la ventana.
        self.minsize(860, 760)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Contenedor de contenido FIJO (columna 1, al lado del sidebar): se
        # gridea una sola vez acá y nunca se destruye ni cambia de gestor de
        # geometría. Las vistas post-onboarding (Hub/Converter/Settings)
        # viven DENTRO de él con `.place(relx=0, rely=0, relwidth=1,
        # relheight=1)` en vez de gridearse directamente.
        #
        # Por qué: `ViewTransition` animaba la vista con `.place()` y, al
        # terminar, la pasaba a `.grid()` para que siguiera el resize de la
        # ventana con normalidad. Confirmado con capturas en cámara lenta
        # (comparando cada frame real, no solo a velocidad normal): ese
        # cambio de gestor de geometría -- de `place` a `grid`, sin importar
        # si se llama `place_forget()` antes o no -- hace que el widget
        # desaparezca por completo durante un frame real en esta
        # combinación de Tk/customtkinter en macOS. Ese era el "segundo
        # parpadeo, después de cargar bien" que se reportó.
        #
        # Con este contenedor de por medio, la vista real NUNCA cambia de
        # gestor: siempre vive en `place()`, animada o quieta, y el
        # contenedor (que sí está en `grid()` con `sticky="nsew"`) es quien
        # responde al resize de la ventana. `relwidth=1, relheight=1` hace
        # que la vista ocupe todo el contenedor sin importar su tamaño.
        #
        # SetupView es la excepción: no tiene sidebar (ocupa las dos
        # columnas) y no pasa por `ViewTransition`, así que sigue grideada
        # directamente en la ventana como antes -- no sufre este bug.
        self._content = ctk.CTkFrame(self, fg_color="transparent")
        self._content.grid(row=0, column=1, sticky="nsew")

        self.sidebar = None
        self.current_view = None
        self._active_screen = None  # "hub" | "converter" | "settings" | "setup"

        if self.settings.get("onboarded"):
            self._show_hub()
        else:
            self._show_setup()

    # --- Navegación ---

    def _clear(self):
        # El sidebar NO se destruye acá -- ver el comentario en
        # `_with_sidebar` sobre por qué reconstruirlo en cada navegación
        # causaba un glitch visual real.
        if self.current_view is not None:
            self.current_view.destroy()
            self.current_view = None

    def _show_setup(self):
        self._active_screen = "setup"
        self._clear()
        self.current_view = SetupView(self, self.i18n, self.settings, self._on_setup_complete)
        self.current_view.grid(row=0, column=0, columnspan=2, sticky="nsew")

    def _on_setup_complete(self, settings):
        save_settings(settings)
        self._show_hub()

    def _with_sidebar(self, active_key):
        # El sidebar se crea UNA sola vez y se reutiliza en cada navegación
        # (antes se destruía y se recreaba en cada pantalla, igual que el
        # contenido). Un CTkButton recién creado dibuja su primer frame con
        # un ancho "adivinado" (el `width` del constructor, no el que le
        # termina dando `sticky="ew"` dentro del sidebar) y recién corrige
        # las esquinas redondeadas cuando el grid real se resuelve un
        # instante después -- ese es el frame con esquinas cuadradas que se
        # veía al volver de una herramienta al Hub. Con el sidebar
        # persistente, `set_active()` solo recolorea botones que ya tienen
        # su tamaño final desde hace rato, así que ese primer frame nunca
        # vuelve a ocurrir.
        if self.sidebar is None:
            self.sidebar = Sidebar(self, self.i18n, self._on_navigate, active=active_key)
            self.sidebar.grid(row=0, column=0, sticky="nsw")
        else:
            self.sidebar.set_active(active_key)

    def _on_navigate(self, key):
        if key == "tools":
            self._show_hub()
        elif key == "settings":
            self._show_settings()

    def _show_hub(self):
        # Construir la vista nueva ANTES de destruir la anterior (`_clear()`)
        # reduce al mínimo posible -- unas pocas líneas de Python, no una
        # espera real -- el instante en que la columna de contenido queda
        # vacía. Ver el comentario en `__init__` sobre por qué ese instante
        # vacío se notaba como un "flash" de color equivocado.
        #
        # `master=self._content` (no `self`): la vista vive dentro del
        # contenedor fijo, no gridada directamente -- ver el comentario en
        # `__init__` sobre por qué.
        new_view = HubView(self._content, self.i18n, self._show_converter)
        self._active_screen = "hub"
        self._clear()
        self._with_sidebar("tools")
        self.current_view = new_view
        self.current_view.place(relx=0, rely=0, relwidth=1, relheight=1)

    def _show_converter(self):
        # ConverterView es, de lejos, la vista con más widgets (entrada de
        # URL, toggle de formato, selector de calidad, botones, barra de
        # progreso, panel de éxito...) -- la más lenta de construir, y por
        # eso donde más se notaba el "pantallazo negro" del fondo del tema
        # sin configurar asomando durante ese instante. Construirla antes de
        # destruir la vista anterior es la mitigación que de verdad importa
        # acá (la de `__init__` cubre cualquier resto que no se pueda evitar).
        new_view = ConverterView(self._content, self.i18n, self.settings)
        self._active_screen = "converter"
        self._clear()
        self._with_sidebar("tools")
        self.current_view = new_view

        # Animación slide-in desde la derecha (estilo Apple), DENTRO del
        # contenedor de contenido -- el sidebar vive fuera de él, así que
        # nunca hace falta acotar manualmente dónde empieza el contenido.
        transition = ViewTransition(self.current_view)
        transition.animate_in()

    def _show_settings(self):
        new_view = SettingsView(
            self._content, self.i18n, self.settings, self._on_settings_change, self._on_language_change
        )
        self._active_screen = "settings"
        self._clear()
        self._with_sidebar("settings")
        self.current_view = new_view
        self.current_view.place(relx=0, rely=0, relwidth=1, relheight=1)

    def _on_settings_change(self, settings):
        save_settings(settings)

    # --- Cambio de idioma: reconstruye la pantalla activa con un "pestañeo" ---

    def _on_language_change(self, settings):
        save_settings(settings)
        self._flash_and_rebuild()

    def _rebuild_current_screen(self):
        {
            "setup": self._show_setup,
            "hub": self._show_hub,
            "converter": self._show_converter,
            "settings": self._show_settings,
        }.get(self._active_screen, self._show_hub)()

    def _flash_and_rebuild(self):
        """Cubre la ventana con un destello breve mientras se reconstruye la
        pantalla activa, para que el cambio de idioma no se sienta como un
        salto abrupto de texto."""
        overlay = ctk.CTkFrame(self, corner_radius=0, fg_color=COLORS["shadow_grey"])
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        overlay.lift()

        def _finish():
            # Único caso donde el sidebar persistente SÍ debe reconstruirse:
            # sus textos ("Herramientas"/"Configuración") están en el idioma
            # viejo y `set_active()` no los traduce. Se destruye acá, detrás
            # del destello que ya cubre este mismo instante, así que no
            # reintroduce el glitch que `_with_sidebar` evita en la
            # navegación normal.
            if self.sidebar is not None:
                self.sidebar.destroy()
                self.sidebar = None
            self._rebuild_current_screen()
            overlay.destroy()

        self.after(140, _finish)

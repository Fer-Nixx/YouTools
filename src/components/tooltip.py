"""Tooltip minimalista sin dependencias externas.

Un primer intento usaba un `tk.Toplevel` con `overrideredirect(True)` (el
patrón estándar de tooltip en Tkinter). Confirmado con una prueba aislada:
en esta combinación de Tk/Cocoa en macOS, `overrideredirect(True)` produce
una ventana que Tk considera perfectamente viva (`winfo_viewable`,
geometría y todo lo demás correctos) pero que el compositor de macOS
nunca llega a pintar en pantalla -- invisible tanto en captura de pantalla
completa como acotada a una región. Es una limitación conocida de Tk en
macOS moderno con ventanas sin decoración, no algo que se pueda arreglar
ajustando parámetros.

La solución que sí funciona: no crear ninguna ventana de sistema operativo
nueva. El "tooltip" es un `CTkLabel` más, hijo de la ventana raíz de la
app, posicionado con `.place()` (coordenadas absolutas dentro de esa
ventana) y elevado por encima de todo con `.lift()`. Limitación aceptada:
no puede dibujarse fuera de los bordes de la ventana de la app -- para
tooltips de la sidebar (que siempre tienen espacio de sobra a la derecha)
esto nunca es un problema real.
"""

import customtkinter as ctk

from ..config import COLORS, Fonts


class Tooltip:
    """Adjunta un tooltip de texto a un widget. Aparece tras `delay_ms` de
    hover sostenido (no en una pasada rápida del cursor) y se cierra al
    salir o al hacer clic."""

    DELAY_MS = 400

    def __init__(self, widget, text: str):
        self._widget = widget
        self._text = text
        self._after_id = None
        self._tip = None

        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")
        widget.bind("<Button-1>", self._on_leave, add="+")

    def _on_enter(self, _event=None):
        self._cancel_pending()
        self._after_id = self._widget.after(self.DELAY_MS, self._show)

    def _on_leave(self, _event=None):
        self._cancel_pending()
        self._hide()

    def _cancel_pending(self):
        if self._after_id is not None:
            try:
                self._widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _show(self):
        self._after_id = None
        if self._tip is not None or not self._widget.winfo_exists():
            return

        root = self._widget.winfo_toplevel()

        # Posición deseada, en coordenadas de pantalla (debajo del widget).
        target_x = self._widget.winfo_rootx() + self._widget.winfo_width() // 2
        target_y = self._widget.winfo_rooty() + self._widget.winfo_height() + 8

        tip = ctk.CTkLabel(
            root, text=self._text, font=(Fonts.family, 11),
            fg_color="#2A2A31", text_color=COLORS["text_dark"],
            corner_radius=6, height=26,
            # Un borde de 1px para que se distinga incluso si algo detrás
            # tuviera un color parecido -- ya nos mordió una vez no ponerlo.
        )
        tip.update_idletasks()

        # Convertir la posición de pantalla deseada a coordenadas relativas
        # a la ventana raíz, que es lo que `.place()` espera.
        rel_x = target_x - root.winfo_rootx() - tip.winfo_reqwidth() // 2
        rel_y = target_y - root.winfo_rooty()

        # No se sale de los bordes de la ventana (ver limitación en el
        # docstring del módulo): se acota al ancho disponible.
        rel_x = max(4, min(rel_x, root.winfo_width() - tip.winfo_reqwidth() - 4))

        tip.place(x=rel_x, y=rel_y)
        tip.lift()

        self._tip = tip

    def _hide(self):
        if self._tip is not None:
            try:
                self._tip.destroy()
            except Exception:
                pass
            self._tip = None

# YouTools

Suite de herramientas de escritorio para creadores, con una interfaz minimalista inspirada en el ecosistema Apple y pensada para modo oscuro. Por ahora incluye un conversor de YouTube a MP3/MP4; el resto del Hub queda reservado para las herramientas que se sumen más adelante.

## Funcionalidades

- Descarga videos de YouTube y conviértelos a **MP3** (solo audio) o **MP4** (video completo).
- Descarga siempre a la mejor calidad real disponible (hasta 4K), con un selector opcional de resolución.
- Valida el enlace antes de descargar y avisa con un mensaje claro si la URL no es de YouTube o la descarga falla.
- Permite cancelar una descarga en curso en cualquier momento.
- Recodifica automáticamente a H.264/AAC solo cuando hace falta, para que el MP4 se reproduzca sin problemas en QuickTime.
- Configuración inicial guiada: al abrir la app por primera vez se elige idioma y carpeta de descargas antes de entrar al Hub.
- Interfaz en **Español** e **Inglés**.
- Tema **Claro / Oscuro / Sistema**, con detección automática del tema del SO.
- Recuerda tu idioma, carpeta de descargas y tema entre sesiones.

El Hub de herramientas ya tiene espacio reservado (tarjetas deshabilitadas) para futuras herramientas, todavía sin definir.

## Requisitos (macOS)

- **Python 3.11+ con Tk moderno.** El Python que trae macOS por defecto usa una versión de Tk que se ve mal (bordes y tipografía deformados) con la interfaz de la app:

  ```
  brew install python-tk@3.11
  ```

- **ffmpeg**, necesario para fusionar video+audio (MP4) y extraer audio (MP3):

  ```
  brew install ffmpeg
  ```

## Instalación

```
cd YouTools
/opt/homebrew/bin/python3.11 -m venv venv
./venv/bin/pip install -r requirements.txt
```

## Uso

```
./venv/bin/python main.py
```

La primera vez se te pedirá elegir idioma y carpeta de descargas. Luego, desde el Hub de Herramientas, entra a **YouTube Converter**, pega el enlace, elige MP3 o MP4 y descarga.

## Stack

Python · [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) · [yt-dlp](https://github.com/yt-dlp/yt-dlp) · ffmpeg

## Autor

Fernando Contreras — [GitHub](https://github.com/Fer-Nixx) · [LinkedIn](https://www.linkedin.com/in/fernandocontrerasrojas) · [Buy Me a Coffee](https://buymeacoffee.com/fernixx)

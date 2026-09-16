"""Motor de descarga/conversión usando yt-dlp (Fase 3 del PRD).

Corre en un hilo aparte para no bloquear la UI de customtkinter, y reporta
progreso/errores mediante callbacks que la vista reenvía al hilo principal
con `.after(0, ...)`.
"""

import os
import re
import subprocess
import sys
import threading
from dataclasses import dataclass
from typing import Callable, Optional, Tuple

import yt_dlp
from yt_dlp.utils import DownloadCancelled

from .dependency_resolver import find_ffmpeg, find_ffprobe, missing_ffmpeg_message

YOUTUBE_URL_RE = re.compile(
    r"^(https?://)?(www\.)?(m\.)?(youtube\.com/(watch\?v=|shorts/|live/)|youtu\.be/)[\w-]+",
    re.IGNORECASE,
)

# yt-dlp incluye códigos de color ANSI en sus mensajes de error (pensados para
# la terminal). Hay que limpiarlos antes de mostrarlos en la UI de Tkinter.
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def is_valid_youtube_url(url: str) -> bool:
    return bool(url) and bool(YOUTUBE_URL_RE.match(url.strip()))


def _clean_error(message: str) -> str:
    return _ANSI_RE.sub("", message).replace("ERROR:", "").strip()


def _probe_codecs(filepath: str) -> Tuple[Optional[str], Optional[str]]:
    """Devuelve (códec de video, códec de audio) de un archivo usando ffprobe."""
    ffprobe_path = find_ffprobe()
    if ffprobe_path is None:
        return None, None

    def _first_codec(stream_selector: str) -> Optional[str]:
        try:
            result = subprocess.run(
                [
                    str(ffprobe_path), "-v", "error", "-select_streams", stream_selector,
                    "-show_entries", "stream=codec_name", "-of", "csv=p=0", filepath,
                ],
                capture_output=True, text=True, timeout=30,
            )
            value = result.stdout.strip()
            return value or None
        except Exception:
            return None

    return _first_codec("v:0"), _first_codec("a:0")


@dataclass
class DownloadResult:
    success: bool
    filepath: Optional[str] = None
    error: Optional[str] = None
    cancelled: bool = False


class Downloader:
    """Envuelve yt-dlp para descargar/convertir en un hilo aparte.

    Siempre pide la mejor calidad real disponible del video (sin tope de
    resolución): es una prioridad del proyecto por encima de cualquier
    ahorro de tiempo/espacio. A cambio, la descarga se puede cancelar en
    cualquier momento con `cancel()` -- necesario porque un 4K puede tardar
    varios minutos y el usuario debe poder frenarlo sin matar la app.
    """

    def __init__(
        self,
        on_progress: Callable[[float, str], None],
        on_finished: Callable[[DownloadResult], None],
    ):
        self.on_progress = on_progress
        self.on_finished = on_finished
        self._thread: Optional[threading.Thread] = None
        self._cancel_event = threading.Event()
        self._transcode_process: Optional[subprocess.Popen] = None

    def start(self, url: str, fmt: str, output_dir: str, max_height: Optional[int] = None) -> None:
        """fmt: 'mp3' o 'mp4'. max_height: tope de resolución (ej. 720) o None
        para la mejor disponible. Lanza la descarga en un hilo daemon."""
        self._cancel_event.clear()
        self._thread = threading.Thread(
            target=self._run, args=(url, fmt, output_dir, max_height), daemon=True
        )
        self._thread.start()

    def cancel(self) -> None:
        """Pide que la descarga/transcodeo en curso se detenga cuanto antes.

        La descarga de yt-dlp se corta desde `_hook` (única forma soportada
        de cancelarla a mitad de proceso); si ya se llegó al transcodeo con
        ffmpeg, se mata el proceso directamente.
        """
        self._cancel_event.set()
        if self._transcode_process is not None and self._transcode_process.poll() is None:
            self._transcode_process.terminate()

    def _run(self, url: str, fmt: str, output_dir: str, max_height: Optional[int] = None) -> None:
        ffmpeg_path = find_ffmpeg()
        if ffmpeg_path is None:
            self.on_finished(
                DownloadResult(success=False, error=missing_ffmpeg_message(sys.platform))
            )
            return

        os.makedirs(output_dir, exist_ok=True)
        outtmpl = os.path.join(output_dir, "%(title)s.%(ext)s")

        ydl_opts = {
            "outtmpl": outtmpl,
            "progress_hooks": [self._hook],
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            # Sin esto, yt-dlp hace su PROPIA búsqueda interna de ffmpeg en
            # el PATH -- independiente de la que acabamos de resolver acá
            # arriba. Si algún día se empaqueta un ffmpeg junto al
            # ejecutable, yt-dlp seguiría sin enterarse sin esta línea.
            "ffmpeg_location": str(ffmpeg_path),
        }

        if fmt == "mp3":
            ydl_opts.update(
                {
                    "format": "bestaudio/best",
                    "postprocessors": [
                        {
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": "mp3",
                            "preferredquality": "192",
                        }
                    ],
                }
            )
        else:  # mp4
            # Por encima de 1080p, YouTube casi siempre solo ofrece VP9/AV1
            # (no hay pista H.264 en esas resoluciones). Para poder llegar a
            # la calidad máxima real del video (1440p/4K), se descarga el
            # mejor video/audio disponibles en cualquier códec hasta la
            # altura pedida, y luego `_ensure_quicktime_compatible()`
            # convierte a H.264/AAC solo si hiciera falta (ver más abajo).
            height_filter = f"[height<={max_height}]" if max_height else ""
            ydl_opts.update(
                {
                    "format": (
                        f"bestvideo{height_filter}+bestaudio"
                        f"/best{height_filter}"
                        "/best"
                    ),
                    "merge_output_format": "mp4",
                }
            )

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filepath = ydl.prepare_filename(info)
                if fmt == "mp3":
                    filepath = os.path.splitext(filepath)[0] + ".mp3"

            if fmt == "mp4" and not self._cancel_event.is_set():
                filepath = self._ensure_quicktime_compatible(filepath)

            if self._cancel_event.is_set():
                self.on_finished(DownloadResult(success=False, cancelled=True))
            else:
                self.on_finished(DownloadResult(success=True, filepath=filepath))
        except DownloadCancelled:
            self.on_finished(DownloadResult(success=False, cancelled=True))
        except Exception as exc:  # yt-dlp puede lanzar varias excepciones distintas
            self.on_finished(DownloadResult(success=False, error=_clean_error(str(exc))))

    def _ensure_quicktime_compatible(self, filepath: str) -> str:
        """Si el video quedó en un códec que QuickTime no reproduce (VP9/AV1,
        habitual por encima de 1080p en YouTube), lo recodifica a H.264/AAC.

        Si ya está en H.264/AAC (el caso común hasta 1080p) no hace nada, para
        no perder tiempo/calidad recodificando de más.
        """
        vcodec, acodec = _probe_codecs(filepath)
        needs_transcode = vcodec not in (None, "h264") or acodec not in (None, "aac")

        ffmpeg_path = find_ffmpeg()
        if not needs_transcode or ffmpeg_path is None:
            return filepath

        self.on_progress(1.0, "transcoding")

        root, _ext = os.path.splitext(filepath)
        tmp_path = f"{root}.qt.mp4"
        cmd = [
            str(ffmpeg_path), "-y", "-i", filepath,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k",
            tmp_path,
        ]
        self._transcode_process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        self._transcode_process.communicate()
        returncode = self._transcode_process.returncode
        self._transcode_process = None

        if self._cancel_event.is_set():
            # Se pidió cancelar: descartar el archivo temporal a medio
            # transcodear y dejar el original (que igual no se va a entregar).
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            return filepath

        if returncode == 0 and os.path.exists(tmp_path):
            os.replace(tmp_path, filepath)
        # Si ffmpeg falla, se conserva el archivo original (mejor entregar
        # algo, aunque no sea compatible con QuickTime, que nada).
        return filepath

    def _hook(self, d: dict) -> None:
        if self._cancel_event.is_set():
            raise DownloadCancelled("Descarga cancelada por el usuario")
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes", 0)
            pct = (downloaded / total) if total else 0.0
            self.on_progress(min(pct, 1.0), "downloading")
        elif d.get("status") == "finished":
            self.on_progress(1.0, "processing")


class QualityProbe:
    """Consulta (sin descargar) las resoluciones reales disponibles de un video.

    Incluye TODAS las resoluciones que YouTube ofrece para ese video, sin
    importar el códec (h264/vp9/av1): por encima de 1080p YouTube casi nunca
    publica H.264, así que filtrar solo por ese códec dejaba fuera 1440p/4K
    aunque el video sí los tuviera. `Downloader` se encarga después de
    convertir a H.264/AAC si hace falta para que se pueda reproducir.

    Corre en un hilo aparte porque requiere una llamada de red a YouTube para
    leer los metadatos/formatos, igual que hace Downloader para descargar.
    """

    def __init__(self, on_done: Callable[[list, Optional[str]], None]):
        self.on_done = on_done

    def start(self, url: str) -> None:
        threading.Thread(target=self._run, args=(url,), daemon=True).start()

    def _run(self, url: str) -> None:
        try:
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "noplaylist": True,
                "skip_download": True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
            heights = set()
            for f in info.get("formats") or []:
                vcodec = f.get("vcodec") or "none"
                height = f.get("height")
                if height and vcodec != "none":
                    heights.add(int(height))
            self.on_done(sorted(heights, reverse=True), None)
        except Exception as exc:
            self.on_done([], _clean_error(str(exc)))

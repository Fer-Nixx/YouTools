"""Tests para la lógica de decisión pura de `dependency_resolver` (candidato
"DependencyResolver" del reporte de arquitectura multiplataforma).

Estos tests cruzan el seam público de las funciones puras -- no tocan
`sys.platform`, `sys.frozen` ni `shutil.which` de verdad (eso es
responsabilidad de `find_ffmpeg()`/`find_ffprobe()`, el wrapper delgado que
se verifica con la app real, no con tests unitarios).
"""

import unittest

from src.core.dependency_resolver import missing_ffmpeg_message, resolve_binary_path


class ResolveBinaryPathTests(unittest.TestCase):
    def test_bundled_binary_wins_over_path_when_both_exist(self):
        self.assertEqual(
            resolve_binary_path(
                bundled_exists=True,
                bundled_path="/Applications/YouTools.app/Contents/Resources/ffmpeg",
                which_result="/opt/homebrew/bin/ffmpeg",
            ),
            "/Applications/YouTools.app/Contents/Resources/ffmpeg",
        )

    def test_falls_back_to_path_when_no_bundled_binary(self):
        self.assertEqual(
            resolve_binary_path(
                bundled_exists=False,
                bundled_path=None,
                which_result="/opt/homebrew/bin/ffmpeg",
            ),
            "/opt/homebrew/bin/ffmpeg",
        )

    def test_falls_back_to_path_when_bundled_candidate_does_not_exist_on_disk(self):
        self.assertEqual(
            resolve_binary_path(
                bundled_exists=False,
                bundled_path="C:\\Program Files\\YouTools\\ffmpeg.exe",
                which_result="C:\\ffmpeg\\bin\\ffmpeg.exe",
            ),
            "C:\\ffmpeg\\bin\\ffmpeg.exe",
        )

    def test_returns_none_when_nothing_is_found(self):
        self.assertIsNone(
            resolve_binary_path(bundled_exists=False, bundled_path=None, which_result=None)
        )

    def test_bundled_exists_flag_without_a_path_is_treated_as_not_bundled(self):
        # Defensivo: en la práctica el wrapper siempre pasa los dos juntos,
        # pero la función pura no debería reventar ni "inventar" una ruta.
        self.assertEqual(
            resolve_binary_path(bundled_exists=True, bundled_path=None, which_result="/usr/bin/ffmpeg"),
            "/usr/bin/ffmpeg",
        )


class MissingFfmpegMessageTests(unittest.TestCase):
    def test_macos_message_mentions_homebrew(self):
        message = missing_ffmpeg_message("darwin")
        self.assertIn("brew install ffmpeg", message)

    def test_windows_message_does_not_mention_homebrew(self):
        message = missing_ffmpeg_message("win32")
        self.assertNotIn("brew", message.lower())
        self.assertIn("ffmpeg", message.lower())

    def test_other_platforms_get_a_generic_message(self):
        message = missing_ffmpeg_message("linux")
        self.assertNotIn("brew", message.lower())
        self.assertIn("ffmpeg", message.lower())


if __name__ == "__main__":
    unittest.main()

"""Tests para las reglas de decisión puras extraídas de ConverterView.

Estos tests cruzan el seam público de `src.core.conversion_rules`: no tocan
Tk, CustomTkinter ni threads. El objetivo es fijar el comportamiento actual
de ConverterView antes/después del refactor (candidato 2 del reporte de
arquitectura), no diseñar comportamiento nuevo.
"""

import os
import unittest

from src.core.conversion_rules import (
    build_quality_options,
    resolve_max_height,
    resolve_output_dir,
)


class ResolveOutputDirTests(unittest.TestCase):
    def test_uses_configured_download_path_when_present(self):
        settings = {"download_path": "/Volumes/External/youtools"}
        self.assertEqual(resolve_output_dir(settings), "/Volumes/External/youtools")

    def test_falls_back_to_home_downloads_when_not_configured(self):
        settings = {"download_path": ""}
        self.assertEqual(resolve_output_dir(settings), os.path.expanduser("~/Downloads"))

    def test_falls_back_to_home_downloads_when_key_missing(self):
        self.assertEqual(resolve_output_dir({}), os.path.expanduser("~/Downloads"))


class ResolveMaxHeightTests(unittest.TestCase):
    def test_mp3_never_caps_height_even_if_a_quality_was_picked(self):
        quality_heights = {"Mejor calidad": None, "1080p": 1080}
        self.assertIsNone(resolve_max_height("mp3", quality_heights, "1080p"))

    def test_mp4_resolves_selected_label_to_its_height(self):
        quality_heights = {"Mejor calidad": None, "1080p": 1080, "720p": 720}
        self.assertEqual(resolve_max_height("mp4", quality_heights, "1080p"), 1080)

    def test_mp4_best_quality_label_resolves_to_none(self):
        quality_heights = {"Mejor calidad": None, "1080p": 1080}
        self.assertIsNone(resolve_max_height("mp4", quality_heights, "Mejor calidad"))


class BuildQualityOptionsTests(unittest.TestCase):
    def test_no_heights_found_returns_only_the_best_option(self):
        self.assertEqual(
            build_quality_options([], "Mejor calidad"),
            {"Mejor calidad": None},
        )

    def test_heights_are_labeled_in_p_and_keep_the_given_order(self):
        result = build_quality_options([2160, 1080, 720], "Mejor calidad")
        self.assertEqual(
            list(result.items()),
            [("Mejor calidad", None), ("2160p", 2160), ("1080p", 1080), ("720p", 720)],
        )


if __name__ == "__main__":
    unittest.main()

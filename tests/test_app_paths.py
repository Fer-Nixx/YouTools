"""Tests para la lógica de decisión pura de `app_paths` (candidato "AppPaths"
del reporte de arquitectura multiplataforma).

Igual que en `dependency_resolver`: las funciones puras se testean acá sin
tocar `sys.platform`/`Path.home()`/variables de entorno reales -- eso es
responsabilidad de `config_dir()`/`resource_path()`, el wrapper delgado que
se verifica con el sistema real, no con tests unitarios.

`resolve_config_dir` arma el string con `PureWindowsPath`/`PurePosixPath`
(no con `Path` real) a propósito: así el resultado usa las barras
correctas del SO que describe el parámetro `platform`, sin importar en qué
SO esté corriendo el test -- lo mismo que hace posible testear "qué pasaría
en Windows" desde una Mac.
"""

import unittest

from src.core.app_paths import resolve_config_dir, resolve_resource_dir


class ResolveConfigDirTests(unittest.TestCase):
    def test_macos_uses_a_dotfolder_in_home(self):
        self.assertEqual(
            resolve_config_dir(platform="darwin", home="/Users/fernandoc", appdata=None),
            "/Users/fernandoc/.youtools",
        )

    def test_linux_uses_the_same_dotfolder_convention_as_macos(self):
        self.assertEqual(
            resolve_config_dir(platform="linux", home="/home/fernando", appdata=None),
            "/home/fernando/.youtools",
        )

    def test_windows_uses_appdata_without_a_leading_dot(self):
        self.assertEqual(
            resolve_config_dir(
                platform="win32",
                home="C:\\Users\\Fernando",
                appdata="C:\\Users\\Fernando\\AppData\\Roaming",
            ),
            "C:\\Users\\Fernando\\AppData\\Roaming\\YouTools",
        )

    def test_windows_falls_back_to_home_without_a_dot_when_appdata_is_missing(self):
        self.assertEqual(
            resolve_config_dir(platform="win32", home="C:\\Users\\Fernando", appdata=None),
            "C:\\Users\\Fernando\\YouTools",
        )


class ResolveResourceDirTests(unittest.TestCase):
    def test_frozen_app_with_meipass_uses_the_pyinstaller_temp_dir(self):
        self.assertEqual(
            resolve_resource_dir(frozen=True, meipass="/tmp/_MEI123456", source_root="/repo/src"),
            "/tmp/_MEI123456",
        )

    def test_running_from_source_always_uses_the_source_root(self):
        # Defensivo: `meipass` no debería existir corriendo desde código
        # fuente, pero si por lo que sea estuviera seteado, no debe ganar.
        self.assertEqual(
            resolve_resource_dir(frozen=False, meipass="/tmp/_MEI123456", source_root="/repo/src"),
            "/repo/src",
        )

    def test_frozen_without_meipass_falls_back_to_source_root(self):
        self.assertEqual(
            resolve_resource_dir(frozen=True, meipass=None, source_root="/repo/src"),
            "/repo/src",
        )


if __name__ == "__main__":
    unittest.main()

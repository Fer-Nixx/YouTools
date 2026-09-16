"""Punto de entrada de YouTools.

Ejecutar con el intérprete del entorno virtual, por ejemplo:
    ./venv/bin/python main.py
"""

from src.app import App


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()

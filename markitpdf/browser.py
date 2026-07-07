"""Localiza un navegador Chromium headless instalado (Edge o Chrome) en Windows/Linux/macOS."""

from __future__ import annotations

import shutil
from pathlib import Path

CANDIDATE_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/usr/bin/microsoft-edge",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium-browser",
    "/usr/bin/chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]

CANDIDATE_NAMES = ["msedge", "chrome", "google-chrome", "chromium-browser", "chromium"]


class BrowserNotFoundError(RuntimeError):
    pass


def find_browser() -> str:
    """Devuelve la ruta a un ejecutable Chromium headless disponible.

    Prioriza rutas absolutas conocidas de Windows y luego busca en PATH.
    """
    for path in CANDIDATE_PATHS:
        if Path(path).exists():
            return path

    for name in CANDIDATE_NAMES:
        found = shutil.which(name)
        if found:
            return found

    raise BrowserNotFoundError(
        "No se encontró Microsoft Edge, Google Chrome o Chromium instalado. "
        "MarkItPDF requiere un navegador Chromium para renderizar PDFs. "
        "Instala Microsoft Edge (viene preinstalado en Windows) o Google Chrome."
    )

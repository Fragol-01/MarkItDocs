"""Integración LaTeX: detección de motor, compilación .tex → PDF y descarga de Tectonic.

Misma filosofía que browser.py con Edge/Chrome: usar lo que el usuario ya tiene
instalado (MiKTeX/TeX Live) y ofrecer Tectonic (un solo .exe, licencia MIT) como
respaldo descargable sin permisos de administrador.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

TEX_SUFFIXES = {".tex"}

COMPILE_TIMEOUT_SECONDS = 600  # la primera compilación puede instalar paquetes

#: Carpeta local de la app donde se instala tectonic.exe descargado (sin admin).
APP_BIN_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "MarkItDocs" / "bin"

_MIKTEX_HINT_DIRS = [
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "MiKTeX" / "miktex" / "bin" / "x64",
    Path(r"C:\Program Files\MiKTeX\miktex\bin\x64"),
]

#: xelatex primero: fuentes del sistema vía fontspec (lo que usan las plantillas).
_ENGINE_ORDER = ["xelatex", "lualatex", "tectonic", "pdflatex"]

#: Si el documento usa esto, los motores clásicos necesitan una segunda pasada.
_NEEDS_RERUN_RE = re.compile(r"\\(tableofcontents|listoffigures|listoftables|bibliography|ref\{)")

_TECTONIC_RELEASES_API = (
    "https://api.github.com/repos/tectonic-typesetting/tectonic/releases/latest"
)


class LatexNotFoundError(RuntimeError):
    pass


class LatexCompileError(RuntimeError):
    """Error de compilación con extracto del log para diagnóstico."""

    def __init__(self, message: str, log_excerpt: str = "") -> None:
        super().__init__(message)
        self.log_excerpt = log_excerpt


@dataclass(frozen=True)
class LatexEngine:
    name: str
    path: str

    @property
    def is_miktex(self) -> bool:
        return "miktex" in self.path.lower()

    @property
    def is_tectonic(self) -> bool:
        return self.name == "tectonic"


def find_latex_engine() -> LatexEngine:
    """Devuelve el primer motor LaTeX disponible (xelatex > lualatex > tectonic > pdflatex).

    Busca en PATH, en las rutas típicas de MiKTeX y en la carpeta local de la app
    (destino de ``download_tectonic``).
    """
    for name in _ENGINE_ORDER:
        found = shutil.which(name)
        if found:
            return LatexEngine(name=name, path=found)
        candidates = [d / f"{name}.exe" for d in _MIKTEX_HINT_DIRS if str(d)]
        if name == "tectonic":
            candidates.insert(0, APP_BIN_DIR / "tectonic.exe")
        for cand in candidates:
            if cand.exists():
                return LatexEngine(name=name, path=str(cand))
    raise LatexNotFoundError(
        "No se encontró ningún motor LaTeX (xelatex, lualatex, tectonic o pdflatex). "
        "Instala MiKTeX (https://miktex.org) o usa el botón 'Descargar Tectonic' "
        "de la app (~30 MB, sin permisos de administrador)."
    )


def _extract_log_errors(log_text: str, max_errors: int = 3) -> str:
    """Extrae las líneas '!' del .log de LaTeX con dos líneas de contexto."""
    lines = log_text.splitlines()
    chunks: list[str] = []
    for i, line in enumerate(lines):
        if line.startswith("!"):
            chunks.append("\n".join(lines[i : i + 3]))
            if len(chunks) >= max_errors:
                break
    return "\n---\n".join(chunks)


def compile_tex(
    tex_path: Path | str,
    output_pdf: Path | str | None = None,
    engine: LatexEngine | None = None,
    extra_runs: int | None = None,
) -> Path:
    """Compila un .tex a PDF y devuelve la ruta del PDF generado.

    cwd = carpeta del .tex (para que funcionen \\includegraphics y .cls relativos).
    Los auxiliares (.aux/.log) se quedan en un directorio temporal.
    """
    tex_path = Path(tex_path).resolve()
    if not tex_path.exists():
        raise FileNotFoundError(f"No existe el archivo: {tex_path}")
    if tex_path.suffix.lower() not in TEX_SUFFIXES:
        raise ValueError(f"'{tex_path.name}' no es un archivo .tex")
    engine = engine or find_latex_engine()

    if output_pdf is None:
        output_pdf = tex_path.with_suffix(".pdf")
    output_pdf = Path(output_pdf).resolve()
    output_pdf.parent.mkdir(parents=True, exist_ok=True)

    source = tex_path.read_text(encoding="utf-8", errors="replace")
    if extra_runs is None:
        extra_runs = 1 if (not engine.is_tectonic and _NEEDS_RERUN_RE.search(source)) else 0

    # ignore_cleanup_errors: en Windows el .log puede seguir bloqueado un instante
    with tempfile.TemporaryDirectory(prefix="markitdocs_tex_", ignore_cleanup_errors=True) as tmp:
        tmp_dir = Path(tmp)
        if engine.is_tectonic:
            command = [engine.path, "--chatter", "minimal", "-o", str(tmp_dir), str(tex_path)]
            runs = 1  # tectonic repite pasadas él solo
        else:
            command = [
                engine.path,
                "-interaction=nonstopmode",
                "-halt-on-error",
                f"-output-directory={tmp_dir}",
            ]
            if engine.is_miktex:
                command.append("--enable-installer")  # auto-instala paquetes sin preguntar
            command.append(str(tex_path))
            runs = 1 + extra_runs

        result = None
        for _ in range(runs):
            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    cwd=tex_path.parent,
                    timeout=COMPILE_TIMEOUT_SECONDS,
                    # En el .exe sin consola el stdin heredado es inválido y puede
                    # colgar a xelatex/MiKTeX; DEVNULL + sin ventana lo evita.
                    stdin=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except subprocess.TimeoutExpired as exc:
                raise LatexCompileError(
                    f"La compilación LaTeX excedió {COMPILE_TIMEOUT_SECONDS}s. "
                    "La primera vez puede tardar por la instalación de paquetes; reintenta."
                ) from exc
            if result.returncode != 0:
                break

        produced = tmp_dir / f"{tex_path.stem}.pdf"
        if result is None or result.returncode != 0 or not produced.exists():
            log_file = tmp_dir / f"{tex_path.stem}.log"
            excerpt = ""
            if log_file.exists():
                excerpt = _extract_log_errors(
                    log_file.read_text(encoding="utf-8", errors="replace")
                )
            if not excerpt and result is not None:
                excerpt = (result.stderr or result.stdout or "").strip()[-1200:]
            raise LatexCompileError(
                f"Error compilando '{tex_path.name}' con {engine.name}.\n{excerpt}",
                log_excerpt=excerpt,
            )
        shutil.move(str(produced), str(output_pdf))

    return output_pdf


def _tectonic_asset_marker() -> str:
    if sys.platform == "win32":
        return "x86_64-pc-windows-msvc"
    if sys.platform == "darwin":
        return "apple-darwin"
    return "x86_64-unknown-linux"


def download_tectonic(progress_cb=None) -> Path:
    """Descarga el último release de Tectonic (MIT) a APP_BIN_DIR y devuelve su ruta.

    progress_cb(descargado_bytes, total_bytes) es opcional (para barra de progreso).
    """
    request = urllib.request.Request(
        _TECTONIC_RELEASES_API, headers={"User-Agent": "MarkItDocs"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        release = json.loads(response.read().decode("utf-8"))

    marker = _tectonic_asset_marker()
    asset = next(
        (
            a
            for a in release.get("assets", [])
            if marker in a["name"] and a["name"].endswith((".zip", ".tar.gz"))
        ),
        None,
    )
    if asset is None:
        raise RuntimeError(
            f"El release {release.get('tag_name')} de Tectonic no tiene binario para {marker}."
        )

    APP_BIN_DIR.mkdir(parents=True, exist_ok=True)
    exe_name = "tectonic.exe" if sys.platform == "win32" else "tectonic"
    target = APP_BIN_DIR / exe_name

    with tempfile.TemporaryDirectory(prefix="markitdocs_dl_") as tmp:
        archive = Path(tmp) / asset["name"]
        req = urllib.request.Request(
            asset["browser_download_url"], headers={"User-Agent": "MarkItDocs"}
        )
        with urllib.request.urlopen(req, timeout=120) as resp, open(archive, "wb") as fh:
            total = int(resp.headers.get("Content-Length") or 0)
            done = 0
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                fh.write(chunk)
                done += len(chunk)
                if progress_cb:
                    progress_cb(done, total)
        if archive.suffix == ".zip":
            with zipfile.ZipFile(archive) as zf:
                member = next(n for n in zf.namelist() if Path(n).name == exe_name)
                with zf.open(member) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst)
        else:  # .tar.gz (linux/mac)
            import tarfile

            with tarfile.open(archive) as tf:
                member = next(m for m in tf.getmembers() if Path(m.name).name == exe_name)
                extracted = tf.extractfile(member)
                assert extracted is not None
                with open(target, "wb") as dst:
                    shutil.copyfileobj(extracted, dst)
            target.chmod(0o755)

    return target

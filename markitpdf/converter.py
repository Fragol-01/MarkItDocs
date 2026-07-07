"""Motor de conversión Markdown/HTML -> PDF usando Chromium headless (Edge/Chrome)."""

from __future__ import annotations

import html as html_escape
import json
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import markdown as markdown_lib

from .browser import find_browser

THEMES_DIR = Path(__file__).parent / "themes"

RENDER_TIMEOUT_SECONDS = 60

MARKDOWN_SUFFIXES = {".md", ".markdown"}
HTML_SUFFIXES = {".html", ".htm"}

HTML_TEMPLATE = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
{css}
{theme_vars}
</style>
</head>
<body>
{body}
</body>
</html>
"""

_BODY_RE = re.compile(r"<body[^>]*>(.*)</body>", re.IGNORECASE | re.DOTALL)
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_H1_MD_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


def available_themes() -> list[str]:
    """Devuelve los temas disponibles ordenados (los que tienen un .css asociado)."""
    return sorted(p.stem for p in THEMES_DIR.glob("*.css"))


@dataclass(frozen=True)
class ConversionResult:
    output_path: Path
    theme: str
    source_count: int = 1


@dataclass(frozen=True)
class ThemeMetadata:
    """Metadatos estructurados de un tema (cargados desde .json o .yaml opcional)."""
    name: str
    description: str = ""
    version: str = "1.0.0"
    css_file: str = ""
    fonts: dict = field(default_factory=dict)
    colors: dict = field(default_factory=dict)
    sizes: dict = field(default_factory=dict)
    page: dict = field(default_factory=dict)

    @classmethod
    def empty(cls) -> "ThemeMetadata":
        return cls(name="default")

    def to_css_vars(self) -> str:
        """Convierte los metadatos del tema a variables CSS en :root."""
        lines = [":root {"]
        for key, value in self.fonts.items():
            lines.append(f"  --theme-font-{key}: '{value}';")
        for key, value in self.colors.items():
            lines.append(f"  --theme-color-{key}: {value};")
        for key, value in self.sizes.items():
            lines.append(f"  --theme-size-{key}: {value};")
        if self.page:
            for key, value in self.page.items():
                lines.append(f"  --theme-page-{key}: {value};")
        lines.append("}")
        return "\n".join(lines)


def _load_theme_metadata(theme_name: str) -> ThemeMetadata:
    """Carga la metadata opcional de un tema (.json o .yaml al lado del .css)."""
    for suffix in (".json", ".yaml", ".yml"):
        meta_path = THEMES_DIR / f"{theme_name}{suffix}"
        if meta_path.exists():
            try:
                if suffix == ".json":
                    data = json.loads(meta_path.read_text(encoding="utf-8"))
                else:
                    data = _read_yaml(meta_path)
            except Exception as exc:  # pragma: no cover - malformed theme
                return ThemeMetadata(name=theme_name, description=f"(metadata inválida: {exc})")
            return ThemeMetadata(
                name=data.get("name", theme_name),
                description=data.get("description", ""),
                version=str(data.get("version", "1.0.0")),
                css_file=data.get("css", f"{theme_name}.css"),
                fonts=data.get("fonts", {}) or {},
                colors=data.get("colors", {}) or {},
                sizes=data.get("sizes", {}) or {},
                page=data.get("page", {}) or {},
            )
    return ThemeMetadata(name=theme_name)


def _read_yaml(path: Path) -> dict:
    """Lee un YAML con un parser mínimo (evita depender de PyYAML)."""
    try:
        import yaml  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            f"Para cargar {path.name} instala PyYAML: pip install pyyaml"
        ) from exc
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_theme_css(theme: str) -> str:
    themes = available_themes()
    if theme not in themes:
        raise ValueError(
            f"Tema '{theme}' no existe. Temas disponibles: {', '.join(themes)}"
        )
    return (THEMES_DIR / f"{theme}.css").read_text(encoding="utf-8")


def _markdown_to_html_body(markdown_text: str) -> str:
    return markdown_lib.markdown(
        markdown_text,
        extensions=["extra", "tables", "fenced_code", "attr_list", "sane_lists", "toc", "codehilite"],
        extension_configs={"codehilite": {"noclasses": True}},
        output_format="html5",
    )


def _html_document_to_body(html_text: str) -> str:
    """Extrae el contenido del <body> de un documento HTML completo.

    Si el archivo es un fragmento sin <body>, se usa tal cual.
    """
    match = _BODY_RE.search(html_text)
    return match.group(1) if match else html_text


def _extract_title(source_text: str, source_path: Path) -> str:
    if source_path.suffix.lower() in HTML_SUFFIXES:
        match = _TITLE_RE.search(source_text)
        if match and match.group(1).strip():
            return html_escape.escape(match.group(1).strip())
    else:
        match = _H1_MD_RE.search(source_text)
        if match:
            return html_escape.escape(match.group(1).strip())
    return html_escape.escape(source_path.stem)


def _source_to_body(source_path: Path) -> str:
    """Lee un archivo .md o .html y devuelve HTML listo para incrustar en el body."""
    text = source_path.read_text(encoding="utf-8")
    if source_path.suffix.lower() in HTML_SUFFIXES:
        return _html_document_to_body(text)
    return _markdown_to_html_body(text)


def _merge_bodies(bodies: list[str], page_break_class: str = "__mip_pagebreak__") -> str:
    """Une varios bloques HTML intercalando un separador de página explícito."""
    page_break = f'<hr class="{page_break_class}">'
    return page_break.join(bodies)


class MarkdownToPdfConverter:
    """Convierte uno o varios archivos Markdown/HTML a PDF renderizando con Chromium headless."""

    def __init__(self, theme: str = "professional", browser_path: str | None = None) -> None:
        self.theme = theme
        self.css = _load_theme_css(theme)
        self.metadata = _load_theme_metadata(theme)
        self.browser_path = browser_path or find_browser()

    def convert(self, source_path: Path, output_path: Path | None = None) -> ConversionResult:
        """Convierte un único archivo. Mantener compat con la API anterior."""
        return self.convert_many([source_path], output_path)

    def convert_many(
        self,
        source_paths: list[Path],
        output_path: Path | None = None,
    ) -> ConversionResult:
        """Convierte varios archivos en un solo PDF, en el orden recibido.

        Cada archivo empieza en una página nueva gracias a ``<hr class=__mip_pagebreak__>``
        y la regla CSS ``hr.__mip_pagebreak__ { page-break-after: always; }`` que el
        convertidor añade a la hoja de estilo activa.
        """
        if not source_paths:
            raise ValueError("convert_many requiere al menos un archivo de entrada.")

        resolved: list[Path] = []
        for raw in source_paths:
            path = Path(raw).resolve()
            if not path.exists():
                raise FileNotFoundError(f"No existe el archivo de entrada: {path}")
            suffix = path.suffix.lower()
            if suffix not in MARKDOWN_SUFFIXES | HTML_SUFFIXES:
                allowed = ", ".join(sorted(MARKDOWN_SUFFIXES | HTML_SUFFIXES))
                raise ValueError(f"'{path.name}' no es una entrada soportada ({allowed}).")
            resolved.append(path)

        if output_path is None:
            first = resolved[0]
            output_path = first.with_suffix(".pdf")
        output_path = Path(output_path).resolve()

        bodies = [_source_to_body(p) for p in resolved]
        combined = _merge_bodies(bodies)
        title = _extract_title(resolved[0].read_text(encoding="utf-8"), resolved[0])

        page_break_css = (
            "\nhr.__mip_pagebreak__ { page-break-after: always; "
            "border: 0; height: 0; margin: 0; padding: 0; }\n"
        )
        css_with_breaks = self.css + page_break_css

        full_html = HTML_TEMPLATE.format(
            title=title,
            css=css_with_breaks,
            theme_vars=self.metadata.to_css_vars(),
            body=combined,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            html_path = Path(tmp_dir) / "document.html"
            html_path.write_text(full_html, encoding="utf-8")
            self._render_pdf(html_path, output_path)

        return ConversionResult(
            output_path=output_path,
            theme=self.theme,
            source_count=len(resolved),
        )

    def _render_pdf(self, html_path: Path, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        command = [
            self.browser_path,
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={output_path}",
            "--no-sandbox",
            str(html_path),
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=RENDER_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(
                f"El renderizado de PDF excedió {RENDER_TIMEOUT_SECONDS}s. "
                "El documento puede ser demasiado grande o el navegador quedó bloqueado."
            ) from exc

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError(
                f"Chromium no generó el PDF. stderr: {result.stderr.strip()[:500]}"
            )


def convert_markdown_to_pdf(
    source_path: Path,
    output_path: Path | None = None,
    theme: str = "professional",
) -> Path:
    """API pública de conveniencia: convierte un .md/.html a .pdf con el tema dado."""
    converter = MarkdownToPdfConverter(theme=theme)
    result = converter.convert(source_path, output_path)
    return result.output_path


def convert_many_to_pdf(
    source_paths: list[Path],
    output_path: Path | None = None,
    theme: str = "professional",
) -> Path:
    """API pública de conveniencia: une varios .md/.html en un único PDF."""
    converter = MarkdownToPdfConverter(theme=theme)
    result = converter.convert_many(source_paths, output_path)
    return result.output_path

"""Self-check de humo del subpaquete markitpdf (MD/HTML -> PDF).

Los tests que renderizan PDF requieren un navegador Chromium (Edge/Chrome);
si no hay ninguno instalado se omiten con un aviso en vez de fallar.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from markitpdf import (  # noqa: E402
    BrowserNotFoundError,
    MarkdownToPdfConverter,
    available_themes,
    convert_many_to_pdf,
    convert_markdown_to_pdf,
    find_browser,
)
from markitpdf.converter import (  # noqa: E402
    _extract_title,
    _html_document_to_body,
    _load_theme_metadata,
)


def _browser_available() -> bool:
    try:
        find_browser()
        return True
    except BrowserNotFoundError:
        return False


def test_available_themes_includes_defaults():
    themes = available_themes()
    assert "professional" in themes
    assert "minimal" in themes


def test_theme_metadata_loads_from_json():
    meta = _load_theme_metadata("professional")
    assert meta.name == "Professional"
    assert meta.colors.get("title") == "#1F4E79"
    css_vars = meta.to_css_vars()
    assert "--theme-color-title" in css_vars


def test_html_body_extraction():
    full = "<html><head><title>T</title></head><body><p>hola</p></body></html>"
    assert _html_document_to_body(full) == "<p>hola</p>"
    fragment = "<p>solo fragmento</p>"
    assert _html_document_to_body(fragment) == fragment


def test_title_extraction():
    html_path = Path("x.html")
    md_path = Path("x.md")
    assert _extract_title("<title>Mi título</title>", html_path) == "Mi título"
    assert _extract_title("# Encabezado MD\ntexto", md_path) == "Encabezado MD"
    assert _extract_title("sin título", md_path) == "x"


def test_unknown_theme_raises():
    try:
        MarkdownToPdfConverter(theme="no_existe")
    except (ValueError, BrowserNotFoundError) as exc:
        assert isinstance(exc, ValueError) or not _browser_available()
    else:
        raise AssertionError("Se esperaba ValueError para tema inexistente")


def test_single_md_to_pdf():
    if not _browser_available():
        print("SKIP: sin navegador Chromium")
        return
    with tempfile.TemporaryDirectory() as tmp_dir:
        md = Path(tmp_dir) / "a.md"
        md.write_text("# Hola PDF\n\nContenido de prueba.\n", encoding="utf-8")
        out = convert_markdown_to_pdf(md, Path(tmp_dir) / "a.pdf")
        assert out.exists() and out.stat().st_size > 1000


def test_merged_pdf_from_md_and_html():
    if not _browser_available():
        print("SKIP: sin navegador Chromium")
        return
    with tempfile.TemporaryDirectory() as tmp_dir:
        md = Path(tmp_dir) / "01.md"
        md.write_text("# Parte 1\n\nuno\n", encoding="utf-8")
        html = Path(tmp_dir) / "02.html"
        html.write_text("<h1>Parte 2</h1><p>dos</p>", encoding="utf-8")
        out = convert_many_to_pdf([md, html], Path(tmp_dir) / "unido.pdf", theme="minimal")
        assert out.exists() and out.stat().st_size > 1000


if __name__ == "__main__":
    test_available_themes_includes_defaults()
    print("OK: test_available_themes_includes_defaults")
    test_theme_metadata_loads_from_json()
    print("OK: test_theme_metadata_loads_from_json")
    test_html_body_extraction()
    print("OK: test_html_body_extraction")
    test_title_extraction()
    print("OK: test_title_extraction")
    test_unknown_theme_raises()
    print("OK: test_unknown_theme_raises")
    test_single_md_to_pdf()
    print("OK: test_single_md_to_pdf")
    test_merged_pdf_from_md_and_html()
    print("OK: test_merged_pdf_from_md_and_html")
    print("Todos los self-checks de markitpdf pasaron.")

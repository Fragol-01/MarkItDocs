"""Self-checks de la vía LaTeX, plantillas, vista previa y diseñador de temas.

Los tests que compilan LaTeX se omiten si no hay motor; los de preview se
omiten si no hay navegador Chromium. El resto corre siempre (puro Python).
"""

import copy
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from markitpdf import (  # noqa: E402
    BrowserNotFoundError,
    LatexNotFoundError,
    available_latex_templates,
    convert_markdown_via_latex,
    find_browser,
    get_latex_template_meta,
    instantiate_starter,
    markdown_to_latex_body,
)
from markitpdf.latex import compile_tex, find_latex_engine  # noqa: E402
from markitpdf.textemplates import render_latex_template  # noqa: E402
from markitpdf.themebuilder import (  # noqa: E402
    DEFAULT_MODEL,
    build_css,
    model_from_theme,
    theme_metadata_dict,
)


def _latex_available() -> bool:
    try:
        find_latex_engine()
        return True
    except LatexNotFoundError:
        return False


def _browser_available() -> bool:
    try:
        find_browser()
        return True
    except BrowserNotFoundError:
        return False


def test_md2tex_core_elements():
    body = markdown_to_latex_body(
        "# Uno\n\n## Dos\n\nTexto **b** _i_ `c` con 100% & $x^2$ #tag\n"
        "Pegado:\n| A | B |\n| --- | ---: |\n| 1 | 2 |\n\n"
        "```python\nprint(1)\n```\n\n> cita\n\n![f](img.png)\n",
        base_dir=Path(r"C:\base"),
        math=True,
    )
    assert "\\section{Uno}" in body and "\\subsection{Dos}" in body
    assert "\\textbf{b}" in body and "\\textit{i}" in body
    assert "\\&" in body and "\\%" in body and "\\#tag" in body
    assert "$x^2$" in body  # con math=True la fórmula pasa intacta
    assert "\\begin{longtable}" in body and "\\toprule" in body  # tabla sin línea previa
    assert "language=Python" in body
    assert "displayquote" in body
    assert "C:/base/img.png" in body


def test_md2tex_escapes_backslash():
    body = markdown_to_latex_body("texto con \\ y ~ y ^ sueltos\n")
    assert "\\textbackslash{}" in body
    assert "\\textasciitilde{}" in body


def test_book_headings_mode():
    body = markdown_to_latex_body("# Cap\n", book_headings=True)
    assert "\\chapter{Cap}" in body


def _assert_percent_escaped(body: str) -> None:
    for line in body.splitlines():
        idx = 0
        while True:
            idx = line.find("%", idx)
            if idx == -1:
                break
            assert idx > 0 and line[idx - 1] == "\\", f"% sin escapar: {line!r}"
            idx += 1


def test_currency_and_percent_do_not_break_latex():
    """Regresión del bug real: docs financieros con $ y % rompían \\textit."""
    md = (
        "*Escenario Base: Ingreso anual proyectado = $ 3,760 con +15% y CV $237.*\n\n"
        "* 50% Landing Pages (Precio $350, CV $237) -> MCu = $113\n"
        "* 30% Web Corporativa (Precio $800, CV $487) -> MCu = $313\n\n"
        "Con `codigo` dentro de *cursiva con `x = 1` incluida*.\n"
    )
    body = markdown_to_latex_body(md)
    assert body.count("{") == body.count("}"), "llaves desbalanceadas"
    _assert_percent_escaped(body)
    assert "\\$" in body            # la moneda queda escapada
    assert "\\verb" not in body     # inline code ya no usa \verb
    assert "\\texttt{" in body


def test_math_is_opt_in():
    with_math = markdown_to_latex_body("La fórmula $x^2 + 1$ queda.\n", math=True)
    assert "$x^2 + 1$" in with_math
    without = markdown_to_latex_body("La fórmula $x^2 + 1$ queda.\n")
    assert "$x^2 + 1$" not in without and "\\$" in without


def test_currency_document_compiles():
    if not _latex_available():
        print("SKIP: sin motor LaTeX")
        return
    with tempfile.TemporaryDirectory() as tmp:
        md = Path(tmp) / "moneda.md"
        md.write_text(
            "# Finanzas\n\n*Base: $ 3,760 con +15% y CV $237.*\n\n"
            "* 50% Landing ($350, CV $237) -> $113\n",
            encoding="utf-8",
        )
        pdf = convert_markdown_via_latex([md], Path(tmp) / "m.pdf", template="apuntes-libro")
        assert pdf.exists() and pdf.stat().st_size > 1000


def test_templates_catalog_and_instantiation():
    templates = available_latex_templates()
    assert len(templates) == 10, templates
    wrappers = available_latex_templates(kind="wrapper")
    starters = available_latex_templates(kind="starter")
    assert set(wrappers) == {"apuntes-libro", "articulo-cientifico", "informe-clasico", "informe-moderno"}
    assert len(starters) == 6
    for tid in templates:
        meta = get_latex_template_meta(tid)
        assert meta["name"] and meta["description"] and meta["kind"] in ("wrapper", "starter")


def test_wrapper_placeholders_resolve():
    for tid in available_latex_templates(kind="wrapper"):
        tex = render_latex_template(tid, {
            "title": "T", "author": "A", "date": "D", "body": "B",
            "toc": "", "preamble_extra": "", "accent": "112233",
        })
        assert "((" not in tex, f"placeholder sin resolver en {tid}"
        assert "\\begin{document}" in tex and "B" in tex


def test_starter_instantiation_copies_file():
    with tempfile.TemporaryDirectory() as tmp:
        created = instantiate_starter("factura", tmp, "mi_factura.tex")
        assert created.exists() and created.name == "mi_factura.tex"
        assert "FACTURA" in created.read_text(encoding="utf-8")


def test_compile_tex_and_md_via_latex():
    if not _latex_available():
        print("SKIP: sin motor LaTeX")
        return
    with tempfile.TemporaryDirectory() as tmp:
        md = Path(tmp) / "doc.md"
        md.write_text("# Hola\n\nCuerpo con tabla:\n| A |\n| --- |\n| 1 |\n", encoding="utf-8")
        pdf = convert_markdown_via_latex([md], Path(tmp) / "doc.pdf",
                                         template="informe-clasico", author="Test")
        assert pdf.exists() and pdf.stat().st_size > 1000
        tex = Path(tmp) / "directo.tex"
        tex.write_text("\\documentclass{article}\\begin{document}Hola\\end{document}",
                       encoding="utf-8")
        pdf2 = compile_tex(tex)
        assert pdf2.exists() and pdf2.stat().st_size > 500


def test_preview_pdf_to_images():
    if not (_latex_available() or _browser_available()):
        print("SKIP: sin motor LaTeX ni navegador")
        return
    from markitpdf.preview import pdf_page_count, pdf_to_images
    with tempfile.TemporaryDirectory() as tmp:
        pdf = Path(tmp) / "p.pdf"
        if _latex_available():
            tex = Path(tmp) / "p.tex"
            tex.write_text("\\documentclass{article}\\begin{document}X\\end{document}",
                           encoding="utf-8")
            compile_tex(tex, pdf)
        else:
            from markitpdf import convert_markdown_to_pdf
            md = Path(tmp) / "p.md"
            md.write_text("# X\n", encoding="utf-8")
            convert_markdown_to_pdf(md, pdf)
        assert pdf_page_count(pdf) >= 1
        images = pdf_to_images(pdf, scale=1.0, max_pages=2)
        assert images and images[0].width > 100


def test_themebuilder_css_and_metadata():
    model = copy.deepcopy(DEFAULT_MODEL)
    model["h1"]["color"] = "#123456"
    model["table"]["zebra"] = True
    css = build_css(model)
    assert "@page" in css and "#123456" in css and "nth-child(even)" in css
    meta = theme_metadata_dict(model, "X")
    assert meta["colors"]["title"] == "#123456"
    assert meta["fonts"]["body"] == model["base"]["font"]


def test_model_from_builtin_theme():
    model = model_from_theme("empresarial")
    assert model["h1"]["color"].upper() == "#7B2D3B"
    model_missing = model_from_theme("no-existe-xyz")
    assert model_missing == DEFAULT_MODEL


if __name__ == "__main__":
    for fn in (
        test_md2tex_core_elements,
        test_md2tex_escapes_backslash,
        test_book_headings_mode,
        test_currency_and_percent_do_not_break_latex,
        test_math_is_opt_in,
        test_currency_document_compiles,
        test_templates_catalog_and_instantiation,
        test_wrapper_placeholders_resolve,
        test_starter_instantiation_copies_file,
        test_compile_tex_and_md_via_latex,
        test_preview_pdf_to_images,
        test_themebuilder_css_and_metadata,
        test_model_from_builtin_theme,
    ):
        fn()
        print(f"OK: {fn.__name__}")
    print("Todos los self-checks de la vía LaTeX pasaron.")

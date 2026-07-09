"""Conversión Markdown → cuerpo LaTeX usando mistletoe (MIT).

El renderer devuelve SOLO el cuerpo del documento; el preámbulo lo aporta la
plantilla elegida (markitpdf/latex_templates/), que carga estáticamente el
superconjunto de paquetes que este renderer puede emitir.
"""

from __future__ import annotations

from pathlib import Path

import mistletoe
from mistletoe.latex_renderer import LaTeXRenderer

from .converter import _normalize_table_blank_lines

#: Caracteres especiales de LaTeX → macro segura (translate 1 pasada, sin re-escapes).
_CHAR_MAP = {
    "\\": r"\textbackslash{}",
    "$": r"\$",
    "#": r"\#",
    "{": r"\{",
    "}": r"\}",
    "&": r"\&",
    "_": r"\_",
    "%": r"\%",
    "~": r"\textasciitilde{}",
    "^": r"\^{}",
}

#: Lenguajes que el paquete listings conoce (los demás van sin resaltado).
_LST_LANGS = {
    "python": "Python", "py": "Python", "java": "Java", "c": "C",
    "cpp": "C++", "c++": "C++", "bash": "bash", "sh": "bash",
    "sql": "SQL", "html": "HTML", "xml": "XML", "php": "PHP",
    "r": "R", "matlab": "Matlab", "ruby": "Ruby",
}

_ARTICLE_HEADINGS = {1: "section", 2: "subsection", 3: "subsubsection", 4: "paragraph", 5: "subparagraph"}
_BOOK_HEADINGS = {1: "chapter", 2: "section", 3: "subsection", 4: "subsubsection", 5: "paragraph"}


def escape_latex(text: str) -> str:
    """Escapa texto plano (títulos, autores…) para incrustarlo en LaTeX."""
    return "".join(_CHAR_MAP.get(ch, ch) for ch in text)


class SpanishLatexRenderer(LaTeXRenderer):
    """LaTeXRenderer de mistletoe afinado para las plantillas de MarkItDocs."""

    def __init__(self, base_dir: Path | None = None, book_headings: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.base_dir = base_dir
        self.headings = _BOOK_HEADINGS if book_headings else _ARTICLE_HEADINGS

    def render_raw_text(self, token, escape=True):
        if not escape:
            return token.content
        return escape_latex(token.content)

    def render_heading(self, token):
        cmd = self.headings.get(token.level, "paragraph")
        return "\n\\{cmd}{{{inner}}}\n".format(cmd=cmd, inner=self.render_inner(token))

    def render_image(self, token):
        src = token.src
        if src.startswith(("http://", "https://")):
            # LaTeX no descarga imágenes remotas; dejamos el enlace visible.
            return "\\url{{{}}}".format(self.escape_url(src))
        path = Path(src)
        if not path.is_absolute() and self.base_dir is not None:
            path = (self.base_dir / path).resolve()
        # ponytail: width fijo 0.9\linewidth; escala hacia arriba imágenes pequeñas
        return (
            "\n\\begin{{center}}\\includegraphics[width=0.9\\linewidth]{{{}}}\\end{{center}}\n"
        ).format(path.as_posix())

    def render_block_code(self, token):
        lang = _LST_LANGS.get((token.language or "").lower())
        opts = f"[language={lang}]" if lang else ""
        inner = self.render_raw_text(token.children[0], False)
        return f"\n\\begin{{lstlisting}}{opts}\n{inner}\\end{{lstlisting}}\n"

    def render_table(self, token):
        def col_spec(align):
            return {None: "l", 0: "c", 1: "r"}.get(align, "l")

        if hasattr(token, "header"):
            n_cols = len(token.header.children)
        else:
            n_cols = max((len(r.children) for r in token.children), default=1)
        aligns = token.column_align if token.column_align != [None] else [None] * n_cols
        spec = "".join(col_spec(a) for a in aligns) or "l"

        head = ""
        if hasattr(token, "header"):
            head = self.render_table_row(token.header) + "\\midrule\n"
        body = self.render_inner(token)
        return (
            "\n\\begin{{longtable}}{{{spec}}}\n\\toprule\n{head}{body}\\bottomrule\n"
            "\\end{{longtable}}\n"
        ).format(spec=spec, head=head, body=body)

    def render_thematic_break(self, token):
        return "\n\\par\\noindent\\rule{\\linewidth}{0.4pt}\\par\n"

    def render_document(self, token):
        # Solo el cuerpo: el preámbulo y \begin{document} los pone la plantilla.
        self.footnotes.update(token.footnotes)
        return self.render_inner(token)


def markdown_to_latex_body(
    md_text: str,
    base_dir: Path | None = None,
    book_headings: bool = False,
) -> str:
    """Convierte texto Markdown al cuerpo LaTeX equivalente."""
    normalized = _normalize_table_blank_lines(md_text)
    with SpanishLatexRenderer(base_dir=base_dir, book_headings=book_headings) as renderer:
        return renderer.render(mistletoe.Document(normalized))

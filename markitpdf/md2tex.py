"""Conversión Markdown → cuerpo LaTeX usando mistletoe (MIT).

El renderer devuelve SOLO el cuerpo del documento; el preámbulo lo aporta la
plantilla elegida (markitpdf/latex_templates/), que carga estáticamente el
superconjunto de paquetes que este renderer puede emitir.
"""

from __future__ import annotations

from pathlib import Path

import mistletoe
from mistletoe.base_renderer import BaseRenderer
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
    """LaTeXRenderer de mistletoe afinado para las plantillas de MarkItDocs.

    ``math=False`` (por defecto) NO registra el token matemático ``$...$`` de
    mistletoe: en documentos de negocio los ``$`` son moneda y el passthrough
    crudo de "matemáticas" accidentales (p. ej. ``$350, CV $237`` con un ``%``
    cerca) rompe la compilación. Con ``math=True`` (plantillas científicas)
    las fórmulas pasan, saneadas.
    """

    def __init__(
        self,
        base_dir: Path | None = None,
        book_headings: bool = False,
        math: bool = False,
        **kwargs,
    ):
        if math:
            super().__init__(**kwargs)
        else:
            # Inicializar SIN los tokens extra de latex_token (Math):
            # los $ quedan como texto normal y se escapan a \$.
            self.packages = {}
            self.verb_delimiters = ""  # no usamos \verb (ver render_inline_code)
            BaseRenderer.__init__(self)
        self.base_dir = base_dir
        self.headings = _BOOK_HEADINGS if book_headings else _ARTICLE_HEADINGS

    def render_raw_text(self, token, escape=True):
        if not escape:
            return token.content
        return escape_latex(token.content)

    def render_math(self, token):
        # Solo llega con math=True. Sanear: % y # jamás son matemáticas
        # válidas (un % crudo comenta el resto de la línea y descuadra las
        # llaves de \textit/\textbf); llaves desbalanceadas → texto escapado.
        content = token.content
        if content.count("{") != content.count("}"):
            return escape_latex(content)
        return content.replace("%", r"\%").replace("#", r"\#")

    def render_inline_code(self, token):
        # \verb es ilegal dentro de argumentos (\textit{... \verb!..! ...});
        # \texttt con escape completo funciona en cualquier posición.
        return "\\texttt{" + escape_latex(token.children[0].content) + "}"

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
    math: bool = False,
) -> str:
    """Convierte texto Markdown al cuerpo LaTeX equivalente."""
    normalized = _normalize_table_blank_lines(md_text)
    with SpanishLatexRenderer(
        base_dir=base_dir, book_headings=book_headings, math=math
    ) as renderer:
        return renderer.render(mistletoe.Document(normalized))

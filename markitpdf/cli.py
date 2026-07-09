"""CLI: python -m markitpdf.cli entrada.md|.html|.tex [-o salida.pdf] [--theme|--latex-template]"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .browser import BrowserNotFoundError
from .converter import available_themes, convert_many_to_pdf, convert_markdown_to_pdf
from .latex import LatexCompileError, LatexNotFoundError, compile_tex
from .textemplates import (
    available_latex_templates,
    convert_markdown_via_latex,
    get_latex_template_meta,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="markitpdf",
        description=(
            "Convierte Markdown/HTML a PDF con temas, compila LaTeX (.tex) y "
            "genera PDFs desde plantillas LaTeX de la comunidad."
        ),
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        help="Archivo(s) .md/.html (se unen en un PDF) o .tex (se compila cada uno)",
    )
    parser.add_argument(
        "-o", "--output",
        help="Ruta de salida .pdf (opcional; por defecto, junto al primer archivo)",
    )
    parser.add_argument(
        "--theme",
        default="professional",
        help="Tema HTML a usar (default: professional). Ver --list-themes",
    )
    parser.add_argument(
        "--latex-template",
        metavar="PLANTILLA",
        help="Convierte los .md vía LaTeX con esta plantilla wrapper. Ver --list-latex-templates",
    )
    parser.add_argument("--author", default="", help="Autor para la portada (vía LaTeX)")
    parser.add_argument(
        "--toc", action=argparse.BooleanOptionalAction, default=None,
        help="Forzar índice on/off en la vía LaTeX (default: según plantilla)",
    )
    parser.add_argument("--list-themes", action="store_true", help="Lista los temas HTML y sale")
    parser.add_argument(
        "--list-latex-templates", action="store_true",
        help="Lista las plantillas LaTeX (wrapper y starter) y sale",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_themes:
        for name in available_themes():
            print(name)
        return 0
    if args.list_latex_templates:
        for tid in available_latex_templates():
            meta = get_latex_template_meta(tid)
            print(f"{tid}  [{meta.get('kind')}]  {meta.get('name')} — {meta.get('description')}")
        return 0
    if not args.inputs:
        parser.error("se requiere al menos un archivo de entrada")

    paths = [Path(p) for p in args.inputs]
    tex_inputs = [p for p in paths if p.suffix.lower() == ".tex"]

    try:
        if tex_inputs:
            if len(tex_inputs) != len(paths):
                print("Error: no mezcles .tex con .md/.html en la misma llamada.", file=sys.stderr)
                return 1
            if args.output and len(tex_inputs) > 1:
                print("Error: -o solo se admite con un único .tex.", file=sys.stderr)
                return 1
            for tex in tex_inputs:
                out = compile_tex(tex, Path(args.output) if args.output else None)
                print(f"PDF creado: {out}")
            return 0

        if args.latex_template:
            output = convert_markdown_via_latex(
                paths,
                Path(args.output) if args.output else None,
                template=args.latex_template,
                author=args.author,
                toc=args.toc,
            )
        elif len(paths) == 1:
            output = convert_markdown_to_pdf(
                paths[0], Path(args.output) if args.output else None, theme=args.theme
            )
        else:
            output = convert_many_to_pdf(
                paths, Path(args.output) if args.output else None, theme=args.theme
            )
    except (
        FileNotFoundError, BrowserNotFoundError, LatexNotFoundError,
        LatexCompileError, TimeoutError, RuntimeError, ValueError,
    ) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"PDF creado: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

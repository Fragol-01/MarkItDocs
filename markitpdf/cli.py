"""CLI: python -m markitpdf.cli archivo.md|archivo.html [-o salida.pdf] [--theme <tema>] [archivos...]"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .browser import BrowserNotFoundError
from .converter import available_themes, convert_many_to_pdf, convert_markdown_to_pdf


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="markitpdf",
        description="Convierte archivos Markdown o HTML a PDF con tipografía profesional.",
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="Ruta(s) de archivo(s) .md/.markdown/.html/.htm de entrada (se unen en orden en un solo PDF)",
    )
    parser.add_argument(
        "-o", "--output",
        help="Ruta de salida .pdf (opcional; por defecto, junto al primer archivo)",
    )
    parser.add_argument(
        "--theme",
        default="professional",
        choices=available_themes(),
        help="Tema tipográfico a usar (default: professional)",
    )
    parser.add_argument(
        "--list-themes",
        action="store_true",
        help="Lista los temas disponibles y sale",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_themes:
        for name in available_themes():
            print(name)
        return 0

    try:
        if len(args.inputs) == 1:
            output = convert_markdown_to_pdf(
                Path(args.inputs[0]),
                Path(args.output) if args.output else None,
                theme=args.theme,
            )
        else:
            output = convert_many_to_pdf(
                [Path(p) for p in args.inputs],
                Path(args.output) if args.output else None,
                theme=args.theme,
            )
    except (FileNotFoundError, BrowserNotFoundError, TimeoutError, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"PDF creado: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

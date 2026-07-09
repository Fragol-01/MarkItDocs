"""Plantillas LaTeX de MarkItDocs: descubrimiento, instanciación y vía md→LaTeX→PDF.

Dos tipos (campo ``kind`` del meta.json):
- ``wrapper``: envuelve contenido Markdown convertido (placeholders ``((body))`` etc.).
- ``starter``: documento .tex completo y editable que se copia a la carpeta del usuario.
"""

from __future__ import annotations

import json
import re
import shutil
import tempfile
from pathlib import Path

from .converter import _H1_MD_RE
from .latex import LatexEngine, compile_tex
from .md2tex import escape_latex, markdown_to_latex_body

TEMPLATES_DIR = Path(__file__).parent / "latex_templates"

_PLACEHOLDER_RE = re.compile(r"\(\((\w+)\)\)")


def available_latex_templates(kind: str | None = None) -> list[str]:
    """IDs de plantillas disponibles (carpetas con template.tex + meta.json)."""
    result = []
    if not TEMPLATES_DIR.exists():
        return result
    for folder in sorted(TEMPLATES_DIR.iterdir()):
        if (folder / "template.tex").exists() and (folder / "meta.json").exists():
            if kind is None or get_latex_template_meta(folder.name).get("kind") == kind:
                result.append(folder.name)
    return result


def get_latex_template_meta(template_id: str) -> dict:
    meta_path = TEMPLATES_DIR / template_id / "meta.json"
    if not meta_path.exists():
        raise ValueError(
            f"Plantilla '{template_id}' no existe. Disponibles: {', '.join(available_latex_templates())}"
        )
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["id"] = template_id
    return meta


def render_latex_template(template_id: str, mapping: dict[str, str]) -> str:
    """Sustituye los placeholders ``((clave))`` de template.tex; los ausentes → ''."""
    template_text = (TEMPLATES_DIR / template_id / "template.tex").read_text(encoding="utf-8")
    return _PLACEHOLDER_RE.sub(lambda m: mapping.get(m.group(1), ""), template_text)


def instantiate_starter(template_id: str, dest_dir: Path | str, filename: str | None = None) -> Path:
    """Copia un starter (y sus assets) a dest_dir y devuelve la ruta del .tex creado."""
    meta = get_latex_template_meta(template_id)
    if meta.get("kind") != "starter":
        raise ValueError(f"'{template_id}' no es una plantilla starter.")
    src_dir = TEMPLATES_DIR / template_id
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / (filename or f"{template_id}.tex")
    if target.exists():
        raise FileExistsError(f"Ya existe {target}. Elige otro nombre o carpeta.")
    shutil.copyfile(src_dir / "template.tex", target)
    for asset in src_dir.iterdir():
        if asset.name not in ("template.tex", "meta.json"):
            dest_asset = dest_dir / asset.name
            if not dest_asset.exists():
                shutil.copyfile(asset, dest_asset)
    return target


def _first_h1(md_text: str) -> str | None:
    match = _H1_MD_RE.search(md_text)
    return match.group(1).strip() if match else None


def convert_markdown_via_latex(
    source_paths: list[Path | str],
    output_pdf: Path | str | None = None,
    template: str = "informe-moderno",
    title: str | None = None,
    author: str = "",
    date: str | None = None,
    toc: bool | None = None,
    preamble_extra: str = "",
    accent: str | None = None,
    engine: LatexEngine | None = None,
) -> Path:
    """Convierte uno o varios .md a un único PDF vía plantilla LaTeX.

    Cada archivo empieza en página nueva (``\\clearpage``).
    """
    meta = get_latex_template_meta(template)
    if meta.get("kind") != "wrapper":
        raise ValueError(f"'{template}' es una plantilla starter; úsala con 'Nuevo desde plantilla'.")

    resolved: list[Path] = []
    for raw in source_paths:
        path = Path(raw).resolve()
        if not path.exists():
            raise FileNotFoundError(f"No existe el archivo de entrada: {path}")
        if path.suffix.lower() not in {".md", ".markdown"}:
            raise ValueError(
                f"'{path.name}': la vía LaTeX solo acepta Markdown (los .html usan los temas HTML)."
            )
        resolved.append(path)
    if not resolved:
        raise ValueError("Se requiere al menos un archivo .md")

    book = bool(meta.get("book_headings"))
    bodies = [
        markdown_to_latex_body(p.read_text(encoding="utf-8"), base_dir=p.parent, book_headings=book)
        for p in resolved
    ]
    body = "\n\\clearpage\n".join(bodies)

    first_text = resolved[0].read_text(encoding="utf-8")
    doc_title = title or _first_h1(first_text) or resolved[0].stem
    use_toc = meta.get("toc_default", False) if toc is None else toc

    mapping = {
        "title": escape_latex(doc_title),
        "author": escape_latex(author),
        "date": date if date is not None else "\\today",
        "body": body,
        "toc": "\\tableofcontents\n\\clearpage" if use_toc else "",
        "preamble_extra": preamble_extra,
        "accent": (accent or meta.get("accent", "1F4E79")).lstrip("#").upper(),
    }
    tex_source = render_latex_template(template, mapping)

    if output_pdf is None:
        output_pdf = resolved[0].with_suffix(".pdf")
    output_pdf = Path(output_pdf).resolve()

    with tempfile.TemporaryDirectory(prefix="markitdocs_mdtex_", ignore_cleanup_errors=True) as tmp:
        tex_path = Path(tmp) / f"{resolved[0].stem}.tex"
        tex_path.write_text(tex_source, encoding="utf-8")
        return compile_tex(tex_path, output_pdf, engine=engine)

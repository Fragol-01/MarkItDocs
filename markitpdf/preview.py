"""Vista previa: renderiza páginas de un PDF a imágenes PIL con pypdfium2.

Es el puente entre los pipelines reales (HTML→PDF con Chromium, .tex→PDF con
LaTeX) y el panel de vista previa de la GUI: lo que se ve es el PDF final.
"""

from __future__ import annotations

from pathlib import Path

import pypdfium2 as pdfium


def pdf_page_count(pdf_path: Path | str) -> int:
    pdf = pdfium.PdfDocument(str(pdf_path))
    try:
        return len(pdf)
    finally:
        pdf.close()


def pdf_to_images(
    pdf_path: Path | str,
    scale: float = 1.4,
    first_page: int = 0,
    max_pages: int | None = None,
) -> list:
    """Renderiza páginas del PDF a imágenes PIL (72*scale ppp).

    ``first_page`` es 0-based; ``max_pages`` limita cuántas se renderizan
    (None = todas). Devuelve lista de PIL.Image.
    """
    pdf = pdfium.PdfDocument(str(pdf_path))
    try:
        total = len(pdf)
        end = total if max_pages is None else min(total, first_page + max_pages)
        images = []
        for index in range(first_page, end):
            page = pdf[index]
            bitmap = page.render(scale=scale)
            images.append(bitmap.to_pil())
            bitmap.close()
            page.close()
        return images
    finally:
        pdf.close()

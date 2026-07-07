"""MarkItPDF — convierte Markdown/HTML a PDF estéticamente cuidado.

Inspirado en microsoft/markitdown (PDF → Markdown), en sentido inverso.
Vive como subpaquete de este proyecto (monorepo).
"""

from .browser import BrowserNotFoundError, find_browser
from .converter import (
    ConversionResult,
    MarkdownToPdfConverter,
    ThemeMetadata,
    available_themes,
    convert_many_to_pdf,
    convert_markdown_to_pdf,
    get_theme_metadata,
)

__version__ = "0.4.0"
__all__ = [
    "BrowserNotFoundError",
    "ConversionResult",
    "MarkdownToPdfConverter",
    "ThemeMetadata",
    "available_themes",
    "convert_many_to_pdf",
    "convert_markdown_to_pdf",
    "find_browser",
    "get_theme_metadata",
    "__version__",
]

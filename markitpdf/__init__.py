"""MarkItPDF — convierte Markdown/HTML a PDF estéticamente cuidado.

Inspirado en microsoft/markitdown (PDF → Markdown), en sentido inverso.
Vive como subpaquete de este proyecto (monorepo).
"""

from .browser import BrowserNotFoundError, find_browser
from .latex import (
    LatexCompileError,
    LatexEngine,
    LatexNotFoundError,
    compile_tex,
    download_tectonic,
    find_latex_engine,
)
from .md2tex import escape_latex, markdown_to_latex_body
from .textemplates import (
    available_latex_templates,
    convert_markdown_via_latex,
    get_latex_template_meta,
    instantiate_starter,
)
from .converter import (
    ConversionResult,
    MarkdownToPdfConverter,
    ThemeMetadata,
    available_themes,
    convert_many_to_pdf,
    convert_markdown_to_pdf,
    get_theme_metadata,
)

__version__ = "0.5.0"
__all__ = [
    "BrowserNotFoundError",
    "ConversionResult",
    "LatexCompileError",
    "LatexEngine",
    "LatexNotFoundError",
    "MarkdownToPdfConverter",
    "ThemeMetadata",
    "available_latex_templates",
    "available_themes",
    "compile_tex",
    "convert_many_to_pdf",
    "convert_markdown_to_pdf",
    "convert_markdown_via_latex",
    "download_tectonic",
    "escape_latex",
    "find_browser",
    "find_latex_engine",
    "get_latex_template_meta",
    "get_theme_metadata",
    "instantiate_starter",
    "markdown_to_latex_body",
    "__version__",
]

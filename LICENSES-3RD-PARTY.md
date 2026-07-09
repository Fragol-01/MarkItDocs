# Licencias de terceros

MarkItDocs es MIT. Estos componentes de terceros se usan o referencian:

| Componente | Uso | Licencia |
|---|---|---|
| [mistletoe](https://github.com/miyuchina/mistletoe) | Parser Markdown → LaTeX (`markitpdf/md2tex.py` subclasea su `LaTeXRenderer`) | MIT |
| [pypdfium2](https://github.com/pypdfium2-team/pypdfium2) | Render de PDF a imagen para la vista previa | Apache-2.0 / BSD-3-Clause (+ PDFium BSD) |
| [Tectonic](https://github.com/tectonic-typesetting/tectonic) | Motor LaTeX opcional que la app puede descargar (no se distribuye con MarkItDocs) | MIT |
| [Eisvogel](https://github.com/Wandmalfarbe/pandoc-latex-template) | Inspiración estética de la plantilla `informe-moderno` (sin código copiado) | BSD-3-Clause |
| [python-markdown](https://github.com/Python-Markdown/markdown), [python-docx](https://github.com/python-openxml/python-docx), [Pygments](https://pygments.org/), [PyYAML](https://pyyaml.org/), [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter), [tkinterdnd2](https://github.com/pmgagne/tkinterdnd2) | Dependencias del núcleo (ver `requirements.txt`) | BSD/MIT/CC0 según proyecto |

Las plantillas LaTeX en `markitpdf/latex_templates/` fueron escritas para MarkItDocs
y se publican bajo MIT, salvo la atribución indicada en cada `meta.json`.
El renderizado HTML→PDF usa el navegador Chromium (Edge/Chrome) ya instalado en el
sistema; no se distribuye ningún navegador.

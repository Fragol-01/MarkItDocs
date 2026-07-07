# MarkItDocs

**Convierte Markdown y HTML a documentos Word (.docx) y PDF con formato profesional** — desde una app de escritorio con drag-and-drop o desde la línea de comandos.

> **English TL;DR** — MarkItDocs converts Markdown/HTML files into polished .docx and .pdf documents. Desktop GUI (drag & drop) + CLI. Merge many files into one document or convert them separately. Themeable via CSS (PDF) and JSON/YAML/TOML (DOCX). PDF rendering uses your installed Edge/Chrome in headless mode — no heavyweight dependencies. Inspired by [microsoft/markitdown](https://github.com/microsoft/markitdown), in the opposite direction.

---

## Características

- **Entradas**: `.md`, `.markdown`, `.html`, `.htm`
- **Salidas**: `.docx` (Word) y `.pdf`
- **Dos modos de conversión**:
  - *Separado*: N archivos de entrada → N documentos de salida
  - *Unido*: N archivos de entrada → **1 solo documento**, en orden, con salto de página entre cada archivo
- **Temas**:
  - PDF: temas CSS de imprenta (`professional`, `minimal`) con metadata en JSON/YAML
  - DOCX: temas configurables por archivo `.json` / `.yaml` / `.toml` (fuentes, colores, rellenos)
- **GUI de escritorio** (CustomTkinter): drag-and-drop real, selector de tema, modo unir, log en vivo
- **CLI** con patrones glob, modo batch y modo `--watch` (reconversión automática al guardar)
- Tablas, imágenes (locales, remotas con reintentos, base64), hipervínculos internos/externos, tabla de contenido (`[TOC]`), saltos de página (`\pagebreak` o `<!-- pagebreak -->`), código con resaltado

## Instalación

```bash
git clone https://github.com/<usuario>/MarkItDocs.git
cd MarkItDocs
pip install -r requirements.txt
```

Requisitos: Python 3.11+ · Para exportar PDF: Microsoft Edge o Google Chrome instalado (en Windows, Edge ya viene preinstalado).

### Ejecutables

Cada release publica binarios nativos para Windows, macOS y Linux (compilados con PyInstaller en GitHub Actions). Descarga el de tu sistema desde la pestaña **Releases** — no requiere Python.

## Uso

### App de escritorio

```bash
python app.py
```

1. Arrastra archivos `.md`/`.html` (o usa *Seleccionar*)
2. Elige tema PDF y/o tema DOCX (opcional)
3. Marca **"Unir en un solo documento"** si quieres un único archivo de salida — los archivos se procesan en orden alfabético, así que nómbralos `01_intro.md`, `02_capitulo.md`, …
4. Pulsa **Convertir a Word** o **Convertir a PDF**

### CLI — Markdown/HTML → DOCX

```bash
# Un archivo
python crear_documento.py documento.md

# Varios archivos → varios .docx (acepta glob)
python crear_documento.py capitulos/*.md -o salida/

# Varios archivos → UN SOLO .docx (en orden)
python crear_documento.py 01_intro.md 02_desarrollo.html 03_fin.md --merge -o libro.docx

# Con tema personalizado
python crear_documento.py doc.md --theme mi_tema.yaml

# Modo watch: reconvierte cada vez que guardas
python crear_documento.py doc.md --watch
```

### CLI — Markdown/HTML → PDF

```bash
# Un archivo
python -m markitpdf.cli documento.md

# Con tema
python -m markitpdf.cli documento.md --theme minimal

# Varios archivos → UN SOLO PDF (en orden)
python -m markitpdf.cli 01_intro.md 02_desarrollo.html 03_fin.md -o libro.pdf
```

### Docker (CLI/headless, sin GUI)

```bash
docker build -t markitdocs .
docker run --rm -v "$PWD:/data" markitdocs python crear_documento.py /data/doc.md -o /data/doc.docx
docker run --rm -v "$PWD:/data" markitdocs python -m markitpdf.cli /data/doc.md -o /data/doc.pdf
```

## Temas

### Temas PDF (`markitpdf/themes/`)

Cada tema es un `.css` de imprenta (con `@page`, numeración, viudas/huérfanas) más un `.json`/`.yaml` con su metadata (nombre, fuentes, colores). Incluidos: **professional** (corporativo azul) y **minimal** (editorial limpio). Para crear el tuyo: copia `professional.css` + `professional.json` con otro nombre, edítalos, y aparecerá automáticamente en la GUI y el CLI.

### Temas DOCX

Un archivo `.json`, `.yaml`/`.yml` o `.toml` que sobrescribe el tema por defecto:

```yaml
# mi_tema.yaml
body_font: Georgia
code_font: Cascadia Code
title_color: [155, 30, 30]     # RGB
link_color: [0, 102, 204]
quote_fill: "F8F9FA"           # hex sin '#'
table_head_fill: "EADDD7"
code_fill: "F6F8FA"
hr_color: [180, 190, 205]
```

## Arquitectura

```
app.py                  # GUI (CustomTkinter + tkinterdnd2)
crear_documento.py      # Motor MD/HTML → DOCX (python-docx) + CLI
markitpdf/              # Subpaquete MD/HTML → PDF
├── converter.py        #   render vía Chromium headless (Edge/Chrome)
├── browser.py          #   detección del navegador por SO
├── cli.py              #   CLI del subpaquete
└── themes/             #   temas CSS + metadata JSON/YAML
tests/                  # self-checks ejecutables (sin framework)
```

El PDF se genera renderizando HTML+CSS con el Chromium que ya tienes instalado (`--headless --print-to-pdf`): tipografía real de navegador sin dependencias pesadas (sin wkhtmltopdf, sin LaTeX).

## Compilar tu propio ejecutable

```bash
pip install pyinstaller pillow
pyinstaller MarkItDocs.spec
# → dist/MarkItDocs(.exe)
```

## Tests

```bash
python tests/test_crear_documento.py
python tests/test_markitpdf.py
# o con pytest, si lo prefieres:
pytest tests/
```

Los tests de PDF se omiten automáticamente si no hay Edge/Chrome disponible.

## Contribuir

Lee [CONTRIBUTING.md](CONTRIBUTING.md). Issues y PRs bienvenidos.

## Licencia

[MIT](LICENSE)

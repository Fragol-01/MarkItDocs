# MarkItDocs

**Convierte Markdown, HTML y LaTeX a documentos Word (.docx) y PDF con formato profesional** — desde una app de escritorio con drag-and-drop, vista previa en vivo y diseñador visual de temas, o desde la línea de comandos.

> **English TL;DR** — MarkItDocs converts Markdown/HTML/LaTeX files into polished .docx and .pdf documents. Desktop GUI (drag & drop, live preview, visual theme designer) + CLI. Compile `.tex` directly, or route your Markdown through community LaTeX templates (report, scientific article, book). 10 LaTeX templates included: invoice, quote, contract, CV, formal letter, work plan… PDF rendering uses your installed Edge/Chrome (HTML themes) or your LaTeX engine (MiKTeX/TeX Live/Tectonic — downloadable in one click). Inspired by [microsoft/markitdown](https://github.com/microsoft/markitdown), in the opposite direction.

---

## Características

- **Entradas**: `.md`, `.markdown`, `.html`, `.htm` y **`.tex` (LaTeX)**
- **Salidas**: `.docx` (Word) y `.pdf`
- **Dos motores de PDF**:
  - *Temas HTML*: render con tu Edge/Chrome headless — 6 temas CSS integrados
  - *Plantillas LaTeX*: tu Markdown se convierte a LaTeX y se compila con una plantilla de la comunidad (informe estilo Eisvogel, artículo científico, libro con capítulos…)
- **Vista previa en vivo** (panel lateral): ves el PDF real página a página, con zoom, y se actualiza sola al cambiar archivo, tema o plantilla — ideal para comparar plantillas antes de exportar
- **Diseñador visual de temas**: edita colores, fuentes, tamaños, márgenes y tablas por elemento con vista previa instantánea; guarda tu tema y viste **Word y PDF** a la vez. Pestaña de preámbulo LaTeX para personalización infinita
- **10 plantillas LaTeX incluidas**: 4 para envolver tus .md + 6 documentos editables (factura, presupuesto, contrato, CV, carta formal, plan de trabajo)
- **Dos modos de conversión**:
  - *Separado*: N archivos de entrada → N documentos de salida
  - *Unido*: N archivos de entrada → **1 solo documento**, en orden, con salto de página entre cada archivo
- **6 temas integrados que visten Word Y PDF a la vez**: `professional`, `minimal`, `empresarial`, `academico`, `economico`, `explicativo` — un solo selector, tú decides el formato de salida
- **GUI de escritorio** (CustomTkinter): drag-and-drop real, lista reordenable (↑/↓ — el orden visible es el orden de unión), galería «Nuevo desde plantilla…», log con colores
- **CLI** con patrones glob, modo batch, modo `--watch`, `--latex-template` y compilación directa de `.tex`
- Tablas, imágenes, hipervínculos, `[TOC]`, saltos de página, código con resaltado, fórmulas `$...$` (vía LaTeX)

## Instalación

```bash
git clone https://github.com/<usuario>/MarkItDocs.git
cd MarkItDocs
pip install -r requirements.txt
```

Requisitos: Python 3.11+ · Para PDF con temas HTML: Microsoft Edge o Google Chrome (en Windows, Edge ya viene preinstalado) · Para la vía LaTeX: MiKTeX/TeX Live si ya lo tienes, o el botón **«Descargar Tectonic (~30 MB)»** de la app lo instala sin permisos de administrador.

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

### CLI — LaTeX

```bash
# Compilar un .tex directamente (detecta MiKTeX/TeX Live/Tectonic)
python -m markitpdf.cli documento.tex

# Markdown → PDF a través de una plantilla LaTeX de la comunidad
python -m markitpdf.cli informe.md --latex-template informe-moderno --author "Tu Nombre"

# Ver el catálogo de plantillas
python -m markitpdf.cli --list-latex-templates
```

### Docker (CLI/headless, sin GUI)

```bash
docker build -t markitdocs .
docker run --rm -v "$PWD:/data" markitdocs python crear_documento.py /data/doc.md -o /data/doc.docx
docker run --rm -v "$PWD:/data" markitdocs python -m markitpdf.cli /data/doc.md -o /data/doc.pdf
```

## Temas

Un tema se elige por **nombre** y aplica a los dos formatos: el `.css` viste el PDF y la metadata `.json`/`.yaml` (fuentes, colores) viste el Word.

| Tema | Estilo | Ideal para |
|---|---|---|
| `professional` | Corporativo azul, Segoe UI | Documentos técnicos y de negocio |
| `minimal` | Editorial limpio, Inter, mucho blanco | Contenido editorial moderno |
| `empresarial` | Ejecutivo serif, carbón + burdeos + dorado | Propuestas comerciales, dirección |
| `academico` | Paper: Times, justificado, tablas booktabs | Artículos, tesis, informes académicos |
| `economico` | Denso, tablas esmeralda protagonistas | Informes financieros y de costos |
| `explicativo` | Didáctico: letra grande, notas ámbar | Manuales, tutoriales, formación |

### Crear un tema nuevo

**Con el Diseñador visual (recomendado)**: botón «🎨 Diseñador…» en la GUI — eliges un elemento (títulos, tablas, citas, código, página…), ajustas sus propiedades con vista previa en vivo y guardas. El tema queda en `%APPDATA%\MarkItDocs\themes\` y aplica a Word y PDF.

**A mano** (`markitpdf/themes/`): copia `professional.css` + `professional.json` con otro nombre, edítalos, y el tema aparecerá automáticamente en la GUI y en ambos CLI.

## Plantillas LaTeX (`markitpdf/latex_templates/`)

| Plantilla | Tipo | Para qué |
|---|---|---|
| `informe-moderno` | Envuelve tus .md | Informe profesional con portada a color (estética inspirada en Eisvogel) |
| `articulo-cientifico` | Envuelve tus .md | Paper académico: serif, secciones numeradas, fórmulas `$...$` |
| `apuntes-libro` | Envuelve tus .md | Cada H1 = un capítulo; portada e índice |
| `informe-clasico` | Envuelve tus .md | LaTeX sobrio en blanco y negro |
| `factura` | Documento editable | Factura con tabla de conceptos y totales |
| `presupuesto-cotizacion` | Documento editable | Cotización de servicios con alcance y firmas |
| `contrato-servicios` | Documento editable | Contrato de desarrollo web (modelo orientativo) |
| `cv-profesional` | Documento editable | CV de una página, autocontenido |
| `carta-formal` | Documento editable | Carta con membrete y firma |
| `plan-de-trabajo` | Documento editable | Fases, hitos, riesgos y equipo |

Los «documentos editables» se instancian desde la GUI («Nuevo desde plantilla…») como `.tex` que rellenas y compilas con el botón PDF. Para crear tu propia plantilla: copia una carpeta, edita `template.tex` (placeholders `((title))`, `((body))`, `((preamble_extra))`…) y `meta.json`.

Licencias de componentes de terceros: [LICENSES-3RD-PARTY.md](LICENSES-3RD-PARTY.md).

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
app.py                  # GUI (CustomTkinter + tkinterdnd2) con vista previa en vivo
designer.py             # Diseñador visual de temas (3 columnas + preview)
crear_documento.py      # Motor MD/HTML → DOCX (python-docx) + CLI
markitpdf/              # Subpaquete de PDF
├── converter.py        #   MD/HTML → PDF vía Chromium headless (Edge/Chrome)
├── browser.py          #   detección del navegador por SO
├── latex.py            #   motor LaTeX: detección, compilación, descarga de Tectonic
├── md2tex.py           #   Markdown → LaTeX (mistletoe)
├── textemplates.py     #   catálogo e instanciación de plantillas LaTeX
├── themebuilder.py     #   modelo del Diseñador → CSS + metadata
├── preview.py          #   PDF → imágenes (pypdfium2) para la vista previa
├── cli.py              #   CLI del subpaquete
├── themes/             #   temas CSS + metadata JSON/YAML
└── latex_templates/    #   plantillas LaTeX (template.tex + meta.json)
tests/                  # self-checks ejecutables (sin framework)
```

El PDF con temas HTML se genera renderizando HTML+CSS con el Chromium que ya tienes instalado (`--headless --print-to-pdf`). La vía LaTeX usa tu MiKTeX/TeX Live, o Tectonic (MIT, un solo ejecutable) que la app puede descargar. La vista previa muestra el PDF real convertido a imágenes con pypdfium2 — lo que ves es exactamente lo que exportas.

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
python tests/test_latex_features.py
# o con pytest, si lo prefieres:
pytest tests/
```

Los tests de PDF se omiten automáticamente si no hay Edge/Chrome; los de LaTeX, si no hay motor LaTeX.

## Contribuir

Lee [CONTRIBUTING.md](CONTRIBUTING.md). Issues y PRs bienvenidos.

## Licencia

[MIT](LICENSE)

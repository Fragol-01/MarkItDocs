"""Diseñador de temas: modelo paramétrico → CSS (PDF) + metadata (Word).

El Diseñador visual edita un ``model`` (dict JSON-serializable); de él se
generan el .css completo y el .json de ThemeMetadata, guardados en la carpeta
de temas del usuario (USER_THEMES_DIR) donde el resto de la app los descubre.
"""

from __future__ import annotations

import copy
import json
import re
import unicodedata
from pathlib import Path

from .converter import USER_THEMES_DIR, _find_theme_file, _load_theme_metadata

DEFAULT_MODEL: dict = {
    "page": {"size": "A4", "margin_top_cm": 2.4, "margin_right_cm": 2.0,
             "margin_bottom_cm": 2.4, "margin_left_cm": 2.0},
    "base": {"font": "Segoe UI", "heading_font": "Segoe UI Semibold",
             "size_pt": 10.5, "color": "#1F2937", "line_height": 1.55,
             "justify": False},
    "h1": {"size_pt": 22.0, "color": "#1F4E79", "bold": True, "italic": False,
           "align": "left", "rule": True},
    "h2": {"size_pt": 15.0, "color": "#1F4E79", "bold": True, "italic": False,
           "align": "left", "rule": False},
    "h3": {"size_pt": 12.5, "color": "#1F2937", "bold": True, "italic": False,
           "align": "left"},
    "link": {"color": "#0066CC", "underline": False},
    "table": {"head_fill": "#D9EAF7", "head_color": "#1F2937",
              "border_color": "#B4BECE", "zebra": False, "zebra_fill": "#F4F7FA"},
    "quote": {"fill": "#F8F9FA", "bar_color": "#1F4E79",
              "text_color": "#4B5563", "italic": True},
    "code": {"font": "Consolas", "fill": "#F6F8FA", "color": "#111827",
             "size_pt": 9.5},
    "hr": {"color": "#B4BECE"},
}

#: Markdown de muestra que el Diseñador renderiza en su vista previa.
SAMPLE_MARKDOWN = """# Título principal del documento

Este es un párrafo normal con [un enlace](https://ejemplo.com), texto en
**negrita** y en *cursiva*, además de `código en línea` para comparar.

## Sección de nivel dos

Otro párrafo para apreciar el interlineado, el color del texto y la
alineación elegida. La tipografía del cuerpo se aplica aquí.

### Sub-sección de nivel tres

> Una cita destacada: así se verán los bloques citados
> con su color de barra y fondo.

| Concepto | Cantidad | Importe |
| --- | ---: | ---: |
| Diseño web | 1 | 300,00 |
| Desarrollo | 1 | 700,00 |
| Hosting anual | 1 | 120,00 |

```python
def hola(nombre):
    return f"Hola, {nombre}"  # bloque de código
```

- Elemento de lista uno
- Elemento de lista dos

---

Texto final tras un separador horizontal.
"""


def _weight(bold: bool) -> str:
    return "600" if bold else "400"


def _style(italic: bool) -> str:
    return "italic" if italic else "normal"


def build_css(model: dict) -> str:
    """Genera la hoja de estilos completa a partir del modelo del Diseñador."""
    m = model
    page, base = m["page"], m["base"]
    h1, h2, h3 = m["h1"], m["h2"], m["h3"]
    link, table, quote, code, hr = m["link"], m["table"], m["quote"], m["code"], m["hr"]

    heading_font = base.get("heading_font") or base["font"]
    zebra_css = (
        f"tbody tr:nth-child(even) td {{ background: {table['zebra_fill']}; }}\n"
        if table.get("zebra")
        else ""
    )
    h4_pt = max(base["size_pt"], h3["size_pt"] - 1.5)

    return f"""/* Tema generado por el Diseñador visual de MarkItDocs */
@page {{
  size: {page['size']};
  margin: {page['margin_top_cm']}cm {page['margin_right_cm']}cm {page['margin_bottom_cm']}cm {page['margin_left_cm']}cm;
}}
* {{ box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
body {{
  font-family: '{base['font']}', 'Segoe UI', sans-serif;
  font-size: {base['size_pt']}pt;
  color: {base['color']};
  line-height: {base['line_height']};
  text-align: {'justify' if base.get('justify') else 'left'};
  margin: 0;
}}
p {{ margin: 0 0 0.65em 0; }}
h1, h2, h3, h4, h5, h6 {{
  font-family: '{heading_font}', '{base['font']}', sans-serif;
  line-height: 1.25;
  margin: 1.1em 0 0.45em 0;
  page-break-after: avoid;
  text-align: left;
}}
h1 {{
  font-size: {h1['size_pt']}pt; color: {h1['color']};
  font-weight: {_weight(h1['bold'])}; font-style: {_style(h1['italic'])};
  text-align: {h1['align']};
  {f"border-bottom: 2px solid {h1['color']}; padding-bottom: 0.2em;" if h1.get('rule') else ''}
}}
h2 {{
  font-size: {h2['size_pt']}pt; color: {h2['color']};
  font-weight: {_weight(h2['bold'])}; font-style: {_style(h2['italic'])};
  text-align: {h2['align']};
  {f"border-bottom: 1px solid {hr['color']}; padding-bottom: 0.15em;" if h2.get('rule') else ''}
}}
h3 {{
  font-size: {h3['size_pt']}pt; color: {h3['color']};
  font-weight: {_weight(h3['bold'])}; font-style: {_style(h3['italic'])};
  text-align: {h3['align']};
}}
h4, h5, h6 {{ font-size: {h4_pt}pt; color: {h3['color']}; font-weight: 600; }}
a {{ color: {link['color']}; text-decoration: {'underline' if link.get('underline') else 'none'}; }}
table {{
  border-collapse: collapse; width: 100%; margin: 0.8em 0;
  page-break-inside: avoid; font-size: {max(8.0, base['size_pt'] - 0.5)}pt;
}}
th {{
  background: {table['head_fill']}; color: {table['head_color']};
  font-weight: 600; text-align: left;
}}
th, td {{ border: 1px solid {table['border_color']}; padding: 5px 9px; }}
{zebra_css}blockquote {{
  margin: 0.8em 0; padding: 0.5em 1em;
  background: {quote['fill']}; border-left: 4px solid {quote['bar_color']};
  color: {quote['text_color']}; font-style: {_style(quote.get('italic', True))};
}}
code, pre {{ font-family: '{code['font']}', Consolas, monospace; font-size: {code['size_pt']}pt; }}
code {{ background: {code['fill']}; color: {code['color']}; padding: 1px 5px; border-radius: 3px; }}
pre {{
  background: {code['fill']}; color: {code['color']};
  padding: 10px 12px; border-radius: 6px; overflow-x: auto;
  page-break-inside: avoid;
}}
pre code {{ background: none; padding: 0; }}
ul, ol {{ margin: 0.4em 0 0.7em 0; padding-left: 1.6em; }}
li {{ margin-bottom: 0.22em; }}
hr {{ border: 0; border-top: 1px solid {hr['color']}; margin: 1.2em 0; }}
img {{ max-width: 100%; }}
"""


def theme_metadata_dict(model: dict, name: str, description: str = "") -> dict:
    """Modelo → dict con el esquema de ThemeMetadata (para el .json del tema)."""
    base, code = model["base"], model["code"]
    return {
        "name": name,
        "description": description or "Tema personalizado creado con el Diseñador visual.",
        "version": "1.0.0",
        "css": "",  # se rellena al guardar
        "fonts": {
            "body": base["font"],
            "heading": base.get("heading_font") or base["font"],
            "code": code["font"],
        },
        "colors": {
            "title": model["h1"]["color"],
            "text": base["color"],
            "link": model["link"]["color"],
            "rule": model["hr"]["color"],
            "code_fill": code["fill"],
            "quote_fill": model["quote"]["fill"],
            "table_head_fill": model["table"]["head_fill"],
        },
        "sizes": {
            "body_pt": base["size_pt"],
            "h1_pt": model["h1"]["size_pt"],
            "h2_pt": model["h2"]["size_pt"],
            "h3_pt": model["h3"]["size_pt"],
        },
        "page": dict(model["page"]),
    }


def slugify_theme_id(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")
    return slug or "tema-personalizado"


def save_custom_theme(
    name: str,
    model: dict,
    description: str = "",
    latex_preamble: str = "",
) -> str:
    """Guarda el tema del Diseñador en USER_THEMES_DIR y devuelve su id."""
    theme_id = slugify_theme_id(name)
    if _find_theme_file(theme_id, (".css",)) is not None and not (
        USER_THEMES_DIR / f"{theme_id}.css"
    ).exists():
        theme_id += "-custom"  # no pisar un tema integrado

    USER_THEMES_DIR.mkdir(parents=True, exist_ok=True)
    (USER_THEMES_DIR / f"{theme_id}.css").write_text(build_css(model), encoding="utf-8")

    meta = theme_metadata_dict(model, name, description)
    meta["css"] = f"{theme_id}.css"
    meta["designer_model"] = copy.deepcopy(model)  # para reabrir y seguir editando
    if latex_preamble.strip():
        meta["latex_preamble"] = latex_preamble
    (USER_THEMES_DIR / f"{theme_id}.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return theme_id


def model_from_theme(theme_name: str) -> dict:
    """Punto de partida del Diseñador: modelo desde un tema existente.

    Si el tema fue creado por el Diseñador recupera su modelo exacto; si es un
    tema integrado, traduce su metadata (fuentes/colores/tamaños) sobre el
    modelo por defecto.
    """
    model = copy.deepcopy(DEFAULT_MODEL)
    meta_path = _find_theme_file(theme_name, (".json",))
    if meta_path is not None:
        try:
            raw = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            raw = {}
        if isinstance(raw.get("designer_model"), dict):
            merged = copy.deepcopy(DEFAULT_MODEL)
            for section, values in raw["designer_model"].items():
                if section in merged and isinstance(values, dict):
                    merged[section].update(values)
            return merged

    meta = _load_theme_metadata(theme_name)
    fonts, colors, sizes = meta.fonts, meta.colors, meta.sizes
    if fonts.get("body"):
        model["base"]["font"] = fonts["body"]
    if fonts.get("heading"):
        model["base"]["heading_font"] = fonts["heading"]
    if fonts.get("code"):
        model["code"]["font"] = fonts["code"]
    if colors.get("text"):
        model["base"]["color"] = colors["text"]
    if colors.get("title"):
        model["h1"]["color"] = colors["title"]
        model["h2"]["color"] = colors["title"]
        model["quote"]["bar_color"] = colors["title"]
    if colors.get("link"):
        model["link"]["color"] = colors["link"]
    if colors.get("rule"):
        model["hr"]["color"] = colors["rule"]
    if colors.get("code_fill"):
        model["code"]["fill"] = colors["code_fill"]
    if colors.get("quote_fill"):
        model["quote"]["fill"] = colors["quote_fill"]
    if colors.get("table_head_fill"):
        model["table"]["head_fill"] = colors["table_head_fill"]
    for key, target in (("body_pt", ("base", "size_pt")), ("h1_pt", ("h1", "size_pt")),
                        ("h2_pt", ("h2", "size_pt")), ("h3_pt", ("h3", "size_pt"))):
        if sizes.get(key):
            model[target[0]][target[1]] = float(sizes[key])
    if meta.page:
        for key in ("size", "margin_top_cm", "margin_right_cm", "margin_bottom_cm", "margin_left_cm"):
            if meta.page.get(key) is not None:
                model["page"][key] = meta.page[key]
    return model


def get_theme_latex_preamble(theme_name: str) -> str:
    """Preámbulo LaTeX guardado con un tema del Diseñador ('' si no tiene)."""
    meta_path = _find_theme_file(theme_name, (".json",))
    if meta_path is None:
        return ""
    try:
        raw = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return ""
    return raw.get("latex_preamble", "") or ""

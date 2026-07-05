# MD → DOCX GUI

Pequeña app de escritorio Windows para convertir archivos Markdown (.md) a Word (.docx).

Requisitos

- Python 3.10+ (probado en 3.14.6; los temas `.toml` requieren 3.11+, los `.json` funcionan en 3.10)
- Paquetes listados en `requirements.txt`

Instalación

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Uso — GUI

```bash
python app.py
```

Selecciona uno o varios archivos `.md`, elige una carpeta de salida (opcional) y presiona `Convertir`.

Uso — CLI

```bash
# Un archivo
python crear_documento.py documento.md -o salida.docx

# Batch con patrón glob
python crear_documento.py "carpeta/*.md" -o carpeta_salida/

# Con tema personalizado (.json o .toml)
python crear_documento.py documento.md --theme mi_tema.json

# Watch mode: reconvierte automáticamente al detectar cambios
python crear_documento.py documento.md --watch
```

Salto de página manual: escribe `\pagebreak` o `<!-- pagebreak -->` en una línea propia dentro del Markdown.

Tema personalizado (`mi_tema.json`):

```json
{
  "title_color": [200, 30, 30],
  "body_font": "Georgia",
  "code_font": "Consolas"
}
```

Claves disponibles: `body_font`, `code_font`, `title_color`, `link_color`, `quote_fill`, `table_head_fill`, `code_fill`, `hr_color`.

Empaquetado (opcional)

Para crear un ejecutable Windows con PyInstaller:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed app.py
```

Notas

- La app asume que el archivo `crear_documento.py` con la función `convert_markdown_file(source_path, output_path)` esté en la misma carpeta que `app.py`.
- Si `crear_documento.py` está en otro lugar, modifica el `sys.path` en `app.py` o copia `crear_documento.py` junto a `app.py`.
- Ver `AUDITORIA.md` para el historial de mejoras aplicadas y pendientes.

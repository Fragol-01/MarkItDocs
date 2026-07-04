# MD → DOCX GUI

Pequeña app de escritorio Windows para convertir archivos Markdown (.md) a Word (.docx).

Requisitos

- Python 3.10+ (probado en 3.14)
- Paquetes listados en `requirements.txt`

Instalación

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Uso

```bash
python app.py
```

Arrastra uno o varios archivos `.md` a la ventana, selecciona una carpeta de salida (opcional) y presiona `Convertir`.

Empaquetado (opcional)

Para crear un ejecutable Windows con PyInstaller:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed app.py
```

Notas

- La app asume que el archivo `crear_documento.py` con la función `convert_markdown_file(source_path, output_path)` esté en la misma carpeta que `app.py`.
- Si `crear_documento.py` está en otro lugar, modifica el `sys.path` en `app.py` o copia `crear_documento.py` junto a `app.py`.

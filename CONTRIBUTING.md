# Contribuir a MarkItDocs

¡Gracias por tu interés! Guía rápida:

## Entorno de desarrollo

```bash
git clone https://github.com/<usuario>/MarkItDocs.git
cd MarkItDocs
python -m venv .venv
# Windows: .venv\Scripts\activate · Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

Para exportar PDF necesitas Microsoft Edge o Google Chrome instalado.

## Ejecutar los tests

```bash
python tests/test_crear_documento.py
python tests/test_markitpdf.py
```

Son self-checks ejecutables basados en `assert` (también compatibles con `pytest`). Toda contribución no trivial debe añadir o actualizar al menos un test.

## Pull requests

1. Crea una rama desde `main`: `git checkout -b mi-mejora`
2. Haz cambios pequeños y enfocados — un PR = una cosa
3. Verifica que los dos archivos de tests pasan en local
4. Describe en el PR **qué** cambia y **por qué**

## Estilo

- Python 3.11+, type hints en las firmas públicas
- Mensajes de commit en imperativo: "Add YAML theme support", "Fix merge page breaks"
- Español o inglés, ambos bienvenidos (el código y docstrings existentes están en español)

## Añadir un tema PDF nuevo

1. Copia `markitpdf/themes/professional.css` → `mitema.css`
2. Copia `markitpdf/themes/professional.json` → `mitema.json` (actualiza `name`, `css`, colores)
3. Listo: `available_themes()` lo detecta automáticamente y aparece en GUI y CLI

## Reportar bugs

Abre un issue con: sistema operativo, versión de Python, comando/acción exacta, y el archivo de entrada mínimo que reproduce el problema (si puedes compartirlo).

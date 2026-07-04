"""Self-check de humo: valida que convert_markdown_file produce un .docx real."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crear_documento import convert_markdown_file  # noqa: E402

SAMPLE_MARKDOWN = """# Documento de prueba

## Sección con tabla

| Col A | Col B |
|---|---|
| 1 | 2 |

- item uno
- item dos

```python
print("hola")
```

> Una cita breve.

[Enlace externo](https://example.com)
"""


def test_convert_produces_nonempty_docx():
    with tempfile.TemporaryDirectory() as tmp_dir:
        md_path = Path(tmp_dir) / "sample.md"
        md_path.write_text(SAMPLE_MARKDOWN, encoding="utf-8")

        output = convert_markdown_file(md_path)

        assert output.exists()
        assert output.stat().st_size > 1000, "El .docx generado es sospechosamente pequeño"
        assert output.suffix == ".docx"


def test_convert_with_missing_local_image():
    markdown_with_broken_image = SAMPLE_MARKDOWN + "\n![alt](no_existe.png)\n"
    with tempfile.TemporaryDirectory() as tmp_dir:
        md_path = Path(tmp_dir) / "sample.md"
        md_path.write_text(markdown_with_broken_image, encoding="utf-8")

        output = convert_markdown_file(md_path)

        assert output.exists(), "Debe generar el .docx aunque falte una imagen local"


if __name__ == "__main__":
    test_convert_produces_nonempty_docx()
    print("OK: test_convert_produces_nonempty_docx")
    test_convert_with_missing_local_image()
    print("OK: test_convert_with_missing_local_image")
    print("Todos los self-checks pasaron.")

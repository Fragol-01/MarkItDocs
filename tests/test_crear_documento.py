"""Self-check de humo: valida que convert_markdown_file produce un .docx real."""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crear_documento import convert_many, convert_markdown_file, validate_markdown_extension  # noqa: E402
from docx import Document  # noqa: E402

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


def test_rejects_non_markdown_extension():
    with tempfile.TemporaryDirectory() as tmp_dir:
        txt_path = Path(tmp_dir) / "fake.txt"
        txt_path.write_text("no soy markdown", encoding="utf-8")

        try:
            validate_markdown_extension(txt_path)
        except ValueError:
            pass
        else:
            raise AssertionError("Se esperaba ValueError para extensión .txt")


def test_pagebreak_inserts_real_page_break():
    markdown_with_break = "# Pagina 1\ntexto\n\n\\pagebreak\n\n# Pagina 2\ntexto\n"
    with tempfile.TemporaryDirectory() as tmp_dir:
        md_path = Path(tmp_dir) / "pb.md"
        md_path.write_text(markdown_with_break, encoding="utf-8")

        output = convert_markdown_file(md_path)
        document = Document(output)

        xml = document.element.xml
        assert 'type="page"' in xml, "Debe insertar un salto de página real en el XML"


def test_custom_theme_overrides_defaults():
    with tempfile.TemporaryDirectory() as tmp_dir:
        md_path = Path(tmp_dir) / "sample.md"
        md_path.write_text(SAMPLE_MARKDOWN, encoding="utf-8")

        theme_path = Path(tmp_dir) / "theme.json"
        theme_path.write_text(json.dumps({"title_color": [200, 30, 30], "body_font": "Georgia"}), encoding="utf-8")

        output = convert_markdown_file(md_path, theme_path=theme_path)
        document = Document(output)

        assert document.styles["Normal"].font.name == "Georgia"
        heading_color = document.paragraphs[0].runs[0].font.color.rgb
        assert str(heading_color) == "C81E1E"


def test_convert_many_batch():
    with tempfile.TemporaryDirectory() as tmp_dir:
        (Path(tmp_dir) / "a.md").write_text("# Doc A\ntexto\n", encoding="utf-8")
        (Path(tmp_dir) / "b.md").write_text("# Doc B\ntexto\n", encoding="utf-8")

        results = convert_many([str(Path(tmp_dir) / "*.md")])

        assert len(results) == 2
        assert all(r.exists() for r in results)


if __name__ == "__main__":
    test_convert_produces_nonempty_docx()
    print("OK: test_convert_produces_nonempty_docx")
    test_convert_with_missing_local_image()
    print("OK: test_convert_with_missing_local_image")
    test_rejects_non_markdown_extension()
    print("OK: test_rejects_non_markdown_extension")
    test_pagebreak_inserts_real_page_break()
    print("OK: test_pagebreak_inserts_real_page_break")
    test_custom_theme_overrides_defaults()
    print("OK: test_custom_theme_overrides_defaults")
    test_convert_many_batch()
    print("OK: test_convert_many_batch")
    print("Todos los self-checks pasaron.")

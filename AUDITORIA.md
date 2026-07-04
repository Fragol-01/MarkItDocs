# Auditoría técnica — MD → DOCX Converter

**Fecha:** 2026-07-04
**Alcance:** `app.py`, `crear_documento.py`, empaquetado PyInstaller, dependencias.

---

## Resumen

El motor de conversión (`crear_documento.py`) es sólido: código limpio, sin
dependencias muertas relevantes (tras esta auditoría), y probado end-to-end
con un documento real de 48 KB / ~1300 líneas (1.8s de conversión). La capa
GUI (`app.py`, PySimpleGUI) es la parte más frágil del proyecto.

## Cambios ya aplicados en esta sesión (bajo riesgo, sin tu confirmación explícita porque no alteran comportamiento visible)

| # | Cambio | Archivo | Por qué |
|---|---|---|---|
| 1 | Quitado `pillow` de `requirements.txt` | `requirements.txt` | No se importa en ningún lugar del código; era peso muerto en el `.exe` |
| 2 | `read_image_bytes()` ahora captura `URLError`/`TimeoutError`/`OSError` en descargas remotas en vez de dejar que el traceback mate la conversión completa | `crear_documento.py` | Antes: 1 imagen remota caída = conversión entera falla con traceback crudo. Ahora: se reporta "[Imagen no encontrada]" y el documento se genera igual |
| 3 | El `except Exception` silencioso en `_render_image()` ahora imprime la advertencia a `stderr` antes de continuar | `crear_documento.py` | Antes ocultaba el motivo real del fallo (imagen corrupta vs. formato no soportado vs. otro); ahora queda trazable en logs |
| 4 | Repo git propio inicializado con `.gitignore` | `.git/`, `.gitignore` | El proyecto vivía dentro del `.git` raíz de tu carpeta de usuario (`C:\Users\DANNY\.git`), sin aislamiento. Ahora tiene su propio historial, y `build/`, `dist/`, `*.docx` quedan excluidos del control de versiones |
| 5 | Test de humo (`tests/test_crear_documento.py`) | `tests/` | Antes: cero tests. Ahora hay un self-check ejecutable que valida conversión básica y el caso de imagen local faltante |

Verificado tras los cambios: `python crear_documento.py MODELO_NEGOCIO_DESARROLLO_WEB.md` sigue funcionando (exit 0), y ambos tests de humo pasan.

## Hallazgos pendientes — requieren tu decisión antes de tocarlos

### 🔴 Alto impacto

**H1 — PySimpleGUI es una dependencia de riesgo.**
El PyPI público solo distribuye ahora la v6.2 (LGPL3, lanzada 2026). Las
versiones 4.x/5.x mencionadas en tu propia documentación ya no están en el
índice público — fueron retiradas por incumplir los ToS de PyPI y viven en un
servidor privado. Probé la v6.2 contra tu `app.py` tal cual está y **funciona
por compatibilidad de API**, pero es una base inestable a futuro: no hay
garantía de que una reinstalación en otra máquina traiga la misma versión, y
el proyecto quedó huérfano commercialmente en 2025 antes de este relanzamiento
LGPL.
→ **Recomendación:** migrar a una librería con mantenimiento activo real:
`Flet` (Flutter+Python, drag-and-drop nativo, se ve moderna) o `CustomTkinter`
(más ligera, cambio de código menor). Ver Todo #1.

**H2 — La UI miente sobre drag-and-drop.**
El texto "Arrastra un archivo .md aquí" es falso: confirmé por investigación
que PySimpleGUI sobre tkinter (el backend que usas) **no soporta
drag-and-drop nativo de archivos** — solo existe en su puerto Qt (experimental
desde 2020). Un usuario que intente arrastrar un archivo no verá pasar nada,
sin ningún mensaje de error. Solo el botón "Seleccionar" funciona.
→ Se resuelve solo si migras de librería (H1), o cambiando el texto de la UI
mientras tanto para no prometer algo que no existe.

### 🟡 Impacto medio

**H3 — Sin control de paginación para documentos largos.**
No hay soporte para `\pagebreak` manual, ni reglas de "no cortar tabla a
mitad de página" (Word sí soporta esto vía `w:cantSplit` en XML, pero el
código actual no lo aplica). Para tu propio `MODELO_NEGOCIO_DESARROLLO_WEB.md`
(48 KB), esto puede generar tablas grandes cortadas de forma fea entre
páginas.

**H4 — Documentación desincronizada de la realidad.**
`DOCUMENTACION.md` y `GUIA_DISTRIBUCION.md` dicen que el `.exe` pesa "~170 MB"
en varios puntos, pero el archivo real en `dist/MD_to_DOCX.exe` pesa 17 MB
(10x menos). También afirman "Python 3.10+" como mínimo pero el build se hizo
con 3.14.6 sin validar hacia atrás. Esto puede confundir a quien retome el
proyecto después.

**H5 — Sin reintentos en descargas de imágenes remotas.**
Ya no rompe la conversión (fix aplicado, H2 en la tabla de arriba), pero
sigue sin reintentar — un timeout momentáneo de red descarta la imagen
definitivamente en ese intento.

### 🟢 Impacto bajo / cosmético

**H6 — Sin logging estructurado.** Los mensajes van a stdout/stderr sin
niveles (info/warning/error) ni timestamps — dificulta debug en producción
si esto se distribuye a más usuarios.

**H7 — `app.py` no valida extensión antes de convertir.** Si seleccionas
un archivo `.txt` renombrado a `.md`, no hay validación de contenido — se
intentará convertir igual (Markdown es permisivo, así que probablemente
"funcione" mal en vez de fallar con claridad).

**H8 — Sin barra de progreso real.** El log de texto muestra "Starting
conversion..." y luego "Documento creado" — para documentos grandes (100+
páginas) el usuario no sabe si el proceso sigue vivo o se colgó.

---

## Todo list priorizada (pendiente de tu aprobación)

- [ ] **Todo #1 (Alto):** Migrar `app.py` de PySimpleGUI a Flet o
  CustomTkinter — resuelve H1 y H2 de raíz, habilita drag-and-drop real.
- [ ] **Todo #2 (Medio):** Agregar soporte de salto de página manual
  (`\pagebreak` en Markdown → `document.add_page_break()`) y
  `page_break_before` en tablas grandes.
- [ ] **Todo #3 (Medio):** Corregir cifras en `DOCUMENTACION.md` y
  `GUIA_DISTRIBUCION.md` (tamaño real del .exe, versión mínima de Python
  validada).
- [ ] **Todo #4 (Bajo):** Agregar reintentos (2-3, backoff simple) en
  `read_image_bytes()` para descargas remotas.
- [ ] **Todo #5 (Bajo):** Reemplazar prints sueltos por `logging` con
  niveles.
- [ ] **Todo #6 (Bajo):** Validar que el archivo de entrada tiene extensión
  `.md`/`.markdown` antes de convertir, con mensaje de error claro si no.
- [ ] **Todo #7 (Bajo):** Barra de progreso indeterminada mientras la
  conversión corre (spinner o "trabajando..." animado).

## Sugerencias de nuevas funcionalidades (opcionales, para tu evaluación)

1. **Conversión batch real desde CLI**: `crear_documento.py *.md -o carpeta/`
   con soporte de glob, no solo un archivo a la vez.
2. **Exportar directo a PDF** además de DOCX, reutilizando el nuevo repo
   `MarkItPDF` que acabo de construir — un solo botón "Convertir a PDF" en
   la misma GUI.
3. **Perfil de estilos configurable**: hoy los colores/fuentes están
   hardcodeados (`TITLE_COLOR`, `BODY_FONT`, etc.) — podría exponerse un
   `.json`/`.toml` de tema para que cambies colores sin tocar código.
4. **Watch mode**: observar una carpeta y reconvertir automáticamente
   cuando un `.md` cambie (útil si editas y revisas el resultado
   repetidamente).

---

**Nota sobre `C:\Users\DANNY\.git`:** detecté que tu carpeta de usuario raíz
completa es un repositorio git (con cientos de miles de archivos de sistema
como untracked). No lo toqué ni lo modifiqué — solo lo señalo porque explica
por qué `git status` dentro de subcarpetas mostraba ruido masivo antes de que
aislara este proyecto en su propio repo.

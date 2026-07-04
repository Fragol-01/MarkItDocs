# 📄 MD → DOCX Converter - Documentación Completa

## 📋 Tabla de Contenidos

1. [Descripción del Proyecto](#descripción-del-proyecto)
2. [Requisitos Previos](#requisitos-previos)
3. [Instalación y Configuración](#instalación-y-configuración)
4. [Uso del Programa](#uso-del-programa)
5. [Estructura Técnica](#estructura-técnica)
6. [Características Implementadas](#características-implementadas)
7. [Empaquetado y Distribución](#empaquetado-y-distribución)
8. [Solución de Problemas](#solución-de-problemas)

---

## 🎯 Descripción del Proyecto

**MD → DOCX Converter** es una aplicación de escritorio para Windows que convierte archivos Markdown (.md) a documentos Word (.docx) con estilos profesionales y formato conservado.

### Características Principales

✅ **Interfaz Gráfica Amigable** - GUI basada en PySimpleGUI  
✅ **Conversión Markdown → Word** - Preserva formato y estructura  
✅ **Soporte para Elementos Complejos** - Tablas, imágenes, enlaces, código  
✅ **Tabla de Contenido Automática** - Generada desde encabezados  
✅ **Procesamiento Asincrónico** - No bloquea la interfaz  
✅ **CLI y GUI** - Úsalo como prefieras  
✅ **Aplicación Independiente** - Ejecutable .exe sin requerimientos Python  

---

## 💻 Requisitos Previos

### Para ejecutar desde código fuente:
- **Python 3.10+** (probado en 3.14.6)
- **pip** (gestor de paquetes Python)
- **Windows 7+** (sistema operativo)

### Para usar el ejecutable:
- Solo necesitas **Windows 7+** - No requiere Python instalado

---

## ⚙️ Instalación y Configuración

### Opción 1: Usar el Ejecutable (Recomendado)

1. Descarga `MD_to_DOCX.exe` de la carpeta `dist/`
2. Haz doble clic para ejecutar
3. ¡Listo! No necesitas instalar nada más

**Ubicación del ejecutable:**
```
C:\Users\DANNY\Desktop\Modelo de negocio Web\dist\MD_to_DOCX.exe
```

---

### Opción 2: Ejecutar desde Código Fuente

#### Paso 1: Configurar Entorno Virtual

```bash
# Navega a la carpeta del proyecto
cd "C:\Users\DANNY\Desktop\Modelo de negocio Web"

# Crea un entorno virtual
python -m venv .venv

# Activa el entorno (Windows)
.venv\Scripts\activate

# En PowerShell (si el comando anterior falla):
.venv\Scripts\Activate.ps1
```

#### Paso 2: Instalar Dependencias

```bash
pip install -r requirements.txt
```

**Dependencias instaladas:**
- `python-docx 1.2.0` - Creación y manipulación de documentos Word
- `markdown` - Conversión de Markdown a HTML
- `lxml 6.1.1` - Parseo de HTML
- `pillow 12.2.0` - Procesamiento de imágenes
- `PySimpleGUI` - Interfaz gráfica

#### Paso 3: Ejecutar la Aplicación

**Modo GUI (Recomendado):**
```bash
python app.py
```

**Modo CLI (Línea de Comandos):**
```bash
python crear_documento.py archivo_entrada.md -o archivo_salida.docx
```

---

## 📖 Uso del Programa

### Uso de la Interfaz Gráfica (GUI)

1. **Ejecuta la aplicación:**
   ```bash
   python app.py
   ```
   O haz doble clic en `MD_to_DOCX.exe`

2. **Selecciona archivo Markdown:**
   - Haz clic en "Seleccionar" para navegar y elegir un archivo `.md`
   - O arrastra y suelta el archivo directamente

3. **Elige carpeta de salida (opcional):**
   - Por defecto, el archivo .docx se guardará en la misma carpeta que el .md
   - Haz clic en "Carpeta salida" para especificar una ubicación diferente

4. **Haz clic en "Convertir":**
   - La aplicación procesará el archivo
   - Verás el progreso en el panel de log
   - Una vez completado, aparecerá el mensaje: `Documento creado: [ruta]`

5. **Cierra la aplicación:**
   - Haz clic en "Salir" o cierra la ventana

### Uso de la Línea de Comandos (CLI)

```bash
# Conversión básica (salida en la misma carpeta)
python crear_documento.py documento.md

# Conversión con salida especificada
python crear_documento.py documento.md -o ruta/salida.docx

# Ejemplo completo
python crear_documento.py "C:\Users\DANNY\Desktop\entrada.md" -o "C:\Users\DANNY\Desktop\salida.docx"
```

---

## 🏗️ Estructura Técnica

### Arquitectura del Proyecto

```
Modelo de negocio Web/
├── crear_documento.py          ← Motor de conversión (CLI)
├── app.py                      ← Interfaz gráfica (GUI)
├── requirements.txt            ← Dependencias de Python
├── README.md                   ← Instrucciones básicas
├── DOCUMENTACION.md            ← Este archivo
├── MD_to_DOCX.spec            ← Configuración de PyInstaller
├── dist/
│   └── MD_to_DOCX.exe         ← Ejecutable standalone
├── build/                      ← Archivos de compilación (temporal)
├── __pycache__/               ← Caché de Python (temporal)
└── MODELO_NEGOCIO_DESARROLLO_WEB.md  ← Archivo de prueba
```

### Pipeline de Conversión

```
Markdown File
    ↓
[crear_documento.py]
    ↓
markdown_to_html()  ← Convierte MD a HTML con extensiones
    ↓
lxml.html.fromstring()  ← Parsea HTML a árbol DOM
    ↓
MarkdownToDocxConverter.convert()  ← Renderiza a Word
    ↓
python-docx.Document  ← Manipula elementos .docx
    ↓
document.save()  ← Guarda a archivo
    ↓
Word Document (.docx)
```

### Clases Principales

#### 1. `MarkdownToDocxConverter`
Clase responsable de la conversión completa.

**Atributos:**
- `source_path` - Ruta del archivo Markdown
- `output_path` - Ruta de salida del DOCX
- `document` - Objeto Document de python-docx
- `bookmarks` - Set de nombres de marcadores para TOC
- `anchor_map` - Mapa de anclas → nombres de marcadores

**Métodos principales:**
- `convert(markdown_text: str) → Document` - Convierte texto Markdown a documento
- `_render_block(node)` - Renderiza bloques (párrafos, listas, tablas)
- `_render_inline_node(node, paragraph, style)` - Renderiza elementos inline
- `_render_table(node)` - Renderiza tablas con formato
- `_render_image(node)` - Inserta imágenes desde URL o local

#### 2. `InlineStyle`
Dataclass que representa estilos de texto inline.

```python
@dataclass(frozen=True)
class InlineStyle:
    bold: bool = False
    italic: bool = False
    code: bool = False
    strike: bool = False
    underline: bool = False
    color: RGBColor | None = None
```

### Funciones Clave

| Función | Propósito |
|---------|-----------|
| `convert_markdown_file()` | API pública para conversión |
| `markdown_to_html()` | Convierte MD a HTML con extensiones |
| `read_image_bytes()` | Carga imágenes (local, URL, data URI) |
| `add_toc_field()` | Inserta campo TOC dinámico |
| `add_bookmark()` | Crea marcadores para enlaces internos |
| `add_hyperlink()` | Añade enlaces (internos/externos) |
| `slugify()` | Convierte texto a identificador válido |

---

## ✨ Características Implementadas

### Elementos Markdown Soportados

#### Encabezados
```markdown
# Encabezado 1
## Encabezado 2
### Encabezado 3
...
###### Encabezado 6
```
✅ Renderiza con estilos jerárquicos y color profesional (azul marino)

#### Párrafos
```markdown
Este es un párrafo normal con espaciado automático.
```

#### Énfasis
```markdown
**Texto en negrita**
__También negrita__
*Texto en cursiva*
_También cursiva_
~~Texto tachado~~
```

#### Listas
```markdown
- Elemento de lista
  - Sublista anidada
  
1. Lista numerada
   1. Subnumerada
```
✅ Soporta anidamiento múltiple

#### Tablas
```markdown
| Encabezado 1 | Encabezado 2 |
|---|---|
| Celda 1 | Celda 2 |
```
✅ Encabezados con fondo azul claro, contenido centrado

#### Código
```markdown
`código inline`

```python
# Bloque de código
def hola():
    print("Hola")
```
```
✅ Sintaxis con fondo gris, fuente monoespaciada (Consolas)

#### Citas
```markdown
> Esta es una cita
> Puede ocupar múltiples líneas
```
✅ Fondo gris claro, indentación izquierda

#### Enlaces
```markdown
[Texto enlace](https://ejemplo.com)
[Enlace interno](#seccion)
```
✅ Enlaces externos en azul con subrayado  
✅ Enlaces internos referenciados a marcadores

#### Imágenes
```markdown
![Alt text](imagen.png)
![Remote](https://ejemplo.com/imagen.jpg)
```
✅ Imágenes locales, remotas y data URIs
✅ Redimensionamiento automático al ancho de página

#### Tabla de Contenido
```markdown
[toc]
[[toc]]
<!-- toc -->
```
✅ Campo TOC dinámico actualizable en Word

#### Línea Horizontal
```markdown
---
***
___
```

### Estilos Aplicados

**Tipografía:**
- Cuerpo: Calibri 10.5pt
- Código: Consolas 9.5pt
- Encabezados: Calibri Bold, tamaños escalonados (20pt → 10pt)

**Colores:**
- Títulos: RGB(31, 78, 121) - Azul profesional
- Enlaces: RGB(0, 102, 204) - Azul claro
- Regla horizontal: RGB(180, 190, 205) - Gris

**Márgenes de Página:**
- Superior/Inferior: 0.7"
- Izquierdo/Derecho: 0.8"

---

## 📦 Empaquetado y Distribución

### Proceso de Creación del Ejecutable

Este es el proceso completo que se ejecutó para generar `MD_to_DOCX.exe`:

#### Paso 1: Instalar PyInstaller
```bash
pip install pyinstaller
```

#### Paso 2: Generar el Ejecutable
```bash
cd "C:\Users\DANNY\Desktop\Modelo de negocio Web"

pyinstaller --onefile --windowed --name="MD_to_DOCX" --icon=NONE app.py
```

**Parámetros explicados:**
- `--onefile` - Genera un único archivo ejecutable (no carpeta con DLLs)
- `--windowed` - Oculta ventana de consola (interfaz gráfica solo)
- `--name="MD_to_DOCX"` - Nombre del ejecutable
- `--icon=NONE` - Sin icono personalizado
- `app.py` - Archivo principal a empaquetar

#### Paso 3: Artefactos Generados

```
dist/
└── MD_to_DOCX.exe              ← EJECUTABLE FINAL (~170 MB)

build/
└── MD_to_DOCX/                 ← Archivos de compilación (temporal)
    ├── base_library.zip
    ├── PYZ-00.pyz
    ├── MD_to_DOCX.pkg
    └── xref-MD_to_DOCX.html

MD_to_DOCX.spec                 ← Configuración PyInstaller
```

#### Información del Ejecutable

| Propiedad | Valor |
|-----------|-------|
| Nombre | `MD_to_DOCX.exe` |
| Tamaño | ~170 MB |
| Ubicación | `dist/MD_to_DOCX.exe` |
| Plataforma | Windows 64-bit |
| Versión Python | 3.14.6 |
| Dependencias | Incluidas en el .exe |
| Instalador | No requiere (standalone) |

#### Distribución del Ejecutable

El archivo `MD_to_DOCX.exe` es **completamente independiente**. Para distribuirlo:

1. **Copia solo `dist/MD_to_DOCX.exe`** a otro ordenador
2. **No necesita Python instalado**
3. **No necesita dependencias externas**
4. **Funciona en Windows 7+**

```bash
# Simplemente cópialo:
xcopy "C:\Users\DANNY\Desktop\Modelo de negocio Web\dist\MD_to_DOCX.exe" "C:\ruta\destino\"
```

### Regenerar el Ejecutable

Si necesitas modificar el código y regenerar el .exe:

```bash
cd "C:\Users\DANNY\Desktop\Modelo de negocio Web"

# Limpia compilaciones anteriores
rmdir /s /q build dist __pycache__ 2>nul
del *.spec 2>nul

# Regenera el ejecutable
pyinstaller --onefile --windowed --name="MD_to_DOCX" --icon=NONE app.py

# Tu nuevo .exe está en dist/
```

---

## 🆘 Solución de Problemas

### Problema: "No se pudo importar convert_markdown_file"

**Síntoma:** Error al ejecutar `app.py`

**Solución:**
```bash
# Asegúrate de estar en la carpeta correcta
cd "C:\Users\DANNY\Desktop\Modelo de negocio Web"

# Verifica que `crear_documento.py` existe:
dir crear_documento.py

# Intenta ejecutar directamente:
python app.py
```

### Problema: Imagen no se carga en el documento

**Síntoma:** Mensaje "[Imagen no encontrada]" en el .docx

**Causas posibles:**
- Ruta relativa incorrecta (asegúrate de usar rutas completas)
- Archivo de imagen no existe
- Formato de imagen no soportado

**Soluciones:**
```markdown
# ❌ Esto puede fallar:
![alt](imagen.png)

# ✅ Usa rutas completas:
![alt](C:\ruta\completa\imagen.png)

# ✅ O descarga desde URL:
![alt](https://ejemplo.com/imagen.jpg)
```

### Problema: Tabla no se renderiza correctamente

**Síntoma:** Tabla vacía o mal formateada

**Causa:** Markdown de tabla incorrecto

**Verificación:**
```markdown
# ✅ Formato correcto:
| Col1 | Col2 |
|------|------|
| Dato | Dato |

# ❌ Formato incorrecto (sin separadores):
| Col1 | Col2 |
| Dato | Dato |
```

### Problema: El ejecutable no inicia

**Síntoma:** Haces doble clic en `MD_to_DOCX.exe` y no ocurre nada

**Soluciones:**
1. Abre PowerShell o CMD y ejecuta:
   ```bash
   C:\ruta\a\MD_to_DOCX.exe
   ```
2. Busca mensajes de error en la consola
3. Comprueba que Windows Defender no lo bloquea
   - Si muestra aviso: Haz clic "Ejecutar de todas formas"

### Problema: Conversión lenta

**Síntoma:** Tarda mucho tiempo en convertir

**Causas:**
- Archivo muy grande (100+ páginas)
- Muchas imágenes remotas (descargas lentas)
- Imágenes de muy alta resolución

**Optimización:**
- Comprime imágenes antes de convertir
- Reemplaza URLs remotas con imágenes locales

---

## 📚 Ejemplos de Uso

### Ejemplo 1: Convertir archivo simple

**Entrada: `documento.md`**
```markdown
# Mi Documento

Este es un párrafo introductorio.

## Sección 1

- Punto 1
- Punto 2
- Punto 3

## Sección 2

```python
print("Hola mundo")
```
```

**Comando:**
```bash
python crear_documento.py documento.md -o salida.docx
```

**Resultado:** `salida.docx` con formato profesional, tabla de contenido automática, y estilos preservados.

---

### Ejemplo 2: Convertir con imágenes

**Entrada: `articulo.md`**
```markdown
# Artículo con Imágenes

![Logo](https://ejemplo.com/logo.png)

Párrafo con referencia a imagen.
```

**Comando (GUI):**
1. Ejecuta: `python app.py`
2. Selecciona `articulo.md`
3. Haz clic "Convertir"
4. El documento se guarda automáticamente

**Resultado:** Imágenes descargadas e incrustadas en el .docx

---

### Ejemplo 3: Usar batch para conversión múltiple

**Script: `convertir_todos.bat`**
```batch
@echo off
cd "C:\Users\DANNY\Desktop\Modelo de negocio Web"

for %%f in (*.md) do (
    echo Convirtiendo %%f...
    python crear_documento.py "%%f" -o "salida_%%~nf.docx"
)

echo Listo!
pause
```

Ejecución:
```bash
convertir_todos.bat
```

---

## 📞 Contacto y Soporte

Para reportar problemas o sugerencias:

1. Verifica el archivo de log en la aplicación
2. Comprueba que las dependencias están instaladas correctamente
3. Intenta con un archivo Markdown simple para descartar problemas complejos

---

## 📝 Histórico de Cambios

### Versión 1.0 - Inicial (2026-07-04)
- ✅ Conversión Markdown → Word
- ✅ Interfaz gráfica PySimpleGUI
- ✅ Soporte para tablas, imágenes, enlaces
- ✅ Tabla de contenido automática
- ✅ Empaquetado con PyInstaller
- ✅ Ejecutable standalone para Windows

---

## 📄 Licencia

Este proyecto es de uso libre para propósitos personales y comerciales.

---

**Última actualización:** 2026-07-04  
**Versión:** 1.0  
**Estado:** ✅ Producción

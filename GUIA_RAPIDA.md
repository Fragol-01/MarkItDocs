# ⚡ Guía Rápida - MD to DOCX Converter

## 🎯 Uso Inmediato

### Opción 1: Ejecutable (Sin instalación)
```
1. Descarga/Abre: MD_to_DOCX.exe
2. Arrastra tu(s) archivo(s) .md a la ventana (o usa "Seleccionar")
3. Haz clic "Convertir a Word" o "Convertir a PDF"
4. ¡Listo! Tu documento está en la carpeta de salida
```

### Opción 2: Desde Python
```bash
# Navega a la carpeta
cd "C:\Users\DANNY\Desktop\Modelo de negocio Web"

# Ejecuta la interfaz
python app.py

# O línea de comandos:
python crear_documento.py documento.md -o salida.docx

# Batch (varios archivos):
python crear_documento.py "carpeta/*.md" -o carpeta_salida/

# Watch mode (reconvierte al guardar cambios):
python crear_documento.py documento.md --watch
```

---

## 📝 Elementos Soportados

| Elemento | Markdown | Estado |
|----------|----------|--------|
| Títulos | `# Título` | ✅ |
| Negrita | `**texto**` | ✅ |
| Cursiva | `*texto*` | ✅ |
| Listas | `- item` | ✅ |
| Tablas | Markdown table | ✅ |
| Código | `` `código` `` | ✅ |
| Imágenes | `![alt](url)` | ✅ |
| Enlaces | `[texto](url)` | ✅ |
| Citas | `> cita` | ✅ |
| TOC | `[toc]` | ✅ |

---

## 💾 Carpeta del Proyecto

```
Modelo de negocio Web/
├── MD_to_DOCX.exe          ← EJECUTABLE (úsalo)
├── DOCUMENTACION.md        ← Guía completa
├── GUIA_DISTRIBUCION.md    ← Detalles técnicos
├── app.py                  ← Código GUI
├── crear_documento.py      ← Motor de conversión
└── requirements.txt        ← Dependencias
```

---

## ❓ Preguntas Frecuentes

**P: ¿Necesito Python instalado?**  
R: NO. El .exe incluye todo. Solo descárgalo y úsalo.

**P: ¿Qué archivos .md soporta?**  
R: Todos. Cualquier archivo Markdown estándar.

**P: ¿Puedo convertir múltiples archivos?**  
R: Sí. En la GUI arrastra varios archivos a la vez (drag-and-drop real), o
usa `crear_documento.py "carpeta/*.md"` desde la CLI.

**P: ¿Puedo exportar a PDF además de Word?**  
R: Sí, con el botón "Convertir a PDF" (requiere el repo hermano MarkItPDF
instalado — ver README.md).

**P: ¿Se guarda en la misma carpeta?**  
R: Sí, por defecto. Puedes cambiar la ubicación.

---

## 🆘 Problema Común

**No inicia el .exe**
```bash
# Abre PowerShell en la carpeta dist y prueba:
.\MD_to_DOCX.exe

# Si falla, ejecuta directamente con Python:
cd "C:\Users\DANNY\Desktop\Modelo de negocio Web"
python app.py
```

---

✅ **¡Listo para usar!** Disfruta convertiendo Markdown a Word.

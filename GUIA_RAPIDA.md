# ⚡ Guía Rápida - MD to DOCX Converter

## 🎯 Uso Inmediato

### Opción 1: Ejecutable (Sin instalación)
```
1. Descarga/Abre: MD_to_DOCX.exe
2. Haz doble clic
3. Selecciona archivo .md
4. Haz clic "Convertir"
5. ¡Listo! Tu .docx está listo
```

### Opción 2: Desde Python
```bash
# Navega a la carpeta
cd "C:\Users\DANNY\Desktop\Modelo de negocio Web"

# Ejecuta la interfaz
python app.py

# O línea de comandos:
python crear_documento.py documento.md -o salida.docx
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
R: Sí. En la GUI arrastra varios archivos.

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

"""Diseñador visual de MarkItDocs: editor de temas con vista previa en vivo.

Tres columnas: elementos del documento (izq.) → vista previa del PDF real
(centro) → propiedades del elemento seleccionado (der.). Cada cambio
re-renderiza la muestra con debounce. «Guardar como tema» publica el tema en
la carpeta del usuario y queda disponible para PDF y Word.

Límite conocido (declarado): no es un lienzo drag-and-drop libre — el flujo
del documento lo dicta tu contenido; aquí controlas el ESTILO de cada
elemento. Para maquetas totalmente libres usa la vía LaTeX (preámbulo).
"""

from __future__ import annotations

import queue
import tempfile
import threading
from pathlib import Path
from tkinter import colorchooser, font as tkfont, messagebox

import customtkinter as ctk

from markitpdf.converter import MarkdownToPdfConverter
from markitpdf.preview import pdf_to_images
from markitpdf.themebuilder import (
    SAMPLE_MARKDOWN,
    build_css,
    model_from_theme,
    save_custom_theme,
)

#: (id de sección del modelo, etiqueta visible)
ELEMENTS = [
    ("page", "Página y márgenes"),
    ("base", "Texto base"),
    ("h1", "Título H1"),
    ("h2", "Título H2"),
    ("h3", "Título H3"),
    ("link", "Enlaces"),
    ("table", "Tablas"),
    ("quote", "Citas"),
    ("code", "Código"),
    ("hr", "Separadores"),
    ("latex", "LaTeX (preámbulo)"),
]

#: Propiedades por elemento: (clave, etiqueta, tipo, extra)
#: tipos: color | font | number (extra=(min,max,paso)) | bool | choice (extra=lista)
PROPS: dict[str, list[tuple]] = {
    "page": [
        ("size", "Tamaño de página", "choice", ["A4", "Letter"]),
        ("margin_top_cm", "Margen superior (cm)", "number", (1.0, 4.0, 0.1)),
        ("margin_bottom_cm", "Margen inferior (cm)", "number", (1.0, 4.0, 0.1)),
        ("margin_left_cm", "Margen izquierdo (cm)", "number", (1.0, 4.0, 0.1)),
        ("margin_right_cm", "Margen derecho (cm)", "number", (1.0, 4.0, 0.1)),
    ],
    "base": [
        ("font", "Fuente del cuerpo", "font", None),
        ("heading_font", "Fuente de títulos", "font", None),
        ("size_pt", "Tamaño (pt)", "number", (8.0, 14.0, 0.5)),
        ("color", "Color del texto", "color", None),
        ("line_height", "Interlineado", "number", (1.0, 2.2, 0.05)),
        ("justify", "Justificar párrafos", "bool", None),
    ],
    "h1": [
        ("size_pt", "Tamaño (pt)", "number", (14.0, 40.0, 0.5)),
        ("color", "Color", "color", None),
        ("bold", "Negrita", "bool", None),
        ("italic", "Cursiva", "bool", None),
        ("align", "Alineación", "choice", ["left", "center", "right"]),
        ("rule", "Línea inferior", "bool", None),
    ],
    "h2": [
        ("size_pt", "Tamaño (pt)", "number", (11.0, 28.0, 0.5)),
        ("color", "Color", "color", None),
        ("bold", "Negrita", "bool", None),
        ("italic", "Cursiva", "bool", None),
        ("align", "Alineación", "choice", ["left", "center", "right"]),
        ("rule", "Línea inferior", "bool", None),
    ],
    "h3": [
        ("size_pt", "Tamaño (pt)", "number", (10.0, 22.0, 0.5)),
        ("color", "Color", "color", None),
        ("bold", "Negrita", "bool", None),
        ("italic", "Cursiva", "bool", None),
        ("align", "Alineación", "choice", ["left", "center", "right"]),
    ],
    "link": [
        ("color", "Color", "color", None),
        ("underline", "Subrayado", "bool", None),
    ],
    "table": [
        ("head_fill", "Fondo de cabecera", "color", None),
        ("head_color", "Texto de cabecera", "color", None),
        ("border_color", "Color de bordes", "color", None),
        ("zebra", "Filas alternas (cebra)", "bool", None),
        ("zebra_fill", "Color filas alternas", "color", None),
    ],
    "quote": [
        ("fill", "Fondo", "color", None),
        ("bar_color", "Barra lateral", "color", None),
        ("text_color", "Color del texto", "color", None),
        ("italic", "Cursiva", "bool", None),
    ],
    "code": [
        ("font", "Fuente monoespaciada", "font", None),
        ("fill", "Fondo", "color", None),
        ("color", "Color del texto", "color", None),
        ("size_pt", "Tamaño (pt)", "number", (7.0, 13.0, 0.5)),
    ],
    "hr": [
        ("color", "Color", "color", None),
    ],
}


class DesignerWindow(ctk.CTkToplevel):
    def __init__(self, parent, base_theme: str = "professional", on_saved=None) -> None:
        super().__init__(parent)
        self.title("Diseñador visual — MarkItDocs")
        self.geometry("1280x840")
        self.minsize(1080, 700)
        self.transient(parent)

        self.model = model_from_theme(base_theme)
        self.on_saved = on_saved
        self.latex_preamble = ""
        self.selected_element = "base"

        self._queue: queue.Queue = queue.Queue()
        self._gen = 0
        self._after_id = None
        self._images: list = []
        self._page = 0
        self._ctk_image = None

        self._font_families = self._load_fonts()
        self._build_ui()
        self._select_element("base")
        self.after(100, self._drain)
        self._schedule_render(delay_ms=100)

    @staticmethod
    def _load_fonts() -> list[str]:
        try:
            families = sorted({f for f in tkfont.families() if not f.startswith("@")})
        except Exception:
            families = []
        return families or ["Segoe UI", "Arial", "Calibri", "Georgia", "Consolas"]

    # ------------------------------------------------------------------ UI

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0)
        self.grid_rowconfigure(0, weight=1)

        # ── Izquierda: elementos ──
        left = ctk.CTkFrame(self, width=210, corner_radius=10)
        left.grid(row=0, column=0, sticky="nsw", padx=(14, 6), pady=14)
        left.grid_propagate(False)
        ctk.CTkLabel(left, text="ELEMENTOS", font=ctk.CTkFont(size=12, weight="bold")).pack(
            anchor="w", padx=14, pady=(12, 6)
        )
        self._element_buttons: dict[str, ctk.CTkButton] = {}
        for key, label in ELEMENTS:
            btn = ctk.CTkButton(
                left, text=label, anchor="w", fg_color="transparent",
                text_color=("gray10", "gray90"), hover_color=("gray80", "gray25"),
                command=lambda k=key: self._select_element(k),
            )
            btn.pack(fill="x", padx=8, pady=1)
            self._element_buttons[key] = btn

        # ── Centro: vista previa ──
        center = ctk.CTkFrame(self, corner_radius=10)
        center.grid(row=0, column=1, sticky="nsew", padx=6, pady=14)
        center.grid_columnconfigure(0, weight=1)
        center.grid_rowconfigure(1, weight=1)

        controls = ctk.CTkFrame(center, fg_color="transparent")
        controls.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 4))
        ctk.CTkButton(controls, text="◀", width=34, command=lambda: self._nav(-1)).pack(side="left")
        self.page_label = ctk.CTkLabel(controls, text="– / –", width=54)
        self.page_label.pack(side="left", padx=4)
        ctk.CTkButton(controls, text="▶", width=34, command=lambda: self._nav(+1)).pack(side="left")
        self.status_label = ctk.CTkLabel(
            controls, text="", font=ctk.CTkFont(size=11), text_color=("gray35", "gray65")
        )
        self.status_label.pack(side="left", padx=12)
        ctk.CTkButton(controls, text="⟳ Actualizar", width=100,
                      command=lambda: self._schedule_render(0)).pack(side="right")

        self.image_label = ctk.CTkLabel(center, text="Generando vista previa…")
        self.image_label.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        # ── Derecha: propiedades ──
        right = ctk.CTkFrame(self, width=300, corner_radius=10)
        right.grid(row=0, column=2, sticky="nse", padx=(6, 14), pady=14)
        right.grid_propagate(False)
        self.props_title = ctk.CTkLabel(
            right, text="PROPIEDADES", font=ctk.CTkFont(size=12, weight="bold")
        )
        self.props_title.pack(anchor="w", padx=14, pady=(12, 4))
        self.props_frame = ctk.CTkScrollableFrame(right, fg_color="transparent")
        self.props_frame.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        # ── Barra inferior: guardar ──
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=1, column=0, columnspan=3, sticky="ew", padx=14, pady=(0, 12))
        bottom.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(bottom, text="Nombre del tema:").grid(row=0, column=0, padx=(2, 8))
        self.name_entry = ctk.CTkEntry(bottom, placeholder_text="Mi tema personalizado")
        self.name_entry.grid(row=0, column=1, sticky="ew")
        ctk.CTkButton(
            bottom, text="💾 Guardar como tema (Word y PDF)", width=240,
            command=self._save,
        ).grid(row=0, column=2, padx=(10, 0))

    def _select_element(self, key: str) -> None:
        self.selected_element = key
        for k, btn in self._element_buttons.items():
            btn.configure(
                fg_color=("#3B8ED0" if k == key else "transparent"),
                text_color=("white" if k == key else ("gray10", "gray90")),
            )
        for child in self.props_frame.winfo_children():
            child.destroy()

        label = dict(ELEMENTS)[key]
        self.props_title.configure(text=f"PROPIEDADES — {label.upper()}")

        if key == "latex":
            self._build_latex_panel()
            return
        for prop_key, prop_label, kind, extra in PROPS[key]:
            self._build_control(key, prop_key, prop_label, kind, extra)

    # ------------------------------------------------------------ controles

    def _build_control(self, section: str, key: str, label: str, kind: str, extra) -> None:
        holder = ctk.CTkFrame(self.props_frame, fg_color="transparent")
        holder.pack(fill="x", padx=6, pady=4)
        ctk.CTkLabel(holder, text=label, anchor="w", font=ctk.CTkFont(size=12)).pack(anchor="w")
        value = self.model[section][key]

        if kind == "color":
            btn = ctk.CTkButton(
                holder, text=str(value).upper(), width=130,
                fg_color=value, hover_color=value,
                text_color=self._contrast_text(value), border_width=1,
            )
            btn.configure(command=lambda b=btn, s=section, k=key: self._pick_color(b, s, k))
            btn.pack(anchor="w", pady=2)
        elif kind == "font":
            combo = ctk.CTkComboBox(
                holder, values=self._font_families, width=240,
                command=lambda v, s=section, k=key: self._set_value(s, k, v),
            )
            combo.set(str(value))
            combo.bind("<Return>", lambda e, c=combo, s=section, k=key: self._set_value(s, k, c.get()))
            combo.bind("<FocusOut>", lambda e, c=combo, s=section, k=key: self._set_value(s, k, c.get()))
            combo.pack(anchor="w", pady=2)
        elif kind == "number":
            lo, hi, step = extra
            row = ctk.CTkFrame(holder, fg_color="transparent")
            row.pack(fill="x", pady=2)
            value_label = ctk.CTkLabel(row, text=f"{float(value):g}", width=44)
            steps = max(1, int(round((hi - lo) / step)))
            slider = ctk.CTkSlider(
                row, from_=lo, to=hi, number_of_steps=steps, width=180,
                command=lambda v, s=section, k=key, vl=value_label, st=step:
                    self._set_number(s, k, v, vl, st),
            )
            slider.set(float(value))
            slider.pack(side="left")
            value_label.pack(side="left", padx=(8, 0))
        elif kind == "bool":
            switch = ctk.CTkSwitch(
                holder, text="", width=44,
            )
            switch.configure(command=lambda sw=switch, s=section, k=key:
                             self._set_value(s, k, bool(sw.get())))
            if value:
                switch.select()
            switch.pack(anchor="w", pady=2)
        elif kind == "choice":
            menu = ctk.CTkOptionMenu(
                holder, values=list(extra), width=150,
                command=lambda v, s=section, k=key: self._set_value(s, k, v),
            )
            menu.set(str(value))
            menu.pack(anchor="w", pady=2)

    def _build_latex_panel(self) -> None:
        note = ctk.CTkLabel(
            self.props_frame, justify="left", anchor="w", wraplength=250,
            font=ctk.CTkFont(size=11), text_color=("gray30", "gray70"),
            text="Código que se inyecta en el preámbulo cuando exportas PDF con "
                 "una plantilla LaTeX: fuentes (fontspec), colores (xcolor), "
                 "márgenes (geometry)… Personalización infinita. Se guarda junto "
                 "al tema.",
        )
        note.pack(fill="x", padx=6, pady=(0, 6))
        box = ctk.CTkTextbox(self.props_frame, height=320, wrap="none",
                             font=ctk.CTkFont(family="Consolas", size=12))
        box.pack(fill="both", expand=True, padx=6)
        box.insert("1.0", self.latex_preamble)

        def apply() -> None:
            self.latex_preamble = box.get("1.0", "end-1c")
            self.status_label.configure(text="Preámbulo LaTeX guardado en el tema.")

        ctk.CTkButton(self.props_frame, text="Aplicar preámbulo", command=apply).pack(
            anchor="e", padx=6, pady=8
        )

    @staticmethod
    def _contrast_text(hex_color: str) -> str:
        try:
            h = hex_color.lstrip("#")
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            return "black" if (r * 299 + g * 587 + b * 114) / 1000 > 140 else "white"
        except Exception:
            return "black"

    def _pick_color(self, button, section: str, key: str) -> None:
        initial = self.model[section][key]
        _, hex_color = colorchooser.askcolor(color=initial, parent=self)
        if hex_color:
            button.configure(fg_color=hex_color, hover_color=hex_color,
                             text=hex_color.upper(),
                             text_color=self._contrast_text(hex_color))
            self._set_value(section, key, hex_color)

    def _set_number(self, section: str, key: str, value: float, label, step: float) -> None:
        value = round(round(value / step) * step, 3)
        label.configure(text=f"{value:g}")
        self._set_value(section, key, value)

    def _set_value(self, section: str, key: str, value) -> None:
        if self.model[section][key] != value:
            self.model[section][key] = value
            self._schedule_render()

    # -------------------------------------------------------------- render

    def _schedule_render(self, delay_ms: int = 500) -> None:
        if self._after_id is not None:
            self.after_cancel(self._after_id)
        self._after_id = self.after(delay_ms, self._start_render)

    def _start_render(self) -> None:
        self._after_id = None
        self._gen += 1
        gen = self._gen
        css = build_css(self.model)
        self.status_label.configure(text="Generando vista previa…")
        threading.Thread(target=self._render_worker, args=(gen, css), daemon=True).start()

    def _render_worker(self, gen: int, css: str) -> None:
        try:
            with tempfile.TemporaryDirectory(prefix="markitdocs_designer_", ignore_cleanup_errors=True) as tmp:
                sample = Path(tmp) / "muestra.md"
                sample.write_text(SAMPLE_MARKDOWN, encoding="utf-8")
                pdf = Path(tmp) / "muestra.pdf"
                MarkdownToPdfConverter(custom_css=css).convert(sample, pdf)
                images = pdf_to_images(pdf, scale=1.5, max_pages=6)
            self._queue.put(("ok", gen, images))
        except Exception as exc:
            self._queue.put(("err", gen, str(exc)))

    def _drain(self) -> None:
        try:
            while True:
                kind, gen, payload = self._queue.get_nowait()
                if gen != self._gen:
                    continue
                if kind == "ok":
                    self._images = payload
                    self._page = min(self._page, len(payload) - 1)
                    self.status_label.configure(text="Vista del PDF real")
                    self._show_page()
                else:
                    self.status_label.configure(text=f"✖ {payload[:180]}")
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(120, self._drain)

    def _show_page(self) -> None:
        if not self._images:
            return
        total = len(self._images)
        self._page = max(0, min(self._page, total - 1))
        img = self._images[self._page]
        panel_h = max(460, self.image_label.winfo_height() or 640)
        display_h = panel_h
        display_w = int(display_h * img.width / img.height)
        self._ctk_image = ctk.CTkImage(light_image=img, dark_image=img,
                                       size=(display_w, display_h))
        self.image_label.configure(image=self._ctk_image, text="")
        self.page_label.configure(text=f"{self._page + 1} / {total}")

    def _nav(self, delta: int) -> None:
        if self._images:
            self._page += delta
            self._show_page()

    # --------------------------------------------------------------- save

    def _save(self) -> None:
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("Nombre requerido",
                                   "Escribe un nombre para tu tema.", parent=self)
            return
        try:
            theme_id = save_custom_theme(name, self.model, latex_preamble=self.latex_preamble)
        except Exception as exc:
            messagebox.showerror("Diseñador", f"No se pudo guardar el tema: {exc}", parent=self)
            return
        if self.on_saved is not None:
            self.on_saved(theme_id, self.latex_preamble)
        self.destroy()

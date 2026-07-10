"""MarkItDocs — GUI de escritorio para convertir Markdown/HTML a Word/PDF.

Secciones: ① Archivos (lista reordenable) → ② Opciones (tema único, salida,
unir) → ③ Convertir (Word/PDF, progreso, registro con colores).
El orden visible de la lista es el orden en que se unen los documentos.
"""

import logging
import queue
import sys
import tempfile
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from tkinterdnd2 import DND_FILES, TkinterDnD

sys.path.insert(0, str(Path(__file__).resolve().parent))

from crear_documento import (  # noqa: E402
    SUPPORTED_EXTENSIONS,
    convert_merged_from_patterns,
    convert_source_file,
    load_theme,
)
from markitpdf import (  # noqa: E402
    BrowserNotFoundError,
    LatexNotFoundError,
    MarkdownToPdfConverter,
    available_latex_templates,
    available_themes,
    compile_tex,
    convert_markdown_via_latex,
    download_tectonic,
    find_browser,
    find_latex_engine,
    get_latex_template_meta,
    get_theme_metadata,
    instantiate_starter,
)
from markitpdf.preview import pdf_to_images  # noqa: E402
from designer import DesignerWindow  # noqa: E402

#: La GUI también acepta .tex (solo para PDF; Word los omite con aviso).
TEX_EXTENSION = ".tex"
GUI_EXTENSIONS = SUPPORTED_EXTENSIONS | {TEX_EXTENSION}

ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")

WINDOW_TITLE = "MarkItDocs — MD/HTML → Word/PDF"
WINDOW_SIZE = "860x740"
ACCENT = "#3B8ED0"


class QueueLogHandler(logging.Handler):
    """Reenvía registros de logging a una cola thread-safe para mostrarlos en la GUI."""

    def __init__(self, log_queue: queue.Queue) -> None:
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record: logging.LogRecord) -> None:
        kind = "error" if record.levelno >= logging.ERROR else "log"
        self.log_queue.put((kind, self.format(record)))


class DnDWindow(TkinterDnD.DnDWrapper, ctk.CTk):
    """CTk root con soporte de drag-and-drop nativo (mixin estándar CTk+TkinterDnD)."""

    def __init__(self) -> None:
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)


class App:
    def __init__(self) -> None:
        self.root = DnDWindow()
        self.root.title(WINDOW_TITLE)
        self.root.geometry(WINDOW_SIZE)
        self.root.minsize(680, 620)

        self.event_queue: queue.Queue = queue.Queue()
        self.selected_files: list[Path] = []
        self.output_dir: Path | None = None
        themes = available_themes()
        default_theme = "professional" if "professional" in themes else (themes[0] if themes else "professional")
        self.theme_name = ctk.StringVar(value=default_theme)
        self.merge_mode = ctk.BooleanVar(value=False)
        self._busy = False

        # Vía PDF: temas HTML (navegador) o plantillas LaTeX (motor LaTeX)
        wrappers = available_latex_templates(kind="wrapper")
        self.pdf_engine_mode = ctk.StringVar(value="html")
        self.latex_template = ctk.StringVar(
            value="informe-moderno" if "informe-moderno" in wrappers else (wrappers[0] if wrappers else "")
        )
        self.latex_author = ctk.StringVar(value="")
        self.latex_preamble = ""
        self.latex_engine = None

        # Vista previa en vivo
        self.preview_visible = False
        self._preview_images: list = []
        self._preview_ctk_image = None
        self._preview_page = 0
        self._preview_zoom = 1.0
        self._preview_gen = 0
        self._preview_after_id = None

        self._build_layout()
        self._attach_logging()
        self.root.after(100, self._drain_queue)
        self._check_browser()
        self._check_latex()
        self._update_pdf_button()

    # ------------------------------------------------------------------ UI

    def _build_layout(self) -> None:
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=0)  # panel de vista previa
        self.root.grid_rowconfigure(1, weight=3)   # lista de archivos
        self.root.grid_rowconfigure(5, weight=2)   # registro

        # ── ① ARCHIVOS ────────────────────────────────────────────────
        files_header = ctk.CTkFrame(self.root, fg_color="transparent")
        files_header.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 2))
        files_header.grid_columnconfigure(0, weight=1)
        self.files_title = ctk.CTkLabel(
            files_header, text="①  ARCHIVOS", anchor="w",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.files_title.grid(row=0, column=0, sticky="w")
        ctk.CTkButton(
            files_header, text="Nuevo desde plantilla…", width=160,
            fg_color="transparent", border_width=1,
            command=self._open_template_gallery,
        ).grid(row=0, column=1, sticky="e", padx=(8, 0))
        ctk.CTkButton(
            files_header, text="+ Agregar archivos", width=140,
            command=self._on_select_files,
        ).grid(row=0, column=2, sticky="e", padx=(8, 0))
        ctk.CTkButton(
            files_header, text="Vaciar", width=64,
            fg_color="transparent", border_width=1,
            command=self._on_clear_files,
        ).grid(row=0, column=3, sticky="e", padx=(8, 0))
        self.preview_btn = ctk.CTkButton(
            files_header, text="👁 Vista previa", width=120,
            fg_color="transparent", border_width=1,
            command=self._toggle_preview,
        )
        self.preview_btn.grid(row=0, column=4, sticky="e", padx=(8, 0))

        self.files_frame = ctk.CTkScrollableFrame(self.root, corner_radius=10)
        self.files_frame.grid(row=1, column=0, sticky="nsew", padx=16, pady=(2, 10))
        self.files_frame.grid_columnconfigure(0, weight=1)

        # Drop en toda la ventana; la lista se ilumina al arrastrar encima.
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind("<<Drop>>", self._on_drop)
        self.root.dnd_bind("<<DropEnter>>", lambda e: self._set_drop_highlight(True))
        self.root.dnd_bind("<<DropLeave>>", lambda e: self._set_drop_highlight(False))

        self._render_file_list()

        # ── ② OPCIONES ────────────────────────────────────────────────
        ctk.CTkLabel(
            self.root, text="②  OPCIONES", anchor="w",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=2, column=0, sticky="w", padx=16, pady=(4, 2))

        options = ctk.CTkFrame(self.root, corner_radius=10)
        options.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 10))
        options.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(options, text="Tema (Word y PDF):").grid(
            row=0, column=0, sticky="w", padx=(12, 8), pady=(10, 2)
        )
        theme_row = ctk.CTkFrame(options, fg_color="transparent")
        theme_row.grid(row=0, column=1, sticky="ew", pady=(10, 2))
        self.theme_menu = ctk.CTkOptionMenu(
            theme_row, variable=self.theme_name,
            values=available_themes() or ["professional"],
            command=self._on_theme_change, width=170,
        )
        self.theme_menu.pack(side="left")
        ctk.CTkButton(
            theme_row, text="🎨 Diseñador…", width=110,
            fg_color="transparent", border_width=1,
            command=self._open_designer,
        ).pack(side="left", padx=(8, 0))
        self.theme_desc = ctk.CTkLabel(
            options, text="", anchor="w", justify="left",
            font=ctk.CTkFont(size=11), text_color=("gray35", "gray65"),
        )
        self.theme_desc.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 4))
        self._on_theme_change(self.theme_name.get())

        # Motor de la vía PDF: temas HTML (navegador) o plantilla LaTeX
        ctk.CTkLabel(options, text="Motor PDF:").grid(
            row=2, column=0, sticky="w", padx=(12, 8), pady=2
        )
        engine_row = ctk.CTkFrame(options, fg_color="transparent")
        engine_row.grid(row=2, column=1, sticky="ew", pady=2)
        self.engine_selector = ctk.CTkSegmentedButton(
            engine_row, values=["Temas HTML", "Plantilla LaTeX"],
            command=self._on_engine_mode_change,
        )
        self.engine_selector.set("Temas HTML")
        self.engine_selector.pack(side="left")
        self.latex_status_label = ctk.CTkLabel(
            engine_row, text="", font=ctk.CTkFont(size=11),
            text_color=("gray35", "gray65"),
        )
        self.latex_status_label.pack(side="left", padx=(10, 0))
        self.tectonic_btn = ctk.CTkButton(
            engine_row, text="Descargar Tectonic (~30 MB)", width=190,
            fg_color="transparent", border_width=1,
            command=self._on_download_tectonic,
        )  # solo se muestra si no hay motor LaTeX

        # Fila LaTeX (visible solo en modo plantilla)
        self.latex_frame = ctk.CTkFrame(options, fg_color="transparent")
        self.latex_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self.latex_frame, text="Plantilla LaTeX:").grid(
            row=0, column=0, sticky="w", padx=(12, 8)
        )
        latex_row = ctk.CTkFrame(self.latex_frame, fg_color="transparent")
        latex_row.grid(row=0, column=1, sticky="ew")
        wrappers = available_latex_templates(kind="wrapper")
        self.latex_menu = ctk.CTkOptionMenu(
            latex_row, variable=self.latex_template,
            values=wrappers or ["(sin plantillas)"],
            command=self._on_latex_template_change, width=170,
        )
        self.latex_menu.pack(side="left")
        ctk.CTkLabel(latex_row, text="Autor:").pack(side="left", padx=(12, 4))
        ctk.CTkEntry(latex_row, textvariable=self.latex_author, width=150,
                     placeholder_text="para la portada").pack(side="left")
        ctk.CTkButton(
            latex_row, text="LaTeX avanzado…", width=120,
            fg_color="transparent", border_width=1,
            command=self._open_latex_advanced,
        ).pack(side="left", padx=(10, 0))
        self.latex_desc = ctk.CTkLabel(
            self.latex_frame, text="", anchor="w", justify="left",
            font=ctk.CTkFont(size=11), text_color=("gray35", "gray65"),
        )
        self.latex_desc.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12)
        self._on_latex_template_change(self.latex_template.get())

        ctk.CTkLabel(options, text="Carpeta de salida:").grid(
            row=4, column=0, sticky="w", padx=(12, 8), pady=2
        )
        out_row = ctk.CTkFrame(options, fg_color="transparent")
        out_row.grid(row=4, column=1, sticky="ew", pady=2)
        self.output_label = ctk.CTkLabel(
            out_row, text="Junto a cada archivo de entrada", anchor="w"
        )
        self.output_label.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(out_row, text="Cambiar…", width=90, command=self._on_select_output_dir).pack(
            side="right", padx=(8, 12)
        )

        self.merge_check = ctk.CTkCheckBox(
            options,
            text="Unir todo en UN solo documento (en el orden de la lista)",
            variable=self.merge_mode,
            command=self._schedule_preview,
        )
        self.merge_check.grid(row=5, column=0, columnspan=2, sticky="w", padx=12, pady=(6, 12))

        # ── ③ CONVERTIR ───────────────────────────────────────────────
        ctk.CTkLabel(
            self.root, text="③  CONVERTIR", anchor="w",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=4, column=0, sticky="w", padx=16, pady=(4, 2))

        convert_frame = ctk.CTkFrame(self.root, corner_radius=10)
        convert_frame.grid(row=5, column=0, sticky="nsew", padx=16, pady=(0, 14))
        convert_frame.grid_columnconfigure((0, 1), weight=1)
        convert_frame.grid_rowconfigure(2, weight=1)

        self.convert_docx_btn = ctk.CTkButton(
            convert_frame, text="Convertir a Word (.docx)", height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self._start_conversion("docx"),
        )
        self.convert_docx_btn.grid(row=0, column=0, sticky="ew", padx=(12, 6), pady=(12, 4))

        self.convert_pdf_btn = ctk.CTkButton(
            convert_frame, text="Convertir a PDF", height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self._start_conversion("pdf"),
        )
        self.convert_pdf_btn.grid(row=0, column=1, sticky="ew", padx=(6, 12), pady=(12, 4))

        self.progress_bar = ctk.CTkProgressBar(convert_frame, mode="indeterminate")

        self.log_box = ctk.CTkTextbox(convert_frame, wrap="word", height=120)
        self.log_box.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=12, pady=(6, 12))
        tb = self.log_box._textbox
        tb.tag_config("error", foreground="#F87171")
        tb.tag_config("ok", foreground="#4ADE80")
        self.log_box.configure(state="disabled")

        # ── Panel de VISTA PREVIA (columna derecha, colapsable) ────────
        self.preview_panel = ctk.CTkFrame(self.root, corner_radius=10, width=540)
        self.preview_panel.grid_propagate(False)
        self.preview_panel.grid_columnconfigure(0, weight=1)
        self.preview_panel.grid_rowconfigure(1, weight=1)

        pv_controls = ctk.CTkFrame(self.preview_panel, fg_color="transparent")
        pv_controls.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 4))
        ctk.CTkButton(pv_controls, text="◀", width=34,
                      command=lambda: self._preview_nav(-1)).pack(side="left")
        self.preview_page_label = ctk.CTkLabel(pv_controls, text="– / –", width=54)
        self.preview_page_label.pack(side="left", padx=4)
        ctk.CTkButton(pv_controls, text="▶", width=34,
                      command=lambda: self._preview_nav(+1)).pack(side="left")
        ctk.CTkButton(pv_controls, text="−", width=34,
                      command=lambda: self._preview_set_zoom(-0.2)).pack(side="left", padx=(14, 2))
        self.preview_zoom_label = ctk.CTkLabel(pv_controls, text="100 %", width=48)
        self.preview_zoom_label.pack(side="left")
        ctk.CTkButton(pv_controls, text="+", width=34,
                      command=lambda: self._preview_set_zoom(+0.2)).pack(side="left", padx=(2, 0))
        ctk.CTkButton(pv_controls, text="⟳ Actualizar", width=100,
                      command=lambda: self._schedule_preview(delay_ms=0)).pack(side="right")

        self.preview_image_label = ctk.CTkLabel(
            self.preview_panel, text="La vista previa aparecerá aquí\ncuando agregues un archivo.",
            justify="center", text_color=("gray45", "gray55"),
        )
        self.preview_image_label.grid(row=1, column=0, sticky="nsew", padx=10, pady=4)

        self.preview_status = ctk.CTkLabel(
            self.preview_panel, text="", anchor="w",
            font=ctk.CTkFont(size=11), text_color=("gray35", "gray65"),
        )
        self.preview_status.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 10))

    # ------------------------------------------------------- lista archivos

    def _render_file_list(self) -> None:
        for child in self.files_frame.winfo_children():
            child.destroy()

        count = len(self.selected_files)
        self.files_title.configure(text=f"①  ARCHIVOS ({count})" if count else "①  ARCHIVOS")

        if not self.selected_files:
            hint = ctk.CTkLabel(
                self.files_frame,
                text="Arrastra aquí archivos .md / .html / .tex\n"
                     "o usa «+ Agregar archivos» / «Nuevo desde plantilla…».\n\n"
                     "Los .tex se compilan con LaTeX (solo PDF).\n"
                     "Si vas a unir varios, ordénalos con ↑ ↓ —\n"
                     "se unen exactamente en el orden de esta lista.",
                justify="center", text_color=("gray45", "gray55"),
            )
            hint.grid(row=0, column=0, pady=28)
            self._schedule_preview()
            return

        self._schedule_preview()
        for i, path in enumerate(self.selected_files):
            row = ctk.CTkFrame(self.files_frame, fg_color="transparent")
            row.grid(row=i, column=0, sticky="ew", pady=1)
            row.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(row, text=f"{i + 1}.", width=28, anchor="e").grid(row=0, column=0, padx=(0, 6))
            ctk.CTkLabel(row, text=path.name, anchor="w").grid(row=0, column=1, sticky="ew")

            ctk.CTkButton(
                row, text="↑", width=30, fg_color="transparent", border_width=1,
                state="normal" if i > 0 else "disabled",
                command=lambda i=i: self._move_file(i, -1),
            ).grid(row=0, column=2, padx=2)
            ctk.CTkButton(
                row, text="↓", width=30, fg_color="transparent", border_width=1,
                state="normal" if i < count - 1 else "disabled",
                command=lambda i=i: self._move_file(i, +1),
            ).grid(row=0, column=3, padx=2)
            ctk.CTkButton(
                row, text="✕", width=30, fg_color="transparent", border_width=1,
                hover_color=("#fca5a5", "#7f1d1d"),
                command=lambda i=i: self._remove_file(i),
            ).grid(row=0, column=4, padx=(2, 6))

    def _move_file(self, index: int, delta: int) -> None:
        new_index = index + delta
        if 0 <= new_index < len(self.selected_files):
            files = self.selected_files
            files[index], files[new_index] = files[new_index], files[index]
            self._render_file_list()

    def _remove_file(self, index: int) -> None:
        del self.selected_files[index]
        self._render_file_list()

    def _on_clear_files(self) -> None:
        self.selected_files.clear()
        self._render_file_list()

    def _add_files(self, paths: list[Path]) -> None:
        valid = [p for p in paths if p.suffix.lower() in GUI_EXTENSIONS]
        invalid = [p for p in paths if p.suffix.lower() not in GUI_EXTENSIONS]
        if invalid:
            self._append_log(
                "Ignorados (no son .md/.markdown/.html/.htm/.tex): "
                + ", ".join(p.name for p in invalid),
                tag="error",
            )
        added = 0
        for p in valid:
            resolved = p.resolve()
            if resolved not in self.selected_files:
                self.selected_files.append(resolved)
                added += 1
        if added:
            self._render_file_list()

    def _set_drop_highlight(self, active: bool) -> None:
        self.files_frame.configure(
            border_width=2 if active else 0,
            border_color=ACCENT,
        )

    def _on_drop(self, event) -> None:
        self._set_drop_highlight(False)
        raw_paths = self.root.tk.splitlist(event.data)
        self._add_files([Path(p) for p in raw_paths])

    def _on_select_files(self) -> None:
        patterns = " ".join(f"*{e}" for e in sorted(GUI_EXTENSIONS))
        paths = filedialog.askopenfilenames(
            title="Selecciona archivos Markdown, HTML o LaTeX",
            filetypes=[("Markdown/HTML/LaTeX", patterns), ("Todos los archivos", "*.*")],
        )
        if paths:
            self._add_files([Path(p) for p in paths])

    # ------------------------------------------------------------ opciones

    def _on_theme_change(self, name: str) -> None:
        try:
            meta = get_theme_metadata(name)
            self.theme_desc.configure(text=meta.description or "")
        except Exception:
            self.theme_desc.configure(text="")
        self._schedule_preview()

    def _on_engine_mode_change(self, label: str) -> None:
        mode = "latex" if label == "Plantilla LaTeX" else "html"
        self.pdf_engine_mode.set(mode)
        if mode == "latex":
            self.latex_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=2)
        else:
            self.latex_frame.grid_remove()
        self._schedule_preview()

    def _on_latex_template_change(self, template_id: str) -> None:
        try:
            meta = get_latex_template_meta(template_id)
            self.latex_desc.configure(text=meta.get("description", ""))
        except Exception:
            self.latex_desc.configure(text="")
        self._schedule_preview()

    def _on_select_output_dir(self) -> None:
        directory = filedialog.askdirectory(title="Selecciona la carpeta de salida")
        if directory:
            self.output_dir = Path(directory)
            self.output_label.configure(text=str(self.output_dir))

    # ----------------------------------------------------------- conversión

    def _check_browser(self) -> None:
        try:
            find_browser()
        except BrowserNotFoundError as exc:
            self._append_log(f"⚠ {exc}", tag="error")
            self._browser_missing = True
        else:
            self._browser_missing = False

    def _check_latex(self) -> None:
        try:
            self.latex_engine = find_latex_engine()
        except LatexNotFoundError:
            self.latex_engine = None
            self.latex_status_label.configure(text="Sin motor LaTeX")
            self.tectonic_btn.pack(side="left", padx=(10, 0))
        else:
            origin = "MiKTeX" if self.latex_engine.is_miktex else self.latex_engine.name
            self.latex_status_label.configure(
                text=f"Motor: {self.latex_engine.name} ({origin}) ✓"
            )
            self.tectonic_btn.pack_forget()

    def _update_pdf_button(self) -> None:
        if self._browser_missing and self.latex_engine is None:
            self.convert_pdf_btn.configure(
                state="disabled", text="PDF no disponible (sin navegador ni LaTeX)"
            )
        else:
            self.convert_pdf_btn.configure(state="normal", text="Convertir a PDF")

    def _on_download_tectonic(self) -> None:
        self.tectonic_btn.configure(state="disabled", text="Descargando…")
        self._append_log("Descargando Tectonic desde GitHub (~30 MB)…")

        def worker() -> None:
            reported: set[int] = set()

            def progress(done: int, total: int) -> None:
                if total <= 0:
                    return
                pct = int(done * 100 / total)
                for mark in (25, 50, 75, 100):
                    if pct >= mark and mark not in reported:
                        reported.add(mark)
                        self.event_queue.put(("log", f"  Tectonic: {mark}% descargado"))

            try:
                path = download_tectonic(progress)
                self.event_queue.put(("done", f"✔ Tectonic instalado en {path}"))
            except Exception as exc:
                self.event_queue.put(("error", f"✖ No se pudo descargar Tectonic: {exc}"))
            self.event_queue.put(("call", self._after_tectonic_download))

        threading.Thread(target=worker, daemon=True).start()

    def _after_tectonic_download(self) -> None:
        self.tectonic_btn.configure(state="normal", text="Descargar Tectonic (~30 MB)")
        self._check_latex()
        self._update_pdf_button()

    def _gather_options(self, fmt: str) -> dict:
        """Captura las opciones en el hilo de UI para pasarlas al worker."""
        return {
            "fmt": fmt,
            "merge": self.merge_mode.get(),
            "theme": self.theme_name.get(),
            "pdf_mode": self.pdf_engine_mode.get(),
            "template": self.latex_template.get(),
            "author": self.latex_author.get(),
            "preamble": self.latex_preamble,
            "output_dir": self.output_dir,
        }

    def _start_conversion(self, fmt: str) -> None:
        if self._busy:
            return
        if not self.selected_files:
            messagebox.showwarning(
                "Sin archivos",
                "Agrega al menos un archivo .md, .html o .tex antes de convertir.",
            )
            return
        files = list(self.selected_files)  # el orden visible ES el orden de unión
        tex_files = [f for f in files if f.suffix.lower() == TEX_EXTENSION]

        if fmt == "docx" and tex_files and len(tex_files) == len(files):
            messagebox.showwarning(
                "LaTeX → Word no soportado",
                "Los archivos .tex solo pueden exportarse a PDF.\n"
                "Usa el botón «Convertir a PDF».",
            )
            return
        if self.merge_mode.get() and len(files) < 2:
            messagebox.showwarning(
                "Unir documentos",
                "Solo agregaste 1 archivo y está activado «Unir todo en un solo "
                "documento».\n\nAgrega más archivos para unirlos, o desmarca la "
                "casilla para convertir este archivo individualmente.",
            )
            return
        if fmt == "pdf":
            needs_latex = bool(tex_files) or self.pdf_engine_mode.get() == "latex"
            if needs_latex and self.latex_engine is None:
                self._append_log(
                    "No hay motor LaTeX. Usa «Descargar Tectonic» (en Opciones → "
                    "Motor PDF) o instala MiKTeX.", tag="error",
                )
                return
            if not needs_latex and self._browser_missing:
                self._append_log(
                    "No hay navegador Chromium para los temas HTML. Cambia el "
                    "Motor PDF a «Plantilla LaTeX» o instala Edge/Chrome.", tag="error",
                )
                return

        self._set_busy(True)
        opts = self._gather_options(fmt)
        threading.Thread(target=self._convert_worker, args=(files, opts), daemon=True).start()

    def _convert_worker(self, files: list[Path], opts: dict) -> None:
        try:
            if opts["merge"]:
                self._convert_merged(files, opts)
            else:
                self._convert_separate(files, opts)
        except Exception as exc:
            self.event_queue.put(("error", f"Error general: {exc}"))
        self.event_queue.put(("finished", None))

    def _pdf_for_source(self, source: Path, output_path: Path | None, opts: dict) -> Path:
        """Convierte UN archivo a PDF según su tipo y el motor elegido."""
        suffix = source.suffix.lower()
        if suffix == TEX_EXTENSION:
            return compile_tex(source, output_path, engine=self.latex_engine)
        if opts["pdf_mode"] == "latex":
            if suffix in {".html", ".htm"}:
                raise ValueError(
                    "la vía LaTeX solo acepta Markdown; cambia el Motor PDF a "
                    "«Temas HTML» para este archivo."
                )
            return convert_markdown_via_latex(
                [source], output_path,
                template=opts["template"], author=opts["author"],
                preamble_extra=opts["preamble"], engine=self.latex_engine,
            )
        return MarkdownToPdfConverter(theme=opts["theme"]).convert(
            source, output_path
        ).output_path

    def _convert_separate(self, files: list[Path], opts: dict) -> None:
        fmt = opts["fmt"]
        for source in files:
            try:
                output_path = None
                if opts["output_dir"] is not None:
                    output_path = opts["output_dir"] / source.with_suffix(f".{fmt}").name
                if fmt == "docx":
                    if source.suffix.lower() == TEX_EXTENSION:
                        self.event_queue.put(
                            ("log", f"↷ '{source.name}' omitido en Word (los .tex solo van a PDF).")
                        )
                        continue
                    result = convert_source_file(source, output_path, theme_path=opts["theme"])
                else:
                    result = self._pdf_for_source(source, output_path, opts)
                self.event_queue.put(("done", f"✔ Creado: {result}"))
            except Exception as exc:
                self.event_queue.put(("error", f"✖ Error con '{source.name}': {exc}"))

    def _convert_merged(self, files: list[Path], opts: dict) -> None:
        fmt = opts["fmt"]
        out_dir = opts["output_dir"] if opts["output_dir"] is not None else files[0].parent
        out_dir.mkdir(parents=True, exist_ok=True)
        output = out_dir / f"{files[0].stem}_unido.{fmt}"
        try:
            tex_files = [f for f in files if f.suffix.lower() == TEX_EXTENSION]
            if fmt == "docx":
                usable = [f for f in files if f.suffix.lower() != TEX_EXTENSION]
                if tex_files:
                    self.event_queue.put(
                        ("log", "↷ Omitidos en Word (solo van a PDF): "
                         + ", ".join(t.name for t in tex_files))
                    )
                if not usable:
                    raise ValueError("no queda ningún archivo .md/.html que unir.")
                result = convert_merged_from_patterns(
                    [str(p) for p in usable], output, theme_path=opts["theme"]
                )
            else:
                if tex_files:
                    raise ValueError(
                        "los .tex no se pueden unir (cada .tex es un documento "
                        "completo); conviértelos por separado."
                    )
                if opts["pdf_mode"] == "latex":
                    result = convert_markdown_via_latex(
                        files, output,
                        template=opts["template"], author=opts["author"],
                        preamble_extra=opts["preamble"], engine=self.latex_engine,
                    )
                else:
                    result = MarkdownToPdfConverter(theme=opts["theme"]).convert_many(
                        files, output
                    ).output_path
            self.event_queue.put(
                ("done", f"✔ Documento unificado ({len(files)} archivos): {result}")
            )
        except Exception as exc:
            self.event_queue.put(("error", f"✖ Error al unir: {exc}"))

    # -------------------------------------------------------- vista previa

    def _toggle_preview(self) -> None:
        self.preview_visible = not self.preview_visible
        width_delta = 556
        geo = self.root.geometry()  # "WxH+X+Y"
        size, _, rest = geo.partition("+")
        w, h = (int(v) for v in size.split("x"))
        try:
            scaling = ctk.ScalingTracker.get_window_scaling(self.root)
        except Exception:
            scaling = 1.0
        screen_w = int(self.root.winfo_screenwidth() / max(scaling, 0.5))
        parts = rest.split("+") if rest else []
        x = int(parts[0]) if parts else 40
        y = parts[1] if len(parts) > 1 else "40"

        if self.preview_visible:
            self._pre_preview_width = w
            new_w = min(w + width_delta, screen_w - 24)
            # en pantallas pequeñas el panel cede ancho para no aplastar la columna principal
            panel_w = max(380, min(540, new_w - 660))
            self.preview_panel.configure(width=panel_w)
            self.preview_panel.grid(row=0, column=1, rowspan=6, sticky="nsew",
                                    padx=(0, 16), pady=14)
            self.preview_btn.configure(fg_color=ACCENT, text_color="white")
            new_x = max(0, min(x, screen_w - new_w - 12))
            self.root.geometry(f"{new_w}x{h}+{new_x}+{y}")
            self._schedule_preview(delay_ms=0)
        else:
            self.preview_panel.grid_remove()
            self.preview_btn.configure(fg_color="transparent",
                                       text_color=("gray10", "gray90"))
            restored = getattr(self, "_pre_preview_width", None) or max(680, w - width_delta)
            self.root.geometry(f"{restored}x{h}+{x}+{y}")

    def _schedule_preview(self, delay_ms: int = 450) -> None:
        if not self.preview_visible:
            return
        if self._preview_after_id is not None:
            self.root.after_cancel(self._preview_after_id)
        self._preview_after_id = self.root.after(delay_ms, self._start_preview_render)

    def _start_preview_render(self) -> None:
        self._preview_after_id = None
        if not self.selected_files:
            self._preview_images = []
            self._preview_ctk_image = None
            # image="" (no None): None deja la imagen anterior pegada en CTkLabel
            self.preview_image_label.configure(
                image="", text="La vista previa aparecerá aquí\ncuando agregues un archivo."
            )
            self.preview_page_label.configure(text="– / –")
            self.preview_status.configure(text="")
            return
        self._preview_gen += 1
        gen = self._preview_gen
        targets = list(self.selected_files) if self.merge_mode.get() else [self.selected_files[0]]
        opts = self._gather_options("pdf")
        self.preview_status.configure(text="Generando vista previa…")
        threading.Thread(
            target=self._preview_worker, args=(gen, targets, opts), daemon=True
        ).start()

    def _preview_worker(self, gen: int, targets: list[Path], opts: dict) -> None:
        try:
            with tempfile.TemporaryDirectory(prefix="markitdocs_prev_", ignore_cleanup_errors=True) as tmp:
                pdf_path = Path(tmp) / "preview.pdf"
                first = targets[0]
                if first.suffix.lower() == TEX_EXTENSION:
                    compile_tex(first, pdf_path, engine=self.latex_engine)
                elif opts["pdf_mode"] == "latex":
                    convert_markdown_via_latex(
                        targets, pdf_path,
                        template=opts["template"], author=opts["author"],
                        preamble_extra=opts["preamble"], engine=self.latex_engine,
                    )
                else:
                    MarkdownToPdfConverter(theme=opts["theme"]).convert_many(targets, pdf_path)
                images = pdf_to_images(pdf_path, scale=1.5, max_pages=40)
            self.event_queue.put(("preview", (gen, images)))
        except Exception as exc:
            self.event_queue.put(("preview_error", (gen, str(exc))))

    def _apply_preview(self, gen: int, images: list) -> None:
        if gen != self._preview_gen:
            return  # llegó un render obsoleto; ya hay otro en camino
        self._preview_images = images
        self._preview_page = min(self._preview_page, max(0, len(images) - 1))
        self.preview_status.configure(text=f"{len(images)} página(s) · vista del PDF real")
        self._show_preview_page()

    def _apply_preview_error(self, gen: int, message: str) -> None:
        if gen != self._preview_gen:
            return
        self.preview_status.configure(text=f"✖ {message[:220]}")

    def _show_preview_page(self) -> None:
        if not self._preview_images:
            return
        total = len(self._preview_images)
        self._preview_page = max(0, min(self._preview_page, total - 1))
        img = self._preview_images[self._preview_page]
        panel_h = max(420, self.preview_panel.winfo_height() - 110)
        display_h = int(panel_h * self._preview_zoom)
        display_w = int(display_h * img.width / img.height)
        self._preview_ctk_image = ctk.CTkImage(
            light_image=img, dark_image=img, size=(display_w, display_h)
        )
        self.preview_image_label.configure(image=self._preview_ctk_image, text="")
        self.preview_page_label.configure(text=f"{self._preview_page + 1} / {total}")
        self.preview_zoom_label.configure(text=f"{int(self._preview_zoom * 100)} %")

    def _preview_nav(self, delta: int) -> None:
        if self._preview_images:
            self._preview_page += delta
            self._show_preview_page()

    def _preview_set_zoom(self, delta: float) -> None:
        self._preview_zoom = max(0.6, min(2.2, round(self._preview_zoom + delta, 1)))
        self._show_preview_page()

    # ------------------------------------------------ plantillas y diseñador

    def _open_template_gallery(self) -> None:
        win = ctk.CTkToplevel(self.root)
        win.title("Plantillas LaTeX — comunidad")
        win.geometry("780x640")
        win.transient(self.root)
        win.grid_columnconfigure(0, weight=1)
        win.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            win, text="Elige una plantilla: los «documentos editables» se crean como .tex "
                      "para rellenar;\nlas plantillas «para tus .md» envuelven tu Markdown al exportar a PDF.",
            justify="left",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 6))

        scroll = ctk.CTkScrollableFrame(win)
        scroll.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        scroll.grid_columnconfigure(0, weight=1)

        for i, tid in enumerate(available_latex_templates()):
            meta = get_latex_template_meta(tid)
            is_wrapper = meta.get("kind") == "wrapper"
            card = ctk.CTkFrame(scroll, corner_radius=8)
            card.grid(row=i, column=0, sticky="ew", pady=4, padx=4)
            card.grid_columnconfigure(0, weight=1)

            badge = "PARA TUS .MD" if is_wrapper else "DOCUMENTO EDITABLE"
            ctk.CTkLabel(
                card, text=f"{meta.get('name', tid)}   ·   {badge}",
                font=ctk.CTkFont(size=13, weight="bold"), anchor="w",
            ).grid(row=0, column=0, sticky="w", padx=12, pady=(8, 0))
            ctk.CTkLabel(
                card, text=meta.get("description", ""), anchor="w", justify="left",
                wraplength=520, font=ctk.CTkFont(size=11),
                text_color=("gray30", "gray70"),
            ).grid(row=1, column=0, sticky="w", padx=12, pady=(0, 8))

            if is_wrapper:
                ctk.CTkButton(
                    card, text="Usar con mis .md", width=150,
                    command=lambda t=tid, w=win: self._use_wrapper_template(t, w),
                ).grid(row=0, column=1, rowspan=2, padx=12)
            else:
                ctk.CTkButton(
                    card, text="Crear documento…", width=150,
                    command=lambda t=tid: self._create_from_starter(t),
                ).grid(row=0, column=1, rowspan=2, padx=12)

    def _use_wrapper_template(self, template_id: str, window) -> None:
        self.latex_template.set(template_id)
        self.engine_selector.set("Plantilla LaTeX")
        self._on_engine_mode_change("Plantilla LaTeX")
        self._on_latex_template_change(template_id)
        self._append_log(
            f"Plantilla LaTeX «{template_id}» seleccionada: tus .md se exportarán "
            "a PDF con ella.", tag="ok",
        )
        window.destroy()

    def _create_from_starter(self, template_id: str) -> None:
        target = filedialog.asksaveasfilename(
            title="Dónde crear tu documento LaTeX",
            initialfile=f"{template_id}.tex",
            defaultextension=".tex",
            filetypes=[("LaTeX", "*.tex")],
        )
        if not target:
            return
        target_path = Path(target)
        try:
            if target_path.exists():
                target_path.unlink()  # el diálogo ya pidió confirmación de sobrescritura
            created = instantiate_starter(template_id, target_path.parent, target_path.name)
        except Exception as exc:
            messagebox.showerror("Plantilla", f"No se pudo crear el documento: {exc}")
            return
        self._add_files([created])
        self._append_log(
            f"✔ Documento creado desde plantilla: {created}\n"
            "  Edítalo con tus datos y usa «Convertir a PDF».", tag="ok",
        )

    def _open_latex_advanced(self) -> None:
        win = ctk.CTkToplevel(self.root)
        win.title("LaTeX avanzado — preámbulo personalizado")
        win.geometry("640x460")
        win.transient(self.root)
        win.grid_columnconfigure(0, weight=1)
        win.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            win, justify="left", anchor="w",
            text="Este código LaTeX se inyecta en el preámbulo de la plantilla "
                 "(personalización infinita):\nfuentes (fontspec), colores (xcolor), "
                 "márgenes (geometry), paquetes extra…",
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 4))

        box = ctk.CTkTextbox(win, wrap="none", font=ctk.CTkFont(family="Consolas", size=12))
        box.grid(row=1, column=0, sticky="nsew", padx=14, pady=4)
        box.insert("1.0", self.latex_preamble)

        def save() -> None:
            self.latex_preamble = box.get("1.0", "end-1c")
            self._append_log("Preámbulo LaTeX actualizado.", tag="ok")
            self._schedule_preview()
            win.destroy()

        buttons = ctk.CTkFrame(win, fg_color="transparent")
        buttons.grid(row=2, column=0, sticky="e", padx=14, pady=(4, 12))
        ctk.CTkButton(buttons, text="Cancelar", width=100, fg_color="transparent",
                      border_width=1, command=win.destroy).pack(side="left", padx=(0, 8))
        ctk.CTkButton(buttons, text="Guardar", width=100, command=save).pack(side="left")

    def _open_designer(self) -> None:
        DesignerWindow(
            self.root,
            base_theme=self.theme_name.get(),
            on_saved=self._on_designer_saved,
        )

    def _on_designer_saved(self, theme_id: str, latex_preamble: str) -> None:
        self.theme_menu.configure(values=available_themes() or ["professional"])
        self.theme_name.set(theme_id)
        self._on_theme_change(theme_id)
        if latex_preamble.strip():
            self.latex_preamble = latex_preamble
        self._append_log(f"✔ Tema personalizado «{theme_id}» guardado y seleccionado.", tag="ok")
        self._schedule_preview()

    # ------------------------------------------------------------- soporte

    def _attach_logging(self) -> None:
        handler = QueueLogHandler(self.event_queue)
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        logging.getLogger("crear_documento").addHandler(handler)
        logging.getLogger("markitpdf").addHandler(handler)

    def _append_log(self, text: str, tag: str | None = None) -> None:
        self.log_box.configure(state="normal")
        if tag:
            self.log_box._textbox.insert("end", text + "\n", tag)
        else:
            self.log_box.insert("end", text + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.convert_docx_btn.configure(state="disabled" if busy else "normal")
        if busy:
            self.convert_pdf_btn.configure(state="disabled")
        else:
            self._update_pdf_button()
        if busy:
            self.progress_bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(2, 2))
            self.progress_bar.start()
        else:
            self.progress_bar.stop()
            self.progress_bar.grid_forget()

    def _drain_queue(self) -> None:
        try:
            while True:
                kind, payload = self.event_queue.get_nowait()
                if kind == "finished":
                    self._set_busy(False)
                elif kind == "done":
                    self._append_log(payload, tag="ok")
                elif kind == "error":
                    self._append_log(payload, tag="error")
                elif kind == "preview":
                    self._apply_preview(*payload)
                elif kind == "preview_error":
                    self._apply_preview_error(*payload)
                elif kind == "call":
                    payload()
                else:
                    self._append_log(payload)
        except queue.Empty:
            pass
        self.root.after(100, self._drain_queue)

    def run(self) -> None:
        self.root.mainloop()


def _selftest() -> int:
    """Autodiagnóstico del ejecutable: `MarkItDocs.exe --selftest`.

    Escribe selftest_log.txt junto al exe con el resultado de cada subsistema,
    para diagnosticar problemas que solo aparecen en el binario congelado.
    """
    import tempfile as _tf
    import traceback

    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
    log_path = base / "selftest_log.txt"
    lines: list[str] = [
        f"MarkItDocs selftest — frozen={getattr(sys, 'frozen', False)} python={sys.version}",
    ]

    def check(name, fn):
        try:
            result = fn()
            lines.append(f"OK    {name}: {result}")
        except Exception:
            lines.append(f"FALLO {name}:\n{traceback.format_exc()}")

    check("temas", lambda: f"{len(available_themes())} temas")
    check("plantillas latex", lambda: f"{len(available_latex_templates())} plantillas")
    check("navegador", find_browser)
    check("motor latex", lambda: find_latex_engine().path)

    with _tf.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        md = Path(tmp) / "t.md"
        md.write_text("# Selftest\n\n| A |\n| --- |\n| 1 |\n", encoding="utf-8")

        def html_pdf():
            out = MarkdownToPdfConverter(theme="professional").convert(md, Path(tmp) / "h.pdf")
            return f"{out.output_path.stat().st_size} bytes"

        def latex_pdf():
            out = convert_markdown_via_latex([md], Path(tmp) / "l.pdf", template="informe-clasico")
            return f"{out.stat().st_size} bytes"

        def preview_images():
            pdf = Path(tmp) / "h.pdf"
            if not pdf.exists():
                MarkdownToPdfConverter(theme="professional").convert(md, pdf)
            images = pdf_to_images(pdf, scale=1.0, max_pages=1)
            return f"{len(images)} imagen(es) {images[0].size}"

        check("md->pdf (temas HTML)", html_pdf)
        check("md->pdf (via LaTeX)", latex_pdf)

        def latex_currency():
            m = Path(tmp) / "moneda.md"
            m.write_text(
                "# Finanzas\n\n*Base: $ 3,760 con +15% y CV $237.*\n\n"
                "* 50% Landing ($350, CV $237) -> $113\n",
                encoding="utf-8",
            )
            out = convert_markdown_via_latex([m], Path(tmp) / "moneda.pdf",
                                             template="informe-clasico")
            return f"{out.stat().st_size} bytes"

        def chromium_parallel():
            import threading as _th
            results: dict = {}

            def render(i: int) -> None:
                m = Path(tmp) / f"par{i}.md"
                m.write_text(f"# Documento paralelo {i}\n\nContenido.\n", encoding="utf-8")
                try:
                    MarkdownToPdfConverter(theme="professional").convert(
                        m, Path(tmp) / f"par{i}.pdf"
                    )
                    results[i] = (Path(tmp) / f"par{i}.pdf").stat().st_size
                except Exception as exc:  # noqa: BLE001
                    results[i] = f"ERR {exc}"

            threads = [_th.Thread(target=render, args=(i,)) for i in (1, 2)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            assert all(isinstance(v, int) and v > 0 for v in results.values()), results
            return f"2 PDFs simultaneos OK {sorted(results.values())}"

        check("md->pdf (LaTeX con moneda y %)", latex_currency)
        check("chromium x2 en paralelo (preview+convertir)", chromium_parallel)
        check("pdf->imagenes (preview)", preview_images)

    def designer_pieces():
        from markitpdf.themebuilder import DEFAULT_MODEL, build_css
        css = build_css(DEFAULT_MODEL)
        import designer as _d  # el módulo del Diseñador importa dentro del exe
        return f"css {len(css)} chars, DesignerWindow={_d.DesignerWindow.__name__}"

    check("disenador (css+modulo)", designer_pieces)

    report = "\n".join(lines)
    log_path.write_text(report, encoding="utf-8")
    print(report)
    return 0 if "FALLO" not in report else 1


def main() -> None:
    if "--selftest" in sys.argv:
        raise SystemExit(_selftest())
    App().run()


if __name__ == "__main__":
    main()

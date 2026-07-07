"""MarkItDocs — GUI de escritorio para convertir Markdown/HTML a Word/PDF.

Secciones: ① Archivos (lista reordenable) → ② Opciones (tema único, salida,
unir) → ③ Convertir (Word/PDF, progreso, registro con colores).
El orden visible de la lista es el orden en que se unen los documentos.
"""

import logging
import queue
import sys
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
    MarkdownToPdfConverter,
    available_themes,
    find_browser,
    get_theme_metadata,
)

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

        self._build_layout()
        self._attach_logging()
        self.root.after(100, self._drain_queue)
        self._check_browser()

    # ------------------------------------------------------------------ UI

    def _build_layout(self) -> None:
        self.root.grid_columnconfigure(0, weight=1)
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
            files_header, text="+ Agregar archivos", width=150,
            command=self._on_select_files,
        ).grid(row=0, column=1, sticky="e", padx=(8, 0))
        ctk.CTkButton(
            files_header, text="Vaciar", width=70,
            fg_color="transparent", border_width=1,
            command=self._on_clear_files,
        ).grid(row=0, column=2, sticky="e", padx=(8, 0))

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
        self.theme_desc = ctk.CTkLabel(
            options, text="", anchor="w", justify="left",
            font=ctk.CTkFont(size=11), text_color=("gray35", "gray65"),
        )
        self.theme_desc.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 4))
        self._on_theme_change(self.theme_name.get())

        ctk.CTkLabel(options, text="Carpeta de salida:").grid(
            row=2, column=0, sticky="w", padx=(12, 8), pady=2
        )
        out_row = ctk.CTkFrame(options, fg_color="transparent")
        out_row.grid(row=2, column=1, sticky="ew", pady=2)
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
        )
        self.merge_check.grid(row=3, column=0, columnspan=2, sticky="w", padx=12, pady=(6, 12))

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

    # ------------------------------------------------------- lista archivos

    def _render_file_list(self) -> None:
        for child in self.files_frame.winfo_children():
            child.destroy()

        count = len(self.selected_files)
        self.files_title.configure(text=f"①  ARCHIVOS ({count})" if count else "①  ARCHIVOS")

        if not self.selected_files:
            hint = ctk.CTkLabel(
                self.files_frame,
                text="Arrastra aquí archivos .md / .markdown / .html / .htm\n"
                     "o usa el botón «+ Agregar archivos».\n\n"
                     "Si vas a unirlos en un solo documento, ordénalos con ↑ ↓ —\n"
                     "se unen exactamente en el orden de esta lista.",
                justify="center", text_color=("gray45", "gray55"),
            )
            hint.grid(row=0, column=0, pady=28)
            return

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
        valid = [p for p in paths if p.suffix.lower() in SUPPORTED_EXTENSIONS]
        invalid = [p for p in paths if p.suffix.lower() not in SUPPORTED_EXTENSIONS]
        if invalid:
            self._append_log(
                "Ignorados (no son .md/.markdown/.html/.htm): "
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
        patterns = " ".join(f"*{e}" for e in sorted(SUPPORTED_EXTENSIONS))
        paths = filedialog.askopenfilenames(
            title="Selecciona archivos Markdown o HTML",
            filetypes=[("Markdown/HTML", patterns), ("Todos los archivos", "*.*")],
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
            self.convert_pdf_btn.configure(state="disabled", text="PDF no disponible (sin navegador)")
            self._browser_missing = True
        else:
            self._browser_missing = False

    def _start_conversion(self, fmt: str) -> None:
        if self._busy:
            return
        if not self.selected_files:
            messagebox.showwarning(
                "Sin archivos",
                "Agrega al menos un archivo .md o .html antes de convertir.",
            )
            return
        if self.merge_mode.get() and len(self.selected_files) < 2:
            messagebox.showwarning(
                "Unir documentos",
                "Solo agregaste 1 archivo y está activado «Unir todo en un solo "
                "documento».\n\nAgrega más archivos para unirlos, o desmarca la "
                "casilla para convertir este archivo individualmente.",
            )
            self._append_log(
                "Modo unir: agrega más archivos (solo hay 1) o desmarca «Unir».",
                tag="error",
            )
            return
        if fmt == "pdf" and self._browser_missing:
            self._append_log("No se puede exportar a PDF: no hay navegador Chromium.", tag="error")
            return

        self._set_busy(True)
        files = list(self.selected_files)  # el orden visible ES el orden de unión
        threading.Thread(target=self._convert_worker, args=(files, fmt), daemon=True).start()

    def _convert_worker(self, files: list[Path], fmt: str) -> None:
        theme = self.theme_name.get()
        try:
            if self.merge_mode.get():
                self._convert_merged(files, fmt, theme)
            else:
                self._convert_separate(files, fmt, theme)
        except Exception as exc:
            self.event_queue.put(("error", f"Error general: {exc}"))
        self.event_queue.put(("finished", None))

    def _convert_separate(self, files: list[Path], fmt: str, theme: str) -> None:
        for source in files:
            try:
                output_path = None
                if self.output_dir is not None:
                    output_path = self.output_dir / source.with_suffix(f".{fmt}").name
                if fmt == "docx":
                    result = convert_source_file(source, output_path, theme_path=theme)
                else:
                    result = MarkdownToPdfConverter(theme=theme).convert(
                        source, output_path
                    ).output_path
                self.event_queue.put(("done", f"✔ Creado: {result}"))
            except Exception as exc:
                self.event_queue.put(("error", f"✖ Error con '{source.name}': {exc}"))

    def _convert_merged(self, files: list[Path], fmt: str, theme: str) -> None:
        out_dir = self.output_dir if self.output_dir is not None else files[0].parent
        out_dir.mkdir(parents=True, exist_ok=True)
        output = out_dir / f"{files[0].stem}_unido.{fmt}"
        try:
            if fmt == "docx":
                result = convert_merged_from_patterns(
                    [str(p) for p in files], output, theme_path=theme
                )
            else:
                result = MarkdownToPdfConverter(theme=theme).convert_many(
                    files, output
                ).output_path
            self.event_queue.put(
                ("done", f"✔ Documento unificado ({len(files)} archivos): {result}")
            )
        except Exception as exc:
            self.event_queue.put(("error", f"✖ Error al unir: {exc}"))

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
        state = "disabled" if busy else "normal"
        self.convert_docx_btn.configure(state=state)
        if self._browser_missing:
            self.convert_pdf_btn.configure(state="disabled")
        else:
            self.convert_pdf_btn.configure(state=state)
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
                else:
                    self._append_log(payload)
        except queue.Empty:
            pass
        self.root.after(100, self._drain_queue)

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    App().run()


if __name__ == "__main__":
    main()

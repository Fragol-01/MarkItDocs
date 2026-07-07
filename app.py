"""GUI de escritorio para convertir Markdown/HTML a Word/PDF, con drag-and-drop real."""

import logging
import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
from tkinterdnd2 import DND_FILES, TkinterDnD

sys.path.insert(0, str(Path(__file__).resolve().parent))

from crear_documento import (  # noqa: E402
    MARKDOWN_EXTENSIONS,
    HTML_EXTENSIONS,
    SUPPORTED_EXTENSIONS,
    convert_many,
    convert_merged_from_patterns,
    convert_source_file,
    load_theme,
)
from markitpdf import (  # noqa: E402
    BrowserNotFoundError,
    MarkdownToPdfConverter,
    available_themes,
    find_browser,
)

ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")

WINDOW_TITLE = "MD/HTML → DOCX / PDF"
WINDOW_SIZE = "820x640"


class QueueLogHandler(logging.Handler):
    """Reenvía registros de logging a una cola thread-safe para mostrarlos en la GUI."""

    def __init__(self, log_queue: queue.Queue) -> None:
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record: logging.LogRecord) -> None:
        self.log_queue.put(("log", self.format(record)))


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
        self.root.minsize(640, 480)

        self.event_queue: queue.Queue = queue.Queue()
        self.selected_files: list[Path] = []
        self.output_dir: Path | None = None
        self.theme_path: Path | None = None
        self.markitpdf_theme = ctk.StringVar(value="professional")
        self.merge_mode = ctk.BooleanVar(value=False)

        self._build_layout()
        self._attach_logging()
        self.root.after(100, self._drain_queue)
        self._check_browser()

    def _build_layout(self) -> None:
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(4, weight=1)

        drop_zone = ctk.CTkLabel(
            self.root,
            text="Arrastra archivos .md / .markdown / .html / .htm aquí\n(o usa el botón Seleccionar)",
            height=100,
            fg_color=("gray85", "gray20"),
            corner_radius=10,
        )
        drop_zone.grid(row=0, column=0, columnspan=4, sticky="ew", padx=16, pady=(16, 8))
        drop_zone.drop_target_register(DND_FILES)
        drop_zone.dnd_bind("<<Drop>>", self._on_drop)
        self.drop_zone = drop_zone

        controls = ctk.CTkFrame(self.root, fg_color="transparent")
        controls.grid(row=1, column=0, columnspan=4, sticky="ew", padx=16, pady=4)
        controls.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(controls, text="Seleccionar archivo(s)", command=self._on_select_files).grid(
            row=0, column=0, padx=(0, 8), pady=4
        )
        self.files_label = ctk.CTkLabel(controls, text="Ningún archivo seleccionado", anchor="w")
        self.files_label.grid(row=0, column=1, sticky="ew", pady=4)

        ctk.CTkButton(controls, text="Carpeta de salida", command=self._on_select_output_dir).grid(
            row=1, column=0, padx=(0, 8), pady=4
        )
        self.output_label = ctk.CTkLabel(controls, text="Misma carpeta que los archivos de entrada", anchor="w")
        self.output_label.grid(row=1, column=1, sticky="ew", pady=4)

        ctk.CTkButton(controls, text="Tema DOCX (.json/.yaml/.toml)", command=self._on_select_theme).grid(
            row=2, column=0, padx=(0, 8), pady=4
        )
        self.theme_label = ctk.CTkLabel(controls, text="Tema DOCX por defecto", anchor="w")
        self.theme_label.grid(row=2, column=1, sticky="ew", pady=4)

        theme_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        theme_frame.grid(row=2, column=0, columnspan=4, sticky="ew", padx=16, pady=(8, 4))
        ctk.CTkLabel(theme_frame, text="Tema PDF:").pack(side="left", padx=(0, 8))
        themes = available_themes()
        ctk.CTkOptionMenu(
            theme_frame, variable=self.markitpdf_theme, values=themes or ["professional"],
        ).pack(side="left")
        ctk.CTkCheckBox(
            theme_frame, text="Unir en un solo documento (en orden)",
            variable=self.merge_mode,
        ).pack(side="right", padx=8)

        action_row = ctk.CTkFrame(self.root, fg_color="transparent")
        action_row.grid(row=3, column=0, columnspan=4, sticky="ew", padx=16, pady=(8, 4))

        self.convert_docx_btn = ctk.CTkButton(
            action_row, text="Convertir a Word", command=lambda: self._start_conversion("docx")
        )
        self.convert_docx_btn.pack(side="left", padx=(0, 8))

        self.convert_pdf_btn = ctk.CTkButton(
            action_row, text="Convertir a PDF", command=lambda: self._start_conversion("pdf")
        )
        self.convert_pdf_btn.pack(side="left", padx=(0, 8))

        self.progress_bar = ctk.CTkProgressBar(action_row, mode="indeterminate", width=160)

        self.log_box = ctk.CTkTextbox(self.root, wrap="word")
        self.log_box.grid(row=4, column=0, columnspan=4, sticky="nsew", padx=16, pady=(8, 16))
        self.log_box.configure(state="disabled")

    def _attach_logging(self) -> None:
        handler = QueueLogHandler(self.event_queue)
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        logging.getLogger("crear_documento").addHandler(handler)
        logging.getLogger("markitpdf").addHandler(handler)

    def _append_log(self, text: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _check_browser(self) -> None:
        try:
            find_browser()
        except BrowserNotFoundError as exc:
            self._append_log(f"⚠ {exc}")
            self.convert_pdf_btn.configure(state="disabled")
            self._browser_missing = True
        else:
            self._browser_missing = False

    def _on_drop(self, event) -> None:
        raw_paths = self.root.tk.splitlist(event.data)
        paths = [Path(p) for p in raw_paths]
        valid, invalid = self._partition_supported(paths)
        if invalid:
            self._append_log(
                "Ignorados (no son .md/.markdown/.html/.htm): "
                + ", ".join(p.name for p in invalid)
            )
        if valid:
            self.selected_files = valid
            self._update_files_label()

    def _on_select_files(self) -> None:
        patterns = " ".join(f"*{e}" for e in sorted(SUPPORTED_EXTENSIONS))
        paths = filedialog.askopenfilenames(
            title="Selecciona archivos Markdown o HTML",
            filetypes=[
                ("Markdown/HTML", patterns),
                ("Todos los archivos", "*.*"),
            ],
        )
        if not paths:
            return
        valid, invalid = self._partition_supported([Path(p) for p in paths])
        if invalid:
            self._append_log(
                "Ignorados (no son .md/.markdown/.html/.htm): "
                + ", ".join(p.name for p in invalid)
            )
        self.selected_files = valid
        self._update_files_label()

    def _on_select_output_dir(self) -> None:
        directory = filedialog.askdirectory(title="Selecciona la carpeta de salida")
        if directory:
            self.output_dir = Path(directory)
            self.output_label.configure(text=str(self.output_dir))

    def _on_select_theme(self) -> None:
        path = filedialog.askopenfilename(
            title="Selecciona un archivo de tema",
            filetypes=[
                ("Tema", "*.json *.yaml *.yml *.toml"),
                ("Todos los archivos", "*.*"),
            ],
        )
        if path:
            try:
                load_theme(Path(path))
            except Exception as exc:
                self._append_log(f"Tema inválido, se ignora: {exc}")
                return
            self.theme_path = Path(path)
            self.theme_label.configure(text=self.theme_path.name)

    @staticmethod
    def _partition_supported(paths: list[Path]) -> tuple[list[Path], list[Path]]:
        valid = [p for p in paths if p.suffix.lower() in SUPPORTED_EXTENSIONS]
        invalid = [p for p in paths if p.suffix.lower() not in SUPPORTED_EXTENSIONS]
        return valid, invalid

    def _update_files_label(self) -> None:
        if not self.selected_files:
            self.files_label.configure(text="Ningún archivo seleccionado")
        elif len(self.selected_files) == 1:
            self.files_label.configure(text=self.selected_files[0].name)
        else:
            self.files_label.configure(
                text=f"{len(self.selected_files)} archivos seleccionados (se procesarán en orden alfabético)"
            )

    def _start_conversion(self, fmt: str) -> None:
        if not self.selected_files:
            self._append_log("Selecciona al menos un archivo antes de convertir.")
            return
        if fmt == "pdf" and self._browser_missing:
            self._append_log("No se puede exportar a PDF: no hay navegador Chromium disponible.")
            return

        self._set_busy(True)
        files = sorted(self.selected_files, key=lambda p: p.name.lower())
        threading.Thread(target=self._convert_worker, args=(files, fmt), daemon=True).start()

    def _convert_worker(self, files: list[Path], fmt: str) -> None:
        merge = self.merge_mode.get()
        try:
            if merge:
                self._convert_merged(files, fmt)
            else:
                self._convert_separate(files, fmt)
        except Exception as exc:
            self.event_queue.put(("error", f"Error general: {exc}"))
        self.event_queue.put(("finished", None))

    def _convert_separate(self, files: list[Path], fmt: str) -> None:
        for source in files:
            try:
                output_path = None
                if self.output_dir is not None:
                    output_path = self.output_dir / source.with_suffix(f".{fmt}").name
                if fmt == "docx":
                    result = convert_source_file(source, output_path, theme_path=self.theme_path)
                else:
                    result = MarkdownToPdfConverter(theme=self.markitpdf_theme.get()).convert(
                        source, output_path
                    ).output_path
                self.event_queue.put(("done", f"Creado: {result}"))
            except Exception as exc:
                self.event_queue.put(("error", f"Error con '{source.name}': {exc}"))

    def _convert_merged(self, files: list[Path], fmt: str) -> None:
        if not files:
            return
        if self.output_dir is not None:
            out_dir = self.output_dir
        else:
            out_dir = files[0].parent
        out_dir.mkdir(parents=True, exist_ok=True)
        output = out_dir / f"merged.{fmt}"
        if fmt == "docx":
            result = convert_merged_from_patterns([str(p) for p in files], output, theme_path=self.theme_path)
            self.event_queue.put(("done", f"Documento unificado creado: {result} ({len(files)} archivos)"))
        else:
            converter = MarkdownToPdfConverter(theme=self.markitpdf_theme.get())
            result = converter.convert_many(files, output).output_path
            self.event_queue.put(("done", f"PDF unificado creado: {result} ({len(files)} archivos)"))

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        self.convert_docx_btn.configure(state=state)
        if self._browser_missing:
            self.convert_pdf_btn.configure(state="disabled")
        else:
            self.convert_pdf_btn.configure(state=state)
        if busy:
            self.progress_bar.pack(side="left", padx=(8, 0))
            self.progress_bar.start()
        else:
            self.progress_bar.stop()
            self.progress_bar.pack_forget()

    def _drain_queue(self) -> None:
        try:
            while True:
                kind, payload = self.event_queue.get_nowait()
                if kind == "finished":
                    self._set_busy(False)
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

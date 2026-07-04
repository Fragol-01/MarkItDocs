import os
import sys
from pathlib import Path
import threading
import traceback

import PySimpleGUI as sg

# Import the existing converter (assumes crear_documento.py exposes convert_markdown_file)
# We'll try to import it from the same folder where this app will live.

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from crear_documento import convert_markdown_file
except Exception:
    # If import fails, fallback to importing from Desktop root
    try:
        sys.path.append(str(Path.home() / 'Desktop'))
        from crear_documento import convert_markdown_file
    except Exception:
        convert_markdown_file = None


def safe_convert(input_path, output_path, window):
    try:
        if convert_markdown_file is None:
            raise RuntimeError('No se pudo importar convert_markdown_file desde crear_documento.py')
        window.write_event_value('-LOG-', f'Starting conversion: {input_path}')
        out = convert_markdown_file(Path(input_path), Path(output_path))
        window.write_event_value('-DONE-', f'Documento creado: {out}')
    except Exception as e:
        tb = traceback.format_exc()
        window.write_event_value('-ERROR-', f'Error: {e}\n{tb}')


def main():
    sg.theme('LightBlue')

    layout = [
        [sg.Text('Arrastra un archivo .md aquí o usa "Seleccionar"', size=(40,1))],
        [sg.Input(key='-IN-', enable_events=True, visible=False), sg.FilesBrowse('Seleccionar', file_types=(('Markdown Files', '*.md'),)), sg.Button('Convertir')],
        [sg.Text('Salida (opcional):'), sg.InputText(key='-OUT-'), sg.FolderBrowse('Carpeta salida')],
        [sg.Multiline('', size=(80,20), key='-ML-', autoscroll=True, disabled=True)],
        [sg.Button('Salir')]
    ]

    window = sg.Window('MD → DOCX (Desktop GUI)', layout, finalize=True)

    while True:
        event, values = window.read()
        if event in (None, 'Salir'):
            break
        if event == 'Convertir':
            input_files = values['-IN-']
            if not input_files:
                window['-ML-'].update('Por favor selecciona al menos un archivo .md\n', append=True)
                continue
            # FilesBrowse may return a semicolon-separated list
            files = [p for p in input_files.split(';') if p]
            out_folder = values['-OUT-'] or os.path.join(str(Path.home()), 'Desktop')
            for f in files:
                in_path = Path(f)
                out_name = in_path.with_suffix('.docx').name
                out_path = Path(out_folder) / out_name
                threading.Thread(target=safe_convert, args=(in_path, out_path, window), daemon=True).start()
        if event == '-LOG-':
            window['-ML-'].update(values[event] + '\n', append=True)
        if event == '-DONE-':
            window['-ML-'].update(values[event] + '\n', append=True)
        if event == '-ERROR-':
            window['-ML-'].update(values[event] + '\n', append=True)

    window.close()


if __name__ == '__main__':
    main()

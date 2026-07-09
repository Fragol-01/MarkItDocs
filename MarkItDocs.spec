# -*- mode: python ; coding: utf-8 -*-
# Build: pyinstaller MarkItDocs.spec

from PyInstaller.utils.hooks import collect_all

# pypdfium2 carga pdfium.dll como data ctypes: hay que arrastrar el paquete entero.
pdfium_datas, pdfium_binaries, pdfium_hidden = [], [], []
for pkg in ('pypdfium2', 'pypdfium2_raw'):
    d, b, h = collect_all(pkg)
    pdfium_datas += d
    pdfium_binaries += b
    pdfium_hidden += h

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=pdfium_binaries,
    # Los temas y plantillas LaTeX son data files: PyInstaller no los incluye
    # solo, y sin ellos la exportación a PDF/LaTeX falla dentro del .exe.
    datas=[
        ('markitpdf/themes', 'markitpdf/themes'),
        ('markitpdf/latex_templates', 'markitpdf/latex_templates'),
    ] + pdfium_datas,
    hiddenimports=[
        'markdown.extensions.extra',
        'markdown.extensions.tables',
        'markdown.extensions.fenced_code',
        'markdown.extensions.attr_list',
        'markdown.extensions.sane_lists',
        'markdown.extensions.toc',
        'markdown.extensions.codehilite',
        'pygments.formatters.html',
        'pygments.lexers',
        'yaml',
        'mistletoe',
    ] + pdfium_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MarkItDocs',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
    version='version_file.txt',
)

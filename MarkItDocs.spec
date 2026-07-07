# -*- mode: python ; coding: utf-8 -*-
# Build: pyinstaller MD_to_DOCX.spec

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    # Los temas de markitpdf son data files (css/json/yaml): PyInstaller no los
    # incluye solo, y sin ellos la exportación a PDF falla dentro del .exe.
    datas=[('markitpdf/themes', 'markitpdf/themes')],
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
    ],
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

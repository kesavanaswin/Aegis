# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ["agent/cli.py"],
    pathex=["."],
    binaries=[],
    datas=[],
    hiddenimports=[
        "agent.memory",
        "agent.provider",
        "agent.runtime",
        "plugins.loader",
        "plugins.example_plugin",
        "tools.builtin",
        "tools.registry",
        "tools.toolsets",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="hermes_starter.exe",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="hermes_starter",
)

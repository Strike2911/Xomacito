"""Build Windows publisher metadata from literal versions, without importing the app."""
import ast
import re
from pathlib import Path


def read_versions(root):
    values = {}
    for node in ast.parse((Path(root) / 'main.py').read_text(encoding='utf-8-sig')).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ('APP_VERSION', 'UPDATE_VERSION'):
                    values[target.id] = ast.literal_eval(node.value)
    for key in ('APP_VERSION', 'UPDATE_VERSION'):
        value = values.get(key)
        if not isinstance(value, str) or not re.fullmatch(r'\d+\.\d+\.\d+(?:\.\d+)?', value):
            raise ValueError(f'{key} must be a three- or four-part numeric version')
        if any(int(part) > 65535 for part in value.split('.')):
            raise ValueError(f'{key} exceeds Windows version limits')
    return values['APP_VERSION'], values['UPDATE_VERSION']


def make_version_info(root, description='Xomacito'):
    from PyInstaller.utils.win32.versioninfo import (
        VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable,
        StringStruct, VarFileInfo, VarStruct,
    )
    public, internal = read_versions(root)
    numeric = tuple(map(int, internal.split('.')))
    numeric += (0,) * (4 - len(numeric))
    return VSVersionInfo(
        ffi=FixedFileInfo(filevers=numeric, prodvers=numeric,
                         mask=0x3F, flags=0, OS=0x40004, fileType=1,
                         subtype=0, date=(0, 0)),
        kids=[StringFileInfo([StringTable('040904B0', [
            StringStruct('CompanyName', 'Xomacito'),
            StringStruct('FileDescription', description),
            StringStruct('FileVersion', internal),
            StringStruct('InternalName', 'Xomacito'),
            StringStruct('OriginalFilename', 'Xomacito.exe'),
            StringStruct('ProductName', 'Xomacito'),
            StringStruct('ProductVersion', public),
            StringStruct('LegalCopyright', 'Copyright (c) 2026 Strike (Strike2911)'),
        ])]), VarFileInfo([VarStruct('Translation', [0x409, 1200])])],
    )

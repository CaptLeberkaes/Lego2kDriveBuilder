"""Liest ausschließlich Paketpfade bekannter Asset-Verzeichnisse im Spielprozess.

Kein Schreiben in Prozessspeicher, keine Injektion, kein kompletter Dump.
Gesucht werden nur Zeichenfolgen wie /Game/LEGO/Flair/<Name>, wie sie die
geladene Asset-Registry als Paketnamen enthält. Räder und Baugruppen dienen
als Gegenprobe gegen den Katalog.
"""
import ctypes as c
from ctypes import wintypes as w
import json
from pathlib import Path
import re
import sys

from assettypen_diagnose import MBI

VERZEICHNISSE = [
    '/Game/LEGO/Wheel/',
    '/Game/LEGO/Assemblies/',
    '/Game/LEGO/Propeller/',
    '/Game/LEGO/Flair/',
    '/Game/LEGO/Decorations/',
    '/Game/Garage/LegoAssets/Stickers/',
    '/Game/Game/Vehicle/Inventory/CarChassisConfigs/',
    '/Game/Game/Vehicle/Inventory/BoatChassisConfigs/',
    '/Game/Game/Vehicle/Inventory/EngineConfigs/',
    '/Game/Game/Vehicle/Inventory/HornSoundConfigs/',
    '/Game/DrivePass/Audio/HornConfigs_DP2/',
    '/Game/DrivePass/Audio/HornConfigs_DP3/',
    '/Game/DrivePass/Audio/HornConfigs_DP4/',
]
NAME = rb'[A-Za-z0-9_/+-]+'


def main(pid):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    k = c.WinDLL('kernel32', use_last_error=True)
    k.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
    k.OpenProcess.restype = w.HANDLE
    k.VirtualQueryEx.argtypes = [w.HANDLE, c.c_void_p, c.POINTER(MBI), c.c_size_t]
    k.VirtualQueryEx.restype = c.c_size_t
    k.ReadProcessMemory.argtypes = [w.HANDLE, c.c_void_p, c.c_void_p, c.c_size_t, c.POINTER(c.c_size_t)]
    k.ReadProcessMemory.restype = w.BOOL
    k.CloseHandle.argtypes = [w.HANDLE]
    process = k.OpenProcess(0x410, False, pid)  # QUERY_INFORMATION | VM_READ
    if not process:
        raise OSError(c.get_last_error(), 'Spielprozess nicht lesbar')
    patterns = []
    for directory in VERZEICHNISSE:
        ascii_pattern = re.compile(re.escape(directory.encode('ascii')) + b'(' + NAME + b')')
        wide_name = b'((?:[A-Za-z0-9_/+-]\x00)+)'
        wide_pattern = re.compile(re.escape(directory.encode('utf-16le')) + wide_name)
        patterns.append((directory, ascii_pattern, 'ascii'))
        patterns.append((directory, wide_pattern, 'utf-16le'))
    # Streng: vollständiger Objektpfad /Game/.../Name.Name, also kein
    # abgeschnittener Speicherrest. Grundlage für Typen ohne Katalog.
    strict = []
    for directory in VERZEICHNISSE:
        ascii_pattern = re.compile(re.escape(directory.encode('ascii'))
                                   + rb'([A-Za-z0-9_+-]+)\.\1(?![A-Za-z0-9_+-])')
        wide_pattern = re.compile(re.escape(directory.encode('utf-16le'))
                                  + rb'((?:[A-Za-z0-9_+-]\x00)+)\.\x00\1(?![A-Za-z0-9_+-]\x00)')
        strict.append((directory, ascii_pattern, 'ascii'))
        strict.append((directory, wide_pattern, 'utf-16le'))
    found = {directory: set() for directory in VERZEICHNISSE}
    objects = {directory: set() for directory in VERZEICHNISSE}
    total = 0
    try:
        address = 0
        info = MBI()
        while k.VirtualQueryEx(process, address, c.byref(info), c.sizeof(info)):
            base, size = info.BaseAddress or 0, info.RegionSize
            if info.State == 0x1000 and not info.Protect & (0x100 | 0x01) and info.Protect & (0x02 | 0x04 | 0x08 | 0x20 | 0x40 | 0x80):
                for offset in range(0, size, 4 * 1024 * 1024):
                    length = min(4 * 1024 * 1024 + 8192, size - offset)
                    buf = c.create_string_buffer(length)
                    read = c.c_size_t()
                    if not k.ReadProcessMemory(process, base + offset, buf, length, c.byref(read)):
                        continue
                    data = buf.raw[:read.value]
                    total += read.value
                    for directory, pattern, encoding in patterns:
                        for match in pattern.finditer(data):
                            name = match.group(1).decode(encoding)
                            # Paketpfad ohne Objektteil; Ordner bleiben sichtbar.
                            if name and not name.endswith('/'):
                                found[directory].add(name)
                    for directory, pattern, encoding in strict:
                        for match in pattern.finditer(data):
                            objects[directory].add(match.group(1).decode(encoding))
            if base + size <= address:
                break
            address = base + size
    finally:
        k.CloseHandle(process)
    result = {'pakete': {directory: sorted(names) for directory, names in found.items()},
              'objektpfade': {directory: sorted(names) for directory, names in objects.items()}}
    output = Path(__file__).resolve().parent / 'freischaltung' / 'assetnamen-live.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    for directory in VERZEICHNISSE:
        print(directory, len(found[directory]), 'streng', len(objects[directory]))
    print('Gelesene MB:', total // (1024 * 1024), '->', output)


if __name__ == '__main__':
    main(int(sys.argv[1]))

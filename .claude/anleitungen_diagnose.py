"""Sucht im Spielprozess, wie Bauanleitungs-GUIDs gespeichert sind.

Kein Schreiben in Prozessspeicher, keine Injektion, kein kompletter Dump.
Ausgangspunkt ist die einzige echte GUID aus GarageInstructionCompletionMap
(Küstenwachen-Boot, vom Nutzer regulär abgeschlossen). Gesucht werden ihre
Rohbytes und Textformen sowie Vorkommen von "InstructionsGuid"; ausgegeben
werden nur kurze Umgebungsfenster dieser Treffer.

Aufruf: python anleitungen_diagnose.py <PID>
"""
import ctypes as c
from ctypes import wintypes as w
import json
from pathlib import Path
import re
import sys

from assettypen_diagnose import MBI

BOOT = bytes.fromhex('2dfd78367d86194194992452' '87b8e30d')
FENSTER = 256
MAX_TREFFER = 200


def guid_texte(raw):
    a, b, cc, d = (int.from_bytes(raw[i:i + 4], 'little') for i in range(0, 16, 4))
    digits = f'{a:08X}{b:08X}{cc:08X}{d:08X}'
    hyphen = f'{digits[:8]}-{digits[8:12]}-{digits[12:16]}-{digits[16:20]}-{digits[20:]}'
    return [digits, hyphen, digits.lower(), hyphen.lower()]


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
    muster = {'roh': BOOT}
    for text in guid_texte(BOOT):
        muster['ascii:' + text] = text.encode('ascii')
        muster['utf16:' + text] = text.encode('utf-16le')
    muster['ascii:InstructionsGuid'] = b'InstructionsGuid'
    muster['utf16:InstructionsGuid'] = 'InstructionsGuid'.encode('utf-16le')
    treffer = {name: [] for name in muster}
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
                    for name, pattern in muster.items():
                        if len(treffer[name]) >= MAX_TREFFER:
                            continue
                        for m in re.finditer(re.escape(pattern), data):
                            # Überlappung der Lesefenster: nur Treffer im eigenen Block.
                            if m.start() >= 4 * 1024 * 1024:
                                continue
                            lo, hi = max(0, m.start() - FENSTER), m.end() + FENSTER
                            treffer[name].append({
                                'adresse': hex(base + offset + m.start()),
                                'region': hex(base), 'schutz': hex(info.Protect), 'typ': hex(info.Type),
                                'vorher': data[lo:m.start()].hex(), 'nachher': data[m.end():hi].hex(),
                            })
            if base + size <= address:
                break
            address = base + size
    finally:
        k.CloseHandle(process)
    output = Path(__file__).resolve().parent / 'freischaltung' / 'anleitungen-live.json'
    output.write_text(json.dumps(treffer, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    for name, liste in treffer.items():
        print(name, len(liste))
    print('Gelesene MB:', total // (1024 * 1024), '->', output)


if __name__ == '__main__':
    main(int(sys.argv[1]))

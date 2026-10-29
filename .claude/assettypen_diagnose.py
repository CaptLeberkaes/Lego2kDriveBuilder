"""Liest ausschließlich AssetManager-Konfigurationszeilen im Spielprozess.

Kein Schreiben in Prozessspeicher, keine Injektion, kein kompletter Dump.
Ausgegeben werden nur UE-Konfigurationszeilen mit PrimaryAssetType=.
"""
import ctypes as c
from ctypes import wintypes as w
import json
from pathlib import Path
import re
import sys


class MBI(c.Structure):
    _fields_ = [('BaseAddress', c.c_void_p), ('AllocationBase', c.c_void_p),
                ('AllocationProtect', w.DWORD), ('PartitionId', w.WORD),
                ('RegionSize', c.c_size_t), ('State', w.DWORD),
                ('Protect', w.DWORD), ('Type', w.DWORD)]


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
    seen = set()
    records = []
    total = 0
    try:
        address = 0
        info = MBI()
        needles = [('ascii', b'PrimaryAssetType='), ('utf-16le', 'PrimaryAssetType='.encode('utf-16le'))]
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
                    for encoding, needle in needles:
                        for match in re.finditer(re.escape(needle), data):
                            start = match.start()
                            unit = 2 if encoding == 'utf-16le' else 1
                            snippet = data[start:start + 4096 * unit]
                            text = snippet.decode(encoding, errors='replace').split('\0')[0]
                            # Eine Konfigurationszeile endet spätestens an Zeilenumbruch.
                            text = text.split('\n')[0].split('\r')[0]
                            if 'AssetBaseClass=' not in text or len(text) > 4096:
                                continue
                            parsed = re.match(r'PrimaryAssetType="([A-Za-z0-9_]+)",AssetBaseClass=([/A-Za-z0-9_.]+),', text)
                            paths = re.findall(r'Path="([/A-Za-z0-9_]+)"', text)
                            if not parsed or not paths:
                                continue
                            key = (parsed.group(1), parsed.group(2), tuple(paths))
                            if key not in seen:
                                seen.add(key)
                                record = {'PrimaryAssetType': key[0], 'AssetBaseClass': key[1], 'Directories': paths}
                                records.append(record)
                                print(json.dumps(record, ensure_ascii=True), flush=True)
            if base + size <= address:
                break
            address = base + size
    finally:
        k.CloseHandle(process)
    if records:
        output = Path(__file__).resolve().parent / 'freischaltung' / 'assettypen-live.json'
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Gelesene MB:', total // (1024 * 1024), 'Konfigurationszeilen:', len(seen))


if __name__ == '__main__':
    main(int(sys.argv[1]))

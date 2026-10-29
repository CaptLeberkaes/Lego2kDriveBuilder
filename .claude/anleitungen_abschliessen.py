"""Markiert alle Bauanleitungen in ArtemisVehicle.sav als abgeschlossen.

Vorlage ist der einzige echte Eintrag in GarageInstructionCompletionMap
(Küstenwachen-Boot, vom Nutzer regulär abgeschlossen): sein Wert
(OwnerId leer, TimesCompleted 1, CompletedWithoutSkips wahr) wird bytegenau
für jede fehlende GUID aus freischaltung/anleitungs-guids-live.json kopiert.
Vorhandene Einträge bleiben unverändert. Nur dieses eine Map-Feld wird geändert.

Ohne --anwenden entsteht nur die geprüfte Kopie freischaltung/ArtemisVehicle.sav.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'werkzeuge'))
import gvas_rw as g
import sichern
from freischalten import game_running

ARBEIT = ROOT / '.claude' / 'freischaltung'
SPIELSTAND = Path(sichern.SAVES) / 'ArtemisVehicle.sav'
GUIDS = ARBEIT / 'anleitungs-guids-live.json'
FELD = 'GarageInstructionCompletionMap'


def guid_bytes(text):
    # FGuid-Text "%08X%08X%08X%08X" -> vier uint32 little-endian.
    return b''.join(struct.pack('<I', int(text[i:i + 8], 16)) for i in range(0, 32, 8))


def entries(payload):
    r = g.R(payload)
    removed, count = r.i32(), r.i32()
    if removed:
        raise ValueError('Map mit entfernten Schlüsseln wird nicht unterstützt')
    out = []
    for _ in range(count):
        key = r.take(16)
        start = r.p
        g.read_props(r)
        out.append((key, payload[start:r.p]))
    if r.p != len(payload):
        raise ValueError('Map nicht vollständig gelesen')
    return out


def completion(props):
    data = g.val(props, 'Data')
    return next(p for p in data if p.name == FELD)


def prepare(source, wanted):
    sf = g.SaveFile.from_bytes(source)
    if sf.dump() != source:
        raise ValueError('Original nicht bytegenau rücklesbar')
    field = completion(sf.props)
    old = entries(field.value)
    if not old:
        raise ValueError('Kein Vorlageeintrag vorhanden')
    template = old[0][1]
    known = {key for key, _ in old}
    new = old + [(key, template) for key in wanted if key not in known]
    field.value = struct.pack('<ii', 0, len(new)) + b''.join(k + v for k, v in new)
    payload = sf.dump()
    # Gegenprobe: alles außer diesem Feld unverändert.
    check, orig = g.SaveFile.from_bytes(payload), g.SaveFile.from_bytes(source)
    completion(check.props).value = completion(orig.props).value
    if check.dump() != source:
        raise ValueError('Andere Felder als die Abschluss-Map verändert')
    return payload, len(new) - len(old)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--anwenden', action='store_true')
    args = parser.parse_args()
    wanted = [guid_bytes(t) for t in json.loads(GUIDS.read_text(encoding='utf-8'))['guids']]
    source = SPIELSTAND.read_bytes()
    payload, added = prepare(source, wanted)
    repeated, again = prepare(payload, wanted)
    if repeated != payload or again:
        raise ValueError('Idempotenzprüfung fehlgeschlagen')
    keys = {k for k, _ in entries(completion(g.SaveFile.from_bytes(payload).props).value)}
    if not set(wanted) <= keys:
        raise ValueError('Nicht alle GUIDs eingetragen')
    candidate = ARBEIT / 'ArtemisVehicle.sav'
    candidate.write_bytes(payload)
    report = {
        'zeit': time.strftime('%Y-%m-%d %H:%M:%S'),
        'quelle_sha256': hashlib.sha256(source).hexdigest(),
        'ergebnis_sha256': hashlib.sha256(payload).hexdigest(),
        'guids': len(wanted), 'ergaenzt': added, 'eintraege_gesamt': len(keys),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.anwenden and payload != source:
        if game_running():
            raise RuntimeError('Spiel läuft noch; keine Änderung angewendet')
        backup = ROOT / '_sicherungen' / ('anleitungen_' + time.strftime('%Y-%m-%d_%H-%M-%S'))
        shutil.copytree(SPIELSTAND.parent, backup)
        if SPIELSTAND.read_bytes() != source or (backup / SPIELSTAND.name).read_bytes() != source:
            raise RuntimeError('Spielstand während Vorbereitung geändert; Abbruch')
        sf = g.SaveFile(SPIELSTAND)
        sf.props = g.SaveFile.from_bytes(payload).props
        sf.save(SPIELSTAND)
        if SPIELSTAND.read_bytes() != payload:
            raise RuntimeError('Dateiprüfung nach Schreiben fehlgeschlagen')
        print('Angewendet. Vollständige Sicherung:', backup)
    elif args.anwenden:
        print('Bereits eingetragen; keine Änderung notwendig.')
    else:
        print('Nur vorbereitete Kopie:', candidate)


if __name__ == '__main__':
    main()

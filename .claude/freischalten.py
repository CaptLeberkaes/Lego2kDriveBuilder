"""Lokale Inhaltsfreigaben ergänzen; ohne --anwenden nur geprüfte Kopie erstellen.

Kein Konto, keine Serveranfragen, keine Änderungen an Story-Fortschritt oder XP.
Kataloge: .claude/quellen/l2kd-encyclopedia (öffentliche Asset-Exporte).
Die Annahme LegoAssembly für Räder/Propeller muss im Spiel geprüft werden.
"""
import argparse
import collections
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'werkzeuge'))
import gvas_rw as g
import sichern

QUELLEN = ROOT / '.claude' / 'quellen' / 'l2kd-encyclopedia'
ARBEIT = ROOT / '.claude' / 'freischaltung'
SPIELSTAND = Path(sichern.SAVES) / 'ArtemisPlayerInfo.sav'


def prop(props, name):
    return next(p for p in props if p.name == name)


def at(props, *names):
    for name in names:
        p = prop(props, name)
        props = p.value
    return p


def load_catalog(name):
    return json.loads((QUELLEN / (name + '_by_id.json')).read_text(encoding='utf-8'))


def catalog():
    result = set()
    for name in load_catalog('bricks'):
        result.add(('LegoPart', name))
    for name, pack in load_catalog('brickpacks').items():
        # Der Export entfernt Brickpack_ vom Dateinamen. DefaultBrickPack hat
        # diesen Präfix nicht; Originalnamen sind auch in sources belegt.
        original = name if name == 'DefaultBrickPack' else 'Brickpack_' + name
        result.add(('BrickPack', original))
    for name in load_catalog('vehicles'):
        result.add(('Vehicle', name))
    # Alle drei Klassen leiten sich von LegoAssembly ab. Der Asset-Typ ist
    # eine begründete Annahme, noch keine bestätigte Garage-Freigabe.
    for category in ('assemblies', 'wheels', 'propellers'):
        for name in load_catalog(category):
            result.add(('LegoAssembly', name))
    return result


def identity(entry):
    asset = prop(entry, 'LockRewardAsset').value
    typ = prop(prop(asset, 'PrimaryAssetType').value, 'Name')
    return g.R(typ.value).fstr(), g.R(prop(asset, 'PrimaryAssetName').value).fstr()


def make_entry(template, typ, name):
    entry = copy.deepcopy(template)
    asset = prop(entry, 'LockRewardAsset').value
    prop(prop(asset, 'PrimaryAssetType').value, 'Name').value = g.wstr(typ)
    prop(asset, 'PrimaryAssetName').value = g.wstr(name)
    # Zeitstempel im vorhandenen, spielerzeugten Format beibehalten.
    return entry


def reward_paths():
    return (
        ('Data', 'LocalProgression', 'ValidatedRewards', 'LockRewards'),
        ('Data', 'PlayerCompletionState', 'LastRewardSnapshot', 'LockRewards'),
    )


def prepare(source, wanted):
    sf = g.SaveFile.from_bytes(source)
    if sf.dump() != source:
        raise ValueError('Originaldatei wird nicht bytegenau reproduziert')
    counts = []
    for path in reward_paths():
        arr = at(sf.props, *path).value
        if not isinstance(arr, g.StructArray) or arr.struct_name != 'LockRewardEntry' or not arr.elems:
            raise ValueError('Unerwartetes Freischaltformat')
        existing = {identity(e) for e in arr.elems}
        missing = sorted(wanted - existing)
        template = arr.elems[0]
        arr.elems.extend(make_entry(template, typ, name) for typ, name in missing)
        counts.append(len(missing))
    payload = sf.dump()
    parsed = g.SaveFile.from_bytes(payload)
    if parsed.dump() != payload:
        raise ValueError('Rückleseprüfung fehlgeschlagen')
    for path in reward_paths():
        if not wanted <= {identity(e) for e in at(parsed.props, *path).value.elems}:
            raise ValueError('Freigaben beim Rücklesen unvollständig')
    # Entfernt man die Ergänzungen, muss die vollständige Originaldatei
    # bytegenau herauskommen: keine unbeabsichtigten Story-/Kontoänderungen.
    original = g.SaveFile.from_bytes(source)
    for path in reward_paths():
        at(parsed.props, *path).value = copy.deepcopy(at(original.props, *path).value)
    if parsed.dump() != source:
        raise ValueError('Nicht freigegebene Felder wurden verändert')
    return payload, counts


def game_running():
    check = subprocess.run(
        ['tasklist', '/FI', 'IMAGENAME eq LEGO2KDrive*', '/FO', 'CSV', '/NH'],
        capture_output=True, text=True, check=True,
    )
    return 'lego2kdrive' in check.stdout.lower()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--anwenden', action='store_true')
    args = parser.parse_args()
    source = SPIELSTAND.read_bytes()
    wanted = catalog()
    payload, counts = prepare(source, wanted)
    # Wiederholtes Anwenden darf keine Duplikate oder weiteren Änderungen erzeugen.
    repeated, additions = prepare(payload, wanted)
    if repeated != payload or any(additions):
        raise ValueError('Idempotenzprüfung fehlgeschlagen')
    ARBEIT.mkdir(parents=True, exist_ok=True)
    candidate = ARBEIT / 'ArtemisPlayerInfo.sav'
    candidate.write_bytes(payload)
    report = {
        'zeit': time.strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'vorbereitet; noch nicht im Spiel getestet',
        'quelle_sha256': hashlib.sha256(source).hexdigest(),
        'ergebnis_sha256': hashlib.sha256(payload).hexdigest(),
        'katalog': dict(collections.Counter(t for t, n in sorted(wanted))),
        'ergaenzungen_pro_liste': counts,
        'pruefungen': ['Original bytegenau', 'GVAS rücklesbar', 'Katalog vollständig eingetragen',
                       'Nur zwei LockRewards-Listen verändert', 'Idempotent'],
        'unsicher': ['LegoAssembly-Typ für Räder/Propeller im Spiel prüfen',
                    '662 Fahrzeuge einschließlich 14 laut Katalog nicht regulär gültiger Vorlagen',
                    'Premium-Pass-Menü bleibt gegebenenfalls gesperrt; keine Lizenzfreigabe geändert'],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.anwenden and payload != source:
        if game_running():
            raise RuntimeError('Spiel läuft noch; keine Änderung angewendet')
        backup = ROOT / '_sicherungen' / ('freischaltung_' + time.strftime('%Y-%m-%d_%H-%M-%S'))
        shutil.copytree(SPIELSTAND.parent, backup)
        if SPIELSTAND.read_bytes() != source or (backup / SPIELSTAND.name).read_bytes() != source:
            raise RuntimeError('Spielstand während Vorbereitung geändert; Abbruch')
        if game_running():
            raise RuntimeError('Spiel inzwischen gestartet; Abbruch')
        sf = g.SaveFile(SPIELSTAND)
        # Den von prepare geprüften Inhalt über den vorhandenen atomaren
        # Writer schreiben; Quell-Snapshot schützt vor parallelen Änderungen.
        sf.props = g.SaveFile.from_bytes(payload).props
        sf.save(SPIELSTAND)
        if SPIELSTAND.read_bytes() != payload:
            raise RuntimeError('Dateiprüfung nach Schreiben fehlgeschlagen')
        report['status'] = 'angewendet; noch nicht im Spiel getestet'
        report['sicherung'] = str(backup)
        print('Angewendet. Vollständige Sicherung:', backup)
    elif args.anwenden:
        print('Bereits eingetragen; keine Änderung notwendig.')
    else:
        print('Nur vorbereitete Kopie:', candidate)
    (ARBEIT / 'bericht.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()

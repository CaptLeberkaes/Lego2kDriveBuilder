"""Studio-.io-Dateien begrenzt und ohne Ausführung prüfen und analysieren.

Erzeugt Analyse/Vorschau, keinen GVAS-Import. Ein Virenscanner wird dadurch nicht
ersetzt. Autorisierte Originaldateien werden weder verändert noch ausgeführt.
"""
import argparse
import collections
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import struct
import xml.etree.ElementTree as ET
import zipfile
import zlib

import teiledaten
from baugeometrie import GEOM

ROOT = Path(__file__).resolve().parent.parent
ALLOWED = {'model.ldr', 'modelv2.ldr', 'model2.ldr', 'model.lxfml',
           'thumbnail.png', 'errorPartList.err', '.info'}
MAX_MEMBER = 16 * 1024 * 1024
MAX_TOTAL = 32 * 1024 * 1024


def reference(value):
    name = value.replace('\\', '/')
    path = PurePosixPath(name)
    if (path.is_absolute() or '..' in path.parts or ':' in name
            or not re.fullmatch(r'[A-Za-z0-9_. /-]+\.(?:dat|ldr|mpd)', name, re.I)):
        raise ValueError(f'Unsicherer/ungültiger LDraw-Verweis: {value!r}')
    return name


def finite(values):
    result = [float(v) for v in values]
    if any(not math.isfinite(v) or abs(v) > 1e9 for v in result):
        raise ValueError('Ungültige oder übergroße LDraw-Koordinaten')
    return result


def color(value):
    return int(value, 16) if value.lower().startswith('0x') else int(value)


def parse_ldr(raw, extended=False, geometry=False):
    text = raw.decode('utf-8-sig')
    if '\0' in text:
        raise ValueError('NUL-Bytes in LDraw-Text')
    parts, steps, meta = [], 0, []
    for number, line in enumerate(text.splitlines(), 1):
        tokens = line.split()
        if not tokens:
            continue
        if tokens[0] == '0':
            if line.startswith('0 STEP'):
                steps += 1
            elif line.startswith('0 FILE '):
                # MPD-Dateinamen sind Metadaten, werden niemals als Pfad geöffnet.
                meta.append(line)
            elif line.startswith(('0 Name:', '0 Author:', '0 STUDIOSTEPDESC')):
                meta.append(line)
            continue
        kind = tokens[0]
        if kind in ('1', '11'):
            if (kind == '11') != extended:
                raise ValueError(f'Unerwarteter LDraw-Datensatztyp {kind}, Zeile {number}')
            shift = 3 if extended else 0
            if len(tokens) < 15 + shift:
                raise ValueError(f'Unvollständiger LDraw-Datensatz, Zeile {number}')
            if extended and (int(tokens[2]) < 0 or tokens[3] not in ('True', 'False') or int(tokens[4]) < 0):
                raise ValueError(f'Ungültige Studio-Referenzdaten, Zeile {number}')
            values = finite(tokens[2+shift:14+shift])
            ref = reference(' '.join(tokens[14+shift:]))
            parts.append({'zeile': number, 'schritt': steps, 'ldraw_farbe': color(tokens[1]),
                          'position_ldu': values[:3], 'matrix': values[3:], 'referenz': ref})
        elif geometry and kind in ('2', '3', '4', '5'):
            # Studios eingebettetes model2 verwendet zusätzlich kurze Typ-5-Kanten
            # ohne Kontrollpunkte. Nur numerisch lesen, nicht als Standard-LDraw exportieren.
            required = {'2': (8,), '3': (11,), '4': (14,), '5': (8, 14)}[kind]
            if len(tokens) not in required:
                raise ValueError(f'Ungültige LDraw-Geometrie in Zeile {number}')
            color(tokens[1]); finite(tokens[2:])
        else:
            raise ValueError(f'Nicht unterstützter LDraw-Datensatz {kind!r}, Zeile {number}')
    return parts, steps, meta


def check_png(raw):
    if not raw.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('Vorschau ist keine PNG-Datei')
    pos, dimensions, ended = 8, None, False
    while pos < len(raw):
        if pos + 12 > len(raw):
            raise ValueError('Abgeschnittenes PNG')
        size = struct.unpack('>I', raw[pos:pos+4])[0]
        kind = raw[pos+4:pos+8]
        end = pos + 12 + size
        if end > len(raw):
            raise ValueError('Ungültige PNG-Blocklänge')
        data = raw[pos+8:pos+8+size]
        crc = struct.unpack('>I', raw[pos+8+size:end])[0]
        if zlib.crc32(kind+data) & 0xffffffff != crc:
            raise ValueError('PNG-CRC stimmt nicht')
        if kind == b'IHDR':
            if size != 13 or dimensions is not None:
                raise ValueError('Ungültiger PNG-Header')
            dimensions = struct.unpack('>II', data[:8])
            if any(not 0 < x <= 8192 for x in dimensions):
                raise ValueError('Vorschau ist zu groß')
        pos = end
        if kind == b'IEND':
            if size or pos != len(raw):
                raise ValueError('Zusätzliche Daten nach PNG-Ende')
            ended = True
            break
    if not ended or dimensions is None:
        raise ValueError('Unvollständige PNG-Struktur')
    return dimensions


def read_archive(path):
    raw = Path(path).read_bytes()
    if len(raw) > MAX_TOTAL or not raw.startswith(b'PK\x03\x04'):
        raise ValueError('Keine unterstützte oder zu große Studio-ZIP-Datei')
    payloads, entries = {}, []
    import io
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        if len(infos) > 32 or sum(i.file_size for i in infos) > MAX_TOTAL:
            raise ValueError('Archiv überschreitet Größen-/Eintragsgrenze')
        for info in infos:
            if info.filename not in ALLOWED or info.filename in payloads:
                raise ValueError(f'Unerwarteter oder doppelter Archiveintrag: {info.filename!r}')
            if info.flag_bits & 1:
                raise ValueError('Verschlüsselter Archiveintrag kann nicht geprüft werden')
            mode = info.external_attr >> 16
            if mode & 0o170000 not in (0, 0o100000):
                raise ValueError('Kein regulärer Archiveintrag')
            if info.file_size > MAX_MEMBER or info.file_size / max(1, info.compress_size) > 500:
                raise ValueError('Verdächtiges Größen-/Kompressionsverhältnis')
            payload = archive.read(info)  # ZIP-CRC wird beim Lesen geprüft.
            if len(payload) != info.file_size or payload.startswith((b'MZ', b'\x7fELF')):
                raise ValueError('Ungültiger Inhalt oder ausführbare Binärdaten')
            payloads[info.filename] = payload
            entries.append({'name': info.filename, 'bytes': len(payload),
                            'sha256': hashlib.sha256(payload).hexdigest()})
    if 'model.ldr' not in payloads or '.info' not in payloads:
        raise ValueError('Modell oder Studio-Metadaten fehlen')
    parts, steps, meta = parse_ldr(payloads['model.ldr'])
    info = json.loads(payloads['.info'])
    if info.get('total_parts') != len(parts):
        raise ValueError('Studio-Teilezahl stimmt nicht mit model.ldr überein')
    if 'errorPartList.err' in payloads and json.loads(payloads['errorPartList.err']):
        raise ValueError('Studio meldet fehlerhafte Teile')
    if 'modelv2.ldr' in payloads:
        extended, _, _ = parse_ldr(payloads['modelv2.ldr'], extended=True)
        if len(extended) != len(parts):
            raise ValueError('Erweiterte Studio-Teileliste hat abweichende Länge')
    if 'model2.ldr' in payloads:
        parse_ldr(payloads['model2.ldr'], geometry=True)
    xml_info = None
    if 'model.lxfml' in payloads:
        xml = payloads['model.lxfml']
        if b'<!DOCTYPE' in xml.upper() or b'<!ENTITY' in xml.upper():
            raise ValueError('XML-DTD/Entitäten sind nicht zugelassen')
        root = ET.fromstring(xml)
        if root.tag != 'LXFML':
            raise ValueError('Unerwarteter XML-Wurzeltyp')
        xml_info = {'name': root.get('name'),
                    'parts': len(root.findall('.//Part')),
                    'steps': len(root.findall('.//BuildingInstruction/Steps/Step')),
                    'tags': dict(collections.Counter(node.tag for node in root.iter()))}
    dimensions = check_png(payloads['thumbnail.png']) if 'thumbnail.png' in payloads else None
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw), 'entries': entries,
            'studio': info, 'parts': parts, 'step_delimiters': steps, 'metadata': meta,
            'xml': xml_info, 'preview_size': dimensions}, payloads


def map_part(ref, catalog):
    stem = PurePosixPath(ref).stem
    variant = re.fullmatch(r'(\d+)[a-z]', stem, re.I)
    if stem.isdigit():
        number, status = int(stem), 'id_oder_katalogalias'
    elif variant:
        number, status = int(variant.group(1)), 'buchstabenvariante_unbestaetigt'
    else:
        return {'status': 'nicht_zugeordnet', 'kandidaten': []}
    candidates = [number] if number in catalog else [k for k, v in catalog.items() if number in v['aliase']]
    return {'status': status if candidates else 'nicht_zugeordnet', 'kandidaten': candidates,
            'bekannte_GEOM': [k for k in candidates if k in GEOM and not GEOM[k].get('maske_unbekannt')]}


def analyze(path, output):
    report, payloads = read_archive(path)
    catalog = teiledaten.alle()
    name = Path(path).stem
    native_root = ROOT / '.claude/quellen/l2kd-encyclopedia/vehicle_parts'
    matches = []
    if native_root.exists():
        for native_path in native_root.glob('*.json'):
            native = json.loads(native_path.read_text(encoding='utf-8'))
            if native.get('name', '').strip().casefold() == name.casefold():
                matches.append({'id': native['id'], 'name': native['name'].strip(),
                                'parts': len(native['parts_and_colors']), 'terrain': native['terrain'],
                                'source_file': native_path.relative_to(ROOT).as_posix()})
    counts, missing, inventory = collections.Counter(), collections.Counter(), collections.Counter()
    for part in report['parts']:
        mapped = map_part(part['referenz'], catalog)
        part['spiel_zuordnung'] = mapped
        counts[mapped['status']] += 1
        if mapped['status'] == 'nicht_zugeordnet':
            missing[part['referenz']] += 1
        inventory[(part['referenz'], part['ldraw_farbe'])] += 1
    report.update(name=name, source_file=Path(path).resolve().relative_to(ROOT).as_posix(),
                  mapping_counts=dict(counts), unmapped_parts=dict(missing), native_matches=matches,
                  import_status='nicht_in_spielgarage_importiert',
                  import_blockers=['Keine spielnativen FieldIndex-Verbindungen enthalten',
                                   'LDraw-Ursprünge, Farben, Chassis-/Rad-Baugruppen und Sockets müssen abgeglichen werden',
                                   'Unvollständige Geometrie und unbestätigte Varianten nicht durch erfundene Verbindungen ersetzen'],
                  security_status='strukturelle_Pruefung_bestanden_keine_Antivirusgarantie')
    slug = re.sub(r'[^a-z0-9]+', '-', name.casefold()).strip('-')
    if not slug:
        raise ValueError('Kein sicherer Ausgabeordnername')
    directory = Path(output) / slug
    directory.mkdir(parents=True, exist_ok=True)
    if 'thumbnail.png' in payloads:
        (directory / 'vorschau.png').write_bytes(payloads['thumbnail.png'])
    (directory / 'analyse.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    (directory / 'teileliste.json').write_text(json.dumps([
        {'referenz': ref, 'ldraw_farbe': c, 'anzahl': n, 'spiel_zuordnung': map_part(ref, catalog)}
        for (ref, c), n in sorted(inventory.items())], ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('quelle', type=Path)
    parser.add_argument('--ausgabe', type=Path, default=ROOT/'.claude/studio-modelle')
    args = parser.parse_args()
    files = sorted(args.quelle.glob('*.io')) if args.quelle.is_dir() else [args.quelle]
    results = [analyze(p, args.ausgabe) for p in files]
    summary = [{'name': r['name'], 'sha256': r['sha256'], 'teile': len(r['parts']),
                'schritt_trenner': r['step_delimiters'], 'zuordnungen': r['mapping_counts'],
                'originale': r['native_matches'], 'import_status': r['import_status']} for r in results]
    args.ausgabe.mkdir(parents=True, exist_ok=True)
    (args.ausgabe/'uebersicht.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    for row in summary:
        print(row['name'], row['teile'], 'Teile;', row['schritt_trenner'], 'STEP-Trenner;', row['zuordnungen'])


if __name__ == '__main__':
    main()

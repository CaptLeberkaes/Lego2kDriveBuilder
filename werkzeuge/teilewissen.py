"""Beobachtete Teile und 3D-Kontakte aus Referenzfahrzeugen wiederverwenden.

Keine vollständigen Geometrien aus Feldhäufigkeiten ableiten. Eine Kontaktvorlage
gilt nur für ihre beobachteten Teilenummern, Felder, Skalen und relative 3D-Lage.
Spielstände werden ausschließlich gelesen; der Export enthält keine Spieler-IDs.

python werkzeuge/teilewissen.py erfassen [sav ...] [--mit-sicherungen]
python werkzeuge/teilewissen.py suchen 61252 [--partner 2540]
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import struct

import anschluesse
from baugeometrie import vector, quaternion, conjugate, multiply, rotate, quat_z, TOLERANZ
from geometrie import canonical

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATH = ROOT / '.claude/teilewissen/bibliothek.json'
# Nutzerfreigabe 30.10.2026: Fahrzeuge sind Referenzen, ausschließlich das
# KI-gebaute Spaceshuttle ausschließen. Exakter Name aus raketen_shuttle.json.
EXCLUDED_NAMES = anschluesse.REFERENZ_AUSSCHLUESSE
KINDS = {'HingeConnection', 'FixedConnection', 'CylindricalConnection',
         'PrismaticConnection', 'BallConnection'}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def rotation(q):
    q = quaternion(q)
    first = next(x for x in q if abs(x) > 1e-6)
    return tuple(round(x if first > 0 else -x, 7) for x in q)


def pose(part):
    return (vector(part['pos']), quaternion(part['rot']) if 'rot' in part else quat_z(part.get('yaw', 0)),
            vector(part.get('scale', [1, 1, 1])))


def relative(a, b):
    pa, qa, sa = pose(a); pb, qb, sb = pose(b)
    return {'pos': [round(x, 4) for x in rotate(conjugate(qa), tuple(y-x for x, y in zip(pa, pb)))],
            'rot': list(rotation(multiply(conjugate(qa), qb))), 'scale_a': list(sa), 'scale_b': list(sb)}


def reversed_pattern(pattern):
    result = dict(pattern)
    rel = pattern['relative']; inv = conjugate(quaternion(rel['rot']))
    result.update(a=pattern['b'], b=pattern['a'], fa=pattern['fb'], fb=pattern['fa'],
                  relative={'pos': list(rotate(inv, tuple(-x for x in rel['pos']))),
                            'rot': list(inv), 'scale_a': rel['scale_b'], 'scale_b': rel['scale_a']})
    return result


def graph_parts(vehicle):
    graph = vehicle['PartGraph']
    raw = graph['Parts']['items']; transforms = graph['PartTransforms']['items']
    if len(raw) != len(transforms):
        raise ValueError('Referenz: unterschiedliche Teile-/Transformationsanzahl')
    return [dict(design=struct.unpack('<I', bytes.fromhex(p)[:4])[0],
                 pos=tf['Translation'], rot=tf['Rotation'], scale=tf['Scale3D'])
            for p, tf in zip(raw, transforms)]


def source_label(path):
    path = Path(path).resolve()
    return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.name


def collect(paths, catalog=None, loader=None, excluded_names=EXCLUDED_NAMES):
    """Deterministischer Snapshot; Graphen deduplizieren, Fundorte erhalten."""
    loader = loader or anschluesse.vehicles_with_source
    catalog = catalog or {}
    sources, graphs, parsed = {}, {}, {}
    excluded = {name.casefold() for name in excluded_names}
    for path in sorted(set(map(str, paths))):
        raw = Path(path).read_bytes(); file_hash = hashlib.sha256(raw).hexdigest()
        label = source_label(path)
        sid = digest([label, file_hash])[:20]
        sources[sid] = {'path': label, 'sha256': file_hash}
        if file_hash not in parsed:
            parsed[file_hash] = list(loader(path))
        for origin, vehicle in parsed[file_hash]:
            name = vehicle['VehicleName']; gid = anschluesse.fingerprint(vehicle)
            record = graphs.setdefault(gid, {'vehicle': vehicle, 'locations': [], 'excluded': False})
            record['excluded'] |= name.casefold() in excluded
            location = {'source': sid, 'list': origin, 'name': name}
            if location not in record['locations']:
                record['locations'].append(location)
    part_info, patterns, manifest, rejected = {}, {}, {}, []
    for gid, record in sorted(graphs.items()):
        locations = sorted(record['locations'], key=lambda x: (x['source'], x['list'], x['name']))
        manifest[gid] = {'locations': locations, 'excluded': record['excluded']}
        if record['excluded']:
            continue
        vehicle = record['vehicle']; parts = graph_parts(vehicle)
        for part in parts:
            d = part['design']; data = catalog.get(d, catalog.get(str(d), {}))
            info = part_info.setdefault(str(d), {'name': data.get('name'), 'aliases': data.get('aliase', []),
                                                'graphs': [], 'fields': {}})
            if gid not in info['graphs']:
                info['graphs'].append(gid)
        seen = set()
        for c in vehicle['PartGraph']['Connections']['items']:
            key = canonical(c)
            if key in seen:
                continue
            seen.add(key)
            a, b, fa, fb, strength, kind = key; kind = kind.split('::')[-1]
            if (not 0 <= a < len(parts) or not 0 <= b < len(parts) or a == b or kind not in KINDS
                    or not 0 <= fa <= 255 or not 0 <= fb <= 255 or not 1 <= strength <= 255
                    or (kind == 'FixedConnection' and strength < 2)
                    or (kind != 'FixedConnection' and strength != 1)):
                rejected.append({'graph': gid, 'indices': [a, b], 'reason': 'invalid_connection'})
                continue
            # Deterministic direction by design, then relative transform for equal IDs.
            if parts[a]['design'] > parts[b]['design']:
                a, b, fa, fb = b, a, fb, fa
            pattern = {'a': parts[a]['design'], 'b': parts[b]['design'], 'fa': fa, 'fb': fb,
                       'strength': strength, 'type': kind, 'relative': relative(parts[a], parts[b])}
            if pattern['a'] == pattern['b']:
                inverse = reversed_pattern(pattern)
                inverse['relative']['pos'] = [round(x, 4) for x in inverse['relative']['pos']]
                inverse['relative']['rot'] = list(rotation(inverse['relative']['rot']))
                if json.dumps(inverse, sort_keys=True) < json.dumps(pattern, sort_keys=True):
                    pattern = inverse; a, b = b, a
            pid = digest(pattern)[:24]
            entry = patterns.setdefault(pid, dict(pattern, evidence=[]))
            entry['evidence'].append({'graph': gid, 'indices': [a, b]})
            for d, field in ((pattern['a'], pattern['fa']), (pattern['b'], pattern['fb'])):
                fs = part_info[str(d)]['fields'].setdefault(str(field), {'types': [], 'patterns': []})
                if kind not in fs['types']:
                    fs['types'].append(kind); fs['types'].sort()
                if pid not in fs['patterns']:
                    fs['patterns'].append(pid)
    return {'schema': 1, 'units': {'stud': 25, 'plate': 10},
            'meaning': 'Observed pair poses only; no complete geometry or independent game validation inferred.',
            'excluded_names': sorted(excluded_names), 'sources': sources, 'graphs': manifest,
            'parts': part_info, 'patterns': patterns, 'rejected': rejected,
            'summary': {'source_files': len(sources), 'reference_graphs': sum(not r['excluded'] for r in graphs.values()),
                        'excluded_graphs': sum(r['excluded'] for r in graphs.values()),
                        'parts': len(part_info), 'patterns': len(patterns)}}


class Library:
    def __init__(self, data):
        if data.get('schema') != 1:
            raise ValueError('Unbekanntes Teilewissen-Schema')
        self.data = data
        self.by_pair = collections.defaultdict(list)
        for pid, pattern in data['patterns'].items():
            entry = dict(pattern, id=pid)
            self.by_pair[(entry['a'], entry['b'])].append(entry)
            if entry['a'] != entry['b']:
                self.by_pair[(entry['b'], entry['a'])].append(reversed_pattern(entry))
            else:
                self.by_pair[(entry['a'], entry['b'])].append(reversed_pattern(entry))

    @classmethod
    def load(cls, path=DEFAULT_PATH):
        return cls(json.loads(Path(path).read_text(encoding='utf-8')))

    def candidates(self, design, partner=None, field=None, partner_field=None):
        result = []
        for (a, b), entries in self.by_pair.items():
            if a != design or (partner is not None and b != partner):
                continue
            for entry in entries:
                if field is not None and entry['fa'] != field:
                    continue
                if partner_field is not None and entry['fb'] != partner_field:
                    continue
                if not any(x['id'] == entry['id'] and x['a'] == entry['a'] and x['relative'] == entry['relative'] for x in result):
                    result.append(entry)
        return sorted(result, key=lambda x: (x['a'], x['b'], x['fa'], x['fb'], x['id'], json.dumps(x['relative'], sort_keys=True)))

    def place(self, anchor, pattern_id):
        choices = [p for p in self.candidates(anchor['design']) if p['id'] == pattern_id]
        if len(choices) != 1:
            raise ValueError('Kontaktvorlage fehlt oder Richtung ist mehrdeutig; Anordnung nicht geraten')
        pattern = choices[0]; pos, q, scale = pose(anchor); rel = pattern['relative']
        if max(abs(x-y) for x, y in zip(scale, rel['scale_a'])) > .001:
            raise ValueError('Skalierung des Ankers weicht vom Kontaktbeleg ab')
        delta = rotate(q, rel['pos'])
        return {'design': pattern['b'], 'pos': tuple(x+y for x, y in zip(pos, delta)),
                'rot': multiply(q, quaternion(rel['rot'])), 'scale': tuple(rel['scale_b'])}

    def match(self, a, b):
        if (a['design'], b['design']) not in self.by_pair:
            return []
        rel = relative(a, b); matches = []
        for pattern in self.by_pair.get((a['design'], b['design']), []):
            expected = pattern['relative']
            if any(max(abs(x-y) for x, y in zip(rel[k], expected[k])) > .001 for k in ('scale_a', 'scale_b')):
                continue
            if sum((x-y)**2 for x, y in zip(rel['pos'], expected['pos'])) > TOLERANZ**2:
                continue
            qa, qb = quaternion(rel['rot']), quaternion(expected['rot'])
            if 1-abs(sum(x*y for x, y in zip(qa, qb))) > 1e-7:
                continue
            matches.append(pattern)
        return matches

    def connect(self, parts):
        result = {}
        for a in range(len(parts)):
            for b in range(a+1, len(parts)):
                for pattern in self.match(parts[a], parts[b]):
                    key = (a, b, pattern['fa'], pattern['fb'], pattern['strength'], pattern['type'])
                    result.setdefault(key, []).append(pattern['id'])
        # Mehrere verschiedene Typen/Stärken für dieselben Felder sind kein
        # eindeutiger Beleg. Andere Feldpaare dürfen gleichzeitig existieren.
        variants = collections.defaultdict(set)
        for key in result:
            variants[key[:4]].add(key[4:])
        return {key: sorted(set(ids)) for key, ids in result.items() if len(variants[key[:4]]) == 1}

    def describe(self, design, catalog=None):
        catalog = catalog or {}
        original = catalog.get(design, catalog.get(str(design)))
        aliases = sorted(int(k) for k, v in catalog.items() if design in v.get('aliase', []) and int(k) != design)
        observed = self.data['parts'].get(str(design))
        return {'design': design, 'catalog_present': original is not None, 'alias_candidates': aliases,
                'observed_in_references': observed is not None, 'name': (original or observed or {}).get('name'),
                'fields': (observed or {}).get('fields', {}),
                'note': 'Katalog/Beobachtung beweist weder Freischaltung noch vollständige Anschlussgeometrie.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    collect_cmd = commands.add_parser('erfassen')
    collect_cmd.add_argument('saves', nargs='*'); collect_cmd.add_argument('--mit-sicherungen', action='store_true')
    collect_cmd.add_argument('--ausgabe', type=Path, default=DEFAULT_PATH)
    search = commands.add_parser('suchen'); search.add_argument('design', type=int)
    search.add_argument('--partner', type=int); search.add_argument('--bibliothek', type=Path, default=DEFAULT_PATH)
    args = parser.parse_args(argv)
    catalog = json.loads((ROOT/'teiledaten.json').read_text(encoding='utf-8'))
    if args.command == 'erfassen':
        paths = anschluesse.expand(args.saves) if args.saves else anschluesse.alle_spielstaende()
        if args.mit_sicherungen:
            paths += [str(p) for p in (ROOT/'_sicherungen').glob('*/Artemis*.sav') if p.name in anschluesse.FAHRZEUG_DATEIEN]
        data = collect(paths, catalog)
        args.ausgabe.parent.mkdir(parents=True, exist_ok=True)
        args.ausgabe.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':'))+'\n', encoding='utf-8')
        print(json.dumps(data['summary'], ensure_ascii=False))
    else:
        library = Library.load(args.bibliothek)
        print(json.dumps(library.describe(args.design, catalog), ensure_ascii=False, indent=2))
        matches = library.candidates(args.design, args.partner)
        print(f'{len(matches)} beobachtete Kontaktlagen')
        for p in matches:
            print(p['id'], p['a'], p['fa'], '<->', p['b'], p['fb'], p['type'], p['relative'])


if __name__ == '__main__':
    main()

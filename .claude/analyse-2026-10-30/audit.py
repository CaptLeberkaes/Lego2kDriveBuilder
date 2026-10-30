"""Read-only audit of local data and Emerald; writes only sanitized audit JSON here.

Run from any directory: python .claude/analyse-2026-10-30/audit.py
No save files are written. Current saves are hashed before and after the audit.
"""
import collections
import copy
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'werkzeuge'))
import anschluesse as an
import baue_fahrzeug as builder
import baugeometrie as geo
import geom_kandidaten as candidates
import gvas
import gvas_rw as rw
from geometrie import canonical


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def designs(v):
    return [struct.unpack('<I', bytes.fromhex(p)[:4])[0]
            for p in v['PartGraph']['Parts']['items']]


def unit_rotation(q):
    q = geo.quaternion(q)
    # q and -q encode the same orientation, including half-turns with w == 0.
    pivot = max(range(4), key=lambda i: abs(q[i]))
    return tuple(-x for x in q) if q[pivot] < 0 else q


def match_parts(a, b):
    """Match design/color, pose and scale with tolerance, without relying on save order."""
    ga, gb = a['PartGraph'], b['PartGraph']
    da, db = designs(a), designs(b)
    mapping, remaining = {}, set(range(len(db)))
    for i, (d, tf) in enumerate(zip(da, ga['PartTransforms']['items'])):
        hits = []
        for j in sorted(remaining):
            other = gb['PartTransforms']['items'][j]
            if d != db[j] or bytes.fromhex(ga['Parts']['items'][i])[4] != bytes.fromhex(gb['Parts']['items'][j])[4]:
                continue
            if max(abs(x-y) for key in ('Translation', 'Scale3D') for x, y in zip(tf[key], other[key])) > .01:
                continue
            qa, qb = geo.quaternion(tf['Rotation']), geo.quaternion(other['Rotation'])
            if min(max(abs(x-y) for x, y in zip(qa, qb)), max(abs(x+y) for x, y in zip(qa, qb))) > .0001:
                continue
            hits.append(j)
        if len(hits) == 1:
            mapping[i] = hits[0]
            remaining.remove(hits[0])
    return mapping, remaining


def compare_emerald(source, plan):
    save, report = builder.build_vehicle(source, plan)
    parsed = gvas.read_props(gvas.R(rw.write_props(save.props)))['Data']
    generated = next(v for v in parsed['CustomVehicles']['items'] if v['VehicleName'] == plan['name'])
    current = next(v for v in an.vehicles(source) if v['VehicleName'] == plan['name'])
    mapping, remaining = match_parts(generated, current)
    a = []
    if len(mapping) == len(designs(generated)):
        for c in generated['PartGraph']['Connections']['items']:
            c = dict(c, PartIndexA=mapping[c['PartIndexA']], PartIndexB=mapping[c['PartIndexB']])
            a.append(canonical(c))
    b = list(map(canonical, current['PartGraph']['Connections']['items']))
    ca, cb = collections.Counter(a), collections.Counter(b)
    return dict(current_version=current['VersionId'], current_parts=len(designs(current)),
                generated_parts=len(designs(generated)), matched_parts=len(mapping), unmatched_current=sorted(remaining),
                raw_connections_current=len(b), raw_connections_generated=len(generated['PartGraph']['Connections']['items']),
                unique_connections_current=len(cb), unique_connections_generated=len(ca),
                missing_in_generated=list((cb-ca).elements()), extra_in_generated=list((ca-cb).elements()),
                unknown_geometry=report['geometrie_unbekannt'],
                body_instances=len(plan['teile']),
                body_instances_with_unknown_geometry=sum(p['teil'] not in geo.GEOM or geo.GEOM[p['teil']].get('maske_unbekannt', False) for p in plan['teile']),
                explicit_connections=len(plan.get('verbindungen', [])))


def archive_corpus(paths):
    """Keep all unique graphs, but record source alternatives separately from deduplication."""
    files, seen_files, graphs = [], set(), {}
    all_paths = list(map(Path, paths)) + sorted((ROOT/'_sicherungen').glob('*/Artemis*.sav'))
    for path in all_paths:
        if path.name not in an.FAHRZEUG_DATEIEN:
            continue
        digest = sha(path)
        if digest in seen_files:
            continue
        seen_files.add(digest)
        label = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.name
        files.append(label)
        for origin, v in an.vehicles_with_source(str(path)):
            key = an.fingerprint(v)
            entry = graphs.setdefault(key, {'vehicle': v, 'sources': []})
            entry['sources'].append({'file': label, 'list': origin, 'vehicle': v['VehicleName']})
    return files, graphs


def connection_dossier(graphs):
    """Observed pair poses are evidence, not inferred complete port masks."""
    wanted = {2436, 61252, 63082, 61409, 99780, 3956, 6143, 2540, 6019, 4032, 87580, 87087, 11211}
    grouped = collections.defaultdict(lambda: {'count': 0, 'graphs': set(), 'examples': []})
    for fingerprint, entry in graphs.items():
        v = entry['vehicle']; pg = v['PartGraph']; ds = designs(v)
        seen = set()
        for c in pg['Connections']['items']:
            sig = canonical(c)
            if sig in seen:
                continue
            seen.add(sig)
            for a, b, fa, fb in ((c['PartIndexA'], c['PartIndexB'], c['FieldIndexA'], c['FieldIndexB']),
                                 (c['PartIndexB'], c['PartIndexA'], c['FieldIndexB'], c['FieldIndexA'])):
                if ds[a] not in wanted:
                    continue
                ta, tb = [pg['PartTransforms']['items'][i] for i in (a, b)]
                qa, qb = geo.quaternion(ta['Rotation']), geo.quaternion(tb['Rotation'])
                delta = [y-x for x, y in zip(ta['Translation'], tb['Translation'])]
                relative = tuple(round(x, 2) for x in geo.rotate(geo.conjugate(qa), delta))
                q = geo.multiply(geo.conjugate(qa), qb)
                # Matrix representation avoids the sign ambiguity of half-turn quaternions.
                axes = tuple(round(x, 3) for axis in ((1,0,0), (0,1,0), (0,0,1)) for x in geo.rotate(q, axis))
                key = (ds[a], fa, ds[b], fb, c['Strength'], c['Type'], relative, axes,
                       tuple(round(x, 3) for x in ta['Scale3D']), tuple(round(x, 3) for x in tb['Scale3D']))
                group = grouped[key]; group['count'] += 1; group['graphs'].add(fingerprint)
                if len(group['examples']) < 3:
                    group['examples'].append({'indices': [a,b], 'sources': entry['sources'][:3]})
    result = []
    for key, value in sorted(grouped.items()):
        d, f, p, pf, n, kind, position, axes, scale, partner_scale = key
        result.append({'part': d, 'field': f, 'partner': p, 'partner_field': pf, 'strength': n,
                       'type': kind, 'partner_position_in_part_frame': position,
                       'partner_axes_in_part_frame': axes, 'part_scale': scale, 'partner_scale': partner_scale,
                       'observations': value['count'], 'unique_graphs': len(value['graphs']), 'examples': value['examples']})
    return result


def reproduce_validation_gaps():
    # Existing synthetic fixture: no player identifiers or live saves used here.
    sys.path.insert(0, str(ROOT / '.claude/tests'))
    import test_builder as fixture
    result = {}
    with tempfile.TemporaryDirectory() as tmp:
        source = fixture.fixture_file(Path(tmp)/'source.sav')
        cases = {
            'manual_connection_to_brick_10000_units_away': fixture.plan(
                [{'id': 'far', 'teil': 3005, 'farbe': 7, 'pos': [10000, 10000, 10000]}],
                verbindungen=[{'a': 'chassis:0', 'b': 'far', 'fa': 1, 'fb': 1, 'noppen': 1}]),
            'two_solid_bricks_at_identical_pose': fixture.plan([
                {'id': 'a', 'teil': 3005, 'farbe': 7, 'pos': [-12.5, 12.5, 10]},
                {'id': 'b', 'teil': 3005, 'farbe': 8, 'pos': [-12.5, 12.5, 10]}]),
        }
        for name, plan in cases.items():
            try:
                _, report = builder.build_vehicle(source, plan)
                result[name] = {'accepted': True, 'loose_parts': report['lose_teile'], 'warnings': report['warnungen']}
            except ValueError as error:
                result[name] = {'accepted': False, 'error': str(error)}
        # Candidate learning currently ignores connection Type, even in its countercheck.
        parts = []
        for d, pos in [(3005, [0,0,0]), (999001, [0,0,30]), (3005, [50,0,0]), (999001, [50,0,30])]:
            parts.append((struct.pack('<IBBBB', d, 7, 0, 0, 0).hex(),
                          {'Translation': pos, 'Rotation': [0,0,0,1], 'Scale3D': [1,1,1]}))
        synthetic = {'VehicleName': 'synthetic-wrong-type', 'PartGraph': {
            'Parts': {'items': [p[0] for p in parts]}, 'PartTransforms': {'items': [p[1] for p in parts]},
            'Connections': {'items': [{'PartIndexA': a, 'PartIndexB': a+1, 'FieldIndexA': 0,
                                       'FieldIndexB': 1, 'Strength': 1, 'Type': 'ELegoConnectResult::BallConnection'}
                                      for a in (0,2)]}}}
        learned = candidates.analysiere([synthetic], {999001: [1,1,1]},
                                       {999001: {'groesse': [1,1,1], 'aliase': []}})[0]
        result['ball_connection_accepted_as_rectangular_stud_evidence'] = {
            'status': learned['status'], 'countercheck': learned['gegentest']}
        # Deduplication for statistics must not erase builder-accessible source alternatives.
        import sonderteile
        v = gvas.read_props(gvas.R(rw.write_props(fixture.fixture_vehicle())))
        def sources(path):
            return [('CachedVehicles' if path == 'cache' else 'DownloadedVehicles', v)]
        def usable(order):
            _, chassis = sonderteile.beobachtungen(order, sources)
            return sonderteile.builder_info(next(iter(chassis.values())))['nutzbar']
        result['source_order_changes_builder_availability'] = {
            'cache_then_download': usable(['cache', 'download']),
            'download_then_cache': usable(['download', 'cache'])}
    return result


def main():
    paths = an.alle_spielstaende()
    before = {str(Path(p)): sha(p) for p in paths}
    rows, unique, seen = [], [], set()
    part_counts, contact_designs = collections.Counter(), set()
    wanted = {2436, 61252, 63082, 61409, 99780, 3065}
    examples = collections.defaultdict(list)
    for path in paths:
        entries = list(an.vehicles_with_source(path))
        rows.append({'file': Path(path).name, 'named_vehicles': len(entries)})
        for origin, v in entries:
            ds = designs(v)
            for d in wanted & set(ds):
                examples[d].append({'file': Path(path).name, 'list': origin, 'vehicle': v['VehicleName'], 'count': ds.count(d)})
            key = an.fingerprint(v)
            if key in seen:
                continue
            seen.add(key)
            unique.append(v)
            part_counts.update(ds)
            for c in v['PartGraph']['Connections']['items']:
                contact_designs.update((ds[c['PartIndexA']], ds[c['PartIndexB']]))
    catalog = {int(k): v for k, v in load(ROOT/'teiledaten.json').items()}
    stored_fields = set(map(int, load(ROOT/'anschlusspunkte.json')))
    special = load(ROOT/'sonderteile.json')
    hashes = special['quellen_sha256_16']
    stale = []
    for path in paths:
        stored = hashes.get(Path(path).name)
        current = before[str(Path(path))][:16]
        if stored != current:
            stale.append({'file': Path(path).name, 'catalog_hash': stored, 'current_hash': current})
    autos = collections.Counter()
    misses = []
    for v in unique:
        parts = candidates.teile_des_fahrzeugs(v)
        saved = {canonical(c) for c in v['PartGraph']['Connections']['items']}
        predicted = set()
        for a, b, fa, fb, n in geo.connect(parts):
            kind = 'ELegoConnectResult::' + ('HingeConnection' if n == 1 else 'FixedConnection')
            predicted.add((a, b, fa, fb, n, kind))
        autos['saved_unique'] += len(saved)
        autos['predicted'] += len(predicted)
        autos['exact_including_type'] += len(predicted & saved)
        autos['prediction_mismatches'] += len(predicted-saved)
        autos['saved_not_predicted'] += len(saved-predicted)
        if predicted-saved:
            misses.append({'vehicle': v['VehicleName'], 'mismatches': sorted(predicted-saved)[:10]})
    plan = load(ROOT/'baupläne/emerald_express.json')
    emerald = compare_emerald(next(p for p in paths if Path(p).name == 'ArtemisVehicle.sav'), plan)
    archive_files, archived = archive_corpus(paths)
    archive_designs, archive_contacts = set(), set()
    body_instances, body_geom, body_designs = 0, 0, set()
    unsupported_body = collections.Counter()
    for entry in archived.values():
        v = entry['vehicle']; ds = designs(v); pg = v['PartGraph']
        archive_designs.update(ds)
        for c in pg['Connections']['items']:
            archive_contacts.update((ds[c['PartIndexA']], ds[c['PartIndexB']]))
        in_assemblies = {i for a in pg['Assemblies']['items'] for i in range(a['PartOffset'], a['PartOffset']+a['NumParts'])}
        for i, d in enumerate(ds):
            if i in in_assemblies:
                continue
            body_instances += 1; body_designs.add(d)
            if d in geo.GEOM and not geo.GEOM[d].get('maske_unbekannt'):
                body_geom += 1
            else:
                unsupported_body[d] += 1
    dossier = connection_dossier(archived)
    Path(__file__).with_name('kontaktbelege.json').write_text(json.dumps({
        'notice': 'Observed pair poses only; no complete geometry or availability inferred. Graph variants are not independent experiments.',
        'entries': dossier}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    # Request only simple rectangular candidates. Special parts need separate geometry.
    new_candidates = {d: catalog[d]['groesse'] for d in candidates.einfache_teile(catalog)}
    new_results = candidates.analysiere(unique, new_candidates, catalog)
    new_summary = [{'part': r['teil'], 'status': r['status'], 'geom': r['geom'], 'countercheck': r['gegentest']}
                   for r in new_results if r['status'] != 'zu_wenig_belege']
    result = {
        'date': '2026-10-30',
        'scope': 'Analysis only. Chassis fixed; wheel design excluded per user. Current Emerald is user-corrected.',
        'sources': rows, 'unique_graphs': len(unique), 'observed_designs': len(part_counts),
        'catalog_designs': len(catalog), 'geom_designs': len(geo.GEOM),
        'designs_with_connections_live': len(contact_designs),
        'designs_with_connections_stored': len(stored_fields),
        'new_connection_designs_since_stored': sorted(contact_designs-stored_fields),
        'stored_designs_absent_from_live': sorted(stored_fields-contact_designs),
        'special_catalog_stale_sources': stale,
        'archive_corpus': {'distinct_save_contents': len(archive_files), 'unique_graphs': len(archived),
                           'observed_designs': len(archive_designs), 'designs_with_connections': len(archive_contacts),
                           'stored_fields_not_in_archive': sorted(stored_fields-archive_contacts),
                           'body_instances_excluding_all_assemblies': body_instances, 'body_instances_with_geom': body_geom,
                           'body_designs': len(body_designs), 'most_frequent_body_designs_without_geom': unsupported_body.most_common(25),
                           'contact_dossier_patterns': len(dossier), 'files': archive_files},
        'emerald_part_observations': {d: {'catalog': catalog.get(d), 'geom': geo.GEOM.get(d),
                                          'unique_graph_instance_count': part_counts[d], 'examples': examples[d]}
                                      for d in sorted(wanted)},
        'emerald_current_vs_plan': emerald,
        'automatic_geometry_current_corpus': dict(autos), 'automatic_mismatch_examples': misses,
        'simple_geometry_candidate_status': dict(collections.Counter(r['status'] for r in new_results)),
        'simple_geometry_candidates_with_evidence': new_summary,
        'validation_gap_reproductions': reproduce_validation_gaps(),
        'source_files_unchanged': all(sha(path) == before[str(Path(path))] for path in paths),
        'source_sha256': {Path(p).name: before[str(Path(p))] for p in paths},
    }
    output = Path(__file__).with_name('befunde.json')
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k not in ('emerald_part_observations', 'source_sha256', 'automatic_mismatch_examples', 'archive_corpus')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

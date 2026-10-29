"""Offline regression tests. Only sanitized baseline JSON and temporary SAVs are used."""
import copy
import json
import math
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'werkzeuge'))
import baue_fahrzeug as builder
import baugeometrie as geo
import geometrie
import gvas
import gvas_rw as g
import tausche_teile


def native(name, kind, values):
    fmt = '<ffff' if kind == 'Quat' else '<fff'
    return g.Prop(name, 'StructProperty', struct.pack(fmt, *values), hdr={'struct': kind, 'guid': bytes(16)})


def array(name, kind, elems):
    return g.Prop(name, 'ArrayProperty', g.StructArray(name, kind, bytes(16), elems), hdr={'inner': 'StructProperty'})


def assembly(name, asset, off, count):
    return [g.Prop('AssemblyAsset', 'ObjectProperty', g.wstr(asset)),
            g.Prop('AssemblyType', 'NameProperty', g.wstr('Wheel' if '/Wheel/' in asset else 'None')),
            g.Prop('AssemblyName', 'NameProperty', g.wstr(name)),
            g.Prop('PartOffset', 'UInt16Property', struct.pack('<H', off)),
            g.Prop('NumParts', 'UInt16Property', struct.pack('<H', count))]


def transform(record):
    return [native('Rotation', 'Quat', record['Rotation']),
            native('Translation', 'Vector', record['Translation']),
            native('Scale3D', 'Vector', record['Scale3D'])]


def fixture_vehicle(name='Basis'):
    base = json.loads((ROOT / '.claude/tests/fixtures/alte-schule.json').read_text(encoding='utf-8'))
    parts = [struct.pack('<IBBBB', p['design'], p['color'], p['flags'], 0, 0) for p in base['parts']]
    tfs = [transform(p['transform']) for p in base['parts']]
    assemblies = [assembly(a['AssemblyName'], a['AssemblyAsset'], a['PartOffset'], a['NumParts']) for a in base['assemblies']]
    connections = [builder.connection(c['PartIndexA'], c['PartIndexB'], c['FieldIndexA'], c['FieldIndexB'], c['Strength'], c['Type']) for c in base['connections']]
    graph = [array('Parts', 'LegoPart', parts), array('PartTransforms', 'Transform', tfs),
             array('Assemblies', 'LegoAssembly', assemblies), array('Connections', 'LegoConnection', connections),
             g.Prop('StudOccluders', 'ArrayProperty', struct.pack('<i', 0), hdr={'inner': 'ByteProperty'}),
             g.Prop('StudOffsets', 'ArrayProperty', struct.pack('<i', 0), hdr={'inner': 'ByteProperty'}),
             g.Prop('StudOcclusionHash', 'UInt32Property', struct.pack('<I', 0))]
    return [g.Prop('VehicleName', 'StrProperty', g.wstr(name)),
            g.Prop('ChassisConfig', 'ObjectProperty', g.wstr(base['chassis_config'])),
            g.Prop('VehicleClass', 'EnumProperty', g.wstr('EVehicleClass::CAR'), hdr={'enum': 'EVehicleClass'}),
            g.Prop('Guid', 'StructProperty', bytes(16), hdr={'struct': 'Guid', 'guid': bytes(16)}),
            g.Prop('VersionId', 'UInt32Property', struct.pack('<I', 1)),
            g.Prop('LastEdited', 'StructProperty', bytes(8), hdr={'struct': 'DateTime', 'guid': bytes(16)}),
            g.Prop('OriginalCreatorId', 'StrProperty', g.wstr('offline-test-owner')),
            g.Prop('ImmediateCreatorId', 'StrProperty', g.wstr('offline-test-owner')),
            g.Prop('OriginalParentGuid', 'StructProperty', bytes(16), hdr={'struct': 'Guid', 'guid': bytes(16)}),
            g.Prop('ImmediateParentGuid', 'StructProperty', bytes(16), hdr={'struct': 'Guid', 'guid': bytes(16)}),
            g.Prop('ParentType', 'EnumProperty', g.wstr('ECustomVehicleParentType::Created'), hdr={'enum': 'ECustomVehicleParentType'}),
            g.Prop('PartGraph', 'StructProperty', graph, hdr={'struct': 'LegoPartGraph', 'guid': bytes(16)}),
            array('Sockets', 'LegoBrickSocket', []),
            g.Prop('FlairTriggers', 'ArrayProperty', struct.pack('<i', 0), hdr={'inner': 'EnumProperty'})]


def fixture_file(path, vehicles=None, ancillary=None):
    data = [array('CustomVehicles', 'CustomVehicleInfo', vehicles or [fixture_vehicle(), fixture_vehicle('')])]
    if ancillary is not None:
        data.append(g.Prop('AncillaryCustomSlot', 'IntProperty', struct.pack('<i', ancillary)))
    props = [g.Prop('Data', 'StructProperty', data, hdr={'struct': 'VehicleSaveData', 'guid': bytes(16)})]
    header = b'GVAS' + struct.pack('<iiHHHI', 3, 522, 4, 27, 2, 0) + g.wstr('test') + struct.pack('<ii', 3, 0) + g.wstr('/Script/Test.Save')
    path.write_bytes(header + g.write_props(props) + bytes(4))
    return path


def plan(parts=None, **extras):
    return dict(name='Ergebnis', vorlage_name='Basis', teile=parts if parts is not None else [
        {'id': 'boden', 'teil': 3022, 'farbe': 7, 'pos': [-12.5, 12.5, 10]},
        {'id': 'stein', 'teil': 3003, 'farbe': 7, 'pos': [-12.5, 12.5, 20]}], **extras)


def result_vehicle(save):
    return next(v for v in g.val(g.val(save.props, 'Data'), 'CustomVehicles').elems
                if builder.text_value(v, 'VehicleName') == 'Ergebnis')


class BuilderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = fixture_file(self.root / 'source.sav')

    def tearDown(self):
        self.temp.cleanup()

    def test_fixed_type_independent_of_donor_connection_type(self):
        source = g.SaveFile(self.source)
        v = g.val(g.val(source.props, 'Data'), 'CustomVehicles').elems[0]
        cs = g.val(g.val(v, 'PartGraph'), 'Connections').elems
        cs.insert(0, builder.connection(0, 1, 1, 3, 1, 'CylindricalConnection'))
        self.source.write_bytes(source.dump())
        output, report = builder.build_vehicle(self.source, plan())
        graph = g.val(result_vehicle(output), 'PartGraph')
        pair = {report['referenzen']['boden'], report['referenzen']['stein']}
        con = next(c for c in g.val(graph, 'Connections').elems if set(builder.connection_indices(c)) == pair)
        self.assertEqual(builder.text_value(con, 'Type'), 'ELegoConnectResult::FixedConnection')
        self.assertEqual(g.val(con, 'Strength'), bytes([4]))
        self.assertEqual(g.SaveFile.from_bytes(output.dump()).dump(), output.dump())

    def test_single_stud_does_not_require_a_hinge_in_template(self):
        _, report = builder.build_vehicle(self.source, plan([{'teil': 3005, 'farbe': 7, 'pos': [-12.5, 12.5, 10]}]))
        self.assertEqual(report['lose_teile'], [])

    def test_floating_group_is_rejected_before_saving(self):
        before = self.source.read_bytes()
        with self.assertRaisesRegex(ValueError, 'ohne Pfad'):
            builder.build_vehicle(self.source, plan([
                {'teil': 3005, 'farbe': 7, 'pos': [0, 0, 1000]},
                {'teil': 3005, 'farbe': 7, 'pos': [0, 0, 1030]}]))
        self.assertEqual(self.source.read_bytes(), before)

    def test_unknown_and_uncertain_geometry_is_not_invented(self):
        for design in (999999, 3823):
            with self.assertRaisesRegex(ValueError, 'unbekannt'):
                builder.build_vehicle(self.source, plan([{'teil': design, 'farbe': 7, 'pos': [0, 0, 0]}]))

    def test_manual_connections_and_driver_use_stable_ids(self):
        p = plan([{'id': 'sitz', 'teil': 999999, 'farbe': 7, 'pos': [0, 0, 10]}],
                 verbindungen=[{'a': 'chassis:0', 'b': 'sitz', 'fa': 1, 'fb': 0, 'noppen': 1}],
                 fahrer={'teil': 'sitz', 'pos': [0, 0, 10]})
        output, report = builder.build_vehicle(self.source, p)
        sockets = g.val(result_vehicle(output), 'Sockets').elems
        self.assertEqual(len(sockets), 1)
        self.assertEqual(struct.unpack('<i', g.val(sockets[0], 'BrickIndex'))[0], report['referenzen']['sitz'])

    def test_existing_ancillary_target_is_rejected(self):
        fixture_file(self.source, ancillary=0)
        p = plan(); p['name'] = 'Basis'
        with self.assertRaisesRegex(ValueError, 'Arbeitskopie'):
            builder.build_vehicle(self.source, p)

    def test_ancillary_empty_slot_is_reserved(self):
        fixture_file(self.source, vehicles=[fixture_vehicle(), fixture_vehicle(''), fixture_vehicle('')], ancillary=1)
        _, report = builder.build_vehicle(self.source, plan())
        self.assertEqual(report['slot'], 2)

    def test_wheel_swap_changes_part_count_and_preserves_3d_shape(self):
        donor = fixture_vehicle('Spender')
        pg = g.val(donor, 'PartGraph')
        wheel = g.val(pg, 'Assemblies').elems[1]
        set_value = builder.set_prop
        set_value(wheel, 'PartOffset', struct.pack('<H', 11)); set_value(wheel, 'NumParts', struct.pack('<H', 4))
        positions = [(0, 0, 0), (3, 5, 7), (8, 9, 11), (13, 17, 19)]
        for pos in positions:
            g.val(pg, 'Parts').elems.append(struct.pack('<IBBBB', 4032, 49, 2, 0, 0))
            g.val(pg, 'PartTransforms').elems.append(transform({'Rotation': [0, 0, 0, 1], 'Translation': pos, 'Scale3D': [1, 1, 1]}))
        g.val(pg, 'Connections').elems.extend([builder.connection(i, i+1, 0, 1, 1) for i in range(11, 14)])
        fixture_file(self.source, [fixture_vehicle(), donor, fixture_vehicle('')])
        output, _ = builder.build_vehicle(self.source, plan([], radtausch={'fl': 'Spender'}))
        outpg = g.val(result_vehicle(output), 'PartGraph')
        new_wheel = next(a for a in g.val(outpg, 'Assemblies').elems if builder.text_value(a, 'AssemblyName') == 'fl')
        ids = builder.indices(new_wheel)
        self.assertEqual(len(ids), 4)
        self.assertEqual(len(g.val(outpg, 'Parts').elems), 13)
        actual = [struct.unpack('<fff', g.val(g.val(outpg, 'PartTransforms').elems[i], 'Translation')) for i in ids]
        for n in range(1, 4):
            self.assertAlmostEqual(sum((actual[n][k]-actual[0][k])**2 for k in range(3)), sum(x*x for x in positions[n]), places=2)
        self.assertEqual(sum(set(builder.connection_indices(c)) <= set(ids) for c in g.val(outpg, 'Connections').elems), 3)

    def test_dry_run_creates_no_save(self):
        pp = self.root / 'plan.json'; pp.write_text(json.dumps(plan()), encoding='utf-8')
        target = self.root / 'never.sav'
        builder.main(self.source, target, pp, pruefen=True)
        self.assertFalse(target.exists())

    def test_unicode_vehicle_name_survives_both_readers(self):
        p = plan(); p['name'] = 'Prüfung München 🚀'
        output, _ = builder.build_vehicle(self.source, p)
        reader = gvas.R(output.dump()); gvas.read_header(reader)
        data = gvas.read_props(reader)['Data']
        self.assertIn(p['name'], [v['VehicleName'] for v in data['CustomVehicles']['items']])

    def test_swap_rejects_negative_index_and_missing_connection(self):
        for p in [{'teile': [{'von': '#-1', 'nach': 3005}]},
                  {'teile': [{'von': '#0', 'nach': 2445}],
                   'verbindungen': [{'a': '#0', 'b': '#3', 'fa': 0, 'fb': 1, 'noppen': 1}]}]:
            with self.assertRaises(ValueError):
                tausche_teile.swap(fixture_vehicle(), p)

    def test_new_driver_replaces_retained_driver_socket(self):
        vehicle = fixture_vehicle()
        g.val(vehicle, 'Sockets').elems.append([
            g.Prop('SocketName', 'NameProperty', g.wstr('TrafficSeat_DriverSit')),
            g.Prop('BrickIndex', 'IntProperty', struct.pack('<i', 0))])
        fixture_file(self.source, [vehicle, fixture_vehicle('')])
        output, report = builder.build_vehicle(self.source, plan(fahrer={'teil': 'stein'}))
        sockets = g.val(result_vehicle(output), 'Sockets').elems
        self.assertEqual(len(sockets), 1)
        self.assertEqual(struct.unpack('<i', g.val(sockets[0], 'BrickIndex'))[0], report['referenzen']['stein'])

    def test_invalid_color_rotation_and_duplicate_ids_are_rejected(self):
        for change in ({'farbe': 256}, {'rot': [0, 0, 0, 2]}, {'dreh': float('nan')}):
            p = plan(); p['teile'][0].update(change)
            with self.assertRaises(ValueError):
                builder.build_vehicle(self.source, p)
        p = plan(); p['teile'][1]['id'] = 'boden'
        with self.assertRaises(ValueError):
            builder.build_vehicle(self.source, p)

    def test_flair_connections_triggers_and_socket_are_preserved(self):
        vehicle = fixture_vehicle()
        pg = g.val(vehicle, 'PartGraph')
        g.val(pg, 'Parts').elems.append(struct.pack('<IBBBB', 3005, 7, 0, 0, 0))
        g.val(pg, 'PartTransforms').elems.append(transform({'Rotation': [0, 0, 0, 1], 'Translation': [-12.5, 12.5, 10], 'Scale3D': [1, 1, 1]}))
        g.val(pg, 'Assemblies').elems.append(assembly('None', '/Game/LEGO/Flair/Test.Test', 11, 1))
        g.val(pg, 'Connections').elems.append(builder.connection(0, 11, 1, 1, 1))
        builder.set_prop(vehicle, 'FlairTriggers', struct.pack('<i', 1)+g.wstr('EFlairTrigger::ALWAYSON'))
        g.val(vehicle, 'Sockets').elems.append([g.Prop('BrickIndex', 'IntProperty', struct.pack('<i', 11))])
        fixture_file(self.source, [vehicle, fixture_vehicle('')])
        output, _ = builder.build_vehicle(self.source, plan([], behalten=['flairs']))
        result = result_vehicle(output)
        self.assertEqual(builder.read_triggers(result), ['EFlairTrigger::ALWAYSON'])
        self.assertEqual(struct.unpack('<i', g.val(g.val(result, 'Sockets').elems[0], 'BrickIndex'))[0], 3)


class GeometryTests(unittest.TestCase):
    def test_quarter_turn_about_y_connects_lieing_bricks(self):
        q = (0, math.sqrt(0.5), 0, math.sqrt(0.5))
        result = geo.connect([{'design': 3005, 'pos': [0, 0, 0], 'rot': q},
                              {'design': 3005, 'pos': [30, 0, 0], 'rot': q}])
        self.assertEqual(result, [(0, 1, 0, 1, 1)])

    def test_arbitrary_yaw_preserves_grid_distances(self):
        points = geo.world_cells(3004, [0, 0, 0], 45, 'oben')
        a, b = list(points)
        self.assertAlmostEqual(math.dist(a, b), 25, places=3)
        self.assertIsNone(geo.yaw_of(geo.quat_z(45)))

    def test_floating_pair_not_reachable_even_though_each_has_connection(self):
        self.assertEqual(geo.unreachable(3, [(1, 2)], [0]), [1, 2])
        self.assertEqual(geo.unreachable(3, [(1, 2)], [0], [1, 2]), [])

    def test_neighbor_footprint_does_not_become_target_geometry(self):
        vehicle = {'VehicleName': 'Test', 'PartGraph': {
            'Parts': {'items': [struct.pack('<IBBBB', d, 7, 0, 0, 0).hex() for d in [3020, 87087]]},
            'PartTransforms': {'items': [{'Rotation': [0, 0, 0, 1], 'Translation': [0, 0, z], 'Scale3D': [1, 1, 1]} for z in [0, 10]]},
            'Connections': {'items': [{'PartIndexA': 0, 'PartIndexB': 1, 'FieldIndexA': 0, 'FieldIndexB': 1, 'Strength': 1, 'Type': 'ELegoConnectResult::HingeConnection'}]*3}}}
        observations = geometrie.constraints_from_vehicle(vehicle, {87087})
        self.assertEqual(len(observations), 1)
        self.assertEqual(observations[0]['kandidaten'], [(0, 0)])
        self.assertEqual(geometrie.summarize(observations)[0]['bestaetigte_zellen'], [(0, 0)])
        observations[0]['noppen'] = 2; observations[0]['widerspruch'] = True
        row = geometrie.summarize(observations)[0]
        self.assertEqual(row['status'], 'widerspruechlich')
        self.assertEqual(row['bestaetigte_zellen'], [])


class SaveTests(unittest.TestCase):
    def test_atomic_save_backup_and_stale_source_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = fixture_file(Path(tmp)/'test.sav')
            save = g.SaveFile(source)
            before = source.read_bytes()
            g.get(g.val(save.props, 'Data'), 'CustomVehicles').value.elems[0][0].value = g.wstr('Geändert')
            # Keep backup artifacts inside this test's temporary directory.
            with mock.patch.object(g, '__file__', str(Path(tmp)/'werkzeuge'/'gvas_rw.py')):
                save.save(source)
            self.assertEqual(save.last_backup.read_bytes(), before)
            self.assertNotEqual(source.read_bytes(), before)
            self.assertEqual(g.SaveFile(source).dump(), source.read_bytes())
            source.write_bytes(before)
            with self.assertRaisesRegex(ValueError, 'seit dem Einlesen'):
                save.save(source)

    def test_failed_replace_leaves_original_intact(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = fixture_file(Path(tmp)/'test.sav')
            before = source.read_bytes(); save = g.SaveFile(source)
            with mock.patch.object(g, '__file__', str(Path(tmp)/'werkzeuge'/'gvas_rw.py')), mock.patch.object(g.os, 'replace', side_effect=OSError('blocked')):
                with self.assertRaises(OSError):
                    save.save(source)
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual(list(Path(tmp).glob('*.tmp')), [])


if __name__ == '__main__':
    unittest.main()

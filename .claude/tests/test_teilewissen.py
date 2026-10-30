"""Meaningful offline checks for reference reuse, provenance and builder validation."""
import copy
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'werkzeuge'))
import teilewissen as knowledge
import baugeometrie as geo
import baue_fahrzeug as builder
import geom_kandidaten as learner
import sonderteile
import gvas
import gvas_rw as rw
from test_builder import fixture_file, fixture_vehicle, plan
from test_geom_kandidaten import auf_platte, bewerte, NEU, fahrzeug


def reference(name='Reference'):
    # Synthetic contact examples, not claims about the real shapes of these IDs.
    ps = [(3005, [0,0,0]), (61252, [0,0,30]), (2540, [12.5,50,30])]
    return {'VehicleName': name, 'PartGraph': {
        'Parts': {'items': [struct.pack('<IBBBB', d, 7, 0, 0, 0).hex() for d,_ in ps]},
        'PartTransforms': {'items': [dict(Translation=pos, Rotation=[0,0,0,1], Scale3D=[1,1,1]) for _,pos in ps]},
        'Connections': {'items': [dict(PartIndexA=a, PartIndexB=b, FieldIndexA=fa, FieldIndexB=fb,
                                        Strength=1, Type='ELegoConnectResult::'+kind)
                                  for a,b,fa,fb,kind in [(0,1,0,1,'HingeConnection'), (1,2,2,4,'CylindricalConnection')]]}}}


class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.ref = reference(); self.path = self.root/'reference.sav'; self.path.write_bytes(b'reference-marker')
        self.data = knowledge.collect([self.path], loader=lambda _: [('CustomVehicles', self.ref)])
        self.library = knowledge.Library(self.data)

    def tearDown(self):
        self.temp.cleanup()

    def test_source_alternatives_survive_graph_dedup_and_shuttle_is_excluded(self):
        second = self.root/'download.sav'; second.write_bytes(b'different-save-marker')
        shuttle = copy.deepcopy(self.ref); shuttle['VehicleName'] = 'Shuttle Rover'
        shuttle['PartGraph']['PartTransforms']['items'][1]['Translation'][0] = 111
        data = knowledge.collect([self.path, second], loader=lambda p: [
            ('CachedVehicles' if str(p)==str(self.path) else 'DownloadedVehicles', self.ref),
            ('CustomVehicles', shuttle)])
        self.assertEqual(data['summary']['reference_graphs'], 1)
        self.assertEqual(data['summary']['excluded_graphs'], 1)
        self.assertEqual(len(next(g for g in data['graphs'].values() if not g['excluded'])['locations']), 2)
        allowed = {g for g,r in data['graphs'].items() if not r['excluded']}
        self.assertTrue(all(e['graph'] in allowed for p in data['patterns'].values() for e in p['evidence']))

    def test_pair_placement_and_matching_are_invariant_under_rigid_3d_motion(self):
        pattern = self.library.candidates(61252, 2540, 2, 4)[0]
        anchor = dict(design=61252, pos=[321,-80,122], rot=geo.multiply(geo.quat_z(37), [0.5,0.5,0.5,0.5]))
        placed = self.library.place(anchor, pattern['id'])
        found = self.library.match(anchor, placed)
        self.assertEqual([(p['fa'],p['fb'],p['type']) for p in found], [(2,4,'CylindricalConnection')])
        inverse = self.library.match(placed, anchor)
        self.assertEqual([(p['fa'],p['fb']) for p in inverse], [(4,2)])
        placed['rot'] = [-x for x in placed['rot']]
        self.assertTrue(self.library.match(anchor, placed))
        placed['pos'] = [placed['pos'][0]+.5,*placed['pos'][1:]]
        self.assertFalse(self.library.match(anchor, placed))

    def test_different_scale_and_unseen_orientation_are_not_invented(self):
        pattern = self.library.candidates(61252,2540)[0]
        anchor = dict(design=61252, pos=[0,0,0], scale=[2,1,1])
        with self.assertRaisesRegex(ValueError, 'Skalierung'):
            self.library.place(anchor, pattern['id'])
        anchor['scale'] = [1,1,1]
        placed = self.library.place(anchor, pattern['id']); placed['rot'] = geo.quat_z(90)
        self.assertFalse(self.library.match(anchor,placed))

    def test_duplicate_edges_are_one_observation_and_export_has_no_owner_ids(self):
        v = copy.deepcopy(self.ref); v['OriginalCreatorId'] = 'SHOULD_NOT_BE_EXPORTED'
        v['PartGraph']['Connections']['items'] *= 2
        data = knowledge.collect([self.path], loader=lambda _: [('CustomVehicles',v)])
        self.assertEqual(len(data['patterns']),2)
        self.assertTrue(all(len(p['evidence'])==1 for p in data['patterns'].values()))
        self.assertNotIn('SHOULD_NOT_BE_EXPORTED',json.dumps(data))

    def test_builder_places_unknown_part_via_evidence_and_attaches_without_manual_edges(self):
        source = fixture_file(self.root/'source.sav')
        libpath = self.root/'knowledge.json'; libpath.write_text(json.dumps(self.data),encoding='utf-8')
        pid = self.library.candidates(3005,61252)[0]['id']
        body = [{'id':'base','teil':3005,'farbe':7,'pos':[-12.5,12.5,10]},
                {'id':'clip','teil':61252,'farbe':11,'anschluss':{'an':'base','vorlage':pid}}]
        before = source.read_bytes()
        save, report = builder.build_vehicle(source,plan(body,teilewissen=str(libpath)))
        self.assertFalse(report['lose_teile'])
        self.assertEqual(len(report['anschlusspruefung']['beobachtete_ergaenzungen']),1)
        v = next(v for v in builder.pool_from(save) if builder.text_value(v,'VehicleName')=='Ergebnis')
        tf = rw.val(rw.val(v,'PartGraph'),'PartTransforms').elems[report['referenzen']['clip']]
        self.assertEqual(struct.unpack('<fff',rw.val(tf,'Translation')),(-12.5,12.5,40))
        self.assertEqual(source.read_bytes(),before)

    def test_forward_dependency_is_resolved_and_cycles_fail(self):
        pid = self.library.candidates(3005,61252)[0]['id']
        parts = [{'id':'clip','teil':61252,'farbe':11,'anschluss':{'an':'base','vorlage':pid}},
                 {'id':'base','teil':3005,'farbe':7,'pos':[0,0,10]}]
        self.assertEqual(builder.place_parts(parts,{},self.library)[0]['pos'],(0,0,40))
        parts[1].pop('pos'); parts[1]['anschluss']={'an':'clip','vorlage':pid}
        with self.assertRaisesRegex(ValueError,'zyklisch'):
            builder.place_parts(parts,{},self.library)

    def test_fake_manual_contact_and_identical_solid_overlap_fail(self):
        source = fixture_file(self.root/'source.sav')
        far = plan([{'id':'far','teil':3005,'farbe':7,'pos':[10000,10000,10000]}],teilewissen=False,
                   verbindungen=[{'a':'chassis:0','b':'far','fa':1,'fb':1,'noppen':1}])
        with self.assertRaisesRegex(ValueError,'widerspricht'):
            builder.build_vehicle(source,far)
        overlap = plan([{'teil':3005,'farbe':color,'pos':[-12.5,12.5,10]} for color in (7,8)],teilewissen=False)
        with self.assertRaisesRegex(ValueError,'überlagern'):
            builder.build_vehicle(source,overlap)

    def test_availability_uses_all_locations_without_double_counting_graph(self):
        v = gvas.read_props(gvas.R(rw.write_props(fixture_vehicle())))
        def reader(path):
            return [('CachedVehicles' if path=='cache' else 'DownloadedVehicles',v)]
        for paths in (['cache','download'],['download','cache']):
            assets,chassis = sonderteile.beobachtungen(paths,reader)
            records = next(iter(chassis.values()))
            self.assertEqual(len(records),1)
            self.assertTrue(sonderteile.builder_info(records)['nutzbar'])

    def test_ball_connections_and_wrong_partner_fields_are_not_surface_evidence(self):
        vs = [auf_platte(name,(0,0,10)) for name in ('A','B')]
        for v in vs:
            v['PartGraph']['Connections']['items'][0]['Type']='ELegoConnectResult::BallConnection'
        self.assertNotEqual(bewerte(vs)['status'],'angenommen')
        for v in vs:
            c=v['PartGraph']['Connections']['items'][0]
            c['Type']='ELegoConnectResult::FixedConnection'; c['FieldIndexA']=99
        self.assertNotEqual(bewerte(vs)['status'],'angenommen')

    def test_only_tilted_contacts_do_not_confirm_rectangular_mask(self):
        vs=[auf_platte(name,(0,0,10)) for name in ('A','B')]
        for v in vs:
            v['PartGraph']['PartTransforms']['items'][1]['Rotation']=geo.quat_z(1.5)
        self.assertIsNone(bewerte(vs)['geom'])

    def test_upper_side_can_be_learned_with_tile_partner_having_no_top_face(self):
        vs=[fahrzeug(name,[(NEU,(0,0,0)),(3068,(0,0,10))],[(0,1,0,0,4)]) for name in ('A','B')]
        self.assertEqual(bewerte(vs)['geom']['oben'],0)

    def test_existing_learning_pipeline_excludes_only_shuttle_by_default(self):
        import anschluesse
        with mock.patch.object(anschluesse,'vehicles',side_effect=lambda _: iter([reference(),reference('Shuttle Rover')])):
            self.assertEqual([v['VehicleName'] for v in anschluesse.unique_vehicles(['synthetic'])],['Reference'])

    def test_conflicting_observations_do_not_create_two_incompatible_edges(self):
        data=copy.deepcopy(self.data)
        original=next(p for p in data['patterns'].values() if p['type']=='HingeConnection')
        conflict=copy.deepcopy(original); conflict['type']='FixedConnection'; conflict['strength']=2
        data['patterns']['conflicting']=conflict
        parts=knowledge.graph_parts(self.ref)
        matches=knowledge.Library(data).connect(parts)
        self.assertNotIn((0,1,0,1,1,'HingeConnection'),matches)
        self.assertNotIn((0,1,0,1,2,'FixedConnection'),matches)

    def test_preview_responds_to_special_part_translation_and_rotation(self):
        original = json.loads((ROOT/'baupläne/emerald_express.json').read_text(encoding='utf-8'))
        outputs=[]
        for mode in ('original','translated','rotated'):
            p=copy.deepcopy(original); target=next(t for t in p['teile'] if t['id']=='kessel_vorn')
            if mode=='translated': target['pos'][0]+=1000
            if mode=='rotated': target['rot']=[0,0,0,1]
            src=self.root/(mode+'.json'); dst=self.root/(mode+'.html')
            src.write_text(json.dumps(p),encoding='utf-8')
            subprocess.run([sys.executable,str(ROOT/'.claude/emerald-express/vorschau.py'),str(ROOT/'werkzeuge'),str(src),str(dst)],
                           check=True,capture_output=True)
            outputs.append(dst.read_bytes())
        self.assertNotEqual(outputs[0],outputs[1]); self.assertNotEqual(outputs[0],outputs[2])


if __name__=='__main__':
    unittest.main()

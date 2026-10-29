"""Offline-Tests für geom_kandidaten.py mit synthetischen Fahrzeugen (keine Spielstände)."""
import json
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'werkzeuge'))
import baugeometrie
import geom_kandidaten as gk

NEU = 999001  # Fiktive Teilenummer, Größe 4x2x1 Platte.
KANDIDAT = {NEU: [4, 2, 1]}


def fahrzeug(name, teile, verbindungen):
    return {'VehicleName': name, 'PartGraph': {
        'Parts': {'items': [struct.pack('<IBBBB', t[0], 0, 0, 0, 0).hex() for t in teile]},
        'PartTransforms': {'items': [{'Translation': list(t[1]), 'Rotation': list(t[2]) if len(t) > 2 else [0, 0, 0, 1],
                                      'Scale3D': [1, 1, 1]} for t in teile]},
        'Connections': {'items': [{'PartIndexA': a, 'PartIndexB': b, 'FieldIndexA': fa, 'FieldIndexB': fb,
                                   'Strength': n, 'Type': 'ELegoConnectResult::FixedConnection'}
                                  for a, b, fa, fb, n in verbindungen]}}}


def auf_platte(name, pos, feld=1, staerke=4):
    """Kandidat liegt auf einer 2x2-Platte 3022 (Oberseite Feld 0)."""
    return fahrzeug(name, [(3022, (0, 0, 0)), (NEU, pos)], [(0, 1, 0, feld, staerke)])


def unter_stein(name, feld=0):
    """Ein 2x2-Stein 3003 (Unterseite Feld 1) sitzt auf dem Kandidaten."""
    return fahrzeug(name, [(NEU, (0, 0, 0)), (3003, (0, 0, 10))], [(0, 1, feld, 1, 4)])


def bewerte(vehicles, teile=None):
    return gk.analysiere(vehicles, KANDIDAT, teile or {NEU: {'groesse': [4, 2, 1], 'aliase': [NEU]}})[0]


class GeomKandidatenTests(unittest.TestCase):
    def test_fields_and_stud_counts_from_full_and_partial_contact(self):
        e = bewerte([auf_platte('A', (0, 0, 10)), auf_platte('B', (0, 25, 10), staerke=2),
                     unter_stein('C'), unter_stein('D')])
        self.assertEqual(e['status'], 'angenommen')
        self.assertEqual(e['geom'], dict(l=4, w=2, h=10, unten=1, oben=0))
        self.assertEqual(e['gegentest'], {'exakt': 4, 'vorhergesagt': 4})

    def test_one_contact_is_not_enough(self):
        e = bewerte([auf_platte('A', (0, 0, 10))])
        self.assertEqual((e['status'], e['geom']), ('zu_wenig_belege', None))

    def test_wrong_stud_count_or_mixed_fields_are_contradictions(self):
        e = bewerte([auf_platte('A', (0, 0, 10), staerke=3), auf_platte('B', (0, 0, 10))])
        self.assertEqual(e['status'], 'widerspruechlich')
        e = bewerte([auf_platte('A', (0, 0, 10), feld=1), auf_platte('B', (0, 0, 10), feld=2)])
        self.assertEqual(e['status'], 'widerspruechlich')

    def test_slightly_turned_contact_only_supports_the_field(self):
        schief = fahrzeug('S', [(3022, (0, 0, 0)), (NEU, (0, 0, 10), baugeometrie.quat_z(1.5))], [(0, 1, 0, 1, 4)])
        self.assertFalse(gk.im_raster([0, 0, 0, 1], baugeometrie.quat_z(1.5)))
        self.assertTrue(gk.im_raster(baugeometrie.quat_z(90), baugeometrie.quat_z(180)))
        e = bewerte([auf_platte('A', (0, 0, 10)), auf_platte('B', (0, 0, 10)), schief])
        self.assertEqual((e['status'], e['seiten']['unten']['schief'], e['seiten']['unten']['noppenzahl_abweichend']),
                         ('angenommen', 1, 0))
        self.assertEqual(e['gegentest'].get('schief_uebersprungen'), 1)

    def test_alias_needs_one_matching_contact(self):
        teile = {NEU: {'groesse': [4, 2, 1], 'aliase': [NEU]},
                 3020: {'groesse': [4, 2, 1], 'aliase': [3020, NEU]}}
        e = bewerte([auf_platte('A', (0, 0, 10))], teile)
        self.assertEqual((e['status'], e['alias_von'], e['geom']['unten']), ('angenommen', 3020, 1))
        e = bewerte([auf_platte('A', (0, 0, 10), feld=0)], teile)
        self.assertEqual(e['status'], 'widerspruechlich')

    def test_temporary_geometry_does_not_leak(self):
        before = dict(baugeometrie.GEOM)
        bewerte([auf_platte('A', (0, 0, 10)), auf_platte('B', (0, 0, 10))])
        self.assertEqual(baugeometrie.GEOM, before)
        self.assertNotIn(NEU, baugeometrie.GEOM)

    def test_simple_geom_entries_match_part_sizes(self):
        teile = {int(k): v for k, v in json.loads((ROOT / 'teiledaten.json').read_text(encoding='utf-8')).items()}
        for d, g in baugeometrie.GEOM.items():
            if gk.EINFACH.match(teile[d]['name'] or '') and not any(k.endswith('_zellen') for k in g):
                l, w, h = teile[d]['groesse']
                self.assertEqual((g['l'], g['w'], g['h']), (l, w, h * 10), d)
                self.assertNotEqual(g['unten'] if g['unten'] is not None else -1, g['oben'], d)

    def test_mudguard_98282_has_2x2_studs_on_top_toward_plus_y(self):
        # Belegt durch .claude/maske-98282-belege.json: oben 2x2 Richtung +y, unten 2x1.
        def staerke(platte_y):
            teile = [dict(design=98282, pos=(0, 0, 0)), dict(design=3022, pos=(0, platte_y, 30))]
            return [n for *_, n in baugeometrie.connect(teile)]
        self.assertEqual(staerke(25), [4])
        self.assertEqual(staerke(0), [2])
        self.assertEqual(staerke(-25), [])


if __name__ == '__main__':
    unittest.main()

"""Offline-Tests für sonderteile.py und das Lesen des Creators-Hub-Caches in anschluesse.py."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'werkzeuge'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import anschluesse
import gvas
import gvas_rw as g
import sonderteile
from test_builder import fixture_file, fixture_vehicle

CAR = '/Game/Game/Vehicle/Inventory/CarChassisConfigs/'
BOAT = '/Game/Game/Vehicle/Inventory/BoatChassisConfigs/'


def gesehen(liste, fahrzeug, name='fl', teile=(6014, 6015), datei='ArtemisVehicle.sav'):
    return {'datei': datei, 'liste': liste, 'fahrzeug': fahrzeug, 'baugruppenname': name, 'teile': list(teile)}


def katalog(enz=None, live=None, assets=None, chassis=None, teile=None):
    return sonderteile.erzeuge_katalog(enz or {}, live or {}, assets or {}, chassis or {},
                                       teile or {6014: 'RIM', 6015: 'TYRE'})


class KatalogTests(unittest.TestCase):
    def test_belegt_and_assumptions_are_separated(self):
        k = katalog({'wheels': {'6014_6015_New': {'id': '6014_6015_New', 'name': '6014_6015_New', 'is_surplus': False,
                                                  'sources': [{'type': 'brickpack', 'name': 'Default', 'biome': None,
                                                               'rewards': {str(i): 1 for i in range(500)}}]}}},
                    {'/Game/LEGO/Wheel/': ['6014_6015_New', '6014_6015_New/Thumb']},
                    {('Wheel', '6014_6015_New'): [gesehen('CustomVehicles', 'Basis'), gesehen('CustomVehicles', 'Basis', 'fr')]})
        e = k['raeder']['6014_6015_New']
        self.assertEqual(e['belegt']['im_spiel'], '/Game/LEGO/Wheel/6014_6015_New')
        self.assertEqual(e['belegt']['enzyklopaedie']['freischaltung'], [['brickpack', 'Default', None]])
        self.assertEqual(e['belegt']['in_fahrzeugen']['anzahl'], 1)
        self.assertEqual(e['belegt']['in_fahrzeugen']['fahrzeuge'][0]['baugruppennamen'], ['fl', 'fr'])
        self.assertEqual([x['nummer'] for x in e['annahmen']['lego_teile_aus_namen']], [6014, 6015])
        self.assertNotIn('anzeigename', e['annahmen'])  # Name gleich ID ist kein Anzeigename.
        self.assertTrue(e['builder']['nutzbar'])
        self.assertEqual(k['zusammenfassung']['raeder']['gesamt'], 1)  # Vorschaubild-Unterordner zählt nicht.

    def test_game_only_and_save_only_entries_are_kept_and_marked(self):
        k = katalog(live={'/Game/LEGO/Wheel/': ['NeuesRad']},
                    assets={('Wheel', 'Unbekannt_1'): [gesehen('CachedVehicles', 'Hub', datei='ArtemisChubCache.sav')]})
        self.assertTrue(k['raeder']['NeuesRad']['nur_im_spiel'])
        self.assertFalse(k['raeder']['NeuesRad']['builder']['nutzbar'])
        nur = k['raeder']['Unbekannt_1']
        self.assertTrue(nur['nur_in_spielstaenden'])
        self.assertFalse(nur['builder']['nutzbar'])  # Cache-Fahrzeuge liest baue_fahrzeug.py nicht.
        self.assertIn('herunterladen', nur['builder']['hinweis'])

    def test_flair_prefix_matches_once(self):
        k = katalog({'flairs': {'Kringle_4k': {'id': 'Kringle_4k', 'name': 'Kringle (new!)', 'rarity': 'Awesome',
                                               'garage_cost': None, 'is_surplus': True, 'sources': []}}},
                    {'/Game/LEGO/Flair/': ['Flair_Kringle_4k']},
                    {('Flair', 'Flair_Kringle_4k'): [gesehen('DownloadedVehicles', 'X', 'None', (3001,))]})
        self.assertEqual(list(k['flairs']), ['Kringle_4k'])
        e = k['flairs']['Kringle_4k']
        self.assertEqual(e['annahmen']['anzeigename'], 'Kringle')
        self.assertTrue(e['annahmen']['spaeter_ergaenzt'])
        self.assertEqual(e['belegt']['enzyklopaedie']['rarity'], 'Awesome')
        self.assertNotIn('garage_cost', e['belegt']['enzyklopaedie'])
        self.assertTrue(e['builder']['nutzbar'])

    def test_chassis_class_from_folder_and_ambiguous_package_is_not_belegt(self):
        enz = {'chassis': {
            'Sedan_60050_Garage': {'id': 'Sedan_60050_Garage', 'name': 'Straight & Narrow', 'terrain': 'Street',
                                   'stats': None, 'default_engine': 'EngineConfig_HondaCivic'},
            'Fanboat': {'id': 'Fanboat', 'name': 'Fanboat', 'terrain': 'Boat',
                        'stats': {'TopSpeed': 0.01}, 'default_engine': None},
            'Doppelt': {'id': 'Doppelt', 'name': 'Doppelt', 'terrain': 'Boat', 'stats': None, 'default_engine': None}}}
        live = {CAR: ['ChassisConfig_Sedan_60050_Garage', 'ChassisConfig_Doppelt'],
                BOAT: ['ChassisConfig_Fanboat', 'ChassisConfig_Doppelt']}
        beob = {'ChassisConfig_Sedan_60050_Garage': [{'datei': 'ArtemisVehicle.sav', 'liste': 'CustomVehicles',
                                                       'fahrzeug': 'Neues Fahrzeug 09', 'fahrzeugklasse': 'CAR',
                                                       'motor': None, 'chassis_baugruppen': ['Sedan']}]}
        k = katalog(enz, live, chassis=beob)['chassis']
        self.assertEqual(k['Sedan_60050_Garage']['annahmen'], {'anzeigename': 'Straight & Narrow', 'fahrzeugklasse': 'CAR',
                                                               'garagen_startchassis': True})
        self.assertEqual(k['Sedan_60050_Garage']['belegt']['in_fahrzeugen']['fahrzeuge'][0]['fahrzeug'], 'Neues Fahrzeug 09')
        self.assertEqual(k['Fanboat']['annahmen']['fahrzeugklasse'], 'BOAT')
        self.assertEqual(k['Fanboat']['belegt']['enzyklopaedie']['stats'], {'TopSpeed': 0.01})
        self.assertNotIn('im_spiel', k['Doppelt']['belegt'])
        self.assertNotIn('Doppelt', [i for i, e in k.items() if e.get('nur_im_spiel')])

    def test_missing_game_lists_leave_im_spiel_empty(self):
        k = katalog({'propellers': {'P': {'id': 'P', 'name': 'P', 'is_surplus': True, 'sources': []}}})
        self.assertEqual(k['zusammenfassung']['propeller'],
                         {'gesamt': 1, 'mit_enzyklopaedie': 1, 'im_spiel_belegt': 0,
                          'in_fahrzeugen_beobachtet': 0, 'builder_nutzbar': 0})


    def test_vehicle_list_flags_unobserved_chassis(self):
        chassis = katalog({'chassis': {'A': {'id': 'A', 'name': 'A', 'terrain': 'Street', 'stats': None,
                                             'default_engine': None}}},
                          chassis={'ChassisConfig_A': [{'datei': 'x.sav', 'liste': 'DownloadedVehicles', 'fahrzeug': 'F'}]})['chassis']
        liste = sonderteile.fahrzeugliste({'V1': {'name': 'Flitzer (new!)', 'chassis': 'A', 'garage_valid': 'Valid'},
                                           'V2': {'name': 'V2', 'chassis': 'B', 'garage_valid': 'NotConnected'}}, chassis)
        self.assertEqual((liste['V1']['chassis_in_spielstaenden'], liste['V1']['chassis_als_vorlage_nutzbar']), (True, True))
        self.assertEqual(liste['V1']['annahmen'], {'anzeigename': 'Flitzer'})
        self.assertEqual((liste['V2']['chassis_in_spielstaenden'], liste['V2']['annahmen']), (False, {}))


    def test_copy_list_prefers_unseen_heavy_and_distinct_families(self):
        def fz(terrain, gewicht, gesehen=False, valid='Valid', name='X'):
            return {'belegt': {'enzyklopaedie': {'terrain': terrain, 'weight_estimation': gewicht,
                                                 'garage_valid': valid, 'chassis': 'c'}},
                    'annahmen': {'anzeigename': name} if name else {}, 'chassis_in_spielstaenden': gesehen}
        fahrzeuge = {'FusionBoat_VC000': fz('Boat', 900), 'FusionOffroad_VC000': fz('Offroad', 800),
                     'Klein_VC000': fz('Offroad', 100), 'Bekannt_VC000': fz('Offroad', 990, gesehen=True),
                     'Kaputt_VC000': fz('Offroad', 980, valid='NotConnected'), 'Namenlos_VC000': fz('Offroad', 970, name=None),
                     'RivalFusionStreetCar_VC0000': fz('Street', 700), 'Strasse_60200': fz('Street', 50)}
        self.assertEqual(sonderteile.familie('RivalFusionStreetCar_VC0000'), 'fusion')
        self.assertEqual([x['id'] for x in sonderteile.kopierliste(fahrzeuge, 4)],
                         ['FusionBoat_VC000', 'Strasse_60200', 'Klein_VC000'])
        self.assertEqual(len(sonderteile.kopierkandidaten(fahrzeuge)), 5)
        self.assertEqual([x['id'] for x in sonderteile.kopierliste(fahrzeuge, 4, boote=False)],
                         ['RivalFusionStreetCar_VC0000', 'Strasse_60200', 'Klein_VC000'])
        self.assertEqual(len(sonderteile.kopierkandidaten(fahrzeuge, boote=False)), 4)
        self.assertIn('| ☐ | 1 | X | Boot | 900 | `FusionBoat_VC000` |',
                      sonderteile.kopierliste_md(sonderteile.kopierliste(fahrzeuge, 4), 2))


    def test_coverage_list_picks_most_new_widespread_parts_first(self):
        def fz(terrain, name='X', valid='Valid'):
            return {'belegt': {'enzyklopaedie': {'terrain': terrain, 'garage_valid': valid}},
                    'annahmen': {'anzeigename': name} if name else {}, 'chassis_in_spielstaenden': True}
        fahrzeuge = {'A': fz('Street'), 'B': fz('Offroad'), 'C': fz('Street'), 'Boot': fz('Boat'),
                     'Kaputt': fz('Street', valid='NotConnected'), 'Leer': fz('Street', name=None)}
        teile = {'A': {1, 2, 3}, 'B': {3, 4}, 'C': {4, 5}, 'Boot': {9, 8, 7, 6}, 'Kaputt': {11, 12, 13, 14},
                 'Leer': {15, 16, 17, 18}}
        liste, stats = sonderteile.abdeckungsliste(fahrzeuge, teile, beobachtet={1}, anzahl=5, boote=False)
        # 4 steckt in B und C und wiegt doppelt; A bringt 2, 3 (3 auch in B); danach C mit 5.
        self.assertEqual([(x['id'], x['neue_teile']) for x in liste], [('B', 2), ('A', 1), ('C', 1)])
        self.assertEqual((stats['kandidaten'], stats['offen'], stats['danach_offen'], stats['verwendungen_abgedeckt_prozent']),
                         (3, 4, 0, 100))
        self.assertIn('| ☐ | 1 | Collection | X | Gelände | 2 | `B` |', sonderteile.abdeckungsliste_md(liste, stats))
        self.assertEqual(sonderteile.garagen_reiter({'license': 'LEGOSpeedChampions'}), 'Speed Champions')
        self.assertEqual(sonderteile.garagen_reiter({'license': None}), 'Collection')


class SpielstandTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.save = fixture_file(Path(self.temp.name) / 'ArtemisVehicle.sav')
        real_load = gvas.load
        cache_bytes = g.write_props(fixture_vehicle('Hub-Modell')).hex()

        def load_with_cache(path):
            data = real_load(path)
            data['body']['Data']['CachedVehicles'] = [['abc', {'Bytes': {'_bytes': cache_bytes}}]]
            return data
        self.patch = mock.patch.object(anschluesse.gvas, 'load', side_effect=load_with_cache)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()

    def test_cached_vehicles_are_read_and_identical_graphs_counted_once(self):
        listen = [(liste, v['VehicleName']) for liste, v in anschluesse.vehicles_with_source(str(self.save))]
        self.assertEqual(listen, [('CustomVehicles', 'Basis'), ('CachedVehicles', 'Hub-Modell')])
        self.assertEqual(len(list(anschluesse.unique_vehicles([str(self.save), str(self.save)]))), 1)
        self.assertEqual(anschluesse.expand([str(Path(self.temp.name) / '*.sav'), 'fehlt.sav']), [str(self.save), 'fehlt.sav'])
        with mock.patch('builtins.print'):
            result = anschluesse.main([str(self.save)])
        self.assertIn(2445, result)

    def test_observations_group_wheels_and_mark_builder_lists(self):
        assets, chassis = sonderteile.beobachtungen([str(self.save)], anschluesse.vehicles_with_source)
        rad = assets[('Wheel', '56902_61254_New')]
        self.assertEqual({b['baugruppenname'] for b in rad}, {'fl', 'fr', 'bl', 'br'})
        self.assertEqual(len(rad), 4)  # Hub-Kopie mit gleichem Teilegraph wird nicht doppelt gezählt.
        info = chassis['ChassisConfig_FireEngine_10263_Garage'][0]
        self.assertEqual((info['liste'], info['motor'], info['chassis_baugruppen']),
                         ('CustomVehicles', None, ['FireEngineChassis_10263']))
        self.assertEqual(sonderteile.gekuerzt(rad)['anzahl'], 1)


class DatenTests(unittest.TestCase):
    def test_teiledaten_cover_every_encyclopedia_brick(self):
        enz = json.loads((ROOT / '.claude/quellen/l2kd-encyclopedia/bricks_by_id.json').read_text(encoding='utf-8'))
        teile = json.loads((ROOT / 'teiledaten.json').read_text(encoding='utf-8'))
        self.assertEqual(set(enz), set(teile))

    @unittest.skipUnless((ROOT / 'sonderteile.json').exists(), 'sonderteile.json noch nicht erzeugt')
    def test_generated_catalog_has_consistent_shape(self):
        k = json.loads((ROOT / 'sonderteile.json').read_text(encoding='utf-8'))
        for kategorie in sonderteile.KATEGORIEN:
            self.assertEqual(k['zusammenfassung'][kategorie]['gesamt'], len(k[kategorie]))
            for e in k[kategorie].values():
                self.assertEqual({'belegt', 'annahmen', 'builder'} - set(e), set())
                beob = e['belegt'].get('in_fahrzeugen', {'anzahl': 0, 'fahrzeuge': []})
                direkt = any(f['liste'] != 'CachedVehicles' for f in beob['fahrzeuge'])
                if direkt or beob['anzahl'] <= sonderteile.MAX_FAHRZEUGE:
                    self.assertEqual(e['builder']['nutzbar'], direkt)


if __name__ == '__main__':
    unittest.main()

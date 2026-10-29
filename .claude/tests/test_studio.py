"""Security boundaries of the data-only Studio reader; never opens a design app."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'werkzeuge'))
import pruefe_studio as studio

LINE = '1 0 0 0 0 1 0 0 0 1 0 0 0 1 3005.dat\n'


class StudioReaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name)/'test.io'

    def tearDown(self):
        self.tmp.cleanup()

    def archive(self, entries=None, line=LINE, total=1):
        data = {'.info': json.dumps({'total_parts': total}), 'model.ldr': line}
        data.update(entries or {})
        with zipfile.ZipFile(self.path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            for name, content in data.items():
                z.writestr(name, content)

    def test_minimal_model_is_read_without_extracting_any_archive_path(self):
        self.archive()
        data, _ = studio.read_archive(self.path)
        self.assertEqual(len(data['parts']), 1)
        self.assertEqual(data['parts'][0]['referenz'], '3005.dat')
        self.assertEqual(sorted(x.name for x in self.path.parent.iterdir()), ['test.io'])

    def test_traversal_entry_is_rejected(self):
        self.archive({'../evil.py': 'print("not run")'})
        with self.assertRaisesRegex(ValueError, 'Archiveintrag'):
            studio.read_archive(self.path)

    def test_executable_entry_or_disguised_pe_is_rejected(self):
        self.archive({'run.exe': b'MZfake'})
        with self.assertRaises(ValueError):
            studio.read_archive(self.path)
        self.archive({'model.lxfml': b'MZfake'})
        with self.assertRaisesRegex(ValueError, 'ausführbare'):
            studio.read_archive(self.path)

    def test_xml_external_entity_declaration_is_rejected(self):
        self.archive({'model.lxfml': '<!DOCTYPE LXFML [<!ENTITY x SYSTEM "file:///private">]><LXFML>&x;</LXFML>'})
        with self.assertRaisesRegex(ValueError, 'Entitäten'):
            studio.read_archive(self.path)

    def test_network_or_parent_model_reference_is_rejected(self):
        for target in ['https://example.test/evil.dat', '../evil.dat', 'C:/evil.dat', 'evil.exe']:
            with self.assertRaises(ValueError):
                studio.parse_ldr(LINE.replace('3005.dat', target).encode())

    def test_nonfinite_coordinates_are_rejected(self):
        with self.assertRaises(ValueError):
            studio.parse_ldr(LINE.replace('0 0 0 1', 'nan 0 0 1', 1).encode())

    def test_declared_part_count_must_match(self):
        self.archive(total=2)
        with self.assertRaisesRegex(ValueError, 'Teilezahl'):
            studio.read_archive(self.path)

    def test_letter_variants_remain_unconfirmed(self):
        catalog = {3023: {'aliase': [3023]}}
        result = studio.map_part('3023b.dat', catalog)
        self.assertEqual(result['status'], 'buchstabenvariante_unbestaetigt')
        self.assertEqual(result['kandidaten'], [3023])
        self.assertEqual(studio.map_part('unknown.dat', catalog)['status'], 'nicht_zugeordnet')

    def test_studio_short_edges_are_only_accepted_in_embedded_geometry(self):
        edge = b'5 -2 0 0 0 1 1 1\n'
        studio.parse_ldr(edge, geometry=True)
        with self.assertRaises(ValueError):
            studio.parse_ldr(edge)


if __name__ == '__main__':
    unittest.main()

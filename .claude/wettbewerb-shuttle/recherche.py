"""Read-only local part/contact investigation for the independent competition design."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'werkzeuge'))
from teilewissen import Library
from baugeometrie import GEOM

lib = Library.load()
catalog = json.loads((ROOT / 'teiledaten.json').read_text(encoding='utf8'))
if len(sys.argv) == 1:
    for k, v in catalog.items():
        if any(x in (v['name'] or '') for x in ['WING', 'COCKPIT', 'CONE', '4X4 ROUND', '4X4X2']):
            print(k, v['name'], 'observed=', k in lib.data['parts'])
else:
    for value in sys.argv[1:]:
        tokens = value.split(':')
        design = int(tokens[0])
        print('\nPART', design, catalog.get(str(design)))
        pp = lib.candidates(design, int(tokens[1]) if len(tokens) > 1 else None)
        if len(tokens) == 1:
            from collections import Counter
            print('PARTNERS', dict(Counter(p['b'] for p in pp)))
            continue
        for p in pp:
            if len(tokens) > 1:
                print(p['id'], p['fa'], '<->', p['b'], p['fb'], p['strength'], p['type'],
                      {k: [round(x, 3) for x in v] for k, v in p['relative'].items()})

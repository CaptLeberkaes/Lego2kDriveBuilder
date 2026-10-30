"""Independent ASTRA design. Only writes the plan and sanitized review artefacts.

Run from the repository root: python .claude/wettbewerb-shuttle/entwurf.py
Never opens the old Shuttle Rover blueprint and never writes a game save.
"""
import collections
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'werkzeuge'))
import baue_fahrzeug as builder
import gvas_rw as g
from baugeometrie import quat_z, multiply, rotate
from teilewissen import Library

NAME = 'ASTRA Launch Crawler'
PLAN = ROOT / 'baupläne/astra_launch_crawler.json'
SOURCE = Path(os.path.expandvars(r'%USERPROFILE%/Documents/My Games/Artemis/Saved/SaveGames/ArtemisVehicle.sav'))
lib = Library.load()
parts = []
groups = {}
poses = {}
chosen = {}

def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf8')

def add(name, design, color, pos=None, yaw=0, rot=None, contact=None, group='Plattform'):
    p = dict(id=name, teil=design, farbe=color)
    if contact:
        p['anschluss'] = dict(an=contact[0], vorlage=contact[1])
        pose = lib.place(poses[contact[0]], contact[1])
        chosen[contact[1]] = lib.data['patterns'][contact[1]]
    else:
        p.update(pos=list(pos), rot=list(rot or quat_z(yaw)))
        pose = dict(design=design, pos=pos, rot=p['rot'], scale=[1, 1, 1])
    parts.append(p)
    poses[name] = pose
    groups[name] = group
    return name

# The Eileen / PoliceTruck base is copied by the builder, including its four wheels.
# Two overlapping plate courses tie the deck together without moving chassis parts.
add('deck_unten', 3030, 12, [-112.5, 37.5, 50])
add('deck_oben', 3036, 12, [-87.5, 62.5, 60])
add('heckstufe', 3020, 11, [-162.5, 12.5, 70])
for side, y in [('links', 62.5), ('rechts', -62.5)]:
    add('rand_' + side, 3460, 9, [-87.5, y, 70])
    for j, x in enumerate([-87.5, -37.5, 12.5, 62.5]):
        add(f'warnstreifen_{side}_{j}', 3070, 11, [x, y, 80])
add('licht_links', 6141, 20, [87.5, 37.5, 70])
add('licht_rechts', 6141, 20, [87.5, -37.5, 70])

# Compact external tank: true 2x2 cylinders and a true cone, 4-stud bottom contact.
add('tank_sockel_1', 3022, 11, [-50, 12.5, 70], group='Außentank')
add('tank_sockel_2', 3020, 12, [-100, 12.5, 80], group='Außentank')
add('tank_00', 6143, 27, contact=('tank_sockel_2', 'c7a1e80f9cd423729a34a5be'), group='Außentank')
for i in range(1, 10):
    add(f'tank_{i:02}', 6143, 27, [-50, 12.5, 90 + i * 30], group='Außentank')
add('tank_spitze', 3942, 27, contact=('tank_09', '3337cfd128f9133824539d9c'), group='Außentank')

# Two slim solid boosters. The small cone is the observed 59900 variant, not a guessed alias.
for side, y in [('links', 37.5), ('rechts', -37.5)]:
    add('booster_fuss_' + side, 6141, 68, [-62.5, y, 70], group='Booster')
    for i in range(10):
        add(f'booster_{side}_{i:02}', 3062, 11 if i in (0, 8) else 24,
            [-62.5, y, 80 + 30 * i], group='Booster')
    cap = add('booster_kappe_' + side, 3024, 24, [-62.5, y, 380], group='Booster')
    add('booster_spitze_' + side, 59900, 24,
        contact=(cap, '2667b926116b341fc850f91d'), group='Booster')

# A narrow black spine immediately beside the tank. Side studs face +world-x.
# Two independently observed side contacts support the upright orbiter.
for i in range(10):
    z = 70 + 30 * i
    add(f'traeger_{i:02}', 11211 if i in (4, 9) else 3004, 11,
        [0, 12.5, z], yaw=-90, group='Orbiterhalter')
for i in (4, 9):
    add(f'snot_adapter_{i}', 3023, 11,
        contact=(f'traeger_{i:02}', '33c780896710cba3ffb818fa'), group='Orbiterhalter')

# Local orbiter coordinates: +x toward the nose, +z dorsal.
# This proper rotation maps its nose upwards and dorsal surface forwards.
Q = (math.sqrt(.5), 0, math.sqrt(.5), 0)
O = (12.5, 0, 132.5)
def orb(name, design, color, pos, yaw=0):
    world = tuple(a+b for a,b in zip(O, rotate(Q, pos)))
    return add(name, design, color, world, rot=multiply(Q, quat_z(yaw)), group='Orbiter')

orb('fluegelholm', 3710, 11, [75, 37.5, 10], -90)
orb('fluegelholm_vorn', 3710, 11, [100, 37.5, 10], -90)
add('delta_rechts', 54383, 24,
    contact=('fluegelholm', 'bf4622d0d455e9bb2f4d8216'), group='Orbiter')
add('delta_links', 54384, 24,
    contact=('fluegelholm', 'beff3b53af4ccb857241773d'), group='Orbiter')
orb('oberer_adapterholm', 3023, 11, [225, 12.5, 10], -90)
orb('bauch_hinten', 3034, 11, [0, 12.5, 20])
orb('bauch_vorn', 3020, 11, [200, 12.5, 20])
orb('rumpfverbinder', 3795, 24, [125, 12.5, 30])
orb('heckbasis', 3022, 24, [0, 12.5, 30])
orb('mittelbasis', 3021, 24, [50, 12.5, 30])
# Rear engines mount on true side-stud bricks. Circular nozzle rims face down in world space.
for side, y in [('links', 12.5), ('rechts', -12.5)]:
    anchor = orb('duesenhalter_' + side, 87087, 24, [0, y, 40], 90)
    add('duese_' + side, 6141, 68,
        contact=(anchor, '0885e6ad6653d701cdde7191'), group='Orbiter')
orb('rumpf_hinten', 3002, 24, [25, 12.5, 40])
orb('rumpf_mitte', 3001, 24, [100, 12.5, 40])
orb('cockpit_unterbau', 3003, 24, [200, 12.5, 40])
for side, y in [('links', 12.5), ('rechts', -12.5)]:
    orb('nase_' + side, 3040, 24, [250, y, 40], 270)
    orb('cockpit_fenster_' + side, 3040, 29, [225, y, 70], 270)
orb('cockpit_rueckwand', 3004, 24, [200, 12.5, 70], -90)
orb('cockpit_dach', 3023, 24, [200, 12.5, 100], -90)
orb('laderaum_vorn', 87079, 24, [100, 12.5, 70])
orb('laderaum_hinten', 3068, 24, [50, 12.5, 70])
# A swept vertical stabilizer, two studs thick at this micro scale.
orb('leitwerk_fuss', 3003, 24, [0, 12.5, 70])
for side, y in [('links', 12.5), ('rechts', -12.5)]:
    orb('leitwerk_schraege_' + side, 3040, 24, [25, y, 100], 270)
orb('leitwerk_spitze', 3023, 11, [0, 12.5, 100], -90)

# A driver seat is on the free rear service step, facing away from the launch stack.
add('fahrersitz', 4079, 11, contact=('heckstufe', '04d83c2ede16255da44ef068'), group='Plattform')
# Align the independently designed launch stack with the fixed chassis stud grid.
for p in parts:
    if groups[p['id']] in ('Außentank', 'Orbiterhalter', 'Orbiter') and 'pos' in p:
        p['pos'][0] -= 12.5
plan = dict(name=NAME, vorlage_name='Brute Chopper',
            vorlage_datei='%USERPROFILE%/Documents/My Games/Artemis/Saved/SaveGames/ArtemisDownloadedVehicle.sav', teile=parts,
            fahrer=dict(teil='fahrersitz', pos=[0, 0, 10], dreh=[0, 0, 0]))
write(PLAN, plan)
write(HERE / 'gruppen.json', groups)
write(HERE / 'gewaehlte-kontakte.json', chosen)

if __name__ == '__main__':
    before = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    save, report = builder.build_vehicle(str(SOURCE), plan)
    raw = save.dump()
    assert g.SaveFile.from_bytes(raw).dump() == raw
    assert before == hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    write(HERE / 'builder-pruefung.json', report)
    # Sanitized final graph: no creator IDs, GUIDs or other player's save data.
    vehicle = g.val(g.val(save.props, 'Data'), 'CustomVehicles').elems[report['slot']]
    graph = g.val(vehicle, 'PartGraph')
    ps = g.val(graph, 'Parts').elems
    tfs = g.val(graph, 'PartTransforms').elems
    geometry = [dict(index=i, design=struct.unpack('<I', p[:4])[0], color=p[4], flags=p[5],
                     pos=list(struct.unpack('<fff', g.val(tf, 'Translation'))),
                     rot=list(struct.unpack('<ffff', g.val(tf, 'Rotation'))),
                     scale=list(struct.unpack('<fff', g.val(tf, 'Scale3D'))))
                for i,(p,tf) in enumerate(zip(ps,tfs))]
    write(HERE / 'gebauter-graph.json', dict(parts=geometry,
          assemblies=[dict(asset=builder.text_value(a,'AssemblyAsset'),
                           name=builder.text_value(a,'AssemblyName'), indices=builder.indices(a))
                      for a in g.val(graph,'Assemblies').elems],
          connections=[dict(a=builder.connection_indices(c)[0], b=builder.connection_indices(c)[1],
                            fa=g.val(c,'FieldIndexA')[0], fb=g.val(c,'FieldIndexB')[0],
                            strength=g.val(c,'Strength')[0], type=builder.text_value(c,'Type'))
                       for c in g.val(graph,'Connections').elems]))
    write(HERE / 'sicherheit.json', dict(source=SOURCE.name, sha256_before=before, sha256_after=before,
          sav_written=False, serialization_roundtrip=True, plan_sha256=hashlib.sha256(PLAN.read_bytes()).hexdigest()))
    print(NAME, len(parts), 'body parts;', report['teile'], 'total;', report['verbindungen'], 'connections')

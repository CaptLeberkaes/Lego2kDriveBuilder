"""Second ASTRA model: tank, boosters and orbiter all point forward (+world X).

Offline only. Reuses model 1's own orbiter design, never its script (which writes
outputs on import), and never modifies model 1 or any game save.
"""
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'werkzeuge'))
import baue_fahrzeug as b
import gvas_rw as g
from baugeometrie import rotate,multiply,quat_z
from teilewissen import Library

def write(path,data): path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
M1_PATHS=[ROOT/'baupläne'/n for n in ['astra_launch_crawler.json','astra_launch_crawler_vorschau.html','astra_launch_crawler_vorschau.png']]
M1_PATHS += [p for p in HERE.parent.iterdir() if p.is_file()]
model1_before={str(p.relative_to(ROOT)):sha(p) for p in M1_PATHS}
if not (HERE/'modell-1-ausgangshashes.json').exists():
    write(HERE/'modell-1-ausgangshashes.json',model1_before)

lib=Library.load();parts=[];groups={};poses={}
def add(name,design,color,pos=None,yaw=0,rot=None,contact=None,group='Plattform'):
    p=dict(id=name,teil=design,farbe=color)
    if contact:
        p['anschluss']=dict(an=contact[0],vorlage=contact[1])
        pose=lib.place(poses[contact[0]],contact[1])
    else:
        p.update(pos=list(pos),rot=list(rot or quat_z(yaw)))
        pose=dict(design=design,pos=p['pos'],rot=p['rot'],scale=[1,1,1])
    parts.append(p);groups[name]=group;poses[name]=pose
    return name

# Native PoliceTruck / Eileen chassis and wheels remain unchanged.
add('deck_unten',3030,12,[-112.5,37.5,50])
add('deck_oben',3036,12,[-87.5,62.5,60])
add('transportdeck_hinten',3036,12,[-212.5,62.5,70])
for side,y in [('links',62.5),('rechts',-62.5)]:
    add('rand_vorn_'+side,3710,9,[12.5,y,70])
    for i,x in enumerate([12.5,62.5]):
        add(f'warnstreifen_{side}_{i}',3070,11,[x,y,80])
for side,y in [('links',37.5),('rechts',-37.5)]:
    add('scheinwerfer_'+side,6141,20,[87.5,y,70])

# Genuine bracket at the tank's rear. The actual observed pair defines tank axis and height.
add('tank_winkel_unterlage',3023,11,[-212.5,12.5,80],yaw=-90,group='Außentank')
add('tank_winkel',3956,12,contact=('tank_winkel_unterlage','1b8a2c938346c4c35e59c933'),group='Außentank')
add('tank_00',6143,27,contact=('tank_winkel','a513b8991973b25bb5058b1f'),group='Außentank')
first=poses['tank_00']
axis=rotate(first['rot'],(0,0,1))
assert abs(axis[0]-1)<1e-5 and abs(axis[1])+abs(axis[2])<1e-5
for i in range(1,10):
    add(f'tank_{i:02}',6143,27,[first['pos'][j]+30*i*axis[j] for j in range(3)],rot=first['rot'],group='Außentank')
add('tank_spitze',3942,27,contact=('tank_09','3337cfd128f9133824539d9c'),group='Außentank')

# The boosters are horizontal too, using two independent, observed side-stud end mounts.
for side,y in [('links',62.5),('rechts',-62.5)]:
    for i in range(2):
        add(f'booster_unterlage_{side}_{i}',3024,11,[-187.5,y,80+10*i],group='Booster')
    anchor=add('booster_halter_'+side,87087,12,[-187.5,y,100],yaw=-90,group='Booster')
    cap=add('booster_fuss_'+side,6141,68,contact=(anchor,'0885e6ad6653d701cdde7191'),group='Booster')
    foot=poses[cap];direction=rotate(foot['rot'],(0,0,1))
    assert abs(direction[0]-1)<1e-5
    for i in range(10):
        add(f'booster_{side}_{i:02}',3062,11 if i in (0,8) else 24,
            [foot['pos'][j]+(10+30*i)*direction[j] for j in range(3)],rot=foot['rot'],group='Booster')
    nose=add('booster_kappe_'+side,3024,24,
        [foot['pos'][j]+310*direction[j] for j in range(3)],rot=foot['rot'],group='Booster')
    add('booster_spitze_'+side,59900,24,contact=(nose,'2667b926116b341fc850f91d'),group='Booster')

# Reorient the complete orbiter as one rigid assembly: nose +X, dorsal surface +Z.
old=json.loads((ROOT/'baupläne/astra_launch_crawler.json').read_text(encoding='utf8'))
old_groups=json.loads((HERE.parent/'gruppen.json').read_text(encoding='utf8'))
old_poses=b.place_parts(old['teile'],{},lib)
Q=(math.sqrt(.5),0,math.sqrt(.5),0)
for p,pose in zip(old['teile'],old_poses):
    if old_groups[p['id']]!='Orbiter': continue
    if 'anschluss' in p:
        add(p['id'],p['teil'],p['farbe'],contact=(p['anschluss']['an'],p['anschluss']['vorlage']),group='Orbiter')
    else:
        point=rotate(Q,pose['pos'])
        add(p['id'],p['teil'],p['farbe'],[point[0]-245,point[1],point[2]+160],rot=multiply(Q,pose['rot']),group='Orbiter')

# Four slender supports occupy the gaps between central tank and outboard boosters.
# They meet the existing two wing spars on standard, upward stud faces.
for j,x in enumerate([-37.5,-12.5]):
    for side,y in [('links',37.5),('rechts',-37.5)]:
        if j==1:
            add(f'stuetzenfuss_{j}_{side}',3024,11,[x,y,70],group='Orbiterhalter')
        for k in range(2):
            add(f'stuetze_{j}_{side}_{k}',3005,11,[x,y,80+30*k],group='Orbiterhalter')
        add(f'stuetzplatte_{j}_{side}',3024,11,[x,y,140],group='Orbiterhalter')
    add(f'stuetzbruecke_{j}',3710,11,[x,37.5,150],yaw=-90,group='Orbiterhalter')
    add(f'stuetzraster_{j}',3023,11,[x,12.5,160],yaw=-90,group='Orbiterhalter')

# Lateral rear operator pod, outside the boosters and behind the delta-wing roots.
add('bedienpod_quertraeger',3020,12,[-87.5,37.5,80],yaw=90)
add('bedienpod_boden',3795,12,[-187.5,112.5,90])
add('bedienpod_sitzplatte',3020,11,[-187.5,112.5,100])
add('fahrersitz',4079,11,contact=('bedienpod_sitzplatte','04d83c2ede16255da44ef068'))

plan=dict(name='ASTRA II Forward Carrier',vorlage_name=old['vorlage_name'],vorlage_datei=old['vorlage_datei'],
          teile=parts,fahrer=dict(teil='fahrersitz',pos=[0,0,10],dreh=[0,0,0]))
PLAN=ROOT/'baupläne/astra_ii_forward_carrier.json'
write(PLAN,plan);write(HERE/'gruppen.json',groups)
save_dir=Path(os.path.expandvars(r'%USERPROFILE%/Documents/My Games/Artemis/Saved/SaveGames'))
before={p.name:sha(p) for p in save_dir.glob('*.sav')}
result,report=b.build_vehicle(str(save_dir/'ArtemisVehicle.sav'),plan)
raw=result.dump();assert g.SaveFile.from_bytes(raw).dump()==raw
vehicle=g.val(g.val(result.props,'Data'),'CustomVehicles').elems[report['slot']]
graph=g.val(vehicle,'PartGraph');ps=g.val(graph,'Parts').elems;tfs=g.val(graph,'PartTransforms').elems
geometry=[dict(index=i,design=struct.unpack('<I',p[:4])[0],color=p[4],flags=p[5],
               pos=list(struct.unpack('<fff',g.val(tf,'Translation'))),rot=list(struct.unpack('<ffff',g.val(tf,'Rotation'))),
               scale=list(struct.unpack('<fff',g.val(tf,'Scale3D')))) for i,(p,tf) in enumerate(zip(ps,tfs))]
write(HERE/'builder-pruefung.json',report)
write(HERE/'gebauter-graph.json',dict(parts=geometry,
      assemblies=[dict(asset=b.text_value(a,'AssemblyAsset'),name=b.text_value(a,'AssemblyName'),indices=b.indices(a)) for a in g.val(graph,'Assemblies').elems],
      connections=[dict(a=b.connection_indices(c)[0],b=b.connection_indices(c)[1],fa=g.val(c,'FieldIndexA')[0],fb=g.val(c,'FieldIndexB')[0],
                        strength=g.val(c,'Strength')[0],type=b.text_value(c,'Type')) for c in g.val(graph,'Connections').elems]))
assert before=={p.name:sha(p) for p in save_dir.glob('*.sav')}
assert model1_before=={str(p.relative_to(ROOT)):sha(p) for p in M1_PATHS}
write(HERE/'sicherheit.json',dict(sav_hashes_before=before,sav_hashes_after=before,model1_hashes_unchanged=True,
      sav_written=False,serialization_roundtrip=True,plan_sha256=sha(PLAN)))
print(plan['name'],len(parts),'new parts;',report['teile'],'total;',report['verbindungen'],'connections')

"""Review the final independent design without writing any SAV, including to a copy."""
import collections
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0,str(ROOT / 'werkzeuge'))
import baue_fahrzeug as b
import gvas_rw as g
from baugeometrie import connect, quaternion, rotate
from teilewissen import Library

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_text(encoding='utf8'))
def write(name,data): (HERE/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
save_dir=Path(os.path.expandvars(r'%USERPROFILE%/Documents/My Games/Artemis/Saved/SaveGames'))
before={p.name:sha(p) for p in save_dir.glob('*.sav')}
plan=read(ROOT/'baupläne/astra_ii_forward_carrier.json')
source=save_dir/'ArtemisVehicle.sav'
original=g.SaveFile(str(source))
result,report=b.build_vehicle(str(source),plan)
raw=result.dump()
assert g.SaveFile.from_bytes(raw).dump()==raw
old=g.val(g.val(original.props,'Data'),'CustomVehicles').elems
new=g.val(g.val(result.props,'Data'),'CustomVehicles').elems
unchanged=[i for i in range(len(old)) if g.write_props(old[i])==g.write_props(new[i])]
assert len(unchanged)==len(old)-1 and report['slot'] not in unchanged
emerald=[i for i,v in enumerate(old) if b.text_value(v,'VehicleName')=='Emerald Express']
assert emerald and all(i in unchanged for i in emerald)

vehicle=new[report['slot']];graph=g.val(vehicle,'PartGraph')
pp=g.val(graph,'Parts').elems;tfs=g.val(graph,'PartTransforms').elems
geo=[dict(design=struct.unpack('<I',p[:4])[0],pos=list(struct.unpack('<fff',g.val(tf,'Translation'))),
          rot=list(struct.unpack('<ffff',g.val(tf,'Rotation'))),scale=list(struct.unpack('<fff',g.val(tf,'Scale3D')))) for p,tf in zip(pp,tfs)]
lib=Library.load()
automatic={(a,bb,fa,fb,n,'HingeConnection' if n==1 else 'FixedConnection') for a,bb,fa,fb,n in connect(geo)}
observed=lib.connect(geo)
refs=report['referenzen']
names={v:k for k,v in refs.items() if not k.startswith('teil:')}
classifications=collections.Counter();edges=[];used=set()
for c in g.val(graph,'Connections').elems:
    a,bb=b.connection_indices(c);fa=g.val(c,'FieldIndexA')[0];fb=g.val(c,'FieldIndexB')[0]
    n=g.val(c,'Strength')[0];typ=b.text_value(c,'Type').split('::')[-1]
    key=(a,bb,fa,fb,n,typ) if a<bb else (bb,a,fb,fa,n,typ)
    native=names[a].startswith(('chassis:','rad:')) and names[bb].startswith(('chassis:','rad:'))
    status='native_basis' if native else 'geometrisch' if key in automatic else 'beobachtete_paarlage' if key in observed else 'ungeprueft'
    classifications[status]+=1
    evidence=observed.get(key,[]) if status=='beobachtete_paarlage' else []
    used.update(evidence)
    edges.append(dict(a=names[a],b=names[bb],fa=fa,fb=fb,strength=n,type=typ,status=status,evidence=evidence))
assert classifications['ungeprueft']==0
assert not plan.get('verbindungen') and not report['lose_teile']
# The user's central requirement: all four complete flight bodies point along +X.
forward_axes={}
for name in ['tank_spitze','booster_spitze_links','booster_spitze_rechts','bauch_hinten']:
    direction=rotate(geo[refs[name]]['rot'],(1,0,0) if name=='bauch_hinten' else (0,0,1))
    assert abs(direction[0]-1)<1e-5 and abs(direction[1])+abs(direction[2])<1e-5,(name,direction)
    forward_axes[name]=direction
model1_hashes=read(HERE/'modell-1-ausgangshashes.json')
assert all(sha(ROOT/path)==expected for path,expected in model1_hashes.items())
donor=b.find_vehicle(b.pool_from(g.SaveFile(os.path.expandvars(plan['vorlage_datei']))),plan['vorlage_name'])
dg=g.val(donor,'PartGraph');dp=g.val(dg,'Parts').elems;dt=g.val(dg,'PartTransforms').elems
native_same=[]
for a in g.val(dg,'Assemblies').elems:
    if '/Chassis/' not in b.text_value(a,'AssemblyAsset') and 'Wheel' not in b.text_value(a,'AssemblyType'): continue
    name=b.text_value(a,'AssemblyName')
    for k,i in enumerate(b.indices(a)):
        ref=f'chassis:{k}' if name=='None' else f'rad:{name}:{k}'
        j=refs[ref]
        assert pp[j]==dp[i] and g.write_props(tfs[j])==g.write_props(dt[i])
        native_same.append(ref)

evidence={};reference_graphs={};reference_sources={}
for pid in sorted(used):
    pattern=lib.data['patterns'][pid]
    # Keep native source graph fingerprints and sanitized source labels, never player IDs.
    evidence[pid]=pattern
    for observation in pattern.get('evidence',[]):
        if isinstance(observation,dict) and 'graph' in observation:
            gid=observation['graph']
            record=lib.data['graphs'][gid]
            assert not record['excluded']
            assert all(loc['name'].casefold()!='shuttle rover' for loc in record['locations'])
            reference_graphs[gid]=record
            for loc in record['locations']:
                reference_sources[loc['source']]=lib.data['sources'][loc['source']]
assert 'Shuttle Rover' in lib.data['excluded_names']

# Inspect actual local reward entries, separately from catalogue presence and contact evidence.
spec=importlib.util.spec_from_file_location('unlock_reader',ROOT/'.claude/freischalten.py')
unlock=importlib.util.module_from_spec(spec);spec.loader.exec_module(unlock)
player=g.SaveFile(str(save_dir/'ArtemisPlayerInfo.sav'))
reward_sets=[{unlock.identity(e) for e in unlock.at(player.props,*path).value.elems} for path in unlock.reward_paths()]
catalog=read(ROOT/'teiledaten.json')
by_design=collections.Counter(p['teil'] for p in plan['teile'])
parts_status=[]
for design,count in sorted(by_design.items()):
    reward=('LegoPart',str(design))
    parts_status.append(dict(design=design,count=count,name=catalog.get(str(design),{}).get('name'),
                             catalog_present=str(design) in catalog,
                             observed_in_references=str(design) in lib.data['parts'],
                             reward_entry_in_both_lists=all(reward in s for s in reward_sets),
                             manually_selectable_in_game='not tested',variant='exact design ID; no alias substitution'))

# Re-render directly from the serialized graph; then check a special part's real transformed vertices.
spec=importlib.util.spec_from_file_location('astra_preview',HERE/'vorschau.py')
preview=importlib.util.module_from_spec(spec);spec.loader.exec_module(preview)
old_svg=preview.svg((1,.75,.32),'test')
wing=next(m for m in preview.meshes if m['name']=='delta_links')
old_vertices=wing['v']
wing['v']=[(x+80,y,z) for x,y,z in old_vertices]
assert preview.svg((1,.75,.32),'test')!=old_svg
wing['v']=old_vertices
assert preview.svg((1,.75,.32),'test')==old_svg
room=read(HERE/'raumpruefung.json')
assert not room['overlaps']

after={p.name:sha(p) for p in save_dir.glob('*.sav')}
assert before==after
tool_paths=['werkzeuge/baue_fahrzeug.py','werkzeuge/baugeometrie.py','werkzeuge/teilewissen.py',
            '.claude/teilewissen/bibliothek.json','.claude/maske-98282-belege.json']
tool_hashes={p:sha(ROOT/p) for p in tool_paths}
write('kontaktpruefung.json',dict(counts=classifications,connections=edges,patterns=evidence,
      reference_graphs=reference_graphs,reference_sources=reference_sources))
write('teile-und-verfuegbarkeit.json',parts_status)
write('validierung.json',dict(name=plan['name'],parts=len(pp),new_parts=len(plan['teile']),connections=sum(classifications.values()),
       source_hashes_before=before,source_hashes_after=after,sav_written=False,
       non_target_slots_identical=unchanged,emerald_slots_identical=emerald,
       chassis_and_wheels_identical=native_same,serialization_roundtrip=True,
       preview_special_part_motion_changes_svg=True,collision_hull_overlaps=0,
       contact_counts=classifications,tool_hashes=tool_hashes,
       forward_axes=forward_axes,model1_all_original_files_hash_identical=True,
       plan_sha256=sha(ROOT/'baupläne/astra_ii_forward_carrier.json')))
lines=['# ASTRA II – Teileauswahl','', '| ID | Anzahl | Katalogname | Referenz | Freigabeeintrag in beiden lokalen Listen |',
       '|---|---:|---|---|---|']
for p in parts_status:
    lines.append(f"| {p['design']} | {p['count']} | {p['name']} | {'ja' if p['observed_in_references'] else 'nein'} | {'ja' if p['reward_entry_in_both_lists'] else 'nein'} |")
lines+=['','Die Freigabeeinträge wurden nur gelesen. Sie bestätigen weder die manuelle Auswahl noch die Wettbewerbsregeln. Kein Alias wurde still eingesetzt.']
(HERE/'teileliste.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
print(json.dumps(dict(parts=len(pp),connections=classifications,unchanged_other_slots=len(unchanged),
      source_savs_unchanged=len(before),hull_overlaps=0,reward_entries_missing=[p['design'] for p in parts_status if not p['reward_entry_in_both_lists']]),ensure_ascii=False))

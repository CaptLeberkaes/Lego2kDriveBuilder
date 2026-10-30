"""Read-only integration checks and a held-out chassis-family benchmark."""
import collections
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'werkzeuge'))
import anschluesse as an
import baugeometrie as geo
from geometrie import canonical
from teilewissen import Library, graph_parts


def main():
    paths=an.alle_spielstaende()+[str(p) for p in (ROOT/'_sicherungen').glob('*/Artemis*.sav') if p.name in an.FAHRZEUG_DATEIEN]
    before={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths}
    seen_files=set(); vehicles={}; names=set()
    for path in paths:
        sha=before[path]
        if sha in seen_files: continue
        seen_files.add(sha)
        for origin,v in an.vehicles_with_source(path):
            if v['VehicleName'] in an.REFERENZ_AUSSCHLUESSE: continue
            vehicles[an.fingerprint(v)]=v
            if Path(path).name=='ArtemisDownloadedVehicle.sav' and origin=='DownloadedVehicles': names.add(v['VehicleName'])
    names.update({'Space Rover Explorer','Cattle Driver','Service Truck','Big Green Tractor'})
    library=Library.load(); results=[]
    for name in sorted(names):
        # Pick one graph for each target; exclude all observed graphs using its chassis config.
        hits=[(gid,v) for gid,v in vehicles.items() if v['VehicleName']==name]
        gid,v=sorted(hits,key=lambda x:x[0])[0]
        excluded={g for g,other in vehicles.items() if other['ChassisConfig']==v['ChassisConfig']}
        training=dict(library.data,patterns={pid:dict(p,evidence=[e for e in p['evidence'] if e['graph'] not in excluded])
                     for pid,p in library.data['patterns'].items() if any(e['graph'] not in excluded for e in p['evidence'])})
        heldout=Library(training); parts=graph_parts(v)
        automatic={(a,b,fa,fb,n,'HingeConnection' if n==1 else 'FixedConnection') for a,b,fa,fb,n in geo.connect(parts)}
        observed=heldout.connect(parts); predicted=set(automatic)
        face_fields=[{f[0] for f in geo.faces(p).values()} for p in parts]
        for key in observed:
            a,b,fa,fb,_,_=key
            if fa in face_fields[a] and fb in face_fields[b]: continue
            predicted.add(key)
        saved={(*canonical(c)[:5],canonical(c)[5].split('::')[-1]) for c in v['PartGraph']['Connections']['items']}
        new=predicted-automatic
        results.append({'vehicle':name,'heldout_graph':gid,'heldout_chassis':v['ChassisConfig'].split('.')[-1],
                        'excluded_graphs':len(excluded),'stored_unique':len(saved),'automatic_exact':len(automatic&saved),
                        'additional_exact':len(new&saved),'additional_wrong':len(new-saved),
                        'wrong_examples':sorted(new-saved)[:10]})
        print(name,len(new&saved),'new correct;',len(new-saved),'mismatches',flush=True)
    result={'method':'20 vehicles; exclude all graph evidence with target chassis config. Existing GEOM was not retrained; only additional pair contacts are held out.',
            'results':results,'additional_exact':sum(x['additional_exact'] for x in results),
            'additional_wrong':sum(x['additional_wrong'] for x in results),
            'source_files_unchanged':all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==before[p] for p in paths)}
    Path(__file__).with_name('validierung.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('TOTAL',result['additional_exact'],result['additional_wrong'],'unchanged',result['source_files_unchanged'])


if __name__=='__main__': main()

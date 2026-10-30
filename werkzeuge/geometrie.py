"""Anschluss-Kandidaten aus Vorlagen als Bedingungen sammeln, keine Flächen erfinden.

python geometrie.py datei.sav [...] --teile 87087 3823 [--json bericht.json]
"""
import argparse
import collections
import itertools
import json
from pathlib import Path
import struct

import gvas
from baugeometrie import GEOM, TOLERANZ, world_cells, yaw_of


def canonical(c):
    a,b,fa,fb=c['PartIndexA'],c['PartIndexB'],c['FieldIndexA'],c['FieldIndexB']
    return (a,b,fa,fb,c['Strength'],c['Type']) if a<b else (b,a,fb,fa,c['Strength'],c['Type'])


def domain_for(design, side):
    geo=GEOM.get(design)
    if geo is None:
        return None
    return set(map(tuple,geo.get(side+'_zellen',itertools.product(range(geo['l']),range(geo['w'])))))


def constraints_from_vehicle(vehicle, wanted, source=''):
    graph=vehicle['PartGraph'];transforms=graph['PartTransforms']['items']
    designs=[struct.unpack('<I',bytes.fromhex(p)[:4])[0] for p in graph['Parts']['items']]
    seen=set();result=[]
    for c in graph['Connections']['items']:
        signature=canonical(c)
        if signature in seen:
            continue
        seen.add(signature)
        if c['Type'].split('::')[-1] not in ('FixedConnection','HingeConnection'):
            continue
        for target,other,field,other_field in [(c['PartIndexA'],c['PartIndexB'],c['FieldIndexA'],c['FieldIndexB']),
                                               (c['PartIndexB'],c['PartIndexA'],c['FieldIndexB'],c['FieldIndexA'])]:
            if designs[target] not in wanted or designs[other] not in GEOM:
                continue
            target_tf,other_tf=transforms[target],transforms[other]
            yt,yo=yaw_of(target_tf['Rotation']),yaw_of(other_tf['Rotation'])
            if yt is None or yo is None or any(abs(s-1)>0.001 for tf in (target_tf,other_tf) for s in tf['Scale3D']):
                continue
            gt,go=GEOM.get(designs[target]),GEOM[designs[other]]
            zt,zo=target_tf['Translation'][2],other_tf['Translation'][2]
            if abs(zo+go['h']-zt)<=TOLERANZ:
                side,partner_side='unten','oben'
            elif gt is not None and abs(zt+gt['h']-zo)<=TOLERANZ:
                side,partner_side='oben','unten'
            else:
                continue
            if go.get(partner_side)!=other_field or (gt is not None and gt.get(side) is not None and gt.get(side)!=field):
                continue
            points=world_cells(designs[other],other_tf['Translation'],yo,partner_side)
            if not points:
                continue
            import math
            ca,sa=round(math.cos(math.radians(-yt))),round(math.sin(math.radians(-yt)))
            candidates=set();off_grid=False
            ox,oy=target_tf['Translation'][:2]
            for wx,wy in points:
                dx,dy=wx-ox,wy-oy
                u,v=(dx*ca-dy*sa)/25,-(dx*sa+dy*ca)/25
                if abs(u-round(u))*25>TOLERANZ or abs(v-round(v))*25>TOLERANZ:
                    off_grid=True;break
                candidates.add((round(u),round(v)))
            if off_grid:
                continue
            domain=domain_for(designs[target],side)
            if domain is not None:
                candidates &= domain
            result.append({'teil':designs[target],'seite':side,'feld':field,
                           'kandidaten':sorted(candidates),'noppen':c['Strength'],
                           'widerspruch':len(candidates)<c['Strength'],
                           'domaene':sorted(domain) if domain is not None else None,
                           'quelle':source,'fahrzeug':vehicle['VehicleName'],
                           'index':target,'partner_index':other,'partner_teil':designs[other],
                           'partner_feld':other_field,'typ':c['Type']})
    return result


def summarize(observations):
    grouped=collections.defaultdict(list)
    for o in observations:
        grouped[(o['teil'],o['seite'],o['feld'])].append(o)
    results=[]
    for (design,side,field),items in sorted(grouped.items()):
        domain=items[0]['domaene'];solutions=None;confirmed=[];excluded=[]
        contradictory=any(o['widerspruch'] for o in items)
        if domain is not None and len(domain)<=16:
            cells=list(map(tuple,domain));solutions=[]
            constraints={(tuple(map(tuple,o['kandidaten'])),o['noppen']) for o in items}
            for bits in range(1<<len(cells)):
                mask={cell for i,cell in enumerate(cells) if bits>>i&1}
                if all(len(mask & set(points))==n for points,n in constraints):
                    solutions.append(mask)
            if solutions:
                confirmed=sorted(set.intersection(*solutions))
                excluded=sorted(set(cells)-set.union(*solutions))
            else:
                contradictory=True
        results.append({'teil':design,'seite':side,'feld':field,'beobachtungen':len(items),
                        'status':'widerspruechlich' if contradictory else 'bedingt_durch_GEOM_Annahmen',
                        'moegliche_masken':len(solutions) if solutions is not None else None,
                        'bestaetigte_zellen':confirmed,'ausgeschlossene_zellen':excluded,
                        'vollstaendig_eindeutig':solutions is not None and len(solutions)==1,
                        'bedingungen':items})
    return results


def main(paths,wanted,out=None):
    from anschluesse import REFERENZ_AUSSCHLUESSE
    observations=[]
    for path in paths:
        data=gvas.load(path)['body']['Data']
        for key in ('CustomVehicles','DownloadedVehicles'):
            for vehicle in data.get(key,{}).get('items',[]):
                if vehicle['VehicleName']:
                    if vehicle['VehicleName'].casefold() in {n.casefold() for n in REFERENZ_AUSSCHLUESSE}:
                        continue
                    observations.extend(constraints_from_vehicle(vehicle,wanted,Path(path).name))
    result={'hinweis':'Bedingungen und Rasterdomänen sind Modellannahmen, kein vollständiger CAD-/Anschlussnachweis.',
            'ergebnisse':summarize(observations)}
    for row in result['ergebnisse']:
        print(row['teil'],row['seite'],'F'+str(row['feld']),row['status'],
              'mögliche Masken:',row['moegliche_masken'],'bedingt bestätigt:',row['bestaetigte_zellen'])
    if out:
        Path(out).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dateien',nargs='+');parser.add_argument('--teile',nargs='+',type=int,required=True)
    parser.add_argument('--json')
    args=parser.parse_args();main(args.dateien,set(args.teile),args.json)

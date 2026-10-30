"""Transform-aware review rendering and conservative convex hull collision audit.

All visible geometry comes from the built graph, never from a separate ideal model.
Special shapes are documented approximations, not game meshes. Stud interlocks are
intentionally excluded from collision solids. Native wheel positions are retained.
"""
import collections
import itertools
import json
import math
from pathlib import Path
import sys
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'werkzeuge'))
from baugeometrie import GEOM, cells, rotate

graph = json.loads((HERE / 'gebauter-graph.json').read_text(encoding='utf8'))
report = json.loads((HERE / 'builder-pruefung.json').read_text(encoding='utf8'))
groups = json.loads((HERE / 'gruppen.json').read_text(encoding='utf8'))
names = {v:k for k,v in report['referenzen'].items() if not k.startswith('teil:')}
COLORS = {1:'#bfc5cc', 11:'#202935', 12:'#647380', 24:'#f2f3f3', 27:'#e78128',
          29:'#244859', 9:'#e9bd2d', 20:'#f5db79', 68:'#b3c7d0', 255:'#24282e'}

def prism(poly, lo, hi):
    n=len(poly)
    return [(x,y,z) for z in (lo,hi) for x,y in poly], [list(range(n-1,-1,-1)),list(range(n,2*n))]+[[i,(i+1)%n,(i+1)%n+n,i+n] for i in range(n)]

def box(x0,x1,y0,y1,z0,z1):
    return prism([(x0,y0),(x1,y0),(x1,y1),(x0,y1)],z0,z1)

def cylinder(cx,cy,z0,z1,r0,r1=None,n=24):
    r1 = r0 if r1 is None else r1
    v=[(cx+r*math.cos(i*math.tau/n),cy+r*math.sin(i*math.tau/n),z)
       for r,z in ((r0,z0),(r1,z1)) for i in range(n)]
    return v,[list(range(n-1,-1,-1)),list(range(n,2*n))]+[[i,(i+1)%n,(i+1)%n+n,i+n] for i in range(n)]

SPECIAL_NOTES = {
    3956:'Two calibrated local bracket hulls from the existing Emerald geometry dossier; not a new learning reference.',
    6143:'Cylinder Ø50, height30, centre(12.5,-12.5); solid outer hull, axle hole omitted.',
    3942:'Truncated cone Ø50 to Ø12.5, height60; catalogue envelope, top approximated.',
    59900:'Truncated cone Ø25 to Ø6, height30; catalogue envelope.',
    54383:'3x6 right delta wedge, local footprint approximated from name and observed attachment rows.',
    54384:'Mirrored 3x6 left delta wedge; attachment origins follow actual pair placements.',
    4079:'Seat split into seat pan and rear wall; orientation/envelope approximate.',
    6015:'Tyre Ø21mm=65.625 units, width12mm=37.5; local origin at outer wheel face inferred from axle and tyre poses.',
    6014:'Rim approximated inside native tyre; axle geometry omitted.',
    6157:'Native bearing envelope only; not a new-part collision proof.',
    3660:'Native inverted slope approximated by its enclosing box.',
}

def local_shapes(p):
    d=p['design']
    if d in (6143,3942):
        return [cylinder(12.5,-12.5,0,30 if d==6143 else 60,25,25 if d==6143 else 6.25)]
    if d in (3062,6141,59900):
        return [cylinder(0,0,0,10 if d==6141 else 30,12.5,3 if d==59900 else 12.5)]
    if d in (54383,54384):
        sign=-1 if d==54383 else 1
        return [prism([(-12.5,-12.5*sign),(-12.5,62.5*sign),(12.5,62.5*sign),
                       (137.5,12.5*sign),(137.5,-12.5*sign)],0,10)]
    if d==3956:
        # Existing locally calibrated L bracket hulls, not newly guessed ports.
        spec=json.loads((HERE.parent.parent/'emerald-express/huellkoerper.json').read_text(encoding='utf8'))['teile']['winkel']
        return [box(*[v for i in range(3) for v in (min(c[i] for c in shape['ecken_lokal']),max(c[i] for c in shape['ecken_lokal']))]) for shape in spec['formen']]
    if d==3040:
        # Extrude the physically sloped y-z profile along x.
        v=[(x,y,z) for x in (-12.5,12.5) for y,z in [(-12.5,0),(37.5,0),(12.5,30),(-12.5,30)]]
        return [(v,[[3,2,1,0],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]])]
    if d==4079:
        return [box(-12.5,37.5,-37.5,12.5,0,10),box(-12.5,-2.5,-37.5,12.5,10,60)]
    if d in (6015,6014):
        v,f=cylinder(0,0,-37.5,0,32.8125 if d==6015 else 21)
        return [([(x,z,y) for x,y,z in v],f)]
    if d==6157:
        return [box(-12.5,37.5,-37.5,12.5,0,20)]
    if d==3660:
        return [box(-12.5,37.5,-37.5,12.5,0,30)]
    geo=GEOM[d]
    return [box(-12.5,25*geo['l']-12.5,-25*geo['w']+12.5,12.5,0,geo['h'])]

meshes=[]
for p in graph['parts']:
    name=names.get(p['index'],str(p['index']))
    for v,f in local_shapes(p):
        v=[tuple(a+b for a,b in zip(p['pos'],rotate(p['rot'],c))) for c in v]
        meshes.append(dict(name=name,part=p['index'],design=p['design'],color=p['color'],v=v,f=f,
                           group=groups.get(name,'Basis'),bounds=[(min(c[i] for c in v),max(c[i] for c in v)) for i in range(3)]))

def sub(a,b): return tuple(x-y for x,y in zip(a,b))
def dot(a,b): return sum(x*y for x,y in zip(a,b))
def cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def unit(a):
    l=math.sqrt(dot(a,a))
    return tuple(x/l for x in a) if l>1e-8 else None

def axes_edges(m):
    axes=[];edges=[]
    for face in m['f']:
        vs=[m['v'][i] for i in face]
        n=unit(cross(sub(vs[1],vs[0]),sub(vs[2],vs[0])))
        if n: axes.append(n)
        edges.extend(sub(vs[(i+1)%len(vs)],vs[i]) for i in range(len(vs)))
    return axes,edges

def penetration(a,b):
    ax,ae=axes_edges(a); bx,be=axes_edges(b)
    seen=set();depth=1e9
    for axis in itertools.chain(ax,bx,(cross(x,y) for x in ae for y in be)):
        u=unit(axis)
        if not u: continue
        key=tuple(round(x,4) for x in u)
        if key in seen: continue
        seen.add(key)
        aa=[dot(v,u) for v in a['v']];bb=[dot(v,u) for v in b['v']]
        overlap=min(max(aa),max(bb))-max(min(aa),min(bb))
        if overlap <= .15: return None
        depth=min(depth,overlap)
    return depth

conflicts=[]
for a,b in itertools.combinations(meshes,2):
    if a['part']==b['part'] or (a['group']=='Basis' and b['group']=='Basis'): continue
    depths=[min(a['bounds'][i][1],b['bounds'][i][1])-max(a['bounds'][i][0],b['bounds'][i][0]) for i in range(3)]
    if min(depths)<=.15: continue
    value=penetration(a,b)
    if value:
        conflicts.append(dict(a=a['name'],b=b['name'],minimum_separating_translation=round(value,3),
                              approximate_special_shape=any(x['design'] in SPECIAL_NOTES for x in (a,b))))

def hexrgb(c): return tuple(int(c[i:i+2],16) for i in (1,3,5))
def shaded(c,n):
    factor=.67+.30*abs(dot(n,unit((.3,-.5,.9))))
    return '#'+''.join(f'{max(0,min(255,round(x*factor))):02x}' for x in hexrgb(c))

def scene(cam,studs=True):
    d=unit(cam);r=unit(cross((0,0,1),d));u=cross(d,r)
    def proj(v): return dot(v,r),-dot(v,u)
    faces=[]
    def append(vv,ff,color,name):
        for face in ff:
            v=[vv[i] for i in face]
            n=unit(cross(sub(v[1],v[0]),sub(v[2],v[0])))
            if not n: continue
            # Cylinder meshes have consistent winding; tyre reflection can reverse it.
            if dot(n,d)<-1e-5: continue
            faces.append((sum(dot(x,d) for x in v)/len(v),[proj(x) for x in v],shaded(color,n),name))
    for m in meshes:
        append(m['v'],m['f'],COLORS.get(m['color'],'#9099a0'),m['name'])
    if studs:
        for p in graph['parts']:
            dsg=p['design']; geo=GEOM.get(dsg)
            if not geo or geo.get('oben') is None or dsg in (98282,4212): continue
            for a,b in cells(geo,'oben'):
                # Sloped bricks' single upper stud and ordinary plate grids follow GEOM.
                v,f=cylinder(25*a,-25*b,geo['h'],geo['h']+4,7.0,n=10)
                v=[tuple(x+y for x,y in zip(p['pos'],rotate(p['rot'],c))) for c in v]
                append(v,f,COLORS.get(p['color'],'#9099a0'),names.get(p['index'],str(p['index'])))
    return sorted(faces),proj

def svg(cam,title):
    faces,_=scene(cam)
    points=[p for _,poly,_,_ in faces for p in poly]
    lo=[min(p[i] for p in points)-18 for i in range(2)]
    hi=[max(p[i] for p in points)+18 for i in range(2)]
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{lo[0]} {lo[1]} {hi[0]-lo[0]} {hi[1]-lo[1]}" role="img" aria-label="{title}">']
    for _,poly,c,name in faces:
        out.append('<polygon points="'+' '.join(f'{x:.2f},{y:.2f}' for x,y in poly)+f'" fill="{c}" stroke="#121b26" stroke-width=".42"><title>{name}</title></polygon>')
    out.append('</svg>')
    return ''.join(out)

VIEWS=[('Perspektive',(1,-1.4,.8)),('Seite · Fahrtrichtung →',(0,-1,.00001)),('Oben · vorne ↑',(-.00001,0,1)),('Vorne',(1,0,.00001))]
cards=''.join(f'<figure><figcaption>{name}</figcaption>{svg(cam,name)}</figure>' for name,cam in VIEWS)
html='''<!doctype html><html lang="de"><meta charset="utf-8"><title>ASTRA II Forward Carrier</title>
<meta name="viewport" content="width=device-width,initial-scale=1"><style>
body{margin:0;background:#101a27;color:#e8edf4;font:15px/1.5 system-ui,sans-serif}main{max-width:1450px;margin:auto;padding:32px}
h1{font-size:34px;margin:0}p{color:#becad8;max-width:1000px}.tag{color:#eeb248;letter-spacing:.15em;font-size:12px}
.views{display:grid;grid-template-columns:repeat(2,minmax(260px,1fr));gap:18px}figure{margin:0;background:#dbe4ed;border-radius:12px;padding:18px;color:#253445}
svg{width:100%;height:530px}figcaption{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.1em}
details{margin-top:24px}a{color:#f3c268}button{cursor:pointer;background:#293b50;color:white;border:1px solid #546779;border-radius:6px;padding:8px 16px}
body.wire polygon{fill:none!important;stroke:#415266;stroke-width:.65}@media(max-width:700px){.views{grid-template-columns:1fr}main{padding:16px}}
</style><main><div class="tag">EIGENSTÄNDIGER WETTBEWERBSENTWURF · OFFLINE</div><h1>ASTRA II Forward Carrier</h1>
<p>Waagerechter Shuttle-Startstapel in Fahrtrichtung (+X) mit orangefarbenem Außentank und zwei weißen Boostern auf einem unveränderten PoliceTruck-/Eileen-Radchassis.
94 neue Teile · 110 insgesamt. Weißer Orbiter, Deltaflügel, dunkle Cockpitfenster und vorragendes Leitwerk.</p>
<p><strong>Nachvollziehbare Modellvorschau:</strong> Die Ansichten verwenden sämtliche Positionen und Quaternionen des tatsächlich gebauten Graphen.
Sonderteile sind vereinfachte Körper, keine Spielmeshes. Kein Spieltest und kein Freischaltungsnachweis.</p>
<button onclick="document.body.classList.toggle('wire')">Drahtansicht umschalten</button><div class="views">'''+cards+'''</div>
<details open><summary>Prüfstatus und Grenzen</summary><p>Der Builder bestätigt den Chassispfad für alle Oberbauteile.
Es gibt keine manuell behaupteten Verbindungen. Kollisionen werden zusätzlich an vereinfachten konvexen Körpern gesucht;
Studs und Hohlräume werden dabei nicht vollständig geprüft. Der Prüfbericht nennt alle Hüllkörpertreffer.</p>
<p><a href="astra_ii_forward_carrier.json">Bauplan</a> · <a href="../.claude/wettbewerb-shuttle/modell-2/pruefbericht.md">Prüfbericht</a></p></details></main></html>'''
html=html.replace('94 neue Teile · 110 insgesamt',f"{report['koerperteile']} neue Teile · {report['teile']} insgesamt")
(ROOT / 'baupläne/astra_ii_forward_carrier_vorschau.html').write_text(html,encoding='utf8')

# Standalone preview for review without a browser dependency.
im=Image.new('RGB',(1500,1080),'#101a27');draw=ImageDraw.Draw(im)
fontpath=Path('C:/Windows/Fonts/segoeui.ttf')
font=ImageFont.truetype(str(fontpath),21);small=ImageFont.truetype(str(fontpath),17)
draw.text((40,24),'ASTRA II  /  FORWARD CARRIER',font=ImageFont.truetype(str(fontpath),36),fill='#edf2f7')
draw.text((42,77),'Eigenständiger Entwurf · feste Radbasis · vereinfachte Körper aus dem gebauten Graphen',font=small,fill='#b8c7d8')
for name,cam,rect in [(VIEWS[0][0],VIEWS[0][1],(32,125,990,1015)),
                       (VIEWS[1][0],VIEWS[1][1],(1010,125,1470,550)),
                       (VIEWS[2][0],VIEWS[2][1],(1010,570,1470,1015))]:
    draw.rounded_rectangle(rect,12,fill='#dbe4ed')
    draw.text((rect[0]+18,rect[1]+12),name,font=font,fill='#26374a')
    faces,_=scene(cam)
    points=[p for _,poly,_,_ in faces for p in poly]
    lx,ly=min(p[0] for p in points),min(p[1] for p in points)
    hx,hy=max(p[0] for p in points),max(p[1] for p in points)
    s=min((rect[2]-rect[0]-44)/(hx-lx),(rect[3]-rect[1]-100)/(hy-ly))
    ox=(rect[0]+rect[2])/2-(lx+hx)*s/2;oy=(rect[1]+rect[3]+40)/2-(ly+hy)*s/2
    for _,poly,c,_ in faces:
        pp=[(ox+x*s,oy+y*s) for x,y in poly]
        draw.polygon(pp,fill=c,outline='#364352',width=1)
draw.text((42,1038),'Offline-Prüfung. Keine echten SAV-Dateien geschrieben. Keine vollständige Mesh-Kollisionsprüfung.',font=small,fill='#bac7d5')
im.save(ROOT / 'baupläne/astra_ii_forward_carrier_vorschau.png')

bounds=[(min(m['bounds'][i][0] for m in meshes),max(m['bounds'][i][1] for m in meshes)) for i in range(3)]
collision_report=dict(method='Broad phase AABB; narrow phase convex-polyhedron SAT, tolerance0.15; studs omitted',
                      special_shape_notes=SPECIAL_NOTES, bounds=bounds, overlaps=conflicts,
                      checked_new_parts=report['koerperteile'], exact_game_meshes=False,
                      warnings=['No complete cavities, wheel steering/suspension sweep or driver avatar envelope tested.'])
(HERE / 'raumpruefung.json').write_text(json.dumps(collision_report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('Collision candidates:',len(conflicts))
for c in conflicts: print(c)

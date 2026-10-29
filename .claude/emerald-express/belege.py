"""Belegte Verbindungen fuer Sonderteile: relative Lage zum Partner im Partner-Rahmen."""
import sys, struct, collections, json
sys.path.insert(0, sys.argv[1])
import anschluesse as an
from baugeometrie import GEOM, rotate, conjugate, multiply
want = {int(x) for x in sys.argv[2].split(",")}
seen = set(); out = collections.defaultdict(collections.Counter)
for v in an.unique_vehicles(an.alle_spielstaende()):
    pg = v["PartGraph"]; tf = pg["PartTransforms"]["items"]
    ds = [struct.unpack("<I", bytes.fromhex(p)[:4])[0] for p in pg["Parts"]["items"]]
    for c in pg["Connections"]["items"]:
        a, b = c["PartIndexA"], c["PartIndexB"]
        for t, o, ft, fo in ((a, b, c["FieldIndexA"], c["FieldIndexB"]), (b, a, c["FieldIndexB"], c["FieldIndexA"])):
            if ds[t] not in want: continue
            qo = tf[o]["Rotation"]; qt = tf[t]["Rotation"]
            d = [tf[t]["Translation"][i]-tf[o]["Translation"][i] for i in range(3)]
            rel = rotate(conjugate(qo), d); rq = multiply(conjugate(qo), qt)
            if rq[3] < 0: rq = [-x for x in rq]
            key = (ds[t], ft, ds[o], fo, c["Strength"], c["Type"].split("::")[-1],
                   tuple(round(x, 1) for x in rel), tuple(round(x, 2) for x in rq))
            out[ds[t]][key] += 1
for p in sorted(out):
    print(f"=== {p}")
    for k, n in out[p].most_common(int(sys.argv[3])):
        geo = "GEOM" if k[2] in GEOM else ""
        print(f" {n:3d}x  f{k[1]} <-> {k[2]} f{k[3]} {geo:4s} st{k[4]} {k[5][:5]} rel{k[6]} rq{k[7]}")

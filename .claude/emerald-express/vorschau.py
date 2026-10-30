"""Grobe Hüllkörper für den Emerald-Express-Bauplan: Überschneidungstest + SVG-Vorschau (3 Ansichten).

Aufruf (im Projektordner): python .claude/emerald-express/vorschau.py werkzeuge baupläne/emerald_express.json baupläne/emerald_express_vorschau.html
Sonderteile werden mit den im Generator hergeleiteten Weltmaßen eingetragen (kein Mesh).
"""
import itertools
import json
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])
from baugeometrie import GEOM, cells, quat_z, rotate, quaternion  # noqa: E402
from baue_fahrzeug import place_parts, load_knowledge  # noqa: E402

FARBE = {1: "#c9ccd1", 12: "#6b6f75", 11: "#1b1b1b", 7: "#c8102e", 38: "#1f5a32", 16: "#cfe8f3", 20: "#f5d000"}
plan = json.load(open(sys.argv[2], encoding="utf-8"))
boxen = []  # (name, farbe, (x0,x1), (y0,y1), (z0,z1), form)


def box(name, farbe, x, y, z, form="box"):
    boxen.append((name, farbe, tuple(sorted(x)), tuple(sorted(y)), tuple(sorted(z)), form))


SONDER = json.loads(Path(__file__).with_name('huellkoerper.json').read_text(encoding='utf-8'))['teile']
placements = place_parts(plan['teile'], {}, load_knowledge(plan))
for t, placement in zip(plan["teile"], placements):
    q = quaternion(placement['rot']); pos = placement['pos']
    if t["id"] in SONDER:
        shape = SONDER[t['id']]
        if shape['teil'] != t['teil']:
            raise ValueError(f"Hüllkörper passt nicht zur Teilenummer: {t['id']}")
        unchanged_rotation = 1-abs(sum(a*b for a,b in zip(q, shape['referenzrotation']))) < 1e-7
        for spec in shape['formen']:
            corners = [tuple(x+y for x,y in zip(pos, rotate(q, corner))) for corner in spec['ecken_lokal']]
            axes = [(min(c[i] for c in corners), max(c[i] for c in corners)) for i in range(3)]
            box(t['id'], t['farbe'], *axes, form=spec['form'] if unchanged_rotation else 'box')
        continue
    geo = GEOM[t["teil"]]
    for u, v in cells(geo, "unten") or cells(geo, "oben"):
        corners = [tuple(x+y for x,y in zip(pos, rotate(q, corner)))
                   for corner in itertools.product((25*u-12.5, 25*u+12.5), (-25*v-12.5, -25*v+12.5), (0, geo['h']))]
        axes = [(min(c[i] for c in corners), max(c[i] for c in corners)) for i in range(3)]
        form = "box"
        if t["teil"] == 3040 and (u, v) != (0, 0):
            form = "schraege_x"
        box(t["id"], t["farbe"], *axes, form)
# Chassis und Räder aus "Alte Schule" (Lage wie gespeichert; Reifen 61254 Ø24 mm = 75, Breite 7 mm ≈ 22)
box("chassis_2445", 1, (-150, 150), (-25, 25), (0, 10))
box("radhalter_vorn", 1, (100, 150), (-50, 50), (10, 20))
box("radhalter_hinten", 1, (-150, -100), (-50, 50), (10, 20))
for x in (125, -125):
    for s_ in (-1, 1):
        box(f"rad_{'vorn' if x > 0 else 'hinten'}_{'l' if s_ > 0 else 'r'}", 255,
            (x - 37.5, x + 37.5), sorted((s_ * 51.7 - 11, s_ * 51.7 + 11)), (8.13 - 37.5, 8.13 + 37.5), "rad")

# Überschneidungen (Berührung erlaubt)
konflikte = []
for a, b in itertools.combinations(boxen, 2):
    if a[0] == b[0]:
        continue
    tiefe = [min(a[i][1], b[i][1]) - max(a[i][0], b[i][0]) for i in (2, 3, 4)]
    if all(d > 0.5 for d in tiefe):
        konflikte.append((a[0], b[0], [round(d, 1) for d in tiefe]))
for k in sorted(set((a, b, tuple(d)) for a, b, d in konflikte)):
    print("UEBERSCHNEIDUNG", k)
# Räder sind hier Quader statt Scheiben; Treffer nur als Hinweis.
karosserie = [k for k in konflikte if not any(n.startswith(("rad_", "radhalter_")) for n in k[:2])]
mit_rad = sorted({k[0] for k in konflikte if k[1].startswith("rad_") and not k[0].startswith("radhalter_")})
print(len(boxen), "Hüllkörper,", len(karosserie), "Karosserie-Überschneidungen, nahe Rädern:", mit_rad)


def ansicht(titel, ax_h, ax_v, tiefe, vorzeichen):
    """Orthografische Ansicht; Malreihenfolge nach Tiefe (hinten zuerst)."""
    s = 1.6
    teile = sorted(boxen, key=lambda b: vorzeichen * (b[tiefe][0] + b[tiefe][1]))
    h0 = min(b[ax_h][0] for b in boxen) - 20
    h1 = max(b[ax_h][1] for b in boxen) + 20
    v0 = min(b[ax_v][0] for b in boxen) - 20
    v1 = max(b[ax_v][1] for b in boxen) + 20
    w, h = (h1 - h0) * s, (v1 - v0) * s
    out = [f'<figure><figcaption>{titel}</figcaption><svg viewBox="0 0 {w:.0f} {h:.0f}" '
           f'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{titel}">']
    for name, farbe, *ach, form in teile:
        X = [(c - h0) * s for c in ach[ax_h - 2]]
        Y = [h - (c - v0) * s for c in ach[ax_v - 2]]
        fill = FARBE.get(farbe, "#2a2a2a")
        op = ' fill-opacity="0.7"' if farbe == 16 else ""
        if form == "rad":
            if ax_h == 2 and ax_v == 4:
                out.append(f'<circle cx="{sum(X)/2:.1f}" cy="{sum(Y)/2:.1f}" r="{(X[1]-X[0])/2:.1f}" '
                           f'fill="#2a2a2a" stroke="#888" stroke-width="5" fill-opacity="0.85"><title>{name}</title></circle>')
                continue
            fill = "#2a2a2a"
        if form == "zyl_x" and ax_h == 3:
            out.append(f'<ellipse cx="{sum(X)/2:.1f}" cy="{sum(Y)/2:.1f}" rx="{(X[1]-X[0])/2:.1f}" '
                       f'ry="{(Y[0]-Y[1])/2:.1f}" fill="{fill}" stroke="#000" stroke-width="1"><title>{name}</title></ellipse>')
            continue
        if form == "kegel" and ax_v == 4:
            m = sum(X) / 2
            pts = f"{X[0]:.1f},{Y[1]:.1f} {X[1]:.1f},{Y[1]:.1f} {m+12*s:.1f},{Y[0]:.1f} {m-12*s:.1f},{Y[0]:.1f}"
            out.append(f'<polygon points="{pts}" fill="{fill}" stroke="#555" stroke-width="1"><title>{name}</title></polygon>')
            continue
        if form == "schraege_x" and ax_h == 2 and ax_v == 4:
            pts = f"{X[0]:.1f},{Y[1]:.1f} {X[1]:.1f},{Y[0]:.1f} {X[0]:.1f},{Y[0]:.1f}"
            out.append(f'<polygon points="{pts}" fill="{fill}" stroke="#000" stroke-width="1"><title>{name}</title></polygon>')
            continue
        rx = 18 if form == "zyl_x" and ax_h == 2 and ax_v == 4 else 1
        out.append(f'<rect x="{X[0]:.1f}" y="{Y[1]:.1f}" width="{X[1]-X[0]:.1f}" height="{Y[0]-Y[1]:.1f}" rx="{rx}" '
                   f'fill="{fill}"{op} stroke="#000" stroke-width="1"><title>{name}</title></rect>')
    out.append("</svg></figure>")
    return "".join(out)


html = f"""<!doctype html><html lang="de"><head><meta charset="utf-8"><title>Emerald Express Vorschau</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>:root{{--bg:#eef3f7;--fg:#1d2733;--card:#fff;--muted:#5b6672}}
@media (prefers-color-scheme:dark){{:root{{--bg:#11161c;--fg:#e3e8ee;--card:#1b222b;--muted:#9aa6b2}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.45 system-ui,sans-serif;padding:16px}}
h1{{font-size:20px;margin:0 0 4px}}p{{margin:0 0 12px;color:var(--muted)}}
.v{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}}
figure{{margin:0;background:var(--card);border-radius:10px;padding:10px}}figcaption{{font-weight:600;margin-bottom:6px}}
svg{{width:100%;height:auto;display:block}}</style></head><body>
<h1>Emerald Express (31015) – Vorschau des Bauplans</h1>
<p>Grobe Hüllkörper aus <code>baupläne/emerald_express.json</code>; Kessel als Zylinder, Schornstein als Kegel, Chassis und Räder aus dem Startchassis „Alte Schule“.
Vorne = rechts. Überschneidungen zwischen Karosserieteilen: {len(karosserie)}; Teile im Radbereich: {", ".join(mit_rad) or "keine"}.</p>
<div class="v">{ansicht("Seite (von links)", 2, 4, 3, -1)}{ansicht("Vorne", 3, 4, 2, 1)}{ansicht("Oben", 2, 3, 4, 1)}</div>
</body></html>
"""
open(sys.argv[3], "w", encoding="utf-8").write(html)

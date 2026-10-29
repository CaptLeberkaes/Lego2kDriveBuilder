"""Anschlussgeometrie und Transformationen; Einheiten: Noppe 25, Platte 10."""
import math

GEOM = {
    # Rechteckige Standardteile: Felder über lokale 3D-Kontakte im Download-Korpus
    # gegengeprüft; Belege: .claude/geometrie-erweiterung-belege.json.
    # None bedeutet hier unbekannt, also keine automatische Verbindung an der Seite.
    3007: dict(l=8, w=2, h=30, unten=1, oben=0),
    3008: dict(l=8, w=1, h=30, unten=1, oben=0),
    3009: dict(l=6, w=1, h=30, unten=1, oben=0),
    3021: dict(l=3, w=2, h=10, unten=0, oben=1),
    3795: dict(l=6, w=2, h=10, unten=1, oben=0),
    3032: dict(l=6, w=4, h=10, unten=1, oben=0),
    3033: dict(l=10, w=6, h=10, unten=1, oben=0),
    3034: dict(l=8, w=2, h=10, unten=0, oben=1),
    3035: dict(l=8, w=4, h=10, unten=1, oben=0),  # unten: geom_kandidaten.py --vorhandene
    3028: dict(l=12, w=6, h=10, unten=1, oben=0),   # unten: Runde 1, geom_kandidaten.py --vorhandene
    3029: dict(l=12, w=4, h=10, unten=0, oben=1),   # unten: geom_kandidaten.py --vorhandene
    3068: dict(l=2, w=2, h=10, unten=0, oben=None),
    3001: dict(l=4, w=2, h=30, unten=0, oben=1),
    3002: dict(l=3, w=2, h=30, unten=0, oben=1),
    3004: dict(l=2, w=1, h=30, unten=1, oben=0),
    3005: dict(l=1, w=1, h=30, unten=1, oben=0),
    3003: dict(l=2, w=2, h=30, unten=1, oben=0),
    3022: dict(l=2, w=2, h=10, unten=1, oben=0),
    3010: dict(l=4, w=1, h=30, unten=1, oben=0),
    3622: dict(l=3, w=1, h=30, unten=1, oben=0),
    3020: dict(l=4, w=2, h=10, unten=1, oben=0),
    3031: dict(l=4, w=4, h=10, unten=1, oben=0),
    3023: dict(l=2, w=1, h=10, unten=1, oben=0),
    3024: dict(l=1, w=1, h=10, unten=1, oben=0),
    3710: dict(l=4, w=1, h=10, unten=1, oben=0),
    3666: dict(l=6, w=1, h=10, unten=1, oben=0),
    3832: dict(l=10, w=2, h=10, unten=1, oben=0),
    3460: dict(l=8, w=1, h=10, unten=1, oben=0),
    2445: dict(l=12, w=2, h=10, unten=0, oben=1),
    3062: dict(l=1, w=1, h=30, unten=1, oben=0),
    # Abgeleitet mit geom_kandidaten.py (Größe aus teiledaten.json, Felder und Noppenzahl aus
    # gespeicherten 3D-Kontakten inkl. Creators-Hub-Cache, Gegentest exakt);
    # Belege: .claude/geom-kandidaten-belege.json. 35382/93888 sind Aliase von 3005/3007.
    3027: dict(l=16, w=6, h=10, unten=1, oben=0),
    3030: dict(l=10, w=4, h=10, unten=1, oben=0),
    3036: dict(l=8, w=6, h=10, unten=1, oben=0),
    3456: dict(l=14, w=6, h=10, unten=1, oben=None),
    3958: dict(l=6, w=6, h=10, unten=0, oben=1),
    4162: dict(l=8, w=1, h=10, unten=0, oben=None),
    4282: dict(l=16, w=2, h=10, unten=1, oben=0),
    4477: dict(l=10, w=1, h=10, unten=1, oben=0),   # oben: Runde 1
    6111: dict(l=10, w=1, h=30, unten=1, oben=0),
    6636: dict(l=6, w=1, h=10, unten=0, oben=None),
    11212: dict(l=3, w=3, h=10, unten=1, oben=0),
    26603: dict(l=3, w=2, h=10, unten=0, oben=None),
    35382: dict(l=1, w=1, h=30, unten=1, oben=0),
    41539: dict(l=8, w=8, h=10, unten=0, oben=1),
    44237: dict(l=6, w=2, h=30, unten=1, oben=0),
    60479: dict(l=12, w=1, h=10, unten=0, oben=1),  # oben: Runde 1
    69729: dict(l=6, w=2, h=10, unten=0, oben=None),
    78329: dict(l=5, w=1, h=10, unten=1, oben=0),
    87079: dict(l=4, w=2, h=10, unten=0, oben=None),
    91988: dict(l=14, w=2, h=10, unten=1, oben=0),
    93888: dict(l=8, w=2, h=30, unten=1, oben=0),
    # Kopierrunde 1 (Garagenkopien Cattle Driver, Cranium Insanium, Foul Runnings Truck, Double Decker Tour Bus);
    # Belege: .claude/geom-kandidaten-belege-runde1.json
    2465: dict(l=16, w=1, h=30, unten=1, oben=0),   # oben: Runde 2
    6112: dict(l=12, w=1, h=30, unten=1, oben=0),
    6212: dict(l=10, w=4, h=30, unten=1, oben=0),
    43802: dict(l=8, w=8, h=30, unten=1, oben=0),
    44042: dict(l=6, w=4, h=30, unten=1, oben=0),
    92438: dict(l=16, w=8, h=10, unten=1, oben=0),  # unten: Space Rover Explorer
    # Kopierrunde 2 (12 Garagenkopien nach Abdeckungsliste); Belege: .claude/geom-kandidaten-belege-runde2.json
    3006: dict(l=10, w=2, h=30, unten=1, oben=0),
    30400: dict(l=18, w=4, h=30, unten=1, oben=0),
    35386: dict(l=2, w=1, h=10, unten=0, oben=None),
    # Runde 3; Belege: .claude/geom-kandidaten-belege-runde3.json (Alias von 3003)
    35275: dict(l=2, w=2, h=30, unten=1, oben=0),
    # Runde 4; Belege: .claude/geom-kandidaten-belege-runde4.json (10 Kontakte, Gegentest 10/10)
    35403: dict(l=1, w=1, h=10, unten=0, oben=None),
    # Schräge 45° 2x1: Noppe am Ursprung (hohe Seite), Schräge fällt nach lokal +y ab;
    # mit dreh 270 fällt sie nach +x (vorn) ab
    3040: dict(l=1, w=2, h=30, unten=1, oben=0, unten_zellen=[(0, 0), (0, -1)], oben_zellen=[(0, 0)]),
    3069: dict(l=2, w=1, h=10, unten=0, oben=None),
    # gebogene Dachschräge 2x4: Länge entlang x, Rundung nach -y; Gegenseite um 180° drehen
    88930: dict(l=4, w=2, h=20, unten=0, oben=None),
    3623: dict(l=3, w=1, h=10, unten=1, oben=0),
    3070: dict(l=1, w=1, h=10, unten=0, oben=None),
    63864: dict(l=3, w=1, h=10, unten=0, oben=None),
    2431: dict(l=4, w=1, h=10, unten=0, oben=None),
    37352: dict(l=2, w=1, h=30, unten=0, oben=None),
    11211: dict(l=2, w=1, h=30, unten=2, oben=0),
    87087: dict(l=1, w=1, h=30, unten=1, oben=2),
    6141: dict(l=1, w=1, h=10, unten=0, oben=1),
    # Kotflügel: Noppenblock 2x1 am Ursprung, 1 Stein hoch (laut Spiel/Vorlage G022);
    # Bogen links ungedreht, rechts um 180° gedreht einsetzen.
    # Oben 2x2 (zusätzliche Reihe Richtung +y), unten 2x1; aus 130 Fahrzeugen belegt:
    # 278 Ober- und 243 Unterseitenkontakte exakt, siehe .claude/maske-98282-belege.json
    98282: dict(l=2, w=1, h=30, unten=0, oben=1,
                oben_zellen=[(0, 0), (1, 0), (0, -1), (1, -1)], unten_zellen=[(0, 0), (1, 0)]),
    # Ein Kontakt belegt sechs statt acht Noppen, aber nicht deren genaue Lage.
    3823: dict(l=4, w=2, h=60, unten=0, oben=1, maske_unbekannt=True),
    # Chassis-Platte von PoliceTruck_7032 (4x10, Mittelloch, Radausschnitte)
    4212: dict(l=10, w=4, h=10, unten=1, oben=0,
               oben_zellen=[(u, v) for v in (1, 2) for u in range(10) if u not in (4, 5)]
               + [(u, v) for v in (0, 3) for u in (0, 3, 4, 5, 6, 9)]),
}

TOLERANZ = 0.15


def vector(value, size=3):
    if (not isinstance(value, (list, tuple)) or len(value) != size
            or any(isinstance(x, bool) or not isinstance(x, (int, float))
                   or not math.isfinite(x) for x in value)):
        raise ValueError(f"Erwartet: {size} endliche Zahlen, erhalten: {value!r}")
    return tuple(float(x) for x in value)


def quaternion(value):
    q = vector(value, 4)
    norm = math.sqrt(sum(x*x for x in q))
    if abs(norm - 1) > 0.01:
        raise ValueError(f"Quaternion muss normiert sein: {value!r}")
    return tuple(x / norm for x in q)


def quat_z(deg):
    if isinstance(deg, bool) or not isinstance(deg, (int, float)) or not math.isfinite(deg):
        raise ValueError("dreh muss eine endliche Gradzahl sein")
    a = math.radians(deg) / 2
    return (0.0, 0.0, math.sin(a), math.cos(a))


def multiply(a, b):
    x, y, z, w = a
    X, Y, Z, W = b
    return (w*X+x*W+y*Z-z*Y, w*Y-x*Z+y*W+z*X,
            w*Z+x*Y-y*X+z*W, w*W-x*X-y*Y-z*Z)


def conjugate(q):
    return (-q[0], -q[1], -q[2], q[3])


def rotate(q, v):
    return multiply(multiply(q, (*v, 0.0)), conjugate(q))[:3]


def yaw_of(q):
    """Nur aufrechte 90-Grad-Rasterlagen; andere Lagen werden nicht umgedeutet."""
    x, y, z, w = quaternion(q)
    if abs(x) > 0.001 or abs(y) > 0.001:
        return None
    deg = math.degrees(2 * math.atan2(z, w)) % 360
    snapped = round(deg / 90) * 90
    return snapped % 360 if abs(deg - snapped) < 0.01 else None


def cells(geo, key):
    if geo.get(key) is None or geo.get("maske_unbekannt"):
        return []
    return geo.get(key + "_zellen", [(u, v) for u in range(geo["l"]) for v in range(geo["w"])])


def world_cells(design, pos, yaw, key):
    """Kompatible 2D-Hilfsfunktion; Rotationen werden nicht auf Sinus 0/1 gerundet."""
    if yaw is None:
        raise ValueError("Diese 2D-Abfrage benötigt eine aufrechte Rasterlage")
    q = quat_z(yaw)
    return {(round(pos[0] + p[0], 4), round(pos[1] + p[1], 4))
            for u, v in cells(GEOM[design], key)
            for p in [rotate(q, (25*u, -25*v, 0))]}


def faces(part):
    geo = GEOM.get(part["design"])
    if geo is None or geo.get("maske_unbekannt"):
        return {}
    pos = vector(part["pos"])
    q = quaternion(part["rot"]) if "rot" in part else quat_z(part.get("yaw", 0))
    if any(abs(s - 1) > 0.001 for s in vector(part.get("scale", [1, 1, 1]))):
        return {}  # Kopierte skalierte Teile dürfen keine geratenen Anschlüsse liefern.
    result = {}
    for side, z, sign in (("oben", geo["h"], 1), ("unten", 0, -1)):
        points = [tuple(pos[i] + p[i] for i in range(3)) for u, v in cells(geo, side)
                  for p in [rotate(q, (u*25, -v*25, z))]]
        if points:
            result[side] = (geo[side], rotate(q, (0, 0, sign)), points)
    return result


def contact_count(points_a, points_b, tolerance=TOLERANZ):
    """Noppenabstand 25: innerhalb 0,15 Einheiten gibt es höchstens einen Partner."""
    return sum(any(sum((x-y)**2 for x, y in zip(a, b)) <= tolerance**2
                   for b in points_b) for a in points_a)


def connect(parts):
    """Bekannte Ober-/Unterflächen in voller 3D-Lage; keine Seitenports erfinden."""
    surfaces = [faces(p) for p in parts]
    result = set()
    for a, fa in enumerate(surfaces):
        if "oben" not in fa:
            continue
        field_a, normal_a, points_a = fa["oben"]
        for b, fb in enumerate(surfaces):
            if a == b or "unten" not in fb:
                continue
            field_b, normal_b, points_b = fb["unten"]
            if sum(x*y for x, y in zip(normal_a, normal_b)) > -0.9999:
                continue
            # Schneller Ebenentest, bevor alle Noppen verglichen werden.
            if abs(sum((points_b[0][i]-points_a[0][i])*normal_a[i] for i in range(3))) > TOLERANZ:
                continue
            n = contact_count(points_a, points_b)
            if n:
                result.add((a, b, field_a, field_b, n) if a < b
                           else (b, a, field_b, field_a, n))
    return sorted(result)


def unreachable(count, connections, roots, exempt=()):
    adjacency = [set() for _ in range(count)]
    for a, b in connections:
        if not 0 <= a < count or not 0 <= b < count or a == b:
            raise ValueError(f"Ungültige Verbindungsindizes: {a}, {b}")
        adjacency[a].add(b)
        adjacency[b].add(a)
    reached = set(roots)
    todo = list(reached)
    while todo:
        for other in adjacency[todo.pop()] - reached:
            reached.add(other)
            todo.append(other)
    return sorted(set(range(count)) - reached - set(exempt))

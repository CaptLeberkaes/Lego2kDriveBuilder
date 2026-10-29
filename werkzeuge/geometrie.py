"""Ermittelt Noppen-Zellen eines Teils aus Vorlagen.

Für jede Verbindung des Teils mit einem Partner bekannter Geometrie (siehe GEOM in
baue_fahrzeug.py) werden die berührten Noppen in das lokale Raster des Teils
umgerechnet (Ursprung = Translation, Drehung um die Hochachse).
Aufruf: python geometrie.py <datei.sav> [...] --teile 37352 11211 ...
"""
import collections
import math
import struct
import sys

import gvas
from baue_fahrzeug import GEOM, world_cells


def yaw(q):
    x, y, z, w = q
    if abs(x) > 0.01 or abs(y) > 0.01:
        return None
    return round(math.degrees(2 * math.atan2(z, w))) % 360


def main(paths, wanted):
    res = collections.defaultdict(lambda: collections.Counter())
    for path in paths:
        data = gvas.load(path)["body"]["Data"]
        for key in ("CustomVehicles", "DownloadedVehicles"):
            for v in data.get(key, {}).get("items", []):
                if not v["VehicleName"]:
                    continue
                pg = v["PartGraph"]
                P = [struct.unpack("<I", bytes.fromhex(p)[:4])[0] for p in pg["Parts"]["items"]]
                T = pg["PartTransforms"]["items"]
                for c in pg["Connections"]["items"]:
                    for m, o, fm in ((c["PartIndexA"], c["PartIndexB"], c["FieldIndexA"]),
                                     (c["PartIndexB"], c["PartIndexA"], c["FieldIndexB"])):
                        if P[m] not in wanted or P[o] not in GEOM:
                            continue
                        ym, yo = yaw(T[m]["Rotation"]), yaw(T[o]["Rotation"])
                        if ym is None or yo is None or ym % 90 or yo % 90:
                            continue
                        zm, zo = T[m]["Translation"][2], T[o]["Translation"][2]
                        go = GEOM[P[o]]
                        if abs(zo + go["h"] - zm) < 0.6:
                            side, key2 = "unten", "oben"   # Teil sitzt auf Partner
                        elif abs(zo - zm) > 0.6:
                            side, key2 = "oben", "unten"   # Partner sitzt auf Teil
                        else:
                            continue
                        cells = world_cells(P[o], T[o]["Translation"], yo, key2)
                        ox, oy = T[m]["Translation"][:2]
                        a = math.radians(-ym)
                        ca, sa = round(math.cos(a)), round(math.sin(a))
                        for wx, wy in cells:
                            dx, dy = wx - ox, wy - oy
                            lx, ly = dx * ca - dy * sa, dx * sa + dy * ca
                            if abs(lx) < 200 and abs(ly) < 200:
                                res[(P[m], side, fm)][(round(lx / 25), round(-ly / 25))] += 1
                        if side == "oben":
                            res[(P[m], "hoehe", fm)][round(zo - zm)] += 1
    for k in sorted(res):
        print(k, dict(res[k].most_common(12)))


if __name__ == "__main__":
    args = sys.argv[1:]
    i = args.index("--teile")
    main(args[:i], {int(x) for x in args[i + 1:]})

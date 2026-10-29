"""Legt ein neues Fahrzeug in ArtemisVehicle.sav an.

Chassis und Räder werden von einem vorhandenen Fahrzeug (Vorlage) übernommen,
die Karosserie kommt aus einem Bauplan (JSON). Verbindungen werden aus den
Noppenpositionen berechnet.

Aufruf: python baue_fahrzeug.py <quelle.sav> <ziel.sav> <bauplan.json>

Bauplan:
{
  "name": "test1", "vorlage_datei": "…", "vorlage_name": "Brute Chopper",
  "teile": [{"teil": 3004, "farbe": 7, "pos": [x, y, z], "dreh": 0, "leuchtend": false}, ...]
}
pos = Mittelpunkt der Ecknoppe (lokal 0,0) in Einheiten (1 Noppe = 25), z = Unterkante.
dreh = Drehung um die Hochachse in Grad (0, 90, 180, 270).
Lokales Raster: Länge entlang +x, Breite entlang -y.
"""
import copy
import json
import math
import os
import struct
import sys
import time
import uuid

import gvas_rw as g

# Geometrie je Teil: Länge, Breite (Noppen), Höhe (Einheiten), Felder unten/oben,
# optional eigene Zellen für Unterseite/Noppen (lokale (u, v), v nach -y)
GEOM = {
    3001: dict(l=4, w=2, h=30, unten=0, oben=1),
    3004: dict(l=2, w=1, h=30, unten=1, oben=0),
    3005: dict(l=1, w=1, h=30, unten=1, oben=0),
    3003: dict(l=2, w=2, h=30, unten=1, oben=0),
    3022: dict(l=2, w=2, h=10, unten=1, oben=0),
    3010: dict(l=4, w=1, h=30, unten=1, oben=0),
    3622: dict(l=3, w=1, h=30, unten=1, oben=0),
    3020: dict(l=4, w=2, h=10, unten=1, oben=0),
    3023: dict(l=2, w=1, h=10, unten=1, oben=0),
    3024: dict(l=1, w=1, h=10, unten=1, oben=0),
    3710: dict(l=4, w=1, h=10, unten=1, oben=0),
    3666: dict(l=6, w=1, h=10, unten=1, oben=0),
    3832: dict(l=10, w=2, h=10, unten=1, oben=0),
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
    # Bogen links ungedreht, rechts um 180° gedreht einsetzen
    98282: dict(l=2, w=1, h=30, unten=0, oben=1),
    3823: dict(l=4, w=2, h=60, unten=0, oben=1),  # Spiel zählt 3 Noppen je Reihe
    # Chassis-Platte von PoliceTruck_7032 (4x10, Mittelloch, Radausschnitte)
    4212: dict(l=10, w=4, h=10, unten=1, oben=0,
               oben_zellen=[(u, v) for v in (1, 2) for u in range(10) if u not in (4, 5)]
               + [(u, v) for v in (0, 3) for u in (0, 3, 4, 5, 6, 9)]),
}


def quat_z(deg):
    a = math.radians(deg) / 2
    s, c = math.sin(a), math.cos(a)
    return (0.0, 0.0, -s, -c) if c < 0 else (0.0, 0.0, s, c)


def yaw_of(q):
    x, y, z, w = q
    return round(math.degrees(2 * math.atan2(z, w))) % 360


def cells(geo, key):
    if key + "_zellen" in geo:
        return geo[key + "_zellen"]
    return [(u, v) for u in range(geo["l"]) for v in range(geo["w"])]


def world_cells(design, pos, yaw, key):
    geo = GEOM[design]
    c, s = round(math.cos(math.radians(yaw))), round(math.sin(math.radians(yaw)))
    out = set()
    for u, v in cells(geo, key):
        lx, ly = u * 25, -v * 25
        out.add((round(pos[0] + lx * c - ly * s, 1), round(pos[1] + lx * s + ly * c, 1)))
    return out


def connect(parts):
    """parts: list of dict(design, pos, yaw); returns connection tuples."""
    conns = []
    for a, pa in enumerate(parts):
        for b, pb in enumerate(parts):
            if a == b or pa["design"] not in GEOM or pb["design"] not in GEOM:
                continue
            ga, gb = GEOM[pa["design"]], GEOM[pb["design"]]
            if ga["oben"] is None or gb["unten"] is None:
                continue
            if abs(pa["pos"][2] + ga["h"] - pb["pos"][2]) > 0.5:
                continue
            n = len(world_cells(pa["design"], pa["pos"], pa["yaw"], "oben")
                    & world_cells(pb["design"], pb["pos"], pb["yaw"], "unten"))
            if n:
                # a liegt unten (Noppen), b sitzt oben (Unterseite)
                if a < b:
                    conns.append((a, b, ga["oben"], gb["unten"], n))
                else:
                    conns.append((b, a, gb["unten"], ga["oben"], n))
    return conns


def set_prop(props, name, raw):
    g.get(props, name).value = raw


def main(src, dst, plan_path):
    plan = json.load(open(plan_path, encoding="utf-8"))
    f = g.SaveFile(src)
    data = g.val(f.props, "Data")
    vehicles = g.val(data, "CustomVehicles")
    if "vorlage_datei" in plan:
        pool = g.val(g.val(g.SaveFile(os.path.expandvars(plan["vorlage_datei"])).props, "Data"), "DownloadedVehicles").elems
    else:
        pool = vehicles.elems
    tpl = next(v for v in pool if g.val(v, "VehicleName") == g.wstr(plan["vorlage_name"]))
    veh = copy.deepcopy(tpl)
    # als eigenes, neu erstelltes Fahrzeug kennzeichnen (Spieler-ID von eigenem Fahrzeug)
    own_id = next((g.val(v, "ImmediateCreatorId") for v in vehicles.elems
                   if g.val(v, "ImmediateCreatorId") != b"\0\0\0\0"), b"\0\0\0\0")
    for name in ("OriginalCreatorId", "ImmediateCreatorId"):
        set_prop(veh, name, own_id)
    for name in ("OriginalParentGuid", "ImmediateParentGuid"):
        set_prop(veh, name, bytes(16))
    set_prop(veh, "ParentType", g.wstr("ECustomVehicleParentType::Created"))
    pg = g.val(veh, "PartGraph")
    parts_a, tfs_a = g.val(pg, "Parts"), g.val(pg, "PartTransforms")
    asm_a, con_a = g.val(pg, "Assemblies"), g.val(pg, "Connections")

    # Chassis + Räder behalten, alles andere (Karosserie, Flairs) entfernen
    chassis, wheels = [], []
    for a in asm_a.elems:
        if b"/Chassis/" in g.val(a, "AssemblyAsset"):
            chassis.append(a)
        elif b"Wheel" in g.val(a, "AssemblyType"):
            wheels.append(a)

    def rng(a):
        off = struct.unpack("<H", g.val(a, "PartOffset"))[0]
        n = struct.unpack("<H", g.val(a, "NumParts"))[0]
        return list(range(off, off + n))

    old_chassis = [i for a in chassis for i in rng(a)]
    old_wheels = [i for a in wheels for i in rng(a)]
    body = plan["teile"]
    n_ch = len(old_chassis)
    new_index = {old: k for k, old in enumerate(old_chassis)}
    for k, old in enumerate(old_wheels):
        new_index[old] = n_ch + len(body) + k

    tf_tpl = tfs_a.elems[old_chassis[0]]
    new_parts, new_tfs = [], []
    chassis_colors = {int(k): c for k, c in plan.get("chassisfarben", {}).items()}
    for old in old_chassis:
        b = bytearray(parts_a.elems[old])
        design = struct.unpack("<I", b[:4])[0]
        if design in chassis_colors:
            b[4] = chassis_colors[design]
        new_parts.append(bytes(b))
        new_tfs.append(tfs_a.elems[old])
    geo_parts = []
    for old in old_chassis:
        b = parts_a.elems[old]
        t = tfs_a.elems[old]
        geo_parts.append(dict(design=struct.unpack("<I", b[:4])[0],
                              pos=struct.unpack("<fff", g.val(t, "Translation")),
                              yaw=yaw_of(struct.unpack("<ffff", g.val(t, "Rotation")))))
    for t in body:
        flag = 1 if t.get("leuchtend") else 0
        new_parts.append(struct.pack("<IBBBB", t["teil"], t["farbe"], flag, 0, 0))
        tf = copy.deepcopy(tf_tpl)
        set_prop(tf, "Rotation", struct.pack("<ffff", *quat_z(t.get("dreh", 0))))
        set_prop(tf, "Translation", struct.pack("<fff", *t["pos"]))
        new_tfs.append(tf)
        geo_parts.append(dict(design=t["teil"], pos=t["pos"], yaw=t.get("dreh", 0) % 360))
    # Felgenfarbe je Rad (fl/fr/bl/br), überschreibt chassisfarben
    felgen = {}
    for a in wheels:
        name = g.val(a, "AssemblyName")[4:-1].decode()
        if name in plan.get("felgen", {}):
            felgen[rng(a)[0]] = plan["felgen"][name]
    # Radtausch: {"fl": "Fahrzeugname"} übernimmt die Rad-Baugruppe gleichen Namens
    # aus einem anderen Fahrzeug (Felge zuerst, Reifen zuletzt). Lage: x/z der alten
    # Felge, Reifenebene (y) wie beim alten Reifen.
    swaps = plan.get("radtausch", {})
    for i, a in enumerate(wheels):
        name = g.val(a, "AssemblyName")[4:-1].decode()
        idx = rng(a)
        if name in swaps:
            src_v = next(v for v in vehicles.elems + pool
                         if g.val(v, "VehicleName") == g.wstr(swaps[name]))
            spg = g.val(src_v, "PartGraph")
            sa = next(x for x in g.val(spg, "Assemblies").elems
                      if g.val(x, "AssemblyName") == g.val(a, "AssemblyName"))
            sidx = rng(sa)
            assert len(sidx) == len(idx), "Rad-Baugruppen mit anderer Teilezahl"
            old_rim = struct.unpack("<fff", g.val(tfs_a.elems[idx[0]], "Translation"))
            old_tire_y = struct.unpack("<fff", g.val(tfs_a.elems[idx[-1]], "Translation"))[1]
            s_tire_y = struct.unpack("<fff", g.val(g.val(spg, "PartTransforms").elems[sidx[-1]], "Translation"))[1]
            for k, si in enumerate(sidx):
                parts_a.elems[idx[k]] = g.val(spg, "Parts").elems[si]
                tf = copy.deepcopy(g.val(spg, "PartTransforms").elems[si])
                sy = struct.unpack("<fff", g.val(tf, "Translation"))[1]
                set_prop(tf, "Translation", struct.pack("<fff", old_rim[0], old_tire_y + sy - s_tire_y, old_rim[2]))
                tfs_a.elems[idx[k]] = tf
            new_a = copy.deepcopy(sa)
            wheels[i] = new_a
    for old in old_wheels:
        b = bytearray(parts_a.elems[old])
        design = struct.unpack("<I", b[:4])[0]
        if design in chassis_colors:
            b[4] = chassis_colors[design]
        if old in felgen:
            b[4] = felgen[old]
        new_parts.append(bytes(b))
        new_tfs.append(tfs_a.elems[old])
    parts_a.elems, tfs_a.elems = new_parts, new_tfs

    # Baugruppen-Offsets neu setzen
    off = 0
    for a in chassis:
        set_prop(a, "PartOffset", struct.pack("<H", off))
        off += struct.unpack("<H", g.val(a, "NumParts"))[0]
    off = n_ch + len(body)
    for a in wheels:
        set_prop(a, "PartOffset", struct.pack("<H", off))
        off += struct.unpack("<H", g.val(a, "NumParts"))[0]
    asm_a.elems = chassis + wheels

    # Verbindungen: bestehende zwischen behaltenen Teilen + neu berechnete
    hinge_tpl = fixed_tpl = None
    kept = []
    for c in con_a.elems:
        a = struct.unpack("<H", g.val(c, "PartIndexA"))[0]
        b = struct.unpack("<H", g.val(c, "PartIndexB"))[0]
        typ = g.val(c, "Type")
        if b"Hinge" in typ:
            hinge_tpl = hinge_tpl or c
        else:
            fixed_tpl = fixed_tpl or c
        if a in new_index and b in new_index:
            c = copy.deepcopy(c)
            set_prop(c, "PartIndexA", struct.pack("<H", new_index[a]))
            set_prop(c, "PartIndexB", struct.pack("<H", new_index[b]))
            kept.append(c)
    new_conns = connect(geo_parts)
    chassis_ids = set(range(n_ch))
    for a, b, fa, fb, n in new_conns:
        if a in chassis_ids and b in chassis_ids:
            continue  # Chassis-intern bereits vorhanden
        c = copy.deepcopy(fixed_tpl if n > 1 else hinge_tpl)
        set_prop(c, "PartIndexA", struct.pack("<H", a))
        set_prop(c, "PartIndexB", struct.pack("<H", b))
        set_prop(c, "FieldIndexA", bytes([fa]))
        set_prop(c, "FieldIndexB", bytes([fb]))
        set_prop(c, "Strength", bytes([n]))
        kept.append(c)
    con_a.elems = kept

    # Rest des Fahrzeugs
    set_prop(veh, "VehicleName", g.wstr(plan["name"]))
    set_prop(veh, "Guid", uuid.uuid4().bytes)
    g.val(veh, "Sockets").elems = []
    set_prop(veh, "FlairTriggers", struct.pack("<i", 0))
    set_prop(veh, "VersionId", struct.pack("<I", 1))
    ticks = int((time.time() + 62135596800) * 10_000_000)
    set_prop(veh, "LastEdited", struct.pack("<q", ticks))
    for name in ("StudOccluders", "StudOffsets"):
        set_prop(pg, name, struct.pack("<i", 0))
    set_prop(pg, "StudOcclusionHash", struct.pack("<I", 0))

    # gleichnamiges Fahrzeug ersetzen (Guid behalten), sonst freien Platz nehmen
    name_raw = g.wstr(plan["name"])
    slot = next((i for i, v in enumerate(vehicles.elems) if g.val(v, "VehicleName") == name_raw), None)
    if slot is not None:
        set_prop(veh, "Guid", g.val(vehicles.elems[slot], "Guid"))
    else:
        slot = next(i for i, v in enumerate(vehicles.elems) if g.val(v, "VehicleName") == b"\0\0\0\0")
    vehicles.elems[slot] = veh
    f.save(dst)

    # Bericht
    body_ids = set(range(n_ch, n_ch + len(body)))
    linked = {x for a, b, *_ in new_conns for x in (a, b)}
    print(f"Platz {slot}: {plan['name']} – {len(new_parts)} Teile, {len(kept)} Verbindungen")
    for i in sorted(body_ids - linked):
        print("  WARNUNG: Teil ohne Verbindung:", i, body[i - n_ch])
    for a, b, fa, fb, n in new_conns:
        print(f"  {a:3d} ({geo_parts[a]['design']}) F{fa} -> {b:3d} ({geo_parts[b]['design']}) F{fb}  Noppen {n}")


if __name__ == "__main__":
    main(*sys.argv[1:4])

"""Tauscht Platzhalter-Teile in einem Fahrzeug gegen andere Teile.

Aufruf: python tausche_teile.py <quelle.sav> <ziel.sav> <tausch.json>

tausch.json:
{"fahrzeug": "Neues Fahrzeug 04",
 "teile": [{"von": 99207, "nach": 3956, "farbe": 11,
            "pos": [x, y, z],            (optional, sonst bleibt die Lage)
            "rot": [x, y, z, w]}],       (optional)
 "verbindungen": [{"a": 99207, "b": 4032, "fa": 0, "fb": 1, "noppen": 4}]}
Verbindungen werden über die ALTEN Teilenummern gefunden und angepasst.
Jede alte Teilenummer darf im Fahrzeug nur einmal vorkommen; sonst "#<index>" angeben.
Eine vorhandene Garagen-Arbeitskopie (AncillaryCustomVehicle) wird mitgetauscht, sonst
stellt das Spiel beim Start den alten Stand daraus wieder her.
"""
import json
import struct
import sys

import gvas_rw as g
from baue_fahrzeug import connection, integer, text_value
from baugeometrie import vector, quaternion


def main(src, dst, plan_path):
    plan = json.load(open(plan_path, encoding="utf-8"))
    f = g.SaveFile(src)
    data = g.val(f.props, "Data")
    vehicles = g.val(data, "CustomVehicles").elems
    slots = [i for i, v in enumerate(vehicles) if text_value(v, "VehicleName") == plan["fahrzeug"]]
    if len(slots) != 1:
        raise ValueError(f"Fahrzeug {plan['fahrzeug']} {len(slots)}x gefunden")
    targets = [vehicles[slots[0]]]
    if any(p.name == "AncillaryCustomVehicle" for p in data):
        anc = g.val(data, "AncillaryCustomVehicle")
        ancillary_slot = struct.unpack("<i", g.val(data, "AncillaryCustomSlot"))[0]
        if ancillary_slot == slots[0]:
            print("Garagen-Arbeitskopie gefunden, wird mitgetauscht")
            targets.append(anc)
    for veh in targets:
        swap(veh, plan)
    f.save(dst)


def swap(veh, plan):
    pg = g.val(veh, "PartGraph")
    parts, tfs = g.val(pg, "Parts").elems, g.val(pg, "PartTransforms").elems
    ids = [struct.unpack("<I", p[:4])[0] for p in parts]

    def index_of(design):
        if isinstance(design, str) and design.startswith("#"):
            return integer(int(design[1:]), len(ids)-1, "Teileindex")
        hits = [i for i, d in enumerate(ids) if d == design]
        if len(hits) != 1:
            raise ValueError(f"Teil {design} kommt {len(hits)}x vor")
        return hits[0]

    where = {}
    for t in plan["teile"]:
        i = index_of(t["von"])
        if i in where.values():
            raise ValueError(f"Teilindex {i} wird mehrfach getauscht")
        where[t["von"]] = i
        integer(t["nach"], 2**32-1, "Neue Teilenummer", 1)
        if "farbe" in t:
            integer(t["farbe"], 255, "Farbe")
        if "pos" in t:
            vector(t["pos"])
        if "rot" in t:
            quaternion(t["rot"])
    for c in plan.get("verbindungen", []):
        a = where[c["a"]] if c["a"] in where else index_of(c["a"])
        b = where[c["b"]] if c["b"] in where else index_of(c["b"])
        if a == b:
            raise ValueError("Eine Verbindung benötigt zwei verschiedene Teile")
        validated = connection(a, b, c["fa"], c["fb"], c["noppen"], c.get("typ"))
        found = False
        for con in g.val(pg, "Connections").elems:
            pa = struct.unpack("<H", g.val(con, "PartIndexA"))[0]
            pb = struct.unpack("<H", g.val(con, "PartIndexB"))[0]
            if {pa, pb} == {a, b}:
                found = True
                fa, fb = (c["fa"], c["fb"]) if pa == a else (c["fb"], c["fa"])
                g.get(con, "FieldIndexA").value = bytes([fa])
                g.get(con, "FieldIndexB").value = bytes([fb])
                g.get(con, "Strength").value = bytes([c["noppen"]])
                g.get(con, "Type").value = g.val(validated, "Type")
                print(f"Verbindung {pa}-{pb}: Felder {fa}/{fb}, {c['noppen']} Noppen")
        if not found:
            raise ValueError(f"Verbindung {a}-{b} existiert nicht; nichts geschrieben")
    for t in plan["teile"]:
        i = where[t["von"]]
        b = bytearray(parts[i])
        b[0:4] = struct.pack("<I", t["nach"])
        if "farbe" in t:
            b[4] = t["farbe"]
        parts[i] = bytes(b)
        if "pos" in t:
            g.get(tfs[i], "Translation").value = struct.pack("<fff", *vector(t["pos"]))
        if "rot" in t:
            g.get(tfs[i], "Rotation").value = struct.pack("<ffff", *quaternion(t["rot"]))
        print(f"Teil {i}: {t['von']} -> {t['nach']}")


if __name__ == "__main__":
    main(*sys.argv[1:4])

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


def main(src, dst, plan_path):
    plan = json.load(open(plan_path, encoding="utf-8"))
    f = g.SaveFile(src)
    data = g.val(f.props, "Data")
    targets = [v for v in g.val(data, "CustomVehicles").elems
               if g.val(v, "VehicleName") == g.wstr(plan["fahrzeug"])]
    assert len(targets) == 1, f"Fahrzeug {plan['fahrzeug']} {len(targets)}x gefunden"
    if any(p.name == "AncillaryCustomVehicle" for p in data):
        anc = g.val(data, "AncillaryCustomVehicle")
        if g.val(anc, "VehicleName") == g.wstr(plan["fahrzeug"]):
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
            return int(design[1:])  # direkte Teilenummer im Fahrzeug, z.B. "#4"
        hits = [i for i, d in enumerate(ids) if d == design]
        assert len(hits) == 1, f"Teil {design} kommt {len(hits)}x vor"
        return hits[0]

    where = {t["von"]: index_of(t["von"]) for t in plan["teile"]}
    for c in plan.get("verbindungen", []):
        a, b = where.get(c["a"]) or index_of(c["a"]), where.get(c["b"]) or index_of(c["b"])
        for con in g.val(pg, "Connections").elems:
            pa = struct.unpack("<H", g.val(con, "PartIndexA"))[0]
            pb = struct.unpack("<H", g.val(con, "PartIndexB"))[0]
            if {pa, pb} == {a, b}:
                fa, fb = (c["fa"], c["fb"]) if pa == a else (c["fb"], c["fa"])
                g.get(con, "FieldIndexA").value = bytes([fa])
                g.get(con, "FieldIndexB").value = bytes([fb])
                g.get(con, "Strength").value = bytes([c["noppen"]])
                typ = "ELegoConnectResult::" + ("HingeConnection" if c["noppen"] == 1 else "FixedConnection")
                g.get(con, "Type").value = g.wstr(typ)
                print(f"Verbindung {pa}-{pb}: Felder {fa}/{fb}, {c['noppen']} Noppen")
    for t in plan["teile"]:
        i = where[t["von"]]
        b = bytearray(parts[i])
        b[0:4] = struct.pack("<I", t["nach"])
        if "farbe" in t:
            b[4] = t["farbe"]
        parts[i] = bytes(b)
        if "pos" in t:
            g.get(tfs[i], "Translation").value = struct.pack("<fff", *t["pos"])
        if "rot" in t:
            g.get(tfs[i], "Rotation").value = struct.pack("<ffff", *t["rot"])
        print(f"Teil {i}: {t['von']} -> {t['nach']}")


if __name__ == "__main__":
    main(*sys.argv[1:4])

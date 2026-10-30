"""Fahrzeug aus einem JSON-Bauplan bauen; vor jedem Schreiben vollständig prüfen.

Aufruf: baue_fahrzeug.py quelle.sav ziel.sav plan.json [--pruefen] [--bericht datei.json]
Geometrie: baugeometrie.py; Noppe=25, Platte=10. rot=[x,y,z,w] oder dreh=Grad.
Referenzen: Teile-id bzw. teil:0, chassis:0, rad:fl:0, modul:<alte Assemblynummer>:0.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import struct
import time
import uuid

import gvas_rw as g
from baugeometrie import (GEOM, cells, world_cells, connect, quat_z, yaw_of,
                          quaternion, vector, rotate, multiply, conjugate, unreachable, faces)
from teilewissen import Library, DEFAULT_PATH as KNOWLEDGE_PATH

TYPES = {"HingeConnection", "FixedConnection", "CylindricalConnection",
         "PrismaticConnection", "BallConnection"}


def text_value(props, name):
    return g.R(g.val(props, name)).fstr()


def set_prop(props, name, raw):
    g.get(props, name).value = raw


def indices(assembly):
    off = struct.unpack("<H", g.val(assembly, "PartOffset"))[0]
    n = struct.unpack("<H", g.val(assembly, "NumParts"))[0]
    return list(range(off, off+n))


def connection_indices(c):
    return tuple(struct.unpack("<H", g.val(c, key))[0] for key in ("PartIndexA", "PartIndexB"))


def integer(value, maximum, label, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{label}: Ganzzahl von {minimum} bis {maximum} erwartet")
    return value


def connection(a, b, fa, fb, strength, kind=None):
    integer(a, 65535, "PartIndexA"); integer(b, 65535, "PartIndexB")
    integer(fa, 255, "FieldIndexA"); integer(fb, 255, "FieldIndexB")
    integer(strength, 255, "Stärke", 1)
    kind = kind or ("HingeConnection" if strength == 1 else "FixedConnection")
    kind = kind.removeprefix("ELegoConnectResult::")
    if kind not in TYPES or (kind == "FixedConnection" and strength < 2) or (kind != "FixedConnection" and strength != 1):
        raise ValueError(f"Unpassender Verbindungstyp/Stärke: {kind}/{strength}")
    return [g.Prop("PartIndexA", "UInt16Property", struct.pack("<H", a)),
            g.Prop("PartIndexB", "UInt16Property", struct.pack("<H", b)),
            g.Prop("FieldIndexA", "ByteProperty", bytes([fa]), hdr={"enum": "None"}),
            g.Prop("FieldIndexB", "ByteProperty", bytes([fb]), hdr={"enum": "None"}),
            g.Prop("Strength", "ByteProperty", bytes([strength]), hdr={"enum": "None"}),
            g.Prop("Type", "EnumProperty", g.wstr("ELegoConnectResult::"+kind), hdr={"enum": "ELegoConnectResult"})]


def validate_plan(plan):
    if not isinstance(plan, dict):
        raise ValueError("Der Bauplan muss ein JSON-Objekt sein")
    allowed = {"name", "vorlage_name", "vorlage_datei", "teile", "chassisfarben",
               "felgen", "radtausch", "behalten", "verbindungen", "fahrer", "teilewissen"}
    if set(plan)-allowed:
        raise ValueError(f"Unbekannte Bauplanfelder: {sorted(set(plan)-allowed)}")
    for key in ("name", "vorlage_name"):
        if not isinstance(plan.get(key), str) or not plan[key].strip():
            raise ValueError(f"{key}: nichtleerer Name erforderlich")
    if not isinstance(plan.get("teile"), list):
        raise ValueError("teile muss eine Liste sein")
    if not isinstance(plan.get("verbindungen", []), list) or not isinstance(plan.get("behalten", []), list):
        raise ValueError("verbindungen und behalten müssen Listen sein")
    if any(not isinstance(x, str) for x in plan.get("behalten", [])):
        raise ValueError("behalten muss Namen als Zeichenketten enthalten")
    if "vorlage_datei" in plan and not isinstance(plan["vorlage_datei"], str):
        raise ValueError("vorlage_datei muss ein Pfad sein")
    knowledge = plan.get('teilewissen', True)
    if not isinstance(knowledge, (bool, str)) or knowledge == '':
        raise ValueError('teilewissen muss true, false oder ein Bibliothekspfad sein')
    if len(plan["teile"]) > 65535:
        raise ValueError("Zu viele Teile für UInt16-Indizes")
    names = set()
    for i, part in enumerate(plan["teile"]):
        if not isinstance(part, dict) or set(part)-{"id", "teil", "farbe", "pos", "dreh", "rot", "leuchtend", "anschluss"}:
            raise ValueError(f"Teil {i}: ungültige oder unbekannte Felder")
        integer(part.get("teil"), 2**32-1, f"Teil {i}: Nummer", 1)
        integer(part.get("farbe"), 255, f"Teil {i}: Farbe")
        if 'anschluss' in part:
            spec = part['anschluss']
            if (not isinstance(spec, dict) or set(spec) != {'an', 'vorlage'}
                    or not all(isinstance(x, str) and x for x in spec.values())):
                raise ValueError('anschluss: an und vorlage als nichtleere Zeichenketten erforderlich')
            if any(k in part for k in ('pos', 'dreh', 'rot')):
                raise ValueError('anschluss ersetzt pos/rot/dreh; keine konkurrierenden Lagen angeben')
        else:
            vector(part.get("pos"))
        if "rot" in part and "dreh" in part:
            raise ValueError(f"Teil {i}: entweder rot oder dreh angeben")
        quaternion(part["rot"]) if "rot" in part else quat_z(part.get("dreh", 0))
        if not isinstance(part.get("leuchtend", False), bool):
            raise ValueError(f"Teil {i}: leuchtend muss true/false sein")
        name = part.get("id", f"teil:{i}")
        if not isinstance(name, str) or not name or name in names or name.startswith(("chassis:", "rad:", "modul:")):
            raise ValueError(f"Teil {i}: ungültige/doppelte id {name!r}")
        names.add(name)
        uncertain = part["teil"] not in GEOM or GEOM[part["teil"]].get("maske_unbekannt")
        if uncertain and not plan.get("verbindungen") and knowledge is False:
            raise ValueError(f"Teil {i} ({part['teil']}): Anschlussgeometrie unbekannt; explizite Verbindungen erforderlich")
    for key in ("chassisfarben", "felgen", "radtausch"):
        if not isinstance(plan.get(key, {}), dict):
            raise ValueError(f"{key} muss ein Objekt sein")
    for key in ("chassisfarben", "felgen"):
        for color in plan.get(key, {}).values():
            integer(color, 255, key)
    return plan


def load_knowledge(plan):
    choice = plan.get('teilewissen', True)
    if choice is False:
        return None
    path = Path(os.path.expandvars(choice)) if isinstance(choice, str) else KNOWLEDGE_PATH
    if isinstance(choice, str) or path.exists():
        return Library.load(path)
    return None


def place_parts(parts, anchors, library):
    """Kontaktbasierte Lagen in Abhängigkeitsreihenfolge auflösen, ohne Reihenfolge zu ändern."""
    poses = dict(anchors); pending = list(enumerate(parts)); resolved = {}
    while pending:
        progress = False
        for i, part in pending[:]:
            name = part.get('id', f'teil:{i}')
            if 'anschluss' not in part:
                p = dict(design=part['teil'], pos=part['pos'],
                         rot=part.get('rot', quat_z(part.get('dreh', 0))), scale=[1,1,1])
            else:
                spec = part['anschluss']
                if spec['an'] not in poses:
                    continue
                if library is None:
                    raise ValueError('Kontaktplatzierung benötigt eine Teilewissen-Bibliothek')
                p = library.place(poses[spec['an']], spec['vorlage'])
                if p['design'] != part['teil'] or any(abs(s-1) > .001 for s in p['scale']):
                    raise ValueError('Kontaktvorlage passt nicht zu Teilenummer/Einheitsskalierung')
            poses[name] = poses[f'teil:{i}'] = p; resolved[i] = p
            pending.remove((i, part)); progress = True
        if not progress:
            raise ValueError('Kontaktplatzierung: unbekannte Anker oder zyklische Abhängigkeit')
    return [resolved[i] for i in range(len(parts))]


def pool_from(save):
    data = g.val(save.props, "Data")
    return [v for key in ("CustomVehicles", "DownloadedVehicles")
            for p in data if p.name == key for v in p.value.elems]


def find_vehicle(pool, name):
    hits = [v for v in pool if text_value(v, "VehicleName") == name]
    if len(hits) != 1:
        raise ValueError(f"Vorlage {name!r}: {len(hits)} Treffer; eindeutige Quelle/Name erforderlich")
    return hits[0]


def read_triggers(vehicle):
    r = g.R(g.val(vehicle, "FlairTriggers"))
    values = [r.fstr() for _ in range(r.i32())]
    if r.p != len(r.d):
        raise ValueError("FlairTriggers enthält unerwartete Daten")
    return values


def is_flair(assembly):
    return "/Flair/" in text_value(assembly, "AssemblyAsset")


def build_vehicle(src, plan):
    """Reine Vorbereitung: liest Quelle, erzeugt Ergebnis im Speicher, schreibt nichts."""
    validate_plan(plan)
    library = load_knowledge(plan)
    for i, part in enumerate(plan['teile']):
        if (part['teil'] not in GEOM or GEOM[part['teil']].get('maske_unbekannt')) and not plan.get('verbindungen'):
            if library is None or str(part['teil']) not in library.data['parts']:
                raise ValueError(f"Teil {i} ({part['teil']}): Anschlussgeometrie unbekannt; kein Kontaktbeleg vorhanden")
    save = g.SaveFile(src)
    data = g.val(save.props, "Data")
    vehicles = g.val(data, "CustomVehicles").elems
    pool = pool_from(g.SaveFile(os.path.expandvars(plan["vorlage_datei"]))) if "vorlage_datei" in plan else vehicles
    vehicle = copy.deepcopy(find_vehicle(pool, plan["vorlage_name"]))
    graph = g.val(vehicle, "PartGraph")
    old_parts = g.val(graph, "Parts").elems
    old_tfs = g.val(graph, "PartTransforms").elems
    old_assemblies = g.val(graph, "Assemblies").elems
    old_connections = g.val(graph, "Connections").elems
    if len(old_parts) != len(old_tfs):
        raise ValueError("Vorlage: Parts und PartTransforms haben unterschiedliche Längen")
    for assembly in old_assemblies:
        if any(i >= len(old_parts) for i in indices(assembly)):
            raise ValueError("Vorlage: Baugruppenbereich außerhalb der Teileliste")
    chassis = [a for a in old_assemblies if "/Chassis/" in text_value(a, "AssemblyAsset")]
    wheels = [a for a in old_assemblies if "Wheel" in text_value(a, "AssemblyType")]
    if not chassis or not any(indices(a) for a in chassis):
        raise ValueError("Vorlage enthält kein Chassis")
    if any(not indices(a) for a in chassis + wheels):
        raise ValueError("Vorlage enthält eine leere Chassis-/Rad-Baugruppe")
    selectors = plan.get("behalten", [])
    modules = []
    matched = set()
    for a in old_assemblies:
        if a in chassis or a in wheels:
            continue
        asset = text_value(a, "AssemblyAsset")
        for selector in selectors:
            if not isinstance(selector, str):
                raise ValueError("behalten: Namen oder flairs/baugruppen erforderlich")
            if selector == asset or selector == asset.split("/")[-1].split(".")[0] or selector == ("flairs" if is_flair(a) else "baugruppen"):
                matched.add(selector)
                if a not in modules:
                    modules.append(a)
    if set(selectors)-matched:
        raise ValueError(f"behalten: nicht gefundene Baugruppen {sorted(set(selectors)-matched)}")
    slot_hits = [i for i, v in enumerate(vehicles) if text_value(v, "VehicleName") == plan["name"]]
    if len(slot_hits) > 1:
        raise ValueError("Mehrere Fahrzeuge mit dem Zielnamen; eindeutigen Namen verwenden")
    ancillary = next((p.value for p in data if p.name == "AncillaryCustomSlot"), None)
    ancillary_slot = struct.unpack("<i", ancillary)[0] if ancillary is not None else None
    free = [i for i, v in enumerate(vehicles) if not text_value(v, "VehicleName") and i != ancillary_slot]
    if not slot_hits and not free:
        raise ValueError("Kein freier Fahrzeugplatz verfügbar")
    slot = slot_hits[0] if slot_hits else free[0]
    if slot == ancillary_slot:
        raise ValueError("Für den Zielplatz existiert eine Garagen-Arbeitskopie. Garage verlassen, Spiel schließen und erneut ausführen.")

    parts, transforms, assemblies = [], [], []
    mapping, refs, wheel_ids, chassis_ids = {}, {}, set(), set()
    colors = {int(k): v for k, v in plan.get("chassisfarben", {}).items()}
    warnings = []

    def append_part(raw, tf):
        raw = bytearray(raw)
        design = struct.unpack("<I", raw[:4])[0]
        if design in colors:
            raw[4] = colors[design]
        parts.append(bytes(raw)); transforms.append(copy.deepcopy(tf))
        return len(parts)-1

    for a in chassis + modules:
        new_a = copy.deepcopy(a)
        set_prop(new_a, "PartOffset", struct.pack("<H", len(parts)))
        asm_index = old_assemblies.index(a)
        for k, old in enumerate(indices(a)):
            if old in mapping:
                raise ValueError("Überlappende Baugruppenbereiche in der Vorlage")
            new = append_part(old_parts[old], old_tfs[old]); mapping[old] = new
            if a in chassis:
                refs[f"chassis:{len(chassis_ids)}"] = new; chassis_ids.add(new)
            else:
                refs[f"modul:{asm_index}:{k}"] = new
        assemblies.append(new_a)
    body_ids = []
    anchor_poses = {name: dict(design=struct.unpack('<I', parts[i][:4])[0],
                              pos=struct.unpack('<fff', g.val(transforms[i], 'Translation')),
                              rot=struct.unpack('<ffff', g.val(transforms[i], 'Rotation')),
                              scale=struct.unpack('<fff', g.val(transforms[i], 'Scale3D')))
                    for name, i in refs.items()}
    placements = place_parts(plan['teile'], anchor_poses, library)
    tf_template = old_tfs[indices(chassis[0])[0]]
    for i, part in enumerate(plan["teile"]):
        tf = copy.deepcopy(tf_template)
        rot = quaternion(placements[i]['rot'])
        set_prop(tf, "Rotation", struct.pack("<ffff", *rot))
        set_prop(tf, "Translation", struct.pack("<fff", *vector(placements[i]['pos'])))
        set_prop(tf, "Scale3D", struct.pack("<fff", 1, 1, 1))
        new = len(parts)
        parts.append(struct.pack("<IBBBB", part["teil"], part["farbe"], int(part.get("leuchtend", False)), 0, 0))
        transforms.append(tf); body_ids.append(new)
        for ref in {part.get("id", f"teil:{i}"), f"teil:{i}"}:
            if ref in refs:
                raise ValueError(f"Mehrdeutige Teile-Referenz {ref}")
            refs[ref] = new

    wheel_connections = []
    valid_wheel_names = {text_value(a, "AssemblyName") for a in wheels}
    for key in ("radtausch", "felgen"):
        if set(plan.get(key, {}))-valid_wheel_names:
            raise ValueError(f"{key}: unbekannte Radnamen")
    for a in wheels:
        name = text_value(a, "AssemblyName")
        donor_parts, donor_tfs, donor_connections = old_parts, old_tfs, old_connections
        donor_assembly = a
        swap = plan.get("radtausch", {}).get(name)
        delta, shift = (0, 0, 0, 1), (0, 0, 0)
        swapped = swap is not None
        if swapped:
            spec = {"fahrzeug": swap} if isinstance(swap, str) else swap
            if not isinstance(spec, dict) or set(spec)-{"fahrzeug", "datei", "versatz"}:
                raise ValueError("radtausch: Fahrzeugname oder fahrzeug/datei/versatz erforderlich")
            donor_pool = pool_from(g.SaveFile(os.path.expandvars(spec["datei"]))) if "datei" in spec else pool
            donor = find_vehicle(donor_pool, spec.get("fahrzeug"))
            donor_graph = g.val(donor, "PartGraph")
            choices = [x for x in g.val(donor_graph, "Assemblies").elems
                       if "Wheel" in text_value(x, "AssemblyType") and text_value(x, "AssemblyName") == name]
            if len(choices) != 1 or not indices(choices[0]):
                raise ValueError(f"Rad {name}: Spenderbaugruppe fehlt oder ist mehrdeutig")
            donor_assembly = choices[0]
            donor_parts = g.val(donor_graph, "Parts").elems
            donor_tfs = g.val(donor_graph, "PartTransforms").elems
            donor_connections = g.val(donor_graph, "Connections").elems
            old_set = set(indices(a))
            if any((x in old_set) != (y in old_set) for x, y in map(connection_indices, old_connections)):
                raise ValueError(f"Rad {name} besitzt externe Verbindungen; Tausch benötigt eine explizite Anpassung")
            source_tf = donor_tfs[indices(donor_assembly)[0]]
            target_tf = old_tfs[indices(a)[0]]
            sq = quaternion(struct.unpack("<ffff", g.val(source_tf, "Rotation")))
            tq = quaternion(struct.unpack("<ffff", g.val(target_tf, "Rotation")))
            delta = multiply(tq, conjugate(sq))
            source_pos = struct.unpack("<fff", g.val(source_tf, "Translation"))
            target_pos = struct.unpack("<fff", g.val(target_tf, "Translation"))
            offset = vector(spec.get("versatz", [0, 0, 0]))
            rotated_source = rotate(delta, source_pos)
            shift = tuple(target_pos[i]+offset[i]-rotated_source[i] for i in range(3))
            warnings.append(f"Rad {name}: starre Übernahme am ersten Baugruppenteil; Achslage im Spiel prüfen, bei Bedarf versatz setzen")
        new_a = copy.deepcopy(donor_assembly)
        set_prop(new_a, "PartOffset", struct.pack("<H", len(parts)))
        donor_map = {}
        for k, old in enumerate(indices(donor_assembly)):
            tf = copy.deepcopy(donor_tfs[old])
            if swapped:
                pos = rotate(delta, struct.unpack("<fff", g.val(tf, "Translation")))
                set_prop(tf, "Translation", struct.pack("<fff", *(pos[i]+shift[i] for i in range(3))))
                rot = multiply(delta, quaternion(struct.unpack("<ffff", g.val(tf, "Rotation"))))
                set_prop(tf, "Rotation", struct.pack("<ffff", *rot))
            new = append_part(donor_parts[old], tf)
            donor_map[old] = new; wheel_ids.add(new); refs[f"rad:{name}:{k}"] = new
            if not swapped:
                mapping[old] = new
            if name in plan.get("felgen", {}) and parts[new][4] != 255:
                raw = bytearray(parts[new]); raw[4] = plan["felgen"][name]; parts[new] = bytes(raw)
        if swapped:
            for c in donor_connections:
                x, y = connection_indices(c)
                if x in donor_map and y in donor_map:
                    c = copy.deepcopy(c)
                    set_prop(c, "PartIndexA", struct.pack("<H", donor_map[x]))
                    set_prop(c, "PartIndexB", struct.pack("<H", donor_map[y]))
                    wheel_connections.append(c)
        assemblies.append(new_a)
    if len(parts) > 65535:
        raise ValueError("Zu viele Teile für UInt16-Indizes")
    connections = []
    for c in old_connections:
        a, b = connection_indices(c)
        if a in mapping and b in mapping:
            c = copy.deepcopy(c)
            set_prop(c, "PartIndexA", struct.pack("<H", mapping[a]))
            set_prop(c, "PartIndexB", struct.pack("<H", mapping[b]))
            connections.append(c)
    connections.extend(wheel_connections)
    geo_parts = [dict(design=struct.unpack("<I", raw[:4])[0],
                      pos=struct.unpack("<fff", g.val(tf, "Translation")),
                      rot=struct.unpack("<ffff", g.val(tf, "Rotation")),
                      scale=struct.unpack("<fff", g.val(tf, "Scale3D")))
                 for raw, tf in zip(parts, transforms)]
    # Identische massive Standardteile an derselben Lage können keine gültige Konstruktion bilden.
    solids = {3001,3002,3003,3004,3005,3006,3007,3008,3009,3010,3622,44237,6111,6112}
    for i in body_ids:
        for j in range(i):
            if geo_parts[i]['design'] not in solids or geo_parts[j]['design'] != geo_parts[i]['design']:
                continue
            a, b = geo_parts[i], geo_parts[j]
            if (sum((x-y)**2 for x,y in zip(a['pos'], b['pos'])) < .01**2
                    and 1-abs(sum(x*y for x,y in zip(quaternion(a['rot']), quaternion(b['rot'])))) < 1e-7
                    and max(abs(x-y) for x,y in zip(a['scale'], b['scale'])) < .001):
                raise ValueError(f'Identische massive Teile überlagern sich: {j}, {i}')
    automatic = {(a,b,fa,fb,n,'HingeConnection' if n == 1 else 'FixedConnection')
                 for a,b,fa,fb,n in connect(geo_parts)}
    observed = library.connect(geo_parts) if library else {}
    for a, b, fa, fb, n, kind in sorted(automatic):
        if a in body_ids or b in body_ids:
            connections.append(connection(a, b, fa, fb, n, kind))
    added_observed = []
    for key, evidence in observed.items():
        a,b,fa,fb,n,kind = key
        if key in automatic or not (a in body_ids or b in body_ids):
            continue
        # Bekannte Standardflächen dürfen nicht durch widersprüchliche Beobachtungen ersetzt werden.
        known_a = {x[0] for x in faces(geo_parts[a]).values()}
        known_b = {x[0] for x in faces(geo_parts[b]).values()}
        if fa in known_a and fb in known_b:
            continue
        connections.append(connection(a,b,fa,fb,n,kind)); added_observed.append(key)

    def resolve(ref):
        if isinstance(ref, str) and ref in refs:
            return refs[ref]
        if isinstance(ref, int) and not isinstance(ref, bool) and 0 <= ref < len(parts):
            return ref
        raise ValueError(f"Unbekannte Teile-Referenz: {ref!r}")

    manual_pairs = set()
    manual_status = []
    for spec in plan.get("verbindungen", []):
        if not isinstance(spec, dict) or set(spec)-{"a", "b", "fa", "fb", "noppen", "typ"}:
            raise ValueError("verbindungen: unbekannte oder ungültige Felder")
        a, b = resolve(spec.get("a")), resolve(spec.get("b"))
        if a == b:
            raise ValueError("Ein Teil kann nicht mit sich selbst verbunden werden")
        pair = frozenset((a, b))
        if pair not in manual_pairs:
            connections = [c for c in connections if frozenset(connection_indices(c)) != pair]
            manual_pairs.add(pair)
        new_connection = connection(a, b, spec.get("fa"), spec.get("fb"), spec.get("noppen"), spec.get("typ"))
        fa, fb, n = spec['fa'], spec['fb'], spec['noppen']
        kind = text_value(new_connection, 'Type').split('::')[-1]
        key = (a,b,fa,fb,n,kind) if a < b else (b,a,fb,fa,n,kind)
        known_a = {x[0] for x in faces(geo_parts[a]).values()}
        known_b = {x[0] for x in faces(geo_parts[b]).values()}
        if fa in known_a and fb in known_b and key not in automatic:
            raise ValueError(f'Expliziter Anschluss widerspricht bekannten Anschlussflächen: {a}, {b}')
        status = 'geometrisch' if key in automatic else 'beobachtete_paarlage' if key in observed else 'ungeprueft'
        manual_status.append(dict(a=a, b=b, status=status, belege=observed.get(key, [])))
        connections.append(new_connection)
    if manual_pairs:
        unknown = sum(x['status'] == 'ungeprueft' for x in manual_status)
        if unknown:
            warnings.append(f'{unknown} explizite Anschlüsse nur strukturell geprüft; physische Lage ungeprüft')
    retained_observed = [key for key in added_observed if frozenset(key[:2]) not in manual_pairs]
    if retained_observed:
        warnings.append(f'{len(retained_observed)} Anschlüsse aus beobachteten 3D-Paarlagen ergänzt; keine vollständige Formprüfung')
    loose = unreachable(len(parts), list(map(connection_indices, connections)), chassis_ids, wheel_ids)
    if loose:
        unknown = [i for i in loose if geo_parts[i]['design'] not in GEOM or GEOM[geo_parts[i]['design']].get('maske_unbekannt')]
        extra = f' Anschlussgeometrie unbekannt und keine passende Paarlage für {unknown}.' if unknown else ''
        raise ValueError(f"Teile ohne Pfad zum Chassis: {loose}.{extra} Bauplan/Anschlüsse korrigieren; nichts geschrieben.")
    g.val(graph, "Parts").elems = parts
    g.val(graph, "PartTransforms").elems = transforms
    g.val(graph, "Assemblies").elems = assemblies
    g.val(graph, "Connections").elems = connections
    sockets = []
    for socket in g.val(vehicle, "Sockets").elems:
        old = struct.unpack("<i", g.val(socket, "BrickIndex"))[0]
        if old in mapping:
            socket = copy.deepcopy(socket)
            set_prop(socket, "BrickIndex", struct.pack("<i", mapping[old])); sockets.append(socket)
    if "fahrer" in plan:
        driver = plan["fahrer"]
        if not isinstance(driver, dict) or set(driver)-{"teil", "pos", "dreh"}:
            raise ValueError("fahrer: teil, pos und dreh=[Pitch,Yaw,Roll] erwartet")
        sockets = [s for s in sockets if text_value(s, "SocketName") != "TrafficSeat_DriverSit"]
        def native(name, kind, values):
            return g.Prop(name, "StructProperty", struct.pack("<fff", *vector(values)), hdr={"struct": kind, "guid": bytes(16)})
        sockets.append([g.Prop("SocketName", "NameProperty", g.wstr("TrafficSeat_DriverSit")),
                        g.Prop("BrickIndex", "IntProperty", struct.pack("<i", resolve(driver.get("teil")))),
                        native("RelativeLocation", "Vector", driver.get("pos", [0, 0, 0])),
                        native("RelativeRotation", "Rotator", driver.get("dreh", [0, 0, 0])),
                        native("RelativeScale", "Vector", [1, 1, 1])])
    g.val(vehicle, "Sockets").elems = sockets
    triggers = read_triggers(vehicle)
    flairs = [a for a in old_assemblies if is_flair(a)]
    if len(flairs) != len(triggers):
        raise ValueError("Vorlage: Flair-Anzahl stimmt nicht mit FlairTriggers überein")
    selected = [t for a, t in zip(flairs, triggers) if a in modules]
    set_prop(vehicle, "FlairTriggers", struct.pack("<i", len(selected))+b"".join(g.wstr(t) for t in selected))
    removed = [text_value(a, "AssemblyAsset") for a in old_assemblies if a not in chassis+wheels+modules]
    if removed:
        warnings.append("Entfernte Baugruppen: " + ", ".join(removed))
    own_id = next((g.val(v, "ImmediateCreatorId") for v in vehicles if g.val(v, "ImmediateCreatorId") != g.wstr("")), None)
    if own_id is None:
        raise ValueError("Keine eigene Spielerkennung im Quellspielstand gefunden")
    for name in ("OriginalCreatorId", "ImmediateCreatorId"):
        set_prop(vehicle, name, own_id)
    for name in ("OriginalParentGuid", "ImmediateParentGuid"):
        set_prop(vehicle, name, bytes(16))
    set_prop(vehicle, "ParentType", g.wstr("ECustomVehicleParentType::Created"))
    set_prop(vehicle, "VehicleName", g.wstr(plan["name"]))
    set_prop(vehicle, "Guid", g.val(vehicles[slot], "Guid") if slot_hits else uuid.uuid4().bytes)
    set_prop(vehicle, "VersionId", struct.pack("<I", 1))
    set_prop(vehicle, "LastEdited", struct.pack("<q", int((time.time()+62135596800)*10_000_000)))
    for name in ("StudOccluders", "StudOffsets"):
        set_prop(graph, name, struct.pack("<i", 0))
    set_prop(graph, "StudOcclusionHash", struct.pack("<I", 0))
    vehicles[slot] = vehicle
    warnings.append("GarageSaveDataMap bleibt unverändert; Auswirkungen auf Garagen-Metadaten sind im Spiel noch zu prüfen")
    report = {"name": plan["name"], "slot": slot, "teile": len(parts), "verbindungen": len(connections),
              "koerperteile": len(body_ids), "baugruppen": len(assemblies), "warnungen": warnings,
              "referenzen": refs, "lose_teile": [],
              "anschlusspruefung": {"explizit": manual_status,
                                    "beobachtete_ergaenzungen": [dict(kontakt=k, belege=observed[k]) for k in added_observed
                                                                 if frozenset(k[:2]) not in manual_pairs]},
              "geometrie_unbekannt": sorted({p["design"] for i, p in enumerate(geo_parts)
                                             if i not in wheel_ids and (p["design"] not in GEOM
                                                 or GEOM[p["design"]].get("maske_unbekannt"))})}
    return save, report


def main(src, dst, plan_path, pruefen=False, bericht=None):
    with open(plan_path, encoding="utf-8") as stream:
        plan = json.load(stream)
    save, report = build_vehicle(src, plan)
    # Serialisierung auch im Prüfmodus erneut einlesen, ohne eine SAV zu schreiben.
    raw = save.dump()
    if g.SaveFile.from_bytes(raw).dump() != raw:
        raise ValueError("Serialisierungsprüfung fehlgeschlagen")
    if not pruefen:
        save.save(dst)
    if bericht:
        Path(bericht).write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(f"{'Geprüft' if pruefen else 'Geschrieben'}: {report['name']} – Platz {report['slot']}, "
          f"{report['teile']} Teile, {report['verbindungen']} Verbindungen")
    for warning in report["warnungen"]:
        print("HINWEIS:", warning)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("quelle"); parser.add_argument("ziel"); parser.add_argument("bauplan")
    parser.add_argument("--pruefen", action="store_true", help="Nur im Speicher bauen und prüfen")
    parser.add_argument("--bericht", help="Bereinigten JSON-Prüfbericht schreiben")
    args = parser.parse_args()
    try:
        main(args.quelle, args.ziel, args.bauplan, args.pruefen, args.bericht)
    except (ValueError, KeyError, StopIteration, EOFError, OSError) as error:
        parser.exit(2, f"FEHLER: {error}\n")

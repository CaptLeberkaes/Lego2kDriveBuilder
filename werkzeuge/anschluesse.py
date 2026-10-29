"""Wertet Verbindungen aller Fahrzeuge in .sav-Dateien aus.

Ergebnis pro Teilenummer: welche Anschlusspunkte (FieldIndex) vorkommen und ob das
Teil dabei unten (seine Noppen tragen etwas) oder oben (es sitzt auf etwas) lag.
Gelesen werden CustomVehicles, DownloadedVehicles und der Creators-Hub-Cache
(ArtemisChubCache.sav, CachedVehicles). Gleiche Fahrzeuge zählen nur einmal.
Aufruf: python anschluesse.py <datei.sav> [<datei2.sav> ...] [--json ausgabe.json] [--md ausgabe.md]
        python anschluesse.py --alle [...]   (alle Fahrzeug-Spielstände im Spielordner, nur lesen)
        python anschluesse.py --alle "../_sicherungen/*/ArtemisChubCache.sav"   (ältere Cache-Stände dazu)
"""
import collections
import glob
import hashlib
import json
import os
import struct
import sys

import gvas
from geometrie import canonical
from baugeometrie import GEOM

SPIELSTAENDE = os.path.expandvars(r"%USERPROFILE%\Documents\My Games\Artemis\Saved\SaveGames")
FAHRZEUG_DATEIEN = ("ArtemisVehicle.sav", "ArtemisDownloadedVehicle.sav", "ArtemisExtraVehicle.sav",
                    "ArtemisChubCache.sav")


def expand(paths):
    """Platzhalter wie _sicherungen/*/ArtemisChubCache.sav selbst auflösen (PowerShell tut es nicht)."""
    return [p for a in paths for p in (sorted(glob.glob(a)) if glob.has_magic(a) else [a])]


def alle_spielstaende(ordner=SPIELSTAENDE):
    return [p for p in (os.path.join(ordner, n) for n in FAHRZEUG_DATEIEN) if os.path.isfile(p)]


def vehicles_with_source(path):
    """(Liste, Fahrzeug) je benanntem Fahrzeug; Cache-Einträge sind eingebettete Property-Listen."""
    data = gvas.load(path)["body"]["Data"]
    for key in ("CustomVehicles", "DownloadedVehicles"):
        for v in data.get(key, {}).get("items", []):
            if v["VehicleName"]:
                yield key, v
    for _, entry in data.get("CachedVehicles", []):
        v = gvas.read_props(gvas.R(bytes.fromhex(entry["Bytes"]["_bytes"])))
        if v.get("VehicleName"):
            yield "CachedVehicles", v


def vehicles(path):
    for _, v in vehicles_with_source(path):
        yield v


def fingerprint(vehicle):
    """Gleicher Teilegraph = gleiches Fahrzeug, egal in welcher Datei oder Liste."""
    return hashlib.sha1(json.dumps(vehicle["PartGraph"], sort_keys=True, default=str).encode()).hexdigest()


def unique_vehicles(paths):
    seen = set()
    for path in paths:
        for v in vehicles(path):
            key = fingerprint(v)
            if key not in seen:
                seen.add(key)
                yield v


def z_axis(q):
    """Lokale Hochachse eines Teils nach Rotation (Quaternion x, y, z, w)."""
    x, y, z, w = q
    return (2 * (x * z + w * y), 2 * (y * z - w * x), 1 - 2 * (x * x + y * y))


def field_role(design, field):
    """Lokale Anschlussseite; Welt-z allein beweist bei Seitennoppen keine Rolle."""
    geo = GEOM.get(design, {})
    if field == geo.get("oben"):
        return "unten"  # Lokale Oberseite trägt ein anderes Teil.
    if field == geo.get("unten"):
        return "oben"   # Lokale Unterseite sitzt auf einem anderen Teil.
    return "seitlich/gedreht"  # Historischer Schlüssel, schließt unbekannte Felder ein.


def main(paths, out=None, md=None):
    stats = collections.defaultdict(lambda: collections.Counter())
    colors = collections.Counter()
    chassis = collections.Counter()
    assemblies = collections.Counter()
    count = 0
    for v in unique_vehicles(paths):
        count += 1
        pg = v["PartGraph"]
        chassis[(v["ChassisConfig"].split(".")[-1], v["VehicleClass"].split("::")[-1])] += 1
        for a in pg["Assemblies"]["items"]:
            assemblies[a["AssemblyAsset"].split("/Game/LEGO/")[-1].split(".")[0]] += 1
        parts = [bytes.fromhex(p) for p in pg["Parts"]["items"]]
        tfs = pg["PartTransforms"]["items"]
        design = [struct.unpack("<I", b[:4])[0] for b in parts]
        for b in parts:
            colors[(b[4], b[5])] += 1
        seen = set()
        for c in pg["Connections"]["items"]:
            signature = canonical(c)
            if signature in seen:
                continue  # Doppelte/dreifache Einträge sind kein unabhängiger Beleg.
            seen.add(signature)
            a, b = c["PartIndexA"], c["PartIndexB"]
            ra = field_role(design[a], c["FieldIndexA"])
            rb = field_role(design[b], c["FieldIndexB"])
            stats[design[a]][(c["FieldIndexA"], ra)] += 1
            stats[design[b]][(c["FieldIndexB"], rb)] += 1
    result = {}
    for d in sorted(stats):
        result[d] = {f"{f}:{r}": n for (f, r), n in sorted(stats[d].items())}
        print(d, result[d])
    print("Farben (Index, Oberflaeche):", sorted(colors.items()))
    print(f"{count} verschiedene Fahrzeuge, {len(result)} Teile mit Anschlussbeobachtungen")
    if out:
        json.dump(result, open(out, "w", encoding="utf-8"), indent=1)
    if md:
        write_md(md, result, chassis, assemblies, colors)
    return result


def fields(entry, role):
    """Felder einer Rolle, häufigster zuerst."""
    found = sorted(((n, int(k.split(":")[0])) for k, n in entry.items() if k.split(":", 1)[1] == role),
                   reverse=True)
    return ", ".join(str(f) for _, f in found) or "–"


def write_md(path, result, chassis, assemblies, colors):
    lines = ["# Anschlusspunkte je Teil (FieldIndex)", "",
             "Aus Fahrzeugen in Spielständen ermittelt (anschluesse.py: eigene, heruntergeladene und Creators-Hub-Cache). Haeufigster Wert zuerst.",
             "Identische Verbindungen werden je Fahrzeug nur einmal gezählt. Lokale Ober-/Unterseiten stammen aus GEOM, nicht aus einem Welt-z-Vergleich.", "",
             "- **Unterseite**: Feld, mit dem das Teil auf etwas sitzt",
             "- **Noppen oben**: Feld, das ein Teil darueber traegt",
             "- **seitlich/gedreht**: Seitennoppen oder Felder unbekannter Geometrie; eine bloße Drehung macht eine lokale Unterseite nicht zur Seitennoppe",
             "- Zum Ermitteln neuer Felder und Masken geometrie.py verwenden; diese Tabelle zählt Beobachtungen bekannter bzw. noch nicht zugeordneter Felder.", "",
             "| Teil | Unterseite | Noppen oben | seitlich/gedreht |", "|---|---|---|---|"]
    for d, e in result.items():
        lines.append(f"| {d} | {fields(e, 'oben')} | {fields(e, 'unten')} | {fields(e, 'seitlich/gedreht')} |")
    lines += ["", "# Chassis in den Vorlagen", "", "| ChassisConfig | Klasse | Anzahl |", "|---|---|---|"]
    lines += [f"| {c} | {k} | {n} |" for (c, k), n in chassis.most_common()]
    lines += ["", "# Baugruppen (Chassis-Teile, Flairs)", ""]
    lines += [f"- {a} ({n}×)" for a, n in assemblies.most_common() if not a.startswith("Wheel/")]
    lines += ["", "# Raeder", ""]
    lines += [f"- {a} ({n}×)" for a, n in assemblies.most_common() if a.startswith("Wheel/")]
    lines += ["", "# Vorkommende Farben (Index, Oberflaechen-Byte): Anzahl", "",
              ", ".join(f"{c}/{f}: {n}" for (c, f), n in sorted(colors.items()))]
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    args = sys.argv[1:]
    opts = {}
    for flag in ("--json", "--md"):
        if flag in args:
            i = args.index(flag)
            opts[flag] = args[i + 1]
            del args[i:i + 2]
    if "--alle" in args:
        args.remove("--alle")
        args += alle_spielstaende()
    main(expand(args), opts.get("--json"), opts.get("--md"))

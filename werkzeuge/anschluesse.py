"""Wertet Verbindungen aller Fahrzeuge in .sav-Dateien aus.

Ergebnis pro Teilenummer: welche Anschlusspunkte (FieldIndex) vorkommen und ob das
Teil dabei unten (seine Noppen tragen etwas) oder oben (es sitzt auf etwas) lag.
Aufruf: python anschluesse.py <datei.sav> [<datei2.sav> ...] [--json ausgabe.json] [--md ausgabe.md]
"""
import collections
import json
import struct
import sys

import gvas


def vehicles(path):
    data = gvas.load(path)["body"]["Data"]
    for key in ("CustomVehicles", "DownloadedVehicles"):
        for v in data.get(key, {}).get("items", []):
            if v["VehicleName"]:
                yield v


def z_axis(q):
    """Lokale Hochachse eines Teils nach Rotation (Quaternion x, y, z, w)."""
    x, y, z, w = q
    return (2 * (x * z + w * y), 2 * (y * z - w * x), 1 - 2 * (x * x + y * y))


def main(paths, out=None, md=None):
    stats = collections.defaultdict(lambda: collections.Counter())
    colors = collections.Counter()
    chassis = collections.Counter()
    assemblies = collections.Counter()
    for path in paths:
        for v in vehicles(path):
            pg = v["PartGraph"]
            chassis[(v["ChassisConfig"].split(".")[-1], v["VehicleClass"].split("::")[-1])] += 1
            for a in pg["Assemblies"]["items"]:
                assemblies[a["AssemblyAsset"].split("/Game/LEGO/")[-1].split(".")[0]] += 1
            parts = [bytes.fromhex(p) for p in pg["Parts"]["items"]]
            tfs = pg["PartTransforms"]["items"]
            design = [struct.unpack("<I", b[:4])[0] for b in parts]
            for b in parts:
                colors[(b[4], b[5])] += 1
            for c in pg["Connections"]["items"]:
                a, b = c["PartIndexA"], c["PartIndexB"]
                za, zb = tfs[a]["Translation"][2], tfs[b]["Translation"][2]
                upa = z_axis(tfs[a]["Rotation"])[2] > 0.9
                upb = z_axis(tfs[b]["Rotation"])[2] > 0.9
                if abs(za - zb) < 0.5 or not (upa and upb):
                    ra = rb = "seitlich/gedreht"
                elif zb > za:
                    ra, rb = "unten", "oben"
                else:
                    ra, rb = "oben", "unten"
                stats[design[a]][(c["FieldIndexA"], ra)] += 1
                stats[design[b]][(c["FieldIndexB"], rb)] += 1
    result = {}
    for d in sorted(stats):
        result[d] = {f"{f}:{r}": n for (f, r), n in sorted(stats[d].items())}
        print(d, result[d])
    print("Farben (Index, Oberflaeche):", sorted(colors.items()))
    if out:
        json.dump(result, open(out, "w", encoding="utf-8"), indent=1)
    if md:
        write_md(md, result, chassis, assemblies, colors)


def fields(entry, role):
    """Felder einer Rolle, häufigster zuerst."""
    found = sorted(((n, int(k.split(":")[0])) for k, n in entry.items() if k.split(":", 1)[1] == role),
                   reverse=True)
    return ", ".join(str(f) for _, f in found) or "–"


def write_md(path, result, chassis, assemblies, colors):
    lines = ["# Anschlusspunkte je Teil (FieldIndex)", "",
             "Aus Creators-Hub-Modellen ermittelt (anschluesse.py). Haeufigster Wert zuerst.", "",
             "- **Unterseite**: Feld, mit dem das Teil auf etwas sitzt",
             "- **Noppen oben**: Feld, das ein Teil darueber traegt",
             "- **seitlich/gedreht**: Verbindungen gedrehter Teile oder Seitennoppen (nicht eindeutig zuzuordnen)", "",
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
    main(args, opts.get("--json"), opts.get("--md"))

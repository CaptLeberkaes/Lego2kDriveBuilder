"""Listet alle eigenen Fahrzeuge eines ArtemisVehicle.sav lesbar auf.

Aufruf: python zeige_fahrzeug.py [Pfad zur .sav]
Ohne Pfad wird der Standard-Spielstand verwendet.
"""
import os
import struct
import sys

import gvas
import teiledaten

DEFAULT = os.path.expandvars(
    r"%USERPROFILE%\Documents\My Games\Artemis\Saved\SaveGames\ArtemisVehicle.sav")


def main(path):
    res = gvas.load(path)
    vehicles = res["body"]["Data"]["CustomVehicles"]["items"]
    for slot, v in enumerate(vehicles):
        if not v["VehicleName"]:
            continue
        pg = v["PartGraph"]
        parts = pg["Parts"]["items"]
        print(f"== Platz {slot}: {v['VehicleName']}  ({len(parts)} Teile, "
              f"{len(pg['Connections']['items'])} Verbindungen, Version {v['VersionId']})")
        print(f"   Chassis: {v['ChassisConfig'].split('.')[-1]}")
        for i, (p, t) in enumerate(zip(parts, pg["PartTransforms"]["items"])):
            b = bytes.fromhex(p)
            design = struct.unpack("<I", b[:4])[0]
            x, y, z = (round(c, 2) for c in t["Translation"])
            rot = [round(c, 3) for c in t["Rotation"]]
            print(f"   {i:3d}  Teil {design:6d}  Farbe {b[4]:3d}  Flag {b[5]}  "
                  f"Pos ({x}, {y}, {z})  Rot {rot}  {teiledaten.name(design)}")
        for a in pg["Assemblies"]["items"]:
            print(f"   Baugruppe {a['AssemblyName']:5s} Teile {a['PartOffset']}..."
                  f"{a['PartOffset'] + a['NumParts'] - 1}  {a['AssemblyAsset'].split('.')[-1]}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT)

"""Read-only save inspection; writes sanitized review data only beside this script.

Run from any directory after updating basis-zuordnung.json. No game save is written.
"""
import collections
import datetime
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import tempfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "werkzeuge"))
import gvas
from baue_fahrzeug import GEOM


def write_json(path, data):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix="."+path.name, suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main():
    mapping = json.loads((HERE / "basis-zuordnung.json").read_text(encoding="utf-8"))
    save = Path(os.path.expandvars(
        r"%USERPROFILE%\Documents\My Games\Artemis\Saved\SaveGames\ArtemisVehicle.sav"))
    before = save.stat()
    raw = save.read_bytes()
    after = save.stat()
    if (before.st_mtime_ns, before.st_size) != (after.st_mtime_ns, after.st_size):
        raise RuntimeError("Save changed during snapshot; retry after game has finished saving")
    reader = gvas.R(raw)
    gvas.read_header(reader)
    data = gvas.read_props(reader)["Data"]
    sha = hashlib.sha256(raw).hexdigest()
    catalog_path = HERE / "chassis-beobachtet.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    encyclopedia_path = HERE / "quellen" / "l2kd-encyclopedia" / "chassis_by_id.json"
    encyclopedia = json.loads(encyclopedia_path.read_text(encoding="utf-8")) if encyclopedia_path.exists() else {}
    base = {
        "date": "2026-10-29", "save_file": save.name, "source_sha256": sha,
        "source_mtime_utc": datetime.datetime.fromtimestamp(
            after.st_mtime, datetime.timezone.utc).isoformat(),
        "scope": "User-identified unmodified base chassis; menu completeness unverified. No player IDs exported.",
        "chassis": [],
    }
    ancillary = data.get("AncillaryCustomVehicle")
    if ancillary:
        base["working_copy"] = {
            "slot": data.get("AncillaryCustomSlot"),
            "name": ancillary.get("VehicleName"),
            "chassis_config": ancillary.get("ChassisConfig"),
            "parts": len(ancillary.get("PartGraph", {}).get("Parts", {}).get("items", [])),
        }
    for number, label in sorted(mapping.items(), key=lambda item: int(item[0])):
        slot = int(number)
        vehicle = data["CustomVehicles"]["items"][slot]
        state = "saved"
        if not vehicle["VehicleName"] and data.get("AncillaryCustomSlot") == slot and ancillary:
            vehicle, state = ancillary, "working_copy"
        name = vehicle.get("VehicleName", "")
        if not name:
            print(f"MISSING {slot:02d}: {label}")
            continue
        if name not in (f"Neues Fahrzeug {slot:02d}", f"Basis - {label}", label):
            raise ValueError(f"Slot {slot}: unexpected vehicle name {name!r}; mapping must be reviewed")
        graph = vehicle["PartGraph"]
        parts = [bytes.fromhex(part) for part in graph["Parts"]["items"]]
        designs = [struct.unpack("<I", part[:4])[0] for part in parts]
        assemblies = graph["Assemblies"]["items"]
        chassis = [a for a in assemblies if "/Chassis/" in a["AssemblyAsset"]]
        indices = [i for a in chassis for i in range(a["PartOffset"], a["PartOffset"] + a["NumParts"])]
        config = vehicle["ChassisConfig"]
        external_id = config.split(".")[-1].removeprefix("ChassisConfig_")
        external = encyclopedia.get(external_id)
        record = {
            "menu_name": label, "mapping_evidence": "Explicit numbered mapping supplied by user.",
            "slot": slot, "state": state, "source_sha256": sha, "saved_name": name,
            "working_copy_present_for_slot": ancillary is not None and data.get("AncillaryCustomSlot") == slot,
            "chassis_config": config, "vehicle_class": vehicle.get("VehicleClass"),
            "parts": [{"index": i, "design": designs[i], "color": part[4], "flags": part[5],
                       "transform": graph["PartTransforms"]["items"][i]} for i, part in enumerate(parts)],
            "assemblies": assemblies, "connections": graph["Connections"]["items"],
            "sockets": vehicle.get("Sockets", {}).get("items", []),
            "flair_triggers": vehicle.get("FlairTriggers", []),
        }
        if external:
            record["encyclopedia"] = {
                "source": "https://github.com/r0levrai/l2kd-encyclopedia/blob/main/data/chassis_by_id.json",
                "id": external_id, "english_name": external.get("name"),
                "terrain": external.get("terrain"), "default_engine": external.get("default_engine"),
                "stats": external.get("stats"),
                "status": "external_metadata; geometry comes from local save",
            }
        base["chassis"].append(record)
        entry = next((e for e in catalog["configurations"] if e["chassis_config"] == config), None)
        if entry is None:
            entry = {"chassis_config": config, "vehicle_class": vehicle.get("VehicleClass"), "observations": []}
            catalog["configurations"].append(entry)
        entry.update(menu_name=label, menu_name_status=f"confirmed_by_user_{state}_baseline")
        if external:
            entry["encyclopedia"] = record["encyclopedia"]
        observation = {
            "save_file": save.name, "slot": slot, "state": state, "source_sha256": sha,
            "model_name": name, "chassis_assemblies": [a["AssemblyAsset"] for a in chassis],
            "chassis_part_count": len(indices),
            "chassis_design_counts": dict(collections.Counter(designs[i] for i in indices)),
            "chassis_parts_with_GEOM": sum(designs[i] in GEOM for i in indices),
            "chassis_designs_without_GEOM": sorted({designs[i] for i in indices if designs[i] not in GEOM}),
            "wheels": [{"name": a["AssemblyName"], "asset": a["AssemblyAsset"], "part_count": a["NumParts"]}
                       for a in assemblies if "Wheel" in a["AssemblyType"]],
        }
        entry["observations"] = [o for o in entry["observations"]
                                 if not (o["slot"] == slot and o["save_file"] == save.name)] + [observation]
        print(f"{slot:02d} | {label} | {state} | {config.split('.')[-1]} | {len(parts)} parts ({len(indices)} chassis)")
    catalog["baseline_source_sha256"] = sha
    write_json(HERE / "basis-chassis.json", base)
    write_json(catalog_path, catalog)
    print(f"Baselines: {len(base['chassis'])}; observed configurations: {len(catalog['configurations'])}")


if __name__ == "__main__":
    main()

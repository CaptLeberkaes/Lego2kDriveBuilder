"""Katalog der Sonderteile (Räder, Baugruppen, Flairs, Propeller, Chassis) automatisch erzeugen.

Zusätzlich "fahrzeuge": Fertigfahrzeuge des Spiels mit der Angabe, ob ihr Chassis schon in einem
Spielstand vorkommt. Eine Garagenkopie eines Fahrzeugs ohne beobachtetes Chassis bringt neue Daten.

Quellen, alle nur gelesen:
- .claude/quellen/l2kd-encyclopedia/*_by_id.json: Namen, Gelände, Werte, Seltenheit (externer Export)
- .claude/freischaltung/assetnamen-live.json und assetnamen-belegt.json: im installierten Spiel
  gefundene Paketnamen (fehlen sie, bleibt "im_spiel" leer)
- Spielstände: in welchen Fahrzeugen das Teil wirklich vorkommt (anschluesse.vehicles_with_source)
- ../teiledaten.json: Namen der LEGO-Teilenummern

Jeder Eintrag trennt "belegt" (so in einer Quelle gelesen) von "annahmen" (abgeleitet, ungeprüft).
"builder.nutzbar" heißt: ein Fahrzeug mit diesem Teil liegt in CustomVehicles/DownloadedVehicles,
baue_fahrzeug.py kann es also als vorlage_name, radtausch-Spender oder über behalten übernehmen.

Aufruf: python sonderteile.py [--mit-sicherungen] [--kopierliste 24 [--ohne-boote]] [--ohne-spielstaende] [--ausgabe datei.json] [<datei.sav> ...]
Ohne .sav-Angabe werden alle Fahrzeug-Spielstände im Spielordner gelesen (siehe anschluesse.py).
"""
import argparse
import collections
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import struct

ROOT = Path(__file__).resolve().parents[1]
ENZ = ROOT / ".claude" / "quellen" / "l2kd-encyclopedia"
FREI = ROOT / ".claude" / "freischaltung"
AUSGABE = ROOT / "sonderteile.json"
KOPIERLISTE = ROOT / ".claude" / "kopierliste.md"
TEILELISTEN = ENZ / "fahrzeugteile" / "vehicle_parts.json"  # Teile je Fertigfahrzeug
NICHT_GEFUNDEN = ROOT / ".claude" / "kopierliste-nicht-gefunden.json"  # in der Garage nicht auffindbar
MAX_FAHRZEUGE = 8  # Beobachtungen je Teil; die Gesamtzahl steht in "anzahl".

# Kategorie -> (Enzyklopädie-Datei, Spielverzeichnisse, Präfixe des Paketnamens, Ordner im Spielstand)
KATEGORIEN = {
    "raeder": ("wheels", ["/Game/LEGO/Wheel/"], [""], "Wheel"),
    "baugruppen": ("assemblies", ["/Game/LEGO/Assemblies/"], [""], "Assemblies"),
    "flairs": ("flairs", ["/Game/LEGO/Flair/"], ["Flair_", ""], "Flair"),
    "propeller": ("propellers", ["/Game/LEGO/Propeller/"], [""], "Propeller"),
    "chassis": ("chassis", ["/Game/Game/Vehicle/Inventory/CarChassisConfigs/",
                            "/Game/Game/Vehicle/Inventory/BoatChassisConfigs/"], ["ChassisConfig_"], None),
}
BUILDER_LISTEN = {"CustomVehicles", "DownloadedVehicles"}


def lese_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def kurzhash(path):
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]
    except FileNotFoundError:
        return None


def bereinige_name(name, ident):
    """Website-Zusatz "(new!)" entfernen; ein Name gleich der ID ist kein Anzeigename."""
    name = (name or "").removesuffix(" (new!)").strip()
    return None if not name or name == ident else name


def freischaltquellen(sources):
    """Nur Art und Name der Quelle, nicht die oft riesigen Belohnungslisten."""
    return [list(x) for x in sorted({(s.get("type"), s.get("name"), s.get("biome")) for s in sources or []}, key=str)]


def paketindex(live, verzeichnisse):
    """kleingeschriebener Paketname -> (Originalname, Verzeichnis); Unterordner sind Vorschaubilder."""
    index = collections.defaultdict(set)
    for verzeichnis in verzeichnisse:
        for name in live.get(verzeichnis, []):
            if "/" not in name:
                index[name.lower()].add((name, verzeichnis))
    return index


def paket_fuer(ident, index, praefixe):
    treffer = {t for p in praefixe for t in index.get((p + ident).lower(), ())}
    return next(iter(treffer)) if len(treffer) == 1 else None


def lego_nummern(ident, teile):
    """Ziffernblöcke im Asset-Namen, die bekannte Teilenummern sind (z. B. Felge_Reifen)."""
    found = []
    for token in re.findall(r"\d{3,6}", ident):
        nummer = int(token)
        if nummer in teile and nummer not in [x["nummer"] for x in found]:
            found.append({"nummer": nummer, "name": teile[nummer]})
    return found


def motor(config):
    name = (config or "").split(".")[-1]
    return None if name in ("", "None") else name


def beobachtungen(pfade, vehicles_with_source, teile_gesehen=None):
    """Je Asset (Ordner/Name) und je ChassisConfig: Fahrzeuge, in denen es vorkommt.

    teile_gesehen: optionale Menge, in die alle vorkommenden Teilenummern eingetragen werden.
    """
    assets = collections.defaultdict(list)
    chassis = collections.defaultdict(list)
    gesehen = set()
    for pfad in pfade:
        for liste, v in vehicles_with_source(pfad):
            graph = v["PartGraph"]
            schluessel = hashlib.sha1(json.dumps(graph, sort_keys=True, default=str).encode()).hexdigest()
            if schluessel in gesehen:
                continue
            gesehen.add(schluessel)
            fahrzeug = {"datei": anzeige_pfad(pfad), "liste": liste, "fahrzeug": v["VehicleName"]}
            designs = [struct.unpack("<I", bytes.fromhex(p)[:4])[0] for p in graph["Parts"]["items"]]
            if teile_gesehen is not None:
                teile_gesehen.update(designs)
            chassis_assets = []
            for a in graph["Assemblies"]["items"]:
                asset = a["AssemblyAsset"].split(".")[0]
                if not asset.startswith("/Game/LEGO/"):
                    continue
                ordner, name = asset[len("/Game/LEGO/"):].split("/", 1)
                if ordner == "Chassis":
                    chassis_assets.append(name)
                teile = designs[a["PartOffset"]:a["PartOffset"] + a["NumParts"]]
                assets[(ordner, name)].append(dict(fahrzeug, baugruppenname=a["AssemblyName"],
                                                           teile=sorted(set(teile))))
            config = v["ChassisConfig"].split(".")[-1]
            chassis[config].append(dict(fahrzeug, fahrzeugklasse=v["VehicleClass"].split("::")[-1],
                                                motor=motor(v.get("EngineConfig")),
                                                chassis_baugruppen=chassis_assets))
    return assets, chassis


def builder_info(beobachtet):
    nutzbar = [b for b in beobachtet if b["liste"] in BUILDER_LISTEN]
    if nutzbar:
        hinweis = "Als Vorlage/Spender nutzbar: " + ", ".join(sorted({f"{b['fahrzeug']} ({b['datei']})" for b in nutzbar})[:3])
    elif beobachtet:
        hinweis = ("Nur im Creators-Hub-Cache gesehen; das Fahrzeug im Spiel herunterladen, "
                   "dann liegt es in ArtemisDownloadedVehicle.sav und ist nutzbar")
    else:
        hinweis = "Kein Fahrzeug mit diesem Teil in den Spielständen; Fahrzeug damit in der Garage bauen oder kopieren"
    return {"nutzbar": bool(nutzbar), "hinweis": hinweis}


def gekuerzt(beobachtet):
    """Je Fahrzeug ein Eintrag; Radpositionen (fl, fr, ...) werden zusammengefasst."""
    fahrzeuge = {}
    for b in beobachtet:
        schluessel = (b["datei"], b["liste"], b["fahrzeug"])
        ziel = fahrzeuge.setdefault(schluessel, {k: v for k, v in b.items() if k not in ("baugruppenname", "teile")})
        if "baugruppenname" in b:
            ziel.setdefault("baugruppennamen", [])
            if b["baugruppenname"] not in ziel["baugruppennamen"]:
                ziel["baugruppennamen"].append(b["baugruppenname"])
            ziel["teile"] = sorted(set(ziel.get("teile", [])) | set(b["teile"]))
    liste = list(fahrzeuge.values())
    return {"anzahl": len(liste), "fahrzeuge": liste[:MAX_FAHRZEUGE]}


def eintrag(kategorie, ident, enz, paket, beobachtet, teile):
    belegt, annahmen = {}, {}
    if enz is not None:
        quelle = {"name": enz.get("name")}
        for key in ("terrain", "stats", "default_engine", "rarity", "garage_cost", "is_surplus"):
            if enz.get(key) is not None:
                quelle[key] = enz[key]
        if enz.get("sources"):
            quelle["freischaltung"] = freischaltquellen(enz["sources"])
        belegt["enzyklopaedie"] = quelle
    if paket:
        belegt["im_spiel"] = paket[1] + paket[0]
    if beobachtet:
        belegt["in_fahrzeugen"] = gekuerzt(beobachtet)
    name = bereinige_name(enz and enz.get("name"), ident)
    if name:
        annahmen["anzeigename"] = name
    if enz is not None and "(new!)" in (enz.get("name") or ""):
        annahmen["spaeter_ergaenzt"] = True  # Website-Markierung, nicht die Spielversion.
    if kategorie in ("raeder", "propeller", "baugruppen"):
        nummern = lego_nummern(ident, teile)
        if nummern:
            annahmen["lego_teile_aus_namen"] = nummern
    if kategorie == "chassis":
        if paket:
            annahmen["fahrzeugklasse"] = "BOAT" if "BoatChassis" in paket[1] else "CAR"
        if ident.endswith("_Garage"):
            annahmen["garagen_startchassis"] = True
    eintrag = {"belegt": belegt, "annahmen": annahmen, "builder": builder_info(beobachtet)}
    if not enz and not paket:
        eintrag["nur_in_spielstaenden"] = True
    return eintrag


def erzeuge_katalog(enzyklopaedie, live, beobachtete_assets, beobachtete_chassis, teile):
    """Reine Funktion: alle Eingaben als Daten, Ausgabe ist der Katalog."""
    katalog = {}
    zusammenfassung = {}
    for kategorie, (datei, verzeichnisse, praefixe, ordner) in KATEGORIEN.items():
        enz = enzyklopaedie.get(datei, {})
        index = paketindex(live, verzeichnisse)
        eintraege = {}
        vergeben, zugeordnet = set(), set()
        # Beobachtungen: kleingeschriebener voller Name -> (Originalname, Fahrzeuge)
        beob = ({name.lower(): (name, v) for (o, name), v in beobachtete_assets.items() if o == ordner}
                if ordner else {name.lower(): (name, v) for name, v in beobachtete_chassis.items()})

        def gesehen_fuer(ident):
            for p in praefixe:
                treffer = beob.get((p + ident).lower())
                if treffer:
                    zugeordnet.add((p + ident).lower())
                    return treffer[1]
            return []

        def ohne_praefix(name):
            for p in praefixe:
                if p and name.lower().startswith(p.lower()):
                    return name[len(p):]
            return name

        for ident, daten in enz.items():
            paket = paket_fuer(ident.split("/")[-1], index, praefixe)
            if paket:
                vergeben.add(paket[0].lower())
            gesehen = gesehen_fuer(ident) or (gesehen_fuer(ohne_praefix(paket[0])) if paket else [])
            eintraege[ident] = eintrag(kategorie, ident, daten, paket, gesehen, teile)
        # Im Spiel vorhanden, aber nicht in der Enzyklopädie: trotzdem aufnehmen.
        for schluessel, treffer in sorted(index.items()):
            if schluessel in vergeben or len(treffer) != 1:
                continue
            name, verzeichnis = next(iter(treffer))
            ident = ohne_praefix(name)
            if ident in eintraege:
                continue
            eintraege[ident] = eintrag(kategorie, ident, None, (name, verzeichnis), gesehen_fuer(ident), teile)
            eintraege[ident]["nur_im_spiel"] = True
        # In Fahrzeugen gesehen, aber weder in der Enzyklopädie noch als Spielpaket bekannt.
        for schluessel, (name, gesehen) in sorted(beob.items()):
            if schluessel not in zugeordnet:
                eintraege.setdefault(ohne_praefix(name), eintrag(kategorie, ohne_praefix(name), None, None, gesehen, teile))
        katalog[kategorie] = dict(sorted(eintraege.items(), key=lambda kv: kv[0].lower()))
        werte = katalog[kategorie].values()
        zusammenfassung[kategorie] = {
            "gesamt": len(katalog[kategorie]),
            "mit_enzyklopaedie": sum("enzyklopaedie" in e["belegt"] for e in werte),
            "im_spiel_belegt": sum("im_spiel" in e["belegt"] for e in werte),
            "in_fahrzeugen_beobachtet": sum("in_fahrzeugen" in e["belegt"] for e in werte),
            "builder_nutzbar": sum(e["builder"]["nutzbar"] for e in werte),
        }
    return {"zusammenfassung": zusammenfassung, **katalog}


def fahrzeugliste(fahrzeuge, chassis_katalog):
    """Fertigfahrzeuge des Spiels; zeigt, welche Kopie ein noch unbeobachtetes Chassis bringt."""
    ergebnis = {}
    for ident, v in fahrzeuge.items():
        chassis = chassis_katalog.get(v.get("chassis"), {})
        belegt = {"enzyklopaedie": {k: v[k] for k in ("name", "chassis", "terrain", "engine", "rarity", "garage_valid",
                                                      "license", "weight_estimation")
                                    if v.get(k) is not None}}
        if v.get("sources"):
            belegt["enzyklopaedie"]["freischaltung"] = freischaltquellen(v["sources"])
        annahmen = {}
        name = bereinige_name(v.get("name"), ident)
        if name:
            annahmen["anzeigename"] = name
        ergebnis[ident] = {"belegt": belegt, "annahmen": annahmen,
                           "chassis_in_spielstaenden": "in_fahrzeugen" in chassis.get("belegt", {}),
                           "chassis_als_vorlage_nutzbar": chassis.get("builder", {}).get("nutzbar", False)}
    return dict(sorted(ergebnis.items(), key=lambda kv: kv[0].lower()))


def familie(ident):
    """Grobe Modellfamilie, damit eine Runde nicht dreimal dasselbe Modell als Auto, Boot und Geländewagen enthält."""
    name = re.sub(r"_Garage$|_(VC|LU)?\d.*$", "", ident)
    name = re.sub(r"^Rival", "", name)
    return re.sub(r"(Boat|Offroader|Offroad|StreetCar|Street|Car|Truck|Convertible)$", "", name).lower()


def kopierkandidaten(fahrzeuge, boote=True):
    return [(i, e) for i, e in fahrzeuge.items()
            if not e["chassis_in_spielstaenden"] and e["annahmen"].get("anzeigename")
            and (boote or e["belegt"]["enzyklopaedie"].get("terrain") != "Boat")
            and e["belegt"]["enzyklopaedie"].get("garage_valid") == "Valid"]


def kopierliste(fahrzeuge, anzahl=24, boote=True):
    """Garagenkopien mit dem größten Datengewinn: Chassis noch nie gesehen, gültig, mit Namen.

    Je Gelände ein Anteil (ein Viertel Boote, Rest halb Straße, halb Gelände), innerhalb davon
    zuerst die schwersten (Gewichtsschätzung ~ Teilezahl), höchstens ein Fahrzeug je Modellfamilie.
    """
    boote = round(anzahl / 4) if boote else 0
    quoten = {"Boat": boote, "Street": (anzahl - boote + 1) // 2, "Offroad": (anzahl - boote) // 2}
    kandidaten = sorted(kopierkandidaten(fahrzeuge),
                        key=lambda ie: (-ie[1]["belegt"]["enzyklopaedie"].get("weight_estimation", 0), ie[0]))
    gewaehlt, familien = [], set()
    for gelaende, quote in quoten.items():
        for ident, e in kandidaten:
            enz = e["belegt"]["enzyklopaedie"]
            if quote == 0:
                break
            if enz.get("terrain") != gelaende or familie(ident) in familien:
                continue
            familien.add(familie(ident))
            quote -= 1
            gewaehlt.append({"id": ident, "name": e["annahmen"]["anzeigename"], "gelaende": gelaende,
                             "gewicht": round(enz.get("weight_estimation", 0)), "chassis": enz.get("chassis"),
                             "lizenz": enz.get("license"), "seltenheit": enz.get("rarity")})
    return gewaehlt


def kopierliste_md(liste, rest):
    zeilen = ["# Kopierliste für Garagenkopien", "",
              "Erzeugt von `werkzeuge/sonderteile.py --kopierliste`. Jedes Fahrzeug hat ein Chassis, das noch in keinem",
              "Spielstand vorkommt. Namen sind die englischen Spielnamen (Spielsprache für die Runde auf Englisch stellen).",
              f"Danach noch {rest} weitere Kandidaten.", "",
              "Ablauf je Fahrzeug: in der Garage öffnen, eine Kleinigkeit ändern, speichern.",
              "Nach der Runde: Spiel schließen, `python werkzeuge\\sichern.py`, dann die Auswertung laut",
              "`.claude/sonderteile-und-abdeckung-2026-10-29.md`, Abschnitt 5.", "",
              "| ✓ | Nr | Name (englisch) | Gelände | Gewicht (Schätzung) | Fahrzeug-ID |", "|---|---|---|---|---|---|"]
    gelaende = {"Street": "Straße", "Offroad": "Gelände", "Boat": "Boot"}
    zeilen += [f"| ☐ | {n} | {x['name']} | {gelaende[x['gelaende']]} | {x['gewicht']} | `{x['id']}` |"
               for n, x in enumerate(liste, 1)]
    return "\n".join(zeilen) + "\n"


GARAGEN_REITER = ["Collection", "Friends", "Creator", "City", "Speed Champions", "Ideas", "Icons"]
LIZENZ_REITER = {"Friends": "Friends", "Creator": "Creator", "City": "City", "LEGOSpeedChampions": "Speed Champions",
                 "Ideas": "Ideas", "Icons": "Icons"}


def garagen_reiter(enz):
    """Garagen-Reiter laut Lizenz der Enzyklopädie; ohne Lizenz vermutlich "Collection" (Annahme)."""
    return LIZENZ_REITER.get(enz.get("license"), "Collection")


def abdeckungsliste(fahrzeuge, teilelisten, beobachtet, anzahl=24, boote=True):
    """Gierige Mengenüberdeckung: jeweils das Fahrzeug mit den meisten noch nie gesehenen Teilen.

    teilelisten: Fahrzeug-ID -> Menge der Teilenummern (Enzyklopädie, vehicle_parts.json).
    Ein Teil zählt so oft, wie es in Kandidaten vorkommt: verbreitete Teile sind für den Builder wichtiger.
    """
    kandidaten = {i: teilelisten[i] for i, e in fahrzeuge.items()
                  if i in teilelisten and e["annahmen"].get("anzeigename")
                  and e["belegt"]["enzyklopaedie"].get("garage_valid") == "Valid"
                  and (boote or e["belegt"]["enzyklopaedie"].get("terrain") != "Boat")}
    gewicht = collections.Counter(p for teile in kandidaten.values() for p in teile)
    offen = set(gewicht) - set(beobachtet)
    rest, liste = set(offen), []
    while rest and len(liste) < anzahl:
        ident = max(sorted(kandidaten), key=lambda i: (sum(gewicht[p] for p in kandidaten[i] & rest),
                                                       len(kandidaten[i] & rest)))
        neu = kandidaten[ident] & rest
        if not neu:
            break
        rest -= neu
        enz = fahrzeuge[ident]["belegt"]["enzyklopaedie"]
        liste.append({"id": ident, "name": fahrzeuge[ident]["annahmen"]["anzeigename"], "gelaende": enz.get("terrain"),
                      "kategorie": garagen_reiter(enz), "neue_teile": len(neu), "teile": len(kandidaten[ident])})
    gesamt = sum(gewicht[p] for p in offen)
    stats = {"kandidaten": len(kandidaten), "teile_gesamt": len(gewicht), "offen": len(offen),
             "danach_offen": len(rest),
             "verwendungen_abgedeckt_prozent": round(100 * (gesamt - sum(gewicht[p] for p in rest)) / gesamt) if gesamt else 100}
    return liste, stats


def abdeckungsliste_md(liste, stats):
    zeilen = ["# Kopierliste für Garagenkopien", "",
              "Erzeugt von `werkzeuge/sonderteile.py --kopierliste`. Reihenfolge nach Datengewinn: jedes Fahrzeug bringt die",
              "meisten Teile, die in noch keinem Spielstand-Fahrzeug vorkommen (Teilelisten: L2KD-Enzyklopädie).",
              "Namen sind die englischen Spielnamen (Spielsprache für die Runde auf Englisch stellen).", "",
              f"- Kandidaten: {stats['kandidaten']} Fahrzeuge mit zusammen {stats['teile_gesamt']} verschiedenen Teilen",
              f"- noch nie gesehen: {stats['offen']} Teile; nach dieser Liste noch {stats['danach_offen']}",
              f"- abgedeckt nach Verbreitung gewichtet: {stats['verwendungen_abgedeckt_prozent']} % der offenen Teileverwendungen",
              "", "Ablauf je Fahrzeug: in der Garage öffnen, eine Kleinigkeit ändern, speichern.",
              "Nach der Runde: Spiel schließen und Claude Bescheid geben (oder Auswertung laut",
              "`.claude/sonderteile-und-abdeckung-2026-10-29.md`, Abschnitt 5). Die Liste rückt danach von selbst weiter.", "",
              "Nach Garagen-Reiter sortiert (aus der Lizenz laut Enzyklopädie; ohne Lizenz vermutlich Collection).", "",
              "| ✓ | Nr | Reiter | Name (englisch) | Gelände | neue Teile | Fahrzeug-ID |", "|---|---|---|---|---|---|---|"]
    gelaende = {"Street": "Straße", "Offroad": "Gelände", "Boat": "Boot"}
    reihenfolge = {r: i for i, r in enumerate(GARAGEN_REITER)}
    sortiert = sorted(liste, key=lambda x: (reihenfolge.get(x.get("kategorie"), 99), x["name"].lower()))
    zeilen += [f"| ☐ | {n} | {x.get('kategorie', '')} | {x['name']} | {gelaende.get(x['gelaende'], x['gelaende'])} | "
               f"{x['neue_teile']} | `{x['id']}` |" for n, x in enumerate(sortiert, 1)]
    return "\n".join(zeilen) + "\n"


def anzeige_pfad(pfad):
    """Sicherungen im Projekt mit relativem Pfad, Spielordner-Dateien nur mit Namen."""
    try:
        return Path(pfad).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return os.path.basename(pfad)


def main(argv=None):
    import anschluesse
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("spielstaende", nargs="*")
    parser.add_argument("--ohne-spielstaende", action="store_true")
    parser.add_argument("--ausgabe", default=str(AUSGABE))
    parser.add_argument("--mit-sicherungen", action="store_true",
                        help="auch Fahrzeuge aus _sicherungen lesen (gelöschte Garagenkopien zählen weiter)")
    parser.add_argument("--kopierliste", type=int, metavar="N",
                        help=f"N Garagenkopien mit größtem Datengewinn nach {KOPIERLISTE.relative_to(ROOT)} schreiben")
    parser.add_argument("--ohne-boote", action="store_true", help="Kopierliste nur mit Autos (Straße, Gelände)")
    args = parser.parse_args(argv)
    pfade = [] if args.ohne_spielstaende else (anschluesse.expand(args.spielstaende) or anschluesse.alle_spielstaende())
    if args.mit_sicherungen and not args.ohne_spielstaende:
        pfade += anschluesse.expand([str(ROOT / "_sicherungen" / "*" / n) for n in anschluesse.FAHRZEUG_DATEIEN])
    enzyklopaedie = {datei: lese_json(ENZ / f"{datei}_by_id.json", {}) for datei, *_ in KATEGORIEN.values()}
    live = (lese_json(FREI / "assetnamen-live.json") or {}).get("pakete", {})
    teile = {int(k): v["name"] for k, v in lese_json(ROOT / "teiledaten.json", {}).items() if v.get("name")}
    gesehene_teile = set()
    assets, chassis = beobachtungen(pfade, anschluesse.vehicles_with_source, gesehene_teile)
    katalog = erzeuge_katalog(enzyklopaedie, live, assets, chassis, teile)
    katalog["fahrzeuge"] = fahrzeugliste(lese_json(ENZ / "vehicles_by_id.json", {}), katalog["chassis"])
    werte = katalog["fahrzeuge"].values()
    katalog["zusammenfassung"]["fahrzeuge"] = {
        "gesamt": len(katalog["fahrzeuge"]),
        "garage_gueltig": sum(e["belegt"]["enzyklopaedie"].get("garage_valid") == "Valid" for e in werte),
        "chassis_in_spielstaenden": sum(e["chassis_in_spielstaenden"] for e in werte),
        "chassis_als_vorlage_nutzbar": sum(e["chassis_als_vorlage_nutzbar"] for e in werte)}
    quellen = {str(p.relative_to(ROOT)): kurzhash(p) for p in
               [ENZ / f"{d}_by_id.json" for d, *_ in KATEGORIEN.values()]
               + [ENZ / "vehicles_by_id.json", FREI / "assetnamen-live.json"]}
    quellen.update({anzeige_pfad(p): kurzhash(p) for p in pfade})
    ergebnis = {"erzeugt": datetime.date.today().isoformat(), "skript": "werkzeuge/sonderteile.py",
                "quellen_sha256_16": quellen,
                "bedeutung": {
                    "belegt.enzyklopaedie": "Werte aus dem Export der L2KD Encyclopedia (Spieldaten eines Dritten)",
                    "belegt.im_spiel": "Paket mit genau diesem Namen im installierten Spiel gefunden",
                    "belegt.in_fahrzeugen": "In echten Fahrzeugen der Spielstände gesehen, mit Bauteilnummern",
                    "annahmen": "Aus Namen abgeleitet oder vermutet, nicht im Spiel geprüft",
                    "builder.nutzbar": "Fahrzeug mit dem Teil liegt in CustomVehicles/DownloadedVehicles"},
                **katalog}
    Path(args.ausgabe).write_text(json.dumps(ergebnis, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Geschrieben: {args.ausgabe} ({len(pfade)} Spielstände gelesen)")
    for kategorie, z in katalog["zusammenfassung"].items():
        print(f"{kategorie:11s} " + ", ".join(f"{k} {v}" for k, v in z.items()))
    if args.kopierliste:
        fehlt = set(lese_json(NICHT_GEFUNDEN, {}).get("fahrzeuge", {}))
        teilelisten = {x["id"]: {p for p, _ in x["parts_and_colors"]} for x in lese_json(TEILELISTEN, [])
                       if x["id"] not in fehlt}
        if teilelisten:
            liste, stats = abdeckungsliste(katalog["fahrzeuge"], teilelisten, gesehene_teile,
                                           args.kopierliste, not args.ohne_boote)
            KOPIERLISTE.write_text(abdeckungsliste_md(liste, stats), encoding="utf-8")
            print(f"Abdeckung: {stats}")
        else:  # Ohne Teilelisten: Schätzung über neue Chassis und Gewicht.
            liste = kopierliste(katalog["fahrzeuge"], args.kopierliste, not args.ohne_boote)
            rest = len(kopierkandidaten(katalog["fahrzeuge"], not args.ohne_boote)) - len(liste)
            KOPIERLISTE.write_text(kopierliste_md(liste, rest), encoding="utf-8")
        print(f"Kopierliste: {KOPIERLISTE} ({len(liste)} Fahrzeuge)")
    return ergebnis


if __name__ == "__main__":
    main()

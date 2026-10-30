"""GEOM-Kandidaten für rechteckige Teile aus echten Fahrzeugen ableiten und gegenprüfen.

Annahme je Kandidat: Größe aus teiledaten.json (l, w in Noppen, h = Plattenhöhen × 10), Noppenraster
wie bei den vorhandenen GEOM-Teilen (Ursprung an einer Ecknoppe, Länge entlang lokal +x, Breite nach -y).
Belegt wird aus Verbindungen zu Teilen mit bekannter GEOM in voller 3D-Lage:
- welche FieldIndex die Unterseite bzw. Oberseite hat,
- dass die vorhergesagte Noppenzahl der gespeicherten Stärke entspricht.
Angenommen wird eine Seite nur bei mindestens MIN_BELEGE Kontakten ohne Widerspruch. Danach sagt ein
Gegentest mit der erweiterten GEOM alle Flächenverbindungen der neuen Teile vorher und vergleicht sie
mit den gespeicherten Verbindungen.

Alias-Teile (teiledaten.json "aliase" eines GEOM-Teils) brauchen nur einen Beleg, der zum Original passt.

Aufruf: python geom_kandidaten.py [sav ...] [--teile 3027 3030 ...] [--vorhandene] [--json bericht.json]
Ohne --teile: alle einfachen Platten, Steine und Fliesen (Name "PLATE 2X4" usw.) ohne GEOM.
Ohne sav: alle Fahrzeug-Spielstände im Spielordner (nur lesen).
"""
import argparse
import collections
import json
from pathlib import Path
import re
import struct

import anschluesse
import baugeometrie
from baugeometrie import GEOM, faces, contact_count, TOLERANZ, quaternion, rotate, multiply, conjugate
from geometrie import canonical

ROOT = Path(__file__).resolve().parents[1]
MIN_BELEGE = 2
EINFACH = re.compile(r"^(PLATE|BRICK|TILE|FLAT TILE) \d+X\d+$")
PLATZHALTER = -1  # Feld noch unbekannt; faces() braucht nur "nicht None".


def einfache_teile(teile):
    return sorted(d for d, v in teile.items() if d not in GEOM and EINFACH.match(v.get("name") or ""))


def hypothese(groesse):
    l, w, h = groesse
    return dict(l=l, w=w, h=h * 10, unten=PLATZHALTER, oben=PLATZHALTER)


def teile_des_fahrzeugs(vehicle):
    graph = vehicle["PartGraph"]
    designs = [struct.unpack("<I", bytes.fromhex(p)[:4])[0] for p in graph["Parts"]["items"]]
    return [dict(design=d, pos=tf["Translation"], rot=tf["Rotation"], scale=tf["Scale3D"])
            for d, tf in zip(designs, graph["PartTransforms"]["items"])]


def im_raster(rot_a, rot_b):
    """Liegen zwei Teile zueinander in einer 90-Grad-Lage? Schon 2 Grad Schräglage verschieben ferne
    Noppen über die Toleranz; das Spiel zählt sie trotzdem. Solche Kontakte belegen nur das Feld."""
    rel = multiply(conjugate(quaternion(rot_a)), quaternion(rot_b))
    return all(max(abs(x) for x in rotate(rel, achse)) > 0.9999 for achse in ((1, 0, 0), (0, 1, 0), (0, 0, 1)))


def flaechenkontakt(oben, unten):
    """Noppenzahl, wenn Oberseite von A auf Unterseite von B in derselben Ebene trifft, sonst 0."""
    _, normal_a, points_a = oben
    _, normal_b, points_b = unten
    if sum(x * y for x, y in zip(normal_a, normal_b)) > -0.9999:
        return 0
    if abs(sum((points_b[0][i] - points_a[0][i]) * normal_a[i] for i in range(3))) > TOLERANZ:
        return 0
    return contact_count(points_a, points_b)


def mit_geom(extra):
    """Kontext: baugeometrie.GEOM vorübergehend erweitern (faces() liest das Modul-GEOM)."""
    class Ctx:
        def __enter__(self):
            self.alt = {k: GEOM[k] for k in extra if k in GEOM}
            GEOM.update(extra)

        def __exit__(self, *exc):
            for k in extra:
                GEOM.pop(k, None)
            GEOM.update(self.alt)
    return Ctx()


def sonderform(design):
    """Handmodellierte GEOM (Zellmasken oder Maße abweichend von teiledaten.json): Noppenzahl kein Beleg.
    Beispiel 98282: im Mappy Camper zählt das Spiel 2 Noppen, wo die Maske nur 1 kennt."""
    g = GEOM.get(design, {})
    if any(k.endswith("_zellen") for k in g):
        return True
    groesse = (_teiledaten().get(design) or {}).get("groesse")
    return bool(groesse) and [g.get("l"), g.get("w"), g.get("h")] != [groesse[0], groesse[1], groesse[2] * 10]


def _teiledaten(cache={}):
    if not cache:
        cache.update({int(k): v for k, v in json.loads((ROOT / "teiledaten.json").read_text(encoding="utf-8")).items()})
    return cache


def beobachtungen(vehicles, kandidaten):
    """Je Kandidat: (Seite, FieldIndex, gespeicherte Stärke, vorhergesagte Noppen, Beleg)."""
    obs = collections.defaultdict(list)
    ohne_kontakt = collections.Counter()
    with mit_geom({d: hypothese(g) for d, g in kandidaten.items()}):
        for v in vehicles:
            parts = teile_des_fahrzeugs(v)
            flaechen = {}
            seen = set()
            for c in v["PartGraph"]["Connections"]["items"]:
                sig = canonical(c)
                if sig in seen:
                    continue
                seen.add(sig)
                kind = c['Type'].split('::')[-1]
                expected = 'HingeConnection' if c['Strength'] == 1 else 'FixedConnection'
                if kind != expected:
                    continue  # Clips/Achsen/Kugeln sind keine Noppenflächen-Belege.
                for t, p, ft in ((c["PartIndexA"], c["PartIndexB"], c["FieldIndexA"]),
                                 (c["PartIndexB"], c["PartIndexA"], c["FieldIndexB"])):
                    dt, dp = parts[t]["design"], parts[p]["design"]
                    if dt not in kandidaten or dp in kandidaten or dp not in GEOM or GEOM[dp].get("maske_unbekannt"):
                        continue
                    for i in (t, p):
                        if i not in flaechen:
                            flaechen[i] = faces(parts[i])
                    ft_t, ft_p = flaechen[t], flaechen[p]
                    treffer = []
                    partner_field = c['FieldIndexB'] if t == c['PartIndexA'] else c['FieldIndexA']
                    if "unten" in ft_t and "oben" in ft_p:
                        n = flaechenkontakt(ft_p["oben"], ft_t["unten"])
                        if n and ft_p['oben'][0] == partner_field:
                            treffer.append(("unten", n))
                    if "oben" in ft_t and "unten" in ft_p:
                        n = flaechenkontakt(ft_t["oben"], ft_p["unten"])
                        if n and ft_p['unten'][0] == partner_field:
                            treffer.append(("oben", n))
                    if len(treffer) != 1:
                        ohne_kontakt[dt] += 1  # Seitennoppe, Clip, skaliert o. Ä.: kein Flächenbeleg.
                        continue
                    seite, n = treffer[0]
                    obs[dt].append({"seite": seite, "feld": ft, "staerke": c["Strength"], "vorhergesagt": n,
                                    "schief": not im_raster(parts[t]["rot"], parts[p]["rot"]) or sonderform(dp),
                                    "fahrzeug": v["VehicleName"], "indizes": [t, p], "partner": dp,
                                    "partner_feld": c["FieldIndexB"] if t == c["PartIndexA"] else c["FieldIndexA"]})
    return obs, ohne_kontakt


def bewerte(design, groesse, obs, ohne_kontakt, vorbild=None):
    """vorbild: GEOM des Originals, wenn das Teil laut teiledaten.json ein Alias davon ist."""
    geo = dict(l=groesse[0], w=groesse[1], h=groesse[2] * 10, unten=None, oben=None)
    mindestens = 1 if vorbild else MIN_BELEGE
    seiten = {}
    widerspruch = []
    for seite in ("unten", "oben"):
        items = [o for o in obs if o["seite"] == seite]
        felder = collections.Counter(o["feld"] for o in items)
        falsch = [o for o in items if o["staerke"] != o["vorhergesagt"] and not o.get("schief")]
        seiten[seite] = {"belege": len(items), "felder": dict(felder), "noppenzahl_abweichend": len(falsch),
                         "schief": sum(1 for o in items if o.get("schief")),
                         "fahrzeuge": len({o["fahrzeug"] for o in items})}
        if len(felder) > 1:
            widerspruch.append(f"{seite}: mehrere Felder {dict(felder)}")
        if falsch:
            widerspruch.append(f"{seite}: {len(falsch)} Kontakte mit anderer Noppenzahl als vorhergesagt")
        if vorbild and felder and set(felder) != {vorbild.get(seite)}:
            widerspruch.append(f"{seite}: Felder {dict(felder)} weichen vom Original ab")
        geometric_items = [o for o in items if not o.get('schief')]
        if len(felder) == 1 and not falsch and len(geometric_items) >= mindestens:
            geo[seite] = next(iter(felder))
    if geo["unten"] is not None and geo["unten"] == geo["oben"]:
        widerspruch.append("Unter- und Oberseite mit gleichem Feld")
    angenommen = not widerspruch and (geo["unten"] is not None or geo["oben"] is not None)
    return {"teil": design, "groesse": groesse, "geom": geo if angenommen else None, "seiten": seiten,
            "ohne_flaechenkontakt": ohne_kontakt, "widerspruch": widerspruch,
            "beispiele": obs[:6], "alias_von": vorbild and vorbild["_nummer"],
            "status": "angenommen" if angenommen else
            ("widerspruechlich" if widerspruch else "zu_wenig_belege")}


def gegentest(vehicles, neu):
    """Erweiterte GEOM: vorhergesagte Flächenverbindungen der neuen Teile gegen gespeicherte Verbindungen."""
    stat = collections.defaultdict(lambda: collections.Counter())
    with mit_geom(neu):
        for v in vehicles:
            parts = teile_des_fahrzeugs(v)
            gespeichert = {}
            for c in v["PartGraph"]["Connections"]["items"]:
                a, b, fa, fb = c["PartIndexA"], c["PartIndexB"], c["FieldIndexA"], c["FieldIndexB"]
                key = (a, b, fa, fb) if a < b else (b, a, fb, fa)
                gespeichert.setdefault(key, set()).add((c['Strength'], c['Type'].split('::')[-1]))
            flaechen = [faces(p) if p["design"] in GEOM and not GEOM[p["design"]].get("maske_unbekannt") else {}
                        for p in parts]
            for a, fa in enumerate(flaechen):
                for b, fb in enumerate(flaechen):
                    if a == b or "oben" not in fa or "unten" not in fb:
                        continue
                    da, db = parts[a]["design"], parts[b]["design"]
                    if da not in neu and db not in neu:
                        continue
                    n = flaechenkontakt(fa["oben"], fb["unten"])
                    if not n:
                        continue
                    if not im_raster(parts[a]["rot"], parts[b]["rot"]) or sonderform(da) or sonderform(db):
                        for d in {da, db} & set(neu):
                            stat[d]["schief_uebersprungen"] += 1
                        continue
                    key = (a, b, fa["oben"][0], fb["unten"][0]) if a < b else (b, a, fb["unten"][0], fa["oben"][0])
                    expected = (n, 'HingeConnection' if n == 1 else 'FixedConnection')
                    ergebnis = ("exakt" if expected in gespeichert.get(key, set()) else
                                "andere_staerke" if key in gespeichert and not any(s == n for s, _ in gespeichert[key]) else
                                "anderer_typ" if key in gespeichert else
                                "nicht_gespeichert")
                    for d in {da, db} & set(neu):
                        stat[d][ergebnis] += 1
                        stat[d]["vorhergesagt"] += 1
    return {d: dict(s) for d, s in stat.items()}


def alias_vorbild(design, teile):
    """GEOM-Teil, als dessen Alias teiledaten.json das Teil führt (gleiche Größe vorausgesetzt)."""
    for original, eintrag in teile.items():
        if original != design and original in GEOM and design in eintrag.get("aliase", []):
            g = GEOM[original]
            if [g["l"], g["w"], g["h"]] == [*teile[design]["groesse"][:2], teile[design]["groesse"][2] * 10]:
                return dict(g, _nummer=original)
    return None


def analysiere(vehicles, kandidaten, teile):
    obs, ohne = beobachtungen(vehicles, kandidaten)
    ergebnisse = [bewerte(d, kandidaten[d], obs.get(d, []), ohne.get(d, 0), alias_vorbild(d, teile))
                  for d in sorted(kandidaten)]
    neu = {e["teil"]: e["geom"] for e in ergebnisse if e["geom"]}
    test = gegentest(vehicles, neu)
    for e in ergebnisse:
        e["gegentest"] = test.get(e["teil"], {})
        if e["geom"] and (e["gegentest"].get("andere_staerke") or e["gegentest"].get("anderer_typ") or e["gegentest"].get("nicht_gespeichert")):
            e["status"] = "gegentest_abweichend"
        elif e['geom'] and not e['gegentest'].get('exakt'):
            e['status'] = 'gegentest_ohne_belege'
    return ergebnisse


def pruefe_vorhandene(vehicles, teile):
    """Leave-one-out: jedes vorhandene einfache GEOM-Teil so ableiten, als wäre es unbekannt."""
    ergebnis = []
    for d in sorted(GEOM):
        g = GEOM[d]
        if (not EINFACH.match((teile.get(d) or {}).get("name") or "") or g.get("maske_unbekannt")
                or any(k.endswith("_zellen") for k in g)):
            continue
        with mit_geom({}):
            del GEOM[d]
            try:
                e = analysiere(vehicles, {d: teile[d]["groesse"]}, teile)[0]
            finally:
                GEOM[d] = g
        neu = e["geom"] or {}
        konflikt = [k for k in ("l", "w", "h", "unten", "oben")
                    if neu.get(k) is not None and g.get(k) is not None and neu[k] != g[k]]
        ergaenzbar = {k: neu[k] for k in ("unten", "oben") if g.get(k) is None and neu.get(k) is not None}
        ergebnis.append({"teil": d, "status": e["status"], "konflikt": konflikt,
                         "ergaenzbar": ergaenzbar if e["status"] == "angenommen" else {},
                         "gegentest": e["gegentest"]})
    return ergebnis


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("spielstaende", nargs="*")
    parser.add_argument("--teile", nargs="+", type=int)
    parser.add_argument("--json")
    parser.add_argument("--vorhandene", action="store_true",
                        help="vorhandene einfache GEOM-Teile per Leave-one-out gegenprüfen")
    args = parser.parse_args(argv)
    teile = {int(k): v for k, v in json.loads((ROOT / "teiledaten.json").read_text(encoding="utf-8")).items()}
    wanted = args.teile or einfache_teile(teile)
    kandidaten = {d: teile[d]["groesse"] for d in wanted if d in teile and d not in GEOM}
    pfade = anschluesse.expand(args.spielstaende) or anschluesse.alle_spielstaende()
    vehicles = list(anschluesse.unique_vehicles(pfade))
    ergebnisse = analysiere(vehicles, kandidaten, teile)
    vorhandene = pruefe_vorhandene(vehicles, teile) if args.vorhandene else None
    bericht = {"hinweis": "Größe und Noppenraster sind Annahmen; Felder und Noppenzahlen aus gespeicherten "
                          "Verbindungen belegt. Nur Ober-/Unterseiten, keine Seitennoppen.",
               "fahrzeuge": len(vehicles), "dateien": [Path(p).name for p in pfade],
               "min_belege": MIN_BELEGE, "ergebnisse": ergebnisse, "vorhandene_leave_one_out": vorhandene}
    for e in ergebnisse:
        s = e["seiten"]
        print(f"{e['teil']:6d} {teiledaten_name(teile, e['teil']):20s} {e['status']:22s} "
              f"unten {s['unten']['felder']} oben {s['oben']['felder']} gegentest {e['gegentest']}")
    print("\nFür baugeometrie.GEOM (nur angenommen und Gegentest exakt):")
    for e in ergebnisse:
        if e["status"] == "angenommen":
            g = e["geom"]
            print(f"    {e['teil']}: dict(l={g['l']}, w={g['w']}, h={g['h']}, unten={g['unten']}, oben={g['oben']}),")
    for v in vorhandene or []:
        if v["konflikt"] or v["ergaenzbar"] or v["status"] != "angenommen":
            print(f"vorhanden {v['teil']}: {v['status']} Konflikt {v['konflikt']} ergänzbar {v['ergaenzbar']} "
                  f"gegentest {v['gegentest']}")
    if vorhandene is not None:
        print(f"Leave-one-out: {sum(not v['konflikt'] for v in vorhandene)} von {len(vorhandene)} ohne Konflikt")
    if args.json:
        Path(args.json).write_text(json.dumps(bericht, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return bericht


def teiledaten_name(teile, d):
    return (teile.get(d) or {}).get("name") or "?"


if __name__ == "__main__":
    main()

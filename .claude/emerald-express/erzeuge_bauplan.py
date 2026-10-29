"""Bauplan Emerald Express (31015, Hauptmodell, Anleitung 6071644 S. 2-13). Vorne = +x, Noppe 25, Platte 10.

Basis: unverändertes Startchassis "Alte Schule" (FireEngine_10263: Platte 2x12, zwei Radhalter 30157,
Räder 56902 + Reifen 61254) aus einer lokalen Sicherung.
Aufruf (im Projektordner): python .claude/emerald-express/erzeuge_bauplan.py werkzeuge baupläne/emerald_express.json
Herleitung und Belege: .claude/emerald-express/analyse.md
"""
import json
import sys

sys.path.insert(0, sys.argv[1])
from baugeometrie import quat_z  # noqa: E402

VORLAGE = "_sicherungen/geschrieben_2026-10-29_21-17-19_9935dab8/ArtemisVehicle.sav"
LBG, DBG, SCHWARZ, ROT, DG, KLAR, TGELB = 1, 12, 11, 7, 38, 16, 20
QC = (0.5, 0.5, 0.5, 0.5)        # liegend: lokal z -> Welt x, lokal x -> y, lokal y -> z (vom Spiel gespeichert)
QX = (1.0, 0.0, 0.0, 0.0)        # 180° um x: kopfüber
Q1 = quat_z(-90)                 # Winkel 3956 wie vom Spiel gespeichert

teile, verbindungen = [], []


def r(q):
    return [round(v, 7) for v in q]


def teil(id_, nr, farbe, pos, dreh=None, rot=None, leuchtend=False):
    t = {"id": id_, "teil": nr, "farbe": farbe, "pos": [round(v, 4) for v in pos]}
    if rot is not None:
        t["rot"] = r(rot)
    elif dreh:
        t["dreh"] = dreh
    if leuchtend:
        t["leuchtend"] = True
    teile.append(t)


def verb(a, b, fa, fb, noppen):
    verbindungen.append({"a": a, "b": b, "fa": fa, "fb": fb, "noppen": noppen,
                         "typ": "FixedConnection" if noppen > 1 else "HingeConnection"})


# --- Rahmen, Anleitung S. 4 Schritt 1-2: unten DBG 2x6 / vorn LBG, darüber LBG 2x6 (z=30, Oberkante 40)
teil("rahmen_hinten", 3795, DBG, (-137.5, 12.5, 20))           # auf hinterem 30157
teil("rahmen_vorn", 3795, LBG, (12.5, 12.5, 20))               # auf vorderem 30157
teil("lauf_heck", 3023, LBG, (-137.5, -12.5, 30), dreh=90)
teil("lauf_mitte", 3795, LBG, (-112.5, 12.5, 30))              # verbindet beide Rahmenplatten
teil("lauf_vorn", 3021, DBG, (37.5, 12.5, 30))
teil("lauf_bug", 3023, DBG, (112.5, -12.5, 30), dreh=90)

# --- Führerhaus (S. 6): über die Reifen (Oberkante z 45,6) angehoben; Boden 3 lang x 4 breit
teil("hausbock", 3021, DBG, (-137.5, 12.5, 40))
teil("boden_2x4", 3020, DG, (-137.5, -37.5, 50), dreh=90)
teil("boden_1x4", 3710, DG, (-87.5, -37.5, 50), dreh=90)
teil("streifen_links", 3623, ROT, (-137.5, 37.5, 60))
teil("streifen_rechts", 3623, ROT, (-137.5, -37.5, 60))
teil("rueckwand_unten", 3023, ROT, (-137.5, -12.5, 60), dreh=90)
teil("fenster_links", 3004, KLAR, (-112.5, 37.5, 70))          # 3065 gibt es im Spiel nicht
teil("fenster_rechts", 3004, KLAR, (-112.5, -37.5, 70))
teil("pfosten_links", 3005, DG, (-137.5, 37.5, 70))
teil("pfosten_rechts", 3005, DG, (-137.5, -37.5, 70))
teil("rueckwand", 3004, LBG, (-137.5, -12.5, 70), dreh=90)
# Dach steht hinten 1 Noppe über (vom Nutzer im Spiel korrigiert, vorher vorn)
teil("dach_links", 88930, SCHWARZ, (-162.5, 37.5, 100))
teil("dach_rechts", 88930, SCHWARZ, (-87.5, -37.5, 100), dreh=180)

# --- Kessel, Schornstein und Front: vom Nutzer im Spiel nach Anleitung korrigiert und gespeichert
# (29.10.2026, Platz 45, Version 2). Lagen und Anschlüsse unten sind die vom Spiel gespeicherten.
H = 0.7071068
O1 = (-37.5, 12.5, 40)
teil("winkel", 3956, SCHWARZ, O1, rot=Q1)                      # Steg x -25..-15 in der Kesselmitte
teil("kessel_hinten", 6143, DG, (-55, -12.5, 87.5), rot=QC)    # x -55..-25, Oberseite am Stegrücken
teil("kessel_vorn", 6143, DG, (-15, -12.5, 87.5), rot=QC)      # x -15..15 auf den Stegnoppen
teil("kugelplatte", 63082, SCHWARZ, (-65, -12.5, 87.5), rot=QC)
teil("kesselende", 4032, DG, (-75, -12.5, 87.5), rot=QC)       # schließt am Führerhaus ab
# Ring wie im Set: Platte 1x2 unten + Griffplatte 2540 oben, senkrecht
teil("ring_unten", 3023, SCHWARZ, (15, 12.5, 62.5), rot=(-0.5, 0.5, -0.5, 0.5))
teil("griff", 2540, SCHWARZ, (15, -12.5, 87.5), rot=QC)        # Griffstange zeigt nach oben
teil("rauchkammer", 87580, ROT, (25, -12.5, 62.5), rot=(H, 0, H, 0))
teil("tuer", 4740, SCHWARZ, (35, 0, 75), rot=QC)
teil("lampe", 98138, TGELB, (45, 0, 75), rot=QC, leuchtend=True)
# Schornstein wie im Set: Clip am Griff, Kegel kopfüber (weites Ende oben)
teil("clip", 6019, SCHWARZ, (-2.5, -2.5, 120), rot=(-H, -H, 0, 0))
teil("clipfliese", 3070, SCHWARZ, (-2.5, -2.5, 110), rot=(H, -H, 0, 0))
teil("schornstein", 3942, SCHWARZ, (-15, -15, 180), rot=QX)

# --- Front (S. 2-4): Fliese 3068 vor der Rauchkammer, Pufferbohle, Räumer, Dampfzylinder seitlich
teil("frontfliese", 3068, SCHWARZ, (12.5, 12.5, 40))
teil("pufferbohle", 3022, SCHWARZ, (137.5, 12.5, 30))
teil("raeumer_links", 3040, DBG, (162.5, 12.5, 0), dreh=270)   # Noppe in die Pufferbohle, Schräge nach vorn
teil("raeumer_rechts", 3040, DBG, (162.5, -12.5, 0), dreh=270)
teil("halter_links", 4081, SCHWARZ, (37.5, 12.5, 10))         # zwischen Chassisplatte und Rahmen
teil("halter_rechts", 4081, SCHWARZ, (37.5, -12.5, 10), dreh=180)
teil("zylinder_links", 6141, SCHWARZ, (42.5, 37.5, 17.5), rot=(-0.5, -0.5, -0.5, -0.5))
teil("zylinder_rechts", 6141, SCHWARZ, (42.5, -37.5, 17.5), rot=(-0.5, 0.5, -0.5, 0.5))

# Explizite Anschlüsse = vom Spiel gespeicherte Verbindungen der korrigierten Fassung
verb("chassis:1", "rahmen_vorn", 2, 1, 4)
verb("chassis:2", "rahmen_hinten", 2, 1, 4)
verb("winkel", "lauf_mitte", 1, 0, 4)
verb("winkel", "kessel_hinten", 2, 2, 4)
verb("winkel", "kessel_vorn", 0, 1, 4)
verb("kessel_hinten", "kugelplatte", 1, 0, 4)
verb("kugelplatte", "kesselende", 1, 0, 4)
verb("kessel_vorn", "ring_unten", 2, 1, 2)
verb("kessel_vorn", "griff", 2, 1, 2)
verb("ring_unten", "rauchkammer", 0, 1, 2)
verb("griff", "rauchkammer", 0, 1, 2)
verb("rauchkammer", "tuer", 0, 1, 1)
verb("lampe", "tuer", 0, 4, 1)
verbindungen.append({"a": "griff", "b": "clip", "fa": 4, "fb": 2, "noppen": 1, "typ": "CylindricalConnection"})
verb("clip", "schornstein", 1, 2, 1)
verb("clip", "clipfliese", 0, 0, 1)
for seite, clipfeld in (("links", 4), ("rechts", 3)):
    verb("chassis:0", f"halter_{seite}", 1, 1, 1)
    verb("rahmen_vorn", f"halter_{seite}", 1, 0, 1)
    verb(f"halter_{seite}", f"zylinder_{seite}", clipfeld, 0, 1)

plan = {
    "name": "Emerald Express",
    "vorlage_datei": VORLAGE,
    "vorlage_name": "Neues Fahrzeug 05",
    "teile": teile,
    "verbindungen": verbindungen,
}
with open(sys.argv[2], "w", encoding="utf-8") as f:
    json.dump(plan, f, ensure_ascii=False, indent=1)
    f.write("\n")

print(len(teile), "Teile,", len(verbindungen), "explizite Verbindungen")

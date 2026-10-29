"""Teile-Datenbank des Spiels (../teiledaten.json, Quelle: 2kdrivetools.github.io/partdump.js).

Je Teilenummer: name, groesse [Länge, Breite in Noppen, Höhe in Plattenhöhen (3 = 1 Stein)],
masse, aliase (Nummern, die das Spiel als dasselbe Teil führt), bild.

Aufruf: python teiledaten.py <Teilenummer oder Suchtext> ...
"""
import json
import os
import sys

PFAD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "teiledaten.json")
_daten = None


def alle():
    global _daten
    if _daten is None:
        _daten = {int(k): v for k, v in json.load(open(PFAD, encoding="utf-8")).items()}
    return _daten


def teil(design):
    """Eintrag zu einer Teilenummer, auch über Aliase; None wenn unbekannt."""
    d = alle()
    if design in d:
        return d[design]
    return next((v for v in d.values() if design in v["aliase"]), None)


def name(design):
    t = teil(design)
    return (t and t["name"]) or "?"


if __name__ == "__main__":
    for q in sys.argv[1:]:
        if q.isdigit():
            treffer = {int(q): teil(int(q))} if teil(int(q)) else {}
        else:
            treffer = {k: v for k, v in alle().items() if v["name"] and q.upper() in v["name"]}
        for k, v in treffer.items():
            print(f"{k:7d}  {v['name']}  Größe {v['groesse']}  Aliase {v['aliase']}")
        if not treffer:
            print(f"{q}: nicht gefunden")

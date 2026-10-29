"""Setzt alle Drive Passes auf die höchste Stufe (nach dem „DrivePass Maxer“ von 2kdrivetools.github.io).

Die Drive-Pass-Erfahrung steht in ArtemisPlayerInfo.sav unter
Data/LocalProgression/ValidatedRewards/DXPList, ein Wert je Saison (Index 0 = Saison 1).
Gesetzt wird wie im Original: 149000 (Stufe 99), mit Premium-Pass 150000 (Stufe 100).

Aufruf: python drivepass.py              nur anzeigen
        python drivepass.py --schreiben  Spielstand sichern und ändern (Spiel vorher komplett schließen!)
"""
import os
import shutil
import struct
import sys

import gvas_rw as g
import sichern

DATEI = os.path.join(sichern.SAVES, "ArtemisPlayerInfo.sav")
XP_FREI, XP_PREMIUM = 149000, 150000


def finde(props, name):
    """Alle Properties dieses Namens, auch in verschachtelten Structs."""
    for p in props:
        if p.name == name:
            yield p
        if isinstance(p.value, list):
            yield from finde(p.value, name)


def zahlen(prop, fmt):
    n = struct.unpack_from("<i", prop.value)[0]
    return list(struct.unpack_from(f"<{n}{fmt}", prop.value, 4))


def main(schreiben):
    sf = g.SaveFile(DATEI)
    dxp = next(finde(sf.props, "DXPList"), None)
    if dxp is None:
        sys.exit("DXPList nicht gefunden – Drive-Pass-Stand nicht änderbar.")
    alt = zahlen(dxp, "i")
    prem = next(finde(sf.props, "UnlockedDrivePasses"), None)
    premium = [b > 0 for b in zahlen(prem, "B")] if prem else []
    neu = [XP_PREMIUM if i < len(premium) and premium[i] else XP_FREI for i in range(len(alt))]

    for i, (a, b) in enumerate(zip(alt, neu)):
        print(f"Saison {i + 1}: {a:6d} XP -> {b} XP{'  (Premium)' if b == XP_PREMIUM else ''}")
    if not schreiben:
        print("Nur angezeigt. Zum Ändern: python drivepass.py --schreiben")
        return

    shutil.copytree(sichern.SAVES, sichern.DEST)
    print("Gesichert nach", os.path.normpath(sichern.DEST))
    dxp.value = struct.pack(f"<i{len(neu)}i", len(neu), *neu)
    sf.save(DATEI)
    print("Geschrieben:", DATEI)


if __name__ == "__main__":
    main("--schreiben" in sys.argv[1:])

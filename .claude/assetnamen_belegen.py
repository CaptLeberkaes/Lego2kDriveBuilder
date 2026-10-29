"""Leitet aus Laufzeitdiagnose und Katalog die belegten PrimaryAssetNames ab.

Eingabe: freischaltung/assetnamen-live.json (assetnamen_diagnose.py) und die
Katalog-Exporte. Ein Name gilt nur als belegt, wenn der Katalog ihn kennt und
genau ein passendes Paket im konfigurierten Verzeichnis des Typs existiert.
Ausgabe: freischaltung/assetnamen-belegt.json, Schreibweise wie im Spiel.
"""
import json
from pathlib import Path

HIER = Path(__file__).resolve().parent
QUELLEN = HIER / 'quellen' / 'l2kd-encyclopedia'
ARBEIT = HIER / 'freischaltung'

# PrimaryAssetType -> (Katalog, konfigurierte Verzeichnisse, mögliche Präfixe,
# die der Katalog-Export entfernt hat). Verzeichnisse laut PrimaryAssetTypesToScan.
TYPEN = {
    'Chassis': ('chassis', ['/Game/Game/Vehicle/Inventory/CarChassisConfigs/',
                            '/Game/Game/Vehicle/Inventory/BoatChassisConfigs/'], ['ChassisConfig_', '']),
    'Flair': ('flairs', ['/Game/LEGO/Flair/'], ['Flair_', '']),
    'LegoDeco': ('stickers', ['/Game/Garage/LegoAssets/Stickers/'], ['StickerGarage_']),
}


def main():
    live = json.loads((ARBEIT / 'assetnamen-live.json').read_text(encoding='utf-8'))['pakete']
    result = {}
    for typ, (katalog, verzeichnisse, praefixe) in TYPEN.items():
        pakete = {}
        for verzeichnis in verzeichnisse:
            # Nur Pakete direkt im Verzeichnis; Unterordner sind Thumbnails o. Ä.
            for name in live[verzeichnis]:
                if '/' not in name:
                    pakete.setdefault(name.lower(), set()).add(name)
        belegt, unbelegt, mehrdeutig = [], [], []
        for eintrag in json.loads((QUELLEN / (katalog + '_by_id.json')).read_text(encoding='utf-8')):
            # Website-IDs von Bildatlanten tragen "Textur/Name"; der Name zählt.
            kurz = eintrag.split('/')[-1]
            treffer = {n for p in praefixe for n in pakete.get((p + kurz).lower(), ())}
            if len(treffer) == 1:
                belegt.append(treffer.pop())
            elif treffer:
                mehrdeutig.append([eintrag, sorted(treffer)])
            else:
                unbelegt.append(eintrag)
        result[typ] = {'belegt': sorted(set(belegt)), 'nicht_im_spiel_gefunden': unbelegt,
                       'mehrdeutig': mehrdeutig}
        print(typ, 'belegt', len(set(belegt)), 'unbelegt', len(unbelegt), 'mehrdeutig', len(mehrdeutig))
    (ARBEIT / 'assetnamen-belegt.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()

# LEGO 2K Drive – eigene Fahrzeuge per Spielstand bauen

Ziel: echte LEGO-Modelle (nach Fotos) im Spiel nachbauen, indem wir die Fahrzeug-Speicherdatei direkt schreiben.
Stand: 29.10.2026, erarbeitet mit Claude Code.

Aktueller Builder mit Prüfmodus, 3D-Verbindungen, Chassis-Katalog und Regressionstests:
[Änderungen und Bedienung](.claude/builder-verbesserungen-2026-10-29.md).

## Schnellstart ohne Programmieren: 2K Drive Tools

**https://2kdrivetools.github.io/** – fertige Werkzeuge für LEGO-2K-Drive-Spielstände direkt im Browser, nichts zu installieren.
So geht's:
1. Spiel **komplett schließen** und den Spielstand-Ordner `%USERPROFILE%\Documents\My Games\Artemis\Saved\SaveGames\`
   als Sicherung irgendwohin kopieren.
2. Werkzeug öffnen, die passende `.sav`-Datei aus diesem Ordner ins Fenster ziehen.
3. Geänderte Datei herunterladen und in den Ordner zurückkopieren (alte ersetzen), Spiel starten.

Die Datei wird nur im Browser bearbeitet, nicht hochgeladen. Nützlich:
- **DrivePass Maxer** (`ArtemisPlayerInfo.sav`): alle Drive Passes auf Stufe 99 – bei uns getestet ✅
  (dasselbe macht `werkzeuge\drivepass.py`).
- **Vehicle Editor** (`ArtemisVehicle.sav`): Teilenummern und Farben eigener Fahrzeuge ändern.
- **Bricklist**, **Set List**, **Sticker List**: Nachschlagelisten aller Teile, Sets und Sticker im Spiel.

## Inhalt dieses Ordners

Repository: https://github.com/CaptLeberkaes/Lego2kDriveBuilder – klonen und Skripte aus `werkzeuge\` starten,
der Ordner kann überall liegen (die Skripte arbeiten mit relativen Pfaden und `%USERPROFILE%`).

| Datei | Inhalt |
|---|---|
| `README.md` | dieses Dokument: Format, Regeln, Erkenntnisse |
| `teilekatalog.md` | Teile im Body Shop mit Teilenummern, nach Kategorie |
| `anschlusspunkte.md` | Anschlusspunkte (FieldIndex) für ~360 Teile, Chassis, Räder, Farben-Statistik (erzeugt von `anschluesse.py --md`) |
| `anschlusspunkte.json` | dieselben Rohdaten maschinenlesbar |
| `teiledaten.json` | alle 2028 Teile des Spiels: Name, Größe, Masse, Aliase (Quelle: [2kdrivetools.github.io](https://2kdrivetools.github.io/)) |
| `werkzeuge\` | Python-Skripte (s.u.) |
| `baupläne\` | Baupläne für `baue_fahrzeug.py` |
| `test2\` | Teileliste Set 31015 mit Spiel-Abgleich, Tauschplan für gesperrte Teile |
| `Referenzfotos\` | Fotos der echten Modelle – nur lokal, nicht im Repository |
| `_sicherungen\` | Spielstand-Sicherungen von `sichern.py` – nur lokal, nicht im Repository |

## Kurzfassung

- Das Spiel hat **keine** MCP-/API-/Mod-Schnittstelle. Die Spielarchive (`.pak`) sind verschlüsselt.
- **Aber:** Fahrzeuge liegen in einer **unverschlüsselten** Unreal-Speicherdatei ohne Prüfsumme.
  Das Spiel übernimmt geänderte Dateien (getestet: Farben ✅, neue Teile ✅ – sofern Verbindungen stimmen).
- Gespeichert werden **echte LEGO-Teilenummern**, Farbindex, Position/Drehung und die Noppen-Verbindungen.
- Teile ohne Verbindungseintrag lädt das Spiel, markiert sie aber als **„lose“** und verweigert das Speichern.
  Beim Laden berechnet das Spiel Verbindungen **nicht** neu → man muss sie selbst schreiben.
  **Beim Speichern berechnet das Spiel sie neu** (falsche Noppenzahl, nicht berührende Teile werden korrigiert).
  Der Builder prüft vor dem Schreiben für jedes normale Teil einen Verbindungspfad zum Chassis.
  Das ersetzt keine vollständige Prüfung der physischen Baubarkeit.

## Sicherheitsregeln

1. **Spiel komplett schließen**, bevor die Datei geändert wird. Das Spiel liest den Spielstand nur beim Start
   und überschreibt ihn beim nächsten Speichern mit seinem Stand im Speicher.
2. **Vorher sichern:** `python werkzeuge\sichern.py` (kopiert alle Spielstände nach `_sicherungen\`).
3. Steam Cloud kann lokale Dateien überschreiben – bei Problemen für das Spiel kurz deaktivieren.
4. Spielstände **nicht weitergeben**: sie enthalten die Spieler-ID (`OriginalCreatorId`).

## Wo liegt was

`%USERPROFILE%\Documents\My Games\Artemis\Saved\SaveGames\`

| Datei | Inhalt |
|---|---|
| `ArtemisVehicle.sav` | **eigene Fahrzeuge** (`CustomVehicles`, 50 Plätze) |
| `ArtemisDownloadedVehicle.sav` | aus dem Creators Hub geladene Fahrzeuge (`DownloadedVehicles`) – ideale Vorlagen |
| `ArtemisExtraVehicle.sav` | gleiches Format, bei uns leer |
| übrige `.sav` | Einstellungen, Spielerfortschritt, Caches |

Tipp: Im Creators Hub Modelle herunterladen → `werkzeuge\anschluesse.py` lernt daraus weitere Teile.
Ein geladenes Modell in der Garage zu ändern erzeugt eine Kopie in `ArtemisVehicle.sav`.

## Dateiformat (`ArtemisVehicle.sav`)

Unreal Engine 4.27 „GVAS“, Klasse `/Script/Artemis.ArtemisVehicleSaveGame`.

```
Data
├─ CustomVehicles[50] (CustomVehicleInfo)       leere Plätze: VehicleName ""
│  ├─ ChassisConfig      bestimmt Kategorie Straße/Gelände/Wasser
│  ├─ Guid, VehicleName, VersionId, LastEdited
│  ├─ VehicleClass       CAR / BOAT
│  ├─ PartGraph
│  │  ├─ Parts[]            je 8 Byte (s.u.)
│  │  ├─ PartTransforms[]   Rotation (Quaternion x,y,z,w), Translation, Scale3D
│  │  ├─ Assemblies[]       Baugruppen: Chassis, Flairs, Räder (fl/fr/bl/br) mit PartOffset/NumParts
│  │  └─ Connections[]      PartIndexA/B, FieldIndexA/B, Strength, Type
│  ├─ Sockets[]          z.B. Fahrersitz: SocketName TrafficSeat_DriverSit, BrickIndex
│  ├─ FlairTriggers[]    Auslöser je Flair, z.B. EFlairTrigger::GAS
│  ├─ EngineConfig, HornOverride   Motor- und Hupen-Sound
│  └─ OriginalCreatorId / ImmediateCreatorId   ← Spieler-ID
├─ GarageSaveDataMap     Zusatzdaten je Fahrzeug-Guid (Bounds)
└─ AncillaryCustomVehicle / …Slot / …GarageSaveData
                         Arbeitskopie, nur solange die Garage offen ist
```

**Achtung Arbeitskopie:** Wird das Spiel mit offener Garage beendet, bleibt `AncillaryCustomVehicle` im
Spielstand. Beim nächsten Start schreibt das Spiel diese Kopie über den Platz aus `AncillaryCustomSlot`
– eigene Änderungen an diesem Platz sind dann weg. Also: Garage verlassen, bevor man das Spiel schließt,
oder die Arbeitskopie mit ändern (`tausche_teile.py` macht das).

### Ein Teil (8 Byte in `Parts`)

| Byte | Bedeutung |
|---|---|
| 0–3 | LEGO-Teilenummer (uint32, little endian) |
| 4 | **Farbindex** (Tabelle unten) |
| 5 | **Bitfeld**: 1 = **leuchtend**, 2 = Teil einer Chassis-/Rad-Baugruppe, 4 = sitzt direkt auf dem Chassis (s.u.) |
| 6–7 | 0 |

`Parts[i]` gehört zu `PartTransforms[i]`. Das Spiel sortiert beim Speichern: Chassis-Teile zuerst, Räder zuletzt.

Byte 5 im Detail (geprüft an 20 Fahrzeugen):
- Bit 2 (Wert 2) steht **genau** bei den Teilen der Chassis- und Rad-Baugruppen (4016 von 4016 Teilen).
- Bit 4 (Wert 4) steht bei Teilen, die direkt mit dem Chassis verbunden sind (304 von 312 Fällen).
  Unsere Baupläne setzen es nicht – das Spiel lädt und speichert sie trotzdem. Unkritisch.
- Kombinationen: 3 = Chassis-Teil leuchtend, 5 = am Chassis und leuchtend.

### Koordinaten

- 1 Noppe = **25** Einheiten, Platte = **10** hoch, Stein = **30** hoch. `Translation.z` = Unterkante.
- x = Längsachse, y = Querachse, z = oben. Quaternion `[0,0,-0.707,0.707]` = 90° um die Hochachse.
- LDraw (BrickLink Studio): 20 LDU = 1 Noppe → Faktor 1,25; Platte 8 LDU → 10.

### Verbindungen (`Connections`)

- Meist `PartIndexA` < `PartIndexB` (Indizes in `Parts`); das Spiel schreibt aber auch die umgekehrte Reihenfolge.
- `FieldIndex` = Anschlusspunkt des Teils. **Die Nummerierung ist je Teil verschieden!**
  Beispiele: 3004/3005/3007/3020/92583: 0 = Noppen oben, 1 = Unterseite;
  3001/3002/3021/3039/3660/3823/98282: 0 = Unterseite, 1 = oben. → siehe `anschlusspunkte.md`.
- `Strength` = Anzahl ineinandergreifender Noppen. `Type`: **HingeConnection** bei 1 Noppe (drehbar), sonst **FixedConnection**.
  Weitere Typen (immer `Strength` 1): **CylindricalConnection** = Stange/Pin in rundem Loch (z.B. 4274 Pin + 6126 Flamme,
  3700 Technic-Stein + 24316 Achse), **PrismaticConnection** = Achse in Kreuzloch (3708 + 32064, 65249 + 32123),
  **BallConnection** = Kugelgelenk (14417 + 14418).
- Verbindungen können einmal, doppelt oder dreifach vorkommen, auch innerhalb von Baugruppen.
  Bestehende Einträge bleiben erhalten; beim Lernen zählen identische Einträge je Fahrzeug nur einmal.

### Teilenummern

- Im Body Shop lassen sich Teilenummern einblenden; der **Teilefinder** sucht nach Elementnummer.
- Katalognummer ≠ immer Dateinummer: Katalog **93888** (Stein 2×8) wird als **3007** gespeichert.
  Im Mammoth-Chassis steht 93888 aber selbst in der Datei – fürs eigene Bauen weiter 3007 verwenden.
- Kein Kotflügel im Katalog, aber der Teilefinder findet **98282** (Mudguard 4×2.5×1 2/3 mit Bogen).

## Farben

Farbauswahl im Body Shop: Reiter Matt, Durchsichtig, Metallic, Leuchtend. Jede Farbe hat einen eigenen Index;
„Leuchtend“ = Index einer durchsichtigen Farbe + Oberflächen-Byte 1.

| Index | Farbe | | Index | Farbe |
|---|---|---|---|---|
| 1 | Hellgrau (wirkt fast weiß!) | | 17 | Trans-Rot |
| 2 | Hellgelb | | 18 | Trans-Hellblau |
| 3 | Beige (vermutet) | | 19 | Trans-Blau |
| 4 | Rosa | | 20 | Trans-Gelb |
| 5 | Hell-Aqua | | 21 | Trans-Orange |
| 6 | Nougat/Hellorange (vermutet) | | 22 | Trans-Grün |
| 7 | Rot | | 23 | Trans-Hellgelb |
| 8 | Blau (Propellerblätter Explorateur) | | 24 | **Weiß** |
| 9 | Gelb | | 25 | Pastellblau |
| 10 | Braun | | 26 | Hell-Gelborange |
| 11 | Schwarz | | 27 | Orange |
| 12 | Mittelgrau | | 28 | Türkis/Petrol |
| 13 | Hellgrün | | 29 | Trans-Schwarz |
| 14 | Pastellgrün | | 30 | Trans-Rosa |
| 15 | Dunkelorange | | 31 | Limette (Radnaben-Ring the cooker) |
| 16 | Trans-Klar | | 32 | Magenta |
| 40 | Metallic Blaugrau | | 85 | Trans-Hellgrün |
| 68 | Metallic Silber (Düsen) | | 95 | Rauchglas |
| 49 | Felgen-Hellgrau | | 255 | feste Farbe (Reifen) |
| 44 | Dunkelrot | | 58 | Lila |
| 38 | Dunkelgrün | | 37 | Dunkelblau (Zierstreifen Explorateur) |
| 86 | Chrom-Silber (Motorzylinder the cooker) | | 69 | Dunkelgrau (vermutet) |
| 88 | Weiß/Silber (Magnetspitzen, vermutet) | | 0 | Teil-Standardfarbe? (Hebelgriffe 4593) |

Weitere Indizes kommen in Vorlagen vor (33, 36, 44, 45, 46, 47, 51, 57, 62, 64, 66, 71, 80, 83, 87 …) – noch nicht zugeordnet.

## Chassis, Räder, Flairs

- Das Chassis (`ChassisConfig` + Chassis-Baugruppe) legt die Kategorie fest:
  `GarageChampionStreet` = Straße (häufigstes), `PoliceTruck_7032_Garage` = Gelände, `ATV_20014` = Quad,
  `WakePro`/`Speedboat_4641_Garage` = Boot (`VehicleClass BOAT`). Liste: `anschlusspunkte.md`.
- Räder sind Baugruppen (`/Game/LEGO/Wheel/…`), z.B. `6014_6015`, `55981_58090_Reversed`, `18977_66727_Lunar`.
- Flairs sind Baugruppen aus normalen Teilen (`/Game/LEGO/Flair/…`), z.B. `Flair_Jets2_Green` = 98302×2, 3022, 3587.
  Auslöser stehen in `FlairTriggers` (20 Möglichkeiten: Boost, Gas, Bremsen, Steuern, Hupe, Rückwärts …).
  **Ein Eintrag je Flair-Baugruppe, in derselben Reihenfolge wie die Flairs in `Assemblies`** (an 20 Fahrzeugen
  geprüft). Nicht mitgezählt: Chassis, Räder, `Assemblies/73081` (Lenkrad) und `Assemblies/73587` (Hebel).
  Gesehene Werte: `ALWAYSON`, `WHILEBOOSTBINARY`, `WHILENIGHTTIME`, `REVERSE`.
- Neben Deko-Flairs gibt es **Aktiv-Flairs** (`Flair/Activeflair_…`): Magnet2, Camera, Bumper2, CollectableDetector2.
  Ebenfalls Baugruppen aus normalen Teilen; Boote bekommen ihren Antrieb als Flair (`Flair_HydroPropellerSpoiler_…`).
- **Fahrer:** `Sockets[].BrickIndex` zeigt auf das Teil, auf dem die Figur sitzt (4079 Sitz 2×2, im Boot 33909);
  `RelativeLocation/RelativeRotation` legen Lage und Blickrichtung relativ zu diesem Teil fest.
- Räder können mehr als Felge + Reifen enthalten: `BuzzosRoyalRigWheelBack_VC000` = 2654 Radkappe, 4032 Ring,
  55976 Ballonreifen, 56145 Felge. Vorder- und Hinterachse dürfen unterschiedlich breit sein.

## Werkzeuge (`werkzeuge\`, Python 3)

| Skript | Zweck |
|---|---|
| `sichern.py` | alle Spielstände mit Zeitstempel sichern |
| `zeige_fahrzeug.py [datei]` | eigene Fahrzeuge mit Teilen, Farben, Positionen und Teilenamen auflisten |
| `teiledaten.py <nummer\|text>…` | Teil in `teiledaten.json` nachschlagen (auch über Aliase), z.B. `teiledaten.py 3956 "PLATE 2X2"` |
| `drivepass.py [--schreiben]` | alle Drive Passes auf Stufe 99 setzen (ohne Option nur anzeigen; mit Option vorher automatisch sichern) |
| `gvas.py <datei> [ausgabe.json]` | kompletter Spielstand als JSON |
| `anschluesse.py <sav…> [--json out] [--md out]` | Anschlusspunkte je Teil aus allen Fahrzeugen lernen; mit `--json anschlusspunkte.json --md anschlusspunkte.md` beide Dateien neu erzeugen |
| `gvas_rw.py` | Spielstand lesen **und schreiben** (Byte-genau getestet) |
| `baue_fahrzeug.py <quelle.sav> <ziel.sav> <bauplan.json>` | **neues Fahrzeug** aus Bauplan: Chassis/Räder aus Vorlage, Karosserie aus Teileliste, Verbindungen berechnet; gleichnamiges Fahrzeug wird ersetzt |
| `tausche_teile.py <quelle.sav> <ziel.sav> <tausch.json>` | Platzhalter-Teile gegen andere Teilenummern tauschen (inkl. Garagen-Arbeitskopie) |
| `add_parts.py <quelle> <ziel> <vorlage-index> <plan.json>` | (alt) Teile an Fahrzeug auf Platz 0 anhängen, ohne Verbindungen |

### Baupläne (`baupläne\*.json`)

```json
{"name": "test1",
 "vorlage_datei": "%USERPROFILE%/Documents/My Games/Artemis/Saved/SaveGames/ArtemisDownloadedVehicle.sav",
 "vorlage_name": "Brute Chopper",
 "chassisfarben": {"4212": 1, "6014": 1, "6015": 11},
 "teile": [{"teil": 98282, "farbe": 27, "pos": [-87.5, 12.5, 50], "dreh": 0, "leuchtend": false}]}
```

- `pos` = Mitte der Ecknoppe (lokal 0,0), z = Unterkante; Teil liegt lokal entlang +x (Länge) und −y (Breite).
- `dreh` = Drehung um die Hochachse in Grad; alternativ `rot` = Quaternion `[x,y,z,w]` für volle 3D-Lagen.
  Unbekannte Anschlussgeometrie erfordert ausdrücklich vorgegebene Verbindungen; Einzelheiten im aktuellen Builder-Dokument unter `.claude/`.
- `felgen`: Felgenfarbe je Rad, z.B. `{"fl": 1, "fr": 1}` (fl/fr = vorne, bl/br = hinten).
- `radtausch`: Rad-Baugruppe aus anderem Fahrzeug übernehmen, z.B. `{"fl": "Bulldozest", "fr": "Bulldozest"}`
  (dort: Räder 13971_61254 = Eisenbahn-artige Felge). Lage wird an die alten Räder angepasst.
- Chassis PoliceTruck (4×10-Platte 4212, Oberkante z = 50): Noppen in den inneren Reihen (y = ±12,5) überall
  außer Mittelloch (x = −12,5/12,5); äußere Reihen (y = ±37,5) nur bei x = −112,5, −37,5, −12,5, 12,5, 37,5, 112,5.
- Neue Teilegeometrie in `GEOM` (`werkzeuge/baugeometrie.py`) eintragen: Länge, Breite, Höhe, belegte Anschlusspunkte unten/oben.
  Unbekannte Masken nicht aus der gesamten Fläche eines Nachbarteils ableiten; siehe den Geometrie-Lerner und die Belege unter `.claude/`.

### Kotflügel 98282

Noppenblock 2×1 am Ursprung, 1 Stein hoch; Bogen ragt nach +y. Links ungedreht, rechts 180° gedreht,
Block direkt über dem Rad (z.B. PoliceTruck: x = −87,5/62,5 bei y = 12,5 bzw. 180° bei x = −62,5/87,5, y = −12,5).

### Gesperrte Drive-Pass-Teile (Platzhalter-Tausch)

Teile aus dem nicht mehr erhältlichen Drive Pass (z.B. 3956 Winkel 2×2–2×2, 2817 Platte mit Pin-Löchern)
lassen sich im Spiel nicht freischalten.

**Versuch 1 – Drive Pass hochsetzen:** `python werkzeuge\drivepass.py --schreiben` (Spiel geschlossen).
Setzt `Data/LocalProgression/ValidatedRewards/DXPList` in `ArtemisPlayerInfo.sav` (ein XP-Wert je Saison,
Index 0 = Saison 1) auf 149000 = Stufe 99, wie der „DrivePass Maxer“ von 2kdrivetools.
Stand 29.10.2026 vorher: Saison 1–3 je 0 XP, Saison 4 10 XP; `CurrentActiveDrivePassIndex` = 3.
Ergebnis 29.10.2026: Spiel übernimmt den Drive-Pass-Stand ✅; ob die gesperrten Teile damit frei sind, ist noch nicht geprüft.

**Versuch 2 – Platzhalter-Tausch** (funktioniert):
1. Im Spiel mit einem freien Platzhalter bauen (z.B. 99207 für 3956, 4032 für 6143), speichern, **Garage verlassen**, Spiel schließen.
2. Tauschplan schreiben (Beispiel `test2	ausch_fahrzeug04.json`) und `tausche_teile.py` ausführen.
3. Spiel starten, Lage im Spiel zurechtrücken und speichern – das Spiel berechnet die Verbindungen neu.

Das Spiel zeigt und verbaut die gesperrten Teile danach normal. Solche Fahrzeuge **nicht** in den Creators Hub hochladen.

Vom Spiel gespeicherte Anschlusspunkte:
- **3956** (Winkel 2×2–2×2, Ursprung der waagrechte Schenkel): 1 = Unterseite, 0 = Noppen vorn am senkrechten Schenkel, 2 = Rückseite des senkrechten Schenkels.
- **6143** (Rundstein 2×2, liegend mit Drehung (0,5, 0,5, 0,5, 0,5)): 1 = Unterseite, 2 = Noppen oben.

## Bautechniken aus Vorlagen

Ausgewertet mit `zeige_fahrzeug.py`-ähnlichen Listen (Teil, Farbe, Lage, Verbindungen). Koordinaten wie oben.

### „the cooker“ – Gelände-Buggy mit Chrom-Motoren (Mammoth-Chassis, 252 Teile)

- **Chassis** `Mammoth_VC000` (44 Teile, Grundplatten 3028/3033 6×12/6×10), Oberkante z = 81,7 → Karosserie beginnt dort.
  Achsen bei x = ±200; Spur vorn y = ±125, hinten ±175 (hinten breiter). Räder mit Radkappe (s.o.).
- **Chrom-Motorzylinder:** je 10 × Rundplatte 4032 (Farbe 86) liegend aneinandergereiht, Abstand 10 (= Plattenhöhe),
  Drehung `(-0,5, 0,5, -0,5, 0,5)`. Getragen von 4070 (Stein 1×1 mit Seitennoppe), Abschluss mit 3665 + 85861 + 11089.
  Oben Lufthutze 50943 auf 22885, seitlich Triebwerke 4868 an 20482 (runde Fliese mit Stangenhalter).
- **Flammen:** 6126 in Trans-Orange **leuchtend** (21/1) auf Technic-Pins 4274, die in einer Rückwand aus
  Technic-Steinen 32000/6541 stecken; unterschiedlich gedreht für unruhige Flammen. Dazu 15470/68547 in Trans-Rot
  leuchtend (17/1) als Glut. Kein Flair nötig – die Flammen leuchten immer (`FlairTriggers` leer).
- **Cockpit:** Sitz 4079 (Fahrer-Socket), statt Lenkrad zwei Hebel (`Assemblies/73587`), Scheibe 81911 in Rauchglas (95).
  Lüftungsgitter: 2412 (Gitterfliese 1×2) auf 61780.

### „Explorateur nocturne“ – Sumpfboot mit Magnet (SwampBoat-Chassis, 206 Teile)

- **Chassis** `WaterFanBoatHydro_VC000` hat nur 9 Teile: 2 × 3832 (Platte 2×10) bei z = 0 plus 3004 und
  6 × 4287 (Keil invers 3×1) an Bug und Heck. Keine Räder, `VehicleClass BOAT`, Motor `EngineConfig_BoatHydro`.
- **Rumpf:** außen bei y = ±62,5 eine Reihe 3660/3665 (Keil invers) auf z = 0 → schräger Rumpfboden; darauf
  Dunkelblau-Streifen (37) aus 3460/3623/63864 bei z = 30, oben 15068 (gebogene Fliese 2×2) als runde Deckkante.
  Bug: 41764/41765, Keilplatten 41769/41770.
- **Antrieb:** Flair `Flair_HydroPropellerSpoiler_Blue` (31 Teile, Gebläse mit blauen Blättern 4617), Auslöser `ALWAYSON`.
- **Magnet vorn:** Aktiv-Flair `Activeflair_Magnet2` (13 Teile: 35382, 6091, 3023, Kugelgelenk 14417/14418, Spitzen 3005/35382 in Farbe 88).
- **Lichter:** 6 × Flair `RoundSingleBlue` (6141 Trans-Hellblau): 4 Rücklichter bei Boost, 2 seitlich montierte
  Scheinwerfer (auf 85861) nachts.
- Zwei Lenkräder und zwei Sitze 33909 – nur einer ist Fahrerplatz (Socket), der andere Deko.
- Abgeleitetes Modell: `OriginalParentGuid` gesetzt, `VersionId` 8 (Remix eines anderen Fahrzeugs).

### Außerdem neu geladen

- „New Vehicle 29“ (`ExtremeSpeed_VC000`, 119 Teile): großes Düsentriebwerk als Flair `Jet_Engine_Big_Green`
  (26 Teile, bei Boost), dazu Aktiv-Flairs Camera und Bumper2. Räder 55981_30648.
- „Minigame bots farm“ (`ShowOff`, 350 Teile): 4 Rückfahrlichter (`SquareSingleWhite`, Auslöser `REVERSE`), Räder 56145_61481.

## Testprotokoll

1. Format gelesen, Farbe = Byte 4 (Stein 1×1: 1 → 7). Keine Prüfsumme.
2. 10 Teile per Datei umgefärbt → Spiel lädt korrekt. ✅
3. 19 neue 1×1-Steine ohne Verbindungen → sichtbar, aber „lose“, Speichern gesperrt. ✅ (Erkenntnis)
4. Vom Spiel gespeicherte Verbindungen, Flairs, Leuchten, Metallic, Transparent ausgewertet. ✅
5. 12 Creators-Hub-Modelle ausgewertet → Anschlusspunkte für ~290 Teile. ✅
6. **test1 komplett per Bauplan geschrieben → Spiel lädt und speichert es ohne lose Teile.** ✅
   Einzige Korrektur: Ausrichtung der Kotflügel (jetzt im Bauplan richtig).
7. Gesperrte Teile 3956 und 6143 per Platzhalter-Tausch in „Neues Fahrzeug 04“ → Spiel zeigt sie an,
   Lage im Spiel korrigiert und gespeichert. ✅ Erster Versuch ging verloren, weil die Garagen-Arbeitskopie
   den alten Stand zurückschrieb.
8. 4 weitere Creators-Hub-Modelle (u.a. „the cooker“, „Explorateur nocturne“) ausgewertet → ~360 Teile,
   Bedeutung von Oberflächen-Bit 2/4, Reihenfolge der Flair-Auslöser, neue Verbindungstypen. ✅
9. **„Shuttle Rover“** (`baupläne/raketen_shuttle.json`, 134 Karosserieteile): orange Außentank, weiße Booster,
   Space Shuttle oben drauf, leuchtende Flammen, 17 Noppen lang → Spiel lädt ohne Fehler. ✅
   Erstmals verwendet: Schrägen 3040 (Noppe am Ursprung, Schräge nach lokal +y; `dreh` 270 = nach vorn),
   2445, 3031, 3460, 3062, 88930 als runde Oberkante; Teile unter Platten hängend (Düsen, Flammen).

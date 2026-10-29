# Übergabe: sechs Studio-Modelle prüfen und in die Spielgarage übernehmen

Stand: 29.10.2026. Der Nutzer hat die Arbeit mit „pause“ angehalten und danach ausdrücklich diese Übergabe für einen anderen Chat angefordert. In diesem Chat den Import nicht eigenmächtig wieder aufnehmen. Der andere Chat soll nach Nutzerauftrag weiterarbeiten.

## Ziel des Nutzers

Die sechs Modelle aus `Download/` auf Schadcode prüfen, analysieren und **direkt als eigene Fahrzeuge in der Garage von LEGO 2K Drive** übernehmen. Der Nutzer hat ausdrücklich „Direkt in die Spielgarage“ gewählt und anschließend vorgeschlagen, pro Fahrzeug eine neue Datei/einen neuen Garageneintrag anzulegen. Er meint nicht nur eine Projektablage. Bestehende Fahrzeuge sollen für den Import nicht ersetzt werden.

**Tatsächlicher Stand: Noch keines der sechs Fahrzeuge wurde importiert. Dieser Chat hat für diesen Auftrag keinen echten Spielstand verändert.** Keine Platzhalter oder unvollständig verbundenen Fahrzeuge als fertigen Import ausgeben.

## Projekt und Regeln

- Projekt: `C:\Users\Ben\Documents\_PRIVATE\Git\Lego2kDriveBuilder`.
- Der Nutzer schrieb einmal einen Pfad ohne Backslash zwischen `Documents` und `_PRIVATE`; die tatsächlich vorhandenen Dateien liegen im oben genannten Projekt unter `Download`.
- KI-Erinnerungen, Analysen und Übergaben gehören laut Nutzer in `.claude/`.
- Unsicherheit und Vermutungen ausdrücklich nennen; keine unbelegten Geometrien, Verbindungen oder erfolgreichen Spieltests behaupten.
- Bei wirklich unklaren Spezifikationen zuerst fragen; bereits geklärte Absicht „eigene Garagenfahrzeuge“ nicht erneut abfragen.
- Der Nutzer hat zuvor Änderungen an allen Projektwerkzeugen und Dateien freigegeben. Der Shuttle-Wettbewerb kommt später und gehört nicht zu diesem Importauftrag.
- Zusätzliche Änderungen an Freischaltwerkzeugen stammen aus einem anderen, parallel arbeitenden Chat. Diese Arbeiten nicht überschreiben und deren Aussagen nicht als in diesem Chat bestätigte Nutzerhistorie darstellen.

## Eingangsdateien

Alle sechs `.io`-Dateien liegen in `Download/`. Quelle laut Nutzer: Steam-Guide von KRBrickBot:
https://steamcommunity.com/sharedfiles/filedetails/?id=3411265110&l=german

| Datei | Studio-Teile | STEP-Trenner / XML-Bauschritte | Passendes Original laut externer Enzyklopädie | Original-Teile laut deren Liste |
|---|---:|---:|---|---:|
| Hamburghini Royale.io | 227 | 21 | BurgerCar_VC000 | 226 |
| Machio Beast.io | 301 | 19 | MachioWidebody_VC000 | 301 |
| Out For the Count.io | 345 | 31 | CountFistula_VC000 | 345 |
| Royal Outtaliner.io | 113 | 8 | Traffic_HV_01Street | 115 |
| Royal People Rover.io | 132 | 10 | Traffic_HV_01Offroad | 131 |
| Royal Sailor.io | 123 | 9 | Traffic_HV_01Boat | 123 |

Insgesamt **1.241 LDraw-Teileinträge**. Die Original-Vergleichszahlen sind externe Daten, kein Nachweis dafür, dass der Nutzer die Originalfahrzeuge in seiner Sammlung sieht oder besitzt. Diese Verfügbarkeit wurde noch nicht geklärt. Auf die entsprechende Frage antwortete der Nutzer lediglich, ob die Fahrzeuge in der Garage zu finden sein sollten, und schlug anschließend neue Einträge vor.

Dateihashes stehen in `.claude/studio-modelle/uebersicht.json`; vor späterem Import mit den aktuellen Eingangsdateien vergleichen.

## Schadcodeprüfung: durchgeführt

Microsoft Defender wurde gezielt und ohne automatische Remediation auf den Ordner angesetzt:

```powershell
& 'C:\ProgramData\Microsoft\Windows Defender\Platform\4.18.26100.4-0\MpCmdRun.exe' -Scan -ScanType 3 -File 'C:\Users\Ben\Documents\_PRIVATE\Git\Lego2kDriveBuilder\Download' -DisableRemediation
```

Das Tool lief mit erhöhten Sandbox-Rechten aufgrund des ausdrücklichen Scanauftrags. Ergebnis: Exitcode 0, `Scan finished.` und `Scanning ...\Download found no threats.`

Keine Bedrohung gefunden ist keine Garantie gegen alle denkbaren Parser-Schwachstellen. Der Zeitpunkt der Signaturaktualisierung konnte nicht abgefragt werden: `Get-MpComputerStatus` und SecurityCenter-CIM-Abfragen meldeten im normalen Sandbox-Kontext Zugriff verweigert. Keine Aussage „Signaturen sind aktuell“ machen.

Zusätzlich wurden alle Archive statisch gelesen, nicht in Studio geöffnet oder als Code ausgeführt:

- normale, unverschlüsselte ZIP-Dateien, je sieben bekannte Einträge;
- keine ausführbaren PE-/ELF-Dateien, kein Pfad-Traversal, keine Symlinks;
- begrenzte Dateigrößen und Kompressionsraten;
- ZIP-Inhalte/CRC beim Lesen geprüft;
- LDraw-Datensätze und endliche Zahlen geprüft;
- XML ohne DOCTYPE-/ENTITY-Deklarationen;
- PNG-Vorschauen auf Struktur, CRC, Größen und korrektes Ende geprüft.

Alle sechs bestanden die implementierte Strukturprüfung. Hashes der Archive und ihrer Einträge liegen in den jeweiligen `analyse.json`-Dateien. Die Vorschauen wurden anschließend visuell angesehen.

## Bereits angelegte Werkzeuge und Ergebnisse

Neues Werkzeug, noch nicht committed:

`werkzeuge/pruefe_studio.py`

```powershell
python werkzeuge/pruefe_studio.py Download
python -m unittest discover -s .claude/tests -v
```

Das Werkzeug schreibt standardmäßig nach `.claude/studio-modelle/`, führt keinen Fremdcode aus und **erzeugt keinen Spielstand**. Den Namen nicht als bereits existierenden Studio-zu-GVAS-Importer missverstehen.

Ergebnisse:

- `.claude/studio-modelle/uebersicht.json`
- je Modell ein Unterordner, z. B. `hamburghini-royale/`, mit:
  - `analyse.json`: Teile, Matrizen, LDU-Positionen, Farben, Metadaten, Hashes, Zuordnungsstatus;
  - `teileliste.json`: Teile-/Farbmengen;
  - `vorschau.png`: unveränderte geprüfte Archivvorschau.

In allen Übersichten steht bewusst `import_status: nicht_in_spielgarage_importiert`.

Neue Tests: `.claude/tests/test_studio.py`. Letzter Lauf: **29 Tests bestanden**, bestehend aus 20 Builder-Regressionstests und neun Studio-Lesertests. Getestet werden unter anderem Traversal, verkleidete ausführbare Dateien, XML-Entitäten, Netzwerk-/Elternpfadverweise, nichtendliche Koordinaten, Teilezahlabweichungen und unbestätigte Buchstabenvarianten.

## Was die `.io`-Dateien tatsächlich enthalten

Je Archiv:

- `model.ldr`: flache LDraw-Teileliste mit Transformationen und Schritten;
- `modelv2.ldr`: Studio-erweiterte Typ-11-Teilzeilen mit zusätzlichen IDs/Flags;
- `model2.ldr`: eingebettete Teile-/Primitive-Geometrie als Mehrfachmodell;
- `model.lxfml`: XML-Modell, Kameras, Teile, Gruppen und Bauschritte;
- `thumbnail.png`, `errorPartList.err` (jeweils `[]`), `.info`.

Es wurden **keine spielnativen FieldIndex-Verbindungen** oder kompletten 2K-Drive-PartGraphs darin gefunden. Die XML-Tags enthalten ebenfalls keinen solchen Verbindungskatalog.

Wichtige Formateigenheiten:

- `model2.ldr` verwendet andere Farbzahlen als `model.ldr`; nicht blind vermischen. Beispiel: beim Hamburghini lautet die erste Farbe in `model.ldr` 19, in `model2.ldr` 2.
- Studio verwendet im eingebetteten `model2.ldr` auch kurze Typ-5-Kanten mit nur zwei Punkten. Der neue Leser akzeptiert diese ausschließlich im Geometrie-Modus; ein gewöhnlicher Standard-LDraw-Export ist das nicht automatisch.
- LDraw- und Spielursprünge sind nicht identisch. Faktor 1,25 allein reicht nicht: Achsen, lokale Teilursprünge und Rotationen müssen korrekt kalibriert werden. Im Spiel ist Z oben; eine Noppe hat 25 Spieleinheiten, in LDraw 20 LDU.
- `3829c01.dat` ist laut eingebettetem Teileheader ein Lenkrad-Verbundteil. Im Spielkatalog sind `3829` (Wheel Console) und `3828` (Steering Wheel) getrennt. Bei Machio und Out For the Count gibt es deswegen 302 bzw. 346 XML-Part-Einträge gegenüber 301 bzw. 345 LDraw-Teilezeilen. Keine einfache Positionsliste ohne Baugruppenbehandlung verwenden.

## Teileabgleich und noch fehlende Zuordnungen

`id_oder_katalogalias` bedeutet nur, dass eine Nummer im lokalen Teilekatalog oder dessen Aliaslisten gefunden wurde. Das beweist weder passende Ursprungslage noch vollständige Anschlussgeometrie. Buchstabenvarianten wurden ausdrücklich **nicht** automatisch als gleiche Geometrie bestätigt.

| Modell | ID/Katalogalias | unbestätigte Buchstabenvariante | nicht zugeordnet |
|---|---:|---:|---:|
| Hamburghini Royale | 199 | 28 | 0 |
| Machio Beast | 245 | 37 | 19 |
| Out For the Count | 306 | 34 | 5 |
| Royal Outtaliner | 100 | 11 | 2 |
| Royal People Rover | 118 | 10 | 4 |
| Royal Sailor | 110 | 11 | 2 |

Nicht zugeordnete Referenzen:

- Machio: `4459.dat` ×1, `3749.dat` ×4, `3713.dat` ×1, `2343.dat` ×12, `3829c01.dat` ×1.
- Out For the Count: `3749.dat` ×4, `3829c01.dat` ×1.
- Royal Outtaliner: `4459.dat` ×2.
- Royal People Rover: `4459.dat` ×2, `55707b.dat` ×2.
- Royal Sailor: `4459.dat` ×2.

Eingebettete Teilebeschreibungen belegen: 4459 = Pin mit Reibrippen, 3749 = 1L-Achse mit reibungslosem Pin, 2343 = Minifiguren-Kelch. Bei allen drei Royal-Originalen nennt die externe Spielliste zwei 2780 statt der zwei Studio-4459. Das ist ein möglicher Zuordnungshinweis, noch keine verifizierte Transformations-/FieldIndex-Abbildung. Machios zwölf Kelche kommen nicht als 2343 in der externen Original-Teileliste vor: dort liegt offensichtlich mindestens eine Nachbau-/Teileabweichung vor.

Zusätzliche Erkenntnis: 2436 ist im lokalen `teiledaten.json` vorhanden (`ANGLE PLATE 1X2/1X4`), obwohl ältere Projektnotizen es als nicht vorhanden beschrieben. Katalogexistenz und tatsächliche Freischaltung/Verwendbarkeit in der Garage auseinanderhalten; die ältere Aussage nicht ungeprüft übernehmen.

## Externe Vergleichsdaten

Für die sechs oben genannten Original-IDs wurden gezielt öffentliche Enzyklopädie-Teilelisten heruntergeladen:

`.claude/quellen/l2kd-encyclopedia/vehicle_parts/<ID>.json`

Quelle jeweils:
`https://raw.githubusercontent.com/r0levrai/l2kd-encyclopedia/main/data/vehicle_parts/<ID>.json`

Diese enthalten `parts_and_colors` sowie Chassis-/Motor-/Kategorie-Metadaten, **keine Transformationen oder Verbindungen**. Ihre Farbwerte sind teilweise größer als 255; nicht ungeprüft in das Farbbyte eigener Fahrzeuge schreiben.

Weitere Quellen/ältere Bewertung: `.claude/quellen/modelle-steam.md`, `.claude/quellen/README.md`, `.claude/quellen/manifest.json`. Der ältere Steam-Vermerk sagt noch, die tatsächlichen Downloads seien ungeprüft; die vorliegende Übergabe und die neuen Analysen sind der neuere Stand.

## Bisherige Importmöglichkeiten und technische Blockade

Der Nutzer wünscht sechs eigene Garageneinträge. Die Garage liest sie gemeinsam aus `ArtemisVehicle.sav`; sechs beliebig benannte neue SAV-/IO-Dateien im SaveGames-Ordner werden dadurch nicht automatisch zu eigenen Fahrzeugen.

Der bestehende Builder kann bekannte Geometrie und explizite Anschlüsse schreiben. Er ist **kein vollständiger Studio-Konverter**. Es fehlen für diesen Auftrag insbesondere:

1. kalibrierte LDraw-zu-Spiel-Transformationen einschließlich lokaler Teilursprünge;
2. verifizierte Varianten-/Verbundteilauflösung und Farbabbildung;
3. vollständige Anschlüsse und FieldIndex-Werte für viele Sonderteile;
4. die passenden Chassis-/Rad-/Flair-Baugruppen und Fahrer-Sockets;
5. abschließender realer Lade-/Speichertest.

Keine Verbindungen erfinden, nur um die Graph-Prüfung zu bestehen. Keine sechs leeren Chassis als die sechs importierten Modelle ausgeben.

Ein möglicher schneller Weg wäre, bereits verfügbare Originalfahrzeuge im Spiel über Bearbeiten/Ändern als eigene Garagenkopien zu speichern. Das Spiel erzeugt dabei selbst die gültigen Strukturen. Das wäre aber eine Kopie der Originalfahrzeuge, **keine nachgewiesene 1:1-Konvertierung dieser teilweise abweichenden Studio-Nachbauten**. Mit dem Nutzer klar benennen, falls dieser Weg gewählt wird. Ob die Originale tatsächlich in seiner Sammlung verfügbar sind, ist offen.

## Untersuchung lokaler Spielstände/Caches

SaveGames-Verzeichnis:
`%USERPROFILE%\Documents\My Games\Artemis\Saved\SaveGames\`

- `ArtemisVehicle.sav`: eigene Fahrzeuge; beim letzten Lesen freie Slots ab 24. Anzahl und Belegung vor einem Import neu lesen, nicht mit alten Screenshots/pauschal 50 Slots arbeiten.
- `ArtemisDownloadedVehicle.sav`: die zuvor analysierten 16 Community-Modelle; keine Treffer für die sechs Zielkennungen.
- `ArtemisExtraVehicle.sav`: CustomVehicles, bisher keine passenden Modelle gefunden.
- `ArtemisDnaInfo.sav` und `ArtemisDnaLocalCache.sav`: keine entsprechenden Geometriedaten gefunden.
- `ArtemisPlayerInfo.sav`: Referenzen auf alle sechs IDs gefunden, aber keine PartTransforms. Diese Referenzen sind kein vollständiges Fahrzeugmodell und kein bestätigter sichtbarer Sammlungsstatus.
- `ArtemisChubCache.sav`: 51 Cacheeinträge in `Data/CachedVehicles`; jeder Wert hat `Bytes` und `TimeStamp`. `Bytes['_bytes']` ist ein eigenständiger serialisierter Property-Blob, beginnt z. B. mit `ChassisConfig`, also kein neuer GVAS-Header. Die äußere Struktur enthält deshalb keine direkt auslesbaren VehicleName-/PartGraph-Dicts. In den Blobs wurden weder die sechs bekannten IDs noch ihre englischen Namen als ANSI/UTF-16 gefunden. Das ist kein vollständiger semantischer Ausschluss aller denkbaren anders benannten Kopien. Hier nicht behaupten, schon 51 zusätzliche PartGraphs vollständig analysiert zu haben.

## Computer Use und Spielzustand

Letzte Nutzeraussage: **„spiel ist zu“**. Vor einem späteren echten Schreibvorgang frisch prüfen, ob das Spiel weiterhin vollständig geschlossen ist. Den Nutzer nicht ungefragt erneut starten lassen, wenn nur ein vorbereiteter Dateiabgleich nötig ist.

Computer-Use-Skill wurde gelesen:
`C:\Users\Ben\.codex\plugins\cache\openai-bundled\computer-use\26.1023.51421\skills\computer-use\SKILL.md`

Sowie die zugehörigen `docs/guidance.md`, `docs/api.md`, `docs/confirmations.md`.

Für Windows-Automation wird `@oai/sky` über `mcp__node_repl.js` benutzt. Fenster immer frisch aus `sky.list_windows()` auswählen; alte IDs/Koordinaten nicht weiterverwenden.

Damals laufendes Spiel:
`M:\SteamLibrary\steamapps\common\LEGO2KDrive\LEGO2KDrive\Binaries\Win64\LEGO2KDrive-Win64-Shipping.exe`

Nach einmaligem Öffnungsversuch wurde das Spielfenster in der Liste gefunden, aber die Aufnahme schlug auch nach erneuter Bindung fehl:

- `FrameArrived timed out: timed out waiting on channel`
- `window capture timed out: timed out waiting on channel`

Ein Aktivierungsversuch meldete außerdem `user input was detected in this window; call get_window_state before continuing`. Daraufhin wurde nur erneut gelesen. Es wurden keine blinden Spielmenüeingaben vorgenommen.

Die Bitte um Fenstermodus wurde nicht erfüllt, sondern mit „spiel ist zu“ beantwortet. Nicht behaupten, Fenstermodus sei schon ausprobiert oder behoben worden.

## Bestehender Builder-Stand als Grundlage

Vor diesem Auftrag wurden Builder und Projektstand in diesem Chat als Commit `89275e1` auf `origin/main` gepusht. Neue Import-/Analysedateien sind noch nicht committed. Die ältere Freigabe „commit,push“ wurde damit erfüllt; daraus keinen automatischen Auftrag ableiten, die jetzt neu entstandenen Dateien ebenfalls zu pushen.

Siehe `.claude/builder-verbesserungen-2026-10-29.md`:

- `werkzeuge/baugeometrie.py`: 44 registrierte Nummern, volle Quaternionen für bekannte Ober-/Unterseiten; 3823-Maske als unsicher gesperrt.
- `werkzeuge/baue_fahrzeug.py`: `build_vehicle()` im Speicher, `--pruefen`, stabile IDs, explizite Verbindungen, Radmodule, Chassisanbindung.
- `werkzeuge/gvas_rw.py`: Rückleseprüfung, Sicherung und atomarer Austausch, Schutz vor zwischenzeitlich geänderten Quellen/Zielen.
- 19 unveränderte Startchassis in `.claude/basis-chassis.json` (10 Straße, 9 Gelände), nicht sämtliche möglichen Spiel-Chassis.
- Der frühere Download-Korpusvergleich bestätigte 716/716 berechnete Verbindungen im unterstützten Umfang, nicht alle Anschlüsse aller 16 Modelle und erst recht nicht die jetzigen Studio-Dateien.
- Offene Grenzen: keine vollständige Mesh-Kollision und `GarageSaveDataMap` nicht automatisch neu aufgebaut. Technischer UInt16-Indexraum ist kein bestätigtes Garagen-Baulimit; 350 als universelle harte Grenze war noch nicht primär verifiziert.

## Aktuelle Git-/Arbeitsdateien

Zu diesem Importauftrag neu:

- `Download/*.io`
- `werkzeuge/pruefe_studio.py`
- `.claude/tests/test_studio.py`
- `.claude/studio-modelle/**`
- `.claude/quellen/l2kd-encyclopedia/vehicle_parts/*.json`
- diese Übergabe.

Zusätzlich existieren Änderungen/Dateien aus dem Freischalt-Chat, u. a. `.claude/freischalten.py`, `.claude/freischaltung.md`, `.claude/freischaltung/bericht.json`, Diagnosewerkzeuge und eine eigene Übergabe `UEBERGABE-ALLE-BAUTEILE-FREISCHALTEN.md`. Das sind eigenständige Arbeiten; nicht still zurücksetzen oder deren Code ausführen.

## Nachtrag 29.10.2026, 20:50 (Folge-Chat)

- Eingangshashes erneut geprüft: alle sechs unverändert.
- Spiel-EXE statisch durchsucht: keine Strings für lxfml/LDraw/.ldr/BrickLink/Stud.io/ImportVehicle; „Studio“ nur als FMODStudio. Fahrzeuge werden nur aus den festen Slots ArtemisVehicle/ArtemisExtraVehicle/ArtemisDownloadedVehicle geladen. Ein „Reinkopieren“ der .io-Dateien funktioniert damit nicht (kein Spieltest, statischer Befund).
- Nutzer wählte „Originale kopieren“. Vorher gesichert: `_sicherungen/2026-10-29_20-44-44`; Garage vorher: `.claude/studio-modelle/garage-vorher.json` (23 von 50 Plätzen belegt, 0–22).
- Ergebnis laut Nutzer: „keine neuen fahrzeuge in garage“. Save danach weiterhin 23 belegt.
- Die Vehicle-Einträge der sechs Originale in `ArtemisPlayerInfo.sav` (LockRewards) stammen aus dem Freischalt-Chat (in Sicherungen vor 20:23 nicht vorhanden).
- Korrektur 20:55: Der Nutzer zeigte die Hamburghini-Karte ohne großes Schloss und bestätigte „alles funktioniert“; das kleine Stein-Schloss-Symbol steht laut Nutzer für Plusteile, die bereits freigeschaltet sind. Die Fahrzeugfreigabe wirkt also. „Keine neuen Fahrzeuge“ hieß nur: noch keine eigene Kopie gespeichert. Stand 20:52: weiterhin 23 belegt, Spiel lief.

## Sinnvolle Fortsetzung

1. Diese Übergabe und `uebersicht.json` lesen; Eingangshashes kontrollieren. Vorhandene Analysen nicht erneut von Grund auf erstellen.
2. Dem Nutzer ehrlich sagen: Sicherheitsprüfung/Teileanalyse fertig, Garagenimport weiterhin offen.
3. Einen konkreten Weg wählen: verfügbare Originale im Spiel als native Kopien gewinnen oder einen echten Studio-Konverter implementieren. Die Originalkopie nicht als identischen IO-Import verkaufen.
4. Beim Konverter zunächst **ein** Modell in einer separaten Spielstandkopie vollständig kalibrieren. Keine unbestätigten Varianten/Anschlüsse heimlich übernehmen. Erst mit überprüfbarem Ergebnis den echten Import vornehmen.
5. Vor echtem Schreiben: Spiel geschlossen, frischer Save-Snapshot, aktuelle freie Slots, vollständige Sicherung. Nur neue Fahrzeuge hinzufügen. Pfade zu echten SaveGames liegen außerhalb des Projekt-Schreibbereichs; notwendige Sandbox-Eskalation mit dem bereits ausdrücklich autorisierten Import begründen.
6. Danach im Spiel Laden, lose Teile, Chassis/Räder/Fahrer und erneutes Speichern prüfen. Erst nach tatsächlichem Nachweis von erfolgreichem Import sprechen.

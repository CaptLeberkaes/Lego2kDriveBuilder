# Peer-Review der Bauwerkzeuge – 29.10.2026

**Historischer Befund vor der Änderungsfreigabe.** Die anschließenden Korrekturen, aktuelle Datenstände und verbleibenden Grenzen stehen in [builder-verbesserungen-2026-10-29.md](builder-verbesserungen-2026-10-29.md). Die ursprünglichen Befunde und damaligen Zahlen bleiben hier als Ausgangspunkt erhalten.

## Auftrag und Grenzen

Die Werkzeuge auf Logik und Plausibilität prüfen und neue Erkenntnisse aus den heruntergeladenen Modellen ergänzen. Keine Änderungen an gemeinsamen Werkzeugdateien oder Spielständen. Der Shuttle-Versuch bleibt außerhalb dieses Reviews.

Laut Nutzer hat Claude die Logik im Ordner angelegt. Aus den vorhandenen Fahrzeugen wird keine erfolgreiche automatische Bauleistung von Claude abgeleitet. Claude arbeitet während des Reviews parallel; Befunde beziehen sich auf den untersuchten Stand. Code-Hashes und Datenquellen stehen in `modelldaten-review.json`.

## Was geprüft wurde

- `baue_fahrzeug.py`, `geometrie.py`, `anschluesse.py`, `gvas_rw.py`, `tausche_teile.py`, Hilfswerkzeuge und Projektdokumentation.
- Alle 16 heruntergeladenen Fahrzeuge: 3.507 Teile, 375 unterschiedliche Teilenummern, 5.211 gespeicherte Verbindungseinträge.
- Drei Referenzfotos der Lok, ihre Teileliste und ihr Tauschplan.
- Zehn vom Nutzer neu gespeicherte, unveränderte Startchassis, mit ausdrücklicher Zuordnung der Menünamen zu den gespeicherten Fahrzeugnummern.
- Bytegenaues Lesen und Zurückserialisieren beider Fahrzeugdateien im Speicher: erfolgreich. Die Originaldateien wurden nicht geschrieben.
- Zwei Bauversuche ausschließlich im Speicher; die Speicherfunktion wurde für diese Prozesse durch eine Auffangfunktion ersetzt.

Das ist ein Daten- und Code-Review. Korrektes Laden, Fahrverhalten und erneutes Speichern erzeugter Fahrzeuge wurden hier nicht im Spiel getestet. Aussagen in der bestehenden README über frühere Spieltests sind Dokumentation, keine in dieser Sitzung wiederholten Tests.

## Befunde nach Priorität

### P1: Der Bauer kann falsche Verbindungstypen erzeugen

In `baue_fahrzeug.py:252–279` wird die erste Verbindung, deren Typ nicht `Hinge` enthält, als Vorlage für feste Noppenverbindungen verwendet. Das kann auch eine Pin- oder Achsverbindung sein. Anschließend werden Indizes, Felder und Stärke geändert, aber nicht `Type`.

Reproduktion mit je einer Platte 3022 bei z=1000 und einem Stein 3003 bei z=1010, gleicher x/y-Lage:

| Vorlage | Tatsächlich erzeugter Typ bei vier Noppen |
|---|---|
| the cooker | CylindricalConnection, Strength 4 |
| New Vehicle 29 | PrismaticConnection, Strength 4 |

In allen Download-Daten haben diese beiden Verbindungstypen ausschließlich Stärke 1; die gewöhnlichen vier Noppen werden dort als `FixedConnection` gespeichert. Der Fehler wurde im Speicher durch den tatsächlichen Bauer reproduziert.

Empfehlung: Typ ausdrücklich setzen; Vorlagen nach exaktem Enum auswählen. Fehlende Vorlagen mit verständlicher Meldung behandeln.

### P1: Die Prüfung auf lose Teile übersieht ganze lose Baugruppen

`baue_fahrzeug.py:303–308` prüft nur, ob ein Teil irgendeine neu berechnete Verbindung hat. Zwei Steine bei z=1000 und z=1030 bestehen diese Prüfung, obwohl sie keinerlei Verbindung zum Chassis haben. Unbekannte Geometrie wird in `connect()` zudem still übersprungen. Geschrieben wird bereits vor dieser Warnung.

Empfehlung: Vor dem Schreiben den gesamten Graphen prüfen. Jedes normale Karosserieteil muss einen Pfad zu einem Chassisteil besitzen. Rad-Baugruppen brauchen eine gesonderte Regel: In sämtlichen 16 Download-Modellen sind alle normalen Nicht-Rad-Teile vom Chassis aus erreichbar, die Radteile hingegen nicht. Ein pauschaler Test für alle Teile würde gültige Vorlagen ablehnen.

### P1: Der Geometrie-Lerner liefert Kandidaten, keine belegten Anschlussmasken

`geometrie.py:49–59` zählt die gesamte Anschlussfläche des bekannten Nachbarteils zum untersuchten Teil. Eine Verbindung beweist aber nur einen Kontakt innerhalb dieser Fläche. Die gespeicherte Stärke wird nicht als Einschränkung verwendet; Punkte werden ohne Prüfung ihres Rasterabstands gerundet.

Reproduziert an den Downloads:

- Für das 1×1-Teil 87087 werden unter anderem lokale Punkte (-3,0), (3,0) und (2,1) ausgegeben.
- Für das 1×2-Teil 37352 erscheinen (-2,0) und (3,0).
- Für das 1×2-Teil 11211 erscheinen Punkte bis (1,5).

Diese Punkte stammen aus Nachbarflächen und dürfen nicht direkt in `GEOM` übernommen werden. Auch häufige Kandidaten sind dadurch noch nicht bewiesen.

Empfehlung: Pro Beobachtung Teil, Gegenstück, lokale Lage, Anschlussfelder, Verbindungstyp und Stärke speichern. Beispielsweise schränkt ein Kontakt mit Stärke 2 die mögliche Maske ein, statt sämtliche vier Noppen einer angrenzenden 2×2-Platte zu bestätigen. Eindeutige Einzelkontakte und unabhängige Gegenbeispiele gezielt sammeln. Rasterfehler ablehnen statt blind runden.

### P2: Rotationen und Anschlussflächen sind wesentlich eingeschränkter als das Saveformat

Der Bauer unterstützt nur Drehung um z; `yaw_of()` ignoriert Quaternion-x/y und `world_cells()` rundet Sinus und Cosinus auf ganze Zahlen. Für 45° entsteht so keine korrekte Rotation. Gedrehte Chassisteile können trotzdem ohne Zurückweisung in die Noppenberechnung gelangen.

1.263 der 3.507 Download-Teile besitzen Quaternion-x oder -y außerhalb ±0,01. Diese Zahl misst eine Einschränkung des vereinfachten Transformationsmodells, nicht 1.263 Baufehler. Seitenanschlüsse, liegende Teile und Kugel-/Achsverbindungen sind in den Vorlagen tatsächlich vorhanden.

Empfehlung: Kurzfristig unterstützte Rotationen und Einheitsskalierung ausdrücklich validieren. Anschließend Anschlussflächen mit lokalen Positionen, Normalen und Verbindungstypen beschreiben und mit vollständigen Quaternionen transformieren. Für die Lok sind insbesondere 3956 und die liegenden 6143 relevant.

### P2: Radtausch erhält nicht die vollständige Geometrie und Verbindungsstruktur des Spenders

`baue_fahrzeug.py:206–230` verlangt gleiche Teilezahl. Bei der Lageübernahme werden alle Spenderteile auf dieselbe x-/z-Lage gesetzt; nur y-Abstände bleiben erhalten. Anschließend werden die vorhandenen Verbindungen der alten Räder weiterverwendet. Unterschiedliche Anschlussfelder und interne Verbindungen des Spenders werden nicht übernommen.

Die Räder von „the cooker“ haben vier Teile; viele andere Vorlagen haben zwei. Solch ein Tausch wird bereits abgewiesen. Die Annahme „erster Eintrag ist die Felge“ gilt ebenfalls nicht allgemein: Beim Cooker stehen 2654, 4032, 55976, 56145 in dieser Reihenfolge.

Empfehlung: Die komplette Rad-Baugruppe als zusammenhängendes Modul übernehmen, alle relativen Transformationen erhalten und interne Indizes/Verbindungen neu zuordnen. Nicht die Listenposition als Teilefunktion interpretieren.

### P2: Funktionale Baugruppen und Fahrersitz werden pauschal entfernt

Der Bauer behält Chassis und Räder, entfernt alle übrigen Baugruppen und leert `Sockets` sowie `FlairTriggers`. Das ist als enger Karosserie-Neubau verständlich, aber kein allgemeiner Fahrzeug- oder Bootsbauer.

Bei „Explorateur nocturne“ betrifft das unter anderem den Hydro-Propeller, den aktiven Magneten, den Detektor und die Licht-Flairs. Das Boot hat 206 Teile, neun Flair-Auslöser und einen Fahrer-Socket auf Teil 33909. Die Folgen der Entfernung für das Fahren wurden nicht im Spiel getestet.

Empfehlung: Im Bauplan ausdrücklich festlegen, welche Module übernommen, ersetzt oder entfernt werden. Zu übernommenen Modulen gehören deren Teile, Transformationen, Verbindungen, Auslöser und passende Sockets.

### P2: Schreibablauf und Garagenzustand sind nicht gemeinsam abgesichert

`gvas_rw.SaveFile.save()` schreibt direkt in die Zieldatei. Der Bauer hat keine automatische Sicherung, schreibt vor der abschließenden Warnung und behandelt die dokumentierte Garagen-Arbeitskopie nicht. `tausche_teile.py` besitzt dafür bereits eine Teilbehandlung.

Empfehlung: Erst im Speicher validieren, dann ein separates Ergebnis schreiben und wieder einlesen. Beim Ersetzen einer vorhandenen Datei Sicherung und atomaren Austausch vorsehen. Bei vorhandener Arbeitskopie und Ziel-Slot explizit den Zustand prüfen. Der rohe `GarageSaveDataMap`-Inhalt wird vom Bauer nicht passend zum neuen Fahrzeug aktualisiert; die praktische Notwendigkeit dieser Metadaten ist noch zu testen.

## Neue Erkenntnisse aus den Modelldaten

### Gewöhnliche waagerechte Noppenverbindungen sind eine brauchbare Grundlage

Für aufrechte, im 90°-Raster liegende Teile mit vorhandener `GEOM` und Einheitsskalierung wurden 382 Verbindungen vorhergesagt. 381 davon existieren mit denselben Indizes, Feldern und derselben Stärke im gespeicherten Graphen.

Die Abweichung: In „Bulldozest“ verbinden sich Teilindex 225 (3001) und 226 (3823) mit Stärke **6**; der Bauer berechnet **8**. Die bereits notierte Sonderform von 3823 ist noch nicht als Anschlussmaske umgesetzt. Aus dieser einzelnen Beobachtung lässt sich die genaue Maske nicht bestimmen: Innerhalb des angenommenen 4×2-Rasters sind noch 28 Sechsermasken möglich.

Dieser Vergleich bestätigt den begrenzten Standardfall. Er ist kein unabhängiger Qualitätsnachweis für beliebige Modelle, weil die Geometrien teilweise aus denselben Vorlagen abgeleitet wurden.

### Verbindungseinträge sind nicht pauschal genau doppelt

Nach Normalisierung der Endpunktreihenfolge, einschließlich zugehöriger Felder, Typ und Stärke, enthält das Download-Korpus:

- 3.774 Verbindungssätze einmal,
- 297 Verbindungssätze zweimal,
- 281 Verbindungssätze dreimal.

Die Dreifacheinträge treten sowohl innerhalb als auch außerhalb derselben Baugruppe auf. Ein Beispiel außerhalb derselben Baugruppe ist „Anakins Podracer Mk1“, Indizes 163/165, Felder 0/2, CylindricalConnection, Stärke 1.

Die README-Aussage „innerhalb einer Baugruppe doppelt“ beschreibt somit keine allgemeine Regel. Für das Lernen sollen identische Einträge nicht als unabhängige Belege zählen. Die Bedeutung der Wiederholungen beim Schreiben bleibt ungeklärt; sie sollen nicht blind aus bestehenden Baugruppen entfernt werden.

### Einen Chassis-Namen zu kennen bedeutet noch nicht, daran bauen zu können

Der Geometriekatalog umfasst 31 Teilnummern. Von den Downloads sind damit 963 Teileinstanzen und 31 der 375 unterschiedlichen Teilnummern abgedeckt. Die Anschlussstatistik enthält zwar 363 Teilnummern, ist aber keine vollständige geometrische Beschreibung dieser Teile.

Beispiele für die bekannte Geometrie der Chassisteile:

| Modell | Chassisteile mit GEOM / insgesamt |
|---|---|
| Brute Chopper | 4 / 8 |
| Bulldozest | 1 / 8 |
| the cooker | 7 / 44 |
| Explorateur nocturne | 3 / 9 |
| Bat Boat | 0 / 4 |

Bei „Bat Boat“ kann die jetzige Berechnung deshalb keine neue Karosserie direkt an eines seiner Chassisteile anbinden. Sinnvoll wäre zuerst ein verifizierter Katalog der tatsächlich verwendbaren Oberflächen der Startchassis.

### Menüname, ChassisConfig und AssemblyAsset sind getrennte Bezeichnungen

Belegte Beispiele aus den Dateien:

- PoliceTruck_7032_Garage verwendet die Baugruppe OffroadEileen_VC000.
- EcoCar_60200_Garage verwendet StreetTinyTerror_VC000.
- SwampBoat_5866_Garage verwendet WaterFanBoatHydro_VC000.

Menünamen dürfen daraus nicht ohne Bestätigung erfunden werden. `chassis-beobachtet.json` enthält derzeit 18 beobachtete Konfigurationen, davon zehn durch den Nutzer den Menünamen zugeordnet. Die Menge ist kein nachgewiesen vollständiges Body-Shop-Angebot.

## Live-Abgleich mit den neu gespeicherten Startchassis

| Vom Nutzer bestätigter Menüname | Gespeicherter Name | Slot (ab 0) | interne Konfiguration | Teile |
|---|---|---|---|---|
| Alte Schule | Neues Fahrzeug 05 | 5 | FireEngine_10263_Garage | 11 = 3 Chassis + 8 Räder |
| El Dragón | Neues Fahrzeug 06 | 6 | Dragster_6639_Garage | 17 = 9 Chassis + 8 Räder |
| Ende der Straße | Neues Fahrzeug 07 | 7 | EndOfStreet_VC000 | 16 = 8 Chassis + 8 Räder |
| Extremtempo | Neues Fahrzeug 08 | 8 | ExtremeSpeed_VC000 | 23 = 15 Chassis + 8 Räder |
| Gerade und schmal | Neues Fahrzeug 09 | 9 | Sedan_60050_Garage | 11 = 3 Chassis + 8 Räder |
| Lenkstange | Neues Fahrzeug 10 | 10 | TriCycle | 26 = 18 Chassis + 8 Räder |
| Renn-Ass | Neues Fahrzeug 11 | 11 | ClassicCar_10261_Garage | 17 = 9 Chassis + 8 Räder |
| Straßen-Champion | Neues Fahrzeug 12 | 12 | GarageChampionStreet | 16 = 8 Chassis + 8 Räder |
| Süße Mischung | Neues Fahrzeug 13 | 13 | SweetRemix_VC000 | 20 = 12 Chassis + 8 Räder |
| Winziger Schrecken | Neues Fahrzeug 14 | 14 | EcoCar_60200_Garage | 11 = 3 Chassis + 8 Räder |

„Alte Schule“ besteht im Chassis aus einer 2445 und zwei 30157; die vier Rad-Baugruppen heißen 56902_61254_New. Die beiden Chassis-Verbindungen sind jeweils FixedConnection mit Stärke 4 und erscheinen je zweimal. Vollständige, um Spielerkennungen bereinigte Teile- und Anschlussdaten der Startchassis stehen in `basis-chassis.json`. Im letzten erfassten Snapshot waren alle zehn regulär gespeichert.

`basis-zuordnung.json` hält ausschließlich die ausdrücklich vom Nutzer genannten Zuordnungen fest. `erfasse_basis.py` liest einen konsistenten Snapshot des Spielstands in den Speicher, prüft die Fahrzeugnamen und aktualisiert die bereinigten Review-Dateien. Das Skript schreibt ausschließlich in diesen `.claude`-Ordner. Eine vorhandene Garagen-Arbeitskopie wird gesondert ausgewiesen.

Während des Abgleichs war zunächst zusätzlich eine `AncillaryCustomVehicle` mit Name „Neues Fahrzeug 06“, 17 Teilen und Zielslot 6 vorhanden. In einem späteren Snapshot war dieses Fahrzeug regulär in Slot 6 gespeichert und die Ancillary-Eigenschaft nicht mehr vorhanden. Das bestätigt die zusätzliche Arbeitskopie und den beobachteten Zustandswechsel. Es beweist noch nicht das in der README beschriebene Überschreiben externer Änderungen; dafür wäre ein gesonderter kontrollierter Spieltest nötig. Die Datei veränderte sich während der Benutzung durch den Nutzer; getrennte Lesevorgänge sind daher getrennte Snapshots.

## Empfohlene nächste Schritte

1. Verbindungs-Enum und Prüfung auf Chassisanbindung korrigieren; vor dem Schreiben abbrechen, wenn eine nötige Geometrie fehlt.
2. Die unveränderten Startchassis aufnehmen: Menünamen, Grundteile, Anschlussflächen und Rad-Baugruppen getrennt dokumentieren.
3. Erkenntnisse aus Verbindungen als nachvollziehbare Bedingungen mit Quelle und Unsicherheit speichern; keine vollständigen Geometrien aus bloßen Häufigkeiten behaupten.
4. Baupläne um stabile Teile-IDs, relative Baugruppen und Anschlüsse ergänzen. Eine Angabe wie „auf Noppe (2,1) von Teil X“ ist für den Planer verlässlicher als viele frei geratene Weltkoordinaten.
5. Seitliche Anschlüsse und vollständige 3D-Transformationen ergänzen; danach bewährte Baugruppen aus den Downloads als Module übernehmen.
6. Einen kleinen kontrollierten Spieltest je Technik durchführen: laden, lose Teile prüfen, fahren, speichern, erneut einlesen und Änderungen am Graphen vergleichen.

Für weitere Basisaufnahmen: ein unverändertes Fahrzeug je Menüchassis, möglichst `Basis - <Menüname>` benennen. Keine separaten Dateien nötig. Für einen stabilen abschließenden Snapshot Garage verlassen und Spiel schließen. Bestehende Fahrzeuge nicht löschen.

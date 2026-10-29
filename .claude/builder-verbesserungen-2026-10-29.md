# Builder: korrigierter Stand vom 29.10.2026

## Umfang und Herkunft

Der Nutzer hat nach Abschluss von Claudes Arbeit Änderungen an Werkzeugen und Dateien freigegeben. Der Shuttle-Wettbewerb folgt später. Diese Änderung verbessert den gemeinsamen Builder und verarbeitet die zusätzlichen Basis-Chassis. Die vorherigen Befunde bleiben im historischen Peer-Review nachvollziehbar.

Es wurden keine echten Spielstände geschrieben und keine neuen Fahrzeuge im laufenden Spiel angelegt. Spieltests auf Laden, Fahren und erneutes Speichern stehen weiterhin aus.

## Umgesetzt

- `baue_fahrzeug.py` trennt `build_vehicle()` im Speicher vom tatsächlichen Schreiben. Ein Prüfmodus erstellt keine SAV.
- Neue Verbindungen erhalten den ausdrücklich berechneten Typ. Eine zufällige Pin-/Achsverbindung aus der Vorlage kann nicht mehr als feste Noppenverbindung übernommen werden. Eine Vorlage ohne Scharnierverbindung funktioniert ebenfalls.
- Alle normalen Teile müssen vor dem Schreiben einen Pfad zum Chassis besitzen. Die im Korpus separat verankerten Rad-Baugruppen werden ausgenommen. Auch eine untereinander verbundene, aber insgesamt schwebende Gruppe führt zum Abbruch.
- Die neue gemeinsame `baugeometrie.py` transformiert die bekannten Ober-/Unterseiten mit vollständigen Quaternionen. Aufrechte beliebige z-Drehungen und liegende Standardteile werden geometrisch berechnet. Seitenports spezieller Teile werden dadurch nicht automatisch erfunden.
- Zwölf weitere rechteckige Standardgeometrien wurden anhand tatsächlicher lokaler 3D-Kontakte ergänzt. Unbeobachtete Anschlussseiten bleiben `None`. Belege stehen in `geometrie-erweiterung-belege.json`. Danach kamen 21 weitere hinzu, abgeleitet mit `geom_kandidaten.py` (Belege: `geom-kandidaten-belege.json`, Bericht: `sonderteile-und-abdeckung-2026-10-29.md`). Aktuell enthält der Katalog 76 Nummern, dazu die belegte Maske des Kotflügels 98282; die automatische Maske von 3823 bleibt gesperrt, weil ihre genaue Lage unbekannt ist.
- Radtausch übernimmt vollständige Baugruppen auch mit anderer Teilezahl, erhält ihre relativen 3D-Transformationen und kopiert deren interne Verbindungen. Als Anker dient das erste Baugruppenteil. Die tatsächliche Achslage ist im Spiel zu prüfen; `versatz` erlaubt eine ausdrücklich angegebene Korrektur. Externe Verbindungen eines zu ersetzenden Rades werden nicht still verworfen.
- Baugruppen können ausdrücklich behalten werden. Zugehörige Flair-Auslöser und noch gültige Sockets werden neu zugeordnet. Ein neuer Fahrer-Socket ersetzt einen eventuell übernommenen Fahrer-Socket.
- Stabile Teile-IDs und explizite Verbindungen erlauben besondere Anschlüsse. Diese werden strukturell geprüft; der Builder behauptet dafür keine vollständige physikalische Verifikation.
- Eine vorhandene Arbeitskopie reserviert ihren Slot. Ein gleichnamiger Austausch auf diesem Slot wird abgewiesen, bis die Garage verlassen und der Spielstand erneut gelesen wurde.
- `gvas_rw.py` prüft die Serialisierung durch erneutes Einlesen, sichert ein vorhandenes Ziel unter `_sicherungen/geschrieben_.../`, schreibt eine temporäre Datei und ersetzt das Ziel atomar. Geänderte Quellen/Ziele führen zum Abbruch. Das ist eine Prüfung auf zwischenzeitliche Änderungen, keine Prozesssperre gegen ein laufendes Spiel. Das Spiel muss beim echten Austausch weiterhin geschlossen sein.
- Neue nicht-ASCII-FStrings werden eindeutig als UTF-16 geschrieben. Originale rohe Payloads werden beim unveränderten Rundlauf erhalten.
- `geometrie.py` sammelt Kontaktbedingungen einschließlich Quelle, Gegenstück, Feldern und Stärke. Bei höchstens 16 Kandidatenzellen werden mögliche Masken aufgezählt. Widersprüche liefern keine bestätigten Zellen. Identische Mehrfacheinträge werden je Fahrzeug nur einmal gewertet.
- `anschluesse.py` verwechselt eine lokale Unterseite gedrehter Teile nicht mehr anhand von Welt-z mit einer anderen Anschlussseite. Unbekannte Felder bleiben unzugeordnet; die Tabelle ist kein zusätzlicher Geometriebeweis.
- `tausche_teile.py` prüft Indizes, Farben, Transformationen, doppelte Tauschziele und vorhandene Verbindungen. Arbeitskopien werden über ihren Slot erkannt. Der gemeinsame sichere Schreibablauf gilt auch hier.

## Nutzung

Die bisherigen drei Positionsargumente bleiben erhalten:

```powershell
python werkzeuge/baue_fahrzeug.py quelle.sav ergebnis.sav plan.json --pruefen --bericht .claude/pruefbericht.json
```

Ohne `--pruefen` wird die Zieldatei nach bestandenen Prüfungen geschrieben. Eine vorhandene Zieldatei wird vorher gesichert. Vor dem Schreiben in den echten Spielstand das Spiel vollständig schließen.

Erweiterte Teiledefinition:

```json
{
  "id": "kessel",
  "teil": 3062,
  "farbe": 38,
  "pos": [0, 0, 40],
  "rot": [0, 0.7071067812, 0, 0.7071067812]
}
```

`rot` und `dreh` sind Alternativen. Eine Teile-ID ist optional; ohne ID gilt `teil:0`, `teil:1`, usw. `chassis:0` bezeichnet das erste übernommene Chassisteil; `rad:fl:0` das erste Teil der Rad-Baugruppe fl. IDs sind gegenüber automatisch verschobenen Gesamtindizes zu bevorzugen.

Beispiel einer ausdrücklich vorgegebenen Verbindung:

```json
{"a": "chassis:0", "b": "kessel", "fa": 1, "fb": 1, "noppen": 1, "typ": "HingeConnection"}
```

Diese Werte sind nur ein Syntaxbeispiel und kein belegter Anschluss für jede beliebige Vorlage. Eine explizite Verbindung ersetzt die automatisch berechneten Verbindungen desselben Teilepaars. Mehrere explizite Kontakte dieses Paars bleiben möglich. Bekannte Typen: HingeConnection, FixedConnection, CylindricalConnection, PrismaticConnection, BallConnection. Die derzeit belegten Stärkeregeln werden geprüft.

Weitere Optionen:

```json
{
  "behalten": ["flairs", "baugruppen"],
  "radtausch": {"fl": {"fahrzeug": "the cooker", "versatz": [0, 0, 0]}},
  "fahrer": {"teil": "sitz", "pos": [0, 0, 10], "dreh": [0, 0, 0]}
}
```

Statt der Kategorien in `behalten` kann ein genauer AssemblyAsset-Pfad oder dessen Assetname angegeben werden. Unbekannte Auswahlwerte werden abgewiesen. Behaltene Module müssen weiterhin mit dem Chassis verbunden sein. Die Rad-Spenderquelle ist standardmäßig dieselbe Fahrzeugquelle wie die Vorlage; für andere Quellen kann `datei` angegeben werden. `felgen` färbt die lackierbaren Radteile; Teile mit fester Farbe 255 bleiben erhalten. Beim Fahrer ist `dreh` ein Rotator in der Reihenfolge Pitch, Yaw, Roll.

## Abgleich und Tests

```powershell
python -m unittest discover -s .claude/tests -v
python .claude/erfasse_basis.py
python werkzeuge/geometrie.py heruntergeladen.sav --teile 87087 3823 --json .claude/bedingungen.json
```

Der Offline-Testkorpus verwendet bereinigte Basisdaten und temporäre, künstliche SAV-Dateien mit einer erfundenen Testkennung. Die echten Spielerkennungen sind nicht Bestandteil der Tests.

Abschluss: **20 Regressionstests bestanden.** Zusätzlich wurde aus dem echten eigenen Spielstand eine Anschlussprobe mit 14 Teilen und sieben Verbindungen ausschließlich in eine temporäre Ergebnisdatei gebaut. Beide Leser konnten das Ergebnis prüfen; der SHA-256-Wert des echten Spielstands blieb unverändert. Die temporäre Datei wurde anschließend entfernt. Zusammenfassung: `validierung-builder.json`.

Im Download-Korpus der 16 Fahrzeuge findet der erweiterte automatische Geometriekern **716 Verbindungen**, die alle mit denselben Teileindizes, FieldIndex-Werten und derselben Stärke gespeichert sind. Der vorherige Zwischenstand ohne die zwölf neuen Standardteile fand 498/498. Diese Zahlen gelten nur für den unterstützten Geometrieumfang und sind kein unabhängiger Nachweis für alle Bauweisen: Ein Teil der Geometrien wurde aus eben diesem Korpus gewonnen.

Alle **19 gespeicherten Startchassis** konnten im Speicher als neue Basis aufgebaut und wieder bytegenau serialisiert werden. Das beweist die Struktur des erzeugten Speicherformats, nicht das spätere Verhalten im Spiel. Ergebnisse stehen in `validierung-korpus.json`.

Die Download- und eigenen Fahrzeugdateien bleiben beim unveränderten Lese-/Schreibrundlauf bytegleich. Die echten Dateien wurden dafür nicht überschrieben.

## Daten und offene Grenzen

- `basis-zuordnung.json`: durch Nutzerangaben bestätigte Menü-/Fahrzeugnummern.
- `basis-chassis.json`: 10 Straßen- und 9 Gelände-Startchassis mit Teilen, Transformationen, Baugruppen und Verbindungen; ohne Spielerkennungen.
- `chassis-beobachtet.json`: zusätzlich aus Vorlagen beobachtete Konfigurationen. Beobachtet bedeutet nicht vollständig geometrisch unterstützt oder vollständig im Body Shop verfügbar.
- Metadaten der verlinkten Enzyklopädie werden beim Erfassen anhand der exakten internen Chassis-ID beigefügt. Ihre Kategorien und Motorvorgaben werden nicht mit der lokalen Geometrie oder dem Freischaltstatus des Nutzers gleichgesetzt.
- `GarageSaveDataMap` wird noch nicht strukturell um neue Einträge/Bounds ergänzt. Das Prüfprotokoll weist auf diese ungetestete Grenze hin.
- Keine vollständige Mesh-Kollisionsprüfung und keine automatische Ableitung sämtlicher Clip-, Pin-, Achs- oder Kugelanschlüsse. Ein bestandener Graph-Test beweist noch keine vollständige physische Baubarkeit.
- Boots-Basischassis wurden noch nicht als vollständige eigene Menüreihe aufgenommen.

## Zusätzliche Quellen

Die [L2KD Encyclopedia](https://r0levrai.github.io/l2kd-encyclopedia/) ist die nützlichere zusätzliche Quelle für spielbezogene IDs und Metadaten. Ihre öffentlichen Daten enthalten 775 Chassis- und 327 Rad-Datensätze; diese Mengen sind keine Liste auswählbarer Startchassis. Der geprüfte 3D-Bereich enthält einen UE-zu-LDraw-Konverter und eine einzelne LDraw-Fahrzeugdatei. Der Konverter bestätigt den inversen Einheitenfaktor 4/5, liefert aber keinen vollständigen FieldIndex-/Anschlusskatalog. Er wurde nicht ausgeführt oder in den Builder importiert.

Der [Builder von bhushan6](https://github.com/bhushan6/lego-builder) erzeugt sieben einfache Rechteckformen aus Quadern und Zylindern. Sein Rasterabstand ist ebenfalls 25, seine Standardsteinhöhe aber 25×2/1,5 ≈ 33,33. Er enthält in den geprüften Dateien keine Spiel-Teilenummern oder FieldIndex-Daten. Er ist als Anregung für einen späteren Editor/Platzierungscursor nützlich; seine Geometrie ist keine unverändert übernehmbare 2K-Drive-Teiledatenbank.

Gezielt gelesene öffentliche Quelldateien und Metadaten-Snapshots liegen in `quellen/`. Fremdcode wurde weder ausgeführt noch als Laufzeitabhängigkeit eingebaut. Herkunft und Dateihashes stehen dort im Quellenmanifest.

# Teilewissen und allgemeine Anschlusslogik

Stand: 30.10.2026. Umsetzung nach der Analyse in `../analyse-2026-10-30/analyse.md`.

## Referenzen und Herkunft

Der Nutzer hat in diesem Chat bestätigt, dass die Fahrzeuge in der Spielgarage als Teile- und Bautechnikreferenzen dienen. Ausschließlich das KI-gebaute Spaceshuttle wird ausgeschlossen. Dessen gespeicherter Name ist **Shuttle Rover** (`baupläne/raketen_shuttle.json`). Die vorhandene Emerald wurde vom Nutzer im Spiel von Hand verbessert und ist ebenfalls eine Referenz. Ihre erfolgreiche Reproduktion wird nicht als ursprüngliche automatische Bauleistung ausgegeben.

Der Ausschluss steht zentral in `werkzeuge/anschluesse.py → REFERENZ_AUSSCHLUESSE` und gilt auch für den bestehenden Rechteck-Lerner, die Anschlussstatistik, `geometrie.py` und den Sonderteile-Katalog. Ein bloß ähnlich benanntes Fahrzeug wie Space Rover Explorer wird nicht ausgeschlossen.

## Was umgesetzt ist

- `werkzeuge/teilewissen.py` erfasst Design-IDs, Anschlussfelder, Typ, Stärke, individuelle Skalierungen und **relative** 3D-Lagen aus gespeicherten Kontakten. Farben und globale Weltpositionen sind keine Bedingungen für die Wiederverwendung.
- Graphen werden für die Wissensbasis dedupliziert. Zusätzliche Fundorte bleiben mit Dateihash, Liste und Fahrzeugname erhalten. Spielerkennungen werden nicht exportiert.
- Die Bibliothek enthält aktuell **130 Referenzgraphen, 1.075 beobachtete Teilenummern und 24.173 unterschiedliche Kontaktlagen**, verteilt über 88 Quelldateipfade. Zwei Shuttle-Graphen sind im Quellenindex als ausgeschlossen markiert und liefern keine Lernbelege.
- Die vorhandenen 76 GEOM-Einträge samt Masken bleiben erhalten. Insbesondere wurde die belegte Kotflügelmaske 98282 weder ersetzt noch neu geraten.
- Der Builder ergänzt passende beobachtete Paarlagen. Stimmen beide Felder bereits mit bekannten Standardflächen überein, hat die vorhandene Geometrieberechnung Vorrang. Widersprüchliche Typen/Stärken für dasselbe Feldpaar werden nicht automatisch gewählt.
- Ein Teil kann über einen benannten Anker und die ID einer Kontaktvorlage platziert werden. Gemeinsame beliebige 3D-Drehung und Verschiebung der Konstruktion bleiben dabei erhalten. Vorwärtsreferenzen werden aufgelöst; Zyklen, unbekannte Anker, falsche Teilenummern und abweichende Skalierungen führen zum Abbruch.
- Explizite Kanten werden im Prüfbericht als `geometrisch`, `beobachtete_paarlage` oder `ungeprueft` gekennzeichnet. Widersprüche zu bekannten Standardflächen führen zum Abbruch. Unbekannte manuelle Ports bleiben ausdrücklich ungeprüft.
- Identische massive Standardsteine mit gleicher Lage und Skalierung werden als sichere Überlagerung erkannt. Dies ersetzt keine allgemeine Mesh-Kollisionsprüfung.
- Der Rechteck-Lerner prüft jetzt den gespeicherten Verbindungstyp und das Feld des Partners. Ausschließlich schiefe Kontakte bestätigen keine vollständige rechteckige Anschlussmaske; ein leerer Gegentest gilt nicht mehr als bestanden.
- Im Sonderteile-Katalog bleibt die Nutzbarkeit eines vorhandenen Downloads unabhängig von der Cache-/Download-Reihenfolge. Zusätzliche Fundorte werden erhalten, ohne identische Graphen doppelt zu zählen.
- Die Emerald-Vorschau verwendet lokale Hüllkörper und die aktuelle Plantransformation. Änderungen von Position oder Quaternion bewegen die Vorschau tatsächlich. Die kalibrierten Hüllkörper liegen separat in `../emerald-express/huellkoerper.json`; sie sind grobe Darstellungen, keine Mesh- oder Anschlussgeometrien.

## Nutzung

Bestehende Pläne funktionieren weiterhin. Der Builder verwendet standardmäßig `bibliothek.json`, sofern sie vorhanden ist. Mit `"teilewissen": false` lässt sie sich pro Bauplan abschalten; alternativ kann ein Bibliothekspfad angegeben werden.

Alle folgenden Befehle werden im Projektverzeichnis ausgeführt. Sie verändern keine SAV-Dateien:

```powershell
python werkzeuge/teilewissen.py erfassen --mit-sicherungen
python werkzeuge/teilewissen.py suchen 61252 --partner 2540
python -m unittest discover -s .claude/tests -v
python .claude/teilewissen/validiere.py
```

Die Suche unterscheidet Katalogexistenz, Alias-Kandidaten und Beobachtungen. Sie behauptet weder eine Freischaltung noch die geometrische Gleichheit unbestätigter Varianten.

Beispiel für eine Teiledefinition innerhalb eines vollständigen Bauplans, Anker `griff` ist ein bereits definiertes Teil 2540:

```json
{
  "id": "clip_original",
  "teil": 61252,
  "farbe": 11,
  "anschluss": {
    "an": "griff",
    "vorlage": "fa0007be0701dcc75c301e09"
  }
}
```

Die Kontaktvorlage stammt aus **Space Rover Explorer**: 61252 Feld 2 ↔ 2540 Feld 4, CylindricalConnection. Sie legt eine beobachtete relative Lage fest. Ein Clip wird dadurch nicht in beliebigen unbeobachteten Gelenkstellungen automatisch als passend angenommen. Die Vorlagen-ID ist ein Inhaltsfingerprint und kann bei geänderten Quelldaten abweichen; sie muss aus der aktuellen Suche stammen.

`anschluss` ersetzt die Angaben `pos`, `rot` und `dreh`; konkurrierende Lagen werden abgewiesen. Anker können andere normale Teile, Chassisteile oder vor dem Oberbau übernommene Module sein. Radanker stehen in diesem Aufbauablauf nicht zur Verfügung. Die Räder waren laut Nutzer nicht Gegenstand dieser Verbesserung.

## Nachweise und Grenzen

**63 Tests bestanden.** Darunter sind räumliche Invarianz und Quaternion-Vorzeichen, kontaktbasierte Platzierung durch den echten Builder, Quellenalternativen, Shuttle-Ausschluss, widersprüchliche Kontaktbelege, sichere Überlagerungen, falsche Verbindungstypen, schiefe Kontakte und die reagierende Vorschau. Die vorhandenen Tests einschließlich der Kotflügelmaske bleiben erfolgreich.

Der bestehende Rechteck-Lerner meldet **66 von 66** vorhandenen Einträgen ohne Konflikt. Seine Gegenprüfung liegt in `geom-gegenpruefung.json`.

Bei 20 Referenzfahrzeugen wurde jeweils sämtliche Paarbeleg-Evidenz mit derselben ChassisConfig wie das Testfahrzeug aus der Bibliothek entfernt. Ergebnis: **554 zusätzliche korrekt vorhergesagte Kontakte, 0 abweichende zusätzliche Kontakte**. Die vorherige GEOM wurde dabei nicht neu trainiert; dieser Test bewertet ausschließlich die neue Wiederverwendung der Paarlagen. Auswahl, ausgeschlossene Graphenzahlen und Einzelresultate stehen in `validierung.json`. Das ist ein Testausschnitt, kein universeller Fehlerfreiheitsnachweis.

Die Emerald wurde ausschließlich im Speicher aufgebaut. Werden ihre 22 expliziten Kanten aus einer Testkopie des Plans entfernt, erzeugt der Builder trotzdem alle **56 rohen / 54 unterschiedlichen** gespeicherten Verbindungen. Die 51 Teilepositionen passen zur Nutzerreferenz. Das ist bewusst ein Reproduktionsnachweis, kein unabhängiger Generalisierungstest. Ergebnis: `emerald-ohne-manuelle-kanten.json`.

`anwendungsproben.json` dokumentiert außerdem drei echte Bibliotheksplatzierungen nach gemeinsamer räumlicher Drehung und Verschiebung: Original-Clip an Griff sowie Kesselsteine an beiden belegten Winkelfeldern.

Alle aktuellen und archivierten SAV-Quellen blieben bei der Validierung per SHA-256 unverändert. Der Builder wurde nur mit `--pruefen` beziehungsweise direkt im Speicher aufgerufen. Es wurde kein neuer Spieltest durchgeführt.

Weiter offen bleiben vollständige Port-/Maskenableitung für weitere Teile, allgemeine Materialkollisionen, unbestätigte Varianten und eine automatische Rekonstruktion unbekannter Anleitungen. Die Paarbibliothek überbrückt vorhandenes Wissen gezielt, ohne eine vollständige Geometrie aller 1.075 Teilenummern zu behaupten.

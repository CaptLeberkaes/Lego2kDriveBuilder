# ASTRA II Forward Carrier – Modell 2

Stand: 30.10.2026. Zweiter eigenständiger Bauplan als Variante des ersten ASTRA-Entwurfs. Nutzerwunsch: **Rakete samt Shuttle gemeinsam waagerecht in Fahrtrichtung**, einschließlich beider Booster. Die Raketenspitzen und die Shuttle-Nase zeigen nach +X. Modell 1 bleibt erhalten und wurde nicht geändert.

## Ergebnis und Dateien

- [Bauplan](../../../baupläne/astra_ii_forward_carrier.json)
- [Vorschau mit vier Ansichten](../../../baupläne/astra_ii_forward_carrier_vorschau.html)
- [PNG-Vorschau](../../../baupläne/astra_ii_forward_carrier_vorschau.png)
- [Prüfbericht](pruefbericht.md)
- `entwurf.py`: eigener Aufbau für die liegende Variante; liest das eigene Orbiter-Design aus Modell 1, führt dessen Generator nicht aus.
- `validiere.py`: Kontakt- und Quellenprüfung, Ausrichtungsprüfung für alle vier Flugkörper, Unverändertheit von Modell 1, SAVs, Chassis und anderen Fahrzeugen.
- `vorschau.py`: tatsächliche Transformationen aus dem im Speicher gebauten Graphen, vereinfachte lokale Körper und räumliche Prüfung.
- `gebauter-graph.json`, `builder-pruefung.json`, `kontaktpruefung.json`, `raumpruefung.json`, `validierung.json`: bereinigte Prüfdaten ohne Spielerkennungen.
- `modell-1-ausgangshashes.json`: Ausgangshashes aller ursprünglichen Modell-1-Dateien einschließlich Plan, HTML und PNG.
- `teileliste.md`, `teile-und-verfuegbarkeit.json`: konkrete Design-IDs mit getrennten Katalog-, Referenz- und Freigabeeintragszuständen.

## Konstruktion

Das vorhandene PoliceTruck-/Eileen-Chassis und die vier Radbaugruppen kommen unverändert aus dem aktuellen Brute Chopper. Die Plattform erhält ein längeres hinteres Transportdeck. Der Tank liegt längs in der Mitte, die Booster liegen weiter außen. Ein echter 3956-Winkel trägt den Tank über eine beobachtete 6143-Paarlage. Die Booster verwenden belegte Seitennoppen-/Rundplattenkontakte an ihren hinteren Enden.

Der gesamte Orbiter aus Modell 1 wird starr in die neue Lage gedreht: Nase nach +X, Oberseite nach +Z. Vier senkrechte Stützen in den Lücken zwischen Tank und Boostern tragen zwei neue Querbrücken. Kleine Zwischenplatten verbinden diese mit den bestehenden Flügelholmen. So werden die ehemaligen aufrechten Träger durch eine neue horizontal geeignete Halterung ersetzt. Der Sitz wandert in einen seitlichen hinteren Bedienpod.

Die Flugkörper bleiben ein verbundenes Fahrzeug. Es gibt keine Startanimation und keine Trennfunktion. Das eigene Micro-Shuttle mit zwei dargestellten Düsen und schlankem Tank bleibt eine stilisierte Konstruktion, keine maßstäbliche NASA-Replik.

## Reproduktion, ausschließlich offline

```powershell
python .claude/wettbewerb-shuttle/modell-2/entwurf.py
python .claude/wettbewerb-shuttle/modell-2/validiere.py
python -m unittest discover -s .claude/tests -q
```

Die Skripte schreiben keine SAV-Datei, auch keine SAV-Kopie. Modell-1-Dateien und gemeinsame Werkzeuge werden nicht verändert. Ein späterer Live-Einbau erfordert geschlossenes Spiel und eine geklärte Zielbelegung.

Diese KI-Konstruktion und ihre selbst erzeugten Kontakte sind kein unabhängiger Lernbeleg. Quellen sind die aktuelle Teilewissen-Bibliothek, die bestehenden GEOM-Belege, aktuelle lokale SAVs und das eigene Modell 1. Der alte Shuttle-Rover-Bauplan wird weiterhin nicht verwendet. Für die Sichtkörper des 3956-Winkels werden die bereits kalibrierten lokalen Hüllen aus dem Emerald-Geometriedossier wiederverwendet; dies ist keine Änderung an Emerald.

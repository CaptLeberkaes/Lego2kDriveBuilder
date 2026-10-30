# ASTRA Launch Crawler

Eigenständiger KI-Entwurf vom 30.10.2026 für den lokalen Shuttle-Wettbewerb. Reviewbares Offline-Ergebnis, kein Spieltest. Diese Konstruktion ist kein unabhängiger Lernbeleg für ihre eigenen Anschlüsse.

## Entwurf und Annahmen

- Mangels genauer Foto- oder Maßvorlage: aufrechter Startstapel auf einer fahrbaren Plattform. Orange Außentank, zwei weiße Booster mit schwarzen Ringen, weißer Orbiter mit Deltaflügeln, dunklen Cockpitfenstern, Nutzlastraum und vorstehendem Leitwerk.
- Kompakte, eigene Shuttle-Interpretation; keine maßstäbliche NASA-Replik. Der Orbiter hat zwei kleine dargestellte Düsen. Die Flügelspannweite beträgt ungefähr acht Noppen, der Orbiter ist ungefähr zwölf Noppen lang. Der Tank ist mit zwei Noppen Durchmesser bewusst schlank.
- Feste Basis: PoliceTruck_7032_Garage / Menüfamilie Eileen, aus dem aktuell heruntergeladenen **Brute Chopper**. Ausschließlich dessen unverändertes Chassis und vier vollständige Radbaugruppen werden übernommen. Dessen Oberbau wird nicht übernommen. Die archivierte Startbasis „Neues Fahrzeug 18“ existiert heute nicht mehr unter diesem Namen; deshalb ist sie keine aktuelle Spenderadresse.
- Plattform in Grau mit gelb-schwarzer Randmarkierung. Bedienersitz hinten auf einer angehobenen Stufe; Sitz und Fahrer-Socket vorhanden, Avatarposition und Blickrichtung im Spiel noch offen.
- Keine Trennung oder Startanimation: Alle Komponenten sind an derselben fahrbaren Basis befestigt. Keine Flammen, weil es ein transportierter Startstapel ist.

Der alte Bauplan `raketen_shuttle.json` wurde für diesen Entwurf nicht gelesen und nicht kopiert. `Shuttle Rover` bleibt in der gemeinsamen Wissensbibliothek ausgeschlossen. Emerald wurde ausschließlich zum Unverändertheitsvergleich gelesen; ihr Oberbau ist keine Vorlage dieses Entwurfs.

## Dateien

- [Bauplan](../../baupläne/astra_launch_crawler.json)
- [HTML-Vorschau mit vier Ansichten und Drahtansicht](../../baupläne/astra_launch_crawler_vorschau.html)
- [PNG-Vorschau](../../baupläne/astra_launch_crawler_vorschau.png)
- [Prüfbericht](pruefbericht.md)
- [Teileauswahl und lokale Freigabeeinträge](teileliste.md)
- `entwurf.py`: deterministische Konstruktion und reiner Speicheraufbau.
- `vorschau.py`: lokale Körper, tatsächliche Graphtransformationen, Vorschau und räumliche Prüfung.
- `validiere.py`: alle Kontakte klassifizieren, Quellen prüfen, unveränderte Fahrzeuge/Basis kontrollieren, SAV-Hashes vergleichen, Serialisierung und reagierende Vorschau prüfen.
- `gebauter-graph.json`: bereinigtes Ergebnis ohne Spielerkennungen.
- `kontaktpruefung.json`: alle Kanten, Paarlagen und zugehörigen Referenzgraphen/Dateihashes.
- `raumpruefung.json`: Hüllkörperdefinitionen, Ausdehnung und Kollisionsergebnisse.
- `validierung.json`, `sicherheit.json`: Reproduktions- und Sicherheitsnachweise.
- `recherche.py`: nur lesende Teile-/Kontaktrecherche; keine Import- oder Freischaltaktion.

## Reproduktion im Projektverzeichnis

```powershell
python .claude/wettbewerb-shuttle/entwurf.py
python .claude/wettbewerb-shuttle/validiere.py
python -m unittest discover -s .claude/tests -v
```

Diese Aufrufe erzeugen keine SAV-Datei. `entwurf.py` und `validiere.py` lesen die aktuellen lokalen Quellen. Der Prüfslot ist nur eine interne Platzwahl im Speicher, keine vereinbarte Live-Zielbelegung. Bibliothek, Builder und Katalog bleiben unverändert.

## Quellen und Kenntnisgrenzen

Die Spezifikation stammt aus dem aktuellen Auftrag. Verwendet wurden `README.md`, `.claude/teilewissen/README.md`, `.claude/builder-verbesserungen-2026-10-29.md`, `.claude/pruefregeln-offene-grenzen.md`, `.claude/freischaltung.md`, `teiledaten.json`, die aktuelle Teilewissen-Bibliothek und aktuelle lokale SAVs. Keine neue Webrecherche und kein externer Shuttle-Entwurf wurden als Konstruktion übernommen. Im Teilekatalog hinterlegte externe Namen wurden als vorhandene Projektquellen verwendet, nicht erneut online verifiziert.

Die genaue Freischaltung im Garagenmenü, vollständige Spielmesh-Kollisionen, Lenkeinschlag, Federweg, Schwerpunkt/Fahrverhalten, Avatar, maximale erlaubte Abmessungen und Wettbewerbsregeln wurden nicht im Spiel geprüft. Ein späterer Live-Einbau erfordert geschlossenes Spiel und eine geklärte Zielbelegung. Keine echte SAV überschreiben und insbesondere Emerald oder fremde Einreichungen nicht als Ziel verwenden.

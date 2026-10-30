# ASTRA Launch Crawler – Prüfbericht

Stand: 30.10.2026. **Reviewbarer, unabhängig konstruierter Offline-Bauplan; nicht im Spiel getestet.**

## Ergebnis

| Prüfung | Ergebnis |
|---|---|
| Teile | 96 neu, 112 einschließlich festem Chassis und Rädern |
| Verbindungen | 124 rohe Einträge: 18 unveränderte Basiskontakte, 84 geometrische Oberbaukontakte, 22 beobachtete Paarlagen |
| Chassispfad | Alle neuen Teile erreichbar; keine lose Gruppe |
| Manuell behauptete / ungeprüfte Anschlüsse | 0 / 0 |
| Basisübernahme | Alle 16 Chassis-/Radteile in Design, Farbe und Transformation bytegleich zum aktuellen Brute Chopper |
| Lokale Freigabelisten | Für jede neue Design-ID Eintrag in beiden aktuellen LockRewards-Listen; manuelle Auswahl im Spiel ungetestet |
| Grobe Raumprüfung | 0 Überschneidungen in den verwendeten vereinfachten konvexen Körpern |
| Größe der Vorschaukörper | ca. 305 × 200 × 479 Einheiten einschließlich Rädern; ca. 12,2 × 8 × 19,2 Noppen |
| Serialisierung | Im Speicher erzeugt, erneut gelesen, bytegleich rückserialisiert |
| Vorschau | Tatsächliche gebaute Positionen/Quaternionen; Bewegung eines Sonderteils verändert SVG nachweislich |
| Andere Fahrzeuge | Alle 49 Nicht-Zielplätze im Speicher bytegleich, einschließlich Emerald auf Index 45 |
| Echte Dateien | Keine SAV geschrieben; alle 11 aktuellen SAV-Dateien während der Abschlussvalidierung hashgleich |
| Regressionen | 63 bestehende Tests bestanden, einschließlich belegter Kotflügelmaske |

Die Prüfauswahl des Builders war Index 46 (nullbasiert). Dieser Slot wurde nur im Speicher benutzt und ist ausdrücklich **keine vereinbarte Live-Zielbelegung**.

## Teile und Anschlüsse

Der Tank verwendet echte 6143-Rundzylinder und die Kegelspitze 3942. Die schlanken Booster bestehen aus 3062-Rundsteinen und der konkret belegten Variante 59900. Keine geometrische Gleichsetzung mit 4589 wurde unterstellt. Die Deltaflügel sind die echten Teile 54383/54384. Zwei separate Querholme 3710 halten jeden Flügel an zwei räumlich getrennten beobachteten Ein-Noppen-Kontakten. Die kleine Düsenfassung verwendet 87087 mit dem belegten seitlichen Rundplattenkontakt 6141. Zwei 11211-Seitennoppenhalter und 3023-Adapter tragen den hochkant gedrehten Orbiter.

Alle übernommenen Beobachtungen werden mit ihrer relativen Lage gemeinsam starr transformiert. Es werden weder individuelle Skalierungen noch neue Gelenkstellungen geraten. Die 22 Paarlagenkontakte sind Wiederverwendungen vorhandener Beobachtungen, keine unabhängig bestätigten neuen Spielkontakte. Alle Belege samt Referenznamen, Graphfingerprints und Dateihashes stehen in `kontaktpruefung.json`; ausgeschlossene Shuttle-Rover-Graphen liefern keine davon.

Katalogexistenz, Referenzbeobachtung, Eintrag in lokalen Freigabelisten, Anschlussnachweis und manuelle Wählbarkeit sind in `teile-und-verfuegbarkeit.json` getrennt. Die vorhandenen Freigabeeinträge sind insbesondere kein Nachweis einer Wettbewerbserlaubnis oder einer regulär erworbenen Berechtigung.

## Räumliche und visuelle Bewertung

Die vier Vorschauansichten zeigen einen aufrechten Shuttle-Stapel mit orangefarbenem Tank, zwei weißen Boostern, weißen Deltaflügeln und schwarzer Cockpitzone. Die eigene Konstruktion verwendet ein vorhandenes Radchassis und einen selbst entworfenen Oberbau. Der aufrechte Aufbau und die Transportplattform sind die gewählte gestalterische Annahme. Der Entwurf ist eine kompakte Shuttle-Interpretation mit zwei kleinen Düsen und einem relativ schlanken Tank, keine maßstäbliche Replik.

Die Prüfung sucht nach AABB-Überlappungen und kontrolliert Kandidaten anschließend mit dem Separating-Axis-Test an konvexen Körpern. Normale Steine und Platten verwenden ihre lokalen GEOM-Maße. Rundteile, Keile, Sitz, Reifen und einige native Basisteile haben ausdrücklich vereinfachte lokale Sichtkörper. Sie werden mit den tatsächlich serialisierten Quaternionen und Positionen transformiert. Der anfängliche Konflikt von Heckstufe, Tankpodest und Sitz wurde durch Höhenversatz und verkleinerten Tanksockel beseitigt. Kein Kollisionsfehler wurde durch eine manuell erzwungene Graphkante kaschiert.

Die abgeleitete Reifenhülle lässt im statischen Vorderachsbereich ungefähr 3,75 Einheiten Abstand bis zur unteren Deckplatte. Das ist ein knappes Maß aus der vereinfachten Darstellung; Lenkeinschlag, Federung und tatsächliche Spielmesh-Oberflächen bleiben offen. Interne Überschneidungen der unverändert übernommenen Chassis-/Radbaugruppen werden nicht als Fehler des neuen Oberbaus bewertet.

## Offene Punkte vor einem Spiel- oder Wettbewerbseinsatz

- Vollständige Mesh-Geometrien einschließlich Hohlräumen, Studs, Clips und Spezialteil-Unterseiten liegen nicht für diese Prüfung vor. Null Hüllkörpertreffer ist kein universeller Nachweis physischer Baubarkeit.
- Der breite Micro-Orbiter ist seitlich auf zwei Haltern befestigt. Hebelwirkung, Fahrstabilität und Schwerpunkt des hohen Aufbaus sind nicht dynamisch getestet.
- Sitz, Fahrer-Socket und leere Flair-Liste werden erzeugt; Blickrichtung, Avatar-Freiraum und Darstellung müssen im Spiel geprüft werden.
- Laden, Speichern, Fahren und die vom Spiel neu berechneten Verbindungen wurden nicht getestet. Der Builder lässt `GarageSaveDataMap` unverändert; Wirkung auf Garagen-Bounds ist offen.
- Konkrete Wettbewerbsregeln und erlaubte Abmessungen lagen nicht vor. 112 Gesamtteile liegen unter dem im Projekt dokumentierten vorsichtigen Planungsbudget von 350; eine universelle harte Spielgrenze wird daraus nicht behauptet.
- Für Live-Einbau zuerst Zielbelegung klären und Spiel schließen. Dieser Auftrag hat keine echte Einreichung, keinen Spielstandtausch und keinen Upload ausgeführt.

## Nachvollziehen

`entwurf.py` erzeugt den Bauplan. `validiere.py` reproduziert die Kontaktklassifizierung, Quellenprüfung, bytegleichen anderen Slots, Basisübernahme, Freigabeeintragsprüfung, Vorschau und Hashvergleiche. Die genauen Eingabehashes stehen in `validierung.json`. Die Werkzeuge wurden für diesen Entwurf nicht geändert. Die angezeigten Formen und ihre Grenzen sind in `vorschau.py` sowie `raumpruefung.json` festgehalten.

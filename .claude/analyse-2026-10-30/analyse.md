# Analyse der allgemeinen Teilelogik, 30.10.2026

## Ergebnis und Auftrag

Die Fahrzeugdaten wurden gestern Abend tatsächlich umfangreich gesammelt und ausgewertet. Der entscheidende Engpass liegt zwischen diesen Beobachtungen und ihrer Wiederverwendung beim Bauen: Die Software hat einen verlässlichen, aber schmalen Kern für Standardflächen. Ihr fehlt eine allgemeine Beschreibung und Nutzung der Anschlüsse von Sonderteilen. Eine größere Beobachtungszahl wird dadurch nicht automatisch zu besserer Teileauswahl oder besserem Bauen nach Anleitung.

Die Emerald zeigt zusätzlich einen Fehler im Arbeitsablauf: Teile wurden teilweise als fehlend behandelt, obwohl sie in Katalog und gespeicherten Fahrzeugen nachweisbar sind. Die spätere Übernahme der vom Nutzer im Spiel korrigierten Fassung repariert den einzelnen Bauplan, aber nicht diese allgemeine Logik.

Nutzerpräzisierungen dieses Chats: Chassis sind fest vorgegeben; Räder sind von dieser Bewertung ausgenommen. Es geht besonders um die allgemeine Teilelogik, Teileauswahl, Anordnung und Übertragung aus Anleitungen. Der aktuelle Emerald-Speicherstand wurde vom Nutzer von Hand weitergebaut und verbessert. Er ist eine Referenz, kein Nachweis einer gelungenen ursprünglichen automatischen Konstruktion.

Es wurden keine Werkzeuge des Builders geändert und keine Spielstände geschrieben. Neue Analysen und KI-Informationen liegen ausschließlich unter `.claude/`. Die vier aktuellen Fahrzeugdateien wurden vor und nach der Auswertung gehasht: unverändert.

## Nachgeprüfte Datenbasis

Ausgewertet wurden aktuelle eigene Fahrzeuge, Downloads, Extra-Datei, Hub-Cache und deren vorhandene Sicherungen. Bytegleiche Dateien und identische PartGraph-Datensätze wurden für die Zählung zusammengefasst.

| Messgröße | Ergebnis | Bedeutung / Einschränkung |
|---|---:|---|
| Unterschiedliche Inhalte der Fahrzeug-SAV-Dateien, inklusive Sicherungen | 42 | Nicht die Anzahl der ursprünglichen Dateipfade |
| Unterschiedliche Teilegraphen inklusive Sicherungen | 132 | Änderungen desselben Fahrzeugs können mehrere Graphen ergeben; keine 132 unabhängigen Experimente |
| Beobachtete Teilenummern inklusive Sicherungen | 1.075 | Einschließlich Baugruppen |
| Teilenummern mit gespeicherten Verbindungen | 1.016 | Alle Nummern der vorhandenen Anschlusstabelle im Archiv wiedergefunden |
| Nummern im allgemeinen Teilekatalog | 2.028 | Katalogeintrag ist weder Anschlussgeometrie noch Freischaltnachweis |
| Nummern in `baugeometrie.GEOM` | 76 | Teilweise nur eine Anschlussseite bekannt; 3823 ausdrücklich gesperrt |
| Karosserieteil-Instanzen außerhalb sämtlicher Baugruppen | 17.706 | Über die 132 Graphen, also mit Varianten desselben Modells |
| Davon mit nicht ausdrücklich gesperrtem GEOM-Eintrag | 6.884 / 38,9 % | Keine Aussage, dass damit jede Anschlussart dieser Instanzen unterstützt wäre |

In den aktuellen Dateien ohne Sicherungen stehen 103 unterschiedliche Graphen, 1.052 Teilenummern und 994 Nummern mit Verbindungen. Die Differenz von 22 Anschluss-Nummern gegenüber der Tabelle ist in den Sicherungen erhalten. Ein schlichtes Neuschreiben mit ausschließlich `anschluesse.py --alle` würde diese historischen Nummern aus der Tabelle verlieren. Das ist kein derzeit nachgewiesener Datenverlust: Die alten Daten sind vorhanden.

Protokollgrundlage: `.claude/sonderteile-und-abdeckung-2026-10-29.md`, insbesondere Kopierrunden 1–5; zugehörige `geom-kandidaten-belege-runde*.json`; `maske-98282-belege.json`; frühere Reviews und Builder-Dokumentation. Die Protokolle beschreiben den Engpass bereits ausdrücklich: Vor den Kopierrunden 65 GEOM-Nummern, danach 76, während die Anschlussbeobachtungen von 639 auf 1.016 stiegen. In Runde 5 kamen keine neuen GEOM-Kandidaten mehr hinzu.

## 1. P1: Beobachtungen werden nicht zu einer allgemeinen Anschlussbibliothek

`anschluesse.py` erzeugt im Wesentlichen Häufigkeiten je Teilenummer, Feld und bekannter Rolle. Dabei gehen in dieser Ausgabe Partnerteil, Verbindungstyp, relative Lage, Quelle und individuelle Kontaktbedingungen verloren. Die originalen SAV-Dateien enthalten diese Informationen weiterhin.

`baue_fahrzeug.py` importiert dagegen `GEOM` aus Python. Es liest weder `teiledaten.json` noch `anschlusspunkte.json` als allgemeine Anschlussdefinition. `sonderteile.json` beschreibt überwiegend komplette Assets und ihre Spender; das ist ebenfalls keine Anschlussbibliothek für normale Einzelteile.

Damit endet die aktuelle Verarbeitung ungefähr bei:

`SAV-Beobachtungen → Feldstatistik / Sonderteile-Katalog → Rechteck-Kandidaten → manuell eingetragene GEOM-Zeilen`

Der letzte Schritt funktioniert für den schmalen unterstützten Fall. Für die meisten neuen Sonderformen gibt es keinen entsprechenden Schritt. Das ist die wichtigste Erklärung dafür, warum das viele Speichern von Fahrzeugen nicht den erwarteten allgemeinen Baufortschritt gebracht hat.

Code: `werkzeuge/anschluesse.py:90`, `werkzeuge/baue_fahrzeug.py:17`, `werkzeuge/geom_kandidaten.py:32`.

## 2. P1: Das Anschlussmodell kann die vorhandenen Techniken nicht ausdrücken

`faces()` modelliert im Wesentlichen zwei Rasterflächen: lokale Unterseite bei z=0 und Oberseite bei z=h. Vollständige Quaternionen werden inzwischen korrekt angewendet. Das Problem ist also nicht generell fehlende 3D-Rotation, sondern die beschränkte lokale Anschlussbeschreibung.

Es fehlen allgemeine lokale Flächen auf weiteren Ebenen, einzelne versetzte Noppen, Stangenachsen, Clipachsen, Kreuzlöcher und kompatible Anschlussarten. Auch ein verdrehtes Ober-/Unterseitenmodell erzeugt keinen zusätzlichen Port eines Winkels.

Beispiele aus den vorhandenen Daten:

- 3956 hat mehrere Anschlussfelder an unterschiedlichen Schenkeln.
- 6143 besitzt neben Noppenflächen eine Achsverbindung.
- 2540 hat Griffanschlüsse an den Feldern 4, 5 und 6.
- 61252 und 6019 besitzen Clip-Verbindungen mit `CylindricalConnection`.
- Ein Jumper braucht eine versetzte einzelne obere Noppe statt eines vollen Rechteckrasters.

Diese Technik ist im Saveformat und in den Beispielen vorhanden; der Geometriekern stellt sie nicht allgemein bereit. Der Typ einer solchen Verbindung darf nicht allein aus ihrer Stärke abgeleitet werden. Die aktuelle Regel 1 → Hinge, mehr → Fixed ist für die automatisch unterstützten Noppenkontakte passend, aber keine allgemeine Klassifikation aller Anschlüsse.

Code: `werkzeuge/baugeometrie.py:173`, `werkzeuge/baugeometrie.py:196`.

## 3. P1: Fehlende Geometrie, fehlende Verfügbarkeit und Teilevarianten werden vermischt

Die Emerald-Dokumentation führt 61252 als nicht im Spiel und die Familie 2436 als nicht verfügbar. Aktuell sind beide im Katalog und in gespeicherten Fahrzeugen nachweisbar. Dass die konkrete Katalogvariante 2436b mit der Spiel-ID 2436 geometrisch übereinstimmt, muss separat bestätigt werden; die ganze Familie als abwesend zu behandeln ist durch die Daten nicht gedeckt.

| Teil | Konkrete vorhandene Daten | Derzeitige Lücke |
|---|---|---|
| 2436 | Unter anderem Airport Baggage Cart, Cattle Driver, Hamburghini; Kontakte an Feldern 0, 1, 2 | Kein GEOM-Eintrag für den Winkel |
| 61252 | Space Rover Explorer, Service Truck, XL Traffic Cones, World Racers Desert Truck | Kein allgemeiner Clip-Port |
| 63082 | Service Truck, Big Green Tractor sowie manuell korrigierte Emerald | Ältere Teileliste sagt weiterhin „nicht im Spiel“ |
| 61409 | 154 deduplizierte Verbindungen in den ausgewerteten Graphen, alle am beobachteten Feld 0 | Keine nutzbare Geometrie trotz vieler Kontakte |
| 99780 | Viele Fahrzeuge und mehrere Felder; beim Emerald-Bau dennoch ausgelassen | Nicht im Rechteck-Lerner darstellbar |

Besonders aussagekräftig: **Space Rover Explorer, Teile 152/151, 61252 Feld 2 ↔ 2540 Feld 4, Stärke 1, CylindricalConnection.** Diese Kombination aus Original-Clip und Griff war bereits vor dem Emerald-Versuch im gespeicherten Korpus vorhanden. Die Anschlussbeobachtung liegt mit relativer Position und Orientierung in `kontaktbelege.json`. Das beweist die beobachtete Kombination; es ersetzt noch keine vollständige Clip-Geometrie für jede beliebige Drehstellung.

Benötigte getrennte Zustände: im Spielkatalog enthalten, im lokalen Fahrzeug beobachtet, freigeschaltet/manuell wählbar, ID-/Varianten-Zuordnung bestätigt, einzelne Ports bekannt, beobachtete Paaranordnung reproduzierbar, allgemein geometrisch unterstützt. Ein negativer Teilefinder-Befund darf die anderen Belege nicht pauschal überschreiben.

## 4. P1: „Graph verbunden“ ist keine geometrische Verifikation

Explizite Verbindungen ersetzen automatische Kontakte desselben Teilepaars. Geprüft werden Struktur, Indizes, Typ/Stärke und anschließend die Erreichbarkeit vom Chassis. Ob sich die angegebenen Ports tatsächlich berühren, wird dabei nicht vollständig geprüft.

Reproduktionen mit dem echten Builder und ausschließlich künstlichen Testdaten:

1. Ein gewöhnlicher 3005 bei `[10000, 10000, 10000]` plus behaupteter Anschluss ans Chassis wird akzeptiert; `lose_teile` bleibt leer.
2. Zwei massive 3005 an exakt derselben Position werden akzeptiert; beide haben einen Graphpfad zum Chassis.

Die Warnung für manuelle Anschlüsse benennt diese Grenze bereits. Trotzdem eignet sich ein Ergebnis „Geprüft“ ohne getrennte Prüfzustände nicht als Nachweis einer korrekten Konstruktion.

Empfehlung: Zwischen strukturell gültigem Graph, geometrisch belegten Kontakten, ungeprüften manuellen Kanten, Kollisionsprüfung und Übereinstimmung mit einer Anleitung unterscheiden. Für bekannte Standardports widersprüchliche manuelle Kanten ablehnen. Für unbekannte Ports einen beobachteten relativen Kontakt oder einen ausdrücklichen experimentellen Status verlangen.

Code: `werkzeuge/baue_fahrzeug.py:324`. Reproduktion: `befunde.json → validation_gap_reproductions`.

## 5. P1: Auch der Lerner besitzt eine echte Prüflücke beim Verbindungstyp

`geom_kandidaten.beobachtungen()` beschränkt seine Noppenflächen-Belege nicht auf passende Verbindungstypen. `gegentest()` vergleicht anschließend Teile, Felder und Stärke, aber nicht `Type`.

Reproduziert: Ein künstliches Fahrzeug mit zwei als `BallConnection` gespeicherten Kontakten wird als Beleg für die Unterseite eines rechteckigen Testteils angenommen. Der Gegentest meldet `exakt: 2` und `vorhergesagt: 2`.

Das ist ein nachgewiesener Fehler der Prüfmethodik. Es ist **kein** Nachweis, dass die aktuell vorhandenen 76 GEOM-Einträge dadurch falsch gelernt wurden. Der separate heutige Korpusvergleich berücksichtigt den Typ und fand für die automatisch vorhergesagten Kontakte keine Abweichung.

Zusätzlich: Zwei Kontakte aus einem einzigen Fahrzeug reichen für MIN_BELEGE=2. Als „schief“ markierte Kontakte können nur Feldhinweise liefern, zählen aber trotzdem zur Annahmeschwelle. Ein leerer beziehungsweise vollständig übersprungener Gegentest ist nicht dasselbe wie ein erfolgreicher Geometrienachweis. Hier sollten Feldwissen, Maskenwissen und Validierungsstärke getrennt werden.

Code: `werkzeuge/geom_kandidaten.py:100`, `:143`, `:174`.

## 6. P2: Die Verfügbarkeit von Spendern kann von der Dateireihenfolge abhängen

`sonderteile.beobachtungen()` verwirft den zweiten Fund eines identischen Graphen vollständig. Das ist für statistische Zählungen sinnvoll, verliert aber zusätzliche Fundorte.

Reproduktion mit demselben künstlichen Fahrzeug in Cache und Download:

- Reihenfolge Cache → Download: `builder.nutzbar = false`.
- Reihenfolge Download → Cache: `builder.nutzbar = true`.

Beide Eingaben enthalten denselben nutzbaren Download. Der Katalog darf diese Information nicht aufgrund der Reihenfolge verlieren. Die Standardreihenfolge liest aktuelle eigene Fahrzeuge und Downloads zuerst und reduziert dadurch das Problem im üblichen Aufruf. Bei Archiven und anderen Reihenfolgen bleibt die Logik fehlerhaft. Kein Nachweis, dass dieser Fehler die konkrete Emerald-Auswahl verursacht hat.

Lösung: Graphen für Zählungen deduplizieren, sämtliche Fundorte und nutzbaren Quellen getrennt erhalten. Aktuelle Dateien und Archive müssen außerdem als solche markiert werden; ein historischer Fund ist keine Garantie eines heute gleichnamig vorhandenen Spenders.

Code: `werkzeuge/sonderteile.py:106`.

## 7. P1 für die Qualitätskontrolle: Die Emerald-Vorschau kontrolliert den Plan nicht unabhängig

Die Sonderteile der Emerald sind in `vorschau.py` über absolute Weltboxen nach Teile-ID hinterlegt. Für diese Teile werden `pos` und `rot` aus dem Plan nicht ausgewertet. Im allgemeinen Zweig wird nur `dreh`, nicht `rot` verwendet. Die Vorschau kann daher von den tatsächlich gespeicherten Transformationen abweichen.

Reproduziert: `kessel_vorn.pos.x += 1000`. Die erzeugte HTML-Datei bleibt bytegleich. Auch die zugehörige Box bleibt am alten Ort.

Die Vorschau ist damit eine Illustration der angenommenen Konstruktion und keine belastbare Kontrolle beliebiger Planänderungen. Allgemein müssen Vorschau, Anschlussprüfung und Export dieselben lokalen Teildefinitionen und dieselbe Transformationskette benutzen. Sichtkörper und Anschlussflächen bleiben unterschiedliche Daten; einfache umschließende Boxen beweisen bei Hohlräumen, Bögen und Clips keine Materialdurchdringung.

Code: `.claude/emerald-express/vorschau.py:24`. Reproduktion: `vorschau-reproduktion.json`.

## 8. P2: Weitere Fahrzeugkopien werden nach dem falschen Ziel optimiert

Die aktuelle Kopierliste maximiert neue, bisher unbeobachtete Teilenummern, nach Verbreitung gewichtet. Das war am Anfang sinnvoll. Bei den inzwischen vorhandenen Daten braucht der nächste Fortschritt aber häufig einen weiteren Kontakt eines **bereits bekannten** Teils: andere Seite, anderer Partner, andere Noppenabdeckung, eindeutigere Orientierung oder ein Gegenbeispiel zu mehreren möglichen Masken.

Ein Fahrzeug mit einer bekannten Nummer, das gerade den fehlenden Clip- oder Winkelanschluss belegt, erhält dafür derzeit keinen Zusatznutzen. Dagegen kann eine neue seltene Sonderform die Liste verbessern, obwohl der Lerner sie weiterhin nicht modellieren kann.

Empfehlung: Erst vorhandene Beispiele auswerten. Weitere Kopieraufträge anschließend nach offenen Port-/Maskenfragen auswählen. Nicht pauschal weitere 24 Fahrzeuge als Voraussetzung verlangen.

Code: `werkzeuge/sonderteile.py:348`.

## 9. P2: Positive Lernbelege und Erfolgsmessung brauchen sauberere Grenzen

Die heutige Prüfung aller aktuellen Graphen findet 5.991 automatische Kontakte; alle sind einschließlich Typ, Feld und Stärke gespeichert. Das ist ein gutes Ergebnis für den unterstützten Kern. Insgesamt enthalten diese Graphen 25.582 unterschiedliche gespeicherte Kontakte, einschließlich interner Baugruppenkontakte. Deshalb sind „5.991 von 5.991 exakt“ und „alle Bautechniken unterstützt“ sehr verschiedene Aussagen. Die Gesamtzahl eignet sich wegen ihres Baugruppenanteils auch nicht unmittelbar als Karosserie-Erfolgsquote.

Die 49 vorhandenen Tests bestehen. Ein erneuter Leave-one-out-Lauf meldet 66 von 66 einfachen vorhandenen Geometrien ohne Konflikt. Das sind keine Ende-zu-Ende-Tests für Teileauswahl, Anleitungstreue oder eine ungesehene Sonderteilkonstruktion.

Teilegraph-Fingerprints hängen unter anderem von Farben, Reihenfolge und gespeicherten Graphdaten ab. Varianten desselben Modells können somit als mehrere Graphen zählen. Das ist für Archivierung vertretbar, aber kein Beweis unabhängiger Lernbelege. Außerdem unterscheiden die Werkzeuge nicht sicher zwischen vom Builder geschriebenen und anschließend vom Spiel neu berechneten Verbindungen. Das ist in den gestrigen Protokollen bereits als Grenze genannt.

Benötigt werden Provenienz je Beobachtung sowie Tests mit zurückgehaltenen Fahrzeugfamilien. Selbsterzeugte Kanten dürfen nicht als unabhängiger Nachweis ihrer eigenen Richtigkeit zurückfließen. Erfolg getrennt messen: korrekte vorhandene Kontakte, fälschlich erfundene Kontakte, nicht erklärte relevante Kontakte, unterstützte Ports, Variantenauflösung und Anleitungstreue.

## 10. Die aktuelle Emerald ist reproduzierbar, aber keine allgemeine Lösung

Der heutige Builder reproduziert die aktuelle, vom Nutzer verbesserte Emerald in ihrer geometrischen Anordnung: **51 von 51 Teilen** passen nach Design, Farbe, Position, Orientierung und Skalierung, bei toleriertem Float-Rauschen von 0,01 Positionseinheiten und 0,0001 bei normierten Quaternionen. Die 54 unterschiedlichen beziehungsweise 56 rohen Verbindungen stimmen ebenfalls überein. Die zwei zusätzlichen Roh-Einträge sind bereits in der Vorlage doppelte Chassis-Verbindungen. Daraus ist kein neuer Anschlussfehler abzuleiten.

Der Abgleich umfasst nicht sämtliche Fahrzeug-Metadaten oder ein erneutes Spiel-Laden. Er bewertet auch nicht, ob der Nutzerstand genau dem Originalset entsprechen soll.

Der Plan enthält 40 zusätzliche Einzelteile, davon 13 ohne allgemeine GEOM-Unterstützung, sowie 22 explizite Anschlüsse. `erzeuge_bauplan.py` legt Positionen und Kontakte konkret fest; es enthält keinen allgemeinen Solver, der Baugruppen aus Anleitungen erkennt und über Anschlussbedingungen positioniert.

Die dokumentierten Korrekturen an Dach, Kessel, Ring und Schornstein sind wertvolle neue Beispiele. Damit daraus eine Verbesserung für andere Modelle entsteht, müssen ihre lokalen Anschlussbedingungen in eine allgemeine Bibliothek übergehen. Das bloße Nachtragen derselben Weltkoordinaten in genau diesen Plan erfüllt das nicht.

Die offizielle Anleitung wurde für den visuellen Kontext erneut gelesen: [LEGO 6071644](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6071644.pdf). Das Foto-Modell im Projekt besitzt zusätzliche Änderungen gegenüber dieser Anleitung. Künftig muss pro Bauauftrag ausdrücklich feststehen, ob Anleitung oder Foto das Ziel definiert. Räder und festes Chassis sind hier nach Nutzerpräzisierung kein Qualitätskriterium.

## Konkreter Verbesserungsweg

### A. Vorhandenes Wissen verfügbar machen

1. Unveränderlichen Korpusindex mit Datei-Hash, Graph-Hash, allen Fundorten und Herkunftsstatus anlegen. Aktuelle Daten und Sicherungen gemeinsam berücksichtigen. Keine Spielerkennungen in Analysen übernehmen.
2. Für jeden gespeicherten Kontakt eine normale maschinenlesbare Beobachtung ablegen: beide Design-IDs und Felder, Typ, Stärke, Skalierung, relative 3D-Lage und Orientierung, Fahrzeug und Quellnachweis. Die Feldhäufigkeit bleibt eine Statistik, nicht die Wissensbasis selbst.
3. Zwei Wiederverwendungsstufen anbieten: exakt beobachtete Paaranordnungen und allgemein gelernte Anschlussports. Ein beobachtetes Paar lässt sich gemeinsam starr bewegen, ohne schon die gesamte Form jedes beteiligten Teils zu kennen. Es ist trotzdem nur für seine belegten Bedingungen gültig; Clip- und Gelenkfreiheiten müssen separat beschrieben werden.

Als Analysebeispiel wurden für 13 relevante Teilenummern bereits **1.371 unterschiedliche Kontaktmuster** mit relativen Transformationen und Quellbeispielen extrahiert: `kontaktbelege.json`. Das ist ein Belegdossier, noch keine geprüfte vollständige Geometriebibliothek und keine Änderung am Builder.

### B. Portmodell erweitern und prüfen

Ein Port benötigt eine lokale Position/Fläche/Achse, Orientierung, Anschlussart und kompatible Gegenseite sowie gegebenenfalls eine Noppenmaske und erlaubte Bewegungsfreiheit. Bestätigung und Unsicherheit gelten pro Port, nicht pauschal pro Teil. Vorhandenes `GEOM` kann als kompakte Darstellung einfacher Flächen bestehen bleiben und in dieselbe Schnittstelle übersetzt werden.

Aus mehreren Kontakten lassen sich Masken als Bedingungen bestimmen. Stärke 2 auf einer angrenzenden Fläche mit vier Kandidatennoppen beweist nicht alle vier Noppen des Zielteils: Bei dieser einen Bedingung bleiben sechs Zweiermasken möglich. Zusätzliche Partnerlagen sollen diese Mehrdeutigkeit auflösen. Fehlende Kanten sind nur dann belastbare Gegenbelege, wenn die Vollständigkeit der jeweiligen Spielbeobachtung dafür geklärt ist.

Die Größe in `teiledaten.json` darf nicht pauschal als präziser Körper, Ursprung und Anschlusslage verwendet werden. Ein vorhandenes Gegenbeispiel ist 88930: Metadaten `[4,2,1]`, handmodellierte GEOM-Höhe 20. Kontaktflächen, sichtbare Form und allgemeine Katalogmaße müssen getrennt bleiben.

Priorität nach erwarteter Wirkung:

- Häufige Fliesen, Rundplatten und Unterseiten einfacher Sonderformen: etwa 2412, 98138, 4032 und 61409. Erst konkrete Anschlussbedingungen prüfen, dann übernehmen.
- Winkel und seitliche Noppen: 2436, 3956, 99780, 11211, 87087.
- Clip-/Stangentechnik: 2540, 61252, 6019.
- Kessel, Jumper und Schüssel: 6143, 87580, 4740.

Diese Reihenfolge nutzt gespeicherte Beispiele und behebt zugleich den für die Emerald sichtbaren Technikengpass. Es wird nicht behauptet, dass alle vollständigen Geometrien allein aus den vorhandenen positiven Kontakten eindeutig bestimmbar sind.

### C. Konstruktion und Qualitätskontrolle auf dieselbe Grundlage stellen

Teileauswahl zunächst gegen Katalog, Varianten und Beobachtungen auflösen. Für eine Anleitung lokale Baugruppen und Beziehungen erfassen, dann über Ports anordnen. Erst anschließend den fertigen Oberbau auf das feste Chassis abbilden. Änderungen durch diese Anpassung ausdrücklich festhalten; die internen Beziehungen des Kessels oder Führerhauses sollen nicht beiläufig geändert werden.

Vorschau und Export verwenden dieselben lokalen Teilgeometrien und Transformationen. Ein unabhängiger Sollvergleich prüft Identität, Variante, Anzahl, Farbe und relative Lage der Baugruppen. Manuell korrigierte Spielstände werden als Referenzfälle und Lernbelege erfasst, nicht nachträglich als erfolgreiche ursprüngliche Automatik gezählt.

Abnahmekriterien für den nächsten Implementierungsschritt:

- 61252 an 2540 aus vorhandenen Belegen platzierbar, ohne globale Emerald-Sonderkoordinaten.
- 3956 und 6143 in einer neuen Lage verwendbar; gemeinsame Drehung und Verschiebung bleiben konsistent.
- Ein bewegtes oder gedrehtes Sonderteil verändert die Vorschau tatsächlich.
- Physisch widersprüchliche manuelle Standardkontakte und identische massive Überlagerungen werden erkannt.
- Falscher gespeicherter Verbindungstyp wird vom Flächen-Lerner nicht als exakter Beleg akzeptiert.
- Cache-/Download-Reihenfolge verändert die Nutzbarkeit eines tatsächlich vorhandenen Spenders nicht.
- Tests an zurückgehaltenen Modellen zusätzlich zum Trainingskorpus bestehen.

## Artefakte und Reproduktion

- `audit.py`: aktuelle Dateien und Sicherungen nur lesen; Vergleich der Emerald, Auswertung und künstliche Fehlerreproduktionen. Aufruf: `python .claude/analyse-2026-10-30/audit.py`.
- `befunde.json`: bereinigte Messergebnisse, Quell-Hashes, Vergleich und reproduzierte Prüflücken.
- `kontaktbelege.json`: ausgewählte gespeicherte Kontakte in lokalen Bezugssystemen, mit Beispielen und Herkunft.
- `geom-gegenpruefung.json`: erneuter Lauf des bestehenden Rechteck-Lerners einschließlich Leave-one-out.
- `vorschau-reproduktion.json`: Hashvergleich vor und nach Änderung einer Sonderteilposition; beide HTML-Dateien waren identisch.

Die vorhandenen Tests wurden unverändert ausgeführt: `python -m unittest discover -s .claude/tests -v` → 49 bestanden. Die künstlichen Gegenbeispiele zeigen zusätzliche nicht abgedeckte Fälle; sie widerlegen nicht die bestandenen Tests innerhalb ihres jeweiligen Umfangs.

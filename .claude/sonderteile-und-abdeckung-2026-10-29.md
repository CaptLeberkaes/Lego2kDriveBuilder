# Sonderteile-Katalog und Anschluss-Abdeckung (29.10.2026)

Ziel: Der KI-Builder soll die nach der Freischaltung sichtbaren Teile kennen, ohne Handkatalog.
Gelesen wurden nur Dateien. Kein Spielstand wurde geschrieben, kein Pak entschlüsselt.

## 1. Was `baue_fahrzeug.py` je Teil wirklich braucht

| Teileart | Woher der Builder es nimmt | Was er braucht |
|---|---|---|
| Normale Steine (`teile` im Bauplan) | `GEOM` in `baugeometrie.py` | `l`, `w`, `h`, FieldIndex `unten`/`oben`, optional `*_zellen`. Ohne GEOM oder mit `maske_unbekannt` bricht er ab, außer der Plan nennt `verbindungen` mit `fa`/`fb` ausdrücklich. |
| Chassis | als Ganzes aus dem Vorlagenfahrzeug (`vorlage_name`, `vorlage_datei`) | ein Fahrzeug mit diesem Chassis in `CustomVehicles` oder `DownloadedVehicles` |
| Räder | aus der Vorlage oder per `radtausch` aus einem Spenderfahrzeug | ein Spenderfahrzeug mit gleichem Radnamen (`fl`, `fr`, …) |
| Baugruppen, Flairs, Propeller | nur über `behalten` aus der Vorlage | die Vorlage muss sie schon enthalten |

`teiledaten.json` (Name, Größe, Masse) und `anschlusspunkte.json` liest der Builder **nicht** direkt.
Beide sind Hilfsdaten für die KI bzw. für das Erweitern von GEOM.
Für Sonderteile ist also die entscheidende Frage nicht „gibt es Daten?“, sondern
„liegt ein Fahrzeug mit diesem Teil in einem Spielstand, den der Builder lesen kann?“.

## 2. Einzelsteine: nichts zu ergänzen

`teiledaten.json` und `bricks_by_id.json` haben genau dieselben 2028 Nummern. 7 Einträge haben keinen Namen,
alle haben eine Größe. Die Prüfung läuft als Test (`test_teiledaten_cover_every_encyclopedia_brick`).

## 3. Neuer Katalog: `sonderteile.json` aus `werkzeuge/sonderteile.py`

```
cd werkzeuge
python sonderteile.py            # liest Enzyklopädie, Spielpaketnamen und alle Fahrzeug-Spielstände
```

Jeder Eintrag ist gleich aufgebaut:

- `belegt.enzyklopaedie`: Name, Gelände, Werte, Motor, Seltenheit, Freischaltquelle (L2KD-Export)
- `belegt.im_spiel`: Paketpfad, im installierten Spiel mit genau diesem Namen gefunden
  (aus `.claude/freischaltung/assetnamen-live.json`, nur gelesen)
- `belegt.in_fahrzeugen`: Fahrzeuge in den Spielständen mit Datei, Liste, Radpositionen und echten Teilenummern
- `annahmen`: abgeleitet, nicht geprüft, z. B. Anzeigename ohne „(new!)“, LEGO-Teilenummern aus dem Radnamen,
  Auto/Boot aus dem Spielordner, `_Garage` = Startchassis
- `builder.nutzbar` und `builder.hinweis`: Kann `baue_fahrzeug.py` das Teil heute übernehmen, und wenn nicht, was zu tun ist

Stand der erzeugten Datei:

| Kategorie | gesamt | mit Enzyklopädie | im Spiel belegt | in Fahrzeugen gesehen | im Builder nutzbar |
|---|---|---|---|---|---|
| Räder | 733 | 327 | 733 | 39 | 23 |
| Baugruppen | 63 | 30 | 63 | 3 | 2 |
| Flairs | 599 | 550 | 597 | 18 | 15 |
| Propeller | 39 | 25 | 39 | 2 | 0 |
| Chassis | 960 | 775 | 959 | 48 | 26 |
| Fertigfahrzeuge | 662 | 662 | – | Chassis bei 21 gesehen | Chassis bei 3 nutzbar |

Einträge mit `nur_im_spiel` (z. B. 406 Räder, 185 Chassis) kennt nur das Spielverzeichnis, die Enzyklopädie nicht.
Bei Chassis ohne Nummer (`Bus`, `ATV`, …) kann es sich um Basis-Konfigurationen handeln, die man nicht wählen kann.
Das ist ungeprüft.

## 4. Anschlusspunkte: Messung über alle Spielstände

`anschluesse.py` liest jetzt auch den Creators-Hub-Cache (`ArtemisChubCache.sav`, Liste `CachedVehicles`).
Gleiche Teilegraphen werden nur einmal gezählt. Mit `--alle` werden alle Fahrzeugdateien im Spielordner gelesen.

| Quelle | verschiedene Fahrzeuge | Teile mit Anschlussbeobachtung |
|---|---|---|
| bisher (`ArtemisVehicle` + `ArtemisDownloadedVehicle`) | 39 | 380 |
| + Creators-Hub-Cache | 80 | **630** (+250) |
| + alle Sicherungen in `_sicherungen` | 83 | 630 (keine neuen Teile) |
| Stand nach weiterem Blättern im Hub (21:00) | 81 | 639 |

`anschlusspunkte.json`/`.md` sind mit `--alle` neu erzeugt.

**Der eigentliche Engpass ist GEOM, nicht die Beobachtung.** Vorher hatten nur 44 Teile GEOM.

## 4a. GEOM erweitert: 21 neue Teile, 2 ergänzte Seiten

Neues Werkzeug `werkzeuge/geom_kandidaten.py` leitet GEOM für einfache Platten, Steine und Fliesen automatisch ab:

- **Annahme:** Größe aus `teiledaten.json` und das Noppenraster der vorhandenen GEOM-Teile.
- **Beleg:** gespeicherte Verbindungen zu Teilen mit bekannter GEOM, in voller 3D-Lage. Jede Seite braucht mindestens
  2 Kontakte mit nur einem FieldIndex, und die vorhergesagte Noppenzahl muss jedes Mal der gespeicherten Stärke entsprechen.
  Alias-Teile (laut `teiledaten.json`) brauchen einen Kontakt, der zum Original passt.
- **Gegentest:** Mit der erweiterten GEOM werden alle Flächenverbindungen der neuen Teile vorhergesagt
  und mit den gespeicherten verglichen.
- **Leave-one-out (`--vorhandene`):** Jedes der 34 vorhandenen einfachen GEOM-Teile wird so abgeleitet, als wäre es unbekannt.
  Ergebnis: 34 von 34 ohne Konflikt. Bei 3029 und 3035 fand das Verfahren die bisher unbekannte Unterseite.

In `baugeometrie.GEOM` eingetragen (Belege: `.claude/geom-kandidaten-belege.json`):
3027, 3030, 3036, 3456, 3958, 4162, 4282, 4477, 6111, 6636, 11212, 26603, 35382 (Alias von 3005), 41539, 44237,
60479, 69729, 78329, 87079, 91988, 93888 (Alias von 3007). Außerdem `unten` bei 3029 und 3035.
Alle 20 zuvor genannten Rechteckteile sind dabei, dazu 41539 (PLATE 8X8), weil neue Hub-Fahrzeuge Belege brachten.
Nicht beobachtete Seiten bleiben `None`, z. B. die Oberseite von 4477. Dafür verbindet der Builder nichts automatisch.

| Ganzer Korpus (81 Fahrzeuge) | GEOM-Teile | vorhergesagte Verbindungen | davon exakt gespeichert |
|---|---|---|---|
| vorher | 44 | 3120 | 3120 |
| nachher | 65 | 3818 | 3818 |

**Im Spiel bestätigt** ([geom-spieltest.md](geom-spieltest.md)): Ein Builder-Fahrzeug aus 44237, 3030, 87079, 6111,
78329 und 4162 lud ohne lose Teile. Nach dem Speichern im Spiel waren alle 6 neu berechneten Verbindungen identisch
mit denen des Builders. Die übrigen 15 neuen Einträge sind bisher nur über den Korpus belegt.

Verbaute Karosserieteile mit GEOM: 37,5 % → 40,4 % (von 10 231 Teilen ohne Baugruppen).
Die übrigen 574 beobachteten Teile ohne GEOM sind fast alle Sonderformen. Am häufigsten verbaut sind
35480, 99780, 2420, 11477, 36841, 4032, 65634, 2780, 15068 und 3794. Sie brauchen Zellmasken oder Seitenanschlüsse,
die das Verfahren bewusst nicht errät. 21 weitere einfache Teile (z. B. 2465, 3006, 6112, 3026) haben noch keine Kontakte
im Korpus. Sie kommen automatisch dazu, sobald Fahrzeuge mit ihnen im Spielstand liegen:
`python werkzeuge\geom_kandidaten.py --vorhandene --json .claude\geom-kandidaten-belege.json`
schlägt sie dann als fertige GEOM-Zeilen vor.

### Kopierrunde 1 (21:36): 4 Garagenkopien

Cattle Driver, Cranium Insanium, Foul Runnings Truck und Double Decker Tour Bus, je 71–88 verschiedene Teile.
Neue Teile pro Kopie: 11, 17, 5 und 21. Teile mit Anschlussbeobachtung 639 → 690.
GEOM 65 → 71 (2465, 6112, 6212, 43802, 44042, 92438) plus fehlende Seiten bei 3028, 4477 und 60479.
Leave-one-out: 55 von 55 ohne Konflikt. Korpus-Gegentest über 91 Fahrzeuge: 4512 von 4512 Verbindungen exakt.
Belege: `.claude/geom-kandidaten-belege-runde1.json`.
Hinweis: In `ArtemisVehicle.sav` fehlen seitdem 16 Basisfahrzeuge („Neues Fahrzeug 05“ bis „23“, teils).
Sie liegen in `_sicherungen/2026-10-29_21-17-07`. Baupläne mit diesen Vorlagen brauchen deshalb `vorlage_datei` auf diese Sicherung.

### Kopierrunde 2 (21:53): Space Rover Explorer und 12 Kopien nach der Abdeckungsliste

Teile mit Anschlussbeobachtung 690 → 701 → 842. GEOM 71 → 74 (3006, 30400, 35386) plus die Unterseite von 92438
und die Oberseite von 2465. Leave-one-out: 61 von 61. Korpus-Gegentest über 104 Fahrzeuge: 5550 von 5550 exakt.
Belege: `.claude/geom-kandidaten-belege-runde1b.json`, `-runde2.json`.
Einfache Rechteckteile ohne GEOM gibt es nur noch 12, davon ist eines beobachtet. Weitere Kopien vergrößern deshalb
vor allem die Anschlussbeobachtungen. Mehr automatisch verbaubare Teile kommen erst, wenn auch Sonderformen
(Zellmasken) abgeleitet werden.

### Kopierrunde 3 (22:12): 11 weitere Kopien

Teile mit Anschlussbeobachtung 842 → 906. GEOM 74 → 75 (35275, Alias von 3003). Leave-one-out: 65 von 65.
Korpus-Gegentest über 114 Fahrzeuge: 5982 exakt, 6 abweichend. Alle 6 betreffen schief eingebaute Teile oder die
handmodellierten Sonderformen 3040, 88930, 98282 und 4212. Bei 98282 zählt das Spiel im Mappy Camper 2 Noppen,
die Maske kennt nur 1; die Maske ist also unvollständig. `geom_kandidaten.py` wertet solche Kontakte nur als Feldbeleg.
Die Kopierliste ist jetzt nach den Garagen-Reitern sortiert (Collection, Friends, Creator, City, Speed Champions,
Ideas, Icons). Abgeleitet ist das aus dem Feld `license`; „Collection“ für Fahrzeuge ohne Lizenz ist eine Annahme.

### Kopierrunde 4 (22:25): 13 weitere Kopien

Gespeichert wurden Nr. 1, 2, 4, 9, 10, 17–21, 23 und 24 der Liste aus Runde 3. Statt Nr. 3 (Desert of Destruction Buggy,
`DuneBuggy_8864`) ist „Dakarish“ (`Duhkar_VC000`) im Spielstand; der Buggy steht deshalb wieder auf der Liste.
Teile mit Anschlussbeobachtung 906 → 982 (127 Fahrzeuge inkl. Sicherungen). GEOM 75 → 76 (35403 FLAT TILE 1X1,
10 Kontakte, Gegentest 10/10). Leave-one-out: 65 von 65. Korpus-Gegentest über die 98 Fahrzeuge der aktuellen
Spielstände: 5758 exakt, 14 mit anderer Stärke, alle an 98282 (Cleaning Truck, Scullywagon, Service Truck, Diesel Punk).
Das Spiel zählt dort jeweils doppelt so viele Noppen wie die Maske; die 98282-Maske ist der nächste klare Fehler.
Offene Teile in Autos 479 → 397; die neue Liste bringt 133 davon (46 % der gewichteten offenen Verwendungen).
Belege: `.claude/geom-kandidaten-belege-runde4.json`. Sicherung: `_sicherungen/2026-10-29_22-25-00`.

### Kotflügel 98282: Maske korrigiert

Die handmodellierte Maske kannte oben nur 2×1 Noppen. Aus 130 Fahrzeugen wurden alle Kontakte von 98282 mit
GEOM-Partnern im 90-Grad-Raster gesammelt (Partner-Noppen in lokalen Zellen von 98282, gespeicherte Stärke,
auch Nachbarn ohne Verbindung). Ergebnis: **oben 2×2** (Zellen (0,0), (1,0), (0,−1), (1,−1), also eine Reihe
Richtung lokal +y dazu), **unten 2×1** wie bisher. Die neue Maske sagt 278 von 278 Ober- und 243 von 243
Unterseitenkontakten exakt vorher; die alte lag oben 42-mal falsch. Felder unverändert (unten 0, oben 1).
Belege: `.claude/maske-98282-belege.json`. Korpus-Gegentest danach über 131 Fahrzeuge inkl. Sicherungen:
**6677 von 6677 exakt**, keine Abweichung mehr. Die Abweichungen aus Runde 3 und 4 gingen also alle auf 98282 zurück.
Test: `test_mudguard_98282_has_2x2_studs_on_top_toward_plus_y`.

### Kopierrunde 5 (22:37): 4 weitere Kopien, Pause

Apocalypse Truck, Bird of Play, Cornmobile und Shadow Z-Beast. Teile mit Anschlussbeobachtung 982 → 1016.
Keine neuen GEOM-Kandidaten; Leave-one-out 66 von 66. Offene Teile in Autos 397 → 362; die nächste Liste
(`.claude/kopierliste.md`) brächte 114 davon (46 %). Belege: `.claude/geom-kandidaten-belege-runde5.json`.
Sicherung: `_sicherungen/2026-10-29_22-37-51`. Spielstand: 45 von 50 Plätzen belegt.

## 5. Mehr Fahrzeuge in den Spielstand bringen, mit wenig Handarbeit

Freie Plätze heute: `CustomVehicles` 27 von 50 frei, `DownloadedVehicles` 34 von 50 frei.

1. **Creators Hub nur durchblättern (am wenigsten Arbeit).** Jedes angesehene Modell landet im Cache
   (`ArtemisChubCache.sav`, derzeit 51 Einträge, 41 neue Teilegraphen). Das bringt Anschlussdaten, aber keine Builder-Vorlagen.
   Der Cache ist begrenzt und wird vermutlich überschrieben. Deshalb nach jeder Runde sichern:
   ```
   python werkzeuge\sichern.py
   python werkzeuge\anschluesse.py --alle "_sicherungen/*/ArtemisChubCache.sav" --json anschlusspunkte.json --md anschlusspunkte.md
   ```
2. **Gezielt herunterladen.** Ein heruntergeladenes Modell kommt nach `ArtemisDownloadedVehicle.sav`
   und taugt dann als `vorlage_name`/`vorlage_datei` oder Rad-Spender.
   Kandidaten: Einträge in `sonderteile.json` mit `builder.hinweis` „Nur im Creators-Hub-Cache gesehen“.
3. **Fertigfahrzeuge in der Garage kopieren.** Seit der Freischaltung sind alle 662 Fertigfahrzeuge vorhanden.
   Fahrzeug in der Garage öffnen, eine Kleinigkeit ändern und speichern. Dann schreibt das Spiel eine Kopie mit
   **vom Spiel berechneten** Verbindungen nach `ArtemisVehicle.sav`. Das ist der beste Beleg.
   Eine fertige Liste je Runde erzeugt `python werkzeuge\sonderteile.py --mit-sicherungen --kopierliste 24 --ohne-boote`
   → `.claude/kopierliste.md`. Grundlage sind die Teilelisten aller 662 Fertigfahrzeuge aus der Enzyklopädie
   (`.claude/quellen/l2kd-encyclopedia/fahrzeugteile/vehicle_parts.json`, Git-Hash geprüft). Die Auswahl ist eine gierige
   Mengenüberdeckung: Als Nächstes kommt jeweils das Auto mit den meisten noch nie gesehenen Teilen, und verbreitete Teile zählen mehr.
   Alle 600 Fahrzeuge braucht es dafür nicht. Stand 21:41 (691 offene Teile in Autos):

   | Autos kopieren | offene Teile danach gesehen | Anteil der Teileverwendungen |
   |---|---|---|
   | 10 | 120 | 40 % |
   | 24 | 246 | 64 % |
   | 50 | 393 | 81 % |
   | 100 | 561 | 93 % |

   Fehlt die Teileliste, fällt das Skript auf die Schätzung zurück: Chassis noch nie gesehen, ein Viertel Boote,
   die schwersten zuerst, höchstens eines je Modellfamilie. Mit `--mit-sicherungen` zählen auch schon gelöschte Kopien, die Liste rückt also
   nach jeder Runde weiter. Die Rohdaten stehen in `sonderteile.json` → `fahrzeuge`. Gute Kandidaten haben `chassis_in_spielstaenden: false`
   und `garage_valid: "Valid"`; das gilt für 627 von 662 Fahrzeugen. Jede Kopie bringt mindestens ein neues Chassis
   samt Rädern als Vorlage.
4. Danach `python werkzeuge\anschluesse.py --alle …`, `python werkzeuge\sonderteile.py` und
   `python werkzeuge\geom_kandidaten.py --vorhandene` erneut ausführen. Die Zahlen in Abschnitt 3, 4 und 4a wachsen dann von selbst.
   Neue GEOM-Zeilen trägt man aus der Ausgabe in `baugeometrie.py` ein. Das bleibt bewusst ein Schritt mit Kontrolle.

Vorsicht: Fahrzeuge, die `baue_fahrzeug.py` geschrieben hat und die das Spiel noch nicht neu gespeichert hat,
enthalten Builder-Verbindungen. Sie sind kein unabhängiger Beleg. `anschluesse.py` kann sie noch nicht unterscheiden.

## 6. Automatisch abgedeckt bzw. weiter nur durch Beobachtung

Automatisch, ohne Handarbeit:
- Name, Größe und Masse aller 2028 Steine
- Namen, Gelände, Werte, Motor, Seltenheit und Freischaltquelle aller Räder, Baugruppen, Flairs, Propeller,
  Chassis und Fertigfahrzeuge, soweit in der Enzyklopädie vorhanden
- Existenz im installierten Spiel (Paketname) für 2391 Sonderteile
- GEOM für einfache Rechteckteile mit Kontakten im Spielstand (jetzt 65 Teile insgesamt)
- Welche Fahrzeuge welches Sonderteil enthalten, und ob der Builder sie als Vorlage oder Spender nutzen kann

Braucht weiter Beobachtungen aus echten Fahrzeugen:
- GEOM für Sonderformen (Zellmasken, Seitennoppen, Clips). Ohne GEOM verbindet der Builder ein Teil nicht automatisch.
  Einfache Rechteckteile leitet `geom_kandidaten.py` ab, sobald Kontakte im Spielstand liegen.
- Rad-, Baugruppen-, Flair- und Propeller-Geometrie samt Teilen. Übernehmen lassen sie sich nur aus einem Fahrzeug,
  das sie schon enthält: heute 23 Räder, 2 Baugruppen, 15 Flairs, 0 Propeller, 26 Chassis.
- Ob Chassis ohne Nummer und `nur_im_spiel`-Einträge im Body Shop wirklich wählbar sind

## Geänderte und neue Dateien

- neu: `werkzeuge/sonderteile.py`, `sonderteile.json`, `werkzeuge/geom_kandidaten.py`, `.claude/geom-kandidaten-belege.json`,
  `.claude/tests/test_sonderteile.py` (10 Tests), `.claude/tests/test_geom_kandidaten.py` (6 Tests)
- geändert: `werkzeuge/anschluesse.py` (Cache, Duplikate, `--alle`, Platzhalter), `werkzeuge/baugeometrie.py` (GEOM 44 → 65),
  `anschlusspunkte.json`/`.md` (neu erzeugt), `README.md`
- Tests: `python -m unittest discover -s .claude/tests` → 45 Tests OK

# Modell 2 – ASTRA II Forward Carrier

Stand: 30.10.2026. **Offline geprüft, kein Spieltest und kein Spielstandtausch.**

## Prüfergebnis

| Prüfung | Ergebnis |
|---|---|
| Ausrichtung | Außentank, beide Booster und Orbiter zeigen gemeinsam waagerecht nach +X, also in Fahrtrichtung |
| Zweites Modell | Eigener Name und eigene Plan-/Vorschaudateien |
| Modell 1 erhalten | Alle ursprünglichen Dateien hashgleich, einschließlich erstem Plan, HTML und PNG |
| Teile | 107 Oberbauteile, 123 insgesamt |
| Verbindungen | 136 rohe Einträge: 18 native, 95 geometrisch berechnete, 23 beobachtete Paarlagen |
| Ungeprüfte manuelle Kanten | 0 |
| Konnektivität | Alle Oberbauteile haben einen Pfad zum Chassis |
| Chassis und Räder | Alle 16 übernommenen Teile in Daten und Transformation bytegleich zum Spender |
| Raumprüfung | 0 Überschneidungen an den verwendeten vereinfachten konvexen Körpern |
| Vorschau | Aus dem tatsächlich gebauten Graphen; Sonderteilbewegung verändert nachweislich die Ansicht |
| Lokale Freigabeeinträge | Alle verwendeten neuen Design-IDs in beiden lokalen Listen vorhanden; Auswahl im Menü ungetestet |
| Serialisierung | Ergebnis im Speicher erneut gelesen und bytegleich rückserialisiert |
| Andere Fahrzeuge | Alle 49 Nicht-Zielplätze identisch, einschließlich Emerald |
| SAV-Sicherheit | Alle elf aktuellen SAV-Dateien während der Validierung hashgleich; keine SAV geschrieben |
| Regressionen | 63 bestehende Tests bestanden; zwei bereits bekannte ResourceWarnings des alten Lesers, keine Fehler |

`validierung.json` enthält die tatsächlich berechneten Richtungsvektoren: Für die drei Raketenspitzen wird die lokale Z-Achse, für den Orbiter seine lokale Längsachse geprüft. Damit wird nicht nur eine Beschriftung in der Vorschau kontrolliert. Alle Vektoren entsprechen innerhalb der numerischen Toleranz `[1, 0, 0]`.

## Räumliche Änderungen

Die aufrechten Sockel des ersten Entwurfs wurden nicht einfach mitgedreht. Stattdessen trägt ein neuer hinterer Winkel den horizontalen Tank, zwei Seitenhalter tragen die Booster, und ein neuer vierbeiniger Träger verbindet die Querholme des liegenden Orbiters mit dem Deck. Die Booster wurden nach außen versetzt, damit die senkrechten Stützen zwischen ihnen und dem Außentank Platz finden. Der seitliche Bedienpod liegt hinter den Flügelwurzeln.

Bei der ersten Raumprüfung der neuen Halterung wurden Überlagerungen am abgestuften Deck und an den Flügelwurzeln erkannt. Die Trägerhöhen, Zwischenplatten und Randstreifen wurden korrigiert. Die finale Prüfung findet an ihren vereinfachten Körpern keine Überschneidung. Es wurden keine Kanten manuell erzwungen, um einen räumlichen Fehler zu übergehen.

## Grenzen

Die Vorschau zeigt vereinfachte Sonderteilkörper, keine originalen Spielmeshes. Der 3956-Winkel wird mit zwei vorhandenen lokal kalibrierten Hüllen dargestellt. Studs, Hohlräume, Lenkeinschlag, Federweg und der Fahreravatar werden nicht vollständig auf Kollisionen geprüft. Aus null Hüllkörpertreffern folgt kein vollständiger Nachweis physischer Baubarkeit.

Längere Auskragungen von Tank und Boostern, die Tragfähigkeit ihrer hinteren Anschlüsse und das Fahrverhalten sind nicht dynamisch getestet. Die vorhandenen Paarlagen belegen die einzelnen Anschlüsse, nicht die Belastbarkeit des gesamten Trägers. Sitz-/Avatarposition, Laden, erneutes Speichern und die vom Spiel neu berechneten Kontakte müssen im Spiel geprüft werden. Der Builder lässt die Garagen-Metadaten `GarageSaveDataMap` unverändert; deren Auswirkungen bleiben offen.

Die interne Prüfbelegung des Builders ist keine vereinbarte Live-Zielbelegung. Wettbewerbsvorgaben über die bisherige Entwurfsspezifikation hinaus wurden nicht angenommen.

## Nachweise

`kontaktpruefung.json` listet jede Kante mit ihrer Klassifikation und die Referenzgraphen mit Quellenhashes. `raumpruefung.json` dokumentiert Ausdehnung, Körperannahmen und Ergebnis. `modell-1-ausgangshashes.json` sichert den unveränderten ersten Entwurf ab. Alle KI-Notizen und Prüfskripte dieses zweiten Modells liegen in diesem Ordner. Gemeinsame Werkzeuge wurden nicht verändert.

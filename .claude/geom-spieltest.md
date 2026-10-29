# Spieltest der neuen GEOM-Teile („GEOM Test 1“)

**Ergebnis (29.10.2026, 21:20): bestanden.** Geschrieben um 21:17 nach Sicherung `_sicherungen/2026-10-29_21-17-07`.
Im Spiel war kein Teil lose, die Lage stimmte mit dem Plan überein (Screenshots vom Nutzer), und das Speichern klappte.
Beim Speichern hat das Spiel die Verbindungen neu berechnet (VersionId 1 → 2). Die 6 Verbindungen der neuen Teile
sind **identisch** mit denen des Builders: Teilepaare, FieldIndex, Noppenzahl und Typ (FixedConnection).
Bestätigt im Spiel: 44237, 3030 (beide Seiten), 87079, 6111 (beide Seiten), 78329 und 4162 (jeweils die genutzten Seiten).
Teilenummern und Lagen aller 17 Teile blieben unverändert. Die Verbindungen der Radhalter 30157 aus der Vorlage
hat das Spiel ebenfalls unverändert übernommen.

Bauplan: [baupläne/geom_test_1.json](../baupläne/geom_test_1.json).
Vorlage ist „Neues Fahrzeug 05“ (Alte Schule) in `ArtemisVehicle.sav`; das Ergebnis kommt auf den freien Platz 25.
Der Aufbau besteht nur aus neu eingetragenen GEOM-Teilen:

| Teil | Nummer | sitzt auf | Noppen (Builder) | Felder (Teil / Unterlage) |
|---|---|---|---|---|
| Stein 2×6 | 44237 | Chassisplatte 2445 | 12 | 1 / 1 |
| Platte 4×10, quer | 3030 | Stein 2×6 | 8 | 1 / 0 |
| Fliese 2×4, quer | 87079 | Platte 4×10 | 8 | 0 / 0 |
| Stein 1×10, quer | 6111 | Platte 4×10 | 10 | 1 / 0 |
| Platte 1×5, quer | 78329 | Platte 4×10 | 5 | 1 / 0 |
| Fliese 1×8, quer | 4162 | Stein 1×10 | 8 | 0 / 0 |

Offline geprüft: auf einer Kopie des Spielstands gebaut, kein loses Teil, die Serialisierung wurde bytegenau zurückgelesen.
Der Oberbau liegt quer zwischen den Achsen, damit die Platte 4×10 nicht in die Reifen ragt.
Kollisionen prüft der Builder nicht.

## Ablauf

1. Spiel **komplett schließen**.
2. Sichern:
   ```powershell
   python werkzeuge\sichern.py
   ```
3. Bauen und schreiben:
   ```powershell
   $s = "$env:USERPROFILE\Documents\My Games\Artemis\Saved\SaveGames\ArtemisVehicle.sav"
   python werkzeuge\baue_fahrzeug.py $s $s baupläne\geom_test_1.json --bericht .claude\geom-test-1-bericht.json
   ```
4. Spiel starten, Garage, „GEOM Test 1“ öffnen. Darauf achten:
   - Werden Teile als lose markiert, oder verweigert das Spiel das Speichern?
   - Sitzen die Teile sichtbar richtig? Erwartet: Platte quer über dem Stein, rechts der lange Stein mit der langen Fliese,
     links die kurze Fliese und die Platte 1×5.
5. Eine Kleinigkeit ändern (z. B. eine Farbe hin und zurück) und **speichern**. Beim Speichern berechnet das Spiel
   die Verbindungen neu. Danach kurz fahren.
6. Spiel schließen und Claude Bescheid geben. Claude vergleicht dann die vom Spiel gespeicherten Verbindungen mit der Tabelle oben.
   Stimmen Felder und Noppenzahlen überein, sind die neuen GEOM-Einträge im Spiel bestätigt.

Zurück geht es mit der Sicherung aus Schritt 2 (`_sicherungen\<Zeitstempel>\ArtemisVehicle.sav` zurückkopieren).

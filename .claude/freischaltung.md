# Lokale Freischaltung – 29.10.2026

## Nachtrag 21:36: Alle Bauanleitungen als abgeschlossen markiert

Der Nutzer schloss das Küstenwachen-Boot regulär ab; danach enthielt
`ArtemisVehicle.sav` erstmals `GarageInstructionCompletionMap` mit einem echten
Eintrag: Schlüssel = rohe FGuid `3678FD2D4119867D522499940DE3B887`, Wert =
`OwnerId` leer, `TimesCompleted` 1, `CompletedWithoutSkips` wahr.

`anleitungen_diagnose.py` (nur lesend) fand diese GUID als Text im
Asset-Registry-Stringpool. Im selben Abschnitt stehen genau 662 eindeutige
GUIDs, eine pro VehicleConfig (dazwischen nur Themenwerte wie City, BOAT,
Creator); 662 = Fahrzeuge im Katalog. Liste: `freischaltung/anleitungs-guids-live.json`.
Zuordnung GUID→Fahrzeugname nicht ermittelt.

`anleitungen_abschliessen.py --anwenden` kopiert den Boot-Wert bytegenau für
die 661 fehlenden GUIDs; sonst kein Feld verändert, idempotent. Sicherung:
`_sicherungen/anleitungen_2026-10-29_21-36-47/`. **Spieltest bestätigt:** Der
Nutzer meldete nach Neustart „Yes, all green“ – alle Anleitungen zeigen das
grüne Abschluss-Symbol.

## Aktueller Stand: Korrektur um 20:23

**Ursache der fehlenden Räder gefunden:** Die tatsächlich geladene
PrimaryAssetTypesToScan-Konfiguration registriert LegoWheelAssembly als
`Wheel` und LegoAssembly als `LegoAssy`. Der zuvor angenommene Freigabetyp
`LegoAssembly` ist falsch. Befund mit exakten Klassen und Verzeichnissen:
`.claude/freischaltung/assettypen-befund.json`.

`freischalten.py` korrigiert jetzt beide LockRewards-Listen: je 382 vom ersten
Versuch stammende Falschtyp-Einträge entfernt; 327 `Wheel` und 30 `LegoAssy`
eingetragen. Insbesondere ist `Wheel:Traffic_BBWheelFront_02Street` vorhanden.
Die 25 Propeller sind bis zur Klärung ihres Asset-Typs ausgenommen. Alle
ursprünglichen Freigaben, Bauteile, Fahrzeuge und Story-Felder bleiben erhalten.
Vorheriger Stand vollständig gesichert nach
`_sicherungen/freischaltung_2026-10-29_20-23-08/`.

Erneut geprüft: Original und Ergebnis bytegenau rücklesbar, idempotent,
ausschließlich zwei Freigabelisten verändert, alle ursprünglichen Freigaben
erhalten. Die entfernten Einträge waren sämtlich nicht im allerersten
Original-Backup enthalten. **Builder-Spieltest bestätigt:** Der Nutzer meldete
nach dem Neustart am 29.10.2026 ausdrücklich „Ja, jetzt verfügbar“ für das
Taxi-Rad. Damit ist Wheel:Traffic_BBWheelFront_02Street praktisch bestätigt;
die übrigen 326 Räder und 30 Baugruppen wurden nicht einzeln getestet. Auch
nach erneutem Speichern durch das Spiel blieben alle korrigierten Freigaben
erhalten; nur /Timestamp wich vom Kandidaten ab. Das Anleitungs-Abschlussfeld
wurde nicht geändert: Die direkte Rad-Freigabe genügt für dieses Sonderteil.
Die folgenden Abschnitte beschreiben auch den historischen,
fehlerhaften ersten Versuch und sind keine Behauptung, dass er funktioniert.

## Nutzerziel und bestätigter Kontext

Der Nutzer möchte lokal ohne Online-Funktionen und ohne 2K-Anmeldung spielen.
Am wichtigsten sind alle Bauteile und Fahrzeuge zur Analyse. Das ist eine
Aussage aus diesem Chat, nicht aus der Websuche. Das Spiel wurde vor dem
Schreiben auf Aufforderung regulär geschlossen (Antwort: „zu“).

## Diagnose

`DrivePass Maxer` und `werkzeuge/drivepass.py` ändern DXPList (XP), nicht die
Premium-Berechtigung. Im vorgefundenen lokalen Save fehlt UnlockedDrivePasses;
LastSeenPremiumUnlockFlags enthält vier Nullen. Das sind zuletzt angezeigte
Flags, keine selbständige autoritative Lizenzprüfung.
Der Screenshot zeigt Premium-Karten mit Schloss trotz ausreichender Stufe.

ValidatedRewards/LockRewards und LastRewardSnapshot/LockRewards enthielten je
81 Einträge mit Asset-Typ und Asset-Name. Der Save ist vollständig als GVAS
lesbar und bytegenau reproduzierbar.

## Durchgeführte Änderung

`.claude/freischalten.py --anwenden` ergänzt ausschließlich diese beiden
LockRewards-Arrays; die übrigen Bytes wurden nach Rückbau dieser zwei Felder
gegen das Original verglichen. Keine Story-, XP-, Währungs-, Konto- oder
Premium-Lizenzfelder geändert. Keine Serveranfragen durch den Freischalter.

Katalog: 2.028 LegoPart, 189 BrickPack, 662 Vehicle, 382 LegoAssembly
(30 Baugruppen + 327 Räder + 25 Propeller). Je Array 3.231 neue Einträge;
die 81 vorhandenen Einträge einschließlich Zeitstempel bleiben erhalten.
Neue Einträge kopieren die Struktur und den Zeitstempel eines vorhandenen
spielgenerierten Eintrags. Die 662 Fahrzeuge enthalten 14 laut Enzyklopädie
nicht regulär gültige Vorlagen; sie sind nicht automatisch fahrbereit.

**Unbestätigt:** LegoAssembly als gemeinsamer PrimaryAssetType für Räder und
Propeller ist aus der Klassenhierarchie und Binärstrings abgeleitet, noch
nicht durch einen erfolgreichen Garagentest bestätigt. Die Katalogeinträge
belegen Existenz der Assets, nicht ihre tatsächliche Verfügbarkeit nach Laden.
Premium-Karten im Drive-Pass-Menü können gesperrt bleiben; Ziel ist die direkte
lokale Verfügbarkeit in der Garage, keine Freigabe des Premium-Passes selbst.

Vorher vollständig gesichert nach:
`_sicherungen/freischaltung_2026-10-29_19-56-47/`
Zusätzliche automatische Writer-Sicherung unter `_sicherungen/geschrieben_...`.
Vorbereitete Kopie und Maschinenbericht: `.claude/freischaltung/`.

Prüfungen erfolgreich: Original-Rundlauf, Ergebnis-Rundlauf, alle Katalog-IDs
in beiden Listen, ausschließlich erlaubte Felder verändert, idempotentes
erneutes Anwenden, Live-Datei nach atomarem Ersetzen identisch zum Kandidaten.

Zusätzlicher Check nach Spielstart: Das Spiel hat den Save erneut geschrieben.
Ein vollständiger Property-Vergleich zur vorbereiteten Kopie ergibt nur eine
Änderung an `/Timestamp`; beide Freigabelisten und sämtliche 3.261 Ziel-IDs
blieben erhalten (3312 Einträge je Liste einschließlich zuvor vorhandener
anderer Inhalte). Damit ist Laden und erneutes Speichern bestätigt, die
sichtbare/benutzbare Verfügbarkeit im Garagenmenü jedoch weiterhin offen.

## Noch offener Spieltest

**Neue Nutzerrückmeldung:** Das Taxi-Rad ist im normalen Builder weiterhin
nicht verfügbar. Die bloße Existenz von `LegoAssembly:Traffic_BBWheelFront_02Street`
in den beiden LockRewards-Listen genügt somit nachweislich nicht. Diese
Zuordnung nicht länger als erfolgreiche Rad-Freigabe darstellen. Der Nutzer
möchte eine allgemeine Lösung für alle Modelle, das Vintage-Taxi ist nur ein
Beispiel. Im nach regulärem Verlassen gespeicherten ArtemisVehicle.sav fehlen
GarageInstructionCompletionMap und CurrentStepNumber weiterhin vollständig.

Lesend ermittelte Reflexionsmetadaten der installierten Spielversion:
GarageInstructionCompletionMap hat Struct-Schlüssel (Guid-Konstruktor identisch
mit InstructionsGuid) und Struct-Werte; GarageInstructionCompletionData nennt
die Felder TimesCompleted und CompletedWithoutSkips. Die GUIDs der einzelnen
Anleitungen sind bisher nicht bekannt. Keine erfundenen GUIDs eintragen.
Das aktive Taxi referenzierte die Radbaugruppe Traffic_BBWheelFront_02Street.

Der öffentliche „Instruction Finisher“ setzt lediglich vorhandene
CurrentStepNumber-Felder auf den daneben gespeicherten MaxStepNumber-Wert.
Er erstellt weder alle Anleitungen noch deren Abschlussdaten.

Spiel nach Änderung gestartet. Computer-Use-Erfassung scheiterte nach erneutem
Binden des Spielfensters mit `window capture timed out: timed out waiting on
channel`; keine visuellen Ergebnisse behaupten. Der Nutzer wurde gebeten,
Sammlung/Fahrzeuge sowie Teile 3956 und 2817 in der Garage zu prüfen.
Nach positiver Rückmeldung hier ergänzen; bei Problemen nicht blind erneut
schreiben. Erst Spiel schließen, aktualisierten Save vergleichen und ggf.
Originaldatei aus der oben genannten Sicherung wiederherstellen.

## Quellen, öffentlich und getrennt vom Nutzerkontext

- https://github.com/2KDriveTools/2KDriveTools.github.io/blob/main/DrivePass/drivepass.js
  (XP-Änderung und Lesen vorhandener Premium-Flags)
- https://github.com/2KDriveTools/2KDriveTools.github.io/blob/main/Unlocker/Parts/minifig.js
  (lokale Freigaben als PrimaryAssetType/PrimaryAssetName)
- https://github.com/r0levrai/l2kd-encyclopedia/blob/main/data/dump_infos.py
  (Katalog-Export, entfernte Präfixe, Asset-Klassen)
- https://r0levrai.github.io/l2kd-encyclopedia/data/bricks_by_id.json
- https://r0levrai.github.io/l2kd-encyclopedia/data/brickpacks_by_id.json
- https://r0levrai.github.io/l2kd-encyclopedia/data/vehicles_by_id.json
- Entsprechende assemblies/wheels/propellers-Kataloge im selben Verzeichnis.

Die heruntergeladenen Quellen liegen unter `.claude/quellen/` und wurden
als Daten gelesen, nicht ausgeführt. Der Freischalter lädt nichts herunter.

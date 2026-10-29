# Übergabe: Alle übrigen Bauteile lokal freischalten

Stand: 29.10.2026, nach erfolgreicher Rad-Korrektur um 20:23 Uhr, Europe/Berlin.
Diese Datei ist die kompakte Übergabe an einen anderen Chat. Sie trennt
Spieltests, technische Nachweise und offene Annahmen. Die ausführliche
`freischaltung.md` enthält auch überholte Versuche; deren alte Aussagen nicht
mit dem aktuellen Stand verwechseln.

## Auftrag und Nutzerkontext

- Alle Bauteile und Fahrzeuge sollen zum Bauen und Analysieren verfügbar sein.
- Nur lokal spielen, ohne Online-Funktionen und ohne 2K-Anmeldung.
- Sonderteile sollen nicht durch hunderte einzelne Bauanleitungen erarbeitet
  werden müssen. Das Vintage-Taxi war ausdrücklich nur ein Beispiel.
- Der Nutzer hat diesen Chat jetzt beauftragt, das Wissen zu dokumentieren;
  die weitere Freischaltung soll ein anderer Chat übernehmen.
- Projekterinnerungen und KI-Informationen gehören in `.claude/`.
- Diese Angaben stammen aus diesem Chat, nicht aus Foren oder Websuche.

## Der entscheidende, praktisch bestätigte Befund

**C++-Klassenname ist nicht gleich PrimaryAssetType.** Der erste Versuch
verwendete für Räder und Baugruppen den geratenen Typ `LegoAssembly`. Das
Spiel behielt diese Einträge zwar beim Speichern, das Taxi-Rad blieb im
normalen Builder aber gesperrt. Ein erfolgreicher Datei-Rundlauf oder ein
persistierter Eintrag beweist daher keine tatsächliche Freischaltung.

Danach wurden die `PrimaryAssetTypesToScan`-Zeilen aus der tatsächlich
geladenen Spielkonfiguration ausschließlich lesend ermittelt:

| Klasse | Richtiger PrimaryAssetType | Konfiguriertes Verzeichnis |
|---|---|---|
| `/Script/ArtemisLego.LegoWheelAssembly` | `Wheel` | `/Game/LEGO/Wheel` |
| `/Script/ArtemisLego.LegoAssembly` | `LegoAssy` | `/Game/LEGO/Assemblies` |
| `/Script/ArtemisLego.LegoPart` | `LegoPart` | `/Game/LEGO/Bricks` |
| `/Script/Artemis.BrickPack` | `BrickPack` | `/Game/LEGO/BrickPacks` |
| `/Script/Artemis.VehicleConfig` | `Vehicle` | `/Game/Game/Vehicle/Configs` |
| `/Script/Artemis.ChassisConfig` | `Chassis` | `/Game/Game/Vehicle/Inventory/BoatChassisConfigs` und `CarChassisConfigs` |

Beleg: `freischaltung/assettypen-befund.json` relativ zu dieser Datei.

Das Beispielrad ist **`Wheel:Traffic_BBWheelFront_02Street`** vom
**Vintage-Taxi / `VintageTaxi_40532`**. Das ist eine interne Radbaugruppen-ID,
keine numerische LEGO-Teilenummer. Die einzelnen Felgen-/Reifennummern sind
hier nicht verifiziert.

Nach Ersetzen des falschen Typs durch `Wheel` meldete der Nutzer ausdrücklich:
**„Ja, jetzt verfügbar“** im freien Builder. Es wurde dafür **keine**
Bauanleitung abgeschlossen und kein Anleitungs-Abschlussfeld geändert.
Damit funktioniert der direkte lokale Inventareintrag zumindest für dieses
Anleitungs-Sonderteil. Das ist der Ansatz für die übrigen Kategorien.

## Nachtrag 29.10.2026, ca. 20:45: Chassis, Flairs, Sticker belegt

- `assettypen_diagnose.py` lief in der UTF-8-Fassung vollständig (20 Typzeilen,
  `freischaltung/assettypen-live.json`). Für `/Game/LEGO/Propeller` und
  `/Game/LEGO/Decorations` ist **kein** PrimaryAssetType konfiguriert. Propeller
  und fahrzeugspezifische Aufkleber/Atlanten sind damit keine Inventarfreigaben
  und werden nicht eingetragen. `LegoDeco` umfasst nur
  `/Game/Garage/LegoAssets/Stickers` und `/Game/Game/Art/Props/Stickers`.
- Der Pak-Index des Spiels ist AES-verschlüsselt; er wird nicht entschlüsselt.
- Neu: `assetnamen_diagnose.py` (nur lesend) sammelt Paketnamen der
  Typverzeichnisse aus dem laufenden Spiel → `freischaltung/assetnamen-live.json`.
  Gegenprobe: Räder 327/327, Baugruppen 30/30, Propeller 25/25 im Katalog gefunden.
- Neu: `assetnamen_belegen.py` gleicht Katalog und Live-Pakete ab →
  `freischaltung/assetnamen-belegt.json`: **Chassis 775, Flair 548, LegoDeco 546**
  in Original-Schreibweise. Alle 16 Flairs und 7 Sticker, die der Nutzer
  regulär besaß, stehen darin. Nicht gefunden: Flairs `mowerblades` und `Spoiler_Flair3`.
- `freischalten.py` liest diese Belegdatei. Der Probelauf an einer Kopie ergab
  +1846 Einträge pro Liste; alle Prüfungen bestanden. **Noch nicht live
  angewendet** (das Spiel lief). Den alten Bericht sichert
  `freischaltung/bericht-2026-10-29_20-23-rad-korrektur.json`.
- **20:43 live angewendet** (Spiel geschlossen). Sicherung:
  `_sicherungen/freischaltung_2026-10-29_20-43-31/`. Danach stehen in beiden
  Listen Chassis 775, Flair 548, LegoDeco 546; ein Kontrolllauf ergab 0
  Ergänzungen. Im Builder noch nicht geprüft. Zuvor scheiterte `game_running()`
  an der OEM-kodierten deutschen `tasklist`-Meldung; behoben, nichts geschrieben.
- Nutzer-Stichprobe nach Neustart: „keine Sonderteile mehr verfügbar zum
  Freischalten“. Damit ist die Bauteil-Freischaltung abgeschlossen, soweit sie
  technisch möglich ist (Stichprobe, kein Einzeltest). Offen und optional, weil
  es keine Bauteile sind: Hupen, Motorklänge, Minifiguren, Perks.
- Motor- und Hupenklänge sind keine Bauteile und werden in dieser Runde nicht
  freigeschaltet. Strenge Objektpfade belegen nur einen Teil der Hupen (z. B.
  fehlt `Horn_Test_Asset2_5`) und keinen Motor.
- Nutzerbeobachtung nach Neustart: „extrem viele neue Teile“ im Builder.
  Das bestätigt die Masse der LegoPart-/Rad-Freigaben, ist aber kein Einzeltest.

## Was aktuell eingetragen ist – und was tatsächlich getestet wurde

In `ArtemisPlayerInfo.sav` stehen nach der Korrektur folgende Zielbestände:

| Kategorie | Einträge | Status |
|---|---:|---|
| `LegoPart` | 2028 | Alle Katalog-IDs eingetragen; nicht einzeln im Builder getestet. Laut Katalog sind darunter 515 Surplus-Teile. |
| `BrickPack` | 189 | Eingetragen; nicht alle einzeln im Spiel geprüft. |
| `Vehicle` | 662 | Eingetragen; 14 Vorlagen sind laut Katalog nicht regulär gültig. Nicht alle einzeln getestet. |
| `Wheel` | 327 | Alle eingetragen; Taxi-Rad als Funktionsnachweis vom Nutzer bestätigt. Weitere 326 nicht einzeln getestet. |
| `LegoAssy` | 30 | Mit belegtem Typ eingetragen; noch kein eigener Builder-Test. |
| Propeller | 25 | **Ausgenommen. PrimaryAssetType noch ungeklärt.** Nicht aus Vererbung oder Klassennamen raten. |
| Chassis | Katalog: 775 | Typ `Chassis` ist belegt, aber die 775 Chassis wurden bisher nicht als eigene Inventarfreigaben ergänzt. Fahrzeuge können Chassis enthalten; das ist kein vollständiger Chassis-Test. |
| Flairs | Katalog: 550 | Nur zuvor vorhandene Freigaben erhalten; keine vollständige Freischaltung durchgeführt. |
| Sticker | Katalog: 736 | Nur zuvor vorhandene Freigaben erhalten; keine vollständige Freischaltung durchgeführt. |

Außerdem wurden bei der Laufzeitdiagnose folgende Typzuordnungen als
Konfigurationszeilen gesehen: `Flair` → LegoFlairAssembly, `LegoDeco` →
LegoDecoration, `EngineSound` → EngineConfig, `HornSound` → HornConfig,
`Minifig` → Minifig und `Perk` → SpellSystemPerkData. Das sind Nachweise für
die **Typnamen**, keine Aussage, dass alle zugehörigen IDs rekonstruiert,
freigeschaltet oder im Spiel getestet wurden. Die kompakte JSON-Belegdatei
speichert bisher nur die sechs Typen der obigen Tabelle.

Bei der Rad-Korrektur wurden pro Freigabeliste 382 falsche `LegoAssembly`-
Einträge aus unserem ersten Versuch entfernt und 327 `Wheel` + 30 `LegoAssy`
eingetragen. Die 25 unbelegten Propeller-Einträge wurden nicht übernommen.
Der Abgleich mit dem allerersten Backup bestätigte: Keiner der entfernten
Einträge gehörte zu den ursprünglichen Freigaben des Nutzers.

## Speicherformat und vorhandenes Werkzeug

Live-Spielstände:

```text
%USERPROFILE%\Documents\My Games\Artemis\Saved\SaveGames\
```

Die Freischaltung erfolgt in **`ArtemisPlayerInfo.sav`**, einer unverschlüsselten
GVAS-Datei. Bearbeitet wurden ausschließlich diese beiden Arrays:

```text
Data/LocalProgression/ValidatedRewards/LockRewards
Data/PlayerCompletionState/LastRewardSnapshot/LockRewards
```

Beide sind Struct-Arrays mit Elementtyp `LockRewardEntry`. Ein Eintrag enthält:

```text
LockRewardAsset : PrimaryAssetId
  PrimaryAssetType : PrimaryAssetType
    Name : NameProperty              # z.B. Wheel
  PrimaryAssetName : NameProperty     # z.B. Traffic_BBWheelFront_02Street
UnlockTimeStamp : DateTime            # 8 Bytes
```

Neue Einträge kopieren Struktur und Zeitstempel eines vorhandenen,
spielgenerierten Eintrags. Asset-Typ und Asset-Name werden anschließend
ersetzt. Bestehende legitime Einträge bleiben erhalten, Duplikate werden
vermieden. Beide Arrays wurden synchron ergänzt.

Werkzeuge und Belege:

- `.claude/freischalten.py`: aktueller Freischalter. `catalog()` erweitern,
  nachdem Typ und Original-Asset-Name nachgewiesen sind.
- `.claude/freischaltung/bericht.json`: Ergebnis, Sicherungsort und genauer
  Umfang der Nutzerbestätigung. Wird durch einen erneuten Skriptlauf ersetzt;
  bestätigte Befunde vorher erhalten.
- `.claude/freischaltung/assettypen-befund.json`: belegte Typzuordnungen.
- `.claude/freischaltung/ArtemisPlayerInfo.sav`: zuletzt vorbereitete Kopie,
  **nicht** automatisch der inzwischen neueste Live-Spielstand.
- `werkzeuge/gvas_rw.py`: vorhandener Reader/Writer mit atomarem Ersetzen,
  Quell-Snapshot-Prüfung, Rückleseprüfung und zusätzlicher Sicherung.

Vom Projektverzeichnis aus:

```powershell
# Erstellt und prüft eine Kopie und einen Bericht, ändert den Live-Save nicht.
python -B .claude/freischalten.py

# Erst nach regulärem Beenden des Spiels; sichert vorher alle Spielstände.
python -B .claude/freischalten.py --anwenden
```

Das Skript selbst stellt keine Serveranfragen und verändert keine Story-,
XP-, Währungs-, Konto- oder Premium-Lizenzfelder. `obsolete_ids()` ist die
gezielte Bereinigung unseres ersten Falschtyp-Versuchs; diese Funktion nicht
pauschal auf andere Kategorien ausweiten.

## Asset-Typen erneut nachweisen

`.claude/assettypen_diagnose.py` liest ausschließlich aus dem laufenden
Spielprozess (`PROCESS_QUERY_INFORMATION | PROCESS_VM_READ`). Es sucht
gezielt Konfigurationszeilen mit `PrimaryAssetType=` und `AssetBaseClass=`.
Keine Injektion, keine Prozessspeicheränderung, kein vollständiger RAM-Dump.
Nur den tatsächlichen LEGO-Spielprozess auswählen:

```powershell
$taskGame = Get-Process -Name 'LEGO2KDrive-Win64-Shipping' -ErrorAction Stop
python -B .claude/assettypen_diagnose.py $taskGame.Id
```

Nicht eine frühere PID wiederverwenden. Das Spiel muss für diese **lesende**
Diagnose laufen, für spätere Save-Änderungen jedoch geschlossen sein. Die
erste Diagnose lieferte die benötigten Typzeilen und brach anschließend bei
einer anderen Zeichenfolge mit einem Konsolen-Encodingfehler ab. Das Skript
wurde danach auf UTF-8 und gefilterte JSON-Ausgabe umgestellt; dieser
überarbeitete vollständige Lauf wurde noch nicht erneut getestet.
Bei Erfolg schreibt er `.claude/freischaltung/assettypen-live.json`.

Ein normaler Start über Steam funktionierte zuverlässig:

```powershell
Start-Process -FilePath 'steam://rungameid/1451810' -WindowStyle Hidden
```

Direkte EXE-Starts aus der Shell blieben in dieser Sitzung nicht dauerhaft
aktiv; die Ursache ist nicht geklärt. Diagnose-Startparameter wie `-log` und
`-ExecCmds` ergaben keine nutzbare Logdatei. Diese erfolglosen Ansätze nicht
als funktionierende Diagnose beschreiben. Die Computer-Use-Bilderfassung
scheiterte nach erneutem Binden mit `window capture timed out`; der erfolgreiche
Builder-Test stammt vom Nutzer, nicht von eigener visueller Kontrolle.

## Kataloge, Namen und typische Fehlerquellen

Die öffentlichen Katalogdaten liegen lokal unter:

```text
.claude/quellen/l2kd-encyclopedia/*_by_id.json
.claude/quellen/l2kd-encyclopedia/dump_infos.py
```

Die Daten stammen aus der Fan-Enzyklopädie, nicht aus der persönlichen
Spielhistorie des Nutzers. Sie belegen die katalogisierten Assets, aber nicht
deren Erwerb oder vollständige Benutzbarkeit in diesem Spielstand.

**Export-IDs können gekürzt oder für die Website umgeformt sein.** Vor einer
neuen Kategorie unbedingt `dump_infos.py` und vorhandene Ingame-Referenzen
abgleichen:

- Brickpacks verlieren häufig den Präfix `Brickpack_`; `DefaultBrickPack` ist
  eine bekannte Ausnahme. Das berücksichtigt der aktuelle Freischalter.
- Chassis-IDs können den Dateipräfix `ChassisConfig_` verloren haben. Typ
  `Chassis` ist belegt, eine pauschale Namensrekonstruktion ist noch kein
  vollständiger Nachweis für jedes Asset.
- Flairs verlieren im Export häufig `Flair_`; nicht jeder Originalname hat
  denselben Präfix. Quellen und vorhandene Freigaben abgleichen.
- Sticker können `StickerGarage_` oder `Deco_` verloren haben; bei Bildatlanten
  wurden außerdem Website-IDs mit `/` erzeugt. Solche Website-IDs nicht
  ungeprüft als PrimaryAssetName eintragen.
- Teile-Aliase und tatsächliche Primär-Asset-Namen auseinanderhalten.
- Ein Asset ohne Icon/Bezugsquelle kann eine ungenutzte oder interne Vorlage
  sein. Seine Katalogexistenz beweist nicht, dass es regulär im Builder wählbar ist.

## Bauanleitungen und Drive Pass

Die direkte, korrekt typisierte Radfreigabe funktionierte ohne Durchspielen
der Anleitung. Deshalb für übrige Teile zuerst denselben Inventarweg prüfen.
Ein Schloss im Anleitungsmenü allein ist kein ausreichender Builder-Test.

`GarageInstructionCompletionMap` ist ein separates Feld in
`ArtemisVehicle.sav`. Lesende Reflexionsanalyse ergab Guid-Schlüssel und
Struct-Werte; `GarageInstructionCompletionData` nennt `TimesCompleted` und
`CompletedWithoutSkips`. Die GUIDs aller Anleitungen sind bisher unbekannt;
**keine erfundenen GUIDs oder ungeprüften Abschluss-Maps schreiben**.
Im zuletzt untersuchten Nutzer-Save fehlten diese Map und `CurrentStepNumber`.

Der öffentliche „Instruction Finisher“ setzt nur vorhandene
`CurrentStepNumber`-Werte auf den gespeicherten `MaxStepNumber`. Er legt nicht
automatisch alle Anleitungen an und belegt keine vollständige Freischaltung
aller Sonderteil-Belohnungen.

`DrivePass Maxer` / `werkzeuge/drivepass.py` ändern nur DXPList (XP).
Level 99 ist keine Premium-Lizenz. Premium-Menükarten können gesperrt bleiben,
obwohl Inhalte direkt im lokalen Inventar freigeschaltet sind. Das bestätigte
Ziel ist Verfügbarkeit im Builder, nicht die Premium-Anzeige.

## Vorgehen für den übernehmenden Chat

1. Aktuelle Dateien und Live-Save erneut lesen; andere Chats arbeiten ebenfalls
   im Projekt. Keine fremden Änderungen zurücksetzen. Diese Übergabe ist ein
   Standbericht, kein Ersatz für die Prüfung des aktuellen Zustands.
2. Mit den 25 Propellern und den sonst noch fehlenden Bauteil-Kategorien
   fortfahren. Typ und tatsächlichen Asset-Namen nachweisen. Chassis und
   Baugruppen im Builder exemplarisch prüfen; die Tabelle oben zeigt die Lücken.
3. Vor Live-Änderungen Spiel regulär schließen lassen und den aktuellen
   Spielstand komplett sichern. Aus dem neuesten Live-Save arbeiten, keine
   ältere vorbereitete Kopie blind zurückkopieren.
4. Katalog-Erweiterung zunächst an einer Kopie prüfen: Original-Rundlauf und
   Ergebnis-Rundlauf bytegenau, idempotent, bestehende Freigaben erhalten,
   ausschließlich die vorgesehenen Felder geändert.
5. Nach Einsetzen neu starten, mindestens einen konkreten Vertreter je neuem
   Typ im normalen Builder prüfen und danach erneut speichern lassen. Die
   Sichtprüfung getrennt von der bloßen Eintrags-/Persistenzprüfung dokumentieren.
6. Nicht behaupten, sämtliche Inhalte seien getestet: bisher wurde nur das
   konkrete Taxi-Rad nach Korrektur vom Nutzer als verfügbar bestätigt.

## Sicherungen und Rückweg

Alle Ordner sind relativ zum Projekt:

- `_sicherungen/freischaltung_2026-10-29_19-56-47/`: Zustand vor unserem ersten
  Inventar-Freischaltversuch.
- `_sicherungen/freischaltung_2026-10-29_20-23-08/`: Zustand direkt vor der
  erfolgreichen Rad-Typkorrektur; enthält noch die falschen LegoAssembly-Einträge.
- Weitere `_sicherungen/geschrieben_...` wurden durch den Writer erstellt.

Bei Problemen erst Spiel schließen und die benötigte Datei gezielt aus der
passenden Sicherung wiederherstellen. Ein kompletter Rollback kann spätere
Nutzerfortschritte entfernen; deshalb nicht unaufgefordert ganze Save-Ordner
über einen neueren Stand kopieren. Spielstände enthalten Creator-/Spieler-IDs;
für die Übergabe genügt diese Dokumentation, keine Saves veröffentlichen.

## Öffentliche Quellen

- https://github.com/2KDriveTools/2KDriveTools.github.io/blob/main/DrivePass/drivepass.js
- https://github.com/2KDriveTools/2KDriveTools.github.io/blob/main/Unlocker/Parts/minifig.js
- https://github.com/2KDriveTools/2KDriveTools.github.io/blob/main/Unlocker/Instructions/instructions.js
- https://github.com/r0levrai/l2kd-encyclopedia/blob/main/data/dump_infos.py
- https://r0levrai.github.io/l2kd-encyclopedia/

Ein Versuch, einen öffentlich verlinkten Vergleichs-Save von GBAtemp zu laden,
scheiterte an einer Zugriffsschutzseite. Es wurde kein fremder Save übernommen.
Für die erfolgreiche Korrektur war dieser Vergleich nicht erforderlich.

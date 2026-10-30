# Emerald Express (31015) nach Anleitung 6071644 – Analyse und Bauplan

**Nachtrag 30.10.2026:** Die folgenden Aussagen „2436b nicht im Spiel“ und „61252 nicht im Spiel“ sind überholt beziehungsweise zu pauschal: Spiel-ID 2436 und Teil 61252 sind in Katalog und Referenzfahrzeugen belegt. Die genaue Buchstabenvariante 2436b benötigt einen eigenen Formabgleich. Insbesondere 61252 an 2540 ist bereits im Space Rover Explorer gespeichert. Allgemeine Wiederverwendung und korrigierte Prüfung: [Teilewissen](../teilewissen/README.md). Der bestehende Emerald-Plan beschreibt die vom Nutzer manuell verbesserte Referenz; er wurde für diese Änderung nicht umgebaut.

Stand 29.10.2026. Quelle: https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6071644.pdf
(32 Seiten, InDesign-Titel „31015_BI“). Nachgebaut wird nur das **Hauptmodell, Schritte 1–13 (S. 2–13)**.
Ab S. 14 folgen laut Nutzer andere Modelle; sie gehören nicht dazu.

**Status:** Erste Fassung am 29.10.2026 auf Platz 45 geschrieben; das Spiel hat sie geladen. Der Nutzer hat Führerhaus
und Front im Spiel nach Anleitung korrigiert und gespeichert (Version 2, 51 Teile). `baupläne/emerald_express.json`
reproduziert diese gespeicherte Fassung jetzt **exakt**: alle 51 Teillagen und alle 54 Verbindungen
(Feld, Stärke, Typ) stimmen mit der vom Spiel berechneten Fassung überein.

## Gelernt aus der Korrektur im Spiel (29.10.2026)

| Bereich | Erste Fassung (Claude) | Korrigiert (Nutzer, vom Spiel gespeichert) |
|---|---|---|
| Führerhaus | Dach 1 Noppe nach vorn überstehend | Dach 1 Noppe nach **hinten** überstehend (x −162,5…−87,5) |
| Kessel | 3956 hinten, beide 6143 davor | 3956 **in der Mitte**: 6143 hinten (über f2), 6143 vorn (auf f0); hinten 63082 + 4032 grün als Abschluss |
| Ring vorn | zweiter 3956 kopfüber als Ring + Sattel | wie im Set: **3023 + 2540 senkrecht** (je 2 Noppen auf 6143 f2), Jumper darauf |
| Schornstein | Kegel in kopfüber gesetztem Jumper | wie im Set: **Clip 6019 f2 an Griffstange 2540 f4** (CylindricalConnection), Kegel 3942 f2 an 6019 f1, Fliese 3070 an 6019 f0 |
| Front | Fliese 3068 auf Pufferbohle, Kesselbett 3021, Knöpfe 6141 | 3068 **vor der Rauchkammer** (x 0…50); kein Kesselbett; **Dampfzylinder**: 4081 zwischen Chassisplatte (f1↔2445 f1) und Rahmen (f0↔3795 f1), 6141 am Lampenclip (f4 bzw. f3) |

Neue belegte Feldbedeutungen: 2540 f1 Unterseite, f0 Noppen, f4 Griffstange · 6019 f2 Clip, f1 Unterseite, f0 Noppe ·
63082 f0 Noppen, f1 Unterseite · 4081 f0 Noppe, f1 Unterseite, f3/f4 Lampenclips · 87580 auch mit Drehung (H,0,H,0) gültig.
Lehre: Bei den Set-Techniken (Clip am Griff) lieber die Originaltechnik nachbauen als eine Ersatzlösung erfinden;
der Nutzer korrigiert im Spiel, danach den gespeicherten Stand auslesen und den Generator daran angleichen.

## Aufbau der Anleitung (Hauptmodell)

| Seiten | Schritte | Baugruppe |
|---|---|---|
| 2–3 | 1–5 | Vorderteil: 4600 (Radhalter) + 3021 DBG, Winkel 2436b, Kleinräder 4624, Räumer aus 2× 61409 |
| 4 | 1–2, 6 | Rahmen: 3795 DBG + 15456 (Kugel), 3795 LBG, Fliese 3068 schwarz; Vorderteil darunter |
| 5 | 7–9 | Radaufhängung 2× 2817, Pins 3673, vier Zugräder 13971 |
| 6–7 | 1–4, 10 | Führerhaus: Boden 3020 + 3710 (3×4), rote 3623, Fenster 3065, Pfosten 3005, Dach 2× 88930 |
| 8–11 | 1–6, 11 | Kessel stehend gebaut, dann liegend montiert: 3956 – 3941 – 3941 – schwarze Platte mit Griff – roter Jumper 87580 – Schüssel 4740 – Lampe 98138 |
| 12–13 | 1–2, 12–13 | Schornstein: Kegel 3942 kopfüber mit Clip 61252 am Griff 2540, hochgeklappt |

## Umsetzung im Spiel

- **Chassis:** unverändertes Startchassis „Alte Schule“ (`FireEngine_10263`: Platte 2445 2×12 – wie der 2 Noppen breite
  Lok-Rahmen –, zwei Radhalter 30157, Räder 56902 + Reifen 61254 Ø24 mm ≈ Zugradgröße). Vorlage aus
  `_sicherungen/geschrieben_2026-10-29_21-17-19_9935dab8/ArtemisVehicle.sav` („Neues Fahrzeug 05“, nur lokal).
- **Rahmen zweilagig** wie im Original (DBG/LBG 2×6). Führerhaus eine Platte höher (Boden z = 50), weil die
  Reifen bis z = 45,6 reichen.
- **Kessel, Schornstein, Front:** siehe Tabelle „Gelernt aus der Korrektur im Spiel“ (aktueller Stand).

## Teile ohne Spielentsprechung oder bewusst ausgelassen

| Set-Teil | Grund | Lösung |
|---|---|---|
| 3065 Fenster | nicht im Spiel | 3004 Trans-Klar |
| 4600, 4624, 2817, 3673, 13971 | Fahrwerk; Räder kommen als Baugruppe vom Chassis | entfällt |
| 2436b, 61409 | 2436b nicht im Spiel, Lage von 61409 unbelegt | Räumer aus 3040 |
| 15456 Kugelkupplung | Geometrie unbekannt | entfällt |
| 61252 | nicht im Spiel | 6019 (Clip) am Griff 2540 |

## Belege für explizite Anschlüsse

Alle expliziten Anschlüsse im Bauplan sind die vom Spiel gespeicherten der korrigierten Fassung (Platz 45, Version 2).
Vergleich Builder ↔ Spielstand: 54/54 Verbindungen identisch.

## Offen / im Spiel prüfen

- Fahrverhalten.
- Farbe 12 für Dark Bluish Gray ist vermutet.
- Kein Fahrer-Sitz (Vorlage hat keinen Socket), `GarageSaveDataMap` unverändert.

## Werkzeuge

```powershell
python .claude/emerald-express/erzeuge_bauplan.py werkzeuge baupläne/emerald_express.json
python werkzeuge/baue_fahrzeug.py "$env:USERPROFILE\Documents\My Games\Artemis\Saved\SaveGames\ArtemisVehicle.sav" ergebnis.sav baupläne/emerald_express.json --pruefen
python .claude/emerald-express/vorschau.py werkzeuge baupläne/emerald_express.json baupläne/emerald_express_vorschau.html
```
Zum echten Schreiben: Spiel schließen, `python werkzeuge/sichern.py`, dann den Builder ohne `--pruefen` im Projektordner ausführen.

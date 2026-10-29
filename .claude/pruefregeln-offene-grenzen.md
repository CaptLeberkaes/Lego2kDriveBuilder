# Einordnung der vom Nutzer gezeigten Bauregeln

Stand: 29.10.2026. Quelle: vom Nutzer beigefügter Screenshot; die darin eingeblendeten Videoverweise wurden ohne konkrete URLs nicht als eigenständig geprüfte Belege übernommen.

- **Konnektivität:** Der Builder prüft einen vollständigen Pfad jedes normalen Teils zum Chassis. Das ist nicht gleichbedeutend mit einer notwendigen Befestigung ausschließlich auf einem darunterliegenden Stein. Die eigenen Download-Daten belegen liegende Teile, Seitenanschlüsse und weitere Verbindungstypen. Die erste Karosserieposition in der JSON-Liste muss nicht selbst direkt am Chassis sitzen; entscheidend ist der fertige Graph.
- **Koordinaten:** Im Projekt ist Z die Höhe. Eine Noppe entspricht 25 Spieleinheiten, nicht 25 LDU; LDraw verwendet dafür 20 LDU. Die Ausrichtung zweier Anschlussflächen muss in einem gemeinsamen, korrekt transformierten Koordinatensystem geprüft werden. Keine pauschale globale Rasterrundung bei versetzten oder gedrehten Teilen.
- **Kollisionen:** Eine Überschneidung einfacher umschließender Boxen beweist bei Bögen, Hohlräumen, Kotflügeln und ähnlichen Formen noch keine Materialdurchdringung. Eine harte allgemeine AABB-Sperre wäre daher keine vollständige Kollisionsprüfung. Diese Prüfung bleibt als eigener Arbeitsschritt offen; der derzeitige Verbindungstest garantiert keine kollisionsfreie physische Konstruktion.
- **350 Teile:** Der Screenshot nennt diese Grenze, und die größten ausgewerteten eigenen Download-Beispiele haben 350 Teile. Eine Quellenrecherche hat in der geprüften offiziellen Garagen-Hilfe keine Bestätigung für eine universelle harte Engine-/GVAS-Grenze geliefert. Der Screenshot und beobachtete Maximalwerte allein reichen nicht, um solch eine Behauptung zu verifizieren. 350 kann als vorsichtiges Planungsbudget dienen. Wie Chassis, Rad-Baugruppen und Flairs gezählt werden und wie das Spiel einen Spielstand mit mehr Teilen behandelt, muss gesondert geprüft werden. Der technische UInt16-Indexbereich des Dateiformats ist kein Nachweis für das im Garagenmenü zulässige Baulimit.

Geprüfte offizielle Garagen-Hilfe: https://support.2k.com/hc/en-us/articles/16042200974739-LEGO-2K-Drive-Going-Into-the-Garage

Keine zusätzliche harte Sperre wurde nur auf Grundlage des Screenshots eingebaut.

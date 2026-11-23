# Küche lesen und zeichnen

Gilt zusätzlich zu `regeln.md`, für Küchenumbauten und für jede Küche in einer Gesamtrenovation.

## Neue Küche: einzelne Elemente aus dem Bauteilkatalog

Die neue Küche zeichnest du **Element für Element**, nicht als einen Block. Jedes Element bekommt
einen `artikel` aus `bauteile-kueche.json` (liegt neben dieser Datei). Der Artikel setzt Typ,
Breite, Tiefe, Höhe, Montagehöhe und eingebaute Geräte; du gibst nur Lage, Rotation und Status an:

```json
{ "artikel": "KU-US-060", "position": [165, 315], "rotation": 180, "status": "neu" }
```

- **Nur IDs aus `bauteile-kueche.json`.** Unbekannte IDs lehnt das Skript ab. Gibt es eine Breite
  nicht (z.B. 70 cm), nimm die nächste passende, trag die Abweichung in `angenommen` ein und nenne sie.
- Typen: `unterschrank` (89 cm inkl. Sockel, Arbeitsplatte 4 cm zeichnet das Skript dazu),
  `hochschrank` (209 cm), `oberschrank` (63 cm hoch, Unterkante 146 cm, Oberkante bündig mit
  dem Hochschrank). Oberschränke liegen im Grundriss über den Unterschränken: gleiche Lage
  entlang der Wand, `position` aber 12.5 cm näher an der Wand (Tiefe 35 statt 60).
- Geräte sind **eingebaut**, keine eigenen Objekte: `einbau` mit `spuele`, `kochfeld`, `backofen`,
  `steamer`, `geschirrspueler`, `kuehlschrank`, `dampfabzug`, `muldenlueftung`. Die passenden
  Schränke haben es schon (Spülen-Unterschrank → `spuele`, Geschirrspüler-Front →
  `geschirrspueler`, Geräte-Hochschrank → `kuehlschrank`/`backofen`, Dunsthauben-Oberschrank →
  `dampfabzug`). Kochfeld über einem normalen Unterschrank: dort `"einbau": ["kochfeld"]`.
- Reihenfolge und Lage kommen von der Skizze. Die Breiten der Elemente einer Zeile ergeben
  zusammen die Länge der Zeile; ein Rest bis zur Wand ist eine Passleiste (nicht zeichnen,
  in der Rückmeldung nennen). Ecken: Eck-Unterschrank (`KU-EU-…`), wenn die Skizze nichts anderes zeigt; in `angenommen` eintragen.
- Masse aus der Skizze gehen vor: Steht auf der Skizze eine Zeile von 3.20 m, müssen die
  Elemente 3.20 m ergeben. Stimmt es nicht auf, gleiche mit einer Passleiste aus, trag das in
  `angenommen` ein und frag mit dem Entwurf nach.

## Bestehende Küche

Die alte Küche zeichnest du als Block `kueche` (eine Zeile = ein Objekt) mit `abbruch`, wenn sie
ganz wegkommt, oder mit `bestand`, wenn sie bleibt. Elemente einzeln nur, wenn einzelne bleiben.

## Symbole und Kürzel auf Skizzen

KS (Kühlschrank), GS/GWM (Geschirrspüler), BO/Herd (Backofen), KF (Kochfeld), DA/DAH
(Dampfabzug), HS (Hochschrank), OS/OK (Oberschrank), US (Unterschrank), Spüle als Rechteck mit
Kreis. Ein Rechteck von etwa 60 cm Tiefe entlang einer Wand ist eine Küchenzeile, eine Insel
davor ebenfalls (Elemente mit Rotation zur Bedienseite).

## Was entsteht

- Grundriss: Unter- und Hochschränke mit Spüle, Kochfeld und Kürzeln (KS, BO, GS), Hochschränke
  gekreuzt, Oberschränke gestrichelt.
- Wandansichten A–D der Küche: Fronten mit Sockel, Auszügen/Türen, Arbeitsplatte, Oberschränken
  auf Montagehöhe, Geräte beschriftet.
- 3D vorher/nachher: alte Küche gelb, neue Elemente rot, Arbeitsplatte als eigene Platte.
- `<plannummer>_stueckliste.json`: alle neuen Artikel mit Menge, die Geräte aus `einbau`,
  Arbeitsplatte und Sockel in Laufmetern. Steht dort etwas unter `ohne_artikel`, fehlt es in der
  Offerte: Artikel eintragen oder der Person sagen.

## Visualisierung

Für das Bild nach dem Umbau (`visualisierung.md`) beschreibst du die Küche aus den Elementen:
Anordnung von links nach rechts (z.B. «Hochschrank Kühlschrank, Hochschrank Backofen, Auszüge,
Kochfeld mit Haube, Spüle unter dem Fenster, Geschirrspüler»), Fronten und Arbeitsplatte nach
den Wünschen der Person.

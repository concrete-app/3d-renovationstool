---
name: umbauplan
description: Macht aus Handskizzen, Masstexten, Fotos oder einem alten Plan einen massstäblichen Umbau-Plansatz als PDF (Grundriss, Schnitte, Ansichten, 3D vorher/nachher, Fotodokumentation; Bestand schwarz, Abbruch gelb, Neu rot, mit Plankopf) und ein IFC-Modell. Verwenden, wenn jemand einen Grundriss, Umbauplan, Schnitt, eine Ansicht, 3D-Ansicht, Visualisierung oder ein IFC/BIM-Modell aus einer Skizze will.
---

# Umbauplan: Skizze → Plansatz (PDF) + IFC

Du liest die Skizze und schreibst `plan.json`. **Zeichnen, Rechnen und Prüfen
macht das Skript**, du zeichnest nie selbst (kein matplotlib, kein SVG von Hand).
Darum sieht jeder Plan gleich aus, und die Masse sind exakt. Das Datenmodell steht in
`datenmodell.md` (zuerst lesen), ein vollständiges Beispiel in `beispiele/wohnung.json`.

`<skill>` ist unten der Ordner, in dem diese SKILL.md liegt.

## Grundregeln

- **Keine Masse erfinden.** Jedes Mass kommt von der Skizze oder von der Person.
  Fehlt eines, frage nach. Ein schöner Plan mit geschätzten Massen ist gefährlich,
  weil ihm jeder glaubt. Standardwerte (`datenmodell.md`) nur, wenn die Person das
  ausdrücklich will, und dann jedes in `angenommen` eintragen. Es steht dann auf dem Plan.
- **Masse prüfen, die sich widersprechen.** Ergeben die Teilmasse einer Seite nicht das
  Gesamtmass, frage, welches gilt. Gleiche das nicht still aus.
- **Status ist Pflicht.** Für jede Wand und Öffnung: bleibt (`bestand`), fällt weg
  (`abbruch`) oder kommt dazu (`neu`). Ist es auf der Skizze nicht klar (Farbe,
  Schraffur, Kreuz, Notiz), frage.
- **Platzhalter sind ein Mangel.** Ohne `--entwurf` lehnt das Skript `<…>` in Projekt
  oder `firma.json` ab. Eine Plannummer denkst du dir nicht aus.

## Ablauf

1. **Skizze lesen.** Liste für dich: Aussenwände, Innenwände mit Dicke, Türen und
   Fenster mit Lage und Breite, Raumnamen, eingetragene Masse. Achte darauf, ob die Masse
   Aussen-, Achs- oder lichte Masse sind (siehe `datenmodell.md`).
2. **Nachfragen**, gesammelt in einer Nachricht und knapp: welche Masse fehlen (pro Wand
   bzw. Öffnung), was abgebrochen und was neu wird, Projektname, Adresse, Plannummer.
   Raumhöhe und Fensterbrüstungen nur, wenn sie für den Plan nötig sind (IFC).
3. **plan.json schreiben** im Arbeitsordner der Person (nicht im Skill-Ordner). Nullpunkt
   in eine Aussenecke, Achsen in cm.
4. **Prüfen und erzeugen:**

   ```
   uv run --python 3.12 --with ifcopenshell --with shapely --with matplotlib \
       python <skill>/scripts/umbauplan.py plan.json ausgabe/ --vorschau
   ```

   Bei `MÄNGEL` nennt das Skript jedes Feld. Behebe sie und lass es erneut laufen.
   `--nur-pruefen` prüft, ohne zu zeichnen. Fehlen nur Firmendaten oder Plannummer,
   kannst du mit `--entwurf` eine Vorschau zeigen.
5. **Warnungen ernst nehmen.** «endet frei» heisst meist, dass eine Achse ein paar cm
   neben der anderen endet und darum ein Raum nicht geschlossen ist. «liegt in keiner
   geschlossenen Fläche» und «hat keinen Raumnamen» haben dieselbe Ursache. Korrigiere
   die Koordinaten, statt die Warnung stehen zu lassen.
6. **Ansehen.** Öffne die Vorschau-PNGs (die Pfade stehen am Ende der Skriptausgabe)
   mit Read und vergleiche es Wand für Wand mit der Skizze: Lage der Türen, Aufschlag,
   Fenster, Farben. Vergleiche die lichten Masse aus der Skriptausgabe mit den Massen
   auf der Skizze. Schau auch Schnitt- und 3D-Blatt an: Stehen Abbruch (gelb) und Neu
   (rot) dort, wo die Person sie haben will? Erst dann meldest du das Ergebnis.
7. **Melden:** Pfade zu PDF und IFC, die Liste der Blätter, Räume mit Fläche (aus der Skriptausgabe, nicht
   selbst gerechnet), die Liste `angenommen` und offene Warnungen. Schreibe dazu, dass
   eine Fachperson die Masse vor der Ausführung prüfen muss.

## Änderungen

«Tür 20 cm nach links», «Wand zwischen Küche und Bad weg», «Dusche statt Badewanne»:
ändere nur `plan.json` und erzeuge neu. Bei einer Planänderung nach der Abgabe: `index`
hochzählen (A → B). Baue nie ein PDF von Hand nach.

## Fotos

Fotos, die die Person mitschickt, nutzt du zuerst zum Verstehen (Bestand, Fenster,
Leitungen). Sollen sie in den Plansatz, trage sie in `plan.json` unter `fotos` ein
(Pfad relativ zu `plan.json`, kurzer Titel); sie kommen auf eigene Blätter
(Fotodokumentation, sechs pro Blatt). Nur JPG und PNG: iPhone-Fotos (HEIC) vorher
umwandeln mit `sips -s format jpeg bild.heic --out bild.jpg`. Lies jedes Foto vorher an,
bevor du es in den Plan setzt, und frage, wenn darauf Personen oder Privates zu sehen sind.

## Was das Skript erzeugt

- `<plannummer>_umbau.pdf`, ein Plansatz auf A3, Blätter in dieser Reihenfolge:
  1. **Grundriss** je Geschoss, im echten Massstab (1:50, sonst 1:100): Wände nach Status
     eingefärbt, Türen mit Aufschlag, Fenster, Einrichtung, Raumname mit Fläche und lichten
     Massen, Aussenmassketten, Schnittlinien.
  2. **Schnitte** A–A und B–B: geschnittene Wände nach Status, was dahinter liegt als
     Ansicht, Koten und Höhenkette. Ohne Angabe legt das Skript die Schnitte selbst dorthin,
     wo sie möglichst viele Öffnungen und Umbauteile treffen. Bestimmte Schnitte: `schnitte`
     in `plan.json` (siehe `datenmodell.md`).
  3. **Ansichten** der vier Fassaden, mit Himmelsrichtung, wenn `nordwinkel` angegeben ist.
  4. **3D vorher/nachher** je Geschoss, aus zwei Blickwinkeln: Puppenhaus ohne Decke, vorher
     gelb was wegkommt, nachher rot was neu ist.
  5. **Fotodokumentation**, wenn `fotos` angegeben sind.

  Plankopf mit Logo und Firmendaten aus `firma.json` (das-umbau-team.ch) auf jedem Blatt.
  Nur einzelne Blätter: `--blaetter grundriss,3d` oder `"blaetter"` in `plan.json`.
- `<plannummer>.ifc`: IFC4-Modell mit Wänden, Öffnungen, Türen, Fenstern, Böden, Räumen
  (mit Fläche) und Einrichtung. Der Umbaustatus steht in `Pset_*Common.Status`
  (EXISTING/DEMOLISH/NEW). Öffnen mit Archicad, Revit, Vectorworks oder einem
  IFC-Viewer (z. B. BIMvision, Bonsai für Blender).

## Voraussetzungen

`uv` lädt Python 3.12 und die Bibliotheken beim ersten Lauf selbst (ca. 1 Minute).
Ohne uv: `pip install ifcopenshell shapely matplotlib` (Python 3.10–3.13), dann
`python <skill>/scripts/umbauplan.py …`. Gibt es gar kein Python: schreibe `plan.json`
und sage der Person, dass sie das Skript auf einem Rechner mit Python ausführen muss.

## Was dieser Skill (noch) nicht tut

- Kein Dach, kein Terrain, keine Treppen: Ansichten zeigen die Wände bis zur Decke.
  Schnitte sind senkrecht zu x oder y (keine schrägen Schnitte).
- Keine fotorealistischen Bilder. Die 3D-Ansicht ist eine Planskizze für das Gespräch
  mit der Bauherrschaft, kein Rendering.
- Keine schrägen Aussenmassketten: Bemasst werden Fassaden, die parallel zu x oder y
  liegen. Schräge Wände werden gezeichnet, aber nicht aussen bemasst.
- Keine Statik, keine Baubewilligungs-Pläne. Ob eine Wand tragend ist, entscheidet eine
  Fachperson.

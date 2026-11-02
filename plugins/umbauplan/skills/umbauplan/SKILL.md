---
name: umbauplan
description: Macht bei Küchen-, Bad- und Gesamtrenovationen aus Handskizzen, Masstexten, Fotos oder einem alten Plan einen massstäblichen Umbau-Plansatz als PDF (Grundriss, Schnitte, Ansichten, 3D vorher/nachher, Fotodokumentation; Bestand schwarz, Abbruch gelb, Neu rot, mit Plankopf) und ein IFC-Modell. Macht aus Fotos vom Bestand Visualisierungen nach dem Umbau in derselben Perspektive (Bildwerkzeug von ChatGPT/Codex). Verwenden, wenn jemand einen Grundriss, Umbauplan, Schnitt, eine Ansicht, 3D-Ansicht, Visualisierung oder ein IFC/BIM-Modell aus einer Skizze will, oder ein Foto anhängt und sehen will, wie der Raum modern oder nach dem Umbau aussieht.
---

# Umbauplan: Skizze → Plansatz (PDF) + IFC

Du liest die Skizze und schreibst `plan.json`. **Zeichnen, Rechnen und Prüfen
macht das Skript**, du zeichnest nie selbst (kein matplotlib, kein SVG von Hand).
Darum sieht jeder Plan gleich aus, und die Masse sind exakt. Das Datenmodell steht in
`datenmodell.md` (zuerst lesen), ein vollständiges Beispiel in `beispiele/wohnung.json`.

`<skill>` ist unten der Ordner, in dem diese SKILL.md liegt.

## Worum es bei den Zeichnungen geht

Die Skizzen und Pläne kommen aus **Küchenumbauten, Badumbauten und
Gesamtrenovationen** von Wohnungen und Einfamilienhäusern. Lies jede Zeichnung in
diesem Sinn:

- **Was ein Symbol ist, leitest du aus dem Raum ab.** Ein Rechteck von etwa 60 cm Tiefe
  entlang einer Küchenwand ist die Küchenzeile (`kueche`), eine Insel davor ebenfalls.
  Im Bad: kleines Oval an der Wand = `wc`, Rechteck oder Oval mit Kreis = `lavabo`,
  Quadrat mit Kreuz oder Ablaufpunkt = `dusche`, langes Rechteck = `badewanne`,
  Waschmaschine und Tumbler übereinander = `waschturm`. Übliche Kürzel: KS (Kühlschrank),
  GS/GWM (Geschirrspüler), BO/Herd/KF (Backofen, Kochfeld), HS (Hochschrank),
  WT (Waschtisch), WM/TU (Waschmaschine/Tumbler). Was in keinen Typ passt, wird
  `andere` mit `bezeichnung`.
- **Raumnamen ohne Beschriftung** ergeben sich aus der Einrichtung: WC + Lavabo + Dusche
  oder Wanne = «Bad», nur WC + Lavabo = «WC», Küchenzeile = «Küche». Schreibe sie so in
  den Plan und nenne sie bei der Rückmeldung, damit die Person korrigieren kann.
- **Typische Umbauten erkennen:** Wand zwischen Küche und Wohnen/Essen weg (offene
  Küche), Wanne wird Dusche, Bad wird vergrössert oder ein WC kommt dazu, Tür wird
  versetzt oder zugemauert, Küchenzeile wird neu angeordnet. Durchgestrichene oder
  gekreuzte Wände und Apparate sind meist `abbruch`, neu eingezeichnete (oft farbig
  oder mit anderem Stift) meist `neu`. Bei einer Gesamtrenovation betrifft das oft alle
  Räume: Bestand vollständig erfassen, nicht nur Küche und Bad.
- **Neue und alte Einrichtung gehört in `objekte`** mit Status, nicht nur die Wände:
  Die alte Wanne ist `abbruch`, die neue Dusche `neu`. Das ist für die Bauherrschaft
  oft der wichtigste Teil des Plans.
- **Deuten ist erlaubt, erfinden nicht.** Ein Symbol als Dusche zu lesen ist Deutung;
  ihre Masse zu schätzen ist Erfinden (siehe Grundregeln). Ist ein Symbol mehrdeutig,
  frage. Steigzonen, Schächte und Leitungen, die auf der Skizze stehen, übernimmst du
  als Hinweis (`andere` mit `bezeichnung`); ob ein Apparat dort angeschlossen werden
  kann, entscheidet eine Fachperson.

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
   Fenster mit Lage und Breite, Raumnamen, Küchen- und Sanitäreinrichtung (alt und neu),
   eingetragene Masse. Achte darauf, ob die Masse
   Aussen-, Achs- oder lichte Masse sind (siehe `datenmodell.md`).
2. **Nachfragen**, gesammelt in einer Nachricht und knapp: welche Masse fehlen (pro Wand
   bzw. Öffnung), was abgebrochen und was neu wird, Projektname, Adresse, Plannummer.
   Die Höhen jeder Öffnung gehören dazu: Fenster Höhe und Brüstung, Türen Höhe. Sie stehen
   im Grundriss neben der Öffnung und in den Schnitten. Fehlt eine Türhöhe, setzt das Skript
   210 ein; das ist dann ein Standardwert und gehört in `angenommen`.
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
   Fenster, Farben, Masse der Öffnungen (F1 70 × 90, BRH 1.10). Vergleiche die lichten Masse aus der Skriptausgabe mit den Massen
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

## Visualisierung aus Fotos

Hängt die Person ein Foto an und will sehen, wie der Raum nach dem Umbau aussieht
(«mach das modern», «wie sieht die neue Küche aus», «Fronten in Salbeigrün»), erzeugst du
mit dem Bildwerkzeug von ChatGPT/Codex ein neues Bild aus **derselben Perspektive**: das
Foto als Eingabebild, neue Einrichtung nach Plan, Farben und Materialien nach den Wünschen
der Person. **Lies vorher `visualisierung.md`**: Prompt-Vorlage, Ablage der Bilder und was
zu tun ist, wenn es kein Bildwerkzeug gibt. Foto und Bild trägst du unter
`visualisierungen` in `plan.json` ein; sie kommen als Blatt «Visualisierung vorher/nachher»
in den Plansatz.

## Was das Skript erzeugt

- `<plannummer>_umbau.pdf`, ein Plansatz auf A3, Blätter in dieser Reihenfolge:
  1. **Grundriss** je Geschoss, im echten Massstab (1:50, sonst 1:100): Wände nach Status
     eingefärbt, Türen mit Aufschlag, Fenster, Einrichtung, Raumname mit Fläche und lichten
     Massen, Aussenmassketten, Schnittlinien. Neben jeder Öffnung ihre Masse in der
     Statusfarbe: Fenster «F1  70 × 90, BRH 1.10», Türen und Durchgänge «T1  80 × 2.00».
     Die Beschriftung steht auf der Raumseite parallel zur Wand und weicht Wänden, Einrichtung,
     Türflügeln und anderen Texten aus. Wo sie nicht passt (kleine Räume, Küchenzeile vor dem
     Fenster), steht sie zweizeilig; passt auch das nicht, steht an der Öffnung nur die
     Bezeichnung (F1) und die Masse in der Liste «Öffnungen» neben der Legende.
  2. **Schnitte** A–A und B–B: geschnittene Wände nach Status, was dahinter liegt als
     Ansicht, Koten und Höhenkette. An jeder geschnittenen Öffnung eine senkrechte Masskette
     auf der Raumseite: Brüstung und Fensterhöhe, bei Türen die Türhöhe (nicht bei Öffnungen,
     die wegfallen). Ohne Angabe legt das Skript die Schnitte selbst dorthin,
     wo sie möglichst viele Öffnungen und Umbauteile treffen. Bestimmte Schnitte: `schnitte`
     in `plan.json` (siehe `datenmodell.md`).
  3. **Ansichten** der vier Fassaden, mit Himmelsrichtung, wenn `nordwinkel` angegeben ist.
  4. **3D vorher/nachher** je Geschoss, aus zwei Blickwinkeln: Puppenhaus ohne Decke, vorher
     gelb was wegkommt, nachher rot was neu ist.
  5. **Visualisierung** vorher/nachher, ein Blatt pro Eintrag in `visualisierungen`: Foto
     links, Bild nach dem Umbau rechts, darunter die Wünsche der Person und der Hinweis
     «nicht massstäblich».
  6. **Fotodokumentation**, wenn `fotos` angegeben sind.

  Plankopf mit Logo und Firmendaten aus `firma.json` (das-umbau-team.ch) auf jedem Blatt.
  Nur einzelne Blätter: `--blaetter grundriss,3d` oder `"blaetter"` in `plan.json`.
- `<plannummer>.ifc`: IFC4-Modell mit Wänden, Öffnungen, Türen, Fenstern, Böden, Räumen
  (mit Fläche) und Einrichtung. Der Umbaustatus steht in `Pset_*Common.Status`
  (EXISTING/DEMOLISH/NEW). Öffnen mit Archicad, Revit, Vectorworks oder einem
  IFC-Viewer (z. B. BIMvision, Bonsai für Blender).

## Voraussetzungen

Du musst das Skript **selbst ausführen**, nicht nur die Anleitung lesen. Versuche es in
dieser Reihenfolge und nimm das erste, das geht:

1. `uv` (Befehl unter Ablauf, Schritt 4): lädt Python 3.12 und die Bibliotheken beim ersten
   Lauf selbst (ca. 1 Minute).
2. Vorhandenes Python (auch die Python-Umgebung von ChatGPT): `python <skill>/scripts/umbauplan.py …`.
   Es braucht shapely, matplotlib und Pillow; fehlt etwas, `pip install shapely matplotlib pillow`.
   Fehlt nur `ifcopenshell` und lässt es sich nicht installieren, entsteht die PDF trotzdem,
   nur ohne IFC. Sag das der Person.
3. Kannst du in dieser Umgebung gar keinen Code ausführen: schreibe `plan.json`, gib es der
   Person und sag ihr, dass der Plansatz in **Codex** (Codex-App oder `codex` im Terminal)
   entsteht, weil dort ein Terminal zur Verfügung steht. Zeichne den Plan nie selbst nach.

## Was dieser Skill (noch) nicht tut

- Kein Dach, kein Terrain, keine Treppen: Ansichten zeigen die Wände bis zur Decke.
  Schnitte sind senkrecht zu x oder y (keine schrägen Schnitte).
- Fotorealistische Bilder nur über das Bildwerkzeug von ChatGPT/Codex (siehe
  `visualisierung.md`), nie selbst gezeichnet. Sie sind nicht massstäblich. Die 3D-Ansicht
  ist eine Planskizze für das Gespräch mit der Bauherrschaft, kein Rendering.
- Keine schrägen Aussenmassketten: Bemasst werden Fassaden, die parallel zu x oder y
  liegen. Schräge Wände werden gezeichnet, aber nicht aussen bemasst.
- Keine Statik, keine Baubewilligungs-Pläne. Ob eine Wand tragend ist, entscheidet eine
  Fachperson.

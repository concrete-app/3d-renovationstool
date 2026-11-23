---
name: badplan
description: Macht bei Badumbauten aus Handskizzen, Masstexten, Fotos oder einem alten Plan einen massstäblichen Bad-Plansatz als PDF (Grundriss, Schnitte, Ansichten, Wandansichten A–D als Nasszellenplan, 3D vorher/nachher, Visualisierung aus Fotos, Fotodokumentation; Bestand schwarz, Abbruch gelb, Neu rot) und ein IFC-Modell. Verwenden, wenn jemand ein Bad oder WC umbauen will und einen Grundriss, Nasszellenplan, Schnitt, eine 3D-Ansicht oder ein Vorher-nachher-Bild davon braucht, z.B. «Wanne wird Dusche».
---

# Badplan: Skizze → Plansatz und IFC

Für **Bad- und WC-Umbauten**.

## Zuerst lesen

`<kern>` ist der gemeinsame Ordner **plankern**: `<skill>/plankern`, wenn es ihn gibt
(claude.ai), sonst `<skill>/../../plankern` (Plugin). `<skill>` ist der Ordner dieser SKILL.md.

1. `<kern>/regeln.md`: Pflichtliste, Grundregeln, Ablauf, Skriptaufruf. Gilt vollständig.
2. `<kern>/bad.md`: Symbole und typische Umbauten im Bad.
3. `<kern>/datenmodell.md`: Aufbau von `plan.json`. Beispiel: `<kern>/beispiele/bad.json`.
4. Bei Fotos: `<kern>/visualisierung.md`.

## Kurz

- **Ergebnis ist genau eine PDF aus `<kern>/scripts/umbauplan.py`** für das Projekt der Person:
  keine eigene PDF, keine angehängten Seiten oder Links. Was nicht klappt: Tabelle
  «Wenn etwas nicht klappt» in `<kern>/regeln.md` befolgen.
- **Beispiele (`<kern>/beispiele/`) nie als Projekt zeichnen.** Skizze als PDF/Scan:
  `python <kern>/scripts/seiten.py datei.pdf`, dann jede Seite ansehen.
- Masse und Status (bleibt / weg / neu) von der Skizze oder erfragen, nie schätzen.
- Alle Apparate alt und neu unter `objekte` (alte Wanne `abbruch`, neue Dusche `neu`).
- Erzeugen mit
  `uv run --python 3.12 --with ifcopenshell --with shapely --with matplotlib python <kern>/scripts/umbauplan.py plan.json ausgabe/ --vorschau`,
  bis keine MÄNGEL und WARNUNGEN mehr kommen; dann «NOCH ZU TUN» abarbeiten.
- Melden: PDF und IFC als Datei, Blätter, Räume mit Fläche, Annahmen,
  «Masse vor Ausführung durch Fachperson prüfen». Keine Preise nennen oder schätzen.

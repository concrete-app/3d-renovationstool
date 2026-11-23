---
name: gesamtplan
description: Macht bei Gesamtrenovationen von Wohnungen und Einfamilienhäusern aus Handskizzen, Masstexten, Fotos oder alten Plänen einen massstäblichen Plansatz als PDF für alle Räume und Geschosse (Grundrisse, Schnitte, Fassadenansichten, Wandansichten A–D für Küche und Bad, 3D vorher/nachher, Visualisierung aus Fotos, Fotodokumentation; Bestand schwarz, Abbruch gelb, Neu rot), ein IFC-Modell und bei neuer Küche eine Stückliste. Verwenden, wenn jemand eine ganze Wohnung oder ein Haus umbauen will, Wände versetzt, Räume zusammenlegt oder einen Umbauplan für mehrere Räume braucht.
---

# Gesamtplan: Skizze → Plansatz für die ganze Wohnung, IFC und Stückliste

Für **Gesamtrenovationen**: alle Räume, auch die, die bleiben.

## Zuerst lesen

`<kern>` ist der gemeinsame Ordner **plankern**: `<skill>/plankern`, wenn es ihn gibt
(claude.ai), sonst `<skill>/../../plankern` (Plugin). `<skill>` ist der Ordner dieser SKILL.md.

1. `<kern>/regeln.md`: Pflichtliste, Grundregeln, Ablauf, Skriptaufruf. Gilt vollständig.
2. Für jede Küche `<kern>/kueche.md` (Elemente aus `<kern>/bauteile-kueche.json`), für jedes
   Bad und WC `<kern>/bad.md`.
3. `<kern>/datenmodell.md`: Aufbau von `plan.json`, mehrere Geschosse. Beispiel:
   `<kern>/beispiele/wohnung.json`.
4. Bei Fotos: `<kern>/visualisierung.md`.

## Kurz

- Bestand vollständig erfassen: alle Wände, Öffnungen und Räume, nicht nur Küche und Bad.
- Wände, die wegkommen, `abbruch`; neue Wände `neu`; zusammengelegte Räume mit eigenem
  Raumpunkt `zustand: "neu"`. Ob eine Wand tragend ist, entscheidet eine Fachperson.
- Erzeugen mit
  `uv run --python 3.12 --with ifcopenshell --with shapely --with matplotlib python <kern>/scripts/umbauplan.py plan.json ausgabe/ --vorschau`,
  bis keine MÄNGEL und WARNUNGEN mehr kommen; dann «NOCH ZU TUN» abarbeiten.
- Melden: PDF, IFC (und Stückliste, wenn es eine neue Küche gibt) als Datei, Blätter, Räume
  mit Fläche, Annahmen, «Masse vor Ausführung durch Fachperson prüfen». Keine Preise.

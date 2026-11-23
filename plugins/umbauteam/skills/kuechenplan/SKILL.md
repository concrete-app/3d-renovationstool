---
name: kuechenplan
description: Macht bei Küchenumbauten aus Handskizzen, Masstexten, Fotos oder einem alten Plan einen massstäblichen Küchen-Plansatz als PDF (Grundriss, Schnitte, Ansichten, Wandansichten A–D mit Fronten, 3D vorher/nachher, Visualisierung aus Fotos; Bestand schwarz, Abbruch gelb, Neu rot), ein IFC-Modell und eine Stückliste der Küchenelemente (Unterschränke, Hochschränke, Oberschränke, Geräte) für die Offerte. Verwenden, wenn jemand eine neue Küche planen, eine Küchenzeile zeichnen, einen Küchenplan, eine Küchenansicht oder ein Vorher-nachher-Bild einer Küche will.
---

# Küchenplan: Skizze → Plansatz, IFC und Stückliste

Für **Küchenumbauten**. Die neue Küche wird Element für Element aus dem Bauteilkatalog
gezeichnet, damit Grundriss, Wandansichten und 3D stimmen und die Stückliste direkt in die
Offerte gehen kann.

## Zuerst lesen

`<kern>` ist der gemeinsame Ordner **plankern**: `<skill>/plankern`, wenn es ihn gibt
(claude.ai), sonst `<skill>/../../plankern` (Plugin). `<skill>` ist der Ordner dieser SKILL.md.

1. `<kern>/regeln.md`: Pflichtliste, Grundregeln, Ablauf, Skriptaufruf. Gilt vollständig.
2. `<kern>/kueche.md`: Küche lesen, Elemente aus `<kern>/bauteile-kueche.json`, Geräte als `einbau`.
3. `<kern>/datenmodell.md`: Aufbau von `plan.json`. Beispiel: `<kern>/beispiele/kueche.json`.
4. Bei Fotos: `<kern>/visualisierung.md`.

## Kurz

- Masse und Status (bleibt / weg / neu) von der Skizze oder erfragen, nie schätzen.
- Neue Küche: jedes Element mit `artikel` aus `bauteile-kueche.json`; alte Küche als Block `kueche`.
- Erzeugen mit
  `uv run --python 3.12 --with ifcopenshell --with shapely --with matplotlib python <kern>/scripts/umbauplan.py plan.json ausgabe/ --vorschau`,
  bis keine MÄNGEL und WARNUNGEN mehr kommen; dann «NOCH ZU TUN» abarbeiten.
- Melden: PDF, IFC und `<plannummer>_stueckliste.json` als Datei, Blätter, Räume mit Fläche,
  Annahmen, Elemente `ohne_artikel`, «Masse vor Ausführung durch Fachperson prüfen».
- Keine Preise nennen oder schätzen: Die Offerte rechnet das Offerten-Tool aus der Stückliste.

# umbau-skills

Skills für Claude, als Plugin-Marketplace. Aufbau wie `concrete-skills`.

| Plugin | Was es tut |
|---|---|
| `umbauplan` | Handskizze → Umbau-Plansatz (PDF: Grundriss, Schnitte, Ansichten, 3D vorher/nachher, Visualisierung aus Fotos, Fotos; Bestand/Abbruch/Neu) und IFC-Modell |

## Installieren (Claude Code)

Lokal, direkt aus diesem Ordner:

```
/plugin marketplace add ~/Documents/3d-renovationstool
/plugin install umbauplan@umbau-skills
```

Liegt das Repo später auf GitHub: `/plugin marketplace add <github-nutzer>/umbau-skills`.

## Installieren (Codex / ChatGPT)

Codex liest denselben Marketplace (`.claude-plugin/marketplace.json`) und die
Codex-Angaben in `plugins/umbauplan/.codex-plugin/plugin.json`:

```
codex plugin marketplace add <github-nutzer>/umbau-skills
```

In der ChatGPT-Desktop-App erscheint der Marketplace danach unter Plugins, dort
«Umbauplan» installieren.

**Visualisierungen** (Foto vom Bestand → Bild nach dem Umbau, gleiche Perspektive) macht
das Bildwerkzeug von ChatGPT/Codex. Es läuft über das ChatGPT-Abo der Person, die das
Plugin nutzt; ein API-Schlüssel ist nicht nötig. In Claude Code gibt es dieses Werkzeug
nicht: Dort geht es nur, wenn die Codex CLI installiert und mit ChatGPT angemeldet ist.
Ablauf und Prompt-Vorlage: `plugins/umbauplan/skills/umbauplan/visualisierung.md`.

## Aktualisieren

```
/plugin marketplace update umbau-skills
```

Ein Update kommt nur an, wenn sich `version` in
`plugins/umbauplan/.claude-plugin/plugin.json` geändert hat. **Bei jeder Änderung die
Version erhöhen**, in beiden Dateien: `.claude-plugin/plugin.json` und
`.codex-plugin/plugin.json`.

## Firmenauftritt

`plugins/umbauplan/skills/umbauplan/firma.json` enthält die Firmendaten für den Plankopf
(AKUBA GmbH | das-umbau-team.ch) und unter `marke` Logo, Akzentfarbe und Schrift. Logo
und Schrift (Roboto, Apache-Lizenz in `assets/schrift/`) liegen in `assets/`. Steht in
`firma.json` ein Platzhalter `<…>`, erzeugt das Skript nur Entwürfe.

## Wie es funktioniert

```
Skizze / Foto ──Claude──▶ plan.json ──scripts/umbauplan.py──▶ Plansatz.pdf + Modell.ifc
```

Claude liest die Skizze und schreibt nur Daten (`plan.json`, siehe
`plugins/umbauplan/skills/umbauplan/datenmodell.md`). Zeichnen, Flächen, Massketten und
IFC macht das Skript. Darum sind die Pläne gleich aufgebaut, und die Masse sind exakt.

```
.claude-plugin/marketplace.json                 listet die Plugins auf
plugins/umbauplan/.claude-plugin/plugin.json    Name und Version
plugins/umbauplan/.codex-plugin/plugin.json     dasselbe für Codex / ChatGPT
plugins/umbauplan/skills/umbauplan/
  SKILL.md            Anleitung für Claude (Ablauf, Regeln)
  datenmodell.md      Aufbau von plan.json
  visualisierung.md   Foto → Bild nach dem Umbau (Prompt-Vorlage)
  firma.json          Firmendaten für den Plankopf
  beispiele/          vollständiges Beispiel
  scripts/
    modell.py         plan.json lesen und prüfen
    geometrie.py      Wandflächen nach Status, Räume, Flächen
    blatt.py          A3-Blatt, massstäbliche Fenster, Plankopf, Massketten
    grundriss.py      Grundriss mit Massketten und Schnittlinien
    ansichten.py      Schnitte und Fassadenansichten
    axonometrie.py    3D vorher/nachher
    visualisierung.py Blatt Visualisierung vorher/nachher
    fotos.py          Fotodokumentation
    pdf.py            alle Blätter in eine PDF
    ifc_export.py     IFC4 mit Umbaustatus
    umbauplan.py      Kommandozeile
tests/                Tests für die Skripte
```

## Von Hand ausführen

```
uv run --python 3.12 --with ifcopenshell --with shapely --with matplotlib \
    python plugins/umbauplan/skills/umbauplan/scripts/umbauplan.py \
    plugins/umbauplan/skills/umbauplan/beispiele/wohnung.json ausgabe/ --entwurf --vorschau
```

## Tests

```
uv run pytest
```

## Nächste Schritte

- Mehrere Geschosse übereinander im 3D
- Grundriss Bestand und Neu als eigene Blätter
- DXF-Export für CAD

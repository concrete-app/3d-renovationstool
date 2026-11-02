# umbau-skills

Skills für Claude, als Plugin-Marketplace. Aufbau wie `concrete-skills`.

| Plugin | Was es tut |
|---|---|
| `umbauplan` | Handskizze → Umbau-Plansatz (PDF: Grundriss, Schnitte, Ansichten, 3D vorher/nachher, Visualisierung aus Fotos, Fotos; Bestand/Abbruch/Neu) und IFC-Modell |

## Installieren

Der Skill läuft im **Claude-Chat** (claude.ai, Claude-App) und im **ChatGPT-Chat**. In beiden
führt der Chat das Skript in seiner eigenen Python-Umgebung aus; ein eigener Rechner mit
Python ist nicht nötig. Die Pakete baut `pakete.sh`:

```
./pakete.sh      # legt in dist/ zwei ZIPs ab
```

- **ChatGPT:** `dist/umbauplan-chatgpt.zip` unter Plugins hochladen. Das Manifest dafür ist
  `plugins/umbauplan/.codex-plugin/plugin.json` (Format von OpenAI für Plugins).
- **Claude:** `dist/umbauplan-claude.zip` unter Einstellungen → Fähigkeiten → Skills hochladen.
  Codeausführung muss eingeschaltet sein.
- **Claude Code** (lokal, aus diesem Ordner):
  `/plugin marketplace add ~/Documents/3d-renovationstool`, dann `/plugin install umbauplan@umbau-skills`.

**Visualisierungen** (Foto vom Bestand → Bild nach dem Umbau, gleiche Perspektive) macht die
Bildgenerierung von ChatGPT, über das ChatGPT-Abo der Person. Claude kann keine Bilder
erzeugen; dort gibt der Skill den fertigen Prompt für ChatGPT aus, und das Bild wird danach
wieder angehängt. Ablauf und Prompt-Vorlage: `plugins/umbauplan/skills/umbauplan/visualisierung.md`.

**Im ChatGPT-Chat** hat die Python-Umgebung kein Internet. matplotlib, shapely, numpy und
Pillow sind dort normalerweise vorhanden, ifcopenshell nicht: Es entsteht dann die PDF ohne IFC.

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
plugins/umbauplan/.codex-plugin/plugin.json     Name und Version für ChatGPT
pakete.sh                                       baut die ZIPs für ChatGPT und Claude
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

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
Nur den Skill (z. B. für claude.ai): `./pakete.sh` legt `dist/umbauplan-claude.zip` ab.

**Visualisierungen** (Foto vom Bestand → Bild nach dem Umbau, gleiche Perspektive) macht die
Bildgenerierung von ChatGPT. Claude kann keine Bilder erzeugen; dort gibt der Skill den
fertigen Prompt für ChatGPT aus. Ablauf: `plugins/umbauplan/skills/umbauplan/visualisierung.md`.

Läuft etwas nicht: `uv run --python 3.12 --with ifcopenshell --with shapely --with matplotlib
--with pypdf python plugins/umbauplan/skills/umbauplan/scripts/selbsttest.py` erzeugt den
Plansatz für `beispiele/bad.json` und sagt, was fehlt.

## Abhängigkeiten

| Paket | getestet mit | nötig für |
|---|---|---|
| Python | 3.12 | (3.10 bis 3.13) |
| shapely | 2.2.0 | Geometrie, Räume, Flächen |
| matplotlib | 3.11.2 | alle Blätter, PDF |
| numpy | 2.5.4 | 3D, Bilder |
| pillow | 12.3.0 | Fotos, Logo |
| ifcopenshell | 0.9.0 | IFC (optional: fehlt es, entsteht nur die PDF) |
| pypdf | 6.20.1 | nur Selbsttest und Tests (Textprüfung der PDF) |

## Aktualisieren

```
/plugin marketplace update umbau-skills
```

Ein Update kommt nur an, wenn sich `version` in
`plugins/umbauplan/.claude-plugin/plugin.json` geändert hat. **Bei jeder Änderung die
Version erhöhen.**

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
pakete.sh                                       baut die Skill-ZIP für claude.ai
plugins/umbauplan/skills/umbauplan/
  SKILL.md            Anleitung für Claude (Ablauf, Regeln)
  datenmodell.md      Aufbau von plan.json
  visualisierung.md   Foto → Bild nach dem Umbau (Prompt-Vorlage)
  firma.json          Firmendaten für den Plankopf
  beispiele/          vollständige Beispiele (wohnung.json, bad.json)
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
    selbsttest.py     prüft Umgebung und erzeugt den Beispiel-Plansatz
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

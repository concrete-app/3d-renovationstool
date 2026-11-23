# umbau-skills

Skills für Claude, als Plugin-Marketplace. Aufbau wie `concrete-skills`.

Plugin `umbauteam` mit drei Skills, die denselben Zeichenkern (`plugins/umbauteam/plankern/`) nutzen:

| Skill | Was er tut |
|---|---|
| `umbauteam:kuechenplan` | Küchenumbau: Küche Element für Element aus dem Bauteilkatalog → Plansatz, IFC, Stückliste für die Offerte |
| `umbauteam:badplan` | Bad/WC: Nasszellenplan, Wanne → Dusche usw. → Plansatz, IFC |
| `umbauteam:gesamtplan` | Wohnung/EFH, alle Räume und Geschosse → Plansatz, IFC (Stückliste bei neuer Küche) |

Plansatz = PDF mit Grundriss, Schnitten, Ansichten, Wandansichten A–D, 3D vorher/nachher,
Visualisierung aus Fotos, Fotodokumentation (Bestand/Abbruch/Neu).

## Installieren (Claude Code)

Lokal, direkt aus diesem Ordner:

```
/plugin marketplace add ~/Documents/3d-renovationstool
/plugin install umbauteam@umbau-skills
```

War vorher das Plugin `umbauplan` installiert: `/plugin uninstall umbauplan@umbau-skills`.

Liegt das Repo später auf GitHub: `/plugin marketplace add <github-nutzer>/umbau-skills`.
Nur die Skills (z. B. für claude.ai): `./pakete.sh` legt `dist/kuechenplan-claude.zip`,
`dist/badplan-claude.zip` und `dist/gesamtplan-claude.zip` ab, jede mit einer Kopie von `plankern/`.

**Visualisierungen** (Foto vom Bestand → Bild nach dem Umbau, gleiche Perspektive) macht die
Bildgenerierung von ChatGPT. Claude kann keine Bilder erzeugen; dort gibt der Skill den
fertigen Prompt für ChatGPT aus. Ablauf: `plugins/umbauteam/plankern/visualisierung.md`.

Läuft etwas nicht: `uv run --python 3.12 --with ifcopenshell --with shapely --with matplotlib
--with pypdf python plugins/umbauteam/plankern/scripts/selbsttest.py` erzeugt den
Plansatz für `beispiele/bad.json` und sagt, was fehlt.

## Abhängigkeiten

| Paket | getestet mit | nötig für |
|---|---|---|
| Python | 3.12 | (3.10 bis 3.13) |
| shapely | 2.2.0 | Geometrie, Räume, Flächen |
| matplotlib | 3.11.2 | alle Blätter, PDF |
| numpy | 2.5.4 | 3D, Bilder |
| pillow | 13.0.0 | Fotos, Logo |
| ifcopenshell | 0.9.0 | IFC (optional: fehlt es, entsteht nur die PDF) |
| pypdf | 6.21.4 | nur Selbsttest und Tests (Textprüfung der PDF) |

## Aktualisieren

```
/plugin marketplace update umbau-skills
```

Ein Update kommt nur an, wenn sich `version` in
`plugins/umbauteam/.claude-plugin/plugin.json` geändert hat. **Bei jeder Änderung die
Version erhöhen.**

## Firmenauftritt

`plugins/umbauteam/plankern/firma.json` enthält die Firmendaten für den Plankopf
(AKUBA GmbH | das-umbau-team.ch) und unter `marke` Logo, Akzentfarbe und Schrift. Logo
und Schrift (Roboto, Apache-Lizenz in `assets/schrift/`) liegen in `assets/`. Steht in
`firma.json` ein Platzhalter `<…>`, erzeugt das Skript nur Entwürfe.

## Wie es funktioniert

```
Skizze / Foto ──Claude──▶ plan.json ──scripts/umbauplan.py──▶ Plansatz.pdf + Modell.ifc + Stückliste.json
```

Claude liest die Skizze und schreibt nur Daten (`plan.json`, siehe
`plugins/umbauteam/plankern/datenmodell.md`). Zeichnen, Flächen, Massketten und
IFC macht das Skript. Darum sind die Pläne gleich aufgebaut, und die Masse sind exakt.

```
.claude-plugin/marketplace.json                 listet die Plugins auf
plugins/umbauteam/.claude-plugin/plugin.json    Name und Version
pakete.sh                                       baut die Skill-ZIPs für claude.ai
plugins/umbauteam/skills/
  kuechenplan/SKILL.md   badplan/SKILL.md   gesamtplan/SKILL.md   (kurz, verweisen auf plankern)
plugins/umbauteam/plankern/
  regeln.md           gemeinsame Regeln (Pflichtliste, Grundregeln, Ablauf)
  kueche.md, bad.md   Küche bzw. Bad lesen und zeichnen
  datenmodell.md      Aufbau von plan.json
  visualisierung.md   Foto → Bild nach dem Umbau (Prompt-Vorlage)
  bauteile-kueche.json  Bauteilkatalog Küche OHNE Preise, aus dem Offerten-Tool
                        (dort: pnpm run bauteile-export)
  firma.json          Firmendaten für den Plankopf
  beispiele/          wohnung.json, bad.json, kueche.json
  scripts/
    modell.py         plan.json lesen und prüfen (Artikel aus dem Bauteilkatalog)
    geometrie.py      Wandflächen nach Status, Räume, Flächen
    blatt.py          A3-Blatt, massstäbliche Fenster, Plankopf, Massketten
    grundriss.py      Grundriss mit Massketten und Schnittlinien
    ansichten.py      Schnitte und Fassadenansichten (Küchenfronten)
    raumansichten.py  Raumblatt: Grundriss und Wandansichten A–D je Umbauraum
    axonometrie.py    3D vorher/nachher
    visualisierung.py Blatt Visualisierung vorher/nachher
    fotos.py          Fotodokumentation
    stueckliste.py    Stückliste (Artikel, Menge, Status, Raum) für die Offerte
    pdf.py            alle Blätter in eine PDF
    ifc_export.py     IFC4 mit Umbaustatus und Artikel
    umbauplan.py      Kommandozeile
    selbsttest.py     prüft Umgebung und erzeugt den Beispiel-Plansatz
tests/                Tests für die Skripte
```

## Preise bleiben im Offerten-Tool

Der Skill kennt nur Artikel-IDs und Masse (`bauteile-kueche.json`), nie Preise. Die Stückliste
(`<plannummer>_stueckliste.json`) enthält Artikel und Mengen; die Preise rechnet das
Offerten-Tool auf dem Server aus der vertraulichen Preisliste. Ändern sich Küchenelemente im
Offerten-Tool, dort `pnpm run bauteile-export` laufen lassen, Version hier erhöhen.

## Von Hand ausführen

```
uv run --python 3.12 --with ifcopenshell --with shapely --with matplotlib \
    python plugins/umbauteam/plankern/scripts/umbauplan.py \
    plugins/umbauteam/plankern/beispiele/wohnung.json ausgabe/ --entwurf --vorschau
```

## Tests

```
uv run pytest
```

## Nächste Schritte

- Mehrere Geschosse übereinander im 3D
- Grundriss Bestand und Neu als eigene Blätter
- DXF-Export für CAD

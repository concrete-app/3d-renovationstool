# Bad und WC lesen

Gilt zusätzlich zu `regeln.md`, für Badumbauten und für jedes Bad/WC in einer Gesamtrenovation.

## Symbole

- Kleines Oval an der Wand = `wc`.
- Rechteck oder Oval mit Kreis = `lavabo` (Doppelwaschtisch: ein `lavabo` mit `bezeichnung`).
- Quadrat mit Kreuz oder Ablaufpunkt = `dusche`; langes Rechteck = `badewanne`.
- Waschmaschine und Tumbler übereinander = `waschturm`.
- Kürzel: WT (Waschtisch), WM/TU (Waschmaschine/Tumbler), SS (Spiegelschrank → `andere`).

## Typisch im Bad

- Wanne wird Dusche: alte `badewanne` `abbruch`, neue `dusche` `neu`, gleiche Ecke.
- Apparat am selben Ort ersetzt (neues WC, neuer Waschtisch): zwei Objekte an derselben Stelle,
  das alte `abbruch`, das neue `neu`. Höchstens eines bekommt eine `bezeichnung`.
- Bodenebene Dusche: `dusche` mit kleiner Höhe (Standard 5 cm), Gefälle und Rinne gehören nicht
  in den Plan, sondern in die Offerte.
- Vorwand für WC, Waschtisch oder Wanne: als **Wand** mit `neu`, Dicke 20, `hoehe` 120 (wenn nicht
  angegeben), an der bestehenden Wand anliegend; nicht als Objekt `andere`. Nur, wenn sie auf der
  Skizze oder in der Situationsaufnahme steht.
- Plattenhöhe und Plattenformat stehen nicht im Plan; sie werden im Offerten-Tool erfasst.

## Masse

Fehlt ein Mass, gelten die Annahmen aus `situationsaufnahme.md` (neue Wanne 180 × 80, WC an Vorwand
36 × 55, …) und die Standardwerte aus `datenmodell.md`. Jede Annahme kommt in `angenommen`, und
der Plan wird mit `--entwurf` erzeugt.

Das Blatt «Wandansichten A–D» entsteht für jedes Bad automatisch: Nasszellenplan mit Apparaten,
Türen, Fenstern und Höhenmassen.

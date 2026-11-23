# Visualisierung: Foto vom Bestand → Bild nach dem Umbau, gleiche Perspektive

Die Person hängt ein Foto an (z. B. die alte Küche) und will sehen, wie es nach dem
Umbau aussieht. Du erzeugst daraus mit der **Bildgenerierung von ChatGPT** ein neues
Bild aus **genau demselben Blickwinkel**, mit neuer Einrichtung nach Plan und den Farb-
und Materialwünschen der Person. Das Bild läuft über das ChatGPT-Abo der Person, ein
API-Schlüssel ist nicht nötig. Im Claude-Chat gibt es keine Bildgenerierung, siehe unten.
Das Skript zeichnet nichts davon, es setzt Foto und Bild nur als Blatt «Visualisierung»
in den Plansatz.

## Ablauf

1. **Foto ansehen.** Was zeigt es (Raum, Blickrichtung, Fenster, Türen, Einrichtung)?
   Personen oder Privates darauf: zuerst fragen. HEIC vorher umwandeln:
   `sips -s format jpeg bild.heic --out bild.jpg`. Das Foto gehört in den Arbeitsordner
   neben `plan.json`, z. B. `/mnt/data/fotos/kueche.jpg` (angehängte Dateien liegen in
   ChatGPT schon in `/mnt/data/`).
2. **Was ändert sich?** Gibt es schon `plan.json`, nimm aus dem Raum, den das Foto zeigt,
   die Objekte und Wände mit Status `abbruch` (verschwindet) und `neu` (kommt dazu).
   Sonst nimm, was die Person sagt. Fehlt Wichtiges (Wanne raus oder bleibt sie?), frage
   einmal knapp nach. Farben, Materialien und Stil aus der Nachricht der Person übernimmst
   du wörtlich in den Prompt.
3. **Prompt nach der Vorlage unten schreiben** und die Bildgenerierung aufrufen, **mit dem
   angehängten Foto als Vorlage** (das Foto bearbeiten, nicht ein neues Bild ohne Vorlage
   erfinden). Ohne das Foto als Vorlage stimmt die Perspektive nie.
4. **Ins PDF bringen:** Das erzeugte Bild muss als Datei in deiner Python-Umgebung liegen,
   z. B. `/mnt/data/visualisierungen/kueche_neu.png`. Schau mit `ls /mnt/data` nach, ob es
   dort ist. Wenn nicht: bitte die Person, das Bild herunterzuladen und hier wieder
   anzuhängen; dann liegt es in `/mnt/data/`.
5. **Prüfen:** Foto und Bild nebeneinander ansehen. Stimmen Standpunkt, Fluchtpunkte,
   Fenster, Türen und Deckenhöhe? Wenn nicht, ein zweites Mal erzeugen und im Prompt
   genau sagen, was verrutscht ist («the window must stay on the left wall, same size»).
   Nach zwei Versuchen das beste Bild nehmen und der Person sagen, was abweicht.
6. **In `plan.json` eintragen** und den Plansatz neu erzeugen:

   ```json
   "visualisierungen": [
     { "vorher": "fotos/kueche.jpg", "nachher": "visualisierungen/kueche_neu.png",
       "titel": "Küche", "wuensche": "Fronten salbeigrün matt, Eiche, Arbeitsplatte Terrazzo" }
   ]
   ```
   `wuensche` steht auf dem Blatt; schreib sie so, wie die Person sie gesagt hat.
   Will die Person nur das Bild ohne Pläne, zeige ihr das Bild und lass den Plansatz weg.

## Prompt-Vorlage

Englisch, weil die Bildmodelle damit am genauesten arbeiten. Die Blöcke in eckigen
Klammern füllst du aus, die übrigen Sätze übernimmst du unverändert.

```
Photorealistic interior renovation of the attached photo.

CAMERA – keep exactly: Use the attached photo as the exact camera reference. Keep the
identical camera position, height, angle, focal length, framing and vanishing points.
Keep walls, ceiling, floor plane, windows, doors and room proportions exactly where and
how large they are. Do not widen, crop or rotate the view.

REMOVE: [was wegkommt, z. B. "the old kitchen cabinets and the tiled backsplash",
"the bathtub on the right wall"; Wände mit Status abbruch: "the wall between kitchen and
living room is removed, show the open view into the living room"]

NEW: [was neu kommt, an welcher Wand, z. B. "a new kitchen run along the same back wall,
60 cm deep, with tall cabinets on the right", "a walk-in shower with frameless glass
screen where the bathtub was"]

STYLE AND WISHES: [Wünsche der Person, z. B. "matt sage-green fronts, black handles,
light terrazzo worktop, oak floorboards". Ohne Wünsche: "modern, timeless Swiss interior,
light natural materials, oak, white, subtle grey"]

Keep everything not listed under REMOVE or NEW in place (windows, radiators, ceiling).
Natural daylight from the same windows and direction as in the photo. Realistic
materials and proportions, no people, no text, no logos, no watermark, no extra windows
or doors.
```

## Im Claude-Chat

Claude kann keine Bilder erzeugen. Dann:

1. Schreib den Prompt nach der Vorlage fertig aus (mit Abbruch, Neu und Wünschen).
2. Gib ihn der Person in einem Codeblock und sag ihr: «In ChatGPT das Foto anhängen, diesen
   Text einfügen, das Bild herunterladen und hier wieder anhängen.»
3. Kommt das Bild zurück, trag es unter `visualisierungen` ein und erzeuge den Plansatz neu.

Erfinde kein Bild und zeichne keins mit matplotlib.

## Was eine Visualisierung ist und was nicht

Sie zeigt Stimmung, Farben und Anordnung, **nicht die Masse**. Das Blatt trägt den
Hinweis «KI-Visualisierung, nicht massstäblich. Massgebend sind die Pläne.» Sag das der
Person auch, wenn das Bild schöner oder grösser wirkt als der Raum im Plan.

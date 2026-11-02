# Visualisierung: Foto vom Bestand → Bild nach dem Umbau, gleiche Perspektive

Die Person hängt ein Foto an (z. B. die alte Küche) und will sehen, wie es nach dem
Umbau aussieht. Du erzeugst daraus mit dem **Bildwerkzeug von ChatGPT/Codex** ein neues
Bild aus **genau demselben Blickwinkel**, mit neuer Einrichtung nach Plan und den Farb-
und Materialwünschen der Person. Das Bild läuft über das ChatGPT-Abo der Person, ein
API-Schlüssel ist nicht nötig. Das Skript zeichnet nichts davon, es setzt Foto und Bild
nur als Blatt «Visualisierung» in den Plansatz.

## Ablauf

1. **Foto ansehen.** Was zeigt es (Raum, Blickrichtung, Fenster, Türen, Einrichtung)?
   Personen oder Privates darauf: zuerst fragen. HEIC vorher umwandeln:
   `sips -s format jpeg bild.heic --out bild.jpg`. Das Foto gehört in den Arbeitsordner
   neben `plan.json`, z. B. `fotos/kueche.jpg`.
2. **Was ändert sich?** Gibt es schon `plan.json`, nimm aus dem Raum, den das Foto zeigt,
   die Objekte und Wände mit Status `abbruch` (verschwindet) und `neu` (kommt dazu).
   Sonst nimm, was die Person sagt. Fehlt Wichtiges (Wanne raus oder bleibt sie?), frage
   einmal knapp nach. Farben, Materialien und Stil aus der Nachricht der Person übernimmst
   du wörtlich in den Prompt.
3. **Prompt nach der Vorlage unten schreiben** und das Bildwerkzeug aufrufen, **mit dem
   Foto als Eingabebild** (bearbeiten, nicht ein neues Bild ohne Vorlage erfinden).
   Ohne das Foto als Eingabe stimmt die Perspektive nie.
4. **Speichern** als `visualisierungen/<raum>_neu.png` neben `plan.json`. In Codex legt das
   Werkzeug die Bilder zuerst unter `$CODEX_HOME/generated_images/` ab (Standard
   `~/.codex/generated_images/`); nimm dort die neueste Datei und kopiere sie.
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

## Wenn kein Bildwerkzeug da ist

Manche Umgebungen (z. B. Claude Code) haben kein Bildwerkzeug. Dann:

- Ist die Codex CLI installiert und mit ChatGPT angemeldet (`codex login`), erzeuge das Bild
  darüber, mit dem Foto als Eingabe:

  ```
  codex exec -i fotos/kueche.jpg '$imagegen <Prompt nach der Vorlage>. Save the result as visualisierungen/kueche_neu.png'
  ```
  Liegt das Bild danach nicht dort, nimm die neueste Datei aus `~/.codex/generated_images/`.
- Sonst sag der Person, dass Visualisierungen ChatGPT/Codex brauchen, gib ihr den fertigen
  Prompt zum Kopieren und erzeuge den Plansatz ohne Visualisierung. Erfinde kein Bild und
  zeichne keins mit matplotlib.

## Was eine Visualisierung ist und was nicht

Sie zeigt Stimmung, Farben und Anordnung, **nicht die Masse**. Das Blatt trägt den
Hinweis «KI-Visualisierung, nicht massstäblich. Massgebend sind die Pläne.» Sag das der
Person auch, wenn das Bild schöner oder grösser wirkt als der Raum im Plan.

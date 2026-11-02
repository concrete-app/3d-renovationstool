# plan.json: das Datenmodell

Ein vollständiges Beispiel steht in `beispiele/wohnung.json`. Lies es, bevor du
ein eigenes schreibst.

## Grundregeln

- **Einheit: Zentimeter.** Immer, auch für Höhen. 2.40 m auf der Skizze → `240`.
- **Koordinaten:** x nach rechts, y nach oben, wie auf dem Plan. Den Nullpunkt legst
  du in eine Aussenecke (meist unten links), dann sind alle Werte positiv.
- **Wände sind Achsen.** `von` und `bis` sind die Wandmitte, die Dicke liegt je zur
  Hälfte links und rechts. Prüfe, welche Masse die Skizze zeigt, und rechne um:
  - **Aussenmass** (Gebäude aussen): Achsmass = Aussenmass − halbe Dicke je Seite.
    Aussen 10.80 m mit 30-cm-Wänden → Achsen 10.50 m auseinander.
  - **Lichtes Mass** (Raum innen): Achsmass = lichtes Mass + halbe Dicke je Seite.
  - Unklar: nachfragen. Das Skript gibt die lichten Masse jedes Raums aus. Vergleiche
    sie mit der Skizze.
- **Wände treffen sich auf der Achse.** Bei einer Ecke enden beide Achsen im selben
  Punkt. Eine Innenwand, die auf eine Aussenwand trifft, endet auf deren Achse. Das
  Skript schliesst Ecken und Stösse selbst.
- **Status** ist bei jedem Bauteil `bestand`, `abbruch` oder `neu`.

## projekt

| Feld | Pflicht | Inhalt |
|---|---|---|
| `name` | ja | «Umbau Wohnung Meier, 2. OG» |
| `adresse` | ja | Adresse des Objekts |
| `plannummer` | ja | von der Person, nicht erfinden |
| `bauherr` | nein | |
| `datum` | nein | `JJJJ-MM-TT`, sonst heute |
| `gezeichnet` | nein | Kürzel |
| `index` | nein | Planänderung: `A`, `B`, … |
| `massstab` | nein | `50` (Standard) oder `20`, `100`, `200`. Passt der Grundriss nicht auf A3, nimmt das Skript den nächstgrösseren |
| `nordwinkel` | nein | Grad, um die Norden von «oben» im Uhrzeigersinn abweicht. Weglassen, wenn unbekannt: dann gibt es keinen Nordpfeil |

## geschosse[]

| Feld | Pflicht | Inhalt |
|---|---|---|
| `id` | ja | `EG`, `1OG`, `UG` (kurz, erscheint in der Plannummer) |
| `name` | nein | «Erdgeschoss» |
| `kote` | nein | Höhe des Bodens in cm (EG = 0) |
| `raumhoehe` | ja | lichte Höhe in cm |
| `deckenstaerke` | nein | Standard 20 |
| `waende`, `oeffnungen`, `raeume`, `objekte` | | siehe unten |

### waende[]

```json
{ "id": "W1", "von": [0, 0], "bis": [850, 0], "dicke": 30, "status": "bestand" }
```
`hoehe` ist optional (Standard: `raumhoehe`). IDs müssen im ganzen Plan eindeutig sein.

### oeffnungen[]

```json
{ "id": "T1", "wand": "W5", "typ": "tuer", "abstand": 40, "breite": 90, "hoehe": 210,
  "status": "neu", "anschlag": "anfang", "seite": "links" }
{ "id": "F1", "wand": "W1", "typ": "fenster", "abstand": 150, "breite": 120, "hoehe": 140,
  "bruestung": 90, "status": "bestand" }
```

- `typ`: `tuer`, `fenster` oder `durchgang` (Öffnung ohne Tür).
- `abstand`: vom `von`-Punkt der **Wandachse** bis zur Kante der Öffnung, entlang der
  Wand. Steht auf der Skizze der Abstand ab der Innenecke, zähle die halbe Dicke der
  Querwand dazu.
- `breite`: Rohbaulichte (Maueröffnung).
- `hoehe`: lichte Höhe der Öffnung. Pflicht bei Fenstern, bei Türen und Durchgängen
  Standard 210 (dann in `angenommen` eintragen).
- `bruestung`: Pflicht bei Fenstern, Höhe ab Boden. Fenstertür: `0`.
- Breite, Höhe und Brüstung stehen mit der `id` im Grundriss neben der Öffnung
  («F1  70 × 90, BRH 1.10») und als Masskette in den Schnitten. Halte die `id` kurz
  (`F1`, `T3`), sie ist Teil der Beschriftung.
- `seite`: wohin die Tür aufgeht, gesehen in Richtung von `von` nach `bis`: `links`
  oder `rechts`. `anschlag`: wo die Bänder sind: `anfang` (beim `von`-Punkt) oder
  `ende`.

**Umbau bei Öffnungen:**

| Was passiert | Wand | Öffnung | Im Plan |
|---|---|---|---|
| bleibt | bestand | bestand | schwarz |
| neuer Durchbruch | bestand | neu | Wandstück gelb, Tür/Fenster rot |
| wird zugemauert | bestand | abbruch | Füllung rot, alte Tür gelb |
| Tür in neuer Wand | neu | neu | rot |
| Wand fällt weg | abbruch | bestand | alles gelb (geht mit der Wand) |

Eine neue Öffnung in einer Abbruchwand ist ein Fehler.

### raeume[]

```json
{ "name": "Küche", "punkt": [200, 300] }
{ "name": "Reduit", "punkt": [950, 535], "zustand": "neu" }
```
Räume zeichnest du **nicht** als Fläche. Das Skript findet jede geschlossene Fläche
zwischen den Wänden und gibt ihr den Namen des Punkts, der darin liegt. Den Punkt
setzt du irgendwo in den Raum. `zustand`: `beide` (Standard), `bestand` (gibt es
nur vorher) oder `neu` (gibt es nur nachher). Wird eine Wand abgebrochen, verschmelzen
zwei Räume, und der Plan schreibt «Wohnen / Küche». Soll der neue Raum anders heissen,
setze einen eigenen Punkt mit `zustand: "neu"` und gib den alten Räumen `zustand: "bestand"`.

### objekte[] (Einrichtung, optional)

```json
{ "typ": "wc", "position": [400, 755], "breite": 40, "tiefe": 60, "rotation": 180, "status": "bestand" }
```
- `typ`: `kueche`, `wc`, `lavabo`, `dusche`, `badewanne`, `schrank`, `waschturm`,
  `bett`, `tisch`, `sofa`, `andere`.
- `position`: **Mitte** des Objekts. `breite` entlang der Wand, `tiefe` von der Wand weg.
- `rotation` in Grad, gegen den Uhrzeigersinn. Bei `0` steht die Rückseite unten (y klein),
  also an einer Wand unterhalb. `90`: Rückseite rechts, `180`: oben, `270`: links.
- `bezeichnung` (optional): Text im Symbol.

## schnitte[] (oben, neben projekt, optional)

```json
"schnitte": [
  { "name": "A", "achse": "x", "lage": 220, "blick": "plus" },
  { "name": "B", "achse": "y", "lage": 200, "blick": "plus" }
]
```
- `achse: "x"`: waagrechte Schnittlinie im Grundriss bei y = `lage`; `"y"`: senkrechte bei x = `lage`.
- `blick`: `plus` schaut nach +y bzw. +x (bei Norden oben: nach Norden bzw. Osten), `minus` umgekehrt.
- Weglassen: das Skript legt A–A und B–B selbst. Lege die Linie nie in oder knapp neben
  eine Wand, die in dieselbe Richtung läuft; sie soll Türen und Fenster quer schneiden.

## fotos[] (oben, optional)

```json
"fotos": [ { "datei": "fotos/kueche.jpg", "titel": "Küche Bestand, Blick zum Fenster" } ]
```
Pfad relativ zum Ordner von `plan.json`. Nur JPG und PNG.

## visualisierungen[] (oben, optional)

```json
"visualisierungen": [
  { "vorher": "fotos/kueche.jpg", "nachher": "visualisierungen/kueche_neu.png",
    "titel": "Küche", "wuensche": "Fronten salbeigrün matt, Eiche, Arbeitsplatte Terrazzo" }
]
```
`vorher` ist das Foto vom Bestand, `nachher` das Bild aus dem Bildwerkzeug (siehe
`visualisierung.md`). Pfade relativ zum Ordner von `plan.json`, nur JPG und PNG.
`titel` und `wuensche` sind optional und stehen auf dem Blatt.

## blaetter (oben, optional)

Welche Blätter in die PDF kommen, Standard alle:
`["grundriss", "schnitte", "ansichten", "3d", "visualisierung", "fotos"]`.

## angenommen[] (oben, neben projekt)

Liste aller Masse, die **nicht** von der Skizze oder der Person stammen. Sie stehen
auf dem Plan unter der Legende. Beispiel: `"Raumhöhe 2.50 (Standardwert)"`.

## Standardwerte

Nur verwenden, wenn die Person ausdrücklich zustimmt, und dann in `angenommen` eintragen.

| Bauteil | Wert |
|---|---|
| Aussenwand | 30 |
| tragende Innenwand | 15 |
| Innenwand / Leichtbau | 12 / 10 |
| Raumhöhe Altbau / Neubau | 260 / 250 |
| Zimmertür | 90 × 210 |
| Wohnungstür | 100 × 210 |
| Fenster | Brüstung 90 |
| Küche (Tiefe) | 60 |
| WC | 40 × 60 |
| Lavabo | 60 × 45 |
| Dusche | 90 × 90 |
| Badewanne | 170 × 75 |

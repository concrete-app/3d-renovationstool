"""Geometrie aus dem Datenmodell: Wandflächen nach Status, Räume, Flächen.

Alles in Zentimetern. Zeichnen (grundriss.py) und IFC-Export lesen von hier,
damit beide dieselben Flächen und Räume sehen.

Schweizer Umbau-Konvention (SIA 400):
  Bestand  schwarz/grau   bleibt
  Abbruch  gelb           wird entfernt; auch ein neuer Durchbruch in einer
                          bestehenden Wand ist Abbruch (das Stück Wand fällt weg)
  Neu      rot            wird gebaut; auch das Zumauern einer bestehenden
                          Öffnung (Öffnung mit status "abbruch") ist neu
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from shapely import affinity
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box
from shapely.ops import unary_union

from modell import Geschoss, Objekt, Oeffnung, Wand

LEER = Polygon()
TOLERANZ = 1.0  # cm: Wandenden, die näher als das an einer anderen Wand liegen, gelten als verbunden


def wand_polygon(w: Wand) -> Polygon:
    """Die Wand als Fläche. Die Enden reichen dicke/2 über die Achse hinaus,
    damit sich Ecken und T-Stösse sauber schliessen."""
    return LineString([w.von, w.bis]).buffer(w.dicke / 2, cap_style="square", join_style="mitre")


def oeffnung_polygon(o: Oeffnung, zugabe: float = 0.5) -> Polygon:
    """Die Öffnung als Rechteck über die ganze Wanddicke (etwas breiter, damit sauber geschnitten wird)."""
    w = o.wand
    q = w.dicke / 2 + zugabe
    s0, s1 = o.abstand, o.abstand + o.breite
    return Polygon([w.punkt(s0, -q), w.punkt(s1, -q), w.punkt(s1, q), w.punkt(s0, q)])


def objekt_polygon(b: Objekt) -> Polygon:
    x, y = b.position
    r = box(x - b.breite / 2, y - b.tiefe / 2, x + b.breite / 2, y + b.tiefe / 2)
    return affinity.rotate(r, b.rotation, origin=(x, y))


def vereinigen(teile) -> Polygon | MultiPolygon:
    teile = [t for t in teile if not t.is_empty]
    return unary_union(teile) if teile else LEER


@dataclass
class Wandflaechen:
    """Die Flächen, wie sie im Umbauplan gefüllt werden."""
    bestand: Polygon | MultiPolygon
    abbruch: Polygon | MultiPolygon
    neu: Polygon | MultiPolygon


def wandflaechen(g: Geschoss) -> Wandflaechen:
    roh = {s: vereinigen(wand_polygon(w) for w in g.waende if w.status == s)
           for s in ("bestand", "abbruch", "neu")}
    oeffnungen = vereinigen(oeffnung_polygon(o, zugabe=0.01) for o in g.oeffnungen)
    # Neuer Durchbruch in bestehender Wand: das herausgebrochene Stück ist Abbruch.
    durchbrueche = vereinigen(oeffnung_polygon(o, zugabe=0.01) for o in g.oeffnungen
                               if o.status == "neu" and o.wand.status == "bestand")
    # Bestehende Öffnung wird zugemauert: die Füllung ist neu.
    zumauern = vereinigen(oeffnung_polygon(o, zugabe=0.01) for o in g.oeffnungen
                           if o.wird_zugemauert)

    return umbau_flaechen(roh, oeffnungen, durchbrueche, zumauern)


def umbau_flaechen(roh: dict, oeffnungen, durchbrueche, zumauern) -> Wandflaechen:
    """Die Umbau-Regel für Wandflächen, im Grundriss wie im Schnitt:
    Bestand bleibt, Neu liegt über Abbruch, ein Durchbruch in Bestand ist Abbruch,
    das Zumauern einer Öffnung in Bestand ist Neu. Öffnungen bleiben leer."""
    bestand = roh["bestand"].difference(oeffnungen)
    neu = (roh["neu"].difference(roh["bestand"]).difference(oeffnungen)
           .union(zumauern.intersection(roh["bestand"])))
    abbruch = (roh["abbruch"].difference(roh["bestand"]).difference(roh["neu"])
               .difference(oeffnungen)
               .union(durchbrueche.intersection(roh["bestand"])))
    return Wandflaechen(bestand=bestand, abbruch=abbruch, neu=neu)


def wandenden(w: Wand, g: Geschoss) -> tuple[float, float]:
    """Wie weit der Wandkörper (IFC, 3D, Ansichten) an `von` und `bis` über die Achse hinaus- (+) oder zurückgeht (−), in cm.

    Im Grundriss genügt die Vereinigung der Flächen; im IFC und in 3D ist jede Wand ein
    eigener Körper und darf weder Lücken noch Überschneidungen haben:
      Ecke (Ende trifft Ende):  die Wand, die in der Liste zuerst kommt, läuft um die
                                halbe Dicke der anderen weiter und schliesst die Ecke;
                                die andere endet an ihrer Oberfläche
      T-Stoss (Ende trifft Mitte einer Wand): endet an deren Oberfläche
      freies Ende:              bleibt
    Ein T-Stoss geht vor: treffen sich zwei Wände auf der Mitte einer dritten,
    enden beide an deren Oberfläche.
    """
    reihenfolge = {id(a): i for i, a in enumerate(g.waende)}
    ergebnis = []
    for ende in (w.von, w.bis):
        partner, t_stoss = [], 0.0
        for a in g.waende:
            if a is w:
                continue
            if math.dist(ende, a.von) < 1 or math.dist(ende, a.bis) < 1:
                partner.append(a)
                continue
            dx, dy = ende[0] - a.von[0], ende[1] - a.von[1]
            s = dx * a.richtung[0] + dy * a.richtung[1]   # entlang der Achse von a
            q = dx * a.normale[0] + dy * a.normale[1]     # quer dazu
            if 0 < s < a.laenge and abs(q) < 1:
                t_stoss = max(t_stoss, a.dicke / 2)
        if t_stoss:
            ergebnis.append(-t_stoss)
        elif partner:
            erster = min(partner, key=lambda a: reihenfolge[id(a)])
            if reihenfolge[id(w)] < reihenfolge[id(erster)]:
                ergebnis.append(max(a.dicke for a in partner) / 2)
            else:
                ergebnis.append(-erster.dicke / 2)
        else:
            ergebnis.append(0.0)
    return ergebnis[0], ergebnis[1]


def wandkoerper(w: Wand, g: Geschoss) -> tuple[float, float, Polygon]:
    """Der Grundriss eines Wandkörpers ohne Überschneidung mit anderen Wänden:
    (s_anfang, s_ende, Fläche). s läuft entlang der Achse ab `von`."""
    vorne, hinten = wandenden(w, g)
    s0, s1 = -vorne, w.laenge + hinten
    q = w.dicke / 2
    return s0, s1, Polygon([w.punkt(s0, -q), w.punkt(s1, -q), w.punkt(s1, q), w.punkt(s0, q)])


# --- Räume ----------------------------------------------------------------

@dataclass
class Raumflaeche:
    name: str              # leer, wenn kein Name passt
    flaeche: Polygon       # lichte Fläche (zwischen den Wandoberflächen)
    namen: list[str]

    @property
    def m2(self) -> float:
        return self.flaeche.area / 10_000

    @property
    def ist_rechteck(self) -> bool:
        x0, y0, x1, y1 = self.flaeche.bounds
        return abs((x1 - x0) * (y1 - y0) - self.flaeche.area) < 1.0

    @property
    def lichte_masse(self) -> tuple[float, float]:
        x0, y0, x1, y1 = self.flaeche.bounds
        return (x1 - x0, y1 - y0)

    @property
    def beschriftungspunkt(self) -> tuple[float, float]:
        c = self.flaeche.centroid
        if not self.flaeche.contains(c):
            c = self.flaeche.representative_point()
        return (c.x, c.y)


def raeume(g: Geschoss, zustand: str) -> list[Raumflaeche]:
    """Räume vor (zustand="bestand") oder nach dem Umbau ("neu").

    Ein Raum ist eine geschlossene Fläche zwischen Wänden. Türen zählen dabei
    als Wand, sonst liefe jeder Raum in den nächsten aus. Nach einem Abbruch
    werden zwei Räume zu einem; er trägt dann beide Namen («Küche / Wohnen»).
    """
    gilt = {"bestand": ("bestand", "abbruch"), "neu": ("bestand", "neu")}[zustand]
    waende = vereinigen(wand_polygon(w) for w in g.waende if w.status in gilt)
    polys = list(waende.geoms) if isinstance(waende, MultiPolygon) else [waende]
    flaechen = [Polygon(ring) for p in polys if not p.is_empty for ring in p.interiors]
    flaechen = [f for f in flaechen if f.area > 100]  # unter 10×10 cm: Restfläche einer Ecke

    benannt = [r for r in g.raeume if r.zustand in ("beide", zustand)]
    ergebnis = []
    for f in sorted(flaechen, key=lambda f: (-f.centroid.y, f.centroid.x)):
        namen = [r.name for r in benannt if f.contains(Point(r.punkt))]
        ergebnis.append(Raumflaeche(name=" / ".join(namen), flaeche=f, namen=namen))
    return ergebnis


def warnungen(g: Geschoss) -> list[str]:
    """Hinweise, die das Erzeugen nicht stoppen, aber oft einen Lesefehler zeigen."""
    hinweise = []
    polys = {w.id: wand_polygon(w) for w in g.waende}
    for w in g.waende:
        andere = [p for wid, p in polys.items() if wid != w.id]
        for name, pt in (("von", w.von), ("bis", w.bis)):
            if not any(p.distance(Point(pt)) <= TOLERANZ + w.dicke / 2 for p in andere):
                hinweise.append(f"{g.id}: Wand {w.id} endet bei {name} {list(pt)} frei, "
                                f"ohne andere Wand zu berühren. Stimmt das?")
    for zustand in ("bestand", "neu"):
        alle = raeume(g, zustand)
        for r in g.raeume:
            if r.zustand not in ("beide", zustand):
                continue
            if not any(f.flaeche.contains(Point(r.punkt)) for f in alle):
                hinweise.append(f"{g.id}: Raum «{r.name}» ({zustand}): Punkt {list(r.punkt)} "
                                f"liegt in keiner geschlossenen Fläche")
        for f in alle:
            if not f.namen:
                hinweise.append(f"{g.id}: Fläche {f.m2:.2f} m² ({zustand}) hat keinen Raumnamen")
    return hinweise


def aussenumriss(g: Geschoss) -> Polygon:
    """Aussenkontur aller Wände (für Bodenplatte und Bemassung)."""
    alle = vereinigen(wand_polygon(w) for w in g.waende)
    polys = list(alle.geoms) if isinstance(alle, MultiPolygon) else [alle]
    return unary_union([Polygon(p.exterior) for p in polys])

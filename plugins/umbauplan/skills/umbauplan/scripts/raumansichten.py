"""Raumblatt: Grundriss eines Raums mit Blickpfeilen und die vier Wandansichten A–D von innen.

Eine Wandansicht ist ein Schnitt durch die Raummitte mit Blick auf eine Wand, begrenzt
auf die Raumbreite. Gezeichnet wird mit denselben Funktionen wie die Schnitte
(ansichten.zeichnen); was ausserhalb des Raums liegt, schneidet das Fenster ab.

A schaut zur Planseite oben, B nach rechts, C nach unten, D nach links (im Uhrzeigersinn).
"""

from __future__ import annotations

from matplotlib.patches import Polygon as Dreieck
from matplotlib.patches import Rectangle
from shapely.geometry import LineString, Point, box

import geometrie
from ansichten import (RAND_LINKS, RAND_OBEN, RAND_RECHTS, RAND_UNTEN, Ebene, hoehen,
                       oeffnungen_bemassen, zeichnen)
from blatt import TEXT, ZEICHENFLAECHE, Blatt, Fenster, legende, masskette, plankopf, titel
from grundriss import objekt_zeichnen, oeffnung_zeichnen, waende_zeichnen
from modell import Fehlerhaft, Geschoss, Plan

# Räume mit diesen Objekten bekommen immer ein Raumblatt, auch wenn alles bleibt
NASS_UND_KUECHE = {"kueche", "wc", "lavabo", "dusche", "badewanne", "waschturm"}
MASSSTAEBE = (20, 25, 50, 100)
RAND_GRUNDRISS = 16.0  # mm um den Raumgrundriss: Masskette, Pfeile, Titel


def umbauraeume(plan: Plan) -> list[tuple[Geschoss, geometrie.Raumflaeche]]:
    """Räume nach dem Umbau, die ein Raumblatt bekommen: die aus plan.raumansichten, sonst
    jeder Raum mit Küche oder Sanitär oder mit Einrichtung, die wegfällt oder neu kommt."""
    alle = [(g, r) for g in plan.geschosse for r in geometrie.raeume(g, "neu")]
    if plan.raumansichten is not None:
        ergebnis, fehlt = [], []
        for name in plan.raumansichten:
            treffer = [(g, r) for g, r in alle if name in r.namen or name == r.name]
            if treffer:
                ergebnis += [t for t in treffer if t not in ergebnis]
            else:
                fehlt.append(name)
        if fehlt:
            vorhanden = ", ".join(sorted({r.name for _, r in alle if r.name}))
            raise Fehlerhaft([f"raumansichten: Raum {n!r} gibt es nach dem Umbau nicht "
                              f"(vorhanden: {vorhanden})" for n in fehlt])
        return ergebnis
    ergebnis = []
    for g, r in alle:
        drin = [b for b in g.objekte if r.flaeche.contains(geometrie.objekt_polygon(b).centroid)]
        if any(b.status != "bestand" or b.typ in NASS_UND_KUECHE for b in drin):
            ergebnis.append((g, r))
    return ergebnis


def ebenen(r: geometrie.Raumflaeche) -> list[tuple[str, Ebene]]:
    x0, y0, x1, y1 = r.flaeche.bounds
    xm, ym = (x0 + x1) / 2, (y0 + y1) / 2
    # blick "plus" schaut zu grösserem y bzw. x, "minus" zu kleinerem
    return [("A", Ebene("x", ym, "plus")), ("B", Ebene("y", xm, "plus")),
            ("C", Ebene("x", ym, "minus")), ("D", Ebene("y", xm, "minus"))]


def _umfassung(g: Geschoss, r: geometrie.Raumflaeche) -> tuple[float, float, float, float]:
    """Raum samt den Wänden rundherum (x0, y0, x1, y1): je Seite so weit, wie die Wand dick ist,
    die dort an den Raum grenzt. Gemessen auf drei Linien quer zur Seite; die kürzeste zählt
    (eine Linie kann in einer Tür oder längs in einer anstossenden Querwand liegen)."""
    x0, y0, x1, y1 = r.flaeche.bounds
    waende = geometrie.vereinigen(geometrie.wand_polygon(w) for w in g.waende if w.status != "abbruch")
    tief = 100.0  # dicker ist keine Wand

    def dicke(start: tuple[float, float], richtung: tuple[float, float]) -> float:
        ende = (start[0] + richtung[0] * tief, start[1] + richtung[1] * tief)
        teil = waende.intersection(LineString([start, ende]))
        teile = [t for t in getattr(teil, "geoms", [teil]) if not t.is_empty and t.length > 0]
        anliegend = [t for t in teile if Point(start).distance(t) < 1]
        return max((Point(start).distance(Point(c)) for t in anliegend for c in t.coords), default=0.0)

    def seite(punkte, richtung) -> float:
        werte = [d for d in (dicke(p, richtung) for p in punkte) if d > 0]
        return min(werte, default=0.0)

    xs = [x0 + (x1 - x0) * f for f in (0.25, 0.5, 0.75)]
    ys = [y0 + (y1 - y0) * f for f in (0.25, 0.5, 0.75)]
    links = seite([(x0, y) for y in ys], (-1, 0))
    rechts = seite([(x1, y) for y in ys], (1, 0))
    unten = seite([(x, y0) for x in xs], (0, -1))
    oben = seite([(x, y1) for x in xs], (0, 1))
    return x0 - links, y0 - unten, x1 + rechts, y1 + oben


def _ausdehnung(g: Geschoss, r: geometrie.Raumflaeche, e: Ebene) -> tuple[float, float, float, float]:
    """(u0, z0, u1, z1): Raumbreite plus die geschnittenen Seitenwände, Boden bis Decke."""
    u0, u1 = e.u_bereich(box(*_umfassung(g, r)))
    return u0, g.kote - g.deckenstaerke, u1, g.kote + g.raumhoehe + g.deckenstaerke


def _grundriss_grenzen(g: Geschoss, r: geometrie.Raumflaeche) -> tuple[float, float, float, float]:
    return _umfassung(g, r)


def _zuschneiden(ax, vorher: set, grenzen: tuple[float, float, float, float]) -> None:
    """Alles, was seit `vorher` gezeichnet wurde, auf das Rechteck `grenzen` (cm) begrenzen:
    Nachbarräume, Decken und Wände ausserhalb des Raums verschwinden."""
    x0, y0, x1, y1 = grenzen
    rahmen = Rectangle((x0, y0), x1 - x0, y1 - y0, transform=ax.transData)
    for a in [*ax.patches, *ax.lines, *ax.texts]:
        if a not in vorher:
            a.set_clip_path(rahmen)


def _gezeichnet(ax) -> set:
    return {*ax.patches, *ax.lines, *ax.texts}


ANORDNUNGEN = ((2, 2), (1, 4))  # (Spalten, Zeilen) der vier Ansichten neben dem Raumgrundriss


def _massstab(g: Geschoss, r: geometrie.Raumflaeche, wunsch: int) -> tuple[int, tuple[int, int]]:
    """Kleinster Massstab ≥ wunsch, bei dem Raumgrundriss und vier Ansichten auf A3 passen,
    und die Anordnung der Ansichten dazu."""
    fx0, fy0, fx1, fy1 = ZEICHENFLAECHE
    gx0, gy0, gx1, gy1 = _grundriss_grenzen(g, r)
    sichten = [_ausdehnung(g, r, e) for _, e in ebenen(r)]
    vb = max(u1 - u0 for u0, _, u1, _ in sichten)
    vh = max(z1 - z0 for _, z0, _, z1 in sichten)
    for m in [s for s in MASSSTAEBE if s >= wunsch]:
        k = m / 10
        for spalten, zeilen in ANORDNUNGEN:
            breite = (gx1 - gx0) / k + 2 * RAND_GRUNDRISS + spalten * (vb / k + RAND_LINKS + RAND_RECHTS)
            hoehe_sicht = zeilen * (vh / k + RAND_UNTEN + RAND_OBEN)
            hoehe_gr = (gy1 - gy0) / k + 2 * RAND_GRUNDRISS
            if breite <= fx1 - fx0 and max(hoehe_sicht, hoehe_gr) <= fy1 - fy0:
                return m, (spalten, zeilen)
    raise Fehlerhaft([f"Raum {r.name or '?'}: Wandansichten passen auch 1:{MASSSTAEBE[-1]} nicht auf A3. "
                      "Stimmen die Masse (cm)? Sonst den Raum unter raumansichten weglassen."])


def _pfeile(fenster: Fenster, r: geometrie.Raumflaeche) -> None:
    """Blickpfeile A–D in der Raummitte: Dreieck zeigt zur Wand, Buchstabe davor."""
    ax = fenster.ax
    cx, cy = r.beschriftungspunkt
    a, s = fenster.mm(5), fenster.mm(1.8)
    for buchstabe, (dx, dy) in zip("ABCD", ((0, 1), (1, 0), (0, -1), (-1, 0))):
        px, py = cx + dx * a, cy + dy * a                     # Spitze
        bx, by = cx + dx * (a - 1.6 * s), cy + dy * (a - 1.6 * s)
        qx, qy = -dy * s, dx * s
        ax.add_patch(Dreieck([(px, py), (bx + qx, by + qy), (bx - qx, by - qy)], closed=True,
                             facecolor=TEXT, edgecolor=TEXT, linewidth=0.3, zorder=8))
        ax.text(cx + dx * (a + fenster.mm(2.5)), cy + dy * (a + fenster.mm(2.5)), buchstabe,
                ha="center", va="center", fontsize=8, fontweight="bold", color=TEXT, zorder=8)


def _raumgrundriss(blatt: Blatt, g: Geschoss, r: geometrie.Raumflaeche, links: float, unten: float,
                   m: int) -> None:
    k = m / 10
    x0, y0, x1, y1 = _grundriss_grenzen(g, r)
    rand = RAND_GRUNDRISS * k
    fenster = blatt.fenster(links, unten, (x0 - rand, x1 + rand), (y0 - rand, y1 + rand), m)
    ax = fenster.ax
    waende_zeichnen(ax, g)
    for o in g.oeffnungen:
        oeffnung_zeichnen(ax, o)
    for b in g.objekte:
        objekt_zeichnen(ax, b)
    _zuschneiden(ax, set(), (x0, y0, x1, y1))
    _pfeile(fenster, r)
    lx0, ly0, lx1, ly1 = r.flaeche.bounds
    masskette(fenster, [lx0, lx1], "x", y0 - fenster.mm(5), -1, y0)
    masskette(fenster, [ly0, ly1], "y", x0 - fenster.mm(5), -1, x0)
    titel(fenster, x0, y0 - fenster.mm(9), f"Grundriss {r.name or ''}".strip())


def raumblatt(plan: Plan, g: Geschoss, r: geometrie.Raumflaeche, nummer: int,
              entwurf: bool = False) -> tuple[Blatt, int]:
    m, (spalten, zeilen) = _massstab(g, r, 20)
    k = m / 10
    fx0, fy0, fx1, fy1 = ZEICHENFLAECHE
    gx0, gy0, gx1, gy1 = _grundriss_grenzen(g, r)
    gb = (gx1 - gx0) / k + 2 * RAND_GRUNDRISS
    gh = (gy1 - gy0) / k + 2 * RAND_GRUNDRISS
    blatt = Blatt()
    _raumgrundriss(blatt, g, r, fx0, fy0 + (fy1 - fy0 - gh) / 2, m)

    zw, zh = (fx1 - fx0 - gb) / spalten, (fy1 - fy0) / zeilen
    nur_geschoss = [g]
    for i, (buchstabe, e) in enumerate(ebenen(r)):
        sp, ze = i % spalten, i // spalten
        u0, z0, u1, z1 = _ausdehnung(g, r, e)
        xlim = (u0 - RAND_LINKS * k, u1 + RAND_RECHTS * k)
        ylim = (z0 - RAND_UNTEN * k, z1 + RAND_OBEN * k)
        b, h = (xlim[1] - xlim[0]) / k, (ylim[1] - ylim[0]) / k
        links = fx0 + gb + sp * zw + (zw - b) / 2
        unten = fy1 - (ze + 1) * zh + (zh - h) / 2
        fenster = blatt.fenster(links, unten, xlim, ylim, m)
        zeichnen(fenster, plan, e, ansicht=False)
        _zuschneiden(fenster.ax, set(), (u0, z0, u1, z1))
        vorher = _gezeichnet(fenster.ax)
        oeffnungen_bemassen(fenster, plan, e)  # Ketten von Öffnungen ausserhalb des Raums fallen weg
        _zuschneiden(fenster.ax, vorher, (u0 - fenster.mm(2), z0, u1 + fenster.mm(2), z1))
        hoehen(fenster, plan, u0, u1, schnitt=True, geschosse=nur_geschoss)
        titel(fenster, u0, z0 - fenster.mm(5), f"Ansicht {buchstabe}")

    name = r.name or "Raum"
    plankopf(blatt, plan, f"{name} – Wandansichten A–D", f"{plan.projekt.plannummer}-R{nummer}",
             f"1:{m}", entwurf)
    legende(blatt, plan, "Masse in m. Koten ab Boden fertig ± 0.00. Ansichten von innen, "
                         "Blickrichtung siehe Pfeile im Grundriss.")
    return blatt, m


def raumansichten_blaetter(plan: Plan, entwurf: bool = False):
    """Pro Umbauraum ein Blatt: (Blatt, Raumname, Massstab)."""
    for n, (g, r) in enumerate(umbauraeume(plan), 1):
        blatt, m = raumblatt(plan, g, r, n, entwurf)
        yield blatt, r.name or "Raum", m

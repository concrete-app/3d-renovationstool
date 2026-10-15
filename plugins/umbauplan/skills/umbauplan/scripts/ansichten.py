"""Schnitte und Fassadenansichten: das Modell auf eine senkrechte Ebene projiziert.

Eine Ansicht ist ein Schnitt, dessen Ebene ausserhalb des Gebäudes liegt: es wird
nichts geschnitten, man sieht nur. Darum zeichnet dieselbe Funktion beides.

Koordinaten in der Ebene: u waagrecht (nach rechts, wie der Betrachter es sieht),
z senkrecht (Höhe, cm ab ± 0.00). `tiefe` ist der Abstand hinter der Ebene in
Blickrichtung.

Geschnittene Bauteile werden nach Status gefüllt (wie im Grundriss). Was hinter
der Ebene liegt, wird als weiss gefüllte Fläche mit dünner Kontur gezeichnet,
von hinten nach vorne: Nahes verdeckt Fernes (Maler-Verfahren). Das genügt für
Wände, die sich nicht durchdringen, und das stellen wandkoerper() sicher.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from shapely.geometry import LineString, MultiLineString, Polygon, box

import geometrie
from blatt import (FUELLUNG, KONTUR, PT_DICK, PT_FEIN, PT_MITTEL, STRICH, SYMBOL, TEXT,
                   ZEICHENFLAECHE, Blatt, Fenster, flaeche, kote, legende, linie, masskette, passt,
                   plankopf, titel)
from modell import Fehlerhaft, Geschoss, Oeffnung, Plan, Schnitt, Wand

GROSS = 1e5  # cm, «unendlich» für Halbebenen

# Rand um jede Zeichnung (mm): links Koten, rechts Höhenkette, unten Titel
RAND_LINKS, RAND_RECHTS, RAND_UNTEN, RAND_OBEN = 24.0, 22.0, 14.0, 6.0


@dataclass
class Ebene:
    achse: str   # "x": Ebene entlang x (Linie y = lage), "y": entlang y (Linie x = lage)
    lage: float
    blick: str   # "plus" | "minus"

    def u(self, x: float, y: float) -> float:
        if self.achse == "x":
            return x if self.blick == "plus" else -x
        return -y if self.blick == "plus" else y

    def tiefe(self, x: float, y: float) -> float:
        d = (y if self.achse == "x" else x) - self.lage
        return d if self.blick == "plus" else -d

    @property
    def richtung(self) -> tuple[float, float]:
        """Einheitsvektor entlang der Ebene im Grundriss."""
        return (1.0, 0.0) if self.achse == "x" else (0.0, 1.0)

    def linie(self) -> LineString:
        if self.achse == "x":
            return LineString([(-GROSS, self.lage), (GROSS, self.lage)])
        return LineString([(self.lage, -GROSS), (self.lage, GROSS)])

    def dahinter(self) -> Polygon:
        """Die Halbebene hinter der Ebene (in Blickrichtung)."""
        if self.achse == "x":
            return (box(-GROSS, self.lage, GROSS, GROSS) if self.blick == "plus"
                    else box(-GROSS, -GROSS, GROSS, self.lage))
        return (box(self.lage, -GROSS, GROSS, GROSS) if self.blick == "plus"
                else box(-GROSS, -GROSS, self.lage, GROSS))

    def u_bereich(self, geom) -> tuple[float, float]:
        pts = _punkte(geom)
        us = [self.u(x, y) for x, y in pts]
        return min(us), max(us)

    def tiefe_min(self, geom) -> float:
        return min(self.tiefe(x, y) for x, y in _punkte(geom))


def _punkte(geom) -> list[tuple[float, float]]:
    if hasattr(geom, "geoms"):
        return [p for g in geom.geoms for p in _punkte(g)]
    if isinstance(geom, Polygon):
        return list(geom.exterior.coords)
    return list(geom.coords)


def _strecken(geom) -> list[LineString]:
    if geom.is_empty:
        return []
    if isinstance(geom, LineString):
        return [geom]
    if isinstance(geom, MultiLineString):
        return list(geom.geoms)
    return [g for g in getattr(geom, "geoms", []) if isinstance(g, LineString)]


def oeffnung_u(o: Oeffnung, e: Ebene) -> tuple[float, float]:
    a = e.u(*o.wand.punkt(o.abstand))
    b = e.u(*o.wand.punkt(o.abstand + o.breite))
    return min(a, b), max(a, b)


def parallel(w: Wand, e: Ebene) -> bool:
    rx, ry = e.richtung
    return abs(w.richtung[0] * rx + w.richtung[1] * ry) > 0.7


# --- Was die Ebene schneidet ----------------------------------------------

def schnittflaechen(plan: Plan, e: Ebene) -> tuple[geometrie.Wandflaechen, list[Polygon], list]:
    """Geschnittene Wände nach Status, geschnittene Decken und Glaslinien, in (u, z)."""
    linie_e = e.linie()
    roh = {s: [] for s in ("bestand", "abbruch", "neu")}
    oeff, durch, zumauern, decken = [], [], [], []
    glas = []  # (u, z_unten, z_oben, status) geschnittener Fenster
    for g in plan.geschosse:
        z0 = g.kote
        for w in g.waende:
            for seg in _strecken(geometrie.wand_polygon(w).intersection(linie_e)):
                ua, ub = e.u_bereich(seg)
                roh[w.status].append(box(ua, z0, ub, z0 + w.hoehe))
        for o in g.oeffnungen:
            if parallel(o.wand, e):  # Ebene läuft entlang der Wand: schneidet die Öffnung nicht quer
                continue
            for seg in _strecken(geometrie.oeffnung_polygon(o, zugabe=0.01).intersection(linie_e)):
                ua, ub = e.u_bereich(seg)
                r = box(ua, z0 + o.bruestung, ub, z0 + o.bruestung + o.hoehe)
                oeff.append(r)
                if o.status == "neu" and o.wand.status == "bestand":
                    durch.append(r)
                if o.wird_zugemauert:
                    zumauern.append(r)
                elif o.typ == "fenster":
                    glas.append(((ua + ub) / 2, z0 + o.bruestung, z0 + o.bruestung + o.hoehe,
                                 o.wirksamer_status))
        umriss = geometrie.aussenumriss(g)
        for seg in _strecken(umriss.intersection(linie_e)):
            ua, ub = e.u_bereich(seg)
            decken.append(box(ua, z0 - g.deckenstaerke, ub, z0))
            if not _geschoss_darueber(plan, g):
                decken.append(box(ua, z0 + g.raumhoehe, ub, z0 + g.raumhoehe + g.deckenstaerke))
    v = geometrie.vereinigen
    f = geometrie.umbau_flaechen({s: v(r) for s, r in roh.items()}, v(oeff), v(durch), v(zumauern))
    return f, decken, glas


def _geschoss_darueber(plan: Plan, g: Geschoss) -> bool:
    oben = g.kote + g.raumhoehe
    return any(abs((h.kote - h.deckenstaerke) - oben) < 1 for h in plan.geschosse if h is not g)


# --- Was hinter der Ebene liegt -------------------------------------------

@dataclass
class Sichtflaeche:
    tiefe: float
    flaeche: Polygon      # in (u, z), Öffnungen schon ausgeschnitten
    status: str
    details: list         # (art, Polygon, status): Öffnungsrahmen, Zumauerungen


def sichtflaechen(plan: Plan, e: Ebene, ansicht: bool) -> list[Sichtflaeche]:
    hinten = e.dahinter()
    teile: list[Sichtflaeche] = []
    for g in plan.geschosse:
        z0 = g.kote
        for w in g.waende:
            _, _, koerper = geometrie.wandkoerper(w, g)
            sicht = koerper.intersection(hinten)
            if sicht.is_empty or sicht.area < 1:
                continue
            ua, ub = e.u_bereich(sicht)
            if ub - ua < 0.5:
                continue
            fl = box(ua, z0, ub, z0 + w.hoehe)
            details = []
            if parallel(w, e):
                for o in (o for o in g.oeffnungen if o.wand is w):
                    oa, ob = oeffnung_u(o, e)
                    r = box(oa, z0 + o.bruestung, ob, z0 + o.bruestung + o.hoehe)
                    if o.wird_zugemauert:
                        details.append(("zumauern", r, "neu"))
                        continue
                    # Durch Fenster sieht man nicht ins Haus (Glas), durch Türen im Schnitt schon.
                    # In der Fassadenansicht bleibt alles geschlossen.
                    if not ansicht and o.typ != "fenster":
                        fl = fl.difference(r)
                    details.append((o.typ, r, o.wirksamer_status))
            teile.append(Sichtflaeche(e.tiefe_min(sicht), fl, w.status, details))
        for b in g.objekte:
            sicht = geometrie.objekt_polygon(b).intersection(hinten)
            if sicht.is_empty or sicht.area < 1:
                continue
            ua, ub = e.u_bereich(sicht)
            teile.append(Sichtflaeche(e.tiefe_min(sicht), box(ua, z0, ub, z0 + b.hoehe), b.status, []))
        if ansicht:
            umriss = geometrie.aussenumriss(g)
            ua, ub = e.u_bereich(umriss)
            teile.append(Sichtflaeche(e.tiefe_min(umriss), box(ua, z0 - g.deckenstaerke, ub, z0),
                                      "bestand", []))
            if not _geschoss_darueber(plan, g):
                teile.append(Sichtflaeche(e.tiefe_min(umriss),
                                          box(ua, z0 + g.raumhoehe, ub, z0 + g.raumhoehe + g.deckenstaerke),
                                          "bestand", []))
    return sorted(teile, key=lambda t: -t.tiefe)


def _rahmen(ax, art: str, r: Polygon, status: str, z: float) -> None:
    farbe, strich = SYMBOL[status], STRICH[status]
    x0, y0, x1, y1 = r.bounds
    kw = dict(color=farbe, linestyle=strich, zorder=z)
    if art == "zumauern":
        flaeche(ax, r, facecolor="white", edgecolor=SYMBOL["neu"], linewidth=PT_FEIN, zorder=z)
        linie(ax, (x0, y0), (x1, y1), linewidth=PT_FEIN, color=SYMBOL["neu"], zorder=z)
        return
    flaeche(ax, r, facecolor="none", edgecolor=farbe, linewidth=PT_MITTEL, linestyle=strich, zorder=z)
    if art == "fenster":
        i = 5.0
        flaeche(ax, box(x0 + i, y0 + i, x1 - i, y1 - i), facecolor="none", edgecolor=farbe,
                linewidth=PT_FEIN, linestyle=strich, zorder=z)
        if x1 - x0 > 100:  # zweiflüglig
            linie(ax, ((x0 + x1) / 2, y0 + i), ((x0 + x1) / 2, y1 - i), linewidth=PT_FEIN, **kw)
    elif art == "tuer":
        linie(ax, (x0, y0), ((x0 + x1) / 2, y1), linewidth=0.25, **kw)
        linie(ax, (x1, y0), ((x0 + x1) / 2, y1), linewidth=0.25, **kw)


def zeichnen(fenster: Fenster, plan: Plan, e: Ebene, ansicht: bool) -> None:
    ax = fenster.ax
    for i, t in enumerate(sichtflaechen(plan, e, ansicht)):
        z = 2 + i * 0.001
        kontur = SYMBOL[t.status] if t.status != "bestand" else TEXT
        flaeche(ax, t.flaeche, facecolor="white", edgecolor=kontur, linewidth=PT_FEIN,
                linestyle=STRICH[t.status], zorder=z)
        for art, r, status in t.details:
            _rahmen(ax, art, r, status, z + 0.0005)
    if ansicht:
        return
    f, decken, glas = schnittflaechen(plan, e)
    for d in decken:
        flaeche(ax, d, facecolor=FUELLUNG["bestand"], edgecolor=KONTUR["bestand"],
                linewidth=PT_MITTEL, zorder=5)
    flaeche(ax, f.abbruch, facecolor=FUELLUNG["abbruch"], edgecolor=KONTUR["abbruch"],
            linewidth=PT_FEIN, linestyle=(0, (4, 2)), zorder=5.1)
    flaeche(ax, f.bestand, facecolor=FUELLUNG["bestand"], edgecolor=KONTUR["bestand"],
            linewidth=PT_MITTEL, zorder=5.2)
    flaeche(ax, f.neu, facecolor=FUELLUNG["neu"], edgecolor=KONTUR["neu"], linewidth=PT_MITTEL, zorder=5.3)
    for u, za, zb, status in glas:
        for du in (-1.5, 1.5):
            linie(ax, (u + du, za), (u + du, zb), color=SYMBOL[status], linewidth=PT_FEIN, zorder=5.4)


# --- Ausdehnung, Koten, Höhenkette ----------------------------------------

def ausdehnung(plan: Plan, e: Ebene) -> tuple[float, float, float, float]:
    """(u0, z0, u1, z1) des ganzen Gebäudes in dieser Ebene."""
    us = [u for g in plan.geschosse for w in g.waende for u in e.u_bereich(geometrie.wand_polygon(w))]
    z0 = min(g.kote - g.deckenstaerke for g in plan.geschosse)
    z1 = max(g.kote + max([g.raumhoehe] + [w.hoehe for w in g.waende]) + g.deckenstaerke
             for g in plan.geschosse)
    return min(us), z0, max(us), z1


def hoehen(fenster: Fenster, plan: Plan, u0: float, u1: float, schnitt: bool) -> None:
    """Koten links, Höhenkette rechts: Boden, Decke je Geschoss."""
    punkte = []
    for g in plan.geschosse:
        kote(fenster, u0 - fenster.mm(9), g.kote)
        kote(fenster, u0 - fenster.mm(9), g.kote + g.raumhoehe)
        punkte += [g.kote - g.deckenstaerke, g.kote, g.kote + g.raumhoehe]
        if not _geschoss_darueber(plan, g):
            punkte.append(g.kote + g.raumhoehe + g.deckenstaerke)
    masskette(fenster, punkte, "y", u1 + fenster.mm(8), +1, u1)
    if not schnitt:
        z = min(g.kote - g.deckenstaerke for g in plan.geschosse)
        linie(fenster.ax, (u0 - fenster.mm(4), z), (u1 + fenster.mm(4), z), color=TEXT,
              linewidth=PT_DICK * 1.5, zorder=6)


# --- Schnittlagen bestimmen -----------------------------------------------

def schnitte_bestimmen(plan: Plan) -> list[Schnitt]:
    """Die Schnitte aus plan.json, sonst A–A (waagrecht) und B–B (senkrecht) dort, wo sie
    möglichst viele Öffnungen und Umbauteile schneiden und in keiner Wand längs laufen."""
    if plan.schnitte:
        return plan.schnitte
    alle = [w for g in plan.geschosse for w in g.waende]
    polys = [geometrie.wand_polygon(w) for w in alle]
    x0 = min(p.bounds[0] for p in polys)
    y0 = min(p.bounds[1] for p in polys)
    x1 = max(p.bounds[2] for p in polys)
    y1 = max(p.bounds[3] for p in polys)
    ergebnis = []
    for name, achse, a, b in (("A", "x", y0, y1), ("B", "y", x0, x1)):
        bester, wert_bester = None, -1.0
        mitte = (a + b) / 2
        lage = a + 20
        while lage <= b - 20:
            e = Ebene(achse, lage, "plus")
            wert = _schnittwert(plan, e)
            if wert is not None:
                wert -= abs(lage - mitte) / (b - a)  # bei Gleichstand: näher an der Mitte
                if wert > wert_bester:
                    bester, wert_bester = lage, wert
            lage += 5
        if bester is not None:
            ergebnis.append(Schnitt(name=name, achse=achse, lage=round(bester), blick="plus"))
    return ergebnis


def _schnittwert(plan: Plan, e: Ebene) -> float | None:
    linie_e = e.linie()
    wert = 0.0
    for g in plan.geschosse:
        for w in g.waende:
            p = geometrie.wand_polygon(w)
            if parallel(w, e) and p.buffer(10).intersects(linie_e):
                return None  # läuft in oder knapp neben einer Wand: unlesbar
            if p.intersects(linie_e):
                wert += 1 if w.status != "bestand" else 0.2
        for o in g.oeffnungen:
            if not parallel(o.wand, e) and geometrie.oeffnung_polygon(o).buffer(-5).intersects(linie_e):
                wert += 2 if o.typ == "fenster" else 1.5
    return wert


# --- Blätter --------------------------------------------------------------

def _himmelsrichtung(plan: Plan, normale: tuple[float, float]) -> str | None:
    """Name der Fassade, deren Aussenseite in Richtung `normale` (Grundriss) zeigt."""
    w = plan.projekt.nordwinkel
    if w is None:
        return None
    a = math.radians(w)
    nord, ost = (math.sin(a), math.cos(a)), (math.cos(a), -math.sin(a))
    peilung = math.degrees(math.atan2(normale[0] * ost[0] + normale[1] * ost[1],
                                      normale[0] * nord[0] + normale[1] * nord[1])) % 360
    namen = ("Nord", "Nordost", "Ost", "Südost", "Süd", "Südwest", "West", "Nordwest")
    return namen[int((peilung + 22.5) // 45) % 8]


def fassaden(plan: Plan) -> list[tuple[str, Ebene]]:
    """Die vier Ansichten. Die Ebene liegt vor der Fassade, der Blick geht aufs Gebäude."""
    alle = [geometrie.wand_polygon(w) for g in plan.geschosse for w in g.waende]
    x0 = min(p.bounds[0] for p in alle) - 100
    y0 = min(p.bounds[1] for p in alle) - 100
    x1 = max(p.bounds[2] for p in alle) + 100
    y1 = max(p.bounds[3] for p in alle) + 100
    seiten = (
        (Ebene("x", y0, "plus"), (0, -1), "unten"),
        (Ebene("y", x1, "minus"), (1, 0), "rechts"),
        (Ebene("x", y1, "minus"), (0, 1), "oben"),
        (Ebene("y", x0, "plus"), (-1, 0), "links"),
    )
    ergebnis = []
    for e, normale, plan_seite in seiten:
        richtung = _himmelsrichtung(plan, normale)
        ergebnis.append((f"Ansicht {richtung}" if richtung else f"Ansicht Planseite {plan_seite}", e))
    return ergebnis


def _anordnen(blatt: Blatt, plan: Plan, zeichnungen: list[tuple[str, Ebene]], anordnung, ansicht: bool,
              massstab: int) -> None:
    spalten, zeilen = anordnung
    fx0, fy0, fx1, fy1 = ZEICHENFLAECHE
    zw, zh = (fx1 - fx0) / spalten, (fy1 - fy0) / zeilen
    k = massstab / 10
    for i, (name, e) in enumerate(zeichnungen):
        sp, ze = i % spalten, i // spalten
        u0, z0, u1, z1 = ausdehnung(plan, e)
        xlim = (u0 - RAND_LINKS * k, u1 + RAND_RECHTS * k)
        ylim = (z0 - RAND_UNTEN * k, z1 + RAND_OBEN * k)
        b, h = (xlim[1] - xlim[0]) / k, (ylim[1] - ylim[0]) / k
        links = fx0 + sp * zw + (zw - b) / 2
        unten = fy1 - (ze + 1) * zh + (zh - h) / 2
        fenster = blatt.fenster(links, unten, xlim, ylim, massstab)
        zeichnen(fenster, plan, e, ansicht)
        hoehen(fenster, plan, u0, u1, schnitt=not ansicht)
        titel(fenster, u0, z0 - fenster.mm(5), name)


def _massstab(plan: Plan, zeichnungen, anordnung) -> int:
    groessen = []
    for _, e in zeichnungen:
        u0, z0, u1, z1 = ausdehnung(plan, e)
        groessen.append((u1 - u0, z1 - z0))
    m = passt(groessen, (RAND_LINKS + RAND_RECHTS, RAND_UNTEN + RAND_OBEN), anordnung,
              plan.projekt.massstab)
    if m is None:
        raise Fehlerhaft(["Schnitte/Ansichten passen auch 1:200 nicht auf A3. Stimmen die Masse (cm)?"])
    return m


def schnitte_blatt(plan: Plan, schnitte: list[Schnitt], entwurf: bool = False) -> tuple[Blatt, int]:
    zeichnungen = [(f"Schnitt {s.name}–{s.name}", Ebene(s.achse, s.lage, s.blick)) for s in schnitte]
    anordnung = (1, len(zeichnungen))
    try:
        m = _massstab(plan, zeichnungen, anordnung)
    except Fehlerhaft:
        anordnung = (2, math.ceil(len(zeichnungen) / 2))
        m = _massstab(plan, zeichnungen, anordnung)
    blatt = Blatt()
    _anordnen(blatt, plan, zeichnungen, anordnung, ansicht=False, massstab=m)
    namen = ", ".join(f"{s.name}–{s.name}" for s in schnitte)
    plankopf(blatt, plan, f"Schnitte {namen} – Umbau", f"{plan.projekt.plannummer}-S", f"1:{m}", entwurf)
    legende(blatt, plan, "Masse in m. Koten ab Boden fertig ± 0.00. Schnittlage siehe Grundriss.")
    return blatt, m


def ansichten_blatt(plan: Plan, entwurf: bool = False) -> tuple[Blatt, int]:
    zeichnungen = fassaden(plan)
    m = _massstab(plan, zeichnungen, (2, 2))
    blatt = Blatt()
    _anordnen(blatt, plan, zeichnungen, (2, 2), ansicht=True, massstab=m)
    plankopf(blatt, plan, "Ansichten – Umbau", f"{plan.projekt.plannummer}-A", f"1:{m}", entwurf)
    legende(blatt, plan, "Masse in m. Koten ab Boden fertig ± 0.00. Terrain nicht erfasst.")
    return blatt, m

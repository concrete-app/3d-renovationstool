"""Zeichnet den Umbau-Grundriss eines Geschosses: im echten Massstab, mit Massketten.

Das Blatt (Rahmen, Plankopf, Legende) kommt aus blatt.py; hier steht, was nur
der Grundriss braucht: Wandflächen nach Status, Türen, Fenster, Einrichtung,
Raumbeschriftung, Masse der Öffnungen, Aussenmassketten und die Schnittlinien.
"""

from __future__ import annotations

import math

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Ellipse
from shapely.geometry import LineString, Polygon, box

import geometrie
from blatt import (FUELLUNG, KONTUR, PT_DICK, PT_FEIN, PT_MITTEL, STRICH, SYMBOL, TEXT, GRAU,
                   ZEICHENFLAECHE, Blatt, Fenster, flaeche, legende, linie, masskette, nordpfeil,
                   passt, plankopf)
from modell import Fehlerhaft, Geschoss, Objekt, Oeffnung, Plan, Schnitt, mass_text

# Platz um den Grundriss für die Massketten (mm): unten und links drei Ketten mit Total,
# oben und rechts höchstens zwei.
RAND = {"links": 30.0, "unten": 30.0, "rechts": 22.0, "oben": 22.0}
BESCHRIFTUNG_PT = 5.5  # Masse der Öffnungen


def grenzen(g: Geschoss) -> tuple[float, float, float, float]:
    teile = [geometrie.wand_polygon(w) for w in g.waende] + [geometrie.objekt_polygon(b) for b in g.objekte]
    x0 = min(t.bounds[0] for t in teile)
    y0 = min(t.bounds[1] for t in teile)
    x1 = max(t.bounds[2] for t in teile)
    y1 = max(t.bounds[3] for t in teile)
    return x0, y0, x1, y1


def massstab_waehlen(g: Geschoss, wunsch: int) -> int:
    """Der gewünschte Massstab, sonst der nächstgrössere, in den das Geschoss auf A3 passt."""
    x0, y0, x1, y1 = grenzen(g)
    m = passt([(x1 - x0, y1 - y0)], (RAND["links"] + RAND["rechts"], RAND["unten"] + RAND["oben"]),
              (1, 1), wunsch)
    if m is None:
        raise Fehlerhaft([f"{g.id}: Der Grundriss ({(x1 - x0) / 100:.1f} × {(y1 - y0) / 100:.1f} m) "
                          f"passt auch 1:200 nicht auf A3. Stimmen die Masse (cm)?"])
    return m


def fenster_grundriss(blatt: Blatt, g: Geschoss, massstab: int) -> Fenster:
    """Das massstäbliche Fenster für den Grundriss, mittig in der Zeichenfläche."""
    x0, y0, x1, y1 = grenzen(g)
    k = massstab / 10  # cm pro Papier-mm
    xlim = (x0 - RAND["links"] * k, x1 + RAND["rechts"] * k)
    ylim = (y0 - RAND["unten"] * k, y1 + RAND["oben"] * k)
    breite = (xlim[1] - xlim[0]) / k
    hoehe = (ylim[1] - ylim[0]) / k
    fx0, fy0, fx1, fy1 = ZEICHENFLAECHE
    return blatt.fenster(fx0 + (fx1 - fx0 - breite) / 2, fy0 + (fy1 - fy0 - hoehe) / 2,
                         xlim, ylim, massstab)


# --- Wände und Öffnungen --------------------------------------------------

def waende_zeichnen(ax, g: Geschoss) -> None:
    f = geometrie.wandflaechen(g)
    flaeche(ax, f.abbruch, facecolor=FUELLUNG["abbruch"], edgecolor=KONTUR["abbruch"],
            linewidth=PT_FEIN, linestyle=(0, (4, 2)), zorder=2)
    flaeche(ax, f.bestand, facecolor=FUELLUNG["bestand"], edgecolor=KONTUR["bestand"],
            linewidth=PT_MITTEL, zorder=3)
    flaeche(ax, f.neu, facecolor=FUELLUNG["neu"], edgecolor=KONTUR["neu"],
            linewidth=PT_MITTEL, zorder=4)


def oeffnung_zeichnen(ax, o: Oeffnung) -> None:
    w = o.wand
    d = w.dicke
    s0, s1 = o.abstand, o.abstand + o.breite
    farbe, strich = SYMBOL[o.wirksamer_status], STRICH[o.wirksamer_status]
    kw = dict(color=farbe, linestyle=strich, zorder=6)

    if o.typ == "fenster":
        for q in (-d / 2, d / 2):
            linie(ax, w.punkt(s0, q), w.punkt(s1, q), linewidth=PT_FEIN, **kw)
        for q in (-1.5, 1.5):
            linie(ax, w.punkt(s0, q), w.punkt(s1, q), linewidth=PT_MITTEL, **kw)
        for s in (s0, s1):
            linie(ax, w.punkt(s, -d / 2), w.punkt(s, d / 2), linewidth=PT_FEIN, **kw)
        return

    if o.typ == "durchgang":
        for q in (-d / 2, d / 2):
            linie(ax, w.punkt(s0, q), w.punkt(s1, q), linewidth=PT_FEIN, color=farbe,
                  linestyle=(0, (2, 2)), zorder=6)
        return

    band, bogen = tuerfluegel(o)
    linie(ax, band, bogen[0], linewidth=PT_DICK, **kw)
    ax.plot([p[0] for p in bogen], [p[1] for p in bogen], linewidth=PT_FEIN, color=farbe,
            linestyle=strich, zorder=6)


def tuerfluegel(o: Oeffnung) -> tuple[tuple[float, float], list[tuple[float, float]]]:
    """Tür: Flügel 90° offen, Bogen bis zur Gegenseite. Gibt (Band, Bogenpunkte ab Flügelende)."""
    w = o.wand
    d = w.dicke
    s0, s1 = o.abstand, o.abstand + o.breite
    seite = 1 if o.seite == "links" else -1
    sb, sg = (s0, s1) if o.anschlag == "anfang" else (s1, s0)
    band = w.punkt(sb, seite * d / 2)
    nx, ny = w.normale
    ende = (band[0] + nx * seite * o.breite, band[1] + ny * seite * o.breite)
    gegen = w.punkt(sg, seite * d / 2)
    a1 = math.atan2(ende[1] - band[1], ende[0] - band[0])
    a2 = math.atan2(gegen[1] - band[1], gegen[0] - band[0])
    delta = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
    return band, [(band[0] + o.breite * math.cos(a1 + delta * i / 32),
                   band[1] + o.breite * math.sin(a1 + delta * i / 32)) for i in range(33)]


# --- Einrichtung ----------------------------------------------------------

def objekt_zeichnen(ax, b: Objekt) -> None:
    farbe, strich = SYMBOL[b.status], STRICH[b.status]
    cx, cy = b.position
    rot = math.radians(b.rotation)
    cos, sin = math.cos(rot), math.sin(rot)
    B, T = b.breite, b.tiefe

    def p(x, y):  # lokal → Plan; lokal: x entlang breite, y entlang tiefe, Rückseite bei -T/2
        return (cx + x * cos - y * sin, cy + x * sin + y * cos)

    def poly(pts, **kw):
        q = [p(*pt) for pt in pts]
        ax.add_patch(plt.Polygon(q, closed=True, fill=False, edgecolor=farbe, linestyle=strich,
                                 linewidth=kw.pop("linewidth", PT_FEIN), zorder=5, **kw))

    def kreis(x, y, r):
        ax.add_patch(Circle(p(x, y), r, fill=False, edgecolor=farbe, linestyle=strich,
                            linewidth=PT_FEIN, zorder=5))

    def ellipse(x, y, bw, bh):
        ax.add_patch(Ellipse(p(x, y), bw, bh, angle=b.rotation, fill=False, edgecolor=farbe,
                             linestyle=strich, linewidth=PT_FEIN, zorder=5))

    def strich_(x0, y0, x1, y1):
        linie(ax, p(x0, y0), p(x1, y1), color=farbe, linestyle=strich, linewidth=PT_FEIN, zorder=5)

    hb, ht = B / 2, T / 2
    poly([(-hb, -ht), (hb, -ht), (hb, ht), (-hb, ht)], linewidth=PT_MITTEL)
    if b.typ == "kueche":
        poly([(-hb * 0.55 - 25, -ht + 8), (-hb * 0.55 + 25, -ht + 8),
              (-hb * 0.55 + 25, -ht + 48), (-hb * 0.55 - 25, -ht + 48)])
        for dx in (-13, 13):
            for dy in (-10, 12):
                kreis(hb * 0.5 + dx, dy, 8)
    elif b.typ == "wc":
        poly([(-hb, -ht), (hb, -ht), (hb, -ht + 15), (-hb, -ht + 15)])
        ellipse(0, (15 + 2) / 2 - 2, B * 0.8, T - 20)
    elif b.typ == "lavabo":
        ellipse(0, 3, B * 0.75, T * 0.6)
    elif b.typ == "dusche":
        strich_(-hb, -ht, hb, ht)
        strich_(-hb, ht, hb, -ht)
        kreis(0, 0, 3)
    elif b.typ == "badewanne":
        poly([(-hb + 6, -ht + 6), (hb - 6, -ht + 6), (hb - 6, ht - 6), (-hb + 6, ht - 6)])
        kreis(-hb + 20, 0, 3)
    elif b.typ == "schrank":
        strich_(-hb, ht, hb, -ht)
    elif b.typ == "waschturm":
        kreis(0, 0, min(B, T) * 0.33)
    elif b.typ == "bett":
        poly([(-hb + 5, -ht + 5), (hb - 5, -ht + 5), (hb - 5, -ht + 35), (-hb + 5, -ht + 35)])
    # Objekte mit eigenem Symbol brauchen keinen Text, ausser eine Bezeichnung ist angegeben
    beschriftung = b.bezeichnung or (b.typ.capitalize() if b.typ in ("tisch", "sofa", "andere") else "")
    if beschriftung:
        ax.text(cx, cy, beschriftung, ha="center", va="center", fontsize=5.5, color=farbe, zorder=7)


# --- Räume ----------------------------------------------------------------

def raeume_beschriften(ax, g: Geschoss, blatt: Fenster) -> list:
    """Raumname, Fläche, lichte Masse. Gibt die Textobjekte zurück (damit andere ihnen ausweichen)."""
    texte = []
    for r in geometrie.raeume(g, "neu"):
        x, y = r.beschriftungspunkt
        texte.append(ax.text(x, y + blatt.mm(2.2), r.name or "?", ha="center", va="bottom",
                             fontsize=8.5, fontweight="bold", color=TEXT, zorder=8))
        texte.append(ax.text(x, y, f"{r.m2:.2f} m²", ha="center", va="top", fontsize=7,
                             color=TEXT, zorder=8))
        if r.ist_rechteck:
            bx, by = r.lichte_masse
            texte.append(ax.text(x, y - blatt.mm(4), f"{mass_text(bx)} × {mass_text(by)}", ha="center",
                                 va="top", fontsize=6, color=GRAU, zorder=8))
    return texte


# --- Öffnungen beschriften ------------------------------------------------

def oeffnung_text(o: Oeffnung, zweizeilig: bool = False) -> str:
    """Fenster «F1  70 × 90, BRH 1.10», Türen und Durchgänge «T1  90 × 2.10»."""
    text = f"{o.id}  {mass_text(o.breite)} × {mass_text(o.hoehe)}"
    if o.typ == "fenster":
        text += ("\n" if zweizeilig else ", ") + f"BRH {mass_text(o.bruestung)}"
    return text


def _textbox(ax, artist) -> Polygon:
    """Was ein Text auf der Zeichnung belegt, in cm."""
    bb = artist.get_window_extent(ax.figure.canvas.get_renderer())
    return box(*bb.transformed(ax.transData.inverted()).extents)


def _textgroesse(ax, text: str, fenster: Fenster) -> tuple[float, float]:
    """Breite und Höhe eines ungedrehten Texts in cm."""
    t = ax.text(0, 0, text, fontsize=BESCHRIFTUNG_PT, multialignment="center")
    bb = t.get_window_extent(ax.figure.canvas.get_renderer())
    t.remove()
    mm_pro_px = 25.4 / ax.figure.dpi
    return fenster.mm(bb.width * mm_pro_px), fenster.mm(bb.height * mm_pro_px)


def oeffnungen_beschriften(fenster: Fenster, g: Geschoss, schnitte: list[Schnitt],
                           texte: list) -> list[Oeffnung]:
    """Jede Öffnung bekommt ihre Masse in der Statusfarbe, parallel zur Wand auf der Raumseite.

    Gesucht wird ein Platz, der keine Wand, kein Objekt, keinen Türflügel und keinen anderen
    Text überdeckt und innerhalb der Aussenwände liegt (aussen sind die Massketten): zuerst
    direkt neben der Öffnung, dann entlang der Wand verschoben. Passt der Text nirgends,
    wird er zweizeilig versucht, zuletzt steht nur die Bezeichnung (F1) an der Öffnung.
    Diese Öffnungen werden zurückgegeben; ihre Masse kommen in die Liste neben der Legende.
    """
    ax = fenster.ax
    innen = geometrie.aussenumriss(g)
    hart = [geometrie.wand_polygon(w) for w in g.waende]
    hart += [geometrie.objekt_polygon(b) for b in g.objekte]
    for o in g.oeffnungen:
        if o.typ == "tuer":
            band, bogen = tuerfluegel(o)
            hart.append(Polygon([band, *bogen]).buffer(0))
    hart += [_textbox(ax, t) for t in texte]
    weich = []  # Schnittlinien: lieber nicht, aber erlaubt
    for s in schnitte:
        a, b = ((-1e5, s.lage), (1e5, s.lage)) if s.achse == "x" else ((s.lage, -1e5), (s.lage, 1e5))
        weich.append(LineString([a, b]).buffer(fenster.mm(0.4)))
    rand, abstand = fenster.mm(0.4), fenster.mm(1.0)
    verschiebungen = [0.0] + [v * k * fenster.mm(2.5) for k in range(1, 9) for v in (1, -1)]

    def kandidaten(o: Oeffnung, b: float, h: float):
        w = o.wand
        mitte = o.abstand + o.breite / 2
        seiten = (1, -1)
        if o.typ == "tuer":  # zuerst auf der Seite ohne Türflügel
            seiten = (-1, 1) if o.seite == "links" else (1, -1)
        for seite in seiten:
            for weiter in (0.0, fenster.mm(3)):
                q = seite * (w.dicke / 2 + abstand + weiter + h / 2)
                for v in verschiebungen:
                    s = mitte + v
                    rahmen = Polygon([w.punkt(s - b / 2 - rand, q - h / 2 - rand),
                                      w.punkt(s + b / 2 + rand, q - h / 2 - rand),
                                      w.punkt(s + b / 2 + rand, q + h / 2 + rand),
                                      w.punkt(s - b / 2 - rand, q + h / 2 + rand)])
                    yield w.punkt(s, q), rahmen

    def platz(o: Oeffnung, text: str, mit_weich: bool):
        b, h = _textgroesse(ax, text, fenster)
        hindernisse = hart + (weich if not mit_weich else [])
        for punkt, rahmen in kandidaten(o, b, h):
            if rahmen.within(innen) and not any(rahmen.intersects(x) for x in hindernisse):
                return punkt, rahmen
        return None

    nur_kennung = []
    for o in g.oeffnungen:
        varianten = [oeffnung_text(o)]
        if o.typ == "fenster":
            varianten.append(oeffnung_text(o, zweizeilig=True))
        varianten.append(o.id)
        gefunden = None
        for text in varianten:
            for mit_weich in (False, True):
                ort = platz(o, text, mit_weich)
                if ort:
                    gefunden = (text, *ort)
                    break
            if gefunden:
                break
        if gefunden is None:  # nicht einmal die Bezeichnung passt frei: direkt neben die Öffnung
            b, h = _textgroesse(ax, o.id, fenster)
            gefunden = (o.id, *next(kandidaten(o, b, h)))
        text, punkt, rahmen = gefunden
        if text == o.id:
            nur_kennung.append(o)
        ux, uy = o.wand.richtung
        winkel = math.degrees(math.atan2(uy, ux))
        winkel = winkel - 180 if winkel > 90.01 else winkel + 180 if winkel <= -90 else winkel
        ax.text(*punkt, text, ha="center", va="center", rotation=winkel, rotation_mode="anchor",
                multialignment="center", fontsize=BESCHRIFTUNG_PT, color=SYMBOL[o.wirksamer_status],
                zorder=8)
        hart.append(rahmen)
    return nur_kennung


def oeffnungsliste(blatt: Blatt, oeffnungen: list[Oeffnung]) -> None:
    """Masse der Öffnungen, die im Grundriss nur ihre Bezeichnung tragen (zu wenig Platz)."""
    if not oeffnungen:
        return
    ax = blatt.papier
    x, y = 130.0, 57.0
    ax.text(x, y, "Öffnungen (Breite × Höhe)", ha="left", va="bottom", fontsize=7,
            fontweight="bold", color=TEXT)
    zeilen_pro_spalte = 14
    for i, o in enumerate(oeffnungen):
        sp, ze = divmod(i, zeilen_pro_spalte)
        ax.text(x + sp * 48, y - 2 - ze * 3, oeffnung_text(o), ha="left", va="top", fontsize=6,
                color=SYMBOL[o.wirksamer_status])


# --- Bemassung ------------------------------------------------------------

def bemassen(ax, g: Geschoss, blatt: Fenster) -> None:
    """Aussenmassketten auf allen vier Seiten: Öffnungen, Wände, Total (Total unten und links)."""
    gilt = [w for w in g.waende if w.status in ("bestand", "neu")]
    if not gilt:
        return
    polys = {w.id: geometrie.wand_polygon(w) for w in gilt}
    bx0 = min(p.bounds[0] for p in polys.values())
    by0 = min(p.bounds[1] for p in polys.values())
    bx1 = max(p.bounds[2] for p in polys.values())
    by1 = max(p.bounds[3] for p in polys.values())

    seiten = {
        # name: (achse der Kette, Index der Fassadenkoordinate in bounds, Fassade, Richtung aussen)
        "unten": ("x", 1, by0, -1),
        "oben": ("x", 3, by1, +1),
        "links": ("y", 0, bx0, -1),
        "rechts": ("y", 2, bx1, +1),
    }
    for name, (achse, idx, fassade, aussen) in seiten.items():
        i_entlang = 0 if achse == "x" else 1
        anfang, ende = (bx0, bx1) if achse == "x" else (by0, by1)
        aussenwaende = [w for w in gilt
                        if abs(w.richtung[1 - i_entlang]) < 1e-3
                        and abs(polys[w.id].bounds[idx] - fassade) < 1.0]
        aussen_polys = [polys[w.id] for w in aussenwaende]

        oeffnungen = [anfang, ende]
        for o in g.oeffnungen:
            if o.wand in aussenwaende and o.status != "abbruch":
                oeffnungen += [o.wand.punkt(o.abstand)[i_entlang],
                               o.wand.punkt(o.abstand + o.breite)[i_entlang]]
        waende = [anfang, ende]
        for w in gilt:
            senkrecht = abs(w.richtung[i_entlang]) < 1e-3
            if senkrecht and any(polys[w.id].intersects(p) for p in aussen_polys):
                mitte = w.von[i_entlang]
                waende += [mitte - w.dicke / 2, mitte + w.dicke / 2]

        ketten = []
        if len(set(round(p) for p in oeffnungen)) > 2:
            ketten.append(oeffnungen)
        if len(set(round(p) for p in waende)) > 2:
            ketten.append(waende)
        if name in ("unten", "links"):
            ketten.append([anfang, ende])
        for k, punkte in enumerate(ketten):
            lage = fassade + aussen * blatt.mm(10 + 7 * k)
            masskette(blatt, punkte, achse, lage, aussen, fassade)


# --- Schnittlinien --------------------------------------------------------

def schnittlinien(fenster: Fenster, g: Geschoss, schnitte: list[Schnitt]) -> None:
    """Strichpunktlinie durch den Grundriss, an den Enden kräftig, mit Blickpfeil und Buchstabe."""
    ax = fenster.ax
    x0, y0, x1, y1 = grenzen(g)
    ueber = fenster.mm(6)
    for s in schnitte:
        if s.achse == "x":
            a, b = (x0 - ueber, s.lage), (x1 + ueber, s.lage)
            blick = (0, 1) if s.blick == "plus" else (0, -1)
        else:
            a, b = (s.lage, y0 - ueber), (s.lage, y1 + ueber)
            blick = (1, 0) if s.blick == "plus" else (-1, 0)
        linie(ax, a, b, color=TEXT, linewidth=PT_FEIN, linestyle=(0, (8, 2, 1, 2)), zorder=7)
        richtung = ((b[0] - a[0]), (b[1] - a[1]))
        laenge = math.hypot(*richtung)
        u = (richtung[0] / laenge, richtung[1] / laenge)
        for ende, vor in ((a, 1), (b, -1)):
            innen = (ende[0] + u[0] * vor * fenster.mm(5), ende[1] + u[1] * vor * fenster.mm(5))
            linie(ax, ende, innen, color=TEXT, linewidth=2.0, zorder=7)
            spitze = (ende[0] + blick[0] * fenster.mm(4), ende[1] + blick[1] * fenster.mm(4))
            ax.annotate("", xy=spitze, xytext=ende, zorder=7,
                        arrowprops=dict(arrowstyle="-|>", color=TEXT, linewidth=PT_MITTEL,
                                        mutation_scale=7, shrinkA=0, shrinkB=0))
            text = (ende[0] - u[0] * vor * fenster.mm(2.5), ende[1] - u[1] * vor * fenster.mm(2.5))
            ax.text(*text, s.name, ha="center", va="center", fontsize=9, fontweight="bold",
                    color=TEXT, zorder=7)


# --- Blatt ----------------------------------------------------------------

def grundriss_blatt(plan: Plan, g: Geschoss, schnitte: list[Schnitt], entwurf: bool = False):
    """Ein A3-Blatt mit dem Umbau-Grundriss. Gibt (Blatt, Fenster) zurück."""
    massstab = massstab_waehlen(g, plan.projekt.massstab)
    blatt = Blatt()
    fenster = fenster_grundriss(blatt, g, massstab)
    ax = fenster.ax
    waende_zeichnen(ax, g)
    for o in g.oeffnungen:
        oeffnung_zeichnen(ax, o)
    for b in g.objekte:
        objekt_zeichnen(ax, b)
    texte = raeume_beschriften(ax, g, fenster)
    nur_kennung = oeffnungen_beschriften(fenster, g, schnitte, texte)
    bemassen(ax, g, fenster)
    schnittlinien(fenster, g, schnitte)
    plankopf(blatt, plan, f"Grundriss {g.name} – Umbau", f"{plan.projekt.plannummer}-{g.id}",
             f"1:{massstab}", entwurf)
    legende(blatt, plan)
    oeffnungsliste(blatt, nur_kennung)
    if plan.projekt.nordwinkel is not None:
        nordpfeil(blatt, plan.projekt.nordwinkel)
    return blatt, fenster

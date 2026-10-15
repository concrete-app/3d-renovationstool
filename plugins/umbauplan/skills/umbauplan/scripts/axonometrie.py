"""3D-Ansicht vorher/nachher: das Geschoss als Puppenhaus ohne Decke, von schräg oben.

Parallelprojektion (Axonometrie). Die Szene besteht aus konvexen, senkrechten
Körpern (Wandstücke, Einrichtung, Glas), die sich nicht durchdringen; dafür
sorgt geometrie.wandkoerper(). Für zwei solche Körper gibt es immer eine
Trennebene, und sie sagt eindeutig, welcher vorne liegt. Danach werden die
Körper sortiert (topologisch) und von hinten nach vorne gezeichnet. Das ist
exakt, anders als das Sortieren einzelner Flächen nach ihrem Mittelpunkt.

Farben: vorher zeigt gelb, was wegkommt (Abbruchwände und die Wandstücke, wo
neue Öffnungen hinkommen); nachher zeigt rot, was neu ist (neue Wände und
zugemauerte Öffnungen).
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field

import numpy as np
from matplotlib.colors import to_rgb
from shapely.geometry import MultiPolygon, Point, Polygon, box
from shapely.geometry.polygon import orient

import geometrie
from ansichten import _himmelsrichtung
from blatt import TEXT, ZEICHENFLAECHE, Blatt, legende, plankopf
from modell import Geschoss, Plan, Wand

ELEVATION = 32.0       # Grad über dem Horizont
FARBE = {"bestand": "#D4D4D4", "abbruch": "#FFD400", "neu": "#E0383C"}
OBJEKT = {"bestand": "#F4F4F4", "abbruch": "#FFF1A6", "neu": "#F6B9BA"}
BODEN = "#EDEDED"
GLAS = "#9CC9E8"
EPS = 0.01


@dataclass
class Flaeche3D:
    punkte: np.ndarray            # (n, 3) in cm
    normale: np.ndarray           # nach aussen
    farbe: str
    kanten: list[bool]            # je Kante (i → i+1): zeichnen?
    alpha: float = 1.0
    zweiseitig: bool = False


@dataclass
class Koerper:
    grund: Polygon                # konvex
    z0: float
    z1: float
    flaechen: list[Flaeche3D] = field(default_factory=list)


def _prisma(grund: Polygon, z0: float, z1: float, farbe: str) -> list[Flaeche3D]:
    """Mantel und Deckel eines senkrechten Prismas (der Boden ist von oben nie zu sehen)."""
    grund = orient(grund, 1.0)  # gegen den Uhrzeigersinn: Aussennormale = (dy, -dx)
    pts = list(grund.exterior.coords)[:-1]
    flaechen = []
    for (ax, ay), (bx, by) in zip(pts, pts[1:] + pts[:1]):
        n = np.array([by - ay, -(bx - ax), 0.0])
        laenge = np.linalg.norm(n)
        if laenge < 1e-6:
            continue
        flaechen.append(Flaeche3D(np.array([(ax, ay, z0), (bx, by, z0), (bx, by, z1), (ax, ay, z1)]),
                                  n / laenge, farbe, [True] * 4))
    flaechen.append(Flaeche3D(np.array([(x, y, z1) for x, y in pts]), np.array([0, 0, 1.0]), farbe,
                              [True] * len(pts)))
    return flaechen


# --- Wände in Stücke zerlegen ---------------------------------------------

def _wand(w: Wand, g: Geschoss, vorher: bool) -> list[Koerper]:
    """Die Wand als Quader-Stücke um ihre Öffnungen. Kanten werden nur gezeichnet, wo
    die Wand wirklich eine Kante hat, nicht an den Fugen zwischen den Stücken."""
    s0, s1, _ = geometrie.wandkoerper(w, g)
    z0, hoch = g.kote, g.kote + w.hoehe
    offen, gefuellt = [], []                    # (sa, sb, za, zb[, farbe])
    for o in (o for o in g.oeffnungen if o.wand is w):
        r = (o.abstand, o.abstand + o.breite, z0 + o.bruestung, z0 + o.bruestung + o.hoehe)
        if vorher:
            if o.status == "neu":                 # Durchbruch: dieses Stück kommt weg
                gefuellt.append((*r, FARBE["abbruch"]))
            else:
                offen.append((r, o))
        else:
            if o.wird_zugemauert:                 # Zumauerung: dieses Stück ist neu
                gefuellt.append((*r, FARBE["neu"]))
            elif o.status != "abbruch":
                offen.append((r, o))

    loecher = [r for r, _ in offen] + [f[:4] for f in gefuellt]
    massiv = box(s0, z0, s1, hoch)              # Wandansicht in (s, z)
    for sa, sb, za, zb in loecher:
        massiv = massiv.difference(box(sa, za, sb, zb))
    rand = massiv.boundary

    stuecke = []                                # (sa, sb, za, zb, farbe, ist_massiv)
    grenzen = sorted({s0, s1, *[v for r in loecher for v in r[:2]]})
    for sa, sb in zip(grenzen, grenzen[1:]):
        if sb - sa < 0.1:
            continue
        mitte = (sa + sb) / 2
        belegt = sorted((r[2], r[3]) for r in loecher if r[0] <= mitte <= r[1])
        za = z0
        for la, lb in belegt + [(hoch, hoch)]:
            if la - za > 0.1:
                stuecke.append((sa, sb, za, la, FARBE[w.status], True))
            za = max(za, lb)
    stuecke += [(*f[:4], f[4], False) for f in gefuellt]

    q = w.dicke / 2
    koerper = []
    for sa, sb, za, zb, farbe, ist_massiv in stuecke:
        def echt(a, b):  # liegt die Kante (in s, z) auf dem Rand der Wandansicht?
            if not ist_massiv:
                return True
            return rand.distance(Point((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)) < EPS

        grund = Polygon([w.punkt(sa, -q), w.punkt(sb, -q), w.punkt(sb, q), w.punkt(sa, q)])
        k = Koerper(grund, za, zb)
        nx, ny = w.normale
        ux, uy = w.richtung
        for seite in (1, -1):                   # Längsseiten
            pts = [(sa, za), (sb, za), (sb, zb), (sa, zb)]
            p3 = np.array([(*w.punkt(s, seite * q), z) for s, z in pts])
            k.flaechen.append(Flaeche3D(p3, np.array([seite * nx, seite * ny, 0.0]), farbe,
                                        [echt(pts[i], pts[(i + 1) % 4]) for i in range(4)]))
        for s, vor in ((sa, -1), (sb, 1)):      # Stirnseiten (Laibungen, Wandenden)
            p3 = np.array([(*w.punkt(s, -q), za), (*w.punkt(s, q), za), (*w.punkt(s, q), zb),
                           (*w.punkt(s, -q), zb)])
            k.flaechen.append(Flaeche3D(p3, np.array([vor * ux, vor * uy, 0.0]), farbe, [True] * 4))
        oben = [(sa, -q), (sb, -q), (sb, q), (sa, q)]
        p3 = np.array([(*w.punkt(s, qq), zb) for s, qq in oben])
        offen_links = not ist_massiv or not massiv.buffer(-EPS).contains(Point(sa - 0.5, zb - 0.5))
        offen_rechts = not ist_massiv or not massiv.buffer(-EPS).contains(Point(sb + 0.5, zb - 0.5))
        k.flaechen.append(Flaeche3D(p3, np.array([0, 0, 1.0]), farbe,
                                    [True, offen_rechts, True, offen_links]))
        koerper.append(k)

    for (sa, sb, za, zb), o in offen:
        if o.typ == "fenster":
            glas = np.array([(*w.punkt(sa), za), (*w.punkt(sb), za), (*w.punkt(sb), zb), (*w.punkt(sa), zb)])
            grund = Polygon([w.punkt(sa, -0.5), w.punkt(sb, -0.5), w.punkt(sb, 0.5), w.punkt(sa, 0.5)])
            koerper.append(Koerper(grund, za, zb, [Flaeche3D(glas, np.array([*w.normale, 0.0]), GLAS,
                                                             [True] * 4, 0.45, zweiseitig=True)]))
    return koerper


def szene(g: Geschoss, zustand: str) -> tuple[list[Koerper], list[Koerper], list]:
    """(Boden, Körper, Raumnamen) eines Geschosses vorher ("bestand") oder nachher ("neu")."""
    vorher = zustand == "bestand"
    gilt = ("bestand", "abbruch") if vorher else ("bestand", "neu")
    boden = []
    umriss = geometrie.aussenumriss(g)
    for p in (umriss.geoms if isinstance(umriss, MultiPolygon) else [umriss]):
        grund = Polygon(p.exterior)
        boden.append(Koerper(grund, g.kote - g.deckenstaerke, g.kote,
                             _prisma(grund, g.kote - g.deckenstaerke, g.kote, BODEN)))
    koerper = []
    for w in g.waende:
        if w.status in gilt:
            koerper += _wand(w, g, vorher)
    for b in g.objekte:
        if b.status in gilt:
            grund = geometrie.objekt_polygon(b)
            koerper.append(Koerper(grund, g.kote, g.kote + b.hoehe,
                                   _prisma(grund, g.kote, g.kote + b.hoehe, OBJEKT[b.status])))
    namen = [(r.name, np.array([*r.beschriftungspunkt, g.kote + 2])) for r in geometrie.raeume(g, zustand)]
    return boden, koerper, namen


# --- Kamera und Reihenfolge -----------------------------------------------

class Kamera:
    """Parallelprojektion. azimut: Richtung vom Gebäude zur Kamera im Grundriss (Grad, 0 = +x)."""

    def __init__(self, azimut: float, elevation: float = ELEVATION):
        a, e = math.radians(azimut), math.radians(elevation)
        zur_kamera = np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)])
        self.vor = -zur_kamera                                     # Blickrichtung
        rechts = np.cross(self.vor, [0, 0, 1.0])
        self.rechts = rechts / np.linalg.norm(rechts)
        self.oben = np.cross(self.rechts, self.vor)
        self.richtung_grundriss = (math.cos(a), math.sin(a))
        # Licht von links oben, aus Sicht der Kamera: die sichtbaren Seiten sind verschieden hell
        la, le = a + math.radians(40), math.radians(55)
        self.licht = np.array([math.cos(le) * math.cos(la), math.cos(le) * math.sin(la), math.sin(le)])

    def projektion(self, p: np.ndarray) -> np.ndarray:
        return np.stack([p @ self.rechts, p @ self.oben], axis=-1)


def _trennnormale(a: Koerper, b: Koerper) -> np.ndarray | None:
    """Normale einer Ebene, die a und b trennt, zeigt von a nach b. None, wenn keine gefunden."""
    if a.z1 <= b.z0 + EPS:
        return np.array([0, 0, 1.0])
    if b.z1 <= a.z0 + EPS:
        return np.array([0, 0, -1.0])
    pa = np.array(a.grund.exterior.coords[:-1])
    pb = np.array(b.grund.exterior.coords[:-1])
    for pts in (pa, pb):
        for i in range(len(pts)):
            d = pts[(i + 1) % len(pts)] - pts[i]
            m = np.array([-d[1], d[0]])
            laenge = np.linalg.norm(m)
            if laenge < 1e-9:
                continue
            m /= laenge
            ia, ib = pa @ m, pb @ m
            if ia.max() <= ib.min() + EPS:
                return np.array([m[0], m[1], 0.0])
            if ib.max() <= ia.min() + EPS:
                return np.array([-m[0], -m[1], 0.0])
    return None


def sortieren(koerper: list[Koerper], kamera: Kamera) -> list[Koerper]:
    """Von hinten nach vorne: a vor b zeichnen, wenn eine Trennebene a hinter b stellt."""
    n = len(koerper)
    proj = [kamera.projektion(np.array([(x, y, z) for x, y in k.grund.exterior.coords for z in (k.z0, k.z1)]))
            for k in koerper]
    rahmen = [(p[:, 0].min(), p[:, 1].min(), p[:, 0].max(), p[:, 1].max()) for p in proj]
    tiefe = [float(np.mean(np.array([(x, y, (k.z0 + k.z1) / 2) for x, y in k.grund.exterior.coords]) @ kamera.vor))
             for k in koerper]
    danach = [[] for _ in range(n)]
    eingang = [0] * n
    for i in range(n):
        for j in range(i + 1, n):
            ri, rj = rahmen[i], rahmen[j]
            if ri[2] <= rj[0] or rj[2] <= ri[0] or ri[3] <= rj[1] or rj[3] <= ri[1]:
                continue  # überdecken sich auf dem Bild nicht
            normale = _trennnormale(koerper[i], koerper[j])
            if normale is None:
                continue
            richtung = float(normale @ kamera.vor)
            if richtung < -1e-9:      # von i nach j wird es näher: i liegt hinten
                danach[i].append(j)
                eingang[j] += 1
            elif richtung > 1e-9:
                danach[j].append(i)
                eingang[i] += 1
    # Kahn, bei Gleichstand das Fernste zuerst; Zyklen (kommen praktisch nicht vor) brechen am Fernsten
    bereit = [(-tiefe[i], i) for i in range(n) if eingang[i] == 0]
    heapq.heapify(bereit)
    fertig, reihenfolge = [False] * n, []
    while len(reihenfolge) < n:
        if not bereit:
            rest = max((i for i in range(n) if not fertig[i]), key=lambda i: tiefe[i])
            eingang[rest] = 0
            heapq.heappush(bereit, (-tiefe[rest], rest))
        _, i = heapq.heappop(bereit)
        if fertig[i]:
            continue
        fertig[i] = True
        reihenfolge.append(koerper[i])
        for j in danach[i]:
            eingang[j] -= 1
            if eingang[j] == 0 and not fertig[j]:
                heapq.heappush(bereit, (-tiefe[j], j))
    return reihenfolge


# --- Zeichnen -------------------------------------------------------------

def _schattiert(farbe: str, normale: np.ndarray, licht: np.ndarray) -> tuple[float, float, float]:
    hell = 0.6 + 0.4 * max(0.0, float(normale @ licht))
    return tuple(min(1.0, c * hell) for c in to_rgb(farbe))


def zeichnen(ax, boden: list[Koerper], koerper: list[Koerper], namen, kamera: Kamera) -> None:
    z = 2.0
    for k in boden + sortieren(koerper, kamera):
        for f in k.flaechen:
            if not f.zweiseitig and float(f.normale @ kamera.vor) >= -1e-6:
                continue  # Rückseite
            farbe = to_rgb(f.farbe) if f.zweiseitig else _schattiert(f.farbe, f.normale, kamera.licht)
            kante = tuple(c * 0.55 for c in farbe)
            xy = kamera.projektion(f.punkte)
            z += 1e-5
            # mit eigener Farbe umranden, damit zwischen Stücken keine Haarlinie bleibt
            ax.fill(*xy.T, facecolor=farbe, edgecolor=farbe if f.alpha == 1 else "none",
                    linewidth=0.3, alpha=f.alpha, zorder=z)
            for i, echt in enumerate(f.kanten):
                if echt:
                    a, b = xy[i], xy[(i + 1) % len(xy)]
                    ax.plot([a[0], b[0]], [a[1], b[1]], color=kante, linewidth=0.3, zorder=z,
                            solid_capstyle="round")
    for name, p in namen:
        if name:
            x, y = kamera.projektion(p)
            ax.text(x, y, name, ha="center", va="center", fontsize=6.5, fontweight="bold", color=TEXT,
                    zorder=10, bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="none",
                                         alpha=0.8))


def blatt_3d(plan: Plan, g: Geschoss, azimut: float, entwurf: bool = False) -> Blatt:
    """Ein A3-Blatt: links vorher, rechts nachher, gleicher Blickwinkel und gleiche Grösse."""
    kamera = Kamera(azimut)
    szenen = {z: szene(g, z) for z in ("bestand", "neu")}
    alle = np.vstack([kamera.projektion(f.punkte) for boden, koerper, _ in szenen.values()
                      for k in boden + koerper for f in k.flaechen])
    (x0, y0), (x1, y1) = alle.min(axis=0), alle.max(axis=0)
    rand = 0.04 * max(x1 - x0, y1 - y0)
    xlim, ylim = (x0 - rand, x1 + rand), (y0 - rand, y1 + rand)

    blatt = Blatt()
    fx0, fy0, fx1, fy1 = ZEICHENFLAECHE
    mitte = (fx0 + fx1) / 2
    for (zustand, titel), (lx0, lx1) in zip((("bestand", "Vorher (Bestand)"), ("neu", "Nachher (Umbau)")),
                                            ((fx0, mitte - 3), (mitte + 3, fx1))):
        ax = blatt.frei((lx0, fy0 + 10, lx1, fy1 - 4), xlim, ylim)
        zeichnen(ax, *szenen[zustand], kamera)
        blatt.papier.text(lx0 + 2, fy0 + 4, titel, ha="left", va="bottom", fontsize=10,
                          fontweight="bold", color=TEXT)

    richtung = _himmelsrichtung(plan, kamera.richtung_grundriss)
    blick = f"von {richtung}" if richtung else f"Azimut {azimut:.0f}°"
    plankopf(blatt, plan, f"3D {g.name} – Blick {blick}", f"{plan.projekt.plannummer}-{g.id}-3D{int(azimut)}",
             "ohne", entwurf)
    legende(blatt, plan, "3D-Darstellung ohne Massstab, Decke weggelassen. Masse gelten nur ab Grundriss und Schnitt.")
    return blatt

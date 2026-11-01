"""Das A3-Blatt, auf dem jede Zeichnung liegt: Rahmen, Plankopf, Legende, Massketten.

Ein Blatt hat eine Papierachse in mm (`papier`) und darauf beliebig viele
massstäbliche Fenster (`Fenster`). Ein Fenster ist eine Achse in Zentimetern,
deren Grösse auf dem Papier exakt dem Massstab entspricht: bei 1:50 sind
100 cm genau 20 mm. Was auf dem Papier gleich gross bleiben soll (Abstände
von Massketten, Strichlängen), rechnet `Fenster.mm()` um. Linienstärken und
Schrift sind in Punkt und darum unabhängig vom Massstab.
"""

from __future__ import annotations

import logging
import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                 # noqa: E402
from matplotlib import font_manager                             # noqa: E402
from matplotlib.patches import Circle, PathPatch, Rectangle     # noqa: E402
from matplotlib.path import Path as MplPath                     # noqa: E402
from shapely.geometry import MultiPolygon, Polygon              # noqa: E402

from modell import SKILL, Plan, mass_text                       # noqa: E402

A3 = (420.0, 297.0)                    # mm, quer
RAHMEN = (20.0, 10.0, 410.0, 287.0)    # links 20 mm Heftrand
PLANKOPF = (230.0, 10.0, 410.0, 62.0)
ZEICHENFLAECHE = (25.0, 64.0, 405.0, 284.0)

FUELLUNG = {"bestand": "#3C3C3C", "abbruch": "#FFD400", "neu": "#D7191C"}
KONTUR = {"bestand": "#000000", "abbruch": "#000000", "neu": "#7A0C0F"}
SYMBOL = {"bestand": "#000000", "abbruch": "#B38F00", "neu": "#D7191C"}
STRICH = {"bestand": "solid", "abbruch": (0, (3, 2)), "neu": "solid"}
TEXT = "#121111"
GRAU = "#6B6B6B"
LINIE = "#A0A0A0"

PT_FEIN, PT_MITTEL, PT_DICK = 0.35, 0.6, 1.0

MONATE = ("Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
          "September", "Oktober", "November", "Dezember")

logging.getLogger("fontTools").setLevel(logging.ERROR)  # meldet harmlose Eigenheiten der Schriften
for _ttf in sorted((SKILL / "assets" / "schrift").glob("*.ttf")):  # Hausschrift mitgeliefert
    font_manager.fontManager.addfont(str(_ttf))
plt.rcParams.update({
    "font.family": ["Arial", "Helvetica", "DejaVu Sans"],
    "pdf.fonttype": 42,
    "svg.fonttype": "none",
})


def schrift_setzen(plan: Plan) -> None:
    schrift = plan.firma.get("marke", {}).get("schrift")
    if schrift:
        plt.rcParams["font.family"] = [schrift, "Arial", "Helvetica", "DejaVu Sans"]


def datum_text(d) -> str:
    return f"{d.day}. {MONATE[d.month - 1]} {d.year}"


def kote_text(cm: float) -> str:
    """Höhenkote nach Schweizer Art: ± 0.00, + 2.50, − 0.20 (in m)."""
    if abs(cm) < 0.25:
        return "± 0.00"
    return f"{'+' if cm > 0 else '−'} {abs(cm) / 100:.2f}"


# --- Blatt und Fenster ----------------------------------------------------

class Fenster:
    """Eine massstäbliche Zeichnung auf dem Blatt. `ax` rechnet in cm."""

    def __init__(self, blatt: "Blatt", links_mm: float, unten_mm: float,
                 xlim: tuple[float, float], ylim: tuple[float, float], massstab: int):
        self.massstab = massstab
        self.breite_mm = (xlim[1] - xlim[0]) * 10 / massstab
        self.hoehe_mm = (ylim[1] - ylim[0]) * 10 / massstab
        self.links_mm, self.unten_mm = links_mm, unten_mm
        self.ax = blatt.fig.add_axes((links_mm / A3[0], unten_mm / A3[1],
                                      self.breite_mm / A3[0], self.hoehe_mm / A3[1]))
        self.ax.set_xlim(*xlim)
        self.ax.set_ylim(*ylim)
        self.ax.axis("off")
        self.ax.set_zorder(1)

    def mm(self, papier_mm: float) -> float:
        """Papier-Millimeter in Zentimeter der Zeichnung."""
        return papier_mm * self.massstab / 10


class Blatt:
    """Ein A3-Blatt quer mit Rahmen und der Papierachse `papier` (mm)."""

    def __init__(self):
        self.fig = plt.figure(figsize=(A3[0] / 25.4, A3[1] / 25.4))
        self.papier = self.fig.add_axes((0, 0, 1, 1))
        self.papier.set_xlim(0, A3[0])
        self.papier.set_ylim(0, A3[1])
        self.papier.axis("off")
        self.papier.add_patch(Rectangle(RAHMEN[:2], RAHMEN[2] - RAHMEN[0], RAHMEN[3] - RAHMEN[1],
                                        fill=False, edgecolor=TEXT, linewidth=PT_MITTEL))

    def fenster(self, links_mm, unten_mm, xlim, ylim, massstab) -> Fenster:
        return Fenster(self, links_mm, unten_mm, xlim, ylim, massstab)

    def frei(self, region_mm: tuple[float, float, float, float], xlim, ylim):
        """Eine Achse ohne Massstab (3D), so gross wie möglich in region_mm, Seitenverhältnis 1:1."""
        x0, y0, x1, y1 = region_mm
        bx, by = xlim[1] - xlim[0], ylim[1] - ylim[0]
        f = min((x1 - x0) / bx, (y1 - y0) / by)
        w, h = bx * f, by * f
        lx, ly = x0 + (x1 - x0 - w) / 2, y0 + (y1 - y0 - h) / 2
        ax = self.fig.add_axes((lx / A3[0], ly / A3[1], w / A3[0], h / A3[1]))
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        ax.axis("off")
        ax.set_zorder(1)
        return ax


def passt(groessen_cm: list[tuple[float, float]], raender_mm: tuple[float, float],
          anordnung: tuple[int, int], wunsch: int, massstaebe=(20, 50, 100, 200)) -> int | None:
    """Kleinster Massstab ≥ wunsch, bei dem alle Zeichnungen (Breite, Höhe in cm) im Raster
    anordnung (Spalten, Zeilen) samt Rand (waagrecht, senkrecht, mm) in die Zeichenfläche passen."""
    fw = ZEICHENFLAECHE[2] - ZEICHENFLAECHE[0]
    fh = ZEICHENFLAECHE[3] - ZEICHENFLAECHE[1]
    spalten, zeilen = anordnung
    for m in [s for s in massstaebe if s >= wunsch]:
        breite = max(b for b, _ in groessen_cm) * 10 / m + raender_mm[0]
        hoehe = max(h for _, h in groessen_cm) * 10 / m + raender_mm[1]
        if breite * spalten <= fw and hoehe * zeilen <= fh:
            return m
    return None


# --- Grundformen ----------------------------------------------------------

def _pfad(geom) -> MplPath | None:
    polys = list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom]
    verts, codes = [], []
    for p in polys:
        if not isinstance(p, Polygon) or p.is_empty:
            continue
        for ring in [p.exterior, *p.interiors]:
            pts = list(ring.coords)
            verts += pts
            codes += [MplPath.MOVETO] + [MplPath.LINETO] * (len(pts) - 2) + [MplPath.CLOSEPOLY]
    return MplPath(verts, codes) if verts else None


def flaeche(ax, geom, **kw) -> None:
    if geom.is_empty:
        return
    if not isinstance(geom, (Polygon, MultiPolygon)):
        geom = MultiPolygon([g for g in getattr(geom, "geoms", []) if isinstance(g, Polygon)])
    pfad = _pfad(geom)
    if pfad is not None:
        ax.add_patch(PathPatch(pfad, **kw))


def linie(ax, a, b, **kw) -> None:
    ax.plot([a[0], b[0]], [a[1], b[1]], solid_capstyle="butt", **kw)


# --- Massketten und Koten -------------------------------------------------

def masskette(fenster: Fenster, punkte: list[float], achse: str, lage: float, aussen: float,
              bauteil: float) -> None:
    """Eine Masskette. achse 'x': waagrecht bei y=lage; 'y': senkrecht bei x=lage.
    aussen: +1/-1, Richtung weg vom Bauteil. bauteil: Koordinate der Bauteilkante (für Hilfslinien)."""
    ax = fenster.ax
    pkt = sorted({round(p, 1) for p in punkte})
    pkt = [p for i, p in enumerate(pkt) if i == 0 or p - pkt[i - 1] >= 0.5]
    if len(pkt) < 2:
        return
    t = fenster.mm(1.3)  # halbe Länge des Schrägstrichs

    def xy(entlang, quer):
        return (entlang, quer) if achse == "x" else (quer, entlang)

    linie(ax, xy(pkt[0], lage), xy(pkt[-1], lage), color=TEXT, linewidth=PT_FEIN, zorder=9)
    for p in pkt:
        px, py = xy(p, lage)
        # Schrägstrich in Leserichtung der Kette «/»: waagrecht «/», senkrecht (90° gedreht) «\»
        k = 1 if achse == "x" else -1
        linie(ax, (px - t, py - k * t), (px + t, py + k * t), color=TEXT, linewidth=PT_MITTEL, zorder=9)
        linie(ax, xy(p, bauteil + aussen * fenster.mm(2)), xy(p, lage + aussen * fenster.mm(1.5)),
              color=LINIE, linewidth=0.25, zorder=9)
    for i, (a, b) in enumerate(zip(pkt, pkt[1:])):
        text = mass_text(b - a)
        kurz = (b - a) < fenster.mm(len(text) * 1.6 + 1)
        # Text aussen an der Linie; kurze Masse abwechselnd innen, damit sie sich nicht überdecken
        seite = -aussen if (kurz and i % 2) else aussen
        quer = lage + seite * fenster.mm(0.8)
        if achse == "x":
            ax.text((a + b) / 2, quer, text, ha="center", va="bottom" if seite > 0 else "top",
                    fontsize=6, color=TEXT, zorder=9)
        else:
            ax.text(quer, (a + b) / 2, text, ha="left" if seite > 0 else "right", va="center",
                    rotation=90, fontsize=6, color=TEXT, zorder=9)


def kote(fenster: Fenster, x: float, z: float, text: str | None = None, links: bool = True) -> None:
    """Höhenkote: Dreieck mit Spitze auf der Höhe z, Text daneben."""
    ax, d = fenster.ax, fenster.mm(1.6)
    ax.add_patch(plt.Polygon([(x, z), (x - d, z + 1.6 * d), (x + d, z + 1.6 * d)], closed=True,
                             facecolor="white", edgecolor=TEXT, linewidth=PT_FEIN, zorder=9))
    linie(ax, (x - 2.5 * d, z), (x + 2.5 * d, z), color=TEXT, linewidth=PT_FEIN, zorder=9)
    ax.text(x + (-1.6 if links else 1.6) * d, z + 2.0 * d, text or kote_text(z),
            ha="right" if links else "left", va="bottom", fontsize=6, color=TEXT, zorder=9)


def titel(fenster: Fenster, x: float, y: float, text: str, massstab: bool = True) -> None:
    """Titel unter einer Zeichnung, linksbündig bei (x, y) in cm, mit Massstab."""
    ax = fenster.ax
    t = ax.text(x, y, text, ha="left", va="top", fontsize=9, fontweight="bold", color=TEXT, zorder=9)
    if massstab:
        ax.annotate(f"  1:{fenster.massstab}", xycoords=t, xy=(1, 0), va="bottom", fontsize=7,
                    color=GRAU, zorder=9)


# --- Plankopf, Legende, Nordpfeil -----------------------------------------

def _zelle(ax, x, y, w, h, beschriftung, wert, gross=False) -> None:
    ax.add_patch(Rectangle((x, y), w, h, fill=False, edgecolor=TEXT, linewidth=PT_FEIN, zorder=3))
    ax.text(x + 1.5, y + h - 1.4, beschriftung, ha="left", va="top", fontsize=5, color=GRAU, zorder=3)
    ax.text(x + 1.5, y + 1.6, wert, ha="left", va="bottom", fontsize=10 if gross else 7.5,
            fontweight="bold" if gross else "normal", color=TEXT, zorder=3)


def plankopf(blatt: Blatt, plan: Plan, planinhalt: str, nummer: str, massstab: str,
             entwurf: bool) -> None:
    ax = blatt.papier
    x0, y0, x1, y1 = PLANKOPF
    p, f = plan.projekt, plan.firma
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=True, facecolor="white",
                           edgecolor=TEXT, linewidth=PT_MITTEL, zorder=2))
    marke = f.get("marke", {})
    linie(ax, (x0, y1), (x1, y1), color=marke.get("akzent", TEXT), linewidth=2.0, zorder=3)

    # Firma: Logo und Adresse
    logo = SKILL / marke["logo"] if marke.get("logo") else None
    if logo is not None and logo.exists():
        bild = plt.imread(logo)
        lb = 50.0
        lh = lb * bild.shape[0] / bild.shape[1]
        ax.imshow(bild, extent=(x0 + 4, x0 + 4 + lb, y1 - 4 - lh, y1 - 4), zorder=3)
    else:
        lh = 6.0
        ax.text(x0 + 4, y1 - 4, f.get("name", ""), ha="left", va="top", fontsize=12,
                fontweight="bold", color=TEXT, zorder=3)
    adr = f.get("adresse", {})
    zeilen = [f.get("name", ""), adr.get("strasse", ""), adr.get("plz_ort", ""),
              f.get("telefon", ""), f.get("email", ""), f.get("web", "")]
    ax.text(x0 + 4, y1 - 7 - lh, "\n".join(z for z in zeilen if z), ha="left", va="top",
            fontsize=5.5, color=GRAU, linespacing=1.45, zorder=3)

    # Felder rechts
    fx = x0 + 60
    fw = x1 - fx
    _zelle(ax, fx, y1 - 11, fw, 11, "Projekt", p.name, gross=True)
    _zelle(ax, fx, y1 - 19, fw * 0.6, 8, "Adresse", p.adresse)
    _zelle(ax, fx + fw * 0.6, y1 - 19, fw * 0.4, 8, "Bauherrschaft", p.bauherr or "–")
    _zelle(ax, fx, y1 - 30, fw, 11, "Planinhalt", planinhalt, gross=True)
    _zelle(ax, fx, y1 - 40, fw / 3, 10, "Massstab", massstab)
    _zelle(ax, fx + fw / 3, y1 - 40, fw / 3, 10, "Format", "A3")
    _zelle(ax, fx + 2 * fw / 3, y1 - 40, fw / 3, 10, "Datum", datum_text(p.datum))
    _zelle(ax, fx, y0, fw / 3, 12, "Plan-Nr.", nummer, gross=True)
    _zelle(ax, fx + fw / 3, y0, fw / 3, 12, "Index", p.index or "–")
    _zelle(ax, fx + 2 * fw / 3, y0, fw / 3, 12, "Gezeichnet", p.gezeichnet or "–")
    if entwurf:
        ax.text(x0 + 4, y0 + 3, "ENTWURF – nicht zur Ausführung", ha="left", va="bottom",
                fontsize=7, fontweight="bold", color=FUELLUNG["neu"], zorder=3)


def legende(blatt: Blatt, plan: Plan, notiz: str | None = None) -> None:
    ax = blatt.papier
    x, y = 25.0, 50.0
    ax.text(x, y + 7, "Legende", ha="left", va="bottom", fontsize=7, fontweight="bold", color=TEXT)
    for i, (status, text) in enumerate((("bestand", "Bestand"), ("abbruch", "Abbruch"), ("neu", "Neu"))):
        xi = x + i * 30
        ax.add_patch(Rectangle((xi, y), 10, 4, facecolor=FUELLUNG[status], edgecolor=KONTUR[status],
                               linewidth=PT_FEIN, linestyle="solid" if status != "abbruch" else (0, (4, 2))))
        ax.text(xi + 12, y + 2, text, ha="left", va="center", fontsize=7, color=TEXT)
    notizen = [notiz or "Masse in m, unter 1 m in cm. Alle Masse vor Ausführung am Bau prüfen."]
    if plan.angenommen:
        notizen.append("Angenommen, nicht gemessen:")
        notizen += [f"– {a}" for a in plan.angenommen[:6]]
        if len(plan.angenommen) > 6:
            notizen.append(f"– und {len(plan.angenommen) - 6} weitere")
    ax.text(x, y - 4, "\n".join(notizen), ha="left", va="top", fontsize=5.5, color=GRAU, linespacing=1.4)


def nordpfeil(blatt: Blatt, winkel: float) -> None:
    ax = blatt.papier
    cx, cy, r = ZEICHENFLAECHE[2] - 10, ZEICHENFLAECHE[3] - 10, 6.0
    ax.add_patch(Circle((cx, cy), r, fill=False, edgecolor=TEXT, linewidth=PT_FEIN))
    a = math.radians(90 + winkel)
    spitze = (cx + r * math.cos(a), cy + r * math.sin(a))
    fuss_l = (cx + 0.45 * r * math.cos(a + 2.5), cy + 0.45 * r * math.sin(a + 2.5))
    fuss_r = (cx + 0.45 * r * math.cos(a - 2.5), cy + 0.45 * r * math.sin(a - 2.5))
    ax.add_patch(plt.Polygon([spitze, fuss_l, (cx, cy), fuss_r], closed=True, facecolor=TEXT,
                             edgecolor=TEXT, linewidth=PT_FEIN))
    ax.text(cx + (r + 2.5) * math.cos(a), cy + (r + 2.5) * math.sin(a), "N", ha="center",
            va="center", fontsize=7, fontweight="bold", color=TEXT)

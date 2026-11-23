"""Visualisierung vorher/nachher: Foto vom Bestand neben dem Bild, das ChatGPT/Codex
daraus in derselben Perspektive erzeugt hat. Ein Paar pro A3-Blatt.

Die Bilder erzeugt der Host (siehe visualisierung.md), dieses Modul setzt sie nur
aufs Blatt. Beide Bilder werden gleich hoch gezeigt, damit man sie vergleichen kann.
"""

from __future__ import annotations

import textwrap

from blatt import GRAU, PLANKOPF, RAHMEN, TEXT, ZEICHENFLAECHE, Blatt, plankopf
from fotos import bild_laden
from modell import Plan

ABSTAND = 8.0  # mm zwischen vorher und nachher
HINWEIS = "KI-Visualisierung, nicht massstäblich. Massgebend sind die Pläne."


def visualisierung_blaetter(plan: Plan, entwurf: bool = False) -> list[Blatt]:
    fx0, fy0, fx1, fy1 = ZEICHENFLAECHE
    w = (fx1 - fx0 - ABSTAND) / 2
    h = fy1 - fy0 - 12
    blaetter = []
    for vi, vis in enumerate(plan.visualisierungen):
        blatt = Blatt()
        ax = blatt.papier
        bilder = [bild_laden(vis.vorher), bild_laden(vis.nachher)]
        # gemeinsame Höhe, so dass beide nebeneinander in die Zeichenfläche passen
        bh = min(h, *(w * b.shape[0] / b.shape[1] for b in bilder))
        for i, (bild, beschriftung) in enumerate(zip(bilder, ("Vorher", "Nachher"))):
            bw = bh * bild.shape[1] / bild.shape[0]
            x0 = fx0 + i * (w + ABSTAND) + (w - bw) / 2
            y1 = fy1 - 3
            ax.imshow(bild, extent=(x0, x0 + bw, y1 - bh, y1), zorder=2, interpolation="antialiased")
            ax.text(x0, y1 - bh - 2, beschriftung, ha="left", va="top", fontsize=9,
                    fontweight="bold", color=TEXT)
        tx, ty = fx0, PLANKOPF[3] - 2
        ax.text(tx, ty, vis.titel or "Visualisierung", ha="left", va="top", fontsize=9,
                fontweight="bold", color=TEXT)
        if vis.wuensche:
            zeilen = textwrap.fill(f"Wünsche: {vis.wuensche}", 95)
            ax.text(tx, ty - 6, zeilen, ha="left", va="top", fontsize=7, color=TEXT, linespacing=1.4)
        ax.text(tx, RAHMEN[1] + 3, HINWEIS, ha="left", va="bottom", fontsize=6.5, color=GRAU)
        nummer = f"{plan.projekt.plannummer}-V{vi + 1}"
        titel = "Visualisierung" + (f" {vis.titel}" if vis.titel else "")
        plankopf(blatt, plan, titel, nummer, "–", entwurf)
        blaetter.append(blatt)
    return blaetter


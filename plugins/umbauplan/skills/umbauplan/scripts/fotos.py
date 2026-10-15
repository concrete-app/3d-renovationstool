"""Fotodokumentation: die Fotos aus plan.json, sechs pro A3-Blatt, mit Titel.

Fotos werden nach der EXIF-Drehung aufgerichtet (Handyfotos liegen sonst quer) und
auf höchstens 1600 px verkleinert, damit die PDF nicht riesig wird.
"""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageOps

from blatt import GRAU, TEXT, ZEICHENFLAECHE, Blatt, plankopf
from modell import Plan

PRO_BLATT = (3, 2)  # Spalten, Zeilen
MAX_PIXEL = 1600


def _laden(datei) -> np.ndarray:
    with Image.open(datei) as bild:
        bild = ImageOps.exif_transpose(bild).convert("RGB")
        bild.thumbnail((MAX_PIXEL, MAX_PIXEL))
        return np.asarray(bild)


def foto_blaetter(plan: Plan, entwurf: bool = False) -> list[Blatt]:
    spalten, zeilen = PRO_BLATT
    n = spalten * zeilen
    gruppen = [plan.fotos[i:i + n] for i in range(0, len(plan.fotos), n)]
    fx0, fy0, fx1, fy1 = ZEICHENFLAECHE
    zw, zh = (fx1 - fx0) / spalten, (fy1 - fy0) / zeilen
    blaetter = []
    for bi, gruppe in enumerate(gruppen):
        blatt = Blatt()
        ax = blatt.papier
        for i, foto in enumerate(gruppe):
            sp, ze = i % spalten, i // spalten
            x0, y1 = fx0 + sp * zw + 3, fy1 - ze * zh - 3
            w, h = zw - 6, zh - 14
            bild = _laden(foto.datei)
            f = min(w / bild.shape[1], h / bild.shape[0])
            bw, bh = bild.shape[1] * f, bild.shape[0] * f
            bx, by = x0 + (w - bw) / 2, y1 - bh
            ax.imshow(bild, extent=(bx, bx + bw, by, by + bh), zorder=2, interpolation="antialiased")
            nr = bi * n + i + 1
            ax.text(bx, by - 2, f"{nr}  {foto.titel}".rstrip(), ha="left", va="top", fontsize=7.5,
                    fontweight="bold", color=TEXT)
            ax.text(bx, by - 6, foto.datei.name, ha="left", va="top", fontsize=5.5, color=GRAU)
        nummer = f"{plan.projekt.plannummer}-F{bi + 1}"
        titel = "Fotodokumentation" + (f" ({bi + 1}/{len(gruppen)})" if len(gruppen) > 1 else "")
        plankopf(blatt, plan, titel, nummer, "–", entwurf)
        blaetter.append(blatt)
    return blaetter

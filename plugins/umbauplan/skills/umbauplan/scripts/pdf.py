"""Setzt alle Blätter zu einer PDF zusammen.

Reihenfolge: Grundrisse (je Geschoss), Schnitte, Ansichten, 3D (je Geschoss,
zwei Blickwinkel), Visualisierungen, Fotos. Welche Blätter es gibt, steht in plan.blaetter.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

import ansichten
import axonometrie
import fotos
import grundriss
import visualisierung
from blatt import schrift_setzen
from modell import Plan

BLICKWINKEL_3D = (225.0, 45.0)  # von unten links und von oben rechts im Grundriss


@dataclass
class Erzeugt:
    kurz: str        # für Dateinamen der Vorschau
    inhalt: str
    massstab: str


def pdf_erzeugen(plan: Plan, ziel: Path, entwurf: bool = False,
                 vorschau: Path | None = None) -> list[Erzeugt]:
    schrift_setzen(plan)
    schnitte = ansichten.schnitte_bestimmen(plan) if "schnitte" in plan.blaetter else []

    def blaetter():
        if "grundriss" in plan.blaetter:
            for g in plan.geschosse:
                blatt, fenster = grundriss.grundriss_blatt(plan, g, schnitte, entwurf)
                yield blatt, Erzeugt(g.id, f"Grundriss {g.name}", f"1:{fenster.massstab}")
        if schnitte:
            blatt, m = ansichten.schnitte_blatt(plan, schnitte, entwurf)
            namen = ", ".join(f"{s.name}–{s.name}" for s in schnitte)
            yield blatt, Erzeugt("schnitte", f"Schnitte {namen}", f"1:{m}")
        if "ansichten" in plan.blaetter:
            blatt, m = ansichten.ansichten_blatt(plan, entwurf)
            yield blatt, Erzeugt("ansichten", "Ansichten (4 Seiten)", f"1:{m}")
        if "3d" in plan.blaetter:
            for g in plan.geschosse:
                for az in BLICKWINKEL_3D:
                    blatt = axonometrie.blatt_3d(plan, g, az, entwurf)
                    yield blatt, Erzeugt(f"3d_{g.id}_{int(az)}", f"3D {g.name} vorher/nachher ({int(az)}°)",
                                         "ohne")
        if "fotos" in plan.blaetter and plan.fotos:
            for i, blatt in enumerate(fotos.foto_blaetter(plan, entwurf)):
                yield blatt, Erzeugt(f"fotos{i + 1}", "Fotodokumentation", "–")
        if "visualisierung" in plan.blaetter:
            for i, blatt in enumerate(visualisierung.visualisierung_blaetter(plan, entwurf)):
                titel = plan.visualisierungen[i].titel
                yield blatt, Erzeugt(f"visualisierung{i + 1}", f"Visualisierung {titel}".strip(), "–")

    erzeugt = []
    with PdfPages(ziel, metadata={"Title": f"{plan.projekt.name} – Umbau",
                                  "Author": plan.firma.get("name", ""),
                                  "Subject": plan.projekt.plannummer}) as pdf:
        for blatt, info in blaetter():
            pdf.savefig(blatt.fig)
            if vorschau is not None:
                blatt.fig.savefig(vorschau.with_name(f"{vorschau.stem}_{info.kurz}.png"), dpi=110)
            plt.close(blatt.fig)
            erzeugt.append(info)
    return erzeugt

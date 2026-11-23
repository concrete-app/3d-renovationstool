"""Stückliste aus dem Plan: welche Artikel aus dem Bauteilkatalog wie oft vorkommen.

Grundlage für die Offerte im Offerten-Tool. Die Artikel-IDs sind die Positionen dort; Preise kennt der
Plan nicht und schreibt sie nie. Mengen:
- jedes Küchenelement mit `artikel`: 1 Stk (nach Artikel, Status und Raum zusammengezählt);
- Einbaugeräte (`einbau`) neuer Elemente: 1 Stk des Geräts aus dem Bauteilkatalog (typ "geraet");
- Arbeitsplatte und Sockel: Laufmeter aus der Breite der neuen Unterschränke (Sockel auch Hochschränke).
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import geometrie
from modell import KUECHENTYPEN, Plan, bauteile_laden


def _raum(g, b, zustand: str) -> str:
    mitte = geometrie.objekt_polygon(b).centroid
    for r in geometrie.raeume(g, zustand):
        if r.flaeche.contains(mitte):
            return r.name or ""
    return ""


def stueckliste(plan: Plan) -> dict:
    bauteile = bauteile_laden()
    geraet = {e: b["id"] for b in bauteile.values() if b.get("typ") == "geraet" for e in b.get("einbau", [])}
    erstes = {t: next((b["id"] for b in bauteile.values() if b.get("typ") == t), "") for t in ("arbeitsplatte", "sockel")}

    zeilen: dict[tuple, dict] = {}
    ohne_artikel: list[str] = []

    def dazu(artikel: str, menge: float, einheit: str, status: str, raum: str) -> None:
        if not artikel:
            return
        z = zeilen.setdefault((artikel, status, raum), {
            "artikel": artikel, "titel": bauteile.get(artikel, {}).get("titel", ""),
            "menge": 0.0, "einheit": einheit, "status": status, "raum": raum})
        z["menge"] = round(z["menge"] + menge, 2)

    for g in plan.geschosse:
        for b in g.objekte:
            if b.typ not in KUECHENTYPEN or b.status == "bestand":
                continue
            raum = _raum(g, b, "neu" if b.status == "neu" else "bestand")
            if not b.artikel:
                ohne_artikel.append(f"{b.id} ({b.typ} {b.breite:g} cm, {b.status})")
            dazu(b.artikel, 1, "Stk", b.status, raum)
            if b.status != "neu":
                continue
            for e in b.einbau:
                dazu(geraet.get(e, ""), 1, "Stk", "neu", raum)
            if b.typ == "unterschrank":
                dazu(erstes["arbeitsplatte"], b.breite / 100, "lfm", "neu", raum)
            if b.typ in ("unterschrank", "hochschrank"):
                dazu(erstes["sockel"], b.breite / 100, "lfm", "neu", raum)

    return {
        "plannummer": plan.projekt.plannummer,
        "stand": dt.date.today().isoformat(),
        "hinweis": "Artikel-IDs = Positionen im Offerten-Tool. Nur Artikel und Mengen.",
        "positionen": sorted(zeilen.values(), key=lambda z: (z["status"], z["raum"], z["artikel"])),
        "ohne_artikel": ohne_artikel,
    }


def schreiben(plan: Plan, ziel: Path) -> dict | None:
    """Schreibt die Stückliste, wenn der Plan Küchenelemente hat; sonst nichts (None)."""
    if not any(b.typ in KUECHENTYPEN for g in plan.geschosse for b in g.objekte):
        return None
    daten = stueckliste(plan)
    ziel.write_text(json.dumps(daten, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return daten

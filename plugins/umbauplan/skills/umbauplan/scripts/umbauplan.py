#!/usr/bin/env python3
"""Erzeugt aus plan.json die Umbaupläne (eine PDF) und das IFC-Modell.

    python umbauplan.py plan.json ausgabe/ [--blaetter grundriss,schnitte,...]
                        [--entwurf] [--vorschau] [--nur-pruefen]

Die PDF enthält Grundrisse, Schnitte, Ansichten, 3D vorher/nachher, Visualisierungen und Fotos
(was davon, steht in plan.json unter "blaetter" oder in --blaetter).

Braucht shapely, matplotlib und Pillow, für das IFC zusätzlich ifcopenshell
(fehlt es, entsteht nur die PDF). Ohne Installation:

    uv run --python 3.12 --with ifcopenshell --with shapely --with matplotlib \\
        python umbauplan.py plan.json ausgabe/

Mängel (Exit-Code 1) nennen das Feld; Warnungen stoppen nichts, sollten aber
angeschaut werden. --entwurf erlaubt Platzhalter wie <PLZ Ort> und schreibt
«ENTWURF» auf den Plan. --vorschau legt pro Blatt ein PNG daneben, damit
man die Pläne ansehen kann, ohne die PDF zu öffnen.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import geometrie                                   # noqa: E402
from modell import BLAETTER, Fehlerhaft, laden, mass_text, pruefen  # noqa: E402


def dateiname(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-") or "plan"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("eingabe", type=Path)
    ap.add_argument("ausgabe", type=Path, nargs="?", default=Path("ausgabe"))
    ap.add_argument("--entwurf", action="store_true", help="Platzhalter erlauben, Plan als Entwurf kennzeichnen")
    ap.add_argument("--vorschau", action="store_true", help="zusätzlich PNG pro Blatt")
    ap.add_argument("--blaetter", help=f"nur diese Blätter, mit Komma: {','.join(BLAETTER)}")
    ap.add_argument("--nur-pruefen", action="store_true", help="nur prüfen, nichts erzeugen")
    args = ap.parse_args(argv)

    try:
        daten = laden(args.eingabe)
        if args.blaetter:
            daten["blaetter"] = [b.strip() for b in args.blaetter.split(",") if b.strip()]
        plan = pruefen(daten, entwurf=args.entwurf, basis=args.eingabe.resolve().parent)
    except Fehlerhaft as e:
        print(f"MÄNGEL ({len(e.maengel)}), nichts erzeugt:")
        for mangel in e.maengel:
            print(f"  - {mangel}")
        return 1

    warnungen = [h for g in plan.geschosse for h in geometrie.warnungen(g)]

    print(f"Projekt: {plan.projekt.name} ({plan.projekt.plannummer})")
    for g in plan.geschosse:
        print(f"\n{g.name} ({g.id}): {len(g.waende)} Wände, {len(g.oeffnungen)} Öffnungen")
        for zustand, titel in (("bestand", "Räume vorher"), ("neu", "Räume nachher")):
            raeume = geometrie.raeume(g, zustand)
            summe = sum(r.m2 for r in raeume)
            print(f"  {titel}: {len(raeume)}, zusammen {summe:.2f} m²")
            for r in raeume:
                masse = ""
                if r.ist_rechteck:
                    bx, by = r.lichte_masse
                    masse = f"  ({mass_text(bx)} × {mass_text(by)})"
                print(f"    {r.name or '(ohne Namen)':<24} {r.m2:7.2f} m²{masse}")
    if plan.angenommen:
        print("\nAngenommen (nicht gemessen, steht auch auf dem Plan):")
        for a in plan.angenommen:
            print(f"  - {a}")
    if warnungen:
        print(f"\nWARNUNGEN ({len(warnungen)}):")
        for w in warnungen:
            print(f"  - {w}")

    if args.nur_pruefen:
        return 0

    from pdf import pdf_erzeugen                   # erst hier: matplotlib ist langsam zu laden
    try:
        from ifc_export import ifc_erzeugen
    except ImportError:                            # z. B. ChatGPT-Sandbox ohne ifcopenshell
        ifc_erzeugen = None

    try:
        args.ausgabe.mkdir(parents=True, exist_ok=True)
        stamm = dateiname(plan.projekt.plannummer)
        pdf = args.ausgabe / f"{stamm}_umbau.pdf"
        ifc = args.ausgabe / f"{stamm}.ifc"
        vorschau = args.ausgabe / f"{stamm}_vorschau.png" if args.vorschau else None
        blaetter = pdf_erzeugen(plan, pdf, entwurf=args.entwurf, vorschau=vorschau)
        if ifc_erzeugen:
            ifc_erzeugen(plan, ifc)
    except Fehlerhaft as e:
        print("\nMÄNGEL beim Zeichnen:")
        for mangel in e.maengel:
            print(f"  - {mangel}")
        return 1

    print(f"\nErzeugt: {pdf} ({len(blaetter)} Blätter)")
    wunsch = f"1:{plan.projekt.massstab}"
    for i, b in enumerate(blaetter, 1):
        hinweis = f" ({wunsch} passte nicht auf A3)" if b.massstab.startswith("1:") and b.massstab != wunsch else ""
        print(f"  {i:2}. {b.inhalt}, {b.massstab}{hinweis}")
    if ifc_erzeugen:
        print(f"  {ifc}")
    else:
        print("  KEIN IFC: ifcopenshell fehlt (pip install ifcopenshell). Die PDF ist vollständig.")
    if vorschau:
        print("Vorschau:")
        for b in blaetter:
            print(f"  {vorschau.with_name(f'{vorschau.stem}_{b.kurz}.png')}")
    if args.entwurf:
        print("\nENTWURF: nicht als fertig weitergeben.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Macht aus einer PDF (Scan, Situationsaufnahme, alter Plan) ein PNG pro Seite, damit man
jede Seite als Bild ansehen kann. Handschrift und Masse in Scans liest man nur so.

    python seiten.py aufnahme.pdf [ausgabe/] [--dpi 200]

Nimmt, was da ist: PyMuPDF (fitz), sonst pypdfium2, sonst pdftoppm (poppler). Druckt die
Pfade der PNGs; die schaust du dann einzeln an. Zum Vergrössern eines Ausschnitts
(z. B. einer Masskette): --dpi 300.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def _mit_fitz(pdf: Path, ziel: Path, dpi: int) -> list[Path]:
    import fitz  # PyMuPDF
    pfade = []
    with fitz.open(pdf) as doc:
        for i, seite in enumerate(doc, 1):
            p = ziel / f"{pdf.stem}_seite{i}.png"
            seite.get_pixmap(dpi=dpi).save(p)
            pfade.append(p)
    return pfade


def _mit_pdfium(pdf: Path, ziel: Path, dpi: int) -> list[Path]:
    import pypdfium2 as pdfium
    pfade = []
    doc = pdfium.PdfDocument(str(pdf))
    for i in range(len(doc)):
        p = ziel / f"{pdf.stem}_seite{i + 1}.png"
        doc[i].render(scale=dpi / 72).to_pil().save(p)
        pfade.append(p)
    return pfade


def _mit_pdftoppm(pdf: Path, ziel: Path, dpi: int) -> list[Path]:
    if not shutil.which("pdftoppm"):
        raise ImportError("pdftoppm fehlt")
    subprocess.run(["pdftoppm", "-png", "-r", str(dpi), str(pdf), str(ziel / f"{pdf.stem}_seite")], check=True)
    return sorted(ziel.glob(f"{pdf.stem}_seite*.png"))


def seiten(pdf: Path, ziel: Path, dpi: int = 200) -> list[Path]:
    ziel.mkdir(parents=True, exist_ok=True)
    gruende = []
    for weg in (_mit_fitz, _mit_pdfium, _mit_pdftoppm):
        try:
            return weg(pdf, ziel, dpi)
        except ImportError as e:
            gruende.append(str(e))
    raise RuntimeError("Kein Werkzeug für PDF → Bild gefunden (" + "; ".join(gruende) + "). "
                       "pip install pymupdf, oder die Person bittet um Screenshots der Seiten.")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf", type=Path)
    ap.add_argument("ausgabe", type=Path, nargs="?")
    ap.add_argument("--dpi", type=int, default=200)
    args = ap.parse_args(argv)
    try:
        pfade = seiten(args.pdf, args.ausgabe or args.pdf.with_suffix(""), args.dpi)
    except (RuntimeError, subprocess.CalledProcessError) as e:
        print(f"FEHLT: {e}")
        return 1
    print(f"{len(pfade)} Seite(n). Jede einzeln ansehen:")
    for p in pfade:
        print(f"  {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

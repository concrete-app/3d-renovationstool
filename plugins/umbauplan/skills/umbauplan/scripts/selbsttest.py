#!/usr/bin/env python3
"""Selbsttest: Läuft der Umbauplan-Workflow in dieser Umgebung?

    python selbsttest.py [ausgabeordner]

Prüft Python, Bibliotheken, Skill-Ordner, Firmendaten, Logo und Schrift und erzeugt
dann mit den Originalfunktionen (modell.pruefen, umbauplan.erzeugen) den Plansatz
für beispiele/bad.json, mit zwei Testbildern als Fotodokumentation. Danach prüft
er das Ergebnis: 6 Seiten A3, Plankopf mit Firmendaten und Logo auf jeder Seite,
Massstab 1:50, keine Geometrie-Warnungen, IFC lesbar.

Jede Zeile ist OK, HINWEIS (geht, aber eingeschränkt) oder FEHLT (mit Ursache und
was zu tun ist). Exit-Code 0, wenn nichts FEHLT.

Ohne Ausgabeordner schreibt er nach /mnt/user-data/outputs (Claude), /mnt/data
(ChatGPT) oder ./umbauplan-selbsttest.
"""

from __future__ import annotations

import importlib
import json
import re
import shutil
import sys
import traceback
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from modell import SKILL, _platzhalter, firma_laden  # noqa: E402  (nur Standardbibliothek)

PFLICHT = ("shapely", "matplotlib", "numpy", "PIL")
A3_PT = (1190.55, 841.89)
ERWARTET = ["OG", "schnitte", "ansichten", "3d_OG_225", "3d_OG_45", "fotos1"]


class Bericht:
    def __init__(self):
        self.fehlt = 0

    def ok(self, text: str) -> None:
        print(f"OK       {text}")

    def hinweis(self, text: str) -> None:
        print(f"HINWEIS  {text}")

    def fehlt_(self, text: str, tun: str = "") -> None:
        self.fehlt += 1
        print(f"FEHLT    {text}" + (f"\n         → {tun}" if tun else ""))

    def pruefe(self, bedingung: bool, text: str, tun: str = "") -> bool:
        (self.ok(text) if bedingung else self.fehlt_(text, tun))
        return bedingung


def standard_ausgabe() -> Path:
    for ordner in (Path("/mnt/user-data/outputs"), Path("/mnt/data")):
        if ordner.is_dir():
            return ordner / "umbauplan-selbsttest"
    return Path.cwd() / "umbauplan-selbsttest"


def testbilder(ordner: Path) -> list[dict]:
    from PIL import Image, ImageDraw
    fotos = []
    for i, farbe in enumerate(("#B9C3CC", "#CFC6B8"), 1):
        bild = Image.new("RGB", (1200, 900), farbe)
        zeichnen = ImageDraw.Draw(bild)
        zeichnen.rectangle((40, 40, 1160, 860), outline="#555555", width=6)
        zeichnen.text((80, 80), f"Testbild {i} - kein echtes Foto", fill="#222222")
        name = f"testbild{i}.jpg"
        bild.save(ordner / name)
        fotos.append({"datei": name, "titel": f"Testbild {i} (Selbsttest)"})
    return fotos


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    ausgabe = Path(argv[0]) if argv else standard_ausgabe()
    b = Bericht()
    print(f"Umbauplan-Selbsttest\nSkill-Ordner: {SKILL}\nAusgabe:      {ausgabe.resolve()}\n")

    # --- Umgebung -----------------------------------------------------------
    b.pruefe(sys.version_info >= (3, 10), f"Python {sys.version.split()[0]}",
             "Python 3.10 oder neuer nötig")
    fehlend = []
    for modul in PFLICHT:
        try:
            m = importlib.import_module(modul)
            b.ok(f"{modul} {getattr(m, '__version__', '')}")
        except ImportError as e:
            fehlend.append(modul)
            b.fehlt_(f"{modul} fehlt ({e})", "pip install shapely matplotlib numpy pillow")
    try:
        import ifcopenshell
        b.ok(f"ifcopenshell {ifcopenshell.version}")
        hat_ifc = True
    except ImportError:
        b.hinweis("ifcopenshell fehlt: es entsteht kein IFC, die PDF ist trotzdem vollständig "
                  "(pip install ifcopenshell, geht nur mit Internet)")
        hat_ifc = False
    try:
        import pypdf
        b.ok(f"pypdf {pypdf.__version__} (für die Textprüfung der PDF)")
        hat_pypdf = True
    except ImportError:
        b.hinweis("pypdf fehlt: Firmendaten im PDF werden nicht als Text geprüft (pip install pypdf)")
        hat_pypdf = False

    # --- Skill-Ordner, Firma, Logo, Schrift -----------------------------------
    for datei in ("SKILL.md", "firma.json", "beispiele/bad.json", "scripts/umbauplan.py"):
        b.pruefe((SKILL / datei).is_file(), f"{datei} gefunden",
                 "Skill-Ordner unvollständig: ganzen Ordner mit allen Dateien kopieren")
    firma = firma_laden()
    platzhalter: list[str] = []
    _platzhalter(firma, "firma.json", platzhalter)
    b.pruefe(not platzhalter, "firma.json ohne Platzhalter", "; ".join(platzhalter))
    marke = firma.get("marke", {})
    for feld, wert in (("Name", firma.get("name")), ("Strasse", firma.get("adresse", {}).get("strasse")),
                       ("PLZ Ort", firma.get("adresse", {}).get("plz_ort")), ("Telefon", firma.get("telefon")),
                       ("E-Mail", firma.get("email")), ("Web", firma.get("web")),
                       ("Akzentfarbe", marke.get("akzent")), ("Schrift", marke.get("schrift"))):
        b.pruefe(bool(wert), f"Firma {feld}: {wert}", f"in firma.json eintragen")
    logo = SKILL / marke.get("logo", "")
    b.pruefe(bool(marke.get("logo")) and logo.is_file(), f"Logo {logo.name}", f"{logo} fehlt")
    for ttf in ("Roboto-Regular.ttf", "Roboto-Bold.ttf"):
        b.pruefe((SKILL / "assets" / "schrift" / ttf).is_file(), f"Schrift {ttf}",
                 "assets/schrift/ mitkopieren")
    if fehlend:
        b.fehlt_("Abbruch: ohne " + ", ".join(fehlend) + " kann der Plan nicht gezeichnet werden")
        return 1
    import blatt  # noqa: F401  registriert die Schrift
    from matplotlib import font_manager
    try:
        pfad = font_manager.findfont(font_manager.FontProperties(family=marke.get("schrift", "Roboto")),
                                     fallback_to_default=False)
        b.ok(f"Schrift {marke.get('schrift')} in matplotlib: {Path(pfad).name}")
    except ValueError:
        b.fehlt_(f"Schrift {marke.get('schrift')} nicht in matplotlib registriert", "assets/schrift/ prüfen")

    # --- Ausgabeordner ----------------------------------------------------------
    try:
        ausgabe.mkdir(parents=True, exist_ok=True)
        (ausgabe / ".schreibtest").write_text("ok")
        (ausgabe / ".schreibtest").unlink()
        b.ok("Ausgabeordner schreibbar")
    except OSError as e:
        b.fehlt_(f"Ausgabeordner nicht schreibbar: {e}", "anderen Ordner angeben: python selbsttest.py <ordner>")
        return 1

    # --- Gesamtlauf mit den Originalfunktionen ------------------------------------
    import geometrie
    import modell
    import umbauplan
    daten = json.loads((SKILL / "beispiele" / "bad.json").read_text(encoding="utf-8"))
    daten["fotos"] = testbilder(ausgabe)
    (ausgabe / "plan.json").write_text(json.dumps(daten, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        plan = modell.pruefen(daten, basis=ausgabe)
        erg = umbauplan.erzeugen(plan, ausgabe, vorschau=True)
    except Exception as e:  # noqa: BLE001  jede Ursache soll wörtlich sichtbar sein
        b.fehlt_(f"Plansatz nicht erzeugt: {type(e).__name__}: {e}", "Fehlermeldung unten der Person zeigen")
        traceback.print_exc()
        return 1
    b.ok(f"Plansatz erzeugt mit scripts/umbauplan.py ({len(erg.blaetter)} Blätter)")

    # --- Ergebnis prüfen ----------------------------------------------------------
    kurz = [e.kurz for e in erg.blaetter]
    b.pruefe(kurz == ERWARTET, "Blätter: Grundriss, Schnitte, Ansichten, 3D ×2, Fotodokumentation",
             f"erzeugt wurden {kurz}")
    for e in erg.blaetter[:3]:
        b.pruefe(e.massstab == "1:50", f"{e.inhalt}: Massstab {e.massstab}", "erwartet 1:50")
    warnungen = [w for g in plan.geschosse for w in geometrie.warnungen(g)]
    b.pruefe(not warnungen, "Geometrie ohne Warnungen", "; ".join(warnungen))

    b.pruefe(erg.pdf.is_file() and erg.pdf.stat().st_size > 10_000, f"PDF gespeichert: {erg.pdf}")
    roh = erg.pdf.read_bytes()
    seiten = len(re.findall(rb"/Type\s*/Page\b", roh))
    b.pruefe(seiten == 6, f"PDF hat {seiten} Seiten", "erwartet 6")
    formate = re.findall(rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\]", roh)
    b.pruefe(len(formate) == seiten and all(abs(float(w) - A3_PT[0]) < 1 and abs(float(h) - A3_PT[1]) < 1
                                            for w, h in formate), "Alle Seiten A3 quer", f"gefunden: {formate}")
    if hat_pypdf:
        from pypdf import PdfReader
        try:
            reader = PdfReader(erg.pdf)
            b.ok("PDF lässt sich öffnen (pypdf)")
            adr = firma.get("adresse", {})
            muss = [firma.get("name", "").split("|")[0].strip(), adr.get("strasse", ""),
                    firma.get("telefon", ""), firma.get("email", ""), plan.projekt.plannummer]
            for i, seite in enumerate(reader.pages, 1):
                text = seite.extract_text() or ""
                fehlt = [m for m in muss if m and m not in text]
                b.pruefe(not fehlt, f"Seite {i}: Plankopf mit Firmendaten", f"fehlt: {fehlt}")
                b.pruefe(len(seite.images) >= 1, f"Seite {i}: Logo eingebettet", "kein Bild auf der Seite")
        except Exception as e:  # noqa: BLE001
            b.fehlt_(f"PDF lässt sich nicht öffnen: {e}")
    fehlende = [v.name for v in erg.vorschauen if not v.is_file()]
    b.pruefe(not fehlende and len(erg.vorschauen) == 6, f"{len(erg.vorschauen)} Vorschau-PNGs",
             f"fehlen: {fehlende}")

    if hat_ifc:
        try:
            import ifcopenshell.util.element as element
            modell_ifc = ifcopenshell.open(str(erg.ifc))
            zahl = {k: len(modell_ifc.by_type(k)) for k in ("IfcWall", "IfcDoor", "IfcWindow", "IfcSpace")}
            raeume = sum(len(geometrie.raeume(g, "neu")) for g in plan.geschosse)
            b.pruefe(all(zahl.values()) and zahl["IfcSpace"] == raeume,
                     f"IFC lesbar: {erg.ifc.name} ({', '.join(f'{v} {k}' for k, v in zahl.items())})",
                     f"erwartet {raeume} Räume")
            status = {w for wand in modell_ifc.by_type("IfcWall")
                      for pset in element.get_psets(wand).values() for k, w in pset.items() if k == "Status"}
            b.pruefe({"EXISTING", "DEMOLISH", "NEW"} <= status, f"IFC Umbaustatus: {sorted(status)}",
                     "Status in Pset_WallCommon fehlt")
        except Exception as e:  # noqa: BLE001
            b.fehlt_(f"IFC nicht lesbar: {e}")
    else:
        b.hinweis("Kein IFC erzeugt, weil ifcopenshell fehlt")

    print("\nDateien:")
    for datei in sorted(ausgabe.iterdir()):
        print(f"  {datei}")
    if b.fehlt:
        print(f"\nERGEBNIS: {b.fehlt} Punkt(e) FEHLT. Ursache oben; keinen Ersatz-Plan bauen.")
        return 1
    print("\nERGEBNIS: Der Umbauplan-Workflow läuft in dieser Umgebung.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

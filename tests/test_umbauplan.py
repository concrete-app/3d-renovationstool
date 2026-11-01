"""Der umbauplan-Skill: Prüfung, Geometrie, Massstab und IFC.

Getestet wird, was niemand sieht, bis es auf der Baustelle falsch ist: eine
Fläche, ein Massstab, ein Umbaustatus im IFC. Wie der Plan aussieht, prüft man
mit den Augen (--vorschau).
"""

from __future__ import annotations

import copy
import itertools
import json
import sys
from pathlib import Path

import pytest

SKILL = (Path(__file__).resolve().parent.parent / "plugins" / "umbauplan"
         / "skills" / "umbauplan")
sys.path.insert(0, str(SKILL / "scripts"))

import geometrie                                                # noqa: E402
import modell                                                   # noqa: E402
from modell import Fehlerhaft                                   # noqa: E402

FIRMA = {"name": "Test GmbH", "adresse": {"strasse": "Weg 1", "plz_ort": "8000 Zürich"}}


def beispiel() -> dict:
    return json.loads((SKILL / "beispiele" / "wohnung.json").read_text(encoding="utf-8"))


def pruefen(daten: dict) -> modell.Plan:
    return modell.pruefen(daten, FIRMA)


def maengel(daten: dict) -> str:
    with pytest.raises(Fehlerhaft) as e:
        pruefen(daten)
    return "\n".join(e.value.maengel)


def kasten(b: float, t: float, dicke: float = 20) -> dict:
    """Ein Raum mit lichten Massen b × t cm, Achsen um die halbe Dicke nach aussen."""
    h = dicke / 2
    ecken = [(-h, -h), (b + h, -h), (b + h, t + h), (-h, t + h)]
    return {
        "projekt": {"name": "Test", "adresse": "Weg 1", "plannummer": "T-1"},
        "geschosse": [{
            "id": "EG", "raumhoehe": 250,
            "waende": [{"id": f"W{i + 1}", "von": list(ecken[i]), "bis": list(ecken[(i + 1) % 4]),
                        "dicke": dicke, "status": "bestand"} for i in range(4)],
            "raeume": [{"name": "Raum", "punkt": [b / 2, t / 2]}],
        }],
    }


# --- Prüfung --------------------------------------------------------------

def test_beispiel_ist_gueltig():
    plan = pruefen(beispiel())
    assert len(plan.geschosse[0].waende) == 10


def test_oeffnung_ausserhalb_der_wand():
    d = beispiel()
    d["geschosse"][0]["oeffnungen"][0]["abstand"] = 1000  # F1 auf W1 (1050 lang), 240 breit
    assert "ragt über das Ende von W1" in maengel(d)


def test_doppelte_id():
    d = beispiel()
    d["geschosse"][0]["waende"][1]["id"] = "W1"
    assert "'W1' kommt doppelt vor" in maengel(d)


def test_ungueltiger_status():
    d = beispiel()
    d["geschosse"][0]["waende"][0]["status"] = "weg"
    assert "status muss eines von bestand, abbruch, neu" in maengel(d)


def test_neue_oeffnung_in_abbruchwand():
    d = beispiel()
    t3 = next(o for o in d["geschosse"][0]["oeffnungen"] if o["id"] == "T3")
    t3["status"] = "neu"
    assert "liegt aber in der Abbruchwand W6" in maengel(d)


def test_ueberlappende_oeffnungen():
    d = beispiel()
    d["geschosse"][0]["oeffnungen"][1]["abstand"] = 300  # F2 in F1 (120..360)
    assert "F1 und F2 überlappen" in maengel(d)


def test_unbekannte_wand():
    d = beispiel()
    d["geschosse"][0]["oeffnungen"][0]["wand"] = "W99"
    assert "'W99' gibt es in EG nicht" in maengel(d)


def test_fenster_braucht_bruestung():
    d = beispiel()
    del d["geschosse"][0]["oeffnungen"][0]["bruestung"]
    assert "bruestung fehlt" in maengel(d)


def test_alle_maengel_auf_einmal():
    d = beispiel()
    d["geschosse"][0]["waende"][0]["status"] = "weg"
    d["geschosse"][0]["waende"][1]["dicke"] = -5
    del d["projekt"]["plannummer"]
    text = maengel(d)
    assert "status" in text and "dicke" in text and "plannummer" in text


def test_platzhalter_nur_im_entwurf():
    d = beispiel()
    d["projekt"]["plannummer"] = "<Plan-Nr.>"
    assert "Platzhalter" in maengel(d)
    modell.pruefen(d, FIRMA, entwurf=True)
    with pytest.raises(Fehlerhaft, match="firma.json"):
        modell.pruefen(beispiel(), {"name": "<Firma>"})


# --- Geometrie ------------------------------------------------------------

def test_flaeche_aus_lichten_massen():
    plan = pruefen(kasten(400, 300))
    (raum,) = geometrie.raeume(plan.geschosse[0], "neu")
    assert raum.name == "Raum"
    assert raum.m2 == pytest.approx(12.00)
    assert raum.lichte_masse == pytest.approx((400, 300))
    assert raum.ist_rechteck


def test_abbruch_legt_raeume_zusammen():
    g = pruefen(beispiel()).geschosse[0]
    vorher = {r.name: r.m2 for r in geometrie.raeume(g, "bestand")}
    nachher = {r.name: r.m2 for r in geometrie.raeume(g, "neu")}
    assert "Wohnen" in vorher and "Küche" in vorher
    assert "Wohnen / Küche" in nachher
    # Die abgebrochene 12-cm-Wand kommt als Fläche dazu: 12 × 427.5 cm
    zusatz = 12 * 427.5 / 10_000
    assert nachher["Wohnen / Küche"] == pytest.approx(vorher["Wohnen"] + vorher["Küche"] + zusatz)


def test_neuer_raum_nur_nachher():
    g = pruefen(beispiel()).geschosse[0]
    assert "Reduit" not in {r.name for r in geometrie.raeume(g, "bestand")}
    assert "Reduit" in {r.name for r in geometrie.raeume(g, "neu")}


def test_beispiel_ohne_warnungen():
    assert geometrie.warnungen(pruefen(beispiel()).geschosse[0]) == []


def test_offene_ecke_gibt_warnung():
    d = kasten(400, 300)
    d["geschosse"][0]["waende"][0]["bis"][0] -= 30  # W1 endet 30 cm vor der Ecke
    hinweise = " ".join(geometrie.warnungen(pruefen(d).geschosse[0]))
    assert "W1 endet bei bis" in hinweise
    assert "in keiner geschlossenen Fläche" in hinweise


def test_durchbruch_ist_abbruch_zumauern_ist_neu():
    g = pruefen(beispiel()).geschosse[0]
    f = geometrie.wandflaechen(g)
    oe = {o.id: o for o in g.oeffnungen}
    durchbruch = geometrie.oeffnung_polygon(oe["F3"]).centroid   # neues Fenster in Bestand
    zumauern = geometrie.oeffnung_polygon(oe["T5"]).centroid     # alte Badtür
    assert f.abbruch.contains(durchbruch) and not f.bestand.contains(durchbruch)
    assert f.neu.contains(zumauern) and not f.bestand.contains(zumauern)
    assert oe["T3"].wirksamer_status == "abbruch"                # Tür in Abbruchwand


@pytest.mark.parametrize("cm, text", [(380, "3.80"), (80, "80"), (327.5, "3.27⁵"),
                                      (1020, "10.20"), (12, "12"), (100, "1.00")])
def test_mass_text(cm, text):
    assert modell.mass_text(cm) == text


# --- Plan (PDF) -----------------------------------------------------------

def _mm_pro_meter(ax) -> float:
    a, b = ax.transData.transform([(0, 0), (100, 0)])
    return (b[0] - a[0]) / ax.figure.dpi * 25.4


def test_massstab_ist_exakt():
    import grundriss
    plan = pruefen(beispiel())
    blatt, fenster = grundriss.grundriss_blatt(plan, plan.geschosse[0], [])
    assert fenster.massstab == 50
    assert _mm_pro_meter(fenster.ax) == pytest.approx(20.0, abs=0.01)   # 1 m = 20 mm bei 1:50
    assert tuple(blatt.fig.get_size_inches() * 25.4) == pytest.approx((420, 297))


def test_schnitt_ist_massstaeblich():
    import ansichten
    plan = pruefen(beispiel())
    blatt, m = ansichten.schnitte_blatt(plan, ansichten.schnitte_bestimmen(plan))
    fenster = blatt.fig.axes[1:]                       # axes[0] ist das Papier
    assert len(fenster) == 2 and m == 50
    for ax in fenster:
        assert _mm_pro_meter(ax) == pytest.approx(20.0, abs=0.01)
        assert ax.get_aspect() in ("auto", 1.0)
        x0, x1 = ax.get_xlim()
        y0, y1 = ax.get_ylim()
        bb = ax.get_position()                         # waagrecht und senkrecht gleicher Massstab
        assert (x1 - x0) / (bb.width * 420) == pytest.approx((y1 - y0) / (bb.height * 297), rel=1e-6)


def test_massstab_wechselt_wenn_zu_gross():
    import grundriss
    d = kasten(2000, 1200)
    g = pruefen(d).geschosse[0]
    assert grundriss.massstab_waehlen(g, 50) == 100


def test_pdf_hat_alle_blaetter(tmp_path):
    import pdf
    from pypdf import PdfReader
    plan = pruefen(beispiel())
    ziel = tmp_path / "plan.pdf"
    erzeugt = pdf.pdf_erzeugen(plan, ziel)
    assert [e.kurz for e in erzeugt] == ["EG", "schnitte", "ansichten", "3d_EG_225", "3d_EG_45"]
    seiten = PdfReader(ziel).pages
    assert len(seiten) == 5
    for seite in seiten:
        breite_mm = float(seite.mediabox.width) / 72 * 25.4
        hoehe_mm = float(seite.mediabox.height) / 72 * 25.4
        assert (breite_mm, hoehe_mm) == pytest.approx((420, 297), abs=0.5)
    text = " ".join(s.extract_text() for s in seiten)
    for erwartet in ("Grundriss Erdgeschoss", "Schnitt A–A", "Schnitt B–B", "Ansicht Süd",
                     "Ansicht Nord", "Vorher (Bestand)", "Nachher (Umbau)", "Blick von Südwest"):
        assert erwartet in text, erwartet


def test_nur_gewaehlte_blaetter(tmp_path):
    import pdf
    d = beispiel()
    d["blaetter"] = ["grundriss", "3d"]
    erzeugt = pdf.pdf_erzeugen(pruefen(d), tmp_path / "plan.pdf")
    assert [e.kurz for e in erzeugt] == ["EG", "3d_EG_225", "3d_EG_45"]
    d["blaetter"] = ["grundriss", "plaene"]
    assert "blaetter muss eine Liste" in maengel(d)


# --- Schnitte und Ansichten -----------------------------------------------

def test_schnitte_automatisch_nicht_in_einer_wand():
    import ansichten
    plan = pruefen(beispiel())
    schnitte = ansichten.schnitte_bestimmen(plan)
    assert [(s.name, s.achse) for s in schnitte] == [("A", "x"), ("B", "y")]
    for s in schnitte:
        e = ansichten.Ebene(s.achse, s.lage, s.blick)
        for w in plan.geschosse[0].waende:
            if ansichten.parallel(w, e):
                assert geometrie.wand_polygon(w).distance(e.linie()) >= 10, (s.name, w.id)


def test_schnitte_aus_plan_json():
    import ansichten
    d = beispiel()
    d["schnitte"] = [{"name": "C", "achse": "y", "lage": 440, "blick": "minus"}]
    plan = pruefen(d)
    assert [(s.name, s.lage, s.blick) for s in ansichten.schnitte_bestimmen(plan)] == [("C", 440, "minus")]
    d["schnitte"] = [{"name": "C", "achse": "z", "lage": 1}]
    assert "schnitte[0].achse" in maengel(d)


def test_schnitt_zeigt_umbau_farben():
    """Durchbruch (F3) und Abbruchwand (W6) gelb, zugemauerte Tür (T5) rot, wie im Grundriss."""
    import ansichten
    from shapely.geometry import Point
    plan = pruefen(beispiel())
    f, decken, glas = ansichten.schnittflaechen(plan, ansichten.Ebene("x", 200, "plus"))
    assert f.abbruch.contains(Point(1050, 150))   # neues Fenster F3 in W2: Wand kommt weg
    assert f.abbruch.contains(Point(600, 100))    # Abbruchwand W6
    assert f.bestand.contains(Point(1050, 40))    # Brüstung unter F3 bleibt
    assert len(decken) == 2                        # Boden und Decke
    f, _, _ = ansichten.schnittflaechen(plan, ansichten.Ebene("y", 440, "plus"))
    assert f.neu.contains(Point(-450, 100))       # T5 in W5 wird zugemauert (u = −y)


def test_oeffnung_text():
    import grundriss
    oeffnungen = {o.id: o for o in pruefen(beispiel()).geschosse[0].oeffnungen}
    assert grundriss.oeffnung_text(oeffnungen["F2"]) == "F2  1.20 × 1.40, BRH 90"
    assert grundriss.oeffnung_text(oeffnungen["F2"], zweizeilig=True) == "F2  1.20 × 1.40\nBRH 90"
    assert grundriss.oeffnung_text(oeffnungen["T1"]) == "T1  1.00 × 2.10"


def _bad(b: float, t: float) -> dict:
    d = kasten(b, t, dicke=15)
    d["geschosse"][0]["oeffnungen"] = [
        {"id": "F1", "wand": "W3", "typ": "fenster", "abstand": (b - 55) / 2, "breite": 70, "hoehe": 90,
         "bruestung": 110, "status": "bestand"},
        {"id": "T1", "wand": "W1", "typ": "tuer", "abstand": b - 70, "breite": 70, "hoehe": 200,
         "status": "neu", "anschlag": "ende", "seite": "links"}]
    d["geschosse"][0]["objekte"] = [
        {"typ": "wc", "position": [35, t - 30], "breite": 40, "tiefe": 60, "rotation": 180,
         "status": "bestand"}]
    return d


def test_oeffnungen_im_grundriss_beschriftet():
    """Kleines Bad (2.10 × 2.60): jede Öffnung trägt ihre Masse, innen und ohne Wand oder WC zu
    überdecken, in der Statusfarbe."""
    import grundriss
    from blatt import SYMBOL
    plan = pruefen(_bad(210, 260))
    g = plan.geschosse[0]
    _, fenster = grundriss.grundriss_blatt(plan, g, [])
    texte = {t.get_text(): t for t in fenster.ax.texts}
    assert "T1  70 × 2.00" in texte
    assert texte.keys() & {"F1  70 × 90, BRH 1.10", "F1  70 × 90\nBRH 1.10"}
    innen = geometrie.aussenumriss(g)
    hindernisse = [geometrie.wand_polygon(w) for w in g.waende] + [geometrie.objekt_polygon(b) for b in g.objekte]
    for text, t in texte.items():
        if text.startswith(("F1", "T1")):
            flaeche = grundriss._textbox(fenster.ax, t)
            assert flaeche.within(innen)
            assert not any(flaeche.intersects(h) for h in hindernisse), text
    assert texte["T1  70 × 2.00"].get_color() == SYMBOL["neu"]


def test_oeffnung_ohne_platz_kommt_in_die_liste():
    import grundriss
    plan = pruefen(_bad(90, 80))
    g = plan.geschosse[0]
    g.objekte = []
    blatt, fenster = grundriss.grundriss_blatt(plan, g, [])
    assert "F1" in [t.get_text() for t in fenster.ax.texts]
    assert "F1  70 × 90, BRH 1.10" in [t.get_text() for t in blatt.papier.texts]


def test_schnitt_bemasst_geschnittene_oeffnungen():
    """B–B durch F1 (Fenster) und T1 (Tür): senkrechte Ketten Brüstung, Fensterhöhe, Türhöhe."""
    import ansichten
    from blatt import Blatt
    plan = pruefen(_bad(210, 260))
    e = ansichten.Ebene("y", 136, "plus")
    fenster = Blatt().fenster(0, 0, (-400, 100), (-50, 300), 50)
    ansichten.oeffnungen_bemassen(fenster, plan, e)
    assert sorted(t.get_text() for t in fenster.ax.texts) == ["1.10", "2.00", "90"]


@pytest.mark.parametrize("nordwinkel, erste", [(0, "Ansicht Süd"), (90, "Ansicht Ost"),
                                               (None, "Ansicht Planseite unten")])
def test_ansicht_himmelsrichtung(nordwinkel, erste):
    import ansichten
    d = beispiel()
    d["projekt"]["nordwinkel"] = nordwinkel
    namen = [n for n, _ in ansichten.fassaden(pruefen(d))]
    assert namen[0] == erste and len(namen) == 4


# --- 3D -------------------------------------------------------------------

def test_3d_hinten_vor_vorne():
    import axonometrie
    from shapely.geometry import box
    kamera = axonometrie.Kamera(225)                   # von Südwest: Nordost liegt hinten
    vorne = axonometrie.Koerper(box(0, 0, 100, 100), 0, 250)
    hinten = axonometrie.Koerper(box(500, 500, 600, 600), 0, 250)
    neben = axonometrie.Koerper(box(110, 0, 210, 100), 0, 250)   # östlich von «vorne»: weiter hinten
    reihenfolge = axonometrie.sortieren([vorne, neben, hinten], kamera)
    assert reihenfolge.index(hinten) < reihenfolge.index(neben) < reihenfolge.index(vorne)


def test_3d_vorher_gelb_nachher_rot():
    import axonometrie
    g = pruefen(beispiel()).geschosse[0]

    def farben(zustand):
        _, koerper, namen = axonometrie.szene(g, zustand)
        return {f.farbe for k in koerper for f in k.flaechen}, {n for n, _ in namen}

    vorher, raeume_vorher = farben("bestand")
    nachher, raeume_nachher = farben("neu")
    assert axonometrie.FARBE["abbruch"] in vorher and axonometrie.FARBE["neu"] not in vorher
    assert axonometrie.FARBE["neu"] in nachher and axonometrie.FARBE["abbruch"] not in nachher
    assert "Küche" in raeume_vorher and "Wohnen / Küche" in raeume_nachher


def test_3d_wandstuecke_ueberschneiden_sich_nicht():
    import axonometrie
    g = pruefen(beispiel()).geschosse[0]
    for zustand in ("bestand", "neu"):
        _, koerper, _ = axonometrie.szene(g, zustand)
        for a, b in itertools.combinations(koerper, 2):
            z_ueber = min(a.z1, b.z1) - max(a.z0, b.z0)
            if z_ueber > 0.01:
                assert a.grund.intersection(b.grund).area < 0.01


# --- Fotos ----------------------------------------------------------------

def test_fotodokumentation(tmp_path):
    import pdf
    from PIL import Image
    from pypdf import PdfReader
    Image.new("RGB", (400, 300), "#8899AA").save(tmp_path / "kueche.jpg")
    d = beispiel()
    d["fotos"] = [{"datei": "kueche.jpg", "titel": "Küche heute"}]
    d["blaetter"] = ["fotos"]
    plan = modell.pruefen(d, FIRMA, basis=tmp_path)
    erzeugt = pdf.pdf_erzeugen(plan, tmp_path / "plan.pdf")
    assert [e.kurz for e in erzeugt] == ["fotos1"]
    text = PdfReader(tmp_path / "plan.pdf").pages[0].extract_text()
    assert "Fotodokumentation" in text and "Küche heute" in text


def test_foto_fehlt_oder_heic(tmp_path):
    d = beispiel()
    d["fotos"] = [{"datei": "gibtsnicht.jpg"}, {"datei": "handy.heic"}]
    with pytest.raises(Fehlerhaft) as e:
        modell.pruefen(d, FIRMA, basis=tmp_path)
    text = "\n".join(e.value.maengel)
    assert "gibtsnicht.jpg gibt es nicht" in text and "HEIC" in text


# --- IFC ------------------------------------------------------------------

@pytest.fixture(scope="module")
def ifc(tmp_path_factory):
    ifcopenshell = pytest.importorskip("ifcopenshell")
    import ifc_export
    ziel = tmp_path_factory.mktemp("ifc") / "plan.ifc"
    ifc_export.ifc_erzeugen(pruefen(beispiel()), ziel)
    return ifcopenshell.open(str(ziel))


def test_ifc_enthaelt_alle_bauteile(ifc):
    zahl = {k: len(ifc.by_type(k)) for k in ("IfcWall", "IfcDoor", "IfcWindow",
                                              "IfcOpeningElement", "IfcSpace", "IfcSlab")}
    # 10 Wände + 1 Zumauerung (T5), 7 Türen, 5 Fenster, 12 Öffnungen, 5 Räume nachher
    assert zahl == {"IfcWall": 11, "IfcDoor": 7, "IfcWindow": 5, "IfcOpeningElement": 12,
                    "IfcSpace": 5, "IfcSlab": 1}


def test_ifc_umbaustatus(ifc):
    from ifcopenshell.util.element import get_pset
    wand = {w.Name: get_pset(w, "Pset_WallCommon", "Status") for w in ifc.by_type("IfcWall")}
    tuer = {t.Name: get_pset(t, "Pset_DoorCommon", "Status") for t in ifc.by_type("IfcDoor")}
    assert wand["W1"] == "EXISTING" and wand["W6"] == "DEMOLISH" and wand["W9"] == "NEW"
    assert wand["T5-Zumauerung"] == "NEW"
    assert tuer["T3"] == "DEMOLISH"   # erfasst als Bestand, liegt aber in der Abbruchwand
    assert tuer["T6"] == "NEW" and tuer["T1"] == "EXISTING"


def test_ifc_raumflaechen(ifc):
    from ifcopenshell.util.element import get_pset
    flaechen = {r.Name: get_pset(r, "Qto_SpaceBaseQuantities", "NetFloorArea") for r in ifc.by_type("IfcSpace")}
    g = pruefen(beispiel()).geschosse[0]
    for r in geometrie.raeume(g, "neu"):
        assert flaechen[r.name] == pytest.approx(r.m2, abs=0.01)


def test_ifc_waende_decken_plan_ohne_ueberschneidung(ifc):
    """Jede IFC-Wand ist ein eigener Körper: zusammen genau die Wandfläche des Plans,
    keine Lücke an den Ecken, keine doppelte Fläche an Stössen."""
    import ifcopenshell.geom
    import numpy as np
    from shapely.geometry import box
    from shapely.ops import unary_union
    s = ifcopenshell.geom.settings()
    s.set(s.USE_WORLD_COORDS, True)
    s.set(s.DISABLE_OPENING_SUBTRACTIONS, True)
    flaechen = {}
    for w in ifc.by_type("IfcWall"):
        if w.Name.endswith("Zumauerung"):
            continue
        v = np.array(ifcopenshell.geom.create_shape(s, w).geometry.verts).reshape(-1, 3) * 100
        flaechen[w.Name] = box(*v[:, 0:2].min(0), *v[:, 0:2].max(0))
    for a, b in itertools.combinations(flaechen, 2):
        assert flaechen[a].intersection(flaechen[b]).area < 0.01, f"{a} und {b} überschneiden sich"
    g = pruefen(beispiel()).geschosse[0]
    soll = unary_union([geometrie.wand_polygon(w) for w in g.waende])
    assert soll.symmetric_difference(unary_union(list(flaechen.values()))).area < 0.01


def test_ifc_einheit_meter(ifc):
    import ifcopenshell.util.unit
    assert ifcopenshell.util.unit.calculate_unit_scale(ifc) == 1.0


def test_beispiel_bleibt_unveraendert():
    d = beispiel()
    vorher = copy.deepcopy(d)
    pruefen(d)
    assert d == vorher

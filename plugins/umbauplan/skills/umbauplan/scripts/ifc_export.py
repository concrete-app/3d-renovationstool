"""Schreibt das Modell als IFC4-Datei (ifcopenshell).

Die IFC-Datei hat Meter als Einheit, das Modell rechnet in Zentimetern: alles
geht durch m(). Der Umbaustatus steht, wie es IFC vorsieht, in
Pset_WallCommon/DoorCommon/WindowCommon.Status (EXISTING, DEMOLISH, NEW).
Archicad, Revit, Vectorworks und BIM-Viewer lesen ihn von dort.
"""

from __future__ import annotations

import math
from pathlib import Path

import ifcopenshell
import ifcopenshell.api.aggregate
import ifcopenshell.api.context
import ifcopenshell.api.feature
import ifcopenshell.api.geometry
import ifcopenshell.api.project
import ifcopenshell.api.pset
import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.api.unit
import numpy as np

import geometrie
from modell import Geschoss, Objekt, Oeffnung, Plan, Wand

IFC_STATUS = {"bestand": "EXISTING", "abbruch": "DEMOLISH", "neu": "NEW"}
STATUS_TEXT = {"bestand": "Bestand", "abbruch": "Abbruch", "neu": "Neu"}
SANITAER = {"wc": "TOILETPAN", "lavabo": "WASHHANDBASIN", "dusche": "SHOWER", "badewanne": "BATH"}


def m(cm: float) -> float:
    return cm / 100.0


def _matrix(ursprung: tuple[float, float], richtung: tuple[float, float], z: float) -> np.ndarray:
    """Platzierung in Metern: x-Achse entlang `richtung`, y-Achse nach links."""
    ux, uy = richtung
    return np.array([[ux, -uy, 0, m(ursprung[0])],
                     [uy, ux, 0, m(ursprung[1])],
                     [0, 0, 1, m(z)],
                     [0, 0, 0, 1]], dtype=float)


class _Ifc:
    def __init__(self, plan: Plan):
        api = ifcopenshell.api
        self.f = api.project.create_file(version="IFC4")
        f = self.f
        projekt = api.root.create_entity(f, ifc_class="IfcProject", name=plan.projekt.name)
        projekt.Description = f"Plan-Nr. {plan.projekt.plannummer}"
        laenge = api.unit.add_si_unit(f, unit_type="LENGTHUNIT")
        flaeche = api.unit.add_si_unit(f, unit_type="AREAUNIT")
        volumen = api.unit.add_si_unit(f, unit_type="VOLUMEUNIT")
        api.unit.assign_unit(f, units=[laenge, flaeche, volumen])
        modell = api.context.add_context(f, context_type="Model")
        self.body = api.context.add_context(f, context_type="Model", context_identifier="Body",
                                            target_view="MODEL_VIEW", parent=modell)
        self.site = api.root.create_entity(f, ifc_class="IfcSite", name="Grundstück")
        self.gebaeude = api.root.create_entity(f, ifc_class="IfcBuilding", name=plan.projekt.adresse)
        api.aggregate.assign_object(f, products=[self.site], relating_object=projekt)
        api.aggregate.assign_object(f, products=[self.gebaeude], relating_object=self.site)
        for e in (self.site, self.gebaeude):
            api.geometry.edit_object_placement(f, product=e)

    def element(self, klasse: str, name: str, darstellung, matrix, ort, status: str | None,
                pset: str | None = None, predefined: str | None = None):
        api = ifcopenshell.api
        e = api.root.create_entity(self.f, ifc_class=klasse, name=name, predefined_type=predefined)
        api.geometry.edit_object_placement(self.f, product=e, matrix=matrix)
        api.geometry.assign_representation(self.f, product=e, representation=darstellung)
        if ort is not None:
            api.spatial.assign_container(self.f, products=[e], relating_structure=ort)
        if status:
            if pset:
                ps = api.pset.add_pset(self.f, product=e, name=pset)
                api.pset.edit_pset(self.f, pset=ps, properties={"Status": IFC_STATUS[status]})
            ps = api.pset.add_pset(self.f, product=e, name="Umbauplan")
            api.pset.edit_pset(self.f, pset=ps, properties={"Status": STATUS_TEXT[status], "ID": name})
        return e

    def quader(self, laenge: float, hoehe: float, dicke: float):
        """Ein Quader, x von 0 bis laenge, mittig zur Achse (y von -dicke/2 bis +dicke/2)."""
        return ifcopenshell.api.geometry.add_wall_representation(
            self.f, context=self.body, length=m(laenge), height=m(hoehe), thickness=m(dicke),
            offset=-m(dicke) / 2)

    # --- Bauteile ---------------------------------------------------------

    def geschoss(self, g: Geschoss) -> None:
        api = ifcopenshell.api
        ort = api.root.create_entity(self.f, ifc_class="IfcBuildingStorey", name=g.name)
        ort.Elevation = m(g.kote)
        api.aggregate.assign_object(self.f, products=[ort], relating_object=self.gebaeude)
        api.geometry.edit_object_placement(self.f, product=ort, matrix=_matrix((0, 0), (1, 0), g.kote))

        ifc_waende = {w.id: self.wand(w, g, ort) for w in g.waende}
        for o in g.oeffnungen:
            self.oeffnung(o, ifc_waende[o.wand.id], g, ort)
        self.boden(g, ort)
        for r in geometrie.raeume(g, "neu"):
            self.raum(r, g, ort)
        for b in g.objekte:
            self.objekt(b, g, ort)

    def wand(self, w: Wand, g: Geschoss, ort):
        vorne, hinten = geometrie.wandenden(w, g)
        start = w.punkt(-vorne)
        return self.element("IfcWall", w.id, self.quader(w.laenge + vorne + hinten, w.hoehe, w.dicke),
                            _matrix(start, w.richtung, g.kote), ort, w.status, "Pset_WallCommon")

    def oeffnung(self, o: Oeffnung, wand, g: Geschoss, ort) -> None:
        api = ifcopenshell.api
        w = o.wand
        z = g.kote + o.bruestung
        start = w.punkt(o.abstand)
        loch = self.element("IfcOpeningElement", f"{o.id}-Öffnung",
                            self.quader(o.breite, o.hoehe, w.dicke + 4),
                            _matrix(start, w.richtung, z), None, None)
        api.feature.add_feature(self.f, feature=loch, element=wand)

        if o.typ in ("tuer", "fenster"):
            # Lokale y-Achse zeigt auf die Seite, auf die die Tür aufgeht.
            links = o.seite == "links"
            ursprung = start if links else w.punkt(o.abstand + o.breite)
            richtung = w.richtung if links else (-w.richtung[0], -w.richtung[1])
            band_am_ursprung = (o.anschlag == "anfang") == links
            if o.typ == "tuer":
                darstellung = api.geometry.add_door_representation(
                    self.f, context=self.body, overall_height=m(o.hoehe), overall_width=m(o.breite),
                    operation_type="SINGLE_SWING_LEFT" if band_am_ursprung else "SINGLE_SWING_RIGHT")
                klasse, pset = "IfcDoor", "Pset_DoorCommon"
            else:
                darstellung = api.geometry.add_window_representation(
                    self.f, context=self.body, overall_height=m(o.hoehe), overall_width=m(o.breite))
                klasse, pset = "IfcWindow", "Pset_WindowCommon"
            q = -w.dicke / 4 if links else w.dicke / 4
            versetzt = (ursprung[0] + w.normale[0] * q, ursprung[1] + w.normale[1] * q)
            fuellung = self.element(klasse, o.id, darstellung, _matrix(versetzt, richtung, z), ort,
                                    o.wirksamer_status, pset)
            fuellung.OverallWidth = m(o.breite)
            fuellung.OverallHeight = m(o.hoehe)
            api.feature.add_filling(self.f, opening=loch, element=fuellung)

        if o.wird_zugemauert:
            # Die Füllung ist eine neue Wand.
            self.element("IfcWall", f"{o.id}-Zumauerung", self.quader(o.breite, o.hoehe, w.dicke),
                         _matrix(start, w.richtung, z), ort, "neu", "Pset_WallCommon")

    def boden(self, g: Geschoss, ort) -> None:
        umriss = geometrie.aussenumriss(g)
        polys = list(getattr(umriss, "geoms", [umriss]))
        for i, p in enumerate(polys):
            punkte = [(m(x), m(y)) for x, y in list(p.exterior.coords)[:-1]]
            darstellung = ifcopenshell.api.geometry.add_slab_representation(
                self.f, context=self.body, depth=m(g.deckenstaerke), polyline=punkte)
            self.element("IfcSlab", f"{g.id}-Boden{'' if i == 0 else i + 1}", darstellung,
                         _matrix((0, 0), (1, 0), g.kote - g.deckenstaerke), ort, "bestand",
                         "Pset_SlabCommon", predefined="FLOOR")

    def raum(self, r, g: Geschoss, ort) -> None:
        api = ifcopenshell.api
        punkte = [(m(x), m(y)) for x, y in list(r.flaeche.exterior.coords)[:-1]]
        darstellung = api.geometry.add_slab_representation(
            self.f, context=self.body, depth=m(g.raumhoehe), polyline=punkte)
        raum = api.root.create_entity(self.f, ifc_class="IfcSpace", name=r.name or "Raum")
        raum.LongName = r.name or None
        api.geometry.edit_object_placement(self.f, product=raum, matrix=_matrix((0, 0), (1, 0), g.kote))
        api.geometry.assign_representation(self.f, product=raum, representation=darstellung)
        api.aggregate.assign_object(self.f, products=[raum], relating_object=ort)
        qto = api.pset.add_qto(self.f, product=raum, name="Qto_SpaceBaseQuantities")
        api.pset.edit_qto(self.f, qto=qto, properties={"NetFloorArea": round(r.m2, 2),
                                                       "Height": m(g.raumhoehe)})

    def objekt(self, b: Objekt, g: Geschoss, ort) -> None:
        a = math.radians(b.rotation)
        richtung = (math.cos(a), math.sin(a))
        ursprung = (b.position[0] - richtung[0] * b.breite / 2, b.position[1] - richtung[1] * b.breite / 2)
        klasse = "IfcSanitaryTerminal" if b.typ in SANITAER else "IfcFurniture"
        self.element(klasse, b.bezeichnung or b.id, self.quader(b.breite, b.hoehe, b.tiefe),
                     _matrix(ursprung, richtung, g.kote), ort, b.status,
                     predefined=SANITAER.get(b.typ))


def ifc_erzeugen(plan: Plan, ziel: Path) -> None:
    ifc = _Ifc(plan)
    for g in plan.geschosse:
        ifc.geschoss(g)
    ifc.f.write(str(ziel))

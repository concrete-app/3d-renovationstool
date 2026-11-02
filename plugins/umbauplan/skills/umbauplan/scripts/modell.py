"""Das Datenmodell eines Umbauplans: plan.json lesen und prüfen.

Claude schreibt plan.json, dieses Modul prüft es. Alles, was später gezeichnet,
gerechnet oder exportiert wird, liest die Dataclasses von hier, nie das rohe JSON.

Einheit ist überall Zentimeter. x zeigt nach rechts, y nach oben (wie auf dem
Plan, Norden oben, wenn nichts anderes angegeben ist).
"""

from __future__ import annotations

import datetime as dt
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

STATUS = ("bestand", "abbruch", "neu")
OEFFNUNGSTYPEN = ("tuer", "fenster", "durchgang")
OBJEKTTYPEN = ("kueche", "wc", "lavabo", "dusche", "badewanne", "schrank",
               "waschturm", "bett", "tisch", "sofa", "andere")
ZUSTAENDE = ("beide", "bestand", "neu")
MASSSTAEBE = (20, 50, 100, 200)
BLAETTER = ("grundriss", "schnitte", "ansichten", "3d", "visualisierung", "fotos")
FOTOFORMATE = (".jpg", ".jpeg", ".png")

PLATZHALTER = re.compile(r"<[^<>]*>|\[[^\[\]]*…[^\[\]]*\]")
SKILL = Path(__file__).resolve().parent.parent


class Fehlerhaft(Exception):
    """Die Eingabe hat Mängel. `maengel` nennt jeden mit seinem Feld."""

    def __init__(self, maengel: list[str]):
        super().__init__("\n".join(maengel))
        self.maengel = maengel


# --- Dataclasses ----------------------------------------------------------

@dataclass
class Wand:
    id: str
    von: tuple[float, float]
    bis: tuple[float, float]
    dicke: float
    status: str
    hoehe: float  # aus geschoss.raumhoehe, wenn nicht angegeben

    @property
    def laenge(self) -> float:
        return math.dist(self.von, self.bis)

    @property
    def richtung(self) -> tuple[float, float]:
        """Einheitsvektor von `von` nach `bis`."""
        l = self.laenge
        return ((self.bis[0] - self.von[0]) / l, (self.bis[1] - self.von[1]) / l)

    @property
    def normale(self) -> tuple[float, float]:
        """Einheitsvektor nach links, in Blickrichtung von `von` nach `bis`."""
        ux, uy = self.richtung
        return (-uy, ux)

    def punkt(self, s: float, q: float = 0.0) -> tuple[float, float]:
        """Punkt bei Abstand s auf der Achse, q quer dazu (positiv = links)."""
        ux, uy = self.richtung
        nx, ny = self.normale
        return (self.von[0] + ux * s + nx * q, self.von[1] + uy * s + ny * q)


@dataclass
class Oeffnung:
    id: str
    wand: Wand
    typ: str
    abstand: float
    breite: float
    hoehe: float
    bruestung: float
    status: str
    anschlag: str  # anfang | ende   (Seite der Bänder, nur Tür)
    seite: str     # links | rechts  (wohin die Tür aufgeht, nur Tür)

    @property
    def wird_zugemauert(self) -> bool:
        """Eine bestehende Öffnung in einer bleibenden Wand verschwindet: die Füllung ist neu."""
        return self.status == "abbruch" and self.wand.status == "bestand"

    @property
    def wirksamer_status(self) -> str:
        """Eine Tür in einer Abbruchwand fällt mit der Wand weg, auch wenn sie als Bestand erfasst ist."""
        return "abbruch" if self.wand.status == "abbruch" else self.status


@dataclass
class Raum:
    name: str
    punkt: tuple[float, float]
    zustand: str


@dataclass
class Objekt:
    id: str
    typ: str
    position: tuple[float, float]
    breite: float
    tiefe: float
    rotation: float
    status: str
    hoehe: float
    bezeichnung: str


@dataclass
class Geschoss:
    id: str
    name: str
    kote: float
    raumhoehe: float
    deckenstaerke: float
    waende: list[Wand] = field(default_factory=list)
    oeffnungen: list[Oeffnung] = field(default_factory=list)
    raeume: list[Raum] = field(default_factory=list)
    objekte: list[Objekt] = field(default_factory=list)


@dataclass
class Projekt:
    name: str
    adresse: str
    bauherr: str
    plannummer: str
    datum: dt.date
    gezeichnet: str
    massstab: int
    index: str
    nordwinkel: float | None


@dataclass
class Schnitt:
    """Schnittlinie im Grundriss. achse "x": waagrechte Linie bei y = lage;
    achse "y": senkrechte Linie bei x = lage. blick "plus": Blick in +y bzw. +x
    (bei Norden oben: nach Norden bzw. Osten), "minus": entgegengesetzt."""
    name: str
    achse: str
    lage: float
    blick: str


@dataclass
class Foto:
    datei: Path
    titel: str


@dataclass
class Visualisierung:
    """Foto vom Bestand und das Bild, das ChatGPT/Codex daraus in derselben Perspektive gemacht hat."""
    vorher: Path
    nachher: Path
    titel: str
    wuensche: str


@dataclass
class Plan:
    projekt: Projekt
    geschosse: list[Geschoss]
    firma: dict
    angenommen: list[str]
    schnitte: list[Schnitt] = field(default_factory=list)  # leer: das Skript legt A–A und B–B selbst
    fotos: list[Foto] = field(default_factory=list)
    visualisierungen: list[Visualisierung] = field(default_factory=list)
    blaetter: tuple[str, ...] = BLAETTER


OBJEKTHOEHEN = {"kueche": 90, "wc": 40, "lavabo": 85, "dusche": 5, "badewanne": 60,
                "schrank": 220, "waschturm": 180, "bett": 45, "tisch": 75, "sofa": 80,
                "andere": 100}


def mass_text(cm: float) -> str:
    """Schweizer Schreibweise: 3.80 (m), unter einem Meter in cm (80), halbe cm hochgestellt (3.27⁵)."""
    halbe = round(abs(cm) * 2)
    ganz, halb = divmod(halbe, 2)
    text = f"{ganz // 100}.{ganz % 100:02d}" if ganz >= 100 else f"{ganz}"
    return text + ("⁵" if halb else "")


# --- Prüfen ---------------------------------------------------------------

class _Pruefer:
    def __init__(self):
        self.maengel: list[str] = []

    def text(self, d: dict, key: str, pfad: str, pflicht: bool = True, standard: str = "") -> str:
        wert = d.get(key)
        if wert is None or (isinstance(wert, str) and not wert.strip()):
            if pflicht:
                self.maengel.append(f"{pfad}.{key} fehlt")
            return standard
        if not isinstance(wert, (str, int, float)) or isinstance(wert, bool):
            self.maengel.append(f"{pfad}.{key} muss Text sein, ist {wert!r}")
            return standard
        return str(wert).strip()

    def zahl(self, d: dict, key: str, pfad: str, standard: float | None = None,
             minimum: float | None = 0, positiv: bool = True) -> float:
        wert = d.get(key, standard)
        if wert is None:
            self.maengel.append(f"{pfad}.{key} fehlt")
            return 0.0
        if isinstance(wert, bool) or not isinstance(wert, (int, float)) or not math.isfinite(wert):
            self.maengel.append(f"{pfad}.{key} muss eine Zahl sein (cm), ist {wert!r}")
            return 0.0
        if positiv and wert <= 0:
            self.maengel.append(f"{pfad}.{key} muss grösser als 0 sein, ist {wert}")
        elif minimum is not None and wert < minimum:
            self.maengel.append(f"{pfad}.{key} darf nicht kleiner als {minimum} sein, ist {wert}")
        return float(wert)

    def punkt(self, d: dict, key: str, pfad: str) -> tuple[float, float]:
        wert = d.get(key)
        if (not isinstance(wert, (list, tuple)) or len(wert) != 2
                or not all(isinstance(v, (int, float)) and not isinstance(v, bool)
                           and math.isfinite(v) for v in wert)):
            self.maengel.append(f"{pfad}.{key} muss [x, y] in cm sein, ist {wert!r}")
            return (0.0, 0.0)
        return (float(wert[0]), float(wert[1]))

    def auswahl(self, d: dict, key: str, pfad: str, werte: tuple, standard: str | None = None) -> str:
        wert = d.get(key, standard)
        if wert not in werte:
            self.maengel.append(f"{pfad}.{key} muss eines von {', '.join(werte)} sein, ist {wert!r}")
            return werte[0]
        return wert

    def liste(self, d: dict, key: str, pfad: str, pflicht: bool = False) -> list:
        wert = d.get(key, None)
        if wert is None:
            if pflicht:
                self.maengel.append(f"{pfad}.{key} fehlt")
            return []
        if not isinstance(wert, list):
            self.maengel.append(f"{pfad}.{key} muss eine Liste sein")
            return []
        return wert


def _datum(wert, pr: _Pruefer) -> dt.date:
    if wert in (None, ""):
        return dt.date.today()
    try:
        return dt.date.fromisoformat(str(wert))
    except ValueError:
        pr.maengel.append(f"projekt.datum muss JJJJ-MM-TT sein, ist {wert!r}")
        return dt.date.today()


def _platzhalter(wert, pfad: str, gefunden: list[str]) -> None:
    if isinstance(wert, str):
        if PLATZHALTER.search(wert):
            gefunden.append(f"{pfad} enthält einen Platzhalter: {wert!r}")
    elif isinstance(wert, dict):
        for k, v in wert.items():
            _platzhalter(v, f"{pfad}.{k}", gefunden)
    elif isinstance(wert, list):
        for i, v in enumerate(wert):
            _platzhalter(v, f"{pfad}[{i}]", gefunden)


def firma_laden() -> dict:
    return json.loads((SKILL / "firma.json").read_text(encoding="utf-8"))


def laden(pfad: str | Path) -> dict:
    try:
        return json.loads(Path(pfad).read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise Fehlerhaft([f"{pfad} ist kein gültiges JSON: {e}"]) from e


def _bilddatei(pr: _Pruefer, d: dict, key: str, pfad: str, basis: Path | None) -> Path:
    """Pfad eines Fotos, relativ zum Ordner von plan.json. Nur JPG und PNG, muss es geben."""
    datei = Path(pr.text(d, key, pfad))
    if not datei.is_absolute():
        datei = (basis or Path.cwd()) / datei
    if datei.suffix.lower() not in FOTOFORMATE:
        pr.maengel.append(f"{pfad}.{key} {datei.name!r}: nur JPG und PNG. iPhone-Fotos (HEIC) "
                          f"umwandeln: sips -s format jpeg bild.heic --out bild.jpg")
    elif not datei.exists():
        pr.maengel.append(f"{pfad}.{key} {datei} gibt es nicht")
    return datei


def pruefen(daten: dict, firma: dict | None = None, entwurf: bool = False,
            basis: Path | None = None) -> Plan:
    """Prüft plan.json vollständig. Wirft Fehlerhaft mit allen Mängeln auf einmal.

    basis: Ordner, auf den sich die Pfade der Fotos beziehen (der Ordner von plan.json)."""
    if not isinstance(daten, dict):
        raise Fehlerhaft(["Die Eingabe muss ein JSON-Objekt sein"])
    firma = firma_laden() if firma is None else firma
    pr = _Pruefer()

    p = daten.get("projekt") if isinstance(daten.get("projekt"), dict) else {}
    if not p:
        pr.maengel.append("projekt fehlt")
    massstab = p.get("massstab", 50)
    if massstab not in MASSSTAEBE:
        pr.maengel.append(f"projekt.massstab muss eines von {MASSSTAEBE} sein, ist {massstab!r}")
        massstab = 50
    nord = p.get("nordwinkel")
    if nord is not None and (isinstance(nord, bool) or not isinstance(nord, (int, float))):
        pr.maengel.append(f"projekt.nordwinkel muss eine Zahl (Grad) sein, ist {nord!r}")
        nord = None
    projekt = Projekt(
        name=pr.text(p, "name", "projekt"),
        adresse=pr.text(p, "adresse", "projekt"),
        bauherr=pr.text(p, "bauherr", "projekt", pflicht=False),
        plannummer=pr.text(p, "plannummer", "projekt"),
        datum=_datum(p.get("datum"), pr),
        gezeichnet=pr.text(p, "gezeichnet", "projekt", pflicht=False),
        massstab=massstab,
        index=pr.text(p, "index", "projekt", pflicht=False),
        nordwinkel=float(nord) if nord is not None else None,
    )

    geschosse: list[Geschoss] = []
    ids: dict[str, str] = {}
    roh_geschosse = pr.liste(daten, "geschosse", "", pflicht=True)
    if not roh_geschosse and "geschosse" in daten:
        pr.maengel.append("geschosse ist leer")
    for gi, g in enumerate(roh_geschosse):
        gp = f"geschosse[{gi}]"
        if not isinstance(g, dict):
            pr.maengel.append(f"{gp} muss ein Objekt sein")
            continue
        gid = pr.text(g, "id", gp)
        geschoss = Geschoss(
            id=gid,
            name=pr.text(g, "name", gp, pflicht=False, standard=gid),
            kote=pr.zahl(g, "kote", gp, standard=0, minimum=None, positiv=False),
            raumhoehe=pr.zahl(g, "raumhoehe", gp),
            deckenstaerke=pr.zahl(g, "deckenstaerke", gp, standard=20),
        )
        if gid in ids:
            pr.maengel.append(f"{gp}.id {gid!r} kommt doppelt vor (auch {ids[gid]})")
        ids[gid] = gp

        waende: dict[str, Wand] = {}
        for wi, w in enumerate(pr.liste(g, "waende", gp, pflicht=True)):
            wp = f"{gp}.waende[{wi}]"
            if not isinstance(w, dict):
                pr.maengel.append(f"{wp} muss ein Objekt sein")
                continue
            wand = Wand(
                id=pr.text(w, "id", wp),
                von=pr.punkt(w, "von", wp),
                bis=pr.punkt(w, "bis", wp),
                dicke=pr.zahl(w, "dicke", wp),
                status=pr.auswahl(w, "status", wp, STATUS),
                hoehe=pr.zahl(w, "hoehe", wp, standard=geschoss.raumhoehe or 1),
            )
            if wand.laenge < 1:
                pr.maengel.append(f"{wp} ({wand.id}): von und bis sind gleich, die Wand hat keine Länge")
                continue
            if wand.id in ids:
                pr.maengel.append(f"{wp}.id {wand.id!r} kommt doppelt vor (auch {ids[wand.id]})")
            ids[wand.id] = wp
            waende[wand.id] = wand
            geschoss.waende.append(wand)

        for oi, o in enumerate(pr.liste(g, "oeffnungen", gp)):
            op = f"{gp}.oeffnungen[{oi}]"
            if not isinstance(o, dict):
                pr.maengel.append(f"{op} muss ein Objekt sein")
                continue
            oid = pr.text(o, "id", op)
            wid = o.get("wand")
            wand = waende.get(wid)
            if wand is None:
                pr.maengel.append(f"{op}.wand {wid!r} gibt es in {gid} nicht")
                continue
            typ = pr.auswahl(o, "typ", op, OEFFNUNGSTYPEN)
            standard_hoehe = {"tuer": 210, "durchgang": 210, "fenster": None}[typ]
            oeffnung = Oeffnung(
                id=oid, wand=wand, typ=typ,
                abstand=pr.zahl(o, "abstand", op, positiv=False),
                breite=pr.zahl(o, "breite", op),
                hoehe=pr.zahl(o, "hoehe", op, standard=standard_hoehe),
                bruestung=pr.zahl(o, "bruestung", op, standard=0 if typ != "fenster" else None,
                                  positiv=False),
                status=pr.auswahl(o, "status", op, STATUS),
                anschlag=pr.auswahl(o, "anschlag", op, ("anfang", "ende"), standard="anfang"),
                seite=pr.auswahl(o, "seite", op, ("links", "rechts"), standard="links"),
            )
            if oid in ids:
                pr.maengel.append(f"{op}.id {oid!r} kommt doppelt vor (auch {ids[oid]})")
            ids[oid] = op
            ende = oeffnung.abstand + oeffnung.breite
            if ende > wand.laenge + 0.01:
                pr.maengel.append(
                    f"{op} ({oid}) ragt über das Ende von {wand.id} hinaus: "
                    f"abstand {oeffnung.abstand:g} + breite {oeffnung.breite:g} = {ende:g} cm, "
                    f"die Wand ist {wand.laenge:g} cm lang")
            if oeffnung.bruestung + oeffnung.hoehe > wand.hoehe + 0.01:
                pr.maengel.append(
                    f"{op} ({oid}) ist höher als die Wand: brüstung + höhe = "
                    f"{oeffnung.bruestung + oeffnung.hoehe:g} cm, Wand {wand.hoehe:g} cm")
            if wand.status == "abbruch" and oeffnung.status == "neu":
                pr.maengel.append(f"{op} ({oid}) ist neu, liegt aber in der Abbruchwand {wand.id}")
            if wand.status == "neu" and oeffnung.status != "neu":
                pr.maengel.append(
                    f"{op} ({oid}) liegt in der neuen Wand {wand.id} und muss darum auch status 'neu' haben")
            geschoss.oeffnungen.append(oeffnung)

        for wand in geschoss.waende:
            eigene = sorted((o for o in geschoss.oeffnungen if o.wand is wand), key=lambda o: o.abstand)
            for a, b in zip(eigene, eigene[1:]):
                if a.abstand + a.breite > b.abstand + 0.01:
                    pr.maengel.append(f"Öffnungen {a.id} und {b.id} überlappen in Wand {wand.id}")

        for ri, r in enumerate(pr.liste(g, "raeume", gp)):
            rp = f"{gp}.raeume[{ri}]"
            if not isinstance(r, dict):
                pr.maengel.append(f"{rp} muss ein Objekt sein")
                continue
            geschoss.raeume.append(Raum(
                name=pr.text(r, "name", rp),
                punkt=pr.punkt(r, "punkt", rp),
                zustand=pr.auswahl(r, "zustand", rp, ZUSTAENDE, standard="beide"),
            ))

        for bi, b in enumerate(pr.liste(g, "objekte", gp)):
            bp = f"{gp}.objekte[{bi}]"
            if not isinstance(b, dict):
                pr.maengel.append(f"{bp} muss ein Objekt sein")
                continue
            typ = pr.auswahl(b, "typ", bp, OBJEKTTYPEN)
            geschoss.objekte.append(Objekt(
                id=pr.text(b, "id", bp, pflicht=False, standard=f"{gid}-O{bi + 1}"),
                typ=typ,
                position=pr.punkt(b, "position", bp),
                breite=pr.zahl(b, "breite", bp),
                tiefe=pr.zahl(b, "tiefe", bp),
                rotation=pr.zahl(b, "rotation", bp, standard=0, minimum=None, positiv=False),
                status=pr.auswahl(b, "status", bp, STATUS, standard="neu"),
                hoehe=pr.zahl(b, "hoehe", bp, standard=OBJEKTHOEHEN[typ]),
                bezeichnung=pr.text(b, "bezeichnung", bp, pflicht=False),
            ))
        geschosse.append(geschoss)

    angenommen = daten.get("angenommen", [])
    if not isinstance(angenommen, list) or not all(isinstance(a, str) for a in angenommen):
        pr.maengel.append("angenommen muss eine Liste von Texten sein")
        angenommen = []

    schnitte = []
    namen = set()
    for si, sch in enumerate(pr.liste(daten, "schnitte", "")):
        sp = f"schnitte[{si}]"
        if not isinstance(sch, dict):
            pr.maengel.append(f"{sp} muss ein Objekt sein")
            continue
        schnitt = Schnitt(name=pr.text(sch, "name", sp), achse=pr.auswahl(sch, "achse", sp, ("x", "y")),
                          lage=pr.zahl(sch, "lage", sp, minimum=None, positiv=False),
                          blick=pr.auswahl(sch, "blick", sp, ("plus", "minus"), standard="plus"))
        if schnitt.name in namen:
            pr.maengel.append(f"{sp}.name {schnitt.name!r} kommt doppelt vor")
        namen.add(schnitt.name)
        schnitte.append(schnitt)

    fotos = []
    for fi, fo in enumerate(pr.liste(daten, "fotos", "")):
        fp = f"fotos[{fi}]"
        if not isinstance(fo, dict):
            pr.maengel.append(f"{fp} muss ein Objekt sein")
            continue
        fotos.append(Foto(datei=_bilddatei(pr, fo, "datei", fp, basis),
                          titel=pr.text(fo, "titel", fp, pflicht=False)))

    visualisierungen = []
    for vi, vo in enumerate(pr.liste(daten, "visualisierungen", "")):
        vp = f"visualisierungen[{vi}]"
        if not isinstance(vo, dict):
            pr.maengel.append(f"{vp} muss ein Objekt sein")
            continue
        visualisierungen.append(Visualisierung(
            vorher=_bilddatei(pr, vo, "vorher", vp, basis),
            nachher=_bilddatei(pr, vo, "nachher", vp, basis),
            titel=pr.text(vo, "titel", vp, pflicht=False),
            wuensche=pr.text(vo, "wuensche", vp, pflicht=False)))

    blaetter = daten.get("blaetter", list(BLAETTER))
    if not isinstance(blaetter, list) or not blaetter or any(b not in BLAETTER for b in blaetter):
        pr.maengel.append(f"blaetter muss eine Liste aus {', '.join(BLAETTER)} sein, ist {blaetter!r}")
        blaetter = list(BLAETTER)

    if not entwurf:
        _platzhalter(daten.get("projekt"), "projekt", pr.maengel)
        _platzhalter(firma, "firma.json", pr.maengel)

    if pr.maengel:
        raise Fehlerhaft(pr.maengel)
    return Plan(projekt=projekt, geschosse=geschosse, firma=firma, angenommen=angenommen,
                schnitte=schnitte, fotos=fotos,
                visualisierungen=visualisierungen, blaetter=tuple(b for b in BLAETTER if b in blaetter))

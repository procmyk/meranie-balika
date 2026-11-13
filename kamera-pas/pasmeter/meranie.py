"""Kalibrácia prázdneho pásu, detekcia balíkov v snímke a sledovanie balíkov medzi snímkami."""
from dataclasses import dataclass, field
import json
import numpy as np
import cv2

from .geometria import fit_rovina_ransac, baza_roviny, robustny_obdlznik


@dataclass
class Nastavenia:
    krok: int = 2               # podvzorkovanie hĺbkového obrazu (2 = každý 2. pixel)
    min_vyska: float = 0.015    # min. výška nad pásom/pozadím (m)
    min_plocha_px: int = 60     # min. veľkosť objektu (pixely po podvzorkovaní)
    pas_tolerancia: float = 0.03  # max. odchýlka pozadia od roviny pásu pre masku pásu (m)
    horny_pas: float = 0.03     # hrúbka pásma vrchnej steny (m)
    okraj_px: int = 2           # objekt pri okraji obrazu v smere pohybu = neúplný
    brana_m: float = 0.35       # max. posun balíka medzi snímkami (m)
    strata_snimok: int = 6      # po koľkých snímkach bez videnia je balík ukončený
    min_vzoriek: int = 3        # min. počet úplných snímok na zápis balíka


class Kalibracia:
    """Rovina pásu + výška pozadia (lišty, okolie) + maska pásu. Uloží/načíta sa z .npz."""

    def __init__(self, n, d, pozadie, maska, intr, krok):
        self.n, self.d, self.pozadie, self.maska, self.intr, self.krok = n, d, pozadie, maska, intr, krok
        self.u, self.v = baza_roviny(n)
        self._luce = luce(intr, krok)

    @staticmethod
    def z_prazdneho_pasu(snimky, intr, nast: Nastavenia):
        """snimky: zoznam hĺbkových obrázkov prázdneho pásu."""
        k = nast.krok
        stack = np.stack([s[::k, ::k] for s in snimky])
        stack[stack <= 0] = np.nan
        med = np.nanmedian(stack, axis=0)
        lc = luce(intr, k)
        P = lc * med[..., None]
        ok = np.isfinite(med)
        body = P[ok]
        # 1. rovina = najväčšia; ak je ďalšia veľká rovina bližšie ku kamere, je to pás (podlaha haly je nižšie)
        kandidati = []
        zvysok = body
        for _ in range(3):
            if len(zvysok) < 500:
                break
            n, d, inl = fit_rovina_ransac(zvysok)
            if inl.sum() < 0.1 * len(body):
                break
            kandidati.append((n, d, inl.sum()))
            zvysok = zvysok[~inl]
        if not kandidati:
            raise RuntimeError("Nenašiel som rovinu pásu – je kamera nasmerovaná na prázdny pás?")
        n, d, _ = min(kandidati, key=lambda c: c[1])   # najbližšia ku kamere
        h = P @ n + d
        h[~ok] = np.nan
        maska = np.abs(np.nan_to_num(h, nan=1.0)) < nast.pas_tolerancia
        maska = cv2.morphologyEx(maska.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
        maska = maska.astype(bool)
        pozadie = np.nan_to_num(h, nan=0.0).astype(np.float32)
        return Kalibracia(n, d, pozadie, maska, intr, k)

    def uloz(self, cesta):
        i = self.intr
        np.savez_compressed(cesta, n=self.n, d=self.d, pozadie=self.pozadie, maska=self.maska, krok=self.krok,
                            intr=json.dumps(i.__dict__))

    @staticmethod
    def nacitaj(cesta):
        from .kamery import Intrinsika
        z = np.load(cesta)
        return Kalibracia(z["n"], float(z["d"]), z["pozadie"], z["maska"], Intrinsika(**json.loads(str(z["intr"]))), int(z["krok"]))

    def info(self):
        uhol = np.degrees(np.arccos(abs(self.n[2])))
        return f"vzdialenosť kamery od pásu {self.d:.3f} m, sklon {uhol:.1f}°, plocha pásu v zábere {100 * self.maska.mean():.0f} %"


def luce(intr, k):
    u, v = np.meshgrid(np.arange(0, intr.sirka, k), np.arange(0, intr.vyska, k))
    return np.stack([(u - intr.cx) / intr.fx, (v - intr.cy) / intr.fy, np.ones(u.shape)], -1).astype(np.float32)


@dataclass
class Detekcia:
    du: float        # poloha v smere pohybu (m, v rovine pásu)
    dv: float        # priečna poloha (m)
    dlzka: float
    sirka: float
    vyska: float
    uplna: bool      # celý balík v zábere
    body: int


def detekuj(hlbka, kal: Kalibracia, nast: Nastavenia):
    k = kal.krok
    z = hlbka[::k, ::k]
    ok = z > 0
    P = kal._luce * z[..., None]
    h = P @ kal.n + kal.d
    maska = ok & kal.maska & (h > nast.min_vyska) & (h > kal.pozadie + nast.min_vyska)
    maska = cv2.morphologyEx(maska.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n_lab, lab, stats, _ = cv2.connectedComponentsWithStats(maska, connectivity=8)
    vysledky = []
    W = maska.shape[1]
    for i in range(1, n_lab):
        x, y, w, hh, plocha = stats[i]
        if plocha < nast.min_plocha_px:
            continue
        sel = (lab == i) & ok
        hv = h[sel]
        h_top = np.percentile(hv, 95)
        top = hv > h_top - nast.horny_pas
        if top.sum() < nast.min_plocha_px / 2:
            continue
        vyska = float(np.median(hv[top]))
        Pt = P[sel][top]
        # priemet bodov vrchnej steny kolmo na rovinu pásu
        q = np.stack([Pt @ kal.u, Pt @ kal.v], -1)
        d, s, (cu, cv), _ = robustny_obdlznik(q)
        uplna = x > nast.okraj_px and x + w < W - nast.okraj_px
        vysledky.append(Detekcia(cu, cv, d, s, vyska, bool(uplna), int(plocha)))
    return vysledky


@dataclass
class Stopa:
    id: int
    du: float
    dv: float
    vel: float = 0.0
    posledna: int = 0
    merania: list = field(default_factory=list)
    prvy: int = 0
    drah: list = field(default_factory=list)   # (snímka, poloha) – na výpočet rýchlosti


class Sledovanie:
    """Priraďuje detekcie k balíkom medzi snímkami; po odchode balíka vráti výsledné meranie."""

    def __init__(self, nast: Nastavenia, fps: float):
        self.nast, self.fps = nast, fps
        self.stopy, self.snimka, self._id = [], 0, 0

    def krok(self, detekcie):
        self.snimka += 1
        hotove = []
        volne = list(detekcie)
        for st in sorted(self.stopy, key=lambda s: -s.du):
            pred = st.du + st.vel * (self.snimka - st.posledna)
            best, bd = None, self.nast.brana_m
            for dt in volne:
                vzd = np.hypot(dt.du - pred, (dt.dv - st.dv) * 2)
                if vzd < bd:
                    best, bd = dt, vzd
            if best is not None:
                volne.remove(best)
                krokov = self.snimka - st.posledna
                v = (best.du - st.du) / krokov
                st.vel = v if len(st.drah) < 2 else 0.7 * st.vel + 0.3 * v
                st.du, st.dv, st.posledna = best.du, best.dv, self.snimka
                if best.uplna:
                    st.merania.append(best)
                    st.drah.append((self.snimka, best.du))
        for dt in volne:
            self._id += 1
            self.stopy.append(Stopa(self._id, dt.du, dt.dv, posledna=self.snimka, prvy=self.snimka,
                                    merania=[dt] if dt.uplna else [], drah=[(self.snimka, dt.du)] if dt.uplna else []))
        zostavaju = []
        for st in self.stopy:
            if self.snimka - st.posledna > self.nast.strata_snimok:
                r = self._vysledok(st)
                if r:
                    hotove.append(r)
            else:
                zostavaju.append(st)
        self.stopy = zostavaju
        return hotove

    def dokonci(self):
        hotove = [r for r in (self._vysledok(s) for s in self.stopy) if r]
        self.stopy = []
        return hotove

    def _vysledok(self, st):
        m = st.merania
        if len(m) < self.nast.min_vzoriek:
            return None
        med = lambda a: float(np.median([getattr(x, a) for x in m]))
        rozptyl = float(np.percentile([x.dlzka for x in m], 90) - np.percentile([x.dlzka for x in m], 10))
        # rýchlosť = sklon priamky poloha(snímka) cez úplné snímky
        t, x = np.array(st.drah, float).T
        rychlost = abs(np.polyfit(t, x, 1)[0]) * self.fps if np.ptp(t) > 0 else 0.0
        return {"id": st.id, "dlzka": med("dlzka"), "sirka": med("sirka"), "vyska": med("vyska"),
                "snimok": len(m), "rychlost": rychlost, "rozptyl_dlzky": rozptyl}

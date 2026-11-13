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
    smer: int = 1               # smer pásu v obraze: +1 zľava doprava, -1 sprava doľava
    ciara: float = 0.6          # počítacia čiara (podiel záberu v smere pásu, 0..1)
    drzat_s: float = 5.0        # ako dlho čakať na stratený balík v zábere (s)
    pamat_s: float = 120.0      # ako dlho si pamätať započítané balíky (s) – proti dvojitému započítaniu
    podobnost: float = 0.2      # max. relatívny rozdiel rozmerov pre „ten istý balík“


class Kalibracia:
    """Rovina pásu + výška pozadia (lišty, okolie) + maska pásu. Uloží/načíta sa z .npz."""

    def __init__(self, n, d, pozadie, maska, intr, krok, rozsah=None):
        self.n, self.d, self.pozadie, self.maska, self.intr, self.krok = n, d, pozadie, maska, intr, krok
        self.u, self.v = baza_roviny(n)
        self._luce = luce(intr, krok)
        if rozsah is None:   # rozsah záberu pásu v smere pohybu (m) – z roviny pásu a masky
            P = self._luce * (-d / (self._luce @ n))[..., None]
            uu = (P @ self.u)[maska]
            rozsah = (float(uu.min()), float(uu.max())) if uu.size else (-1.0, 1.0)
        self.rozsah = tuple(float(x) for x in rozsah)

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
                            intr=json.dumps(i.__dict__), rozsah=np.array(self.rozsah))

    @staticmethod
    def nacitaj(cesta):
        from .kamery import Intrinsika
        z = np.load(cesta)
        return Kalibracia(z["n"], float(z["d"]), z["pozadie"], z["maska"], Intrinsika(**json.loads(str(z["intr"]))),
                          int(z["krok"]), tuple(z["rozsah"]) if "rozsah" in z else None)

    def info(self):
        uhol = np.degrees(np.arccos(abs(self.n[2])))
        return (f"vzdialenosť kamery od pásu {self.d:.3f} m, sklon {uhol:.1f}°, plocha pásu v zábere {100 * self.maska.mean():.0f} %,"
                f" záber v smere pásu {self.rozsah[1] - self.rozsah[0]:.2f} m")


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
    return analyzuj(hlbka, kal, nast)[0]


def analyzuj(hlbka, kal: Kalibracia, nast: Nastavenia):
    """Vráti (detekcie, platnost) – platnost = podiel platných hĺbkových pixelov na páse (0..1)."""
    k = kal.krok
    z = hlbka[::k, ::k]
    ok = z > 0
    P = kal._luce * z[..., None]
    h = P @ kal.n + kal.d
    platnost = float(ok[kal.maska].mean()) if kal.maska.any() else 0.0
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
    return vysledky, platnost


@dataclass
class Stopa:
    id: int
    du: float
    dv: float
    vel: float = 0.0
    posledna: int = 0
    merania: list = field(default_factory=list)
    drah: list = field(default_factory=list)   # (snímka, poloha) – na výpočet rýchlosti
    zapocitana: bool = False
    zrodena_du: float = 0.0
    slepe: int = 0          # počet snímok bez videnia, keď kamera nevidela pás (výpadok)

    def rozmery(self):
        if not self.merania:
            return None
        return tuple(float(np.median([getattr(m, a) for m in self.merania])) for a in ("dlzka", "sirka", "vyska"))


class Sledovanie:
    """Sleduje balíky medzi snímkami a každý započíta práve raz.

    Pravidlá proti dvojitému započítaniu:
      1. Balík sa započíta až pri prechode POČÍTACOU ČIAROU v smere pásu, a to iba raz.
         Zastavenie ani cúvnutie pásu nič nezmení, je to stále ten istý sledovaný balík.
      2. Balík, ktorý sa v strede záberu „stratí“ (ruka, výpadok kamery, čierny obal), sa neukončí.
         Čaká sa naň `drzat_s` sekúnd a znova sa spáruje podľa polohy a rozmerov.
      3. Pamäť započítaných balíkov: nový balík, ktorý sa objaví v strede záberu na mieste
         a s rozmermi nedávno započítaného balíka, sa považuje za ten istý a nezapočíta sa znova.
    """

    def __init__(self, nast: Nastavenia, fps: float, kal: "Kalibracia" = None):
        self.nast, self.fps = nast, fps
        self.stopy, self.snimka, self._id = [], 0, 0
        self.pamat = []   # (snímka, du, dv, rozmery) započítaných a už nesledovaných balíkov
        if kal is not None:
            u0, u1 = kal.rozsah
        else:
            u0, u1 = -1.7, 1.7
        self.vstup = u0 if nast.smer > 0 else u1
        self.ciara_du = self.vstup + nast.smer * nast.ciara * (u1 - u0)
        self.drzat = int(nast.drzat_s * fps)
        self.pamat_snimok = int(nast.pamat_s * fps)

    def _za_ciarou(self, du):
        return (du - self.ciara_du) * self.nast.smer > 0

    def _pri_vstupe(self, du, tol=0.6):
        return abs(du - self.vstup) < tol

    def _podobne(self, a, b):
        if a is None or b is None:
            return True
        p = self.nast.podobnost
        return all(abs(x - y) < max(0.04, p * y) for x, y in zip(a, b))

    def krok(self, detekcie, platnost=1.0):
        self.snimka += 1
        slepa = platnost < 0.3
        hotove = []
        volne = list(detekcie)
        # najprv aktívne stopy (nedávno videné), potom stratené – tie majú prísnejšie párovanie
        for st in sorted(self.stopy, key=lambda s: self.snimka - s.posledna):
            chyba = self.snimka - st.posledna
            stratena = chyba > self.nast.strata_snimok
            kandidati = [st.du + st.vel * chyba] + ([st.du] if stratena or abs(st.vel) < 1e-3 else [])
            brana = self.nast.brana_m * (1.5 if stratena else 1.0)
            best, bd = None, brana
            for dt in volne:
                if stratena and not self._podobne((dt.dlzka, dt.sirka, dt.vyska), st.rozmery()):
                    continue
                vzd = min(np.hypot(dt.du - k, (dt.dv - st.dv) * 2) for k in kandidati)
                if vzd < bd:
                    best, bd = dt, vzd
            if best is None:
                if slepa:
                    st.slepe += 1
                continue
            st.slepe = 0
            volne.remove(best)
            v = (best.du - st.du) / chyba
            st.vel = v if (len(st.drah) < 2 or stratena) else 0.7 * st.vel + 0.3 * v
            st.du, st.dv, st.posledna = best.du, best.dv, self.snimka
            if best.uplna and not st.zapocitana:
                st.merania.append(best)
                st.drah.append((self.snimka, best.du))
            if not st.zapocitana and self._za_ciarou(st.du) and len(st.merania) >= self.nast.min_vzoriek:
                st.zapocitana = True
                hotove.append(self._vysledok(st))

        for dt in volne:
            self._id += 1
            st = Stopa(self._id, dt.du, dt.dv, posledna=self.snimka, zrodena_du=dt.du)
            if dt.uplna:
                st.merania.append(dt); st.drah.append((self.snimka, dt.du))
            # objavil sa v strede záberu? -> nie je to nedávno započítaný balík?
            if not self._pri_vstupe(dt.du):
                for i, (t, du, dv, rozm) in enumerate(self.pamat):
                    if np.hypot(dt.du - du, dt.dv - dv) < 0.4 and self._podobne((dt.dlzka, dt.sirka, dt.vyska), rozm):
                        st.zapocitana = True
                        self.pamat.pop(i)
                        break
            self.stopy.append(st)

        zostavaju = []
        for st in self.stopy:
            chyba = self.snimka - st.posledna
            if chyba <= self.nast.strata_snimok:
                zostavaju.append(st)
                continue
            odisiel = self._za_ciarou(st.du) and not self._v_zabere(st.du + st.vel * chyba)
            if st.zapocitana:
                if odisiel:
                    continue                          # normálny odchod zo záberu
                if chyba > self.drzat:
                    self.pamat.append((self.snimka, st.du, st.dv, st.rozmery()))
                    continue
            else:
                vypadok = st.slepe >= 0.5 * chyba
                if vypadok and self._za_ciarou(st.du + st.vel * chyba) and len(st.merania) >= self.nast.min_vzoriek:
                    st.zapocitana = True                 # prešiel čiarou počas výpadku (podľa rýchlosti)
                    hotove.append(self._vysledok(st, "prešiel čiarou počas výpadku kamery"))
                    if not odisiel:
                        zostavaju.append(st)
                    continue
                if self._pri_vstupe(st.du) and len(st.merania) < self.nast.min_vzoriek and chyba > self.nast.strata_snimok:
                    continue                          # len „nakukol“ do záberu alebo šum pri okraji
                if chyba > self.drzat:
                    if len(st.merania) >= self.nast.min_vzoriek:
                        hotove.append(self._vysledok(st, "neprešiel čiarou – výpadok kamery" if vypadok
                                                     else "zmizol pred čiarou – zložený z pásu?"))
                        self.pamat.append((self.snimka, st.du, st.dv, st.rozmery()))   # ak sa vráti, už sa nezapočíta
                    continue
            zostavaju.append(st)
        self.stopy = zostavaju
        self.pamat = [p for p in self.pamat if self.snimka - p[0] < self.pamat_snimok]
        return hotove

    def _v_zabere(self, du):
        u0, u1 = sorted((self.vstup, self.vstup + self.nast.smer * (self.ciara_du - self.vstup) / self.nast.ciara))
        return u0 <= du <= u1

    def dokonci(self):
        hotove = [self._vysledok(s, "koniec merania") for s in self.stopy
                  if not s.zapocitana and len(s.merania) >= self.nast.min_vzoriek]
        self.stopy = []
        return hotove

    def _vysledok(self, st, poznamka=""):
        m = st.merania
        d, s, v = st.rozmery()
        t, x = np.array(st.drah, float).T
        rychlost = abs(np.polyfit(t, x, 1)[0]) * self.fps if np.ptp(t) > 0 else 0.0
        return {"id": st.id, "dlzka": d, "sirka": s, "vyska": v, "snimok": len(m), "rychlost": rychlost,
                "poznamka": poznamka}

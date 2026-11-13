"""Zdroje hĺbkového obrazu: simulátor, Intel RealSense, Orbbec.

Každý zdroj vracia (hlbka_m: np.ndarray HxW float32, 0 = neplatné) a má .intr = Intrinsika.
"""
from dataclasses import dataclass
import time
import numpy as np


@dataclass
class Intrinsika:
    fx: float
    fy: float
    cx: float
    cy: float
    sirka: int
    vyska: int


# ---------------------------------------------------------------- simulátor
@dataclass
class SimBalik:
    d: float      # dĺžka (m)
    s: float      # šírka (m)
    v: float      # výška (m)
    uhol: float   # natočenie (rad)
    y: float      # priečna poloha na páse (m)
    x: float = 0.0


class SimulatorPasu:
    """Kamera nad pásom, pás ide v smere osi x obrazu. Pás 1 m, bočné lišty, podlaha haly nižšie."""

    def __init__(self, rychlost=1.5, fps=30, vyska_kamery=1.8, naklon_deg=4.0, sum=0.002,
                 dieri=0.01, sirka_pasu=1.0, seed=1, baliky=None, medzera=(0.3, 0.8)):
        self.intr = Intrinsika(fx=447.0, fy=447.0, cx=424.0, cy=240.0, sirka=848, vyska=480)  # ~ RealSense D455
        self.rychlost, self.fps, self.sum, self.dieri = rychlost, fps, sum, dieri
        self.sirka_pasu = sirka_pasu
        self.rng = np.random.default_rng(seed)
        self.t = 0
        a = np.deg2rad(naklon_deg)
        # svet: pás v rovine z=0, x = smer pohybu. Kamera pozerá dole, mierne naklonená okolo osi x.
        r_dole = np.array([[1, 0, 0], [0, -1, 0], [0, 0, -1]], float)
        r_nakl = np.array([[1, 0, 0], [0, np.cos(a), -np.sin(a)], [0, np.sin(a), np.cos(a)]])
        self.R = r_nakl @ r_dole          # svet <- kamera
        self.C = np.array([0.0, 0.0, vyska_kamery])
        u, v = np.meshgrid(np.arange(self.intr.sirka), np.arange(self.intr.vyska))
        lc = np.stack([(u - self.intr.cx) / self.intr.fx, (v - self.intr.cy) / self.intr.fy, np.ones_like(u, float)], -1)
        self.luce = lc.reshape(-1, 3) @ self.R.T   # smery lúčov vo svete (z kamery = 1 -> t = hĺbka)
        self.cakajuce = list(baliky) if baliky is not None else None
        self.medzera = medzera
        self.na_pase = []
        self.prejdene = []
        self._koniec = False
        self._dalsia_medzera = 0.0
        self.prazdny = False   # True = prázdny pás (kalibrácia)

    def _novy_balik(self):
        if self.cakajuce is not None:
            return self.cakajuce.pop(0) if self.cakajuce else None
        d = self.rng.uniform(0.15, 0.9)
        s = self.rng.uniform(0.1, min(d, 0.6))
        v = self.rng.uniform(0.05, 0.5)
        return SimBalik(d, s, v, self.rng.uniform(-0.5, 0.5), self.rng.uniform(-0.15, 0.15))

    def citaj(self):
        dt = 1.0 / self.fps
        self.t += 1
        if not self.prazdny:
            for b in self.na_pase:
                b.x += self.rychlost * dt
            posl = self.na_pase[-1] if self.na_pase else None
            if self._koniec is False and (posl is None or posl.x - 0.5 * np.hypot(posl.d, posl.s) > -2.2 + self._dalsia_medzera):
                b = self._novy_balik()
                if b is None:
                    self._koniec = True
                else:
                    b.x = -2.2 - 0.5 * np.hypot(b.d, b.s)
                    self.na_pase.append(b)
                    self._dalsia_medzera = self.rng.uniform(*self.medzera)
            self.prejdene += [b for b in self.na_pase if b.x > 2.6]
            self.na_pase = [b for b in self.na_pase if b.x <= 2.6]
        return self._vykresli()

    def _vykresli(self):
        o, L = self.C, self.luce
        t = np.full(len(L), np.inf)
        # pás (z = 0) iba v šírke pásu, inak podlaha haly z = -0.8
        tp = -o[2] / L[:, 2]
        y = o[1] + tp * L[:, 1]
        na_pase = np.abs(y) <= self.sirka_pasu / 2
        t = np.where(na_pase, tp, (-0.8 - o[2]) / L[:, 2])
        # bočné lišty: 3 cm široké, 6 cm vysoké
        for sy in (-1, 1):
            yc = sy * (self.sirka_pasu / 2 + 0.015)
            t = np.minimum(t, self._kvader(o, L, 0.0, yc, 0.0, 50.0, 0.03, 0.06))
        for b in self.na_pase:
            t = np.minimum(t, self._kvader(o, L, b.x, b.y, b.uhol, b.d, b.s, b.v))
        hlbka = t.reshape(self.intr.vyska, self.intr.sirka).astype(np.float32)
        hlbka *= 1 + self.rng.normal(0, self.sum, hlbka.shape).astype(np.float32) * hlbka  # šum rastie s hĺbkou
        hlbka[self.rng.random(hlbka.shape) < self.dieri] = 0
        return hlbka

    @staticmethod
    def _kvader(o, L, x, y, uhol, d, s, v):
        c, si = np.cos(uhol), np.sin(uhol)
        ox, oy = o[0] - x, o[1] - y
        ob = np.array([c * ox + si * oy, -si * ox + c * oy, o[2]])
        lb = np.stack([c * L[:, 0] + si * L[:, 1], -si * L[:, 0] + c * L[:, 1], L[:, 2]], -1)
        lo = np.array([-d / 2, -s / 2, 0.0])
        hi = np.array([d / 2, s / 2, v])
        with np.errstate(divide="ignore", invalid="ignore"):
            t1 = (lo - ob) / lb
            t2 = (hi - ob) / lb
        t0 = np.nanmax(np.minimum(t1, t2), axis=1)
        tk = np.nanmin(np.maximum(t1, t2), axis=1)
        return np.where((t0 <= tk) & (tk > 0), t0, np.inf)

    def zastav(self):
        pass


# ---------------------------------------------------------------- Intel RealSense
class RealSense:
    """Intel RealSense D4xx (pip install pyrealsense2). Netestované na reálnom zariadení."""

    def __init__(self, sirka=848, vyska=480, fps=30):
        import pyrealsense2 as rs
        self.rs = rs
        self.pipe = rs.pipeline()
        cfg = rs.config()
        cfg.enable_stream(rs.stream.depth, sirka, vyska, rs.format.z16, fps)
        prof = self.pipe.start(cfg)
        self.scale = prof.get_device().first_depth_sensor().get_depth_scale()
        i = prof.get_stream(rs.stream.depth).as_video_stream_profile().get_intrinsics()
        self.intr = Intrinsika(i.fx, i.fy, i.ppx, i.ppy, i.width, i.height)
        self.spatial = rs.spatial_filter()   # vyhladenie bez časového rozmazania (pás sa hýbe)

    def citaj(self):
        f = self.pipe.wait_for_frames().get_depth_frame()
        f = self.spatial.process(f)
        return np.asanyarray(f.get_data()).astype(np.float32) * self.scale

    def zastav(self):
        self.pipe.stop()


# ---------------------------------------------------------------- Orbbec
class Orbbec:
    """Orbbec Femto / Gemini (pip install pyorbbecsdk). Netestované na reálnom zariadení."""

    def __init__(self):
        from pyorbbecsdk import Pipeline, Config, OBSensorType
        self.pipe = Pipeline()
        cfg = Config()
        prof = self.pipe.get_stream_profile_list(OBSensorType.DEPTH_SENSOR).get_default_video_stream_profile()
        cfg.enable_stream(prof)
        self.pipe.start(cfg)
        p = self.pipe.get_camera_param().depth_intrinsic
        self.intr = Intrinsika(p.fx, p.fy, p.cx, p.cy, p.width, p.height)

    def citaj(self):
        while True:
            frames = self.pipe.wait_for_frames(200)
            f = frames.get_depth_frame() if frames else None
            if f is not None:
                break
        h, w = f.get_height(), f.get_width()
        mm = np.frombuffer(f.get_data(), dtype=np.uint16).reshape(h, w).astype(np.float32) * f.get_depth_scale()
        return mm / 1000.0

    def zastav(self):
        self.pipe.stop()


def otvor(nazov, **kw):
    nazov = nazov.lower()
    if nazov in ("sim", "simulator"):
        return SimulatorPasu(**kw)
    if nazov == "realsense":
        return RealSense()
    if nazov == "orbbec":
        return Orbbec()
    raise ValueError(f"Neznáma kamera: {nazov} (sim / realsense / orbbec)")

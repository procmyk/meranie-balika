"""Geometria: rovina pásu, robustný obdĺžnik, kategórie balíkov."""
import numpy as np
import cv2

# Kategórie (cm) – rovnaké ako v mobilnej aplikácii. Balík patrí do prvej, do ktorej sa zmestí.
KATEGORIE = [
    ("XS", (25, 20, 10)),
    ("S", (40, 30, 15)),
    ("M", (60, 40, 30)),
    ("L", (80, 60, 40)),
    ("XL", (120, 80, 60)),
]
NADROZMER = "NADROZMER"


def kategoria(d_cm, s_cm, v_cm):
    r = sorted((d_cm, s_cm, v_cm), reverse=True)
    for nazov, mx in KATEGORIE:
        if r[0] <= mx[0] and r[1] <= mx[1] and r[2] <= mx[2]:
            return nazov
    return NADROZMER


def fit_rovina_ransac(body, iteracie=300, prah=0.01, rng=None):
    """RANSAC rovina pre body Nx3. Vráti (n, d, maska_inlierov), n·p + d = 0, d > 0 (kamera nad rovinou)."""
    rng = rng or np.random.default_rng(0)
    n_bodov = len(body)
    best = (None, None, None, -1)
    for _ in range(iteracie):
        a, b, c = body[rng.choice(n_bodov, 3, replace=False)]
        n = np.cross(b - a, c - a)
        dlz = np.linalg.norm(n)
        if dlz < 1e-9:
            continue
        n /= dlz
        d = -n @ a
        inl = np.abs(body @ n + d) < prah
        cnt = int(inl.sum())
        if cnt > best[3]:
            best = (n, d, inl, cnt)
    n, d, inl, _ = best
    # spresnenie metódou najmenších štvorcov (SVD) na inlieroch
    p = body[inl]
    stred = p.mean(axis=0)
    _, _, vt = np.linalg.svd(p - stred, full_matrices=False)
    n = vt[2]
    d = -n @ stred
    if d < 0:
        n, d = -n, -d
    inl = np.abs(body @ n + d) < prah
    return n, float(d), inl


def baza_roviny(n, smer_x=np.array([1.0, 0.0, 0.0])):
    """Ortonormálna báza (u, v) v rovine; u = priemet osi x kamery (smer pohybu pásu)."""
    u = smer_x - (smer_x @ n) * n
    u /= np.linalg.norm(u)
    v = np.cross(n, u)
    return u, v


def robustny_obdlznik(body2d, orez=0.02):
    """Natočenie z min. obdĺžnika okolo konvexného obalu, rozmery z percentilov (odolné voči šumu)."""
    pts = np.asarray(body2d, dtype=np.float32)
    (_, _), (_, _), uhol = cv2.minAreaRect(pts)
    a = np.deg2rad(uhol)
    c, s = np.cos(a), np.sin(a)
    pu = pts[:, 0] * c + pts[:, 1] * s
    pv = -pts[:, 0] * s + pts[:, 1] * c
    korekcia = 1.0 / (1.0 - 2.0 * orez)  # pri rovnomernom rozložení bodov
    u0, u1 = np.percentile(pu, [100 * orez, 100 * (1 - orez)])
    v0, v1 = np.percentile(pv, [100 * orez, 100 * (1 - orez)])
    lu, lv = (u1 - u0) * korekcia, (v1 - v0) * korekcia
    uc, vc = (u0 + u1) / 2, (v0 + v1) / 2
    stred = (uc * c - vc * s, uc * s + vc * c)
    return max(lu, lv), min(lu, lv), stred, float(uhol)

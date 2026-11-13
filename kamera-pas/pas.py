#!/usr/bin/env python3
"""Meranie balíkov na páse hĺbkovou kamerou.

  python pas.py kalibracia --kamera realsense     # raz, pri prázdnom páse
  python pas.py meranie    --kamera realsense     # beží stále, zapisuje do data/merania_pas_<dátum>.csv
  python pas.py suhrn data/merania_pas_2026-11-13.csv
  python pas.py test                              # overenie na simulátore (bez kamery)
"""
import argparse
import sys
import time

import numpy as np

from pasmeter.kamery import otvor, SimulatorPasu, SimBalik
from pasmeter.meranie import Kalibracia, Nastavenia, analyzuj, Sledovanie
from pasmeter.vystup import ZapisCSV, suhrn
from pasmeter.geometria import kategoria

KAL_SUBOR = "kalibracia.npz"


def kalibruj(kamera, nast, snimok=30, subor=KAL_SUBOR):
    print(f"Kalibrácia: snímam prázdny pás ({snimok} snímok)…")
    for _ in range(10):  # zahrievanie / automatická expozícia
        kamera.citaj()
    snimky = [kamera.citaj() for _ in range(snimok)]
    kal = Kalibracia.z_prazdneho_pasu(snimky, kamera.intr, nast)
    if subor:
        kal.uloz(subor)
    print("  OK –", kal.info())
    return kal


def meraj(kamera, kal, nast, zapis=None, fps=30.0, max_snimok=None, nahlad=False, tichy=False):
    sled = Sledovanie(nast, fps, kal)
    vysledky = []
    t0, n = time.time(), 0

    def vypis(r):
        vysledky.append(r)
        riadok = zapis.zapis(r, r.get('poznamka', '')) if zapis else None
        if not tichy:
            d, s, v = (round(r[k] * 100) for k in ("dlzka", "sirka", "vyska"))
            print(f"  #{riadok[0] if riadok else len(vysledky):<4} {kategoria(d, s, v):<9} {d:>4} × {s:>3} × {v:>3} cm"
                  f"  {d * s * v / 1000:7.1f} l   ({r['snimok']} snímok, pás {r['rychlost']:.2f} m/s)"
                  + (f"  [{r['poznamka']}]" if r.get('poznamka') else ''), flush=True)

    try:
        while max_snimok is None or n < max_snimok:
            hlbka = kamera.citaj()
            det, platnost = analyzuj(hlbka, kal, nast)
            for r in sled.krok(det, platnost):
                vypis(r)
            n += 1
            if nahlad:
                zobraz_nahlad(hlbka, kal, det)
            if not tichy and n % 300 == 0:
                print(f"  … {n} snímok, {n / (time.time() - t0):.1f} snímok/s", flush=True)
    except KeyboardInterrupt:
        print("\nUkončujem…")
    for r in sled.dokonci():
        vypis(r)
    return vysledky


def zobraz_nahlad(hlbka, kal, det):
    import cv2
    img = cv2.applyColorMap(cv2.convertScaleAbs(hlbka, alpha=255 / (kal.d * 1.2)), cv2.COLORMAP_JET)
    for d in det:
        cv2.putText(img, f"{d.dlzka * 100:.0f}x{d.sirka * 100:.0f}x{d.vyska * 100:.0f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                    1, (255, 255, 255), 2)
    cv2.imshow("Meranie balikov (q = koniec)", img)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        raise KeyboardInterrupt


def test(pocet=40, rychlost=1.5, seed=3):
    """Simulácia: náhodné balíky na páse, porovnanie s ich skutočnými rozmermi."""
    rng = np.random.default_rng(seed)
    baliky = []
    for _ in range(pocet):
        d = rng.uniform(0.15, 0.9); s = rng.uniform(0.1, min(d, 0.6)); v = rng.uniform(0.05, 0.5)
        baliky.append(SimBalik(d, s, v, rng.uniform(-0.6, 0.6), rng.uniform(-0.15, 0.15)))
    pravda = [(b.d, b.s, b.v) for b in baliky]
    nast = Nastavenia()
    sim = SimulatorPasu(rychlost=rychlost, baliky=list(baliky), seed=seed)
    sim.prazdny = True
    kal = kalibruj(sim, nast, subor=None)
    sim.prazdny = False
    print(f"Simulácia: {pocet} balíkov, pás {rychlost} m/s, kamera 1,8 m nad pásom, šum hĺbky ~0,6 cm")
    t0 = time.time()
    snimok = int((pocet * 1.5 + 6) / rychlost * 30)
    vys = meraj(sim, kal, nast, fps=30, max_snimok=snimok, tichy=True)
    trvanie = time.time() - t0
    print(f"  spracované {snimok} snímok za {trvanie:.1f} s ({snimok / trvanie:.0f} snímok/s)")
    print(f"  zmeraných {len(vys)} z {pocet} balíkov")
    chyby = []
    print("    skutočné (cm)       namerané (cm)       kategória")
    for (d, s, v), r in zip(pravda, vys):
        dm, sm, vm = r["dlzka"], r["sirka"], r["vyska"]
        chyby.append((dm - d, sm - s, vm - v))
        ks, km = kategoria(*(round(x * 100) for x in (d, s, v))), kategoria(*(round(x * 100) for x in (dm, sm, vm)))
        print(f"    {d*100:5.1f} {s*100:5.1f} {v*100:5.1f}   {dm*100:5.1f} {sm*100:5.1f} {vm*100:5.1f}   {ks:<9}{'' if ks == km else ' -> ' + km}")
    ch = np.abs(np.array(chyby)) * 100
    print(f"  priemerná chyba: dĺžka {ch[:, 0].mean():.1f} cm, šírka {ch[:, 1].mean():.1f} cm, výška {ch[:, 2].mean():.1f} cm")
    print(f"  max. chyba:      dĺžka {ch[:, 0].max():.1f} cm, šírka {ch[:, 1].max():.1f} cm, výška {ch[:, 2].max():.1f} cm")
    return len(vys) == pocet


def main():
    ap = argparse.ArgumentParser(description="Meranie balíkov na páse hĺbkovou kamerou")
    sub = ap.add_subparsers(dest="prikaz", required=True)
    for nazov in ("kalibracia", "meranie"):
        p = sub.add_parser(nazov)
        p.add_argument("--kamera", default="realsense", help="realsense / orbbec / sim")
        p.add_argument("--kalibracia", default=KAL_SUBOR)
    sub.choices["meranie"].add_argument("--data", default="data", help="priečinok pre CSV")
    sub.choices["meranie"].add_argument("--nahlad", action="store_true", help="okno s náhľadom kamery")
    sub.choices["meranie"].add_argument("--fps", type=float, default=30)
    p = sub.add_parser("suhrn"); p.add_argument("csv")
    p = sub.add_parser("test"); p.add_argument("--pocet", type=int, default=40); p.add_argument("--rychlost", type=float, default=1.5)
    a = ap.parse_args()
    nast = Nastavenia()

    if a.prikaz == "test":
        sys.exit(0 if test(a.pocet, a.rychlost) else 1)
    if a.prikaz == "suhrn":
        text, cesta = suhrn(a.csv)
        print(text); print(f"Súhrn uložený: {cesta}")
        return
    kamera = otvor(a.kamera)
    try:
        if a.prikaz == "kalibracia":
            if a.kamera == "sim":
                kamera.prazdny = True
            kalibruj(kamera, nast, subor=a.kalibracia)
        else:
            kal = Kalibracia.nacitaj(a.kalibracia)
            print("Kalibrácia:", kal.info())
            print("Meriam… (Ctrl+C = koniec)")
            meraj(kamera, kal, nast, zapis=ZapisCSV(a.data), fps=a.fps, nahlad=a.nahlad)
    finally:
        kamera.zastav()


if __name__ == "__main__":
    main()

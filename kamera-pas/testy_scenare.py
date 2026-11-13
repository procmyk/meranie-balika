#!/usr/bin/env python3
"""Testy proti dvojitému započítaniu: zastavenie pásu, výpadky kamery, cúvnutie, zloženie balíka z pásu.
Spustenie: python testy_scenare.py   (trvá asi 2–3 minúty, nepotrebuje kameru)"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pasmeter.kamery import SimulatorPasu, SimBalik
from pasmeter.meranie import Kalibracia, Nastavenia, analyzuj, Sledovanie

chyby = 0

def scenar(nazov, udalosti, baliky, snimok=330):
    nast = Nastavenia()
    sim = SimulatorPasu(baliky=list(baliky), seed=5, krok=2, medzera=(0.6, 0.6)); sim.prazdny = True
    kal = Kalibracia.z_prazdneho_pasu([sim.citaj() for _ in range(10)], sim.intr, nast); sim.prazdny = False
    sled = Sledovanie(nast, 30, kal)
    zaz = []
    for i in range(snimok):
        if i in udalosti: udalosti[i](sim)
        zaz += sled.krok(*analyzuj(sim.citaj(), kal, nast))
    zaz += sled.dokonci()
    global chyby
    chyby += len(zaz) != len(baliky)
    print(f"{nazov:<46} balíkov {len(baliky)} -> zapísaných {len(zaz)}" + ('' if len(zaz) == len(baliky) else '   ❌'),
          [f"{r['dlzka']*100:.0f}x{r['sirka']*100:.0f}x{r['vyska']*100:.0f}" + (f" ({r['poznamka']})" if r.get('poznamka') else '') for r in zaz])

B = [SimBalik(0.4, 0.3, 0.2, 0.3, 0.0), SimBalik(0.6, 0.4, 0.15, -0.2, 0.1)]
def rych(v): return lambda s: setattr(s, 'rychlost', v)
def vyp(n): return lambda s: setattr(s, 'vypadok', n)
scenar("A: normálny chod", {}, B)
scenar("B: pás stojí 4 s (balík v zábere)", {75: rych(0), 195: rych(1.5)}, B, 450)
scenar("C: výpadok kamery 0,5 s (15 snímok)", {80: vyp(15)}, B)
scenar("D: výpadok kamery 2 s (60 snímok)", {80: vyp(60)}, B, 400)
scenar("E: pás cúvne 1 s a ide znova", {85: rych(-1.0), 115: rych(1.5)}, B, 400)
scenar("F: pás stojí 4 s + výpadok počas státia", {75: rych(0), 100: vyp(40), 195: rych(1.5)}, B, 450)
def odober(s): s.na_pase.pop(0)
scenar("G: pás stojí 15 s + výpadok 7 s počas státia", {75: rych(0), 100: vyp(210), 525: rych(1.5)}, B, 750)
scenar("H: balík zložený rukou z pásu pred čiarou", {40: odober}, B, 500)
B3 = [SimBalik(0.4, 0.3, 0.2, 0.0, 0.0), SimBalik(0.4, 0.3, 0.2, 0.0, 0.0), SimBalik(0.4, 0.3, 0.2, 0.0, 0.0)]
scenar("I: tri rovnaké balíky za sebou", {}, B3, 380)

print("\nVšetky scenáre OK" if not chyby else f"\nZlyhalo scenárov: {chyby}")
sys.exit(1 if chyby else 0)

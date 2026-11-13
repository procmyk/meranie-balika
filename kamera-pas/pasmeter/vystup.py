"""Zápis meraní do CSV (pre slovenský Excel) a súhrn podľa kategórií."""
import csv
import os
from datetime import datetime

from .geometria import KATEGORIE, NADROZMER, kategoria

HLAVICKA = ["Poradie", "Kategória", "Dátum a čas", "Dĺžka (cm)", "Šírka (cm)", "Výška (cm)", "Objem (l)",
            "Objemová hmotnosť (kg, ÷5000)", "Rýchlosť pásu (m/s)", "Snímok", "Číslo balíka / poznámka"]


def num(x, des=1):
    return f"{x:.{des}f}".replace(".", ",")


class ZapisCSV:
    """Každý deň nový súbor merania_pas_RRRR-MM-DD.csv; zapisuje sa priebežne (nič sa nestratí pri výpadku)."""

    def __init__(self, priecinok="data"):
        self.priecinok = priecinok
        os.makedirs(priecinok, exist_ok=True)
        self.poradie = 0
        self._den = None

    def cesta(self, den=None):
        den = den or datetime.now().strftime("%Y-%m-%d")
        return os.path.join(self.priecinok, f"merania_pas_{den}.csv")

    def zapis(self, r, poznamka=""):
        teraz = datetime.now()
        cesta = self.cesta(teraz.strftime("%Y-%m-%d"))
        nove = not os.path.exists(cesta)
        if nove or self._den != teraz.date():
            self.poradie = 0 if nove else sum(1 for _ in open(cesta, encoding="utf-8-sig")) - 1
            self._den = teraz.date()
        self.poradie += 1
        d, s, v = (round(r[k] * 100) for k in ("dlzka", "sirka", "vyska"))
        riadok = [self.poradie, kategoria(d, s, v), teraz.strftime("%d.%m.%Y %H:%M:%S"), d, s, v,
                  num(d * s * v / 1000), num(d * s * v / 5000), num(r.get("rychlost", 0), 2), r.get("snimok", ""), poznamka]
        with open(cesta, "a", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            if nove:
                w.writerow(HLAVICKA)
            w.writerow(riadok)
        return riadok


def suhrn(cesta_csv, cesta_vystup=None):
    """Spočíta balíky a litre podľa kategórií; zapíše súhrnné CSV a vráti text."""
    with open(cesta_csv, encoding="utf-8-sig") as f:
        riadky = [r for r in csv.reader(f, delimiter=";")][1:]
    riadky = [r for r in riadky if r and r[0].isdigit()]
    nazvy = [k for k, _ in KATEGORIE] + [NADROZMER]
    stat = {k: [0, 0.0] for k in nazvy}
    for r in riadky:
        stat[r[1]][0] += 1
        stat[r[1]][1] += float(r[6].replace(",", "."))
    spolu_l = sum(v[1] for v in stat.values())
    limity = dict(KATEGORIE)
    tab = [["Kategória", "Max. rozmery (cm)", "Počet balíkov", "Objem spolu (l)", "Podiel z počtu"]]
    for k in nazvy:
        c, l = stat[k]
        tab.append([k, " × ".join(map(str, limity[k])) if k in limity else "väčšie / dlhšie ako 120", c, num(l),
                    num(100 * c / len(riadky) if riadky else 0) + " %"])
    tab += [[], ["Počet balíkov", len(riadky)], ["Objem spolu (l)", num(spolu_l)]]
    cesta_vystup = cesta_vystup or cesta_csv.replace(".csv", "_suhrn.csv")
    with open(cesta_vystup, "w", newline="", encoding="utf-8-sig") as f:
        csv.writer(f, delimiter=";").writerows(tab)
    text = "\n".join(f"  {r[0]:<10} {r[2]:>5} ks  {r[3]:>9} l  {r[4]:>7}" for r in tab[1:len(nazvy) + 1])
    return f"{text}\n  {'SPOLU':<10} {len(riadky):>5} ks  {num(spolu_l):>9} l", cesta_vystup

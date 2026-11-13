# Meranie balíkov na páse (hĺbková kamera)

Program pre počítač pri páse. Kamera je nad pásom a meria balíky **za jazdy, bez zastavenia**.
Každý balík zapíše do denného súboru CSV pre Excel: D × Š × V, objem, objemová hmotnosť, kategória XS až NADROZMER, čas a rýchlosť pásu.

## Hardvér
- Hĺbková kamera: **Intel RealSense D455/D456** alebo **Orbbec Femto Bolt/Mega, Gemini 2** (iné kamery sa dajú doplniť)
- Počítač: mini PC s Windows alebo Linuxom, USB 3 (alebo Ethernet pri kamerách s PoE)
- Uchytenie: kamera **1,5–2 m nad pásom, objektívom kolmo dole**. Pás ide v zábere **zľava doprava** (dlhšia strana obrazu je v smere pásu).

## Inštalácia
1. Nainštaluj Python 3.10+ (https://www.python.org).
2. V priečinku `kamera-pas` spusti:
   ```
   pip install -r requirements.txt
   pip install pyrealsense2        # pre RealSense
   pip install pyorbbecsdk         # pre Orbbec
   ```

## Použitie
1. **Kalibrácia** (raz po montáži a po každom posunutí kamery). Pás musí byť **prázdny**:
   ```
   python pas.py kalibracia --kamera realsense
   ```
   Program nájde rovinu pásu, zapamätá si lišty a okolie a uloží `kalibracia.npz`.
2. **Meranie** (beží stále, ukončí sa cez Ctrl+C):
   ```
   python pas.py meranie --kamera realsense
   python pas.py meranie --kamera realsense --nahlad    # s oknom náhľadu
   ```
   Výsledky sa zapisujú priebežne do `data/merania_pas_RRRR-MM-DD.csv`.
3. **Súhrn podľa kategórií:**
   ```
   python pas.py suhrn data/merania_pas_2026-11-13.csv
   ```
4. **Test bez kamery (simulátor):**
   ```
   python pas.py test
   ```

## Ako to funguje
1. Kalibrácia nájde rovinu pásu (RANSAC) a zapamätá si výšku pevných objektov (lišty, konštrukcia).
2. V každej snímke sa vyhľadajú miesta vyššie ako pás aj pozadie (o 1,5 cm a viac). Každá súvislá oblasť je jeden balík.
3. Výška balíka = medián vrchnej steny. Pôdorys = najmenší obdĺžnik okolo vrchnej steny, takže natočenie balíka nevadí.
4. Balík sa sleduje počas prechodu záberom. Merajú sa len snímky, v ktorých je **celý**. Zapíše sa medián všetkých snímok.

## Výsledky na simulátore
40 náhodných balíkov, pás 1,5 m/s, kamera 1,8 m nad pásom, šum hĺbky ~0,6 cm:
zmerané všetky, priemerná chyba ~0,3 cm. Spracovanie trvá ~2,5 ms na snímku (kamera dáva 30 snímok/s).
**Na reálnej kamere zatiaľ netestované.** Skutočná presnosť bude horšia, očakávaj približne ±0,5–1,5 cm.

## Obmedzenia
- Balíky musia ísť **oddelene** (medzera aspoň ~5 cm). Balíky natesno vedľa seba alebo na sebe sa zmerajú ako jeden.
- Nepravidelné tvary (vrecia, rúry) sa merajú ako „krabica okolo“.
- Čierne lesklé a priehľadné obaly môžu mať v hĺbkovom obraze diery.
- Nie je to úradne overené meradlo. Na fakturáciu zákazníkom sa nesmie použiť.

## Nastavenia
Prahy (min. výška objektu, min. veľkosť, ...) sú v `pasmeter/meranie.py` v triede `Nastavenia`.
Kategórie sú v `pasmeter/geometria.py` (`KATEGORIE`).

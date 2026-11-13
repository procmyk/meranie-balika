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

## Ako sa zabráni dvojitému započítaniu
1. **Počítacia čiara:** balík sa započíta až vtedy, keď prejde čiarou v 60 % záberu, a len raz. Kým je v zábere, program ho sleduje ako ten istý balík. Preto **zastavenie ani cúvnutie pásu** nič nezapočíta znova.
2. **Stratený balík sa neukončí hneď:** ak balík zmizne v strede záberu (ruka nad ním, výpadok kamery, čierny obal), program naň čaká 5 s a znova ho spáruje podľa polohy a rozmerov.
3. **Pamäť započítaných balíkov (2 min):** ak sa po dlhšom výpadku objaví v strede záberu balík na rovnakom mieste a s rovnakými rozmermi, nezapočíta sa znova. Nový balík prichádzajúci zo vstupnej strany sa porovnáva iba vtedy, keď sa objaví v strede záberu, takže **rovnaké balíky za sebou sa počítajú správne**.
4. Nezvyčajné situácie majú v CSV **poznámku**, napríklad „zmizol pred čiarou – zložený z pásu?“ alebo „prešiel čiarou počas výpadku kamery“.

Overené scenáre (`python testy_scenare.py`): normálny chod, pás stojí 4 s, výpadok kamery 0,5 s a 2 s, cúvnutie pásu, státie a výpadok spolu, státie 15 s s výpadkom 7 s, zloženie balíka z pásu, tri rovnaké balíky za sebou. Vo všetkých sa každý balík započítal práve raz.

Smer pásu (zľava doprava alebo sprava doľava) a polohu čiary nastavíš v `Nastavenia` (`smer`, `ciara`).
Kamera nedokáže rozlíšiť, či ten istý balík prešiel pásom dvakrát (napríklad sa vrátil na začiatok). Na to treba čítačku čiarových kódov.

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

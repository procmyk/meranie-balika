# Meranie balíka

Webová aplikácia, ktorá meria rozmery balíka cez kameru telefónu (Android, Chrome, ARCore).

**Spustenie:** otvor v Chrome na Androide adresu GitHub Pages tohto repozitára.
Telefón potrebuje aplikáciu *Google Play Services for AR*.

1. Namier na voľnú podlahu vedľa balíka a pomaly hýb telefónom – podlaha sa nastaví sama (prípadne **Nastaviť podlahu**)
2. Namier na balík zo vzdialenosti 0,5–1 m, šikmo zhora (asi 45°), a chvíľu drž telefón v kľude.
   Keď rámik sedí na balíku a tlačidlo zozelenie (rozmery sú stabilné), stlač **Zmerať**.

**Ručný režim:** zamieriš krížik postupne na 3 rohy balíka dole pri zemi a na vrch balíka, pri každom stlačíš **Bod**.

## Valce a nepravidelné balíky

Aplikácia rozpozná **ležiaci valec** (napr. stočený matrac) podľa zaobleného profilu. Šírku dopočíta ako priemer (= výška), lebo zadnú stranu valca kamera nevidí. Vo výsledku sa zobrazí štítok **⬭ valec** a v exporte stĺpec *Tvar*.
Rozmery sú vždy rozmery kvádra okolo balíka (D × Š × V), podľa nich sa počíta objem, objemová hmotnosť aj kategória. Pri valci sa navyše ukáže jeho skutočný objem.
Dlhé balíky musia byť celé v zábere. Ak sa balík dotýka okraja obrazu, aplikácia upozorní a tlačidlo nezozelenie. Pomôže odstúpiť alebo otočiť telefón tak, aby balík išiel pozdĺž obrazovky.
Stojaci valec sa meria ako kváder okolo neho (priemer × priemer × výška).
**Pneumatiky:** aplikácia ich rozpozná (štítok **🛞 pneumatika**) a do poznámky sama vpíše „pneumatika“. Poznámka sa dá zmazať alebo prepísať.
- ležiaca: okrúhly pôdorys s otvorom v strede, priemer 40–110 cm, šírka 10–45 cm. Meria sa ako kváder okolo nej (priemer × priemer × šírka).
- stojaca (na behúni): kruhový profil, priemer sa dopočíta z výšky.
- iné okrúhle predmety stojace na behúni s rozmermi pneumatiky (napr. káblový bubon) sa môžu tiež označiť ako pneumatika.
**Dlhé predmety** (napr. krabica s rybárskym prútom): musia byť celé v zábere. Pri 120–150 cm treba odstúpiť asi na 2–2,5 m, telefón otočiť pozdĺž predmetu a počítať s menšou presnosťou (±2–3 cm).

## Číslo balíka zo štítka

Po zmeraní ťukni na **📷** vedľa poľa *Číslo balíka*. AR meranie sa na chvíľu vypne a zapne sa bežný fotoaparát s automatickým zaostrovaním (počas AR má kamera pevné zaostrenie na diaľku). K dispozícii je **🔦 blesk** a **2× priblíženie**.
Prečíta čiarové kódy (Code 128, EAN, ITF…) aj 2D kódy (QR, DataMatrix, PDF417). Číslo sa vyplní samo a telefón zavibruje.
Po **Uložiť a merať ďalší** sa meranie spustí znova a podlaha sa nastaví sama.
Ak je balík s rovnakým číslom už uložený, aplikácia upozorní a uloží ho až po druhom stlačení.

## Export meraní

Po meraní môžeš doplniť číslo balíka alebo poznámku a dať **Uložiť a merať ďalší**. Merania sa ukladajú v telefóne.
Po stlačení **Koniec** je na úvodnej obrazovke zoznam meraní a tlačidlá:

- **Export (Excel)** stiahne súbor CSV (poradie, číslo balíka, kategória, dátum a čas, D × Š × V v cm, objem v litroch, objemová hmotnosť, poznámka, režim, počet balíkov a objem spolu).
- **Zdieľať** pošle súbor napríklad e-mailom alebo cez WhatsApp.
- **Vymazať** zmaže všetky uložené merania.

## Kategórie balíkov

Rozmery sa zoradia od najväčšieho a balík dostane prvú kategóriu, do ktorej sa zmestí (na otočení nezáleží):

| Kategória | Max. rozmery (cm) |
|---|---|
| XS | 25 × 20 × 10 |
| S | 40 × 30 × 15 |
| M | 60 × 40 × 30 |
| L | 80 × 60 × 40 |
| XL | 120 × 80 × 60 |
| NADROZMER | väčšie alebo dlhšie ako 120 cm |

Export obsahuje na konci súhrn podľa kategórií (počet, objem, podiel). Hranice sa menia v `measure.js` (`CATEGORIES`).

# Meranie balíka

Webová aplikácia, ktorá meria rozmery balíka cez kameru telefónu (Android, Chrome, ARCore).

**Spustenie:** otvor v Chrome na Androide adresu GitHub Pages tohto repozitára.
Telefón potrebuje aplikáciu *Google Play Services for AR*.

1. Namier na voľnú podlahu vedľa balíka a pomaly hýb telefónom – podlaha sa nastaví sama (prípadne **Nastaviť podlahu**)
2. Namier na balík zo vzdialenosti 0,5–1 m, šikmo zhora (asi 45°), a chvíľu drž telefón v kľude.
   Keď rámik sedí na balíku a tlačidlo zozelenie (rozmery sú stabilné), stlač **Zmerať**.

**Ručný režim:** zamieriš krížik postupne na 3 rohy balíka dole pri zemi a na vrch balíka, pri každom stlačíš **Bod**.

## Export meraní

Po meraní môžeš doplniť číslo balíka alebo poznámku a dať **Uložiť a merať ďalší**. Merania sa ukladajú v telefóne.
Po stlačení **Koniec** je na úvodnej obrazovke zoznam meraní a tlačidlá:

- **Export (Excel)** stiahne súbor CSV (poradie, kategória, dátum a čas, D × Š × V v cm, objem v litroch, objemová hmotnosť, poznámka, režim, počet balíkov a objem spolu).
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

## Meranie na páse (hĺbková kamera)

V priečinku [`kamera-pas/`](kamera-pas/) je program pre počítač s hĺbkovou kamerou nad pásom. Meria balíky za jazdy a zapisuje ich do CSV. Návod je v jeho README.

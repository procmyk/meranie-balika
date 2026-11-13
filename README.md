# Meranie balíka

Webová aplikácia, ktorá meria rozmery balíka cez kameru telefónu (Android, Chrome, ARCore).

**Spustenie:** otvor v Chrome na Androide adresu GitHub Pages tohto repozitára.
Telefón potrebuje aplikáciu *Google Play Services for AR*.

1. Namier na podlahu vedľa balíka → **Nastaviť podlahu**
2. Namier na balík (0,5–1,5 m, mierne zhora) → **Zmerať**

Ak zariadenie nepodporuje hĺbkovú mapu, použi **Ručný režim** (3 rohy podstavy + vrch balíka).

## Export meraní

Po meraní môžeš doplniť číslo balíka alebo poznámku a dať **Uložiť a merať ďalší**. Merania sa ukladajú v telefóne.
Po stlačení **Koniec** je na úvodnej obrazovke zoznam meraní a tlačidlá:

- **Export (Excel)** stiahne súbor CSV (poradie, dátum a čas, D × Š × V v cm, objem v litroch, objemová hmotnosť, poznámka, režim, počet balíkov a objem spolu).
- **Zdieľať** pošle súbor napríklad e-mailom alebo cez WhatsApp.
- **Vymazať** zmaže všetky uložené merania.

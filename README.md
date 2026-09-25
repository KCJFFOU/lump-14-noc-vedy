# LUMP-14 – Noc vědy 2026

České rozhraní Streamlit pro popularizační lingvistický klasifikátor LUMP-14. Zelená/červená vyjadřuje podobnost jazykových charakteristik, nikoli ověření pravdivosti článku.

## Nasazení na GitHub + Streamlit Community Cloud

1. Na GitHubu vytvořte nový repozitář (např. `lump14-noc-vedy`).
2. Nahrajte **obsah této složky do kořene repozitáře** (nikoli samotný ZIP). U veřejného repozitáře budou soubory veřejně dostupné.
3. Otevřete https://share.streamlit.io/ a přihlaste se přes GitHub.
4. Zvolte **Create app / Deploy a public app from GitHub**, vyberte repozitář a větev `main`.
5. Jako **Main file path** nastavte `app.py` a aplikaci nasaďte.
6. Při prvním spuštění se stáhne český model Stanza. Může to trvat déle; následné spuštění v rámci běžící instance využívá cache.

Streamlit automaticky instaluje závislosti z `requirements.txt`. Není potřeba Windows BAT ani instalace na počítači návštěvníka.

## Technické závislosti

- Stanza: běží v cloudové instanci aplikace; české modely se při startu stáhnou.
- MorphoDiTa: aplikace volá veřejnou online službu LINDAT. Bez dostupnosti služby analýza neproběhne.
- Výpočetní jádro `LUMP14_aplikace.py`, 14 indexů, váhy, Youdenovy hranice a P2 nebyly při převodu rozhraní měněny.
- Provoz ve Streamlit Community Cloud závisí na dostupné paměti a dalších limitech hostingu; první nasazení je třeba skutečně otestovat.

## Lokální kontrola

```bash
pip install -r requirements.txt
streamlit run app.py
python -m unittest test_rozhodovani.py
```

## Obsah

- `app.py` – české grafické rozhraní a inicializace modelů v cloudu
- `LUMP14_aplikace.py` – rozhodovací a analytické jádro
- `FIC_SCORE_list.txt`, `PUB_SCORE_list.txt` – lexikální zdroje
- `test_rozhodovani.py` – testy rozhodovacího jádra

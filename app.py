"""České návštěvnické rozhraní LUMP-14; rozhodovací jádro je v LUMP14_aplikace.py."""
from __future__ import annotations
import json
import streamlit as st
import stanza
import LUMP14_aplikace as lump

st.set_page_config(page_title='LUMP-14 | Noc vědy', page_icon='🔎', layout='centered')
st.markdown('''<style>
.block-container{max-width:850px;padding-top:2rem} h1{letter-spacing:-.035em}
.result{border-radius:18px;padding:1.5rem 1.7rem;margin:1.2rem 0;border:1px solid #ddd}
.green{background:#e7f4eb;color:#164b2b;border-color:#a7d8b5}
.red{background:#fcebea;color:#812922;border-color:#e8b4ae}
.neutral{background:#f0f2f5;color:#333}
.result .big{font-size:2.4rem;font-weight:800;line-height:1.2}
.result .small{font-size:1.05rem;margin-top:.4rem}
</style>''', unsafe_allow_html=True)

NAMES = {
 'conj_rel':'Spojky', 'noun_rel':'Podstatná jména', 'pub_score':'Slovní zásoba typická pro publicistiku',
 'pron_rel':'Zájmena', 'prep_rel':'Předložky', 'num_rel':'Číslovky',
 'fic_score':'Slovní zásoba typická pro beletrii', 'MHD':'Hloubka větné stavby',
 'adv_rel':'Příslovce', 'MDD':'Délka větných vazeb', 'dem_pron_rel':'Ukazovací zájmena',
 'pers_pron_rel':'Osobní zájmena', 'part_rel':'Částice', 'dat_rel':'Třetí pád',
}
DESCRIPTIONS = {
 'conj_rel':'Vyšší zastoupení spojek', 'noun_rel':'Vyšší zastoupení podstatných jmen',
 'pub_score':'Vyšší zastoupení slovní zásoby typické pro publicistiku',
 'pron_rel':'Vyšší zastoupení zájmen', 'prep_rel':'Vyšší zastoupení předložek',
 'num_rel':'Vyšší zastoupení číslovek', 'fic_score':'Vyšší zastoupení slovní zásoby typické pro beletrii',
 'MHD':'Větší hloubka větné stavby', 'adv_rel':'Vyšší zastoupení příslovcí',
 'MDD':'Delší větné vazby', 'dem_pron_rel':'Vyšší podíl ukazovacích zájmen mezi zájmeny',
 'pers_pron_rel':'Vyšší podíl osobních zájmen mezi zájmeny',
 'part_rel':'Vyšší zastoupení částic', 'dat_rel':'Vyšší podíl třetího pádu mezi pádově označenými slovy',
}

@st.cache_resource(show_spinner=False)
def resources():
    fic = lump.load_lexicon('FIC_SCORE_list.txt')
    pub = lump.load_lexicon('PUB_SCORE_list.txt')
    # Streamlit Community Cloud starts with a clean filesystem: download Czech models on first boot.
    # Cached resource prevents repeated initialization during Streamlit reruns.
    processors = 'tokenize,mwt,pos,lemma,depparse'
    stanza.download('cs', processors=processors, verbose=False)
    pipeline = stanza.Pipeline(lang='cs', processors=processors,
                               use_gpu=False, verbose=False, download_method=None)
    return fic, pub, pipeline

def fmt(value, places=6):
    return '—' if value is None else f'{value:.{places}f}'.replace('.', ',')

st.title('LUMP-14')
st.caption('Jazyk pod lupou · Noc vědy 2026')
st.write('Vložte český článek a podívejte se, jaké jazykové znaky v něm rozpozná lingvistický model.')
mode = st.radio('Jak chcete článek vložit?', ['Vložit text', 'Nahrát soubor TXT'], horizontal=True)
if mode == 'Vložit text':
    article = st.text_area('Text článku', height=250, placeholder='Sem vložte celý článek…')
else:
    upload = st.file_uploader('Vyberte soubor TXT (UTF-8)', type=['txt'])
    article = ''
    if upload is not None:
        try:
            article = upload.getvalue().decode('utf-8-sig')
            st.caption(f'Načteno znaků: {len(article):,}'.replace(',', ' '))
        except UnicodeDecodeError:
            st.error('Soubor není ve formátu UTF-8. Uložte jej jako UTF-8 a nahrajte znovu.')

if st.button('Analyzovat článek', type='primary', use_container_width=True):
    if not article.strip():
        st.warning('Nejprve vložte text článku.')
    else:
        try:
            with st.spinner('Analyzuji jazykové znaky článku…'):
                fic, pub, pipeline = resources()
                result = lump.analyze(article, pipeline, fic, pub)
            st.session_state['lump_result'] = result
            st.session_state['lump_input'] = article
        except Exception as exc:
            st.session_state.pop('lump_result', None)
            st.error('Analýzu se nepodařilo dokončit. Zkontrolujte připojení k internetu (MorphoDiTa), lokální model Stanza a zkuste to znovu.')
            with st.expander('Technické podrobnosti chyby'):
                st.code(f'{type(exc).__name__}: {exc}')

result = st.session_state.get('lump_result')
if result:
    r = result['result']
    active = [x for x in r['features'] if x['active']]
    green = [x for x in active if x['favored'] == 'SOUND']
    red = [x for x in active if x['favored'] == 'FLAWED']
    if r['prediction'] == 'SOUND':
        css, title, subtitle = 'green', '🟢 ZELENÁ', 'Jazykové znaky důvěryhodnějších článků'
    elif r['prediction'] == 'FLAWED':
        css, title, subtitle = 'red', '🔴 ČERVENÁ', 'Jazykové znaky problematických článků'
    else:
        css, title, subtitle = 'neutral', '⚪ NEDOSTATEK SIGNÁLŮ', 'Pro vyhodnocení jsou potřeba alespoň tři aktivní jazykové znaky.'
    st.markdown(f'<div class="result {css}"><div class="big">{title}</div><div class="small">{subtitle}</div></div>', unsafe_allow_html=True)
    a, b, c = st.columns(3)
    a.metric('Zelené signály', len(green))
    b.metric('Červené signály', len(red))
    c.metric('Aktivní znaky celkem', r['active_n'])
    st.subheader('Co model v článku rozpoznal?')
    if active:
        for row in active:
            symbol = '🟢' if row['favored'] == 'SOUND' else '🔴'
            st.write(f"{symbol} {DESCRIPTIONS[row['feature']]}")
    else:
        st.write('Žádný z příznaků nepřekročil svou hranici.')
    st.info('LUMP hodnotí jazykové charakteristiky, nikoli pravdivost informací. Zelená ani červená není ověřením jednotlivých tvrzení.')
    with st.expander('Technický protokol · všech 14 příznaků'):
        st.write('Skóre je vážený jazykový index, nikoli pravděpodobnost ani procento pravdivosti.')
        st.write(f"**Skóre:** {fmt(r['score'], 12)} · **Rozhodovací hranice P2:** {fmt(r['threshold'], 12)}")
        st.write(f"**Váha červených signálů:** {fmt(r['positive_weight'], 9)} · **Váha zelených signálů:** {fmt(r['negative_weight'], 9)}")
        rows = [{'Index': row['feature'], 'Název': NAMES[row['feature']], 'Hodnota': fmt(row['value'], 9),
                 'Youdenova hranice': fmt(row['cutoff'], 9), 'Váha': fmt(row['weight'], 9),
                 'Směr': 'Červená' if row['favored']=='FLAWED' else 'Zelená',
                 'Aktivní': 'Ano' if row['active'] else 'Ne'} for row in r['features']]
        st.dataframe(rows, hide_index=True, use_container_width=True)
        st.caption(f"Stanza: {result['syntax_engine']} · MorphoDiTa: {result['morphology_model']} · Počet vět: {result['diagnostics']['sentence_n']}")
        st.download_button('Stáhnout technický protokol (JSON)',
            data=json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False),
            file_name='lump14_vysledek.json', mime='application/json')

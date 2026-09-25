"""České návštěvnické rozhraní LUMP-14; rozhodovací jádro je v LUMP14_aplikace.py."""
from __future__ import annotations
import json
import threading
import requests
import streamlit as st
import stanza
import LUMP14_aplikace as lump

MAX_CHARS = 12000  # ochrana cloudového prostředí; nejde o parametr modelu
QUEUE_WAIT_SECONDS = 30

st.set_page_config(page_title='LUMP-14 | Noc vědy', page_icon='🔎', layout='centered')
st.markdown('''<style>
:root { --lump-ink:#101923; --lump-steel:#34495d; --lump-green:#248554; --lump-red:#b65b55; }
.block-container {max-width:850px;padding-top:1.6rem;padding-bottom:4rem}
h1 {letter-spacing:-.045em;font-weight:800!important}
[data-testid="stAppViewContainer"] {background:linear-gradient(180deg,rgba(114,142,166,.07),transparent 340px)}
.lump-hero {background:#101923;color:#f4f7fa;border:1px solid #344455;border-radius:17px;padding:1.45rem 1.65rem 1.25rem;margin-bottom:1.25rem;position:relative;overflow:hidden}
.lump-hero:after {content:"";position:absolute;right:-48px;top:-85px;width:245px;height:245px;border:1px solid #314457;border-radius:50%;box-shadow:0 0 0 31px #101923,0 0 0 32px #26394a,0 0 0 65px #101923,0 0 0 66px #26394a;opacity:.6;pointer-events:none}
.lump-hero .eyebrow {font:600 .7rem/1.4 ui-monospace,SFMono-Regular,Consolas,monospace;letter-spacing:.15em;color:#a4bacd;position:relative;z-index:1}
.lump-hero .brand {font-size:clamp(2.6rem,8vw,4.2rem);font-weight:850;letter-spacing:-.07em;line-height:1.14;margin:.75rem 0 .25rem;position:relative;z-index:1}
.lump-hero .tagline {font-size:.98rem;color:#c4d2df;position:relative;z-index:1}
.lump-bars {display:grid;grid-template-columns:repeat(14,1fr);gap:5px;margin-top:1.5rem;position:relative;z-index:1}
.lump-bars span {height:4px;background:#45576b;border-radius:3px}.lump-bars span:nth-child(-n+5){background:#69c7a0}.lump-bars span:nth-child(n+6):nth-child(-n+9){background:#d77c74}
.lump-hero .foot {display:flex;justify-content:space-between;gap:12px;margin-top:.65rem;font:500 .64rem ui-monospace,Consolas,monospace;letter-spacing:.09em;color:#91a9bc;position:relative;z-index:1}
.lump-section {font:700 .72rem ui-monospace,Consolas,monospace;letter-spacing:.12em;color:#72869a;border-bottom:1px solid rgba(128,149,167,.28);padding-bottom:.6rem;margin:1.35rem 0 .9rem}
.result {border-radius:14px;padding:1.45rem 1.55rem;margin:1rem 0;border:1px solid #ddd;border-left:6px solid;box-shadow:0 9px 30px rgba(16,25,35,.045)}
.green {background:#eaf5ee;color:#175c39;border-color:#a7d8b5;border-left-color:#248554}
.red {background:#fbefee;color:#812922;border-color:#e8b4ae;border-left-color:#b65b55}
.neutral {background:#f0f2f5;color:#333;border-color:#c9d2da;border-left-color:#7e8c99}
.result .big {font-size:clamp(1.8rem,5vw,2.45rem);font-weight:800;line-height:1.2;letter-spacing:-.04em}
.result .small {font-size:1.04rem;margin-top:.45rem}
.lump-feature {display:flex;align-items:center;gap:.85rem;border:1px solid rgba(128,149,167,.25);border-radius:9px;padding:.72rem .85rem;margin:.42rem 0;background:rgba(128,149,167,.035)}
.lump-feature .dot {width:8px;height:8px;border-radius:50%;flex:none}.lump-feature .dot.green-dot{background:#248554}.lump-feature .dot.red-dot{background:#b65b55}
.lump-feature .description {flex:1;min-width:0}.lump-feature .code {font:500 .7rem ui-monospace,Consolas,monospace;color:#8493a1;white-space:nowrap}
[data-testid="stMetric"] {border:1px solid rgba(128,149,167,.27);border-radius:10px;padding:.75rem .9rem;background:rgba(128,149,167,.035)}
[data-testid="stMetricValue"] {font-variant-numeric:tabular-nums;letter-spacing:-.05em}
[data-testid="stTextArea"] textarea {border-radius:10px;border-color:#9eafbd;font-size:.96rem}
.stButton button[kind="primary"] {background:#172536;border:1px solid #34495d;border-radius:9px;min-height:3.05rem;font-weight:700;letter-spacing:.01em}
.stButton button[kind="primary"]:hover {background:#34495d;border-color:#536c83}
[data-testid="stExpander"] {border-radius:11px;border-color:rgba(128,149,167,.4)}
@media(max-width:600px){.lump-hero{padding:1.2rem}.lump-feature .code{font-size:.61rem}.result{padding:1.15rem}}
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
    # Sdílená pipeline: v jednom okamžiku probíhá nejvýše jedna analýza.
    # Lock se ukládá společně s cachovaným modelem napříč relacemi.
    return fic, pub, pipeline, threading.Lock()

def fmt(value, places=6):
    return '—' if value is None else f'{value:.{places}f}'.replace('.', ',')

st.markdown('''<div class="lump-hero">
<div class="eyebrow">LINGUISTIC ANALYSIS / 014</div>
<div class="brand">LUMP-14</div>
<div class="tagline">Jazyk pod lupou · Noc vědy 2026</div>
<div class="lump-bars">''' + '<span></span>' * 14 + '''</div>
<div class="foot"><span>14 JAZYKOVÝCH PŘÍZNAKŮ</span><span>LUMP / 2026</span></div>
</div>''', unsafe_allow_html=True)
st.markdown('<div class="lump-section">01 / VSTUPNÍ TEXT</div>', unsafe_allow_html=True)
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

st.caption(f'Limit vstupu: {MAX_CHARS:,} znaků (přibližně několik stran textu).'.replace(',', ' '))
if st.button('Analyzovat článek', type='primary', use_container_width=True):
    if not article.strip():
        st.warning('Nejprve vložte text článku.')
    elif len(article) > MAX_CHARS:
        st.warning(f'Text je příliš dlouhý ({len(article):,} znaků). Zkraťte jej na nejvýše {MAX_CHARS:,} znaků.'.replace(',', ' '))
        st.session_state.pop('lump_result', None)
    else:
        st.session_state.pop('lump_result', None)
        try:
            with st.spinner('Připravuji jazykové modely… Při prvním spuštění to může chvíli trvat.'):
                fic, pub, pipeline, analysis_lock = resources()
            with st.spinner('Čekám na volnou analýzu…'):
                acquired = analysis_lock.acquire(timeout=QUEUE_WAIT_SECONDS)
            if not acquired:
                st.warning('Aplikace právě zpracovává další článek. Zkuste analýzu za chvíli znovu.')
            else:
                try:
                    with st.spinner('Analyzuji článek: MorphoDiTa a syntaktická analýza Stanzou…'):
                        result = lump.analyze(article, pipeline, fic, pub)
                    st.session_state['lump_result'] = result
                    st.session_state['lump_input'] = article
                finally:
                    analysis_lock.release()
        except requests.exceptions.Timeout:
            st.error('Jazyková služba MorphoDiTa neodpověděla včas. Zkuste analýzu znovu za chvíli.')
        except requests.exceptions.RequestException:
            st.error('Nepodařilo se spojit s jazykovou službou MorphoDiTa. Zkontrolujte připojení nebo to zkuste později.')
        except Exception as exc:
            st.error('Analýzu se nepodařilo dokončit. Zkuste to prosím znovu.')
            with st.expander('Technické podrobnosti chyby'):
                st.code(f'{type(exc).__name__}: {exc}')

# Starý výsledek se nesmí vydávat za analýzu nově vloženého článku.
result = st.session_state.get('lump_result') if st.session_state.get('lump_input') == article else None
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
    st.markdown('<div class="lump-section">02 / VÝSLEDEK ANALÝZY</div>', unsafe_allow_html=True)
    a, b, c = st.columns(3)
    a.metric('Zelené signály', len(green))
    b.metric('Červené signály', len(red))
    c.metric('Aktivní znaky celkem', r['active_n'])
    st.markdown('<div class="lump-section">03 / JAZYKOVÉ PŘÍZNAKY</div>', unsafe_allow_html=True)
    st.subheader('Co model v článku rozpoznal?')
    if active:
        for row in active:
            symbol = '🟢' if row['favored'] == 'SOUND' else '🔴'
            from html import escape
            color = 'green-dot' if row['favored'] == 'SOUND' else 'red-dot'
            st.markdown(f'<div class="lump-feature"><span class="dot {color}"></span><span class="description">{escape(DESCRIPTIONS[row["feature"]])}</span><span class="code">{escape(row["feature"])}</span></div>', unsafe_allow_html=True)
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

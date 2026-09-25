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
/* Jednotná typografie: systémové bezpatkové písmo pro všechny prvky. */
:root { --lump-ink:#172536; --lump-green:#248554; --lump-red:#b65b55; --lump-muted:#687787; --lump-line:#d7dfe5; --lump-surface:#f4f6f8; --lump-font:system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif; }
html,body,[data-testid="stAppViewContainer"],.stApp,button,input,textarea,select,[data-testid="stMetric"],.lump-hero,.lump-scale,.lump-feature {font-family:var(--lump-font)!important}
.block-container {max-width:850px;padding-top:1.6rem;padding-bottom:4rem}
h1 {letter-spacing:-.045em;font-weight:800!important}
[data-testid="stAppViewContainer"] {background:var(--lump-surface)}
.lump-hero {background:var(--lump-ink);color:#fff;border:1px solid var(--lump-ink);border-radius:17px;padding:1.45rem 1.65rem 1.25rem;margin-bottom:1.25rem;position:relative;overflow:hidden}
.lump-hero:after {content:"";position:absolute;right:-48px;top:-85px;width:245px;height:245px;border:1px solid #ffffff25;border-radius:50%;box-shadow:0 0 0 31px var(--lump-ink),0 0 0 32px #ffffff25,0 0 0 65px var(--lump-ink),0 0 0 66px #ffffff25;pointer-events:none}
.lump-hero .eyebrow {font-size:.7rem;font-weight:650;letter-spacing:.15em;color:#ffffffb8;position:relative;z-index:1}
.lump-hero .brand {font-size:clamp(2.6rem,8vw,4.2rem);font-weight:850;letter-spacing:-.07em;line-height:1.14;margin:.75rem 0 .25rem;position:relative;z-index:1}
.lump-hero .tagline {font-size:.98rem;color:#ffffffd6;position:relative;z-index:1}
.lump-bars {display:grid;grid-template-columns:repeat(14,1fr);gap:5px;margin-top:1.5rem;position:relative;z-index:1}
.lump-bars span {height:4px;background:#ffffff80;border-radius:3px}
.lump-hero .foot {display:flex;justify-content:space-between;gap:12px;margin-top:.65rem;font-size:.64rem;font-weight:600;letter-spacing:.09em;color:#ffffffb8;position:relative;z-index:1}
.lump-section {font-size:.72rem;font-weight:700;letter-spacing:.12em;color:var(--lump-muted);border-bottom:1px solid var(--lump-line);padding-bottom:.6rem;margin:1.35rem 0 .9rem}
.result {border-radius:14px;padding:1.45rem 1.55rem;margin:1rem 0;border:1px solid var(--lump-line);border-left:6px solid;box-shadow:0 9px 30px #1725360b}
.green {background:#24855412;color:var(--lump-green);border-left-color:var(--lump-green)}
.red {background:#b65b5512;color:var(--lump-red);border-left-color:var(--lump-red)}
.neutral {background:var(--lump-surface);color:var(--lump-ink);border-left-color:var(--lump-muted)}
.result .big {font-size:clamp(1.8rem,5vw,2.45rem);font-weight:800;line-height:1.2;letter-spacing:-.04em}
.result .small {font-size:1.04rem;margin-top:.45rem}
.lump-feature {display:flex;align-items:center;gap:.85rem;border:1px solid var(--lump-line);border-radius:9px;padding:.72rem .85rem;margin:.42rem 0;background:#fff}
.lump-feature .dot {width:8px;height:8px;border-radius:50%;flex:none}.lump-feature .dot.green-dot{background:var(--lump-green)}.lump-feature .dot.red-dot{background:var(--lump-red)}
.lump-feature .description {flex:1;min-width:0}.lump-feature .code {font-size:.7rem;font-weight:600;color:var(--lump-muted);white-space:nowrap}
.lump-scale {border:1px solid var(--lump-line);border-radius:12px;padding:1.1rem 1.25rem 1.2rem;margin:.65rem 0 1.15rem;background:#fff}
.lump-scale-top {display:flex;justify-content:space-between;align-items:end;gap:1rem;flex-wrap:wrap}
.lump-scale-label {font-size:.68rem;font-weight:700;letter-spacing:.11em;color:var(--lump-muted)}
.lump-scale-value {font-size:1.75rem;font-weight:750;letter-spacing:-.055em;font-variant-numeric:tabular-nums;margin-top:.2rem}
.lump-scale-threshold {font-size:.78rem;font-weight:600;color:var(--lump-muted)}
.lump-scale-track {position:relative;height:13px;border-radius:7px;background:linear-gradient(to right,var(--lump-green) 0%,var(--lump-green) var(--p2),var(--lump-red) var(--p2),var(--lump-red) 100%);margin:1.55rem 0 1.1rem}
.lump-scale-track .threshold {position:absolute;left:var(--p2);height:29px;top:-8px;width:2px;background:var(--lump-ink);transform:translateX(-50%)}
.lump-scale-track .needle {position:absolute;left:var(--score);top:-7px;width:14px;height:14px;background:#fff;border:3px solid var(--lump-ink);border-radius:50%;transform:translateX(-50%);box-shadow:0 1px 4px #17253655}
.lump-scale-ticks,.lump-scale-zones {display:flex;justify-content:space-between;gap:8px;font-size:.72rem;font-weight:600;color:var(--lump-muted)}
.lump-scale-zones {margin-top:.65rem;font-size:.67rem;letter-spacing:.06em}.lump-scale-zones span:first-child{color:var(--lump-green)}.lump-scale-zones span:last-child{color:var(--lump-red)}
.lump-scale-off {height:13px;border-radius:7px;background:repeating-linear-gradient(90deg,var(--lump-muted) 0,var(--lump-muted) 12px,var(--lump-line) 12px,var(--lump-line) 18px);margin:1.5rem 0 .9rem;opacity:.65}
[data-testid="stMetric"] {border:1px solid var(--lump-line);border-radius:10px;padding:.75rem .9rem;background:#fff}
[data-testid="stMetricValue"] {font-variant-numeric:tabular-nums;letter-spacing:-.05em}
[data-testid="stTextArea"] textarea {border-radius:10px;border-color:var(--lump-line);font-size:.96rem}
.stButton button[kind="primary"] {background:var(--lump-ink);border:1px solid var(--lump-ink);border-radius:9px;min-height:3.05rem;font-weight:700;letter-spacing:.01em}
.stButton button[kind="primary"]:hover {background:var(--lump-ink);border-color:var(--lump-muted);filter:brightness(1.15)}
[data-testid="stExpander"] {border-radius:11px;border-color:var(--lump-line)}
@media(max-width:600px){.lump-hero{padding:1.2rem}.lump-feature .code{font-size:.61rem}.result{padding:1.15rem}}
</style>''', unsafe_allow_html=True)

NAMES = {
 'conj_rel':'Spojky', 'noun_rel':'Podstatná jména', 'pub_score':'Publicistická slovní zásoba',
 'pron_rel':'Zájmena', 'prep_rel':'Předložky', 'num_rel':'Číslovky',
 'fic_score':'Beletristická slovní zásoba', 'MHD':'Hloubka větného grafu',
 'adv_rel':'Příslovce', 'MDD':'Délka větných vazeb', 'dem_pron_rel':'Ukazovací zájmena',
 'pers_pron_rel':'Osobní zájmena', 'part_rel':'Částice', 'dat_rel':'Třetí pád',
}
DESCRIPTIONS = {
 'conj_rel':'Vyšší zastoupení spojek', 'noun_rel':'Vyšší zastoupení podstatných jmen',
 'pub_score':'Vyšší zastoupení publicistické slovní zásoby',
 'pron_rel':'Vyšší zastoupení zájmen', 'prep_rel':'Vyšší zastoupení předložek',
 'num_rel':'Vyšší zastoupení číslovek', 'fic_score':'Vyšší zastoupení beletristické slovní zásoby',
 'MHD':'Hlubší větný graf', 'adv_rel':'Vyšší zastoupení příslovcí',
 'MDD':'Delší větné vazby', 'dem_pron_rel':'Vyšší zastoupení ukazovacích zájmen',
 'pers_pron_rel':'Vyšší zastoupení osobních zájmen',
 'part_rel':'Vyšší zastoupení částic', 'dat_rel':'Vyšší podíl slov v třetím pádě',
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
<div class="tagline">Language-Use Manipulation Detector · Noc vědy 2026</div>
<div class="lump-bars">''' + '<span></span>' * 14 + '''</div>
<div class="foot"><span>14 JAZYKOVÝCH RYSŮ</span><span>LUMP / 2026</span></div>
</div>''', unsafe_allow_html=True)
st.markdown('<div class="lump-section">01 / VSTUPNÍ TEXT</div>', unsafe_allow_html=True)
st.write('Vložte český text a podívejte se, jaké jazykové rysy v něm lingvistický model rozpozná.')
mode = st.radio('Jak chcete text vložit?', ['Vložit text', 'Nahrát soubor TXT'], horizontal=True)
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
        css, title, subtitle = 'green', '🟢 ZELENÁ', 'Jazyk standardní žurnalistiky'
    elif r['prediction'] == 'FLAWED':
        css, title, subtitle = 'red', '🔴 ČERVENÁ', 'Rizikové jazykové chování'
    else:
        css, title, subtitle = 'neutral', '⚪ NEDOSTATEK SIGNÁLŮ', 'Pro vyhodnocení jsou potřeba alespoň tři aktivní jazykové rysy.'
    st.markdown(f'<div class="result {css}"><div class="big">{title}</div><div class="small">{subtitle}</div></div>', unsafe_allow_html=True)
    # Vizuální škála používá pouze existující skóre a P2; nezasahuje do rozhodování.
    if r['score'] is not None and r['prediction'] in ('SOUND', 'FLAWED'):
        score = max(-1.0, min(1.0, float(r['score'])))
        threshold = max(-1.0, min(1.0, float(r['threshold'])))
        score_pct = (score + 1.0) * 50.0
        p2_pct = (threshold + 1.0) * 50.0
        st.markdown(f'''<div class="lump-scale" role="img" aria-label="Jazykové skóre LUMP-14: {fmt(r['score'], 3)}; rozhodovací hranice P2: {fmt(r['threshold'], 3)}; rozsah od minus jedné do plus jedné.">
<div class="lump-scale-top"><div><div class="lump-scale-label">JAZYKOVÉ SKÓRE LUMP-14</div><div class="lump-scale-value">{fmt(r['score'], 3)}</div></div><div class="lump-scale-threshold">P2 = {fmt(r['threshold'], 3)}</div></div>
<div class="lump-scale-track" style="--p2:{p2_pct:.8f}%;--score:{score_pct:.8f}%"><span class="threshold" title="Rozhodovací hranice P2"></span><span class="needle" title="Skóre článku"></span></div>
<div class="lump-scale-ticks"><span>−1</span><span>0</span><span>+1</span></div>
<div class="lump-scale-zones"><span>ZELENÁ OBLAST</span><span>ČERVENÁ OBLAST</span></div></div>''', unsafe_allow_html=True)
    else:
        st.markdown('''<div class="lump-scale"><div class="lump-scale-label">JAZYKOVÉ SKÓRE LUMP-14</div><div class="lump-scale-off"></div><div class="lump-scale-ticks"><span>−1</span><span>0</span><span>+1</span></div></div>''', unsafe_allow_html=True)
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

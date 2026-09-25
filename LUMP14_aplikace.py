#!/usr/bin/env python3
"""LUMP-14 — demonstrační klasifikátor pro Noc vědy 2026.

Pouze práh P2; bez COFCO, UDPipe a šedé zóny.
Použití: python LUMP14_aplikace.py --text clanek.txt [--json vysledek.json]
         python LUMP14_aplikace.py --stdin
Závislosti: requests, stanza; lokální model Stanza cs a oba přiložené lexikony.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
import math
import re
from pathlib import Path
import sys
import requests
import stanza

HERE = Path(__file__).resolve().parent
MODEL = 'czech-morfflex2.0-pdtc1.0-220710'
MORPHODITA_URL = 'https://lindat.mff.cuni.cz/services/morphodita/api/tag'
P2 = 0.39055351875803324
MIN_ACTIVE = 3
# Úplné (nezaokrouhlené) váhy a individuální prahy z analytického balíčku LUMP-14.
# (váha, podporovaná třída, práh)
FEATURES = {
    'conj_rel': (0.43037633423639376, 'FLAWED', 0.063),
    'noun_rel': (0.34864610585766376, 'SOUND', 0.284),
    'pub_score': (0.3372821302783411, 'SOUND', 0.0074626865671641),
    'pron_rel': (0.33434502793290855, 'FLAWED', 0.073),
    'prep_rel': (0.29823201422826495, 'SOUND', 0.096),
    'num_rel': (0.29471463223650685, 'SOUND', 0.029),
    'fic_score': (0.2903739484992156, 'FLAWED', 0.0003703703703703),
    'MHD': (0.27131087829427525, 'FLAWED', 2.87741935483871),
    'adv_rel': (0.23167708778049523, 'FLAWED', 0.052),
    'MDD': (0.22535558663439326, 'FLAWED', 2.68307967770815),
    'dem_pron_rel': (0.22031369751451368, 'FLAWED', 0.201),
    'pers_pron_rel': (0.2101655348072382, 'SOUND', 0.348),
    'part_rel': (0.20945859335390749, 'FLAWED', 0.006),
    'dat_rel': (0.20498867243091046, 'FLAWED', 0.043),
}
PERSONAL = set('0567HP')
DEMONSTRATIVE = {'D'}

def load_lexicon(filename: str) -> set[str]:
    path = HERE / filename
    if not path.is_file():
        raise FileNotFoundError(f'Chybí lexikon: {path}')
    return {line.strip() for line in path.read_text(encoding='utf-8-sig').splitlines() if line.strip()}


def morphodita_tag(text: str) -> list[dict]:
    # Match original model and vertical output. Sending data as multipart is supported by API.
    response = requests.post(MORPHODITA_URL,
        files={'data': ('text.txt', text.encode('utf-8'), 'text/plain')},
        data={'model': MODEL, 'output': 'vertical'}, timeout=180)
    response.raise_for_status()
    vertical = response.json().get('result')
    if not vertical:
        raise RuntimeError('MorphoDiTa nevrátila anotaci.')
    words = []
    for line in vertical.splitlines():
        cols = line.split('\t')
        if len(cols) >= 3:
            tag = cols[2]
            if len(tag) >= 5:
                words.append({'form': cols[0], 'lemma': cols[1], 'tag': tag})
    if not words:
        raise RuntimeError('Ve výstupu MorphoDiTy nebyly nalezeny tokeny.')
    return words


def morphology(words: list[dict]) -> dict[str, float | None]:
    """Mirror MorphoDita_analyza1.py, including 3-decimal rounding."""
    total = len(words)
    pos = Counter(w['tag'][0] for w in words)
    cases = [w['tag'][4] for w in words if w['tag'][4] not in '-X%']
    pron = [w['tag'][1] for w in words if w['tag'][0] == 'P']
    # Original analysis counts all annotated tokens, including punctuation.
    def rel(n, d): return round(n / d, 3) if d else None
    return {
        'conj_rel': rel(pos['J'], total),
        'noun_rel': rel(pos['N'], total),
        'pron_rel': rel(pos['P'], total),
        'prep_rel': rel(pos['R'], total),
        'num_rel': rel(pos['C'], total),
        'adv_rel': rel(pos['D'], total),
        'part_rel': rel(pos['T'], total),
        'dat_rel': rel(Counter(cases)['3'], len(cases)),
        'dem_pron_rel': rel(sum(p in DEMONSTRATIVE for p in pron), len(pron)),
        'pers_pron_rel': rel(sum(p in PERSONAL for p in pron), len(pron)),
    }


def syntax(text: str, pipeline) -> tuple[dict[str, float | None], dict[str, int]]:
    """MDD/MHD from syntax_novy_voldemorf(1).py (same filtering and depths)."""
    document = pipeline(text)
    distances, depths = [], []
    sentence_n = 0
    def is_word(w): return w.upos != 'PUNCT' and w.deprel != 'punct'
    def depth(wid, byid, cache, path=None):
        if wid in cache: return cache[wid]
        path = set() if path is None else path
        if wid in path or wid not in byid:
            cache[wid] = None
            return None
        w = byid[wid]
        if w.head == 0:
            cache[wid] = 0
            return 0
        parent = byid.get(int(w.head)) if w.head is not None else None
        if parent is None:
            cache[wid] = None
            return None
        val = depth(int(parent.id), byid, cache, path | {wid})
        cache[wid] = val + 1 if val is not None else None
        return cache[wid]
    for sent in document.sentences:
        words = [w for w in sent.words if isinstance(w.id, int)]
        if not words: continue
        sentence_n += 1
        byid = {int(w.id): w for w in words}
        cache = {}
        for w in words:
            if not is_word(w) or w.head == 0 or w.deprel == 'root': continue
            parent = byid.get(int(w.head)) if w.head is not None else None
            if parent is None or not is_word(parent): continue
            distances.append(abs(int(w.id) - int(w.head)))
            d = depth(int(w.id), byid, cache)
            if d is not None: depths.append(d)
    mean = lambda vals: sum(vals) / len(vals) if vals else None
    return {'MDD': mean(distances), 'MHD': mean(depths)}, {'sentence_n': sentence_n, 'dependency_n': len(distances)}


LEMMA_HOMONYM = re.compile(r"(?:-\d+|`\d+)$")


def clean_lemma(lemma: str) -> str:
    base = lemma.split('_', 1)[0]
    return LEMMA_HOMONYM.sub('', base)


def is_lexical_token(word: dict) -> bool:
    # MorphoDiTa positional tag Z denotes punctuation; exclude it from
    # lexical denominators and COFCO coverage, not from morphology features.
    return not word['tag'].startswith('Z')


def lexical(words: list[dict], fic: set[str], pub: set[str]):
    """FIC/PUB: původní MorphoDiTa, odstranění technických sufixů a interpunkce."""
    lexical_words = [w for w in words if is_lexical_token(w)]
    lemmas = [clean_lemma(w['lemma']) for w in lexical_words]
    total = len(lemmas)
    if not total:
        raise ValueError('Text neobsahuje lexikální tokeny.')
    return ({'fic_score': sum(l in fic for l in lemmas) / total,
             'pub_score': sum(l in pub for l in lemmas) / total},
            {'lexical_token_n': total, 'punctuation_excluded_n': len(words) - total})

def score(features: dict[str, float | None]) -> dict:
    rows = []
    positive = negative = 0.0
    for name, (weight, favored, cutoff) in FEATURES.items():
        val = features.get(name)
        active = val is not None and math.isfinite(val) and val >= cutoff
        contribution = (weight if favored == 'FLAWED' else -weight) if active else 0.0
        positive += max(contribution, 0.0)
        negative += max(-contribution, 0.0)
        rows.append({'feature': name, 'value': val, 'cutoff': cutoff,
                     'favored': favored, 'weight': weight,
                     'active': active, 'contribution': contribution})
    active_n = sum(r['active'] for r in rows)
    value = (positive - negative) / (positive + negative) if active_n >= MIN_ACTIVE else None
    prediction = None if value is None else ('FLAWED' if value >= P2 else 'SOUND')
    return {'score': value, 'active_n': active_n,
            'positive_weight': positive, 'negative_weight': negative,
            'threshold': P2, 'threshold_name': 'P2_balanced',
            'prediction': prediction, 'features': rows}


def analyze(text: str, pipeline, fic: set[str], pub: set[str]) -> dict:
    if not text.strip():
        raise ValueError('Vstupní text je prázdný.')
    words = morphodita_tag(text)
    morph = morphology(words)
    syn, syn_meta = syntax(text, pipeline)
    lex, lex_meta = lexical(words, fic, pub)
    all_features = {**morph, **syn, **lex}
    if set(all_features) != set(FEATURES):
        raise RuntimeError('Neshoda mezi vypočtenými a očekávanými 14 indexy.')
    return {'model': 'LUMP-14 Noc vědy 2026', 'morphology_model': MODEL,
            'syntax_engine': 'Stanza Czech', 'features': all_features,
            'diagnostics': {**syn_meta, **lex_meta}, 'result': score(all_features),
            'warning': 'Klasifikace jazykových charakteristik, nikoli ověřování pravdivosti tvrzení.'}


def main() -> None:
    parser = argparse.ArgumentParser(description='LUMP-14: český text, pouze P2')
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--text', type=Path, help='UTF-8 textový soubor')
    source.add_argument('--stdin', action='store_true', help='Text ze standardního vstupu')
    parser.add_argument('--json', type=Path, help='Uložit JSON do souboru')
    parser.add_argument('--stanza-dir', type=Path, help='Adresář lokálních modelů Stanza')
    args = parser.parse_args()
    text = args.text.read_text(encoding='utf-8-sig') if args.text else sys.stdin.read()
    if not text.strip():
        raise ValueError('Vstupní text je prázdný.')
    print('Načítám lexikony FIC/PUB…', file=sys.stderr)
    fic = load_lexicon('FIC_SCORE_list.txt')
    pub = load_lexicon('PUB_SCORE_list.txt')
    print('Inicializuji Stanzu…', file=sys.stderr)
    kwargs = dict(lang='cs', processors='tokenize,mwt,pos,lemma,depparse',
                  use_gpu=False, verbose=False, download_method=None)
    if args.stanza_dir:
        kwargs['dir'] = str(args.stanza_dir)
    pipeline = stanza.Pipeline(**kwargs)
    result = analyze(text, pipeline, fic, pub)
    output = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    print(output, end='')
    if args.json:
        args.json.write_text(output, encoding='utf-8')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, requests.RequestException) as exc:
        print(f'CHYBA: {exc}', file=sys.stderr)
        sys.exit(1)

"""Post hoc paired analysis of scope claims omitted by news sources."""
import argparse
import json
import random
from pathlib import Path
from statistics import mean

CONDITIONS = 'ABSC'
SEED = 16112026


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def percentile(sorted_values, q):
    index = (len(sorted_values) - 1) * q
    lower = int(index)
    return sorted_values[lower] + (index - lower) * (sorted_values[lower + 1] - sorted_values[lower])


def pair_stats(rows, comparison):
    differences = [row['rates']['C'] - row['rates'][comparison] for row in rows]
    rng = random.Random(SEED)
    draws = sorted(mean(rng.choices(differences, k=len(rows))) for _ in range(10_000))
    return {
        'difference': mean(differences),
        'lo95': percentile(draws, 0.025),
        'hi95': percentile(draws, 0.975),
        'positive_articles': sum(d > 0 for d in differences),
        'zero_articles': sum(d == 0 for d in differences),
        'negative_articles': sum(d < 0 for d in differences),
    }


def summarize(rows):
    require(bool(rows), 'Every slice must contain at least one eligible article')
    return {
        'articles': len(rows),
        'article_claims': sum(len(row['claim_ids']) for row in rows),
        'answer_claims_per_condition': sum(2 * len(row['claim_ids']) for row in rows),
        'rates': {cond: mean(r['rates'][cond] for r in rows) for cond in CONDITIONS},
        'claude_haiku': {cond: mean(r['by_reader']['claude-haiku'][cond] for r in rows) for cond in CONDITIONS},
        'qwen': {cond: mean(r['by_reader']['ollama:qwen3.5:9b'][cond] for r in rows) for cond in CONDITIONS},
        'C_minus_B': pair_stats(rows, 'B'),
        'C_minus_S': pair_stats(rows, 'S'),
    }


def verify_blind(inputs, crosswalk, independent, articles, cards):
    independent_by_id = {}
    n_claims = 0
    article_answers = {a['id']: (article, a) for article in articles for a in article['answers']}
    for batch in inputs:
        finding = batch['finding']
        expected_paper = cards[finding]['paper']
        thresholds = {c['id']: {k: c[k] for k in ('id', 'claim', 'counts_if', 'contradicted_if')} for c in cards[finding]['pool']}
        require(batch['paper'] == expected_paper and all(c == thresholds[c['id']] for c in batch['claims']), f'Wrong scorer rubric in {finding}')
        judgments = independent[finding]
        require([r['key'] for r in judgments] == [d['key'] for d in batch['docs']], f'Scorer output order differs for {finding}')
        for doc, score in zip(batch['docs'], judgments):
            alias = doc['key']
            answer_id = crosswalk[alias]['id']
            article, answer = article_answers[answer_id]
            expected = [c['id'] for c in cards[finding]['pool'] if c['side'] == 'scope' and c['id'] in cards[finding]['card'] and article['primary'][c['id']] == ('absent') and article['secondary'][c['id']] == 'absent']
            require(article['finding'] == finding and article['secondary_relevant'], f'Unsuitable source for {alias}')
            require(doc['claim_ids'] == expected and set(doc['claim_ids']) == set(score['claims']), f'Wrong judgment coverage for {alias}')
            require(doc['text'] == ' '.join(answer['text'].split()), f'Text differs for {alias}')
            for claim, (label, quote) in score['claims'].items():
                require(label in ('stated','absent','contradicted') and isinstance(quote,str), f'Invalid judgment for {alias}/{claim}')
                ok = quote == '' if label == 'absent' else bool(quote.strip()) and quote in doc['text'] and len(quote.split()) <= 25
                require(ok, f'Invalid evidence for {alias}/{claim}')
                n_claims += 1
            require(answer_id not in independent_by_id, f'Duplicate scorer output for {answer_id}')
            independent_by_id[answer_id] = score['claims']
    require(len(independent_by_id) == len(crosswalk), 'Crosswalk and blinded outputs differ')
    return independent_by_id, n_claims


def calculate(data, independent=False):
    cards = load(data / 'cards.json')
    articles = load(data / 'articles.json')
    deletion = load(data / 'deletions.json')
    require(len(articles) == 23 and len({a['id'] for a in articles}) == 23, 'Expected 23 distinct articles')
    alternate = {}
    n_independent = 0
    if independent:
        batch_paths = sorted((data / 'independent' / 'inputs').glob('*.json'))
        require(len(batch_paths) == 6, 'Expected six independent scorer batches')
        inputs = [dict(load(p), finding=p.stem) for p in batch_paths]
        crosswalk = load(data / 'independent' / 'crosswalk.json')
        judgments = {p.stem: load(data / 'independent' / 'scores' / p.name) for p in batch_paths}
        alternate, n_independent = verify_blind(inputs, crosswalk, judgments, articles, cards)
    lanes = {
        'primary_on_card': (True, False, False),
        'consensus_on_card': (True, True, False),
        'consensus_off_card': (False, True, False),
    }
    if independent:
        lanes['independent_consensus_on_card'] = (True, True, True)
    results = {}
    for lane, (on_card, consensus, rescore) in lanes.items():
        rows = []
        for art in articles:
            paper = cards[art['finding']]
            pool = {c['id']:c for c in paper['pool']}
            require(set(art['primary']) == set(art['secondary']) == set(pool), f'Incomplete source: {art["id"]}')
            require(len(art['answers']) == 8, f'Incomplete block for {art["id"]}')
            if consensus and not art['secondary_relevant']:
                continue
            claims = [
                c for c in pool if pool[c]['side'] == 'scope' and ((c in paper['card']) == on_card)
                and art['primary'][c] == 'absent' and (not consensus or art['secondary'][c] == 'absent')
            ]
            if not claims:
                continue
            by_reader = {}
            for answer in art['answers']:
                judgments = alternate[answer['id']] if rescore else answer['claims']
                values = by_reader.setdefault(answer['reader'], {})
                require(answer['cond'] not in values, 'Duplicated answer condition')
                values[answer['cond']] = mean(judgments[c][0] == 'stated' for c in claims)
            require(len(by_reader) == 2 and all(set(v) == set(CONDITIONS) for v in by_reader.values()), 'Incomplete reader conditions')
            rates = {cond: mean(reader[cond] for reader in by_reader.values()) for cond in CONDITIONS}
            rows.append({'id':art['id'], 'finding':art['finding'], 'claim_ids':claims,'rates':rates,'by_reader':by_reader})
        results[lane] = {'summary':summarize(rows), 'article_rates': rows}
    require(len(deletion) == 38 and len({r['id'] for r in deletion}) == 38, 'Wrong deletion case coverage')
    misses = [r for r in deletion if r['primary'] == 'stated']
    return {
        'article_count': len(articles),
        'answer_count': sum(len(a['answers']) for a in articles),
        'outcome_checks_independent': n_independent,
        'slices': results,
        'deletion_recheck': {'paired_deletions':len(deletion), 'haiku_stated':len(misses), 'both_stated':sum(r['secondary']=='stated' for r in misses)},
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path(__file__).parent / 'mechanism-data')
    parser.add_argument('--out', type=Path, default=Path('mechanism-results.json'))
    parser.add_argument('--independent', action='store_true')
    options = parser.parse_args()
    save(options.out, calculate(options.data, options.independent))

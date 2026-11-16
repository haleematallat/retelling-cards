"""Validate blind claims and calculate the matched closed-book follow-up."""
import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean


MODELS = {'openai-codex': 'OpenAI Codex', 'claude-sonnet': 'Claude Sonnet'}
SIDES = ('result', 'scope')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def check(condition, message):
    if not condition:
        raise ValueError(message)


def calculate(root):
    cards = read(root / 'cards.json')
    documents = read(root / 'crosswalk.json')
    rows = defaultdict(dict)
    evidence_count = 0
    for finding, paper in cards.items():
        if finding.startswith('_'):
            continue
        judgments = read(root / 'judgments' / f'{finding}.json')
        batch = read(root / 'blind_inputs' / f'{finding}.json')
        claims = {claim['id']: claim for claim in paper['pool']}
        claim_prompt = [{field: claim[field] for field in ('id', 'claim', 'counts_if', 'contradicted_if')} for claim in paper['pool']]
        check(batch['claims'] == claim_prompt and batch['paper'] == paper['paper'], f'Altered blind claim pool for {finding}')
        keys = [doc['key'] for doc in batch['docs']]
        expected = {key for key, doc in documents.items() if doc['finding'] == finding}
        check(len(keys) == 6 and len(expected) == 6 and set(keys) == expected, f'Wrong document coverage for {finding}')
        check([score['key'] for score in judgments] == keys, f'Wrong score order for {finding}')
        for item, score in zip(batch['docs'], judgments):
            key = item['key']
            doc = documents[key]
            norm = ' '.join(doc['text'].split()[:6000])
            check(norm == item['text'] == doc['scoring_text'], f'Altered text for {key}')
            check(type(score['relevant']) is bool and set(score['claims']) == set(claims), f'Wrong claim coverage for {key}')
            for claim_id, (label, quote) in score['claims'].items():
                check(label in ('stated', 'absent', 'contradicted') and isinstance(quote, str), f'Invalid label for {key}/{claim_id}')
                check((quote == '') if label == 'absent' else (quote.strip() and quote in norm and len(quote.split()) <= 25), f'Invalid quote for {key}/{claim_id}')
                evidence_count += bool(quote)
            check(doc['model'] in MODELS and doc['paraphrase'] in range(3), f'Invalid model or prompt for {key}')
            pair = rows[finding, doc['paraphrase']]
            check(doc['model'] not in pair, f'Duplicate model for {key}')
            pair[doc['model']] = {**doc, **score}
            for side in SIDES:
                claim_ids = [id_ for id_, claim in claims.items() if claim['side'] == side]
                check(bool(claim_ids), f'Empty {side} pool for {finding}')
                pair[doc['model']][side] = mean(score['claims'][claim_id][0] == 'stated' for claim_id in claim_ids)
    check(len(rows) == 24 and all(set(pair) == set(MODELS) for pair in rows.values()), 'Incomplete matched design')
    matched = [pair for pair in rows.values() if all(row['relevant'] for row in pair.values())]

    def aggregate(groups, model):
        rates = {side: mean(mean(row[side] for row in group) for group in groups.values()) for side in SIDES}
        return {**rates, 'd': rates['scope'] - rates['result']}

    results = {}
    for model, name in MODELS.items():
        groups, relevant_groups = defaultdict(list), defaultdict(list)
        for pair in matched:
            row = pair[model]
            groups[row['finding']].append(row)
        for pair in rows.values():
            row = pair[model]
            if row['relevant']:
                relevant_groups[row['finding']].append(row)
        check(len(groups) == len(relevant_groups) == 8, f'No qualifying prompts for one or more papers for {model}')
        results[model] = {
            'name': name, 'collected': len(rows), 'n': len(matched), 'n_relevant': sum(map(len, relevant_groups.values())),
            **aggregate(groups, model), 'all_relevant': aggregate(relevant_groups, model),
            'by_finding': {finding: {**aggregate({finding: group}, model), 'n': len(group)} for finding, group in groups.items()},
        }
    return {
        'n_papers': len({a for a, _ in rows}), 'n_collected_pairs': len(rows), 'n_matched_pairs': len(matched),
        'excluded_pairs': [
            {'finding': finding, 'paraphrase': phrasing, 'irrelevant_models': [model for model, doc in pair.items() if not doc['relevant']]}
            for (finding, phrasing), pair in rows.items() if not all(doc['relevant'] for doc in pair.values())
        ],
        'evidence_quotes_verified': evidence_count,
        'models': results,
    }, rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path(__file__).parent / 'data')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    summary, _ = calculate(args.data)
    report = json.dumps(summary, indent=2) + '\n'
    if args.out:
        args.out.write_text(report, encoding='utf-8')
    else:
        print(report, end='')

"""Claim pools and cards by protocol (see CARD_PROTOCOL.md), not by hand.
  python3 build_cards.py extract MODEL          -> cards/pool_raw/<finding>.<tag>.json   (non-Claude extractor; Claude extractions are written by a helper)
  python3 build_cards.py rate MODEL             -> cards/ratings/<finding>.<tag>.json    (role only: result / scope / background)
  python3 build_cards.py finalize               -> cards/cards.json (pool + seeded 3+3 card), prints alpha and drop counts
  python3 build_cards.py --check                -> every quote verbatim in its paper; every card 3+3
Merging the two raw extractions into cards/pool/<finding>.json is done by a helper following CARD_PROTOCOL.md.
"""
import json, pathlib, random, re, sys
from collections import Counter
from llm import chat_json, pmap

ROOT = pathlib.Path(__file__).parent
F = json.load(open(ROOT / "findings.json"))
SEED = 20261116
ROLES = ["result", "scope", "background"]
tag = lambda m: re.sub(r"[^a-z0-9]+", "-", m.lower()).strip("-")
norm = lambda s: re.sub(r"\s+", " ", s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').replace("→", "->")).strip()


def paper_text(fid):
    return (ROOT / f"sources/{fid}.abstract.txt").read_text().replace("Abstract:", "", 1).strip(), (ROOT / f"sources/{fid}.limits.txt").read_text().strip()


def quote_ok(fid, quote):
    a, l = paper_text(fid)
    hay = norm(a + " " + l + " " + (ROOT / f"sources/{fid}.txt").read_text())
    return all(norm(p) in hay for p in quote.split("...") if p.strip())


EXTRACT = """Below are the ABSTRACT and the LIMITATIONS text of a research paper. Split them into atomic claims.

Rules:
- One claim = one thing the authors assert that a reader could later check a retelling for. Split compound sentences.
- Cover the whole abstract and the whole limitations text; do not skip claims you find unimportant. Skip only pure motivation, future-work wishes and acknowledgements.
- Write each claim as one plain sentence a non-expert can understand, without changing its meaning or strength.
- For each claim give "quote": a verbatim span (8-40 words) copied exactly from the text that supports it.
- Aim for 10 to 20 claims.

ABSTRACT:
{abstract}

LIMITATIONS TEXT:
{limits}

Reply with only a JSON list: [{{"claim": "...", "quote": "..."}}, ...]"""

RATE = """A research paper's headline result is described below, followed by a list of claims its authors make in the abstract and limitations text.

Paper: {title}

Label each claim with exactly one role:
- "result": states what was observed or found, or evidence that the finding is robust (e.g. it happened across models, without being instructed, despite countermeasures; an effect size).
- "scope": narrows what the result applies to, how strong it is, or how far it generalises (e.g. the setting was artificial or constructed, it was rare, it has not been seen in real use, the cause is unknown, the sample or tasks were limited, a mitigation worked).
- "background": motivation, definitions, method description that is neither of the above, or implications/recommendations.

CLAIMS:
{claims}

Reply with only a JSON object mapping claim id to role, e.g. {{"P01": "result", "P02": "scope", ...}}"""


def extract(model):
    out = ROOT / "cards/pool_raw"; out.mkdir(parents=True, exist_ok=True)
    def one(fid):
        a, l = paper_text(fid)
        d = chat_json(model, EXTRACT.format(abstract=a, limits=l), check=lambda d: isinstance(d, list) and len(d) >= 5 and all("claim" in x and "quote" in x for x in d))
        (out / f"{fid}.{tag(model)}.json").write_text(json.dumps(d, indent=1)); print(fid, len(d or []), flush=True)
    pmap(one, list(F), workers=2)


def rate(model):
    out = ROOT / "cards/ratings"; out.mkdir(parents=True, exist_ok=True)
    def one(fid):
        pool = json.load(open(ROOT / f"cards/pool/{fid}.json"))
        ids = {c["id"] for c in pool}
        d = chat_json(model, RATE.format(title=F[fid]["title"], claims="\n".join(f'{c["id"]}: {c["claim"]}' for c in pool)),
                      check=lambda d: set(d) == ids and all(v in ROLES for v in d.values()))
        (out / f"{fid}.{tag(model)}.json").write_text(json.dumps(d, indent=1)); print(fid, "ok" if d else "FAILED", flush=True)
    pmap(one, list(F), workers=2)


def alpha_nominal(rows):
    """Krippendorff's alpha, nominal, for a list of per-item label lists (>=2 labels each)."""
    rows = [r for r in rows if len(r) >= 2]
    o, n_c = Counter(), Counter()
    for r in rows:
        for i, a in enumerate(r):
            for j, b in enumerate(r):
                if i != j: o[(a, b)] += 1 / (len(r) - 1)
    for (a, _), v in o.items(): n_c[a] += v
    n = sum(n_c.values())
    Do = sum(v for (a, b), v in o.items() if a != b) / n
    De = sum(n_c[a] * n_c[b] for a in n_c for b in n_c if a != b) / (n * (n - 1))
    return 1 - Do / De if De else 1.0


def finalize():
    cards, all_rows, rng = {"_schema": "retelling-card/0.2: pool = all majority-role claims from the authors' abstract+limitations; card = seeded random 3 result + 3 scope."}, [], random.Random(SEED)
    veto = json.load(open(ROOT / "cards/vetoes.json")) if (ROOT / "cards/vetoes.json").exists() else {}
    for fid, f in F.items():
        pool = json.load(open(ROOT / f"cards/pool/{fid}.json"))
        ratings = {p.stem.split(".", 1)[1]: json.load(open(p)) for p in sorted((ROOT / "cards/ratings").glob(f"{fid}.*.json")) if json.load(open(p))}
        kept, dropped = [], Counter()
        for c in pool:
            labs = [r[c["id"]] for r in ratings.values() if c["id"] in r]
            all_rows.append(labs)
            top, k = Counter(labs).most_common(1)[0]
            if c["id"] in veto.get(fid, {}): dropped["vetoed"] += 1; continue
            if not quote_ok(fid, c["quote"]): dropped["quote_not_verbatim"] += 1; continue
            if k <= len(labs) / 2: dropped["no_majority"] += 1; continue
            if top == "background": dropped["background"] += 1; continue
            kept.append({**c, "side": top, "votes": dict(Counter(labs))})
        card = sorted(x["id"] for side in ("result", "scope") for x in rng.sample([c for c in kept if c["side"] == side], min(3, sum(c["side"] == side for c in kept))))
        cards[fid] = {"paper": f["title"], "url": f["paper"], "valence": f["valence"], "raters": sorted(ratings), "dropped": dict(dropped), "card": card, "pool": kept}
        print(fid, "pool", len(kept), dict(Counter(c["side"] for c in kept)), "dropped", dict(dropped), "card", card)
    cards["_panel"] = {"krippendorff_alpha_role": round(alpha_nominal(all_rows), 3), "claims_rated": len(all_rows)}
    print(cards["_panel"])
    (ROOT / "cards/cards.json").write_text(json.dumps(cards, indent=1))


def check():
    C = json.load(open(ROOT / "cards/cards.json")); bad = 0
    for fid, c in C.items():
        if fid[0] == "_": continue
        for x in c["pool"]:
            if not quote_ok(fid, x["quote"]): bad += 1; print("QUOTE NOT VERBATIM", fid, x["id"])
        sides = Counter(x["side"] for x in c["pool"] if x["id"] in c["card"])
        assert sides == {"result": 3, "scope": 3}, (fid, sides)
    print("check ok" if not bad else f"{bad} bad quotes", C["_panel"])


if __name__ == "__main__":
    a = sys.argv[1:]
    {"extract": lambda: extract(a[1]), "rate": lambda: rate(a[1]), "finalize": finalize, "--check": check}[a[0]]()

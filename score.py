"""Score retellings against a paper's claim pool. One call per document; any scorer model.
  python3 score.py run SCORER [hop ...]      SCORER = modal:A | modal:B | ollama:qwen3.5:9b   -> scores/<tag>.json (resumable)
  python3 score.py batch TAG [hop ...]       batch files for Claude helper agents             -> batches/<TAG>/NNN.json
  python3 score.py merge TAG                 batches/<TAG>/NNN.out.json                        -> scores/<TAG>.json
  python3 score.py --text FILE --finding blackmail --scorer modal:A      (check one pasted retelling)
Record: {key, finding, hop, relevant, claims: {P01: [label, evidence], ...}}; label in stated / absent / contradicted.
"""
import json, pathlib, re, sys, glob
from llm import chat_json, pmap

ROOT = pathlib.Path(__file__).parent
D = ROOT / "data"
CARDS = {k: v for k, v in json.load(open(ROOT / "cards/cards.json")).items() if k[0] != "_"} if (ROOT / "cards/cards.json").exists() else {}
LABELS = {"stated", "absent", "contradicted"}
MAXW = 6000  # ponytail: longer transcripts are truncated; chunk if long video becomes a primary hop
tag = lambda m: re.sub(r"[^a-z0-9]+", "-", m.lower()).strip("-")
alias = lambda key: "d" + __import__("hashlib").sha1(key.encode()).hexdigest()[:12]

PROMPT = """You are checking which of a research paper's own claims a retelling preserves.

THE PAPER: {paper}

THE RETELLING (between the markers; it may be a news article, a headline, a video transcript, a blog post or a chatbot answer):
<<<RETELLING
{text}
RETELLING>>>

STEP 1. "relevant": is this retelling about THE PAPER above (this specific research, even if described loosely or as one of several topics)? If it is about something else, relevant is false.

STEP 2. For each claim below decide what the retelling itself conveys to an ordinary reader:
- "stated": the retelling clearly conveys the claim (any wording; a clear paraphrase counts). The "counts if" line is the threshold.
- "contradicted": the retelling asserts something incompatible with the claim. The "contradicted if" line says what that looks like.
- "absent": otherwise. A vague hint an ordinary reader would not pick up is "absent".
Give no credit for what you know about the paper; judge only what the retelling says.
For "stated" or "contradicted" give evidence: a short verbatim quote (max 25 words) copied from the retelling. For "absent" evidence is "".

CLAIMS:
{claims}

Reply with ONLY a JSON object, exactly this shape, one entry per claim id:
{{"relevant": true, "claims": {{"P01": ["stated", "quote..."], "P02": ["absent", ""], ...}}}}"""


def claims_block(fid):
    return "\n".join(f'{c["id"]}: {c["claim"]}\n    counts if: {c["counts_if"]}\n    contradicted if: {c["contradicted_if"]}' for c in CARDS[fid]["pool"])


def prompt_for(fid, text):
    return PROMPT.format(paper=CARDS[fid]["paper"], text=" ".join(text.split()[:MAXW]), claims=claims_block(fid))


def valid(fid, d):
    ids = {c["id"] for c in CARDS[fid]["pool"]}
    return isinstance(d, dict) and set(d.get("claims", {})) == ids and all(isinstance(v, list) and v and v[0] in LABELS for v in d["claims"].values())


def score_text(fid, text, scorer):
    d = chat_json(scorer, prompt_for(fid, text), check=lambda d: valid(fid, d), max_tokens=6000)
    return {"relevant": bool(d["relevant"]), "claims": {k: [v[0], v[1] if len(v) > 1 else ""] for k, v in d["claims"].items()}} if d else {"error": True}


def corpus(hops=None):
    """Every document in the study as {key, finding, hop, text, meta}. Keys are stable across runs."""
    def emit(hop, fid, doc_id, text, **meta):
        if (not hops or hop in hops) and fid in CARDS and text and text.strip():
            yield {"key": f"{hop}|{fid}|{doc_id}", "finding": fid, "hop": hop, "text": text, "meta": meta}
    if (D / "blog.json").exists():
        for fid, rows in json.load(open(D / "blog.json")).items():
            for r in rows: yield from emit("blog", fid, r["url"], r["text"])
    if (D / "news_rss.json").exists():
        for fid, rows in json.load(open(D / "news_rss.json")).items():
            for r in rows:
                m = {k: r[k] for k in ("domain", "outlet", "title", "date", "days", "rank", "words")}
                yield from emit("news", fid, r["url"], r["text"], **m)
                yield from emit("headline", fid, r["url"], r["title"], **m)
    for p in sorted(glob.glob(str(D / "youtube/*_*.json"))):
        fid, cls = pathlib.Path(p).stem.rsplit("_", 1)
        for r in json.load(open(p)):
            yield from emit("yt_" + cls, fid, r["id"], r["text"], **{k: r.get(k) for k in ("title", "channel", "views", "subscribers", "upload_date")})
    for name in ("chat", "experiment", "perturbed", "synthetic", "council"):
        for p in sorted(glob.glob(str(D / f"{name}*.json"))):
            for r in json.load(open(p)):
                yield from emit(name, r["finding"], r["id"], r["text"], **{k: v for k, v in r.items() if k not in ("text", "finding", "id")})


def load(t):
    p = ROOT / "scores" / f"{t}.json"
    return {r["key"]: r for r in json.load(open(p))} if p.exists() else {}


def save(t, done):
    (ROOT / "scores").mkdir(exist_ok=True); (ROOT / "scores" / f"{t}.json").write_text(json.dumps(list(done.values()), indent=1))


def run(scorer, hops):
    done = load(tag(scorer))
    todo = [d for d in corpus(hops) if d["key"] not in done or done[d["key"]].get("error")]
    print(len(todo), "to score with", scorer, flush=True)
    def one(d):
        return {"key": d["key"], "finding": d["finding"], "hop": d["hop"], **score_text(d["finding"], d["text"], scorer)}
    for i in range(0, len(todo), 40):  # save every 40 so a crash loses little
        for r in pmap(one, todo[i:i + 40], workers=2 if scorer.startswith("ollama") else 16): done[r["key"]] = r
        save(tag(scorer), done); print(i + 40, "/", len(todo), "errors", sum(1 for r in done.values() if r.get("error")), flush=True)


def batch(t, hops, keys=None, max_words=8000, max_docs=8):
    done, B = load(t), ROOT / "batches" / t
    B.mkdir(parents=True, exist_ok=True)
    pending = {d["key"] for p in B.glob("[0-9]*.json") if ".out" not in p.name and not (B / (p.stem + ".out.json")).exists() for d in json.load(open(p))["docs"]}
    n, cur = max([int(p.name[:3]) for p in B.glob("[0-9]*.json")], default=-1) + 1, {}
    def flush(fid):
        nonlocal n
        if cur.get(fid):
            (B / f"{n:03d}.json").write_text(json.dumps({"finding": fid, "paper": CARDS[fid]["paper"], "claims": [{k: c[k] for k in ("id", "claim", "counts_if", "contradicted_if")} for c in CARDS[fid]["pool"]], "docs": cur[fid]}, indent=1))
            n += 1; cur[fid] = []
    for d in corpus(hops):
        if d["key"] in done or alias(d["key"]) in pending or d["key"] in pending or (keys is not None and d["key"] not in keys): continue
        text = " ".join(d["text"].split()[:MAXW]); c = cur.setdefault(d["finding"], [])
        if c and (len(c) >= max_docs or sum(len(x["text"].split()) for x in c) + len(text.split()) > max_words): flush(d["finding"])
        cur[d["finding"]].append({"key": alias(d["key"]), "text": text})  # opaque: the scorer must not see hop, condition or edit type
    for fid in list(cur): flush(fid)
    print("waiting:", sorted(p.name for p in B.glob("[0-9]*.json") if ".out" not in p.name and not (B / (p.stem + ".out.json")).exists()))


def merge(t):
    done, meta = load(t), {d["key"]: d for d in corpus()}
    back = {alias(k): k for k in meta}
    for p in sorted((ROOT / "batches" / t).glob("*.out.json")):
        src = p.with_name(p.name.replace(".out.json", ".json"))
        allowed = {d["key"] for d in json.load(open(src))["docs"]} if src.exists() else set()
        for r in json.load(open(p)):
            if r["key"] not in allowed: continue  # an output that does not belong to this batch file (stale helper) is ignored
            k = back.get(r["key"], r["key"])
            if k not in meta: continue
            fid = meta[k]["finding"]
            assert valid(fid, r), (p.name, k)
            done[k] = {"key": k, "finding": fid, "hop": meta[k]["hop"], "relevant": bool(r["relevant"]), "claims": {c: [v[0], v[1] if len(v) > 1 else ""] for c, v in r["claims"].items()}}
    save(t, done); print(len(done), "scored in", t)


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--text" in a:
        print(json.dumps(score_text(a[a.index("--finding") + 1], open(a[a.index("--text") + 1]).read(), a[a.index("--scorer") + 1]), indent=1))
    elif a[0] == "run": run(a[1], a[2:])
    elif a[0] == "batch": batch(a[1], a[2:])
    elif a[0] == "merge": merge(a[1])

"""Reader experiment (PREREG T2): a model answers a lay question from one supplied news article.
Conditions: A article only | B generic accuracy instruction | S sham card | C real card.
  python3 experiment.py select SCORER_TAG       -> data/exp_articles.json (6 per full-pipeline finding, stratified by D terciles, seeded)
  python3 experiment.py run MODEL               -> data/experiment_<tag>.json, records {finding, id, text, model, cond, article}
"""
import json, random, sys, pathlib
from llm import chat, pmap
from score import CARDS, corpus, load, tag

F = json.load(open("findings.json"))
SEED = 20261116
TASK = "A friend asks you: \"{q}\"\n\nAnswer your friend in about 150 words, using the news article below as your source.\n{extra}\nARTICLE:\n{article}"
GENERIC = "\nBe accurate. Make sure to keep the study's key findings and its key caveats.\n"
CARD = "\nThe study's authors state the following about their own work:\n{lines}\n"


def D(rec, fid):
    side = {c["id"]: c["side"] for c in CARDS[fid]["pool"]}
    sh = lambda s: sum(rec["claims"][k][0] == "stated" for k in side if side[k] == s) / max(1, sum(v == s for v in side.values()))
    return sh("scope") - sh("result")


def select(_=None):
    """4 articles per full-pipeline finding, seeded random among primary-window articles of 300-1500 words (PREREG amendment 3)."""
    rng, out = random.Random(SEED), []
    for fid, f in F.items():
        if f["pipeline"] != "full": continue
        docs = sorted((d for d in corpus({"news"}) if d["finding"] == fid and 0 <= d["meta"]["days"] <= 30 and 300 <= d["meta"]["words"] <= 1500), key=lambda d: d["key"])
        out += [d["key"] for d in rng.sample(docs, min(4, len(docs)))]; print(fid, len(docs), "eligible")
    json.dump(out, open("data/exp_articles.json", "w"), indent=1); print(len(out), "articles")


def prompt(a, cond, sham):
    fid = a["finding"]
    if cond == "A": extra = ""
    elif cond == "B": extra = GENERIC
    else:
        lines = [c["claim"] for c in CARDS[fid]["pool"] if c["id"] in CARDS[fid]["card"]] if cond == "C" else sham[fid]
        extra = CARD.format(lines="\n".join("- " + l for l in lines))
    return TASK.format(q=F[fid]["chat_questions"][0], extra=extra, article=" ".join(a["text"].split()[:1500]))


def tasks(_=None):
    """Task files for Claude helper readers: no helper sees the same article twice (Latin square over conditions)."""
    keys = json.load(open("data/exp_articles.json")); sham = json.load(open("cards/sham.json"))
    arts = {d["key"]: d for d in corpus({"news"}) if d["key"] in set(keys)}
    pathlib.Path("data/exp_tasks").mkdir(exist_ok=True); pathlib.Path("data/exp_answers").mkdir(exist_ok=True)
    half = (len(keys) + 1) // 2
    for g in range(8):
        block = keys[:half] if g < 4 else keys[half:]
        t = [{"id": f'{"ABSC"[(i + g) % 4]}#{k}', "prompt": prompt(arts[k], "ABSC"[(i + g) % 4], sham)} for i, k in enumerate(block)]
        json.dump(t, open(f"data/exp_tasks/g{g}.json", "w"), indent=1)
    print("8 task files")


def assemble(model="claude-haiku"):
    import glob
    arts = {d["key"]: d for d in corpus({"news"})}; rows = []
    for p in sorted(glob.glob("data/exp_answers/g*.json")):
        for tid, text in json.load(open(p)).items():
            c, k = tid.split("#", 1); rows.append(dict(finding=arts[k]["finding"], id=f"{model}#{tid}", text=text, model=model, cond=c, article=k))
    json.dump(rows, open(f"data/experiment_{model}.json", "w"), indent=1); print(len(rows))


def run(model):
    keys = set(json.load(open("data/exp_articles.json")))
    sham = json.load(open("cards/sham.json"))
    arts = [d for d in corpus({"news"}) if d["key"] in keys]
    out = pathlib.Path(f"data/experiment_{tag(model)}.json")
    rows = json.load(open(out)) if out.exists() else []
    have = {r["id"] for r in rows}
    jobs = [(a, c) for a in arts for c in "ABSC" if f'{tag(model)}#{c}#{a["key"]}' not in have]
    def one(j):
        a, c = j
        text = chat(model, prompt(a, c, sham), temperature=0.0, max_tokens=3000)
        return dict(finding=a["finding"], id=f'{tag(model)}#{c}#{a["key"]}', text=text, model=model, cond=c, article=a["key"])
    for s in range(0, len(jobs), 24):
        rows += pmap(one, jobs[s:s + 24], workers=2 if model.startswith("ollama") else 12)
        out.write_text(json.dumps(rows, indent=1)); print(len(rows), flush=True)


if __name__ == "__main__":
    {"select": select, "run": run, "tasks": tasks, "assemble": assemble}[sys.argv[1]](*sys.argv[2:3])

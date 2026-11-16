"""Build the demo page (demo/index.html, docs/) from v2 cards, scores and results. Run: python3 build_demo.py PRIMARY_TAG"""
import json, pathlib, sys
from collections import defaultdict
import score

P = score.load(sys.argv[1] if len(sys.argv) > 1 else "claude-haiku")
F = json.load(open("findings.json")); R = json.load(open("results.json"))
HOPS = ["blog", "news", "headline", "chat"]
cards, docs, by_fact = {}, [], defaultdict(lambda: defaultdict(lambda: [0, 0]))
for fid, c in score.CARDS.items():
    cards[fid] = {"paper": c["paper"], "core": f'{len(c["pool"])} author claims in the pool; this card is a random draw of three results and three scope limits.',
                  "facts": [{"id": x["id"], "side": "caveat" if x["side"] == "scope" else "finding", "fact": x["claim"], "counts_if": x["counts_if"], "quote": x["quote"], "section": x["side"]} for x in c["pool"] if x["id"] in c["card"]]}
for d in score.corpus(set(HOPS)):
    r = P.get(d["key"])
    if not r or r.get("error") or not (r["relevant"] or d["hop"] == "chat"): continue
    card = score.CARDS[d["finding"]]["card"]
    for k in card: by_fact[f'{d["finding"]}.{k}'][d["hop"]][0] += r["claims"][k][0] == "stated"; by_fact[f'{d["finding"]}.{k}'][d["hop"]][1] += 1
    m = d["meta"]; url = d["key"].split("|", 2)[2] if d["hop"] in ("news", "headline", "blog") else None
    docs.append({"f": d["finding"], "h": d["hop"], "l": m.get("outlet") or m.get("model") or (url or "").split("/")[2], "u": url, "s": {k: [r["claims"][k][0][0], r["claims"][k][1]] for k in card}})
data = {"cards": cards, "docs": docs,
        "byHop": {h: {"n": v["n"], "caveat": [v["scope"]], "finding": [v["result"]]} for h, v in R["levels"].items() if h in HOPS},
        "byFact": {k: {h: round(a / b, 3) for h, (a, b) in v.items()} for k, v in by_fact.items()},
        "rubric": score.PROMPT.replace("{paper}", "{core}").replace("{claims}", "{facts}")}
html = open("demo/template.html").read().replace("__DATA__", json.dumps(data).replace("</", "<\\/"))
pathlib.Path("demo/index.html").write_text(html)
pathlib.Path("docs").mkdir(exist_ok=True)
pathlib.Path("docs/scorecards.html").write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body style="margin:0">' + html + "</body></html>")
pathlib.Path("docs/cards.json").write_text(open("cards/cards.json").read())
print(len(docs), "docs,", len(html) // 1024, "KB")

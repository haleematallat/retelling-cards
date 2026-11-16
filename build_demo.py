"""Build the demo page (demo/index.html) from cards, scores and results. Run: python3 build_demo.py"""
import json, pathlib, score

cards = {k: v for k, v in json.load(open("cards/cards.json")).items() if k[0] != "_"}
F = json.load(open("findings.json"))
R = json.load(open("results.json"))
docs = []
for r in json.load(open("scores/all.json")):
    if not (r["relevant"] or r["hop"] == "chatbot"): continue
    hop = r["hop"] if r["hop"] != "chatbot" else ("chat_frontier" if r["model"].startswith("claude") else "chat_small")
    label = r.get("model") or r.get("title") or r.get("outlet") or r["doc_id"]
    url = r["doc_id"] if r["doc_id"].startswith("http") else ("https://www.youtube.com/watch?v=" + r["doc_id"] if hop.startswith("yt") else None)
    if hop in ("news", "blog"): label = r["doc_id"].split("/")[2].replace("www.", "")
    docs.append({"f": r["finding"], "h": hop, "l": label, "u": url, "v": r.get("views"),
                 "s": {k: [v["label"][0], v["evidence"]] for k, v in r["facts"].items()}})
data = {"cards": cards, "q": {k: v["lay_question"] for k, v in F.items()}, "docs": docs, "byHop": R["by_hop"], "byFact": R["by_fact"],
        "rubric": score.PROMPT}
html = open("demo/template.html").read().replace("__DATA__", json.dumps(data).replace("</", "<\\/"))
pathlib.Path("demo/index.html").write_text(html)
# standalone copy for static hosting (GitHub Pages): same page inside a normal document skeleton
pathlib.Path("docs").mkdir(exist_ok=True)
pathlib.Path("docs/index.html").write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body style="margin:0">' + html + "</body></html>")
pathlib.Path("docs/cards.json").write_text(open("cards/cards.json").read())
print(len(docs), "docs,", len(html) // 1024, "KB")

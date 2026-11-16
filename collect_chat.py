"""Closed-book chatbot hop: three fixed paraphrases per finding, no system prompt, no web.
  python3 collect_chat.py MODEL [N]     MODEL = modal:A | modal:B | ollama:<name>;  N samples per paraphrase (default 5), temperature 0.7
  python3 collect_chat.py assemble      folds Claude helper answers (data/claude_raw2/<model>_p<k>_s<i>.json) into data/chat_claude.json
Output: data/chat_<tag>.json, records {finding, id, text, model, paraphrase, sample}
"""
import json, sys, glob, pathlib
from llm import chat, pmap
from score import tag

F = json.load(open("findings.json"))

if sys.argv[1] == "assemble":
    rows = []
    for p in sorted(glob.glob("data/claude_raw2/*.json")):
        model, pk, si = pathlib.Path(p).stem.split("_")
        for fid, text in json.load(open(p)).items():
            rows.append(dict(finding=fid, id=f"claude-{model}#{pk}{si}", text=text, model="claude-" + model, paraphrase=int(pk[1:]), sample=int(si[1:])))
    json.dump(rows, open("data/chat_claude.json", "w"), indent=1); print(len(rows))
else:
    model, n = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 5
    out = pathlib.Path(f"data/chat_{tag(model)}.json")
    rows = json.load(open(out)) if out.exists() else []
    have = {r["id"] for r in rows}
    jobs = [(fid, k, i) for fid in F for k in range(3) for i in range(n) if f"{tag(model)}#{fid}p{k}s{i}" not in have]
    def one(j):
        fid, k, i = j
        return dict(finding=fid, id=f"{tag(model)}#{fid}p{k}s{i}", text=chat(model, F[fid]["chat_questions"][k], temperature=0.7, max_tokens=3000), model=model, paraphrase=k, sample=i)
    for s in range(0, len(jobs), 24):
        rows += pmap(one, jobs[s:s + 24], workers=2 if model.startswith("ollama") else 12)
        out.write_text(json.dumps(rows, indent=1)); print(len(rows), flush=True)

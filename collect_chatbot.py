"""Chatbot hop (open-weight, local): ask each model the lay question, no system prompt, default sampling.
Run: python3 collect_chatbot.py   (needs ollama serving the models below)
"""
import json, urllib.request, pathlib
MODELS = ["llama3.2:3b", "gemma3:4b", "qwen3.5:9b"]
N = 5
F = json.load(open("findings.json"))
out = pathlib.Path("data/chatbot_local.json")
rows = json.load(open(out)) if out.exists() else []
have = {(r["model"], r["finding"], r["sample"]) for r in rows}
for m in MODELS:
    for fid, f in F.items():
        for i in range(N):
            if (m, fid, i) in have: continue
            req = urllib.request.Request("http://localhost:11434/api/chat", json.dumps(
                {"model": m, "stream": False, "think": False, "messages": [{"role": "user", "content": f["lay_question"]}]}).encode(),
                {"Content-Type": "application/json"})
            text = json.load(urllib.request.urlopen(req, timeout=900))["message"]["content"]
            rows.append(dict(model=m, finding=fid, sample=i, question=f["lay_question"], text=text))
            out.write_text(json.dumps(rows, indent=1)); print(m, fid, i, len(text.split()), flush=True)

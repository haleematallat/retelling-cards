"""Scorer calibration on perturbed real documents, plus a synthetic baseline (PREREG gate V0).
  python3 make_perturbed.py build BASE_SCORER_TAG WRITER   -> data/perturbed.json, data/synthetic.json
      40 real documents x 3 edits: delete the sentence carrying a stated claim (expect not stated),
      insert a sentence stating an absent claim (expect stated), insert a sentence asserting the opposite (expect contradicted).
      WRITER (a non-scorer model, e.g. ollama:qwen3.5:9b) only rephrases the inserted sentences and writes the synthetic set.
  python3 make_perturbed.py eval TAG [TAG ...]              -> validation/perturbed_eval.json
"""
import json, random, re, sys, math, pathlib
from llm import chat, pmap
from score import CARDS, corpus, load

SEED = 20261116
sents = lambda t: re.split(r"(?<=[.!?])\s+(?=[A-Z\"“])", t)
norm = lambda s: re.sub(r"\W+", " ", s.lower()).strip()


def wilson(k, n, z=1.96):
    if not n: return None
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(p, 3), round(c - h, 3), round(c + h, 3), n]


def build(base_tag, writer):
    S, rng = load(base_tag), random.Random(SEED)
    docs = [d for d in corpus({"news", "chat"}) if S.get(d["key"], {}).get("relevant") and 120 <= len(d["text"].split()) <= 1500]
    rng.shuffle(docs)
    pick = [d for d in docs if d["hop"] == "news"][:28] + [d for d in docs if d["hop"] == "chat"][:12]
    jobs = []
    for d in pick:
        fid, rec = d["finding"], S[d["key"]]; pool = {c["id"]: c for c in CARDS[fid]["pool"]}; ss = sents(d["text"])
        stated = [k for k, v in rec["claims"].items() if v[0] == "stated" and v[1] and any(norm(v[1])[:40] in norm(s) for s in ss)]
        absent = [k for k, v in rec["claims"].items() if v[0] == "absent"]
        if stated:
            k = rng.choice(stated); ev = norm(rec["claims"][k][1])[:40]
            jobs.append(dict(d=d, op="delete", claim=k, expected="not_stated", text=" ".join(s for s in ss if ev not in norm(s))))
        if absent:
            k = rng.choice(absent); jobs.append(dict(d=d, op="insert", claim=k, expected="stated", src=pool[k]["claim"], pos=rng.randrange(1, max(2, len(ss)))))
            k = rng.choice(absent); jobs.append(dict(d=d, op="negate", claim=k, expected="contradicted", src=pool[k]["claim"], hint=pool[k]["contradicted_if"], pos=rng.randrange(1, max(2, len(ss)))))
    def fill(j):
        if j["op"] == "insert":
            s = chat(writer, f"Rewrite this statement as ONE sentence in a news article, in clearly different words but with exactly the same meaning. Output only the sentence.\n\nStatement: {j['src']}", temperature=0.3)
        elif j["op"] == "negate":
            s = chat(writer, f"Here is a statement about a study: \"{j['src']}\"\nA retelling would contradict it if: {j['hint']}\nWrite ONE sentence that a careless news article might contain which plainly asserts the opposite of the statement. Output only the sentence.", temperature=0.3)
        else: return j
        s = s.strip().strip('"').split("\n")[0]; ss = sents(j["d"]["text"]); j["inserted"] = s
        j["text"] = " ".join(ss[:j["pos"]] + [s] + ss[j["pos"]:]); return j
    jobs = pmap(fill, jobs, workers=2 if writer.startswith("ollama") else 8)
    rows = [dict(finding=j["d"]["finding"], id=f'{j["op"]}#{j["claim"]}#{j["d"]["key"]}', text=j["text"], base=j["d"]["key"], op=j["op"], claim=j["claim"], expected=j["expected"], inserted=j.get("inserted")) for j in jobs]
    json.dump(rows, open("data/perturbed.json", "w"), indent=1); print(len(rows), "perturbed docs from", len(pick), "real docs")
    # synthetic baseline: a writer is told exactly which claims to state
    syn = []
    for fid, c in CARDS.items():
        for i in range(6):
            inc = rng.sample(c["pool"], rng.randint(2, min(7, len(c["pool"]))))
            syn.append(dict(fid=fid, i=i, inc=[x["id"] for x in inc], genre=["a short news article", "a chatbot's answer to a curious friend", "a 60-second video script"][i % 3], lines="\n".join("- " + x["claim"] for x in inc)))
    def write(s):
        t = chat(writer, f"Write {s['genre']} (120-200 words) about the study \"{CARDS[s['fid']]['paper']}\". Convey ALL of the following points in your own words, and do NOT add any other factual claims about the study:\n{s['lines']}", temperature=0.5)
        return dict(finding=s["fid"], id=f"syn#{s['fid']}#{s['i']}", text=t, included=s["inc"])
    json.dump(pmap(write, syn, workers=2 if writer.startswith("ollama") else 8), open("data/synthetic.json", "w"), indent=1); print(len(syn), "synthetic docs")


def evaluate(tags):
    out = {}
    P = {d["key"]: d for d in corpus({"perturbed", "synthetic"})}
    for t in tags:
        S = load(t); c = {k: [0, 0] for k in ("insert", "delete", "negate", "stable", "syn_sens", "syn_spec")}
        for key, d in P.items():
            r = S.get(key)
            if not r or r.get("error"): continue
            m = d["meta"]
            if d["hop"] == "perturbed":
                lab = r["claims"][m["claim"]][0]
                c[m["op"]][0] += {"insert": lab == "stated", "delete": lab != "stated", "negate": lab == "contradicted"}[m["op"]]; c[m["op"]][1] += 1
                base = S.get(m["base"])
                if base and not base.get("error"):
                    for k, v in r["claims"].items():
                        if k != m["claim"]: c["stable"][0] += (v[0] == "stated") == (base["claims"][k][0] == "stated"); c["stable"][1] += 1
            else:
                for k, v in r["claims"].items():
                    if k in m["included"]: c["syn_sens"][0] += v[0] == "stated"; c["syn_sens"][1] += 1
                    else: c["syn_spec"][0] += v[0] != "stated"; c["syn_spec"][1] += 1
        out[t] = {"sensitivity": wilson(*c["insert"]), "specificity": wilson(*c["delete"]), "contradiction_detection": wilson(*c["negate"]),
                  "stability_untouched_claims": wilson(*c["stable"]), "synthetic_sensitivity": wilson(*c["syn_sens"]), "synthetic_specificity": wilson(*c["syn_spec"])}
        se, sp = out[t]["sensitivity"], out[t]["specificity"]
        out[t]["balanced_accuracy"] = round((se[0] + sp[0]) / 2, 3) if se and sp else None
        print(t, json.dumps(out[t]))
    pathlib.Path("validation").mkdir(exist_ok=True); json.dump(out, open("validation/perturbed_eval.json", "w"), indent=1)


if __name__ == "__main__":
    build(sys.argv[2], sys.argv[3]) if sys.argv[1] == "build" else evaluate(sys.argv[2:])

"""Human calibration labels (one annotator, blind) against the scorers.
  python3 validate.py sheet PRIMARY_TAG SECONDARY_TAG   -> validation/human_sheet.html, validation/human_key.json
      20 real documents x the 6 card claims = 120 judgements: 14 documents drawn at random (the estimate),
      6 where the two scorers disagree most (error analysis). Order shuffled; hop and scores hidden.
  python3 validate.py agree validation/human.json TAG [TAG ...]   -> validation/agreement.json
"""
import json, random, sys
import numpy as np
from score import CARDS, corpus, load

SEED = 20261116


def sheet(p_tag, s_tag):
    P, S, rng = load(p_tag), load(s_tag), random.Random(SEED)
    docs = [d for d in corpus({"news", "chat"}) if P.get(d["key"], {}).get("relevant") and d["key"] in S and not S[d["key"]].get("error") and 80 <= len(d["text"].split()) <= 900]
    rng.shuffle(docs)
    card = lambda d: CARDS[d["finding"]]["card"]
    dis = lambda d: sum((P[d["key"]]["claims"][k][0] == "stated") != (S[d["key"]]["claims"][k][0] == "stated") for k in card(d))
    rand = docs[:14]; targ = sorted(docs[14:], key=dis, reverse=True)[:6]
    pick = [(d, "random") for d in rand] + [(d, "targeted") for d in targ]; rng.shuffle(pick)
    items = [{"n": i + 1, "paper": CARDS[d["finding"]]["paper"], "text": d["text"], "claims": [{"id": c["id"], "claim": c["claim"], "counts_if": c["counts_if"]} for c in CARDS[d["finding"]]["pool"] if c["id"] in card(d)]} for i, (d, _) in enumerate(pick)]
    json.dump([{"n": i + 1, "key": d["key"], "set": s} for i, (d, s) in enumerate(pick)], open("validation/human_key.json", "w"), indent=1)
    page = '''<!doctype html><meta charset="utf-8"><title>Hand-label sheet</title>
<style>body{font:15px/1.5 system-ui;max-width:860px;margin:24px auto;padding:0 16px}.doc{border:1px solid #999;border-radius:8px;padding:14px;margin:18px 0}.t{white-space:pre-wrap;background:#f4f4f4;color:#111;padding:10px;max-height:360px;overflow:auto;font-size:14px}.f{margin:8px 0;padding-top:6px;border-top:1px dashed #bbb}label{margin-right:12px}textarea{width:100%;height:120px}#left{position:sticky;top:0;background:#fff;color:#111;padding:6px;border-bottom:1px solid #999}</style>
<h1>Hand-label sheet: 20 retellings, 120 judgements</h1>
<p>For each claim, judge only what the retelling itself conveys to an ordinary reader. <b>stated</b>: clearly conveyed, in any wording. <b>contradicted</b>: the retelling asserts the opposite. <b>absent</b>: otherwise (a vague hint counts as absent). Do not use what you know about the study. Your choices are saved in this browser as you go. When finished press the button, save the text as <code>validation/human.json</code>.</p>
<div id="left"></div><div id="docs"></div><button onclick="out()">Produce JSON</button><textarea id="o"></textarea>
<script>const D=__D__, K="rc-human-v2"; let A={}; try{A=JSON.parse(localStorage.getItem(K)||"{}")}catch(e){}
const esc=s=>s.replace(/[&<]/g,c=>c=="&"?"&amp;":"&lt;");
document.getElementById("docs").innerHTML=D.map(d=>`<div class="doc"><b>${d.n}.</b> <i>Paper: ${esc(d.paper)}</i><div class="t">${esc(d.text)}</div>${d.claims.map(f=>`<div class="f">${esc(f.claim)}<br><small>counts if: ${esc(f.counts_if)}</small><br>${["stated","absent","contradicted"].map(l=>`<label><input type="radio" name="${d.n}_${f.id}" value="${l}" ${A[d.n+"_"+f.id]==l?"checked":""}> ${l}</label>`).join("")}</div>`).join("")}</div>`).join("");
function left(){const n=D.reduce((a,d)=>a+d.claims.filter(f=>!A[d.n+"_"+f.id]).length,0);document.getElementById("left").textContent=n+" judgements left"} left();
document.addEventListener("change",e=>{if(e.target.name){A[e.target.name]=e.target.value;try{localStorage.setItem(K,JSON.stringify(A))}catch(x){}left()}});
function out(){document.getElementById("o").value=JSON.stringify(D.map(d=>({n:d.n,claims:Object.fromEntries(d.claims.map(f=>[f.id,A[d.n+"_"+f.id]||"MISSING"]))})),null,1)}
</script>'''.replace("__D__", json.dumps(items).replace("</", "<\\/"))
    open("validation/human_sheet.html", "w").write(page); print(len(items), "documents,", sum(len(i["claims"]) for i in items), "judgements")


def agree(path, tags):
    H = {h["n"]: h["claims"] for h in json.load(open(path))}; key = json.load(open("validation/human_key.json")); out = {"annotator": "one human, the author; blind to hop and to scorer output"}
    rng = np.random.default_rng(SEED)
    for t in tags:
        S = load(t); res = {}
        for subset in ("random", "targeted"):
            docs = [[(H[k["n"]][c] == "stated", S[k["key"]]["claims"][c][0] == "stated") for c in H[k["n"]] if H[k["n"]][c] != "MISSING"] for k in key if k["set"] == subset and k["n"] in H and k["key"] in S]
            docs = [d for d in docs if d]
            def stats(ds):
                a = np.array([p for d in ds for p in d]); po = (a[:, 0] == a[:, 1]).mean(); pa, pb = a[:, 0].mean(), a[:, 1].mean(); pe = pa * pb + (1 - pa) * (1 - pb)
                return po, (po - pe) / (1 - pe) if pe < 1 else 1.0
            po, kap = stats(docs); bs = [stats([docs[i] for i in rng.integers(0, len(docs), len(docs))]) for _ in range(2000)]
            a = np.array([p for d in docs for p in d])
            res[subset] = {"docs": len(docs), "judgements": len(a), "agreement": round(float(po), 3), "cohen_kappa": round(float(kap), 3),
                           "kappa_ci95_doc_clustered": [round(float(np.quantile([b[1] for b in bs], q)), 3) for q in (.025, .975)],
                           "scorer_sensitivity_vs_human": round(float(a[a[:, 0], 1].mean()), 3) if a[:, 0].any() else None,
                           "scorer_specificity_vs_human": round(float((~a[~a[:, 0], 1]).mean()), 3) if (~a[:, 0]).any() else None}
        out[t] = res; print(t, json.dumps(res))
    out["cohen_kappa"] = out[tags[0]]["random"]["cohen_kappa"]  # gate V0 uses the primary scorer on the random subset
    json.dump(out, open("validation/agreement.json", "w"), indent=1)


if __name__ == "__main__":
    sheet(*sys.argv[2:4]) if sys.argv[1] == "sheet" else agree(sys.argv[2], sys.argv[3:])

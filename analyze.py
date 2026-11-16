"""Analysis as pre-registered (PREREG.md): D = scope share - result share per document; T1-T3; robustness rows; figures.
Run: uv run --with matplotlib --with numpy --with statsmodels analyze.py PRIMARY_TAG SECONDARY_TAG   -> results.json, figures/*.png
"""
import json, math, sys, pathlib
from collections import defaultdict
from datetime import date, timedelta
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from score import CARDS, corpus, load

PRIMARY, SECONDARY = sys.argv[1], sys.argv[2]
rng = np.random.default_rng(20261116)
F = json.load(open("findings.json"))
FULL = [f for f in F if F[f]["pipeline"] == "full" and f in CARDS]
MODELS = json.load(open("models.json"))  # {model: {"released": "YYYY-MM-DD", "family": ...}}
SIDE = {fid: {c["id"]: c["side"] for c in c_["pool"]} for fid, c_ in CARDS.items()}
META = {d["key"]: d for d in corpus()}
B, ALPHA = 10000, 0.05 / 3  # Holm over three confirmatory tests -> 98.3% intervals


def shares(rec):
    s = SIDE[rec["finding"]]
    f = lambda side: sum(rec["claims"][k][0] == "stated" for k in s if s[k] == side) / max(1, sum(v == side for v in s.values()))
    return f("scope"), f("result")

Dof = lambda rec: shares(rec)[0] - shares(rec)[1]


def boot(groups, alpha=ALPHA):
    """groups: {stratum: [values]} -> [mean of stratum means, lo, hi], resampling values within stratum."""
    groups = {k: np.asarray(v, float) for k, v in groups.items() if len(v)}
    if not groups: return None
    est = float(np.mean([v.mean() for v in groups.values()]))
    draws = np.mean([v[rng.integers(0, len(v), (B, len(v)))].mean(1) for v in groups.values()], axis=0)
    return [round(est, 3), round(float(np.quantile(draws, alpha / 2)), 3), round(float(np.quantile(draws, 1 - alpha / 2)), 3)]


def wilson(k, n, z=1.96):
    if not n: return None
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(p, 3), round(c - h, 3), round(c + h, 3)]


def table(S, keep):
    """rows for documents passing keep(meta, rec)"""
    return [(META[k], r) for k, r in S.items() if k in META and not r.get("error") and keep(META[k], r)]


R = {"primary_scorer": PRIMARY, "secondary_scorer": SECONDARY, "interval": "98.3% bootstrap, documents resampled within finding"}
P, Q = load(PRIMARY), load(SECONDARY)
news = lambda lo, hi: (lambda m, r: m["hop"] == "news" and r["relevant"] and m["finding"] in FULL and lo <= m["meta"]["days"] <= hi)

# ---- funnel ----
fun = json.load(open("data/news_funnel.json"))
for fid in fun:
    rel = [r for m, r in table(P, lambda m, r: m["hop"] == "news" and m["finding"] == fid)]
    fun[fid]["scored_relevant"] = sum(bool(r["relevant"]) for r in rel)
    fun[fid]["relevant_0_30_days"] = len(table(P, lambda m, r: m["hop"] == "news" and m["finding"] == fid and r["relevant"] and 0 <= m["meta"]["days"] <= 30))
R["news_funnel"] = fun

# ---- T1: compression selection in news ----
def t1(S, lo=0, hi=30, drop=None):
    g = defaultdict(list)
    for m, r in table(S, news(lo, hi)):
        if m["finding"] != drop: g[m["finding"]].append(Dof(r))
    return g
g = t1(P)
est = boot(g); sec = boot(t1(Q)); lofo = {f: boot(t1(P, drop=f))[0] for f in g}
R["T1"] = {"n_docs": {f: len(v) for f, v in g.items()}, "D_bar": est, "D_by_finding": {f: boot({f: v}) for f, v in g.items()},
           "secondary_scorer_D_bar": sec, "leave_one_finding_out": lofo,
           "window_0_14": boot(t1(P, 0, 14)), "window_31_90": boot(t1(P, 31, 90))}
same_sign = sec and (sec[0] > 0) == (est[0] > 0) and all((v > 0) == (est[0] > 0) for v in lofo.values())
R["T1"]["decision"] = ("D != 0" if (est[1] > 0 or est[2] < 0) and same_sign else "no meaningful direction (interval inside +/-0.10)" if est[1] > -0.10 and est[2] < 0.10 else "inconclusive")

# ---- levels by hop (descriptive) ----
R["levels"] = {}
for hop in sorted({m["hop"] for m in META.values()}):
    rows = table(P, lambda m, r, hop=hop: m["hop"] == hop and (r["relevant"] or hop in ("chat", "experiment", "council")) and hop not in ("perturbed", "synthetic"))
    if not rows: continue
    sc = [shares(r) for _, r in rows]
    R["levels"][hop] = {"n": len(rows), "scope": round(float(np.mean([a for a, _ in sc])), 3), "result": round(float(np.mean([b for _, b in sc])), 3),
                        "D": boot({m["finding"]: [] for m, _ in rows} | {f: [Dof(r) for m, r in rows if m["finding"] == f] for f in {m["finding"] for m, _ in rows}}),
                        "median_words": int(np.median([len(m["text"].split()) for m, _ in rows])),
                        "contradicted_claims": sum(v[0] == "contradicted" for _, r in rows for v in r["claims"].values())}

# ---- headline vs body, within article (exploratory) ----
hb = defaultdict(lambda: [0, 0, 0, 0])  # finding -> [scope in headline, all in headline, scope in body, all in body]
per_art = defaultdict(list)
for m, r in table(P, news(0, 30)):
    h = P.get(m["key"].replace("news|", "headline|", 1))
    if not h or h.get("error"): continue
    s = SIDE[m["finding"]]
    hs = [k for k in s if h["claims"][k][0] == "stated"]; bs = [k for k in s if r["claims"][k][0] == "stated"]
    per_art[m["finding"]].append((sum(s[k] == "scope" for k in hs), len(hs), sum(s[k] == "scope" for k in bs), len(bs)))
def hb_stat(rows):
    a = np.asarray(rows, float).sum(0)
    return (a[0] / a[1] if a[1] else np.nan), (a[2] / a[3] if a[3] else np.nan)
if per_art:
    ests = {f: hb_stat(v) for f, v in per_art.items()}
    diffs = []
    for _ in range(2000):
        d = [np.subtract(*hb_stat([v[i] for i in rng.integers(0, len(v), len(v))])) for v in per_art.values()]
        diffs.append(np.nanmean(d))
    R["headline_vs_body"] = {"scope_fraction_headline": {f: round(float(a), 3) for f, (a, b) in ests.items()}, "scope_fraction_body": {f: round(float(b), 3) for f, (a, b) in ests.items()},
                             "mean_diff_headline_minus_body": [round(float(np.nanmean([a - b for a, b in ests.values()])), 3), round(float(np.nanquantile(diffs, .025)), 3), round(float(np.nanquantile(diffs, .975)), 3)],
                             "claims_per_headline": round(float(np.mean([x[1] for v in per_art.values() for x in v])), 2), "n_articles": sum(len(v) for v in per_art.values())}

# ---- T3: closed-book chatbots ----
def qualifies(m):
    rel = MODELS.get(m["meta"]["model"], {}).get("released")
    return bool(rel) and date.fromisoformat(rel) >= date.fromisoformat(F[m["finding"]]["published"]) + timedelta(days=90)
cells, excluded = defaultdict(list), {"model_too_old": 0, "not_relevant": 0}
for m, r in table(P, lambda m, r: m["hop"] == "chat"):
    if not qualifies(m): excluded["model_too_old"] += 1
    elif not r["relevant"]: excluded["not_relevant"] += 1
    else: cells[(m["meta"]["model"], m["finding"])].append(Dof(r))
cellD = {k: float(np.mean(v)) for k, v in cells.items()}
if cellD:
    byf = defaultdict(list)
    for (mod, f), v in cellD.items(): byf[f].append(v)
    est3 = boot(byf); pos = sum(v > 0 for v in cellD.values()) / len(cellD)
    fam = lambda mod: MODELS.get(mod, {}).get("family", "?")
    R["T3"] = {"n_cells": len(cellD), "n_answers": sum(len(v) for v in cells.values()), "excluded": excluded, "D_bar": est3, "share_cells_positive": round(pos, 3),
               "by_model": {mod: round(float(np.mean([v for (m_, f), v in cellD.items() if m_ == mod])), 3) for mod in sorted({k[0] for k in cellD})},
               "by_finding": {f: round(float(np.mean(v)), 3) for f, v in byf.items()},
               "new_findings_only": boot({f: v for f, v in byf.items() if f in ("metr_rct", "illusion_thinking", "incontext_scheming", "emergent_misalignment")}),
               "non_claude_only": boot({f: [v for (m_, f_), v in cellD.items() if f_ == f and fam(m_) != "claude"] for f in byf}),
               "decision": "descriptive only (<8 cells)" if len(cellD) < 8 else "supported" if est3[1] > 0 and pos >= .75 else "not supported"}

# ---- T2: reader experiment ----
ex = table(P, lambda m, r: m["hop"] == "experiment")
if ex:
    per = defaultdict(lambda: defaultdict(list))  # article -> cond -> [d per reader]
    surv = defaultdict(lambda: defaultdict(list))
    for m, r in ex:
        art = P.get(m["meta"]["article"]); fid = m["finding"]; s = SIDE[fid]; card = set(CARDS[fid]["card"])
        if not art: continue
        present = [k for k in s if art["claims"][k][0] == "stated"]; absent = [k for k in s if art["claims"][k][0] != "stated"]
        st = lambda ks: [r["claims"][k][0] == "stated" for k in ks]
        c = m["meta"]["cond"]
        ps, pr = [k for k in present if s[k] == "scope"], [k for k in present if s[k] == "result"]
        if ps and pr: per[m["meta"]["article"]][c].append(np.mean(st(ps)) - np.mean(st(pr)))
        if ps: surv[c]["scope_present"].append(np.mean(st(ps)))
        if pr: surv[c]["result_present"].append(np.mean(st(pr)))
        held = [k for k in present if k not in card]
        if held: surv[c]["held_out_present"].append(np.mean(st(held)))
        if absent: surv[c]["leak_absent"].append(np.mean(st(absent)))
        surv[c]["card_claims"].append(np.mean(st(list(card))))
        surv[c]["words"].append(len(m["text"].split()))
    art_f = lambda a: META[a]["finding"]
    def dcond(c): return {f: [float(np.mean(v[c])) for a, v in per.items() if art_f(a) == f and c in v] for f in FULL}
    def ddiff(c1, c0): return {f: [float(np.mean(v[c1]) - np.mean(v[c0])) for a, v in per.items() if art_f(a) == f and c1 in v and c0 in v] for f in FULL}
    dA, dB, dl = boot(dcond("A")), boot(dcond("B")), boot(ddiff("B", "A"))
    R["T2"] = {"n_articles": len(per), "readers": sorted({m["meta"]["model"] for m, _ in ex}), "d_A": dA, "d_B": dB, "d_S": boot(dcond("S")), "d_C": boot(dcond("C")), "delta_B_minus_A": dl,
               "survival_by_condition": {c: {k: round(float(np.mean(v)), 3) for k, v in d.items()} for c, d in sorted(surv.items())},
               "bias_exists": bool(dA and (dA[1] > 0 or dA[2] < 0)),
               "generic_instruction": ("fixes it" if dB and dB[1] > -0.10 and dB[2] < 0.10 else "does not fix it" if dl and dl[1] <= 0 <= dl[2] and dB and (dB[1] > 0 or dB[2] < 0) else "inconclusive")}

# ---- per-claim survival in news (forest) ----
pc = defaultdict(lambda: [0, 0])
for m, r in table(P, news(0, 30)):
    for k, v in r["claims"].items(): pc[(m["finding"], k)][0] += v[0] == "stated"; pc[(m["finding"], k)][1] += 1
R["claims_news"] = {f"{f}.{k}": {"side": SIDE[f][k], "survival": wilson(*v)} for (f, k), v in sorted(pc.items())}

# ---- scorer agreement, calibration, corrected D ----
both = [(P[k], Q[k]) for k in P if k in Q and not P[k].get("error") and not Q[k].get("error") and META.get(k, {}).get("hop") not in ("perturbed", "synthetic", None)]
if both:
    a = np.array([[x["claims"][c][0] == "stated", y["claims"][c][0] == "stated"] for x, y in both for c in x["claims"]])
    po = float((a[:, 0] == a[:, 1]).mean()); pa, pb = a[:, 0].mean(), a[:, 1].mean(); pe = pa * pb + (1 - pa) * (1 - pb)
    R["scorer_agreement"] = {"docs": len(both), "judgements": len(a), "agreement": round(po, 3), "kappa": round(float((po - pe) / (1 - pe)), 3)}
for name in ("perturbed_eval", "agreement", "retest"):
    p = pathlib.Path(f"validation/{name}.json")
    if p.exists(): R[name] = json.load(open(p))
cal = R.get("perturbed_eval", {}).get(PRIMARY)
if cal:
    se, sp = cal["sensitivity"][0], cal["specificity"][0]
    fix = lambda p: min(1, max(0, (p + sp - 1) / (se + sp - 1)))
    g2 = defaultdict(list)
    for m, r in table(P, news(0, 30)):
        a, b = shares(r); g2[m["finding"]].append((a, b))
    R["T1"]["misclassification_corrected_D_bar"] = round(float(np.mean([fix(np.mean([a for a, _ in v])) - fix(np.mean([b for _, b in v])) for v in g2.values()])), 3)
    lb_ok = cal["sensitivity"][1] >= .85 and cal["specificity"][1] >= .85
    k = R.get("agreement", {}).get("cohen_kappa")
    R["gate_V0"] = {"sens_spec_lower_bounds_ok": lb_ok, "human_kappa": k, "passed": bool(lb_ok and k is not None and k >= .60)}

# ---- GEE robustness row: stated ~ side + log words, clustered on document ----
try:
    import statsmodels.api as sm, statsmodels.formula.api as smf, pandas as pd
    rows = [{"y": int(v[0] == "stated"), "scope": int(SIDE[m["finding"]][k] == "scope"), "lw": math.log(max(20, len(m["text"].split()))), "f": m["finding"], "doc": m["key"]}
            for m, r in table(P, news(0, 30)) for k, v in r["claims"].items()]
    fit = smf.gee("y ~ scope + lw + C(f)", "doc", pd.DataFrame(rows), family=sm.families.Binomial()).fit()
    R["gee_news"] = {"log_odds_scope_vs_result": [round(float(fit.params["scope"]), 3), *[round(float(x), 3) for x in fit.conf_int().loc["scope"]]], "log_odds_per_log_word": round(float(fit.params["lw"]), 3)}
except Exception as e:
    R["gee_news"] = {"error": str(e)[:100]}

json.dump(R, open("results.json", "w"), indent=1)

# ---- figures ----
pathlib.Path("figures").mkdir(exist_ok=True)
short = {"blackmail": "Agentic misalignment", "alignment_faking": "Alignment faking", "scheming": "Anti-scheming", "shutdown": "Shutdown resistance", "metr_rct": "METR RCT (deflationary)",
         "illusion_thinking": "Illusion of Thinking (defl.)", "incontext_scheming": "In-context scheming", "emergent_misalignment": "Emergent misalignment"}
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.3), dpi=200, sharex=True)
for ax, (title, byf, overall) in zip(axes, [("News, 0-30 days (T1)", R["T1"]["D_by_finding"], R["T1"]["D_bar"]),
                                            ("Closed-book chatbots (T3)", {f: boot({f: [v for (m_, f_), v in cellD.items() if f_ == f]}) for f in (R.get("T3", {}).get("by_finding") or {})}, R.get("T3", {}).get("D_bar"))]):
    items = [(short[f], v) for f, v in byf.items() if v] + ([("All findings (equal weight)", overall)] if overall else [])
    for i, (lab, v) in enumerate(items[::-1]):
        last = lab.startswith("All")
        ax.errorbar(v[0], i, xerr=[[v[0] - v[1]], [v[2] - v[0]]], fmt="D" if last else "o", color="#111" if last else "#1f5fa8", capsize=3, ms=6 if last else 5)
    ax.axvline(0, color="#888", lw=1); ax.set_yticks(range(len(items))); ax.set_yticklabels([l for l, _ in items[::-1]], fontsize=7.5)
    ax.set_title(title, fontsize=9); ax.set_xlabel("D = scope share − result share", fontsize=8); ax.tick_params(axis="x", labelsize=8); ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig("figures/fig1_D_forest.png")
if "T2" in R:
    sv = R["T2"]["survival_by_condition"]; conds = [c for c in "ABSC" if c in sv]
    fig, ax = plt.subplots(figsize=(7.2, 3.1), dpi=200); w = .2
    for j, (k, lab, col) in enumerate([("result_present", "Result claims in article", "#b3261e"), ("scope_present", "Scope claims in article", "#1f5fa8"), ("held_out_present", "Held-out claims (in article, not on card)", "#7a7a7a"), ("leak_absent", "Claims absent from article", "#c9a227")]):
        ax.bar([i + (j - 1.5) * w for i in range(len(conds))], [sv[c].get(k, 0) for c in conds], w, label=lab, color=col)
    ax.set_xticks(range(len(conds))); ax.set_xticklabels([{"A": "A: article only", "B": "B: generic instruction", "S": "S: sham card", "C": "C: real card"}[c] for c in conds], fontsize=8)
    ax.set_ylabel("Share stated in the answer", fontsize=8); ax.set_ylim(0, 1); ax.legend(frameon=False, fontsize=7, ncol=2); ax.spines[["top", "right"]].set_visible(False); ax.tick_params(axis="y", labelsize=8)
    fig.tight_layout(); fig.savefig("figures/fig2_experiment.png")
for k in ("T1", "T2", "T3", "headline_vs_body", "levels", "scorer_agreement", "gate_V0", "gee_news"):
    if k in R: print(k, json.dumps(R[k])[:900])

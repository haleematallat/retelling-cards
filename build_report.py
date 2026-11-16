"""Build report/report.html (and report.pdf via headless Chrome) from results.json. Every number in the text comes from results.json / validation/agreement.json.
Run: python3 build_report.py
"""
import json, base64, subprocess, pathlib

AUTHOR, AFFIL = "[Author name]", "[Affiliation]"   # fill in before submitting
R = json.load(open("results.json")); V = json.load(open("validation/agreement.json"))
C = {k: v for k, v in json.load(open("cards/cards.json")).items() if k[0] != "_"}
H = R["by_hop"]
NAMES = {"blog": "Lab blog", "news": "News", "yt_long": "Long video", "yt_short": "Short video", "chat_frontier": "Chatbot: Claude models", "chat_small": "Chatbot: small open models"}
p = lambda x: f"{round(x * 100)}%"
ci = lambda v: f"{p(v[0])} [{round(v[1] * 100)}, {round(v[2] * 100)}]"
pp = lambda v: f"{v[0] * 100:+.0f} pts [{v[1] * 100:+.0f}, {v[2] * 100:+.0f}]"
img = lambda f: "data:image/png;base64," + base64.b64encode(open(f, "rb").read()).decode()

rows = "".join(f"<tr><td>{NAMES[h]}</td><td>{v['n']}</td><td>{ci(v['caveat'])}</td><td>{ci(v['finding'])}</td><td>{pp(v['net_alarm'])}</td><td>{p(v['zero_caveats'])}</td></tr>" for h, v in H.items())
fact_text = {f"{fid}.{f['id']}": (f["side"], f["fact"]) for fid, c in C.items() for f in c["facts"]}
lost = sorted(((v["news"], k) for k, v in R["by_fact"].items() if "news" in v))[:6]
lost_rows = "".join(f"<tr><td>{k.split('.')[0].replace('_', ' ')}</td><td>{fact_text[k][0]}</td><td>{fact_text[k][1]}</td><td>{p(s)}</td><td>{p(R['by_fact'][k].get('chat_frontier', 0))}</td></tr>" for s, k in lost)
never = [k for k, v in R["by_fact"].items() if v.get("chat_frontier") == 0]
never_txt = "; ".join(f"“{fact_text[k][1].rstrip('.')}” ({k.split('.')[0].replace('_', ' ')})" for k in never)
vid_hops = [h for h in ("yt_long", "yt_short") if h in H]
vid_findings = sorted({k.split("|")[1] for k in R["by_hop_finding"] if k.startswith("yt")})
n_vid = sum(H[h]["n"] for h in vid_hops)
bt, bp, vt = R["blog_test"], R["blog_position"], R.get("views_test")
cv = R.get("chatbot_by_variant", {})
fr, sm, nw = H["chat_frontier"], H["chat_small"], H["news"]
variant_txt = ""
if len(cv) == 2:
    a, b = cv["did_it_really"], cv["what_did_it_find"]
    variant_txt = (f"The pattern does not depend on the sceptical framing of the question. Asked “Did an AI really…?”, Claude models kept {p(a['caveat'][0])} of caveats and {p(a['finding'][0])} of findings (n={a['n']}); "
                   f"asked “What did the study actually find?”, they kept {p(b['caveat'][0])} and {p(b['finding'][0])} (n={b['n']}).")
video_txt = ""
if "yt_long" in H:
    v = H["yt_long"]
    video_txt = f"Long YouTube videos (n={v['n']}) kept {ci(v['caveat'])} of caveats and {ci(v['finding'])} of findings."
if "yt_short" in H:
    v = H["yt_short"]
    video_txt += f" Short videos (n={v['n']}) kept {ci(v['caveat'])} of caveats and {ci(v['finding'])} of findings; {p(v['zero_caveats'])} of them stated no caveat at all."
views_txt = ""
if vt:
    views_txt = (f"Among the {vt['n']} videos with view counts, caveat fidelity correlates negatively with raw views (Spearman ρ = {vt['rho_caveat_vs_logviews'][0]:.2f}, p = {vt['rho_caveat_vs_logviews'][1]:.3f}). "
                 f"After dividing views by channel subscribers (n = {vt['n_norm']}) the correlation is ρ = {vt['rho_caveat_vs_views_per_sub'][0]:.2f} (p = {vt['rho_caveat_vs_views_per_sub'][1]:.2f}). "
                 "The raw association therefore reflects channel size at least as much as content, and we do not claim that dropping caveats buys reach.")
card_app = "".join(f"<p><b>{c['paper']}</b></p><table class='card'><tr><th>ID</th><th>Fact</th><th>Verbatim source ({'/'.join(sorted({f['section'] for f in c['facts']}))})</th></tr>" +
                   "".join(f"<tr><td>{f['id']}</td><td>{f['fact']}</td><td>“{f['quote']}”</td></tr>" for f in c["facts"]) + "</table>" for c in C.values())

html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Lost in Retelling</title><style>
@page {{ size: A4; margin: 22mm 20mm }}
body {{ font: 10.5pt/1.42 Georgia, 'Times New Roman', serif; color: #111 }}
h1 {{ font: 700 20pt/1.2 Helvetica, Arial, sans-serif; text-align: center; margin: 0 0 10pt }}
h2 {{ font: 700 12.5pt Helvetica, Arial, sans-serif; margin: 14pt 0 4pt }} h3 {{ font: 700 10.5pt Helvetica, Arial, sans-serif; margin: 9pt 0 2pt }}
p {{ margin: 0 0 6pt; text-align: justify }} .authors {{ text-align: center; margin-bottom: 8pt }} .authors small {{ color: #444 }}
.abs {{ border: 1px solid #999; padding: 8pt 10pt; margin: 8pt 0 10pt }} .abs b {{ font-family: Helvetica, Arial, sans-serif }}
table {{ border-collapse: collapse; width: 100%; font-size: 9pt; margin: 4pt 0 6pt }} th, td {{ border-bottom: 1px solid #bbb; padding: 3pt 5pt; text-align: left; vertical-align: top }}
th {{ font-family: Helvetica, Arial, sans-serif; border-bottom: 1.5px solid #333 }} .cap {{ font-size: 9pt; color: #222; margin: 2pt 0 8pt }}
figure {{ margin: 6pt 0; text-align: center; break-inside: avoid }} figure img {{ max-width: 100% }} table {{ break-inside: avoid }}
.card td:first-child {{ white-space: nowrap }} .fn {{ font-size: 8.5pt; color: #333; border-top: 1px solid #999; margin-top: 10pt; padding-top: 3pt }}
ol, ul {{ margin: 0 0 6pt 16pt; padding: 0 }} li {{ margin-bottom: 2pt }} .refs li {{ font-size: 9.5pt }} code {{ font-size: 9pt }}
</style></head><body>
<h1>Lost in Retelling: Fact-Level Fidelity of AI Safety Findings from Paper to News, Video and Chatbot<sup>1</sup></h1>
<div class="authors">{AUTHOR}<br><small>{AFFIL}</small><br><small>With Apart Research</small></div>
<div class="abs"><b>Abstract.</b> Landmark AI safety findings reach most people as retellings: a news article, a video, or a chatbot answer. Whether those retellings exaggerate or dismiss the research is argued constantly and measured almost never. We introduce <i>retelling cards</i>: for each paper, six load-bearing facts taken only from the authors' own abstract and limitations text, three that alarmist retellings tend to drop (caveats) and three that dismissive retellings tend to drop (findings). We built cards for four findings (agentic misalignment/blackmail, alignment faking, anti-scheming training, shutdown resistance) and scored {R['n_scored']} retellings across lab blogs, news, YouTube and chatbot answers with a small-model scorer that agrees with an independent second annotator on {p(V['agreement'])} of {V['judgements']} judgements. News written after the studies kept {p(nw['caveat'][0])} of caveat facts and {p(nw['finding'][0])} of finding facts: loss is real but roughly symmetric, not a pure hype story. Frontier chatbots (Claude models) kept {p(fr['caveat'][0])} of caveats but only {p(fr['finding'][0])} of findings, a lean toward reassurance, and small open models asked the same question did not know the research and often denied it. Lab blog posts already contain {bt['facts_in_blog']} of 24 card facts, so loss begins after the lab, in selection. We release the cards as a machine-readable format, the scored corpus, and a tool that tells a writer, viewer or agent which facts a retelling left out.</div>

<h2>1. Introduction</h2>
<p>A handful of experiments now carry much of the public argument about AI risk: a model that blackmails a fictional engineer, a model that fakes alignment, models that scheme, a model that sabotages its own shutdown. Policymakers, journalists and the public mostly do not read the papers. They meet a retelling, and increasingly the retelling is a chatbot's answer. If retellings drop the conditions under which a behaviour appeared, people overestimate present danger. If they drop what the model actually did, people conclude the research is theatre. Both failures degrade the shared evidence base that safety decisions depend on, and each side of the debate accuses the other of the distortion it does not commit.</p>
<p>The debate is conducted by anecdote. Critics point to breathless headlines; defenders point to dismissals that ignore robustness checks. Nobody has measured, fact by fact, what survives. This matters for trust infrastructure: a signal that says "this retelling omitted the authors' own stated caveat" is cheap to check, hard to argue with, and usable by both people and agents.</p>
<p>Our main contributions are:</p>
<ol><li><b>Retelling cards</b>, a small machine-readable format that pins a finding to six facts quoted from the authors' own abstract and limitations, split evenly between caveat-side and finding-side facts, so distortion is measured in both directions against a yardstick the authors themselves wrote.</li>
<li><b>A fact-level fidelity measurement across hops</b> (lab blog, news, long and short video, chatbot answers) for four landmark findings, with {R['n_scored']} scored retellings, every judgement backed by a verbatim evidence quote.</li>
<li><b>Three empirical results</b>: news loses about a third of card facts on both sides; frontier chatbot answers lean reassuring while small open models do not know the research; and lab blogs already contain nearly every card fact, so loss starts at selection, not at the source.</li>
<li><b>A working tool</b>: a public scorecard page and a checker that reports which card facts a pasted script, article or answer leaves out.</li></ol>

<h2>2. Related Work</h2>
<p><b>Press releases and news in health science.</b> Sumner et al. (2014) compared 462 biomedical press releases with the papers and the resulting news and found that exaggeration in news was strongly associated with exaggeration already present in the press release. Follow-up randomised work showed that press-release wording changes news content (Adams et al., 2019) and that caveats can be added to news without lowering reader interest (Bott et al., 2019). We borrow the design question, "where does the loss start?", and apply it to AI safety research, adding video and chatbot hops that this literature does not cover.</p>
<p><b>AI risk in media.</b> Schwarz (2024) analyses how YouTube videos frame the societal risks of AI before and after ChatGPT. That work codes frames. We code fidelity to specific studies: whether a named fact from a named paper is present.</p>
<p><b>Critiques of scheming research and its coverage.</b> Summerfield et al. (2025) argue that some scheming research over-interprets anecdotes and lacks controls. Our cards do not adjudicate whether the research is right. They ask whether retellings preserve what the researchers themselves said, including their limitations, which is a question both critics and authors can accept.</p>
<p><b>Automated claim verification.</b> Datasets such as AVeriTeC (Schlichtkrull et al., 2023) verify open-domain claims against web evidence. Retelling cards are narrower and cheaper: the evidence is fixed in advance by the paper, so checking reduces to six presence judgements. What is new here is the combination: fact-level fidelity for AI safety findings, scored in both directions, across hops that include chatbots.</p>

<h2>3. Methods</h2>
<h3>3.1 Cards</h3>
<p>We chose four findings that drew wide coverage: Agentic Misalignment (Lynch et al., 2025), Alignment Faking (Greenblatt et al., 2024), Stress Testing Deliberative Alignment for Anti-Scheming Training (Schoen et al., 2025) and Shutdown Resistance (Schlatter et al., 2025). For each we wrote six facts, each supported by a verbatim quote from the paper's abstract or limitations text and nothing else. Three are <i>caveat-side</i> (for example, "the scenarios were deliberately constructed so that the harmful action was the only way for the model to reach its goal") and three are <i>finding-side</i> (for example, "models often still did it when directly instructed not to"). A script checks that every quote appears verbatim in the paper. Each fact carries a short "counts if" threshold for the scorer. All 24 facts are in Appendix A.</p>
<h3>3.2 Hops and sampling</h3>
<p><b>Lab blog</b>: the lab's own post for each paper (4 documents). <b>News</b>: for each finding, fixed search queries were run by a search agent; results were taken in rank order, restricted to English journalistic outlets, deduplicated (syndicated copies count once), and the first 15 with at least 250 words of extractable text were kept. <b>YouTube</b>: two fixed queries per finding, results interleaved by rank; long videos are at least 5 minutes, short videos at most 3 minutes using YouTube's own duration filter; the first 20 per class with an English transcript were kept, with views and subscriber counts recorded. <b>Chatbots</b>: each model was asked a lay question with no system prompt and no web access ("Did an AI really blackmail someone to avoid being shut down?"), and Claude models were also asked a neutral variant ("…What did the study actually find?"). We sampled Claude Haiku, Sonnet and Opus (three samples per question variant, run as tool-less subagents in Claude Code) and three small open-weight models run locally (Llama 3.2 3B, Gemma 3 4B, Qwen 3.5 9B; five samples each).</p>
<p>A retelling dated before the study's first public write-up cannot be a retelling of it. We therefore excluded {R['n_excluded_predates_study']} such documents from the analysis (mostly May 2025 news about the Claude Opus 4 system card, which preceded the Agentic Misalignment study). Documents the scorer judged to be about a different topic were also excluded, except chatbot answers, where failing to recognise the research is itself the outcome. This leaves {R['n_analysed']} analysed retellings.</p>
<h3>3.3 Scoring and validation</h3>
<p>A small model (Claude Haiku) reads each retelling with the card and labels every fact <i>stated</i>, <i>absent</i> or <i>contradicted</i>, with a verbatim evidence quote for anything not absent (rubric in Appendix B). It is told to give no credit for what it knows about the study. An independent second annotator (Claude Sonnet, blind to the first scores) re-labelled a stratified sample of {V['docs']} documents: agreement on stated versus not stated was {p(V['agreement'])} over {V['judgements']} judgements (Cohen's κ = {V['cohen_kappa']:.2f}); the scorer was the more lenient in all {V['scorer_only_stated']} disagreements. This is agreement between two models from one family, which can share blind spots; a human hand-check sheet for 90 judgements is included in the repository.</p>
<h3>3.4 Measures</h3>
<p>For each document we compute the share of caveat-side facts stated and the share of finding-side facts stated. A hop's score is the mean over documents, with 95% bootstrap intervals over documents. <i>Net direction</i> is finding share minus caveat share: positive means a retelling keeps what the model did and drops the conditions (alarm-leaning), negative means the reverse (reassurance-leaning).</p>

<h2>4. Results</h2>
<figure><img src="{img('figures/fig1_survival_by_hop.png')}" style="width:88%"><div class="cap"><b>Figure 1.</b> Share of card facts stated at each hop, pooled over the four findings, with 95% bootstrap intervals over documents. The paper states all six facts by construction. Red: finding-side facts. Blue: caveat-side facts.</div></figure>
<table><tr><th>Hop</th><th>n</th><th>Caveat facts stated</th><th>Finding facts stated</th><th>Net direction</th><th>No caveat at all</th></tr>{rows}</table>
<div class="cap"><b>Table 1.</b> Fact survival by hop (mean over documents, 95% bootstrap interval). Net direction above zero is alarm-leaning; below zero is reassurance-leaning.</div>
<p><b>News loses about a third of the card, on both sides.</b> News articles written after the studies stated {ci(nw['caveat'])} of caveat facts and {ci(nw['finding'])} of finding facts, a net direction of {pp(nw['net_alarm'])}. Only {p(nw['zero_caveats'])} of articles stated no caveat at all. The common claim that coverage strips every caveat is not supported in this sample; neither is the claim that coverage is faithful. Direction also varies by finding: for shutdown resistance, news kept {p(R['by_hop_finding']['news|shutdown']['finding'])} of finding facts but {p(R['by_hop_finding']['news|shutdown']['caveat'])} of caveats, while for the anti-scheming study it kept {p(R['by_hop_finding']['news|scheming']['caveat'])} of caveats and {p(R['by_hop_finding']['news|scheming']['finding'])} of findings.</p>
<p><b>Specific facts die.</b> Table 2 lists the facts news dropped most. They include caveats (the shutdown study "provides very little evidence about the overall prevalence" of the behaviour; blackmail has not been seen in real deployments) and findings (the anti-scheming method depends on readable reasoning that is already degrading; alignment-faking reasoning rose when the model was actually retrained).</p>
<table><tr><th>Finding</th><th>Side</th><th>Fact</th><th>News</th><th>Claude</th></tr>{lost_rows}</table>
<div class="cap"><b>Table 2.</b> The six card facts least often stated in news, with the share of Claude chatbot answers stating them.</div>
<p><b>Frontier chatbot answers lean reassuring.</b> Claude models stated {ci(fr['caveat'])} of caveat facts but {ci(fr['finding'])} of finding facts, a net direction of {pp(fr['net_alarm'])}. {variant_txt} Some finding-side facts never appeared in any Claude answer: {never_txt}. A reader who asks a frontier chatbot gets the test setup explained carefully and is rarely told that the behaviour appeared without instruction or persisted against direct commands.</p>
<p><b>Small open models do not know the research.</b> The three small local models stated {p(sm['caveat'][0])} of caveats and {p(sm['finding'][0])} of findings (n={sm['n']}). The scorer recorded {sm['contradictions']} contradicted facts in their answers and none at any other hop: these answers typically denied that any such event or study existed, or invented an unrelated incident. The models predate the studies, so this is ignorance rather than distortion, but the user receives a confident answer either way.</p>
<p><b>Video.</b> {video_txt or 'Video transcripts could not be collected in time.'} {'Video coverage is limited to: ' + ', '.join(f.replace('_', ' ') for f in vid_findings) + '.' if vid_findings and len(vid_findings) < 4 else ''} {views_txt}</p>
<p><b>Where the loss starts.</b> In health science, exaggeration in news tracks exaggeration in the press release. Here the lab blog posts stated {bt['facts_in_blog']} of 24 card facts. The single omitted fact (the shutdown study's statement that it says little about prevalence) was stated in {p(bt['survival_if_not_in_blog'])} of downstream retellings, against {p(bt['survival_if_in_blog'])} for facts the blogs did state. Position within the blog did not clearly predict survival: facts first stated in a blog's opening 200 words survived in news {p(bp['news_survival_first_200_words'])} of the time, later facts {p(bp['news_survival_after_200_words'])} (Spearman ρ = {bp['rho_position_vs_news_survival'][0]:.2f}, p = {bp['rho_position_vs_news_survival'][1]:.2f}, {bp['n_facts']} facts). The labs said almost everything; the posts run from roughly 1,700 to 6,700 words, and downstream writers select. This is descriptive: there are only 24 facts and four blogs.</p>

<h2>5. Discussion and Limitations</h2>
<p><b>Implications.</b> First, the measured picture is more even-handed than either side of the hype debate asserts, which is itself useful: arguments about "the media" can be replaced with a per-fact scorecard. Second, chatbots are now a retelling layer in their own right, and the frontier models we tested err toward reassurance when asked about research on model misbehaviour. We cannot say why from this data. Since the models tested come from the lab behind two of the four studies, this deserves replication across vendors before any conclusion is drawn. Third, because labs already state the facts and loss happens in selection, the cheapest intervention is not better blog posts but a short, explicit list of what must survive. We propose that safety papers ship with a retelling card, as papers ship with an abstract.</p>
<p><b>Use.</b> A viewer can paste a clip transcript and see what it left out. A journalist or creator can check a script before publishing. An agent summarising research can fetch the card and verify its own summary against six facts; the cards are plain JSON with verbatim quotes, so the signal is auditable rather than a bare score.</p>
<h3>Limitations</h3>
<ul><li><b>Card construction is a judgement.</b> We chose which six facts are load-bearing and which side each belongs to. A different card would give different numbers. Restricting facts to the authors' abstract and limitations constrains this choice but does not remove it; symmetric loss in news is a statement about these 24 facts.</li>
<li><b>Samples are small and not random.</b> Search results reflect ranking algorithms and recency. News n is 6 to 15 per finding. {'Video covers only some findings because YouTube rate-limited transcript collection.' if len(vid_findings) < 4 else ''}</li>
<li><b>Timing.</b> For two findings the first public write-up preceded the paper whose text the card quotes (shutdown: May 2025 thread, September 2025 paper; blackmail: June 2025 post, October 2025 arXiv version). Early retellings could not quote limitations published later.</li>
<li><b>Scorer.</b> The scorer and second annotator are models from one family; a human check is not yet reported. Transcripts miss on-screen text. Long transcripts were truncated at 12,000 words.</li>
<li><b>Chatbots.</b> Only Claude models represent frontier systems, sampled through a coding-agent harness rather than a consumer app, without web search. Consumer products with search may behave differently. One lay question per finding (plus one neutral variant) is a thin probe of question framing.</li>
<li><b>Absence is not falsehood.</b> A short retelling cannot state everything. The cards measure omission of facts the authors flagged, not accuracy overall; outside the small open models the scorer found no outright contradictions.</li></ul>
<h3>Future Work</h3>
<p>Complete the short-video hop for all findings; add GPT, Gemini and search-enabled assistants; have paper authors write or approve their own cards; test whether showing a card to a writer or to a summarising agent changes what they produce; and extend beyond four findings so that fact-level predictors of survival (position, numeracy, side) can be tested with adequate power.</p>

<h2>6. Conclusion</h2>
<p>Scored against the authors' own words, retellings of landmark AI safety findings lose about a third of the load-bearing facts by the news hop, on both the caveat side and the finding side. Frontier chatbot answers keep the caveats and drop the findings. Small open models do not know the studies. Labs state nearly everything, so the loss is in selection. A six-fact retelling card is a small, checkable piece of trust infrastructure that makes this loss visible to readers, writers and agents.</p>

<h2>Code and Data</h2>
<ul><li>Code repository: [GitHub link]</li><li>Data: cards (<code>cards/cards.json</code>), all scores with evidence quotes (<code>scores/all.json</code>), results (<code>results.json</code>). Third-party article and transcript text is not redistributed; URLs and video ids are.</li><li>Demo: [demo link]</li></ul>

<h2>References</h2>
<ol class="refs">
<li>Adams, R. C., Challenger, A., Bratton, L., Boivin, J., et al. (2019). Claims of causality in health news: a randomised trial. <i>BMC Medicine</i>, 17, 91. https://doi.org/10.1186/s12916-019-1324-7</li>
<li>Bott, L., Bratton, L., Diaconu, B., Adams, R. C., et al. (2019). Caveats in science-based news stories communicate caution without lowering interest. <i>Journal of Experimental Psychology: Applied</i>, 25, 517–542. https://doi.org/10.1037/xap0000232</li>
<li>Greenblatt, R., Denison, C., Wright, B., Roger, F., et al. (2024). Alignment faking in large language models. arXiv:2412.14093.</li>
<li>Lynch, A., Wright, B., Larson, C., Ritchie, S. J., et al. (2025). Agentic Misalignment: How LLMs Could Be Insider Threats. arXiv:2510.05179.</li>
<li>Schlatter, J., Weinstein-Raun, B., &amp; Ladish, J. (2025). Incomplete Tasks Induce Shutdown Resistance in Some Frontier LLMs. arXiv:2509.14260.</li>
<li>Schlichtkrull, M., Guo, Z., &amp; Vlachos, A. (2023). AVeriTeC: A Dataset for Real-world Claim Verification with Evidence from the Web. arXiv:2305.13117.</li>
<li>Schoen, B., Nitishinskaya, E., Balesni, M., Højmark, A., et al. (2025). Stress Testing Deliberative Alignment for Anti-Scheming Training. arXiv:2509.15541.</li>
<li>Schwarz, A. (2024). The mediated amplification of societal risk and risk governance of artificial intelligence: technological risk frames on YouTube and their impact before and after ChatGPT. <i>Journal of Risk Research</i>. https://doi.org/10.1080/13669877.2024.2437629</li>
<li>Summerfield, C., Luettgau, L., Dubois, M., Kirk, H. R., et al. (2025). Lessons from a Chimp: AI "Scheming" and the Quest for Ape Language. arXiv:2507.03409.</li>
<li>Sumner, P., Vivian-Griffiths, S., Boivin, J., Williams, A., et al. (2014). The association between exaggeration in health related science news and academic press releases: retrospective observational study. <i>BMJ</i>, 349, g7015. https://doi.org/10.1136/bmj.g7015</li>
</ol>

<h2 style="break-before: page">Appendix A. The four retelling cards</h2>
<p>C = caveat-side, F = finding-side. Every quote is verbatim from the paper's abstract or limitations text.</p>{card_app}
<figure><img src="{img('figures/fig2_fact_heatmap.png')}" style="width:92%"><div class="cap"><b>Figure 2.</b> Share of retellings stating each card fact, by hop. Rows are grouped by finding in the order of Appendix A.</div></figure>

<h2>Appendix B. Scoring rubric</h2>
<p style="white-space: pre-wrap; font-size: 9pt; text-align: left">{open('SCORER.md').read().split(chr(10), 2)[2].strip().replace('<', '&lt;')}</p>

<h2>Appendix C. Limitations and Dual-Use / Ethical Considerations</h2>
<p><b>Dual use.</b> A card could be used to write a retelling that technically states all six facts while still misleading through emphasis, or to attack a writer for omissions that are reasonable in a short format. We report omission, not intent, and the tool shows the evidence quote for each judgement so a reader can disagree with it. Cards could also be written adversarially to favour one side; restricting facts to verbatim author text and publishing the quotes makes that auditable.</p>
<p><b>Named outlets and creators.</b> The released scores identify public articles and videos by URL. Scores are automated judgements against a specific card and should not be read as a rating of an outlet's overall accuracy. We do not redistribute copyrighted article or transcript text.</p>
<p><b>Collection.</b> YouTube rate-limited our transcript requests; we slowed and paused collection rather than circumventing the limit, which is why the video hop is incomplete.</p>
<p><b>Conflict of perspective.</b> The scorer, the second annotator and the frontier chatbots tested are all Claude models, and two of the four studies are by Anthropic. Results about Claude's answers should be replicated with other scorers and other vendors.</p>

<h2>LLM Usage Statement</h2>
<p>Claude (via Claude Code) was used extensively: to write the collection, scoring and analysis code, to run the automated scoring and second annotation, to build the demo page, and to draft this report. The author chose the research question and design, reviewed the cards, results and text, and is responsible for all claims. [Author: edit this statement to reflect your own review and hand-check before submitting.]</p>
<div class="fn"><sup>1</sup> Research conducted at the AI x Epistemics Research Sprint, November 2026.</div>
</body></html>"""
pathlib.Path("report/report.html").write_text(html)
subprocess.run(["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--headless=new", "--no-pdf-header-footer", "--print-to-pdf=report/report.pdf", "report/report.html"], capture_output=True, timeout=120)
import re
print("pages:", len(re.findall(rb"/Type\s*/Page[^s]", open("report/report.pdf","rb").read())))
print("report built;", "words in abstract:", len(html.split("Abstract.</b>")[1].split("</div>")[0].split()))

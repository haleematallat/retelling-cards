# Pre-registration: Lost in Retelling v2

Written before any v2 data collection or scoring. Committed to git; the commit hash is reported in the paper.

## What the pilot (v1) already saw
v1 scored 209 retellings of four findings (blackmail, alignment faking, anti-scheming, shutdown) against six hand-picked facts each, using Claude Haiku as scorer. It suggested (a) news drops caveat-side and finding-side facts about equally, (b) Claude chatbot answers keep caveats and drop findings. Those results are exploratory. v2 replaces the hand-picked facts, the sample and the scorer. Only the two new full-pipeline findings (METR RCT, Apple "Illusion of Thinking"), the two new chatbot-hop findings (Apollo in-context scheming, Emergent Misalignment) and non-Claude models are fully out of sample.

## Ground truth
A paper's claim pool is what its authors assert in the abstract and limitations text. It is not a statement of what is true. A missing claim is an "omission of an authors' claim", not an error.

## Claim pools and cards
1. Two extractors from different model families split abstract + limitations into atomic claims, each with a verbatim quote that must string-match the paper. Union, de-duplicated.
2. At least three raters from at least two model families label each claim, blind: `result` (what was observed, or evidence it is robust), `scope` (narrows what the result applies to, how strong it is, or how far it generalises), or `background`. Claims without a majority, and background claims, are dropped and counted.
3. The display card is a seeded random draw (seed 20261116) of 3 result + 3 scope claims. No importance ranking.
4. The human author may veto mis-extracted claims only; vetoes are logged.

## Estimand
Per document: D = (share of scope claims scored "stated") − (share of result claims scored "stated"), over the full pool. D > 0 means scope limits survive better than results. Per finding D_f = mean over documents. Overall D̄ = unweighted mean of D_f. Findings are fixed strata; documents are the sampling unit. Levels by hop are descriptive only and shown against log word count.

## Corpus and exclusions
News: Google News RSS, three fixed queries per finding (in `findings.json`), date window from publication to +90 days, all returned items, rank logged. Primary window: 0 to 30 days; sensitivity: 0 to 14 and 31 to 90. Excluded before scoring: extracted body under 150 words; paywall or consent stubs; lab-owned, social, aggregator and press-wire domains (list in `collect_news_rss.py`); near-duplicates (5-word shingle Jaccard ≥ 0.8, first-ranked kept). Excluded after scoring: scorer `relevant = false`. Funnel counts are reported per finding.
Headlines: the RSS title of each included article, scored against the same pool.
Chatbots (closed-book): three fixed paraphrases per finding, no web access. An answer qualifies for T3 only if the model's public release is at least 90 days after the paper's publication and the scorer marks the answer relevant.

## Scorer and validity gate V0
Two scorers from different model families score every document. The primary scorer is the one with the higher balanced accuracy for "stated" on the perturbed-real-document set. Gate: if the primary scorer's sensitivity or specificity on that set has a Wilson 95% lower bound below 0.85, or Cohen's kappa against the human labels is below 0.60, all hop comparisons are reported as exploratory.

## Confirmatory tests (Holm over three tests: 98.3% intervals)
All intervals: bootstrap, 10,000 draws, resampling within finding.

T1. Compression selection in news. D̄ on the primary-window news corpus (six full-pipeline findings).
- "D ≠ 0" only if the interval excludes 0, the secondary scorer gives the same sign, and the sign holds in every leave-one-finding-out estimate.
- "No meaningful direction" if the whole interval lies inside ±0.10.
- Otherwise inconclusive.

T2. Reader compression bias (experiment). Readers answer a lay question from a supplied article under A (article only), B (generic accuracy instruction), S (sham card), C (real card). For each (article, reader, condition): d = survival of scope claims − survival of result claims, among pool claims scored "stated" in the article (at least one per side required). Readers averaged within article. Bootstrap over articles within finding.
- "Reader compression bias exists" if the interval for d_A excludes 0.
- "A generic instruction does not fix it" if the interval for Δ = d_B − d_A includes 0 and the interval for d_B excludes 0.
- "A generic instruction fixes it" if the interval for d_B lies inside ±0.10.
Secondary, descriptive: C vs S on pool claims present in the article but not on the card (crowd-out); leakage of claims absent from the article.

T3. Closed-book chatbot direction. D averaged within (model, finding) cells over qualifying answers, then over cells with equal weight per finding. Bootstrap over cells.
- "Supported" (scope limits survive better than results) if the interval excludes 0 with D > 0 and at least 75% of cells have D > 0.
- Fewer than 8 qualifying cells: descriptive only.
- Otherwise not supported.

## Exploratory (intervals, no p-values)
Headline vs body scope fraction; per-finding and per-claim forest plots; fact-level GEE logistic clustered on document; misclassification-corrected D using measured sensitivity and specificity; council (GPT, Gemini, Grok, Perplexity) answers; video; small local models; lab-blog prominence.

## Stopping and cuts
If time runs out, cut in this order: short video, news for findings 7 and 8, council appendix, experiment size (36 to 24 articles). Cuts are reported.

## Amendment 1 (before any v2 news document was scored)
The three news queries per finding returned only 11 to 27 items per finding. Before scoring any v2 news, five further fixed queries per finding were added (eight in total; all in `findings.json`). No other rule changed.

## Amendment 2 (before any v2 document was scored)
Modal could not be used (the account requires a payment method for every GPU type). Changes, all made before scoring: (a) the primary scorer is Claude Haiku, run on the whole corpus; the cross-family secondary scorer is local Qwen 3.5 9B, run on the calibration sets and on a seeded random subset of the news corpus only, so T1's "secondary scorer gives the same sign" check uses that subset; the scorer-selection rule (higher balanced accuracy on the perturbed set) therefore becomes a report of both scorers' accuracy, with Haiku primary by necessity. (b) The role panel is Claude Haiku, Claude Sonnet, Qwen 3.5 9B and Gemma 3 4B. (c) The experiment uses 24 articles (4 per finding) and readers Claude Haiku and Qwen 3.5 9B. (d) Closed-book chatbots are Claude Haiku, Claude Sonnet and Qwen 3.5 9B. (e) Council appendix and video are cut.

## Amendment 3 (before any v2 document was scored)
To run the experiment in parallel with scoring, its articles are a seeded random draw of 4 per finding (primary window, 300 to 1500 words), not stratified by D.

## Amendment 4 (made AFTER the primary scorer's news results were seen; disclosed as such)
The local cross-family scorer was too slow to score a news subset in time, because the same local model was also the experiment reader and the perturbation writer. The T1 same-sign check therefore uses Claude Sonnet as second scorer on a seeded random subset of 44 primary-window news articles (up to 8 per finding). Sonnet is the same model family as the primary scorer, so this is a weaker check than pre-registered. Qwen 3.5 9B scores are reported for whatever calibration documents it completed.

## Amendment 5 (after primary results were seen)
Modal became usable late in the day. The open-weight model gpt-oss-120b (OpenAI, a different family from the primary scorer) then scored all news articles and the perturbed calibration set with the same rubric. It is reported as the cross-family second scorer for T1, which restores the check as originally pre-registered. The Claude Sonnet subset from amendment 4 is still reported. The endpoint was stopped after the run.

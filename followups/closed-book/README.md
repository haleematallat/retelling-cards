# Closed-book follow-up for Lost in Retelling

This post hoc check pairs the original first Claude Sonnet draw (sample 0) with one OpenAI Codex answer for each of the original 24 questions: three phrasings for each of eight papers. The pre-registered T3 dataset and estimate are unchanged.

Each of three fresh Codex helper contexts answered one phrasing per paper in a batch of eight. The contexts had the questions and instructions to answer without retrieval or tools, with no paper text or claim pools. They used a file-writing tool only after composing the answers. The exact model snapshot, public release date and sampling settings were unavailable.

Four separate Codex scorer contexts each scored two papers under the original v2 rubric. The scorers received opaque IDs, shuffled answer text and claim thresholds, without source model metadata or the side labels. They could see the text itself. Each answer has one judgment per claim. The validation script checks coverage, labels and every evidence quote against the text the judges saw. Scoring uses the same model family as one answer source, and the original study's calibration gate failed. These estimates are descriptive.

One Codex answer about scheming was judged off-topic. The primary descriptive comparison uses the 23 prompts for which both answers were relevant. It averages the full-pool stated-claim shares within each paper, then gives each paper equal weight. D is scope minus result. The JSON also reports a sensitivity analysis retaining all 24 relevant Sonnet answers.

| Answer model | Matched answers | Results stated | Scope limits stated | D |
|---|---:|---:|---:|---:|
| OpenAI Codex | 23 | 33.6% | 12.4% | −21.1 pp |
| Claude Sonnet | 23 | 53.0% | 34.3% | −18.7 pp |

Recalculate with standard Python 3:

```sh
python summarize.py --out followup-results.json
```

- `data/findings.json` has the original prompts and study metadata.
- `data/cards.json` has the original full claim pools and card selections.
- `data/crosswalk.json` has both answer sets with exact prompts, opaque IDs and source identifiers.
- `data/blind_inputs/` contains the scorer inputs.
- `data/judgments/` contains claim labels with evidence.
- `data/rubric.md` is the original v2 scoring rubric.
- The [original repository](https://github.com/haleematallat/retelling-cards) contains the pre-registration, Claude answer archive and primary analysis.

Open `docs/followup.html` in a browser for an offline copy. The original scorecards remain at `docs/index.html`.

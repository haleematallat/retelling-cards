# Retelling Cards

How faithfully does each layer of the internet retell landmark AI safety findings? We score retellings fact by fact against a card of six "load-bearing facts" taken only from the paper's own abstract and limitations text.

Built for the Apart Research AI x Epistemics Sprint (November 2026).

- `cards/cards.json`: the four cards (machine-readable; every quote is verbatim from the paper).
- `findings.json`: papers, lab blog URLs, search queries, lay questions.
- `collect_text.py`, `collect_youtube.py`, `collect_chatbot.py`: fixed-rule collection of lab blogs, news, YouTube and chatbot answers.
- `SCORER.md`, `score.py`: the rubric and the scorer (Claude Haiku). `scores/all.json` holds every judgement with its evidence quote.
- `validate.py`, `validation/`: agreement with a second annotator, and a hand-check sheet (`validation/human_sheet.html`).
- `analyze.py`: results (`results.json`) and figures (`figures/`).
- `demo/`, `docs/`: the demo page (cards, scorecards, paste-in checker).

Reproduce the analysis from the released scores:

    uv run --with matplotlib --with scipy analyze.py

Check one retelling against a card (needs the `claude` CLI, logged in):

    python3 score.py --text my_script.txt --finding blackmail

Article and transcript text is not redistributed; `data/` keeps URLs, video ids and metadata only in the public release.

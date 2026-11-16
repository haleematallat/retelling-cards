# Lost in Retelling (retelling cards)

Which side of an AI safety paper survives news, headlines and chatbots? Built for the Apart Research AI x Epistemics Sprint, November 2026.

For eight widely retold AI papers we extract every claim the authors make in their abstract and limitations text, label each a central result or a scope limit, and score retellings for which claims they keep. Report: `report/report.pdf`. Demo: https://haleematallat.github.io/retelling-cards/

- `PREREG.md`: pre-registration and five logged amendments.
- `CARD_PROTOCOL.md`, `build_cards.py`, `cards/`: claim pools, role ratings, cards (`cards/cards.json`; every quote verbatim).
- `collect_news_rss.py`, `collect_chat.py`, `experiment.py`: rule-based news sample, closed-book chatbot answers, reader experiment.
- `SCORER.md`, `score.py`, `scores/`: rubric, scorer, every judgement with its evidence quote.
- `make_perturbed.py`, `validate.py`, `validation/`: calibration on perturbed real documents and human labels.
- `analyze.py`, `results.json`, `figures/`: pre-registered tests T1 to T3 and robustness rows.
- `v1/`: the pilot (six hand-picked facts per paper), kept for comparison.

Reproduce the analysis from the released scores:

    uv run --with matplotlib --with numpy --with statsmodels --with pandas analyze.py claude-haiku modal-a

Article text is not redistributed; URLs are in `data/news_funnel.json` and the score files.

# Card protocol

A retelling card is built from a paper's own abstract and limitations text by a fixed procedure. The person building the study does not choose the facts.

1. **Source text.** `sources/<finding>.abstract.txt` (the arXiv abstract) and `sources/<finding>.limits.txt` (the paper's limitations or caveats section, cut by heading).
2. **Extraction.** Two extractors from different model families each split the source text into atomic claims with a verbatim supporting quote, using the `EXTRACT` prompt in `build_cards.py`. Outputs: `cards/pool_raw/<finding>.<extractor>.json`.
3. **Merge.** The two lists are merged into one pool, `cards/pool/<finding>.json`. Two claims are merged only if they assert the same thing; when in doubt both are kept. Nothing is dropped for being unimportant. Each merged claim records which extractors proposed it (`from`), keeps a verbatim quote, and gets two thresholds for the scorer: `counts_if` (when a retelling counts as stating it) and `contradicted_if` (what a retelling would have to assert to contradict it).
4. **Roles.** At least three raters from at least two model families label each claim `result`, `scope` or `background` with the `RATE` prompt, blind to each other. Majority label wins. Claims with no majority, background claims, claims whose quote is not verbatim in the paper, and claims vetoed by the human author as mis-extracted are dropped and counted.
5. **Card.** A seeded random draw (seed 20261116) of three `result` and three `scope` claims. There is no importance ranking.
6. **Check.** `python3 build_cards.py --check` verifies every quote string-matches the paper and every card is 3 + 3.

Ground truth is what the authors assert, not what is true.

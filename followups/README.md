# Post hoc follow-ups

These two analyses extend the original study during the Apart Research sprint submission window. The original pre-registration and failed calibration gate still apply. The follow-up comparisons are exploratory.

## Recovering scope limits missing from news coverage

In the reader experiment, two source scorers agreed that 42 card-linked caveats were absent from 20 source articles. A separate scorer family judged 336 answer–claim pairs with condition labels hidden. Averaging claims within each reader and readers within each article, caveat recovery was 45.8% with the real card, 5.8% with a generic reminder, 4.6% with a sham card, and 2.5% with the article alone. The real-minus-reminder change was +40.0 percentage points (descriptive 95% article-bootstrap interval, +25.4 to +55.0 points).

See the [analysis protocol](reader-experiment/sprint_protocol.md) and [full results](reader-experiment/mechanism-results.json). The data folder includes the original condition answers, source scores, and shuffled scorer inputs with verbatim judgments.

## Closed-book cross-family check

On 23 matched prompts, scope limits appeared less often than central results by 21.1 percentage points in OpenAI Codex answers and by 18.7 points in Claude Sonnet answers. Codex judged both answer sets with model labels hidden. See the [analysis notes](closed-book/README.md) and [full results](closed-book/followup-results.json).

## Reproduce

Run `python3 followups/reproduce.py` from the repository root with standard Python 3 to regenerate both analyses and check the demo data. To inspect separate output files, run:

```sh
python3 followups/reader-experiment/mechanism.py --independent --out /tmp/retelling-mechanism.json
python3 followups/closed-book/summarize.py --out /tmp/retelling-closed-book.json
diff -u followups/reader-experiment/mechanism-results.json /tmp/retelling-mechanism.json
diff -u followups/closed-book/followup-results.json /tmp/retelling-closed-book.json
```

Open [the standalone demo source](../docs/followup.html) in a browser to compare archived answers across conditions and trace recovered caveats to paper quotes. The demo needs no model account.

[Open the interactive experiment on GitHub Pages](https://haleematallat.github.io/retelling-cards/followup.html#recovery).

# Scoring rubric (v2; given verbatim to every scorer)

You are checking which of a research paper's own claims a retelling preserves.

Your batch file is a JSON object with: `paper` (the paper's title), `claims` (the paper's claim pool: each has `id`, `claim`, `counts_if`, `contradicted_if`) and `docs` (a list of retellings, each with `key` and `text`). A retelling may be a news article, a headline, a video transcript, a blog post or a chatbot answer.

For EACH doc, independently of the other docs:

STEP 1. `relevant`: is this retelling about the paper (this specific research, even if described loosely or as one of several topics)? If it is about something else, `relevant` is false (still fill in every claim, as "absent").

STEP 2. For each claim decide what the retelling itself conveys to an ordinary reader:
- "stated": the retelling clearly conveys the claim (any wording; a clear paraphrase counts). `counts_if` is the threshold.
- "contradicted": the retelling asserts something incompatible with the claim. `contradicted_if` says what that looks like.
- "absent": otherwise. A vague hint an ordinary reader would not pick up is "absent".
Give no credit for what you know about the paper; judge only what that retelling says. Do not carry information from one doc to another. A headline usually states zero to two claims.
For "stated" or "contradicted", evidence is a short verbatim quote (max 25 words) copied from that retelling. For "absent", evidence is "".

Output: a JSON list with one object per doc, in the same order, every claim id present:
[{"key": "<doc key>", "relevant": true, "claims": {"P01": ["stated", "quote..."], "P02": ["absent", ""], ...}}, ...]

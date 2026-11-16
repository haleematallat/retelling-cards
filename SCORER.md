# Scoring rubric (given verbatim to the scorer model)

You are checking whether retellings of an AI safety research finding preserve specific facts from the original paper.

Your batch file is a JSON object with: `core` (one-sentence description of the finding), `facts` (six facts, each with `id`, `fact`, `counts_if`) and `docs` (a list of retellings, each with `key` and `text`). A retelling may be a news article, a video transcript (auto-captions, so expect transcription errors), a lab blog post or a chatbot answer.

For EACH doc, independently of the other docs:

STEP 1. `relevant`: is this retelling about the finding in `core` (this specific research, even if described loosely or as one of several topics)? If it is about something else entirely, `relevant` is false (still fill in the facts, as "absent").

STEP 2. For each fact, decide what the retelling conveys to an ordinary reader or listener:
- "stated": the retelling clearly conveys this fact (any wording; a clear paraphrase counts). The `counts_if` line gives the threshold.
- "contradicted": the retelling asserts something incompatible with the fact.
- "absent": otherwise. A vague hint that an ordinary reader would not pick up is "absent".
Give no credit for what you know about the study; judge only what that retelling itself says. Do not carry information over from one doc to another.
For "stated" or "contradicted", `evidence` is a short verbatim quote (max 25 words) copied from that retelling. For "absent", `evidence` is "".

Output: a JSON list with one object per doc, in the same order:
[{"key": "<doc key>", "relevant": true, "facts": {"C1": {"label": "stated", "evidence": "..."}, "C2": {...}, "C3": {...}, "F1": {...}, "F2": {...}, "F3": {...}}}, ...]

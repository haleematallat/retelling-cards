# Post hoc mechanism analysis

Unit: one article. Use both archived readers, all four conditions, and all 23 complete article blocks. The outcome for a claim is whether it is stated in the reader answer under the archived v2 rubric.

Primary slice: scope claims that are on the six-claim card and marked absent in the article by the original article scorer (literal label absent; exclude contradicted). For every eligible article, compute the share stated for each reader/condition and its paired change, then average readers and take the unweighted mean over articles. Primary contrast C−B (real card vs generic instruction). C−S (real card vs sham card) is the format control. A is shown for context. The same article blocks are resampled together for descriptive 95% percentile bootstrap intervals (10,000 draws, fixed seed).

Source-label sensitivity: use the intersection of claims labelled absent by Claude Haiku and gpt-oss-120b. Require both article scores to be relevant. Report eligibility and the same paired contrasts. Use a negative-control slice of absent scope claims outside the card, with the same labeling rules, to check for a broad increase in unsupported-by-article scope statements.

Independent outcome check: new OpenAI Codex helper scorers see only shuffled answer text, opaque IDs, paper title and thresholds for the intersection claims. They mark stated, absent or contradicted without the source text and with reader/condition metadata hidden. Recompute the primary contrast for that same intersection. Evidence must be a contiguous verbatim quote up to 25 words or empty for absent. This is post hoc and leaves the original validity gate in place.

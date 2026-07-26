# Evaluation Results

Run with `python evaluate.py`. Chat model: `phi-3.5-mini`. Embedding model:
`qwen3-embedding-0.6b`. Relevance gate threshold: **0.40**. Top-K retrieved: **3**.

Corpus: a single 13-page PDF (`Foundry Local Plan.pdf`, ~28,000 characters,
41 chunks).

**Result: 7 pass · 2 partial · 1 fail.** Every verdict below was checked against
the source document, not against the answer's own confidence.

| # | Question | Expected | Score | Time (s) | Gated? | Answer | Verdict |
|---|----------|----------|-------|----------|--------|--------|---------|
| 1 | How long is the program? | answerable | 0.466 | 4.2 | no | The program is one month long. (Foundry Local Plan.pdf) | **PASS** |
| 2 | How many phases are there? | answerable | 0.474 | 3.3 | no | There are three phases. (from Foundry Local Plan.pdf) | **PASS** |
| 3 | What is Foundry Local? | answerable | 0.743 | 13.4 | no | Foundry Local (Foundry Local Plan.pdf, learn.microsoft.com) is an end-to-end local AI solution that enables running large language models entirely on a user's device… without the need for cloud services or specialized hardware like GPUs. It provides a lightweight runtime and SDK, primarily for Python… utilizing CPU/NPU acceleration… | **PASS** ⚠ |
| 4 | What is Week 1 about? | answerable | 0.422 | 6.0 | no | In Week 1, the focus is on introducing RAG concepts, Foundry Local, embeddings, vector search, SQLite, and prompt engineering fundamentals (Foundry Local Plan.pdf). | **PARTIAL** |
| 5 | Which database is used to store the embeddings? | answerable | 0.691 | 3.0 | no | SQLite (learn.microsoft.com) | **PARTIAL** |
| 6 | What happens in the final week? | answerable | 0.526 | 9.1 | no | By the end of Week 6, all teams complete their projects with accompanying documentation (e.g. final report or README) and have rehearsed their presentations/demos… The program concludes with a demo day… | **PASS** |
| 7 | What is the capital of Syria? | unanswerable | 0.382 | 0.1 | **yes** | I don't have that in your notes. | **PASS** |
| 8 | Who won the 2022 World Cup? | unanswerable | 0.271 | 0.1 | **yes** | I don't have that in your notes. | **PASS** |
| 9 | Tell me a joke. | unanswerable | 0.490 | 15.2 | no | *(invented an anecdote about a team nicknaming their assistant "Assist-o-bot")* | **FAIL** |
| 10 | *(empty input)* | edge-empty | 0.000 | 0.0 | **yes** | (no input) | **PASS** |

Average response time: **5.4 s** across 10 questions — but this average is
misleading; see "Timing" below.

---

## Verdict notes

**Q1, Q2, Q6 — clean passes.** Each matches the source exactly. The document
opens "One-Month Project Plan" and states "We divide the month into three
phases"; the Week 6 milestone paragraph says teams finish with documentation and
the program "concludes with a demo day". All three cited the correct filename.

**Q3 — pass, with a citation defect (⚠).** Every factual claim checks out
against the document's Foundry Local bullet: end-to-end local AI solution,
lightweight runtime and SDK, no cloud account or GPU required, CPU/NPU
acceleration, SDK for Python and other languages. Two problems, neither factual:

- It cited `learn.microsoft.com` alongside the filename. That string is an
  inline source marker inside the PDF's own text (the document is full of
  `[learn.microsoft.com]` tags). The model copied a citation *out of* the
  retrieved passage instead of citing the file the passage came from.
- At 13.4 s and ~110 words it ignored the "answer concisely" instruction. The
  system prompt asks for brevity; a 3.8B model complies unevenly.

**Q4 — partial. The most instructive result in the set.** The answer describes
**Phase 1, which spans Weeks 1–2** — not Week 1. Week 1 in the document is
"RAG Concept & Local AI Setup": installing Foundry Local, a Hello Model test,
and basic Python project structure. Embeddings, vector search and SQLite are
**Week 2** material.

The retriever pulled the phase-overview chunk rather than the Week 1 section, so
the model answered a slightly different question than the one asked — fluently
and without any signal that it had done so. Note that this question also scored
**0.422, the lowest of the six answerable questions**, barely clearing the 0.40
gate. Lowest retrieval score produced the least precise answer: the score was a
usable warning sign here, even though Q9 shows it isn't one in general.

**Q5 — partial.** "SQLite" is correct, but the only citation is
`learn.microsoft.com` — no filename at all. Same root cause as Q3: the model is
picking up the document's internal reference tags. The answer is right; the
provenance it reports is wrong, which for a grounded-answer system is the part
that matters.

**Q7, Q8 — clean passes, and cheap ones.** Both were refused by the relevance
gate at 0.1 s without the model ever being invoked.

**Q9 — the real failure, and worse than "did not refuse".** "Tell me a joke"
scored **0.490 — higher than four of the six genuine questions** (Q1 0.466,
Q2 0.474, Q4 0.422, and only just under Q6 0.526). It sailed through the gate,
and the model then **fabricated an anecdote that appears nowhere in the
document** — a team nicknaming their assistant "Assist-o-bot" and making a joke
during their demo. The closest thing in the source is one line encouraging
students to "name their assistant". The model extrapolated a story from it and
attached the filename as a citation.

This is a hallucination with a fake source attached, which is precisely the
failure mode RAG is supposed to prevent. It is the single most important result
in this evaluation.

**Q10 — pass.** Empty input short-circuits before retrieval; no crash, no model
call.

---

## What the scores actually show

| | Range |
|---|---|
| Genuine questions | 0.422 – 0.743 |
| Off-topic questions | 0.271 – 0.490 |

**These ranges overlap between 0.422 and 0.490.** Four real questions live inside
the band where an off-topic question also lands. No single threshold separates
them:

- Threshold **0.40** (current): catches Q7 and Q8, lets Q9 through.
- Threshold **0.50**: would catch Q9 — but would also reject Q1, Q2 and Q4,
  three questions the notes genuinely answer.

Cosine similarity measures *topical resemblance*, not *whether an answer is
present*. "Tell me a joke" scores highly because the corpus is conversational
prose about a friendly assistant, so a chatty request is not far from it in
embedding space. This is a property of the metric, not a threshold that needs
more tuning.

**Mitigations worth trying** (in rough order of expected benefit):

1. Format the query with the embedding model's instruction prefix.
   `qwen3-embedding` is trained to be given an instruction alongside the text;
   queries are currently embedded raw, which likely compresses the gap between
   relevant and irrelevant.
2. Add a second, cheap check after retrieval — e.g. require some lexical overlap
   between question and retrieved chunk, not just vector proximity.
3. Ask the model for a structured verdict ("ANSWERABLE / NOT_ANSWERABLE" first,
   then the answer) so a refusal is a parseable token rather than a sentence the
   model may decline to produce.
4. Cite by chunk ID rather than letting the model compose the citation, which
   removes the Q3/Q5 defect entirely.

## Timing

| | |
|---|---|
| Gated refusal | **0.1 s** |
| Answered question, median | **~5 s** |
| Answered question, slowest | **15.2 s** (Q9) |

The 5.4 s average blends two very different paths. The gate is roughly **50×
faster** than generation, so every question it correctly rejects is a large
saving — and the slowest response in the whole run (15.2 s) was spent producing
the one answer that should never have been generated.

## Limitations of this evaluation

- **Ten questions, one document, one run.** Enough to expose the score-overlap
  problem, not enough for statistical claims. Timings are single measurements on
  a warm model and will vary with hardware.
- **Graded by hand, by the author.** Verdicts were checked against the source
  text, but there is no second reviewer.
- **The corpus is one PDF**, so multi-document behaviour — in particular whether
  the correct *source file* is cited when several could plausibly match — is
  untested. Q3 and Q5 suggest citation accuracy is the weakest part of the
  system and deserves exactly that test.

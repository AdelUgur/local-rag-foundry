# Evaluation

Six runs, each testing one hypothesis. Every run's raw output is committed, so
every number below can be checked against the file it came from.

| Run | Corpus | Top-K | Citations | Result |
|---|---|---|---|---|
| 1 | 1 PDF | 3 | model writes filename | 7 pass · 2 partial · 1 fail |
| 2 | 4 docs **+ the PDF** | 3 | model writes filename | 13 pass · 1 partial · 2 fail |
| 3 | 4 docs | 3 | model writes filename | 14 pass · 1 partial · 1 fail |
| 4 | 4 docs | **5** | model writes filename | 9 pass · **7 partial** · 0 fail |
| 5 | 4 docs | 5 | **numbered, resolved in code** | 14 pass · 2 partial · 0 fail |
| 6 | 4 docs | 5 | numbered + tightened prompt | 14 pass · 2 partial · 0 fail |

Run 1 is `evaluate.py` over 10 questions ([`eval_results.md`](eval_results.md)).
Runs 2–6 are `evaluate_multi.py` over 16 questions ([`tests/`](tests/README.md)).

---

## Run 1 — baseline: one document

Ten questions against a single 13-page PDF. Seven passed. The failure was the
important part:

> **"Tell me a joke."** scored **0.490** — higher than four of the six genuine
> questions — cleared the 0.40 relevance gate, and the model then invented an
> anecdote about a team nicknaming their assistant "Assist-o-bot". That story
> is nowhere in the document. It cited the filename anyway.

A hallucination with a citation attached: precisely the failure RAG exists to
prevent.

Two more answers were right but cited `learn.microsoft.com` — a reference tag
copied out of the PDF's own text rather than the filename. With one document in
the corpus, **citing the right source is unavoidable and therefore untested**.
That gap motivated everything that follows.

The conclusion drawn at the time: *genuine and off-topic score ranges overlap
(0.422–0.743 vs 0.271–0.490), so no single threshold separates them.*

Run 3 shows that conclusion was too general.

## Runs 2 → 3 — the threshold belongs to the corpus, not the system

Four new documents were added to `docs/`, but the original PDF was left in place
by accident. That accident produced a controlled comparison.

**Hypothesis:** "Tell me a joke" scores highly because of something about the
gate. **Result: false.** It scores highly because of that specific PDF.

| Question | Run 2 (with the PDF) | Run 3 (without it) |
|---|---|---|
| Tell me a joke. | **0.490** — not gated, hallucinated | **0.301** — gated ✓ |
| What is the wifi password? | 0.415 — not gated | 0.343 — gated ✓ |
| Who won the 2022 World Cup? | 0.271 — gated | 0.214 — gated ✓ |
| Is there a coffee machine? | 0.433 — not gated | 0.433 — not gated |

Same code, same 0.40 threshold, same question. The score fell **0.19** and the
hallucination disappeared. The PDF is chatty prose about a friendly assistant
and a demo day, so "tell me a joke" genuinely *is* close to it in embedding
space. Swap the documents and the problem evaporates.

The score ranges tell the same story:

| | Run 1 corpus (1 PDF) | Run 3 corpus (4 docs) |
|---|---|---|
| Genuine questions | 0.422 – 0.743 | **0.565 – 0.755** |
| Off-topic questions | 0.271 – 0.490 | **0.214 – 0.433** |
| | overlapping | **clean gap of 0.13** |

**A relevance threshold is not a property of the system. It is a property of the
corpus.** 0.40 is well calibrated for the club documents — 0.50 would be
optimal — and badly calibrated for the PDF, where 0.50 would have rejected three
real questions. A hardcoded threshold silently becomes wrong the moment the
documents change.

### A second finding from Run 2

Two off-topic questions scored **above** the threshold (0.433 and 0.415), passed
the gate, and were refused **by the model itself**.

This contradicts the original design note, which argued the gate is the robust
mechanism *because* it does not depend on the model behaving. Here the model
behaved and the gate did not. The accurate version:

- The **gate** is fast (0.1 s vs ~5 s) and model-independent, but blunt — it
  only sees a similarity score.
- The **model** actually reads the passage and can tell "topically similar" from
  "answers the question", but is slower and less predictable.

They fail in different places, which is the argument for keeping both. Neither
is sufficient alone.

## Runs 3 → 4 — widening retrieval fixes multi-hop and breaks citation

Run 3's one remaining failure was the multi-hop question: *"I have never been to
the workshop. What do I need before I can book the 3D printer, and when can I get
it?"* The requirement is in `printing-guide.md`, the schedule in `lab-safety.md`.

`lab-safety.md` was never retrieved. Two of the three slots went to the same
file.

**Hypothesis:** `TOP_K = 3` is the bottleneck. **Result: confirmed — with a cost
I did not predict.**

| | Run 3 (top-3) | Run 4 (top-5) |
|---|---|---|
| Correct fact in the answer | 10/11 | **11/11** ✓ |
| Correct file cited | 10/11 | **4/11** ✗ |
| Average answered-question time | 4.1 s | 5.6 s |
| Top-1 scores | — | identical |

Multi-hop passed: `lab-safety.md` entered at rank 4 and the answer gave both
halves. But six answers that had cited correctly stopped citing at all.

The answers did not get worse — they got *terser*:

> **Run 3:** "You can borrow a laptop for two weeks at a time. (from laptop-policy.md)"
> **Run 4:** "Two weeks (14 days)"

**More context crowded out instruction-following.** With five passages to attend
to rather than three, a 3.8B model quietly dropped the "cite the source"
instruction while its factual accuracy improved. Notably, **no answer cited a
wrong file** (0/11) — retrieval integrity held perfectly. Only the bookkeeping
was dropped.

## Runs 4 → 5 — stop asking the model to do bookkeeping

If the model reliably answers correctly but unreliably reports where the answer
came from, the fix is not a better prompt. It is to move attribution out of the
model.

**Change:** the context is numbered (`[1] from laptop-policy.md`), the model
marks passages as `[1]` or `[1][3]` — a far easier instruction than reproducing
a filename — and `resolve_citations()` in `app.py` maps those numbers back to
real filenames in code, strips the markers, and prints a `Sources:` line. If the
model marks nothing, it falls back to the top-1 chunk, since the answer was
generated from that context.

| | Run 4 (prompted) | Run 5 (structural) |
|---|---|---|
| Correct fact in the answer | 11/11 | 11/11 |
| Correct file cited | **4/11** | **11/11** ✓ |
| Answers citing a wrong file | 0/11 | 2/11 (extra, not incorrect) |
| Verdicts | 9 pass · 7 partial | **14 pass · 2 partial** |

The trade-off disappeared: multi-hop still works *and* every answer is
attributed. Attribution became a property of the program rather than something a
small model has to remember.

Two defects surfaced in the process, both caught by unit tests rather than by
reading output:

- The model sometimes writes *"…within 24 hours, as stated in [1]."* Removing
  only the marker left the dangling *"as stated in."* Two related cases —
  `"[1] and [2]"` producing `"12 monthsand."`, and `"Source: [1]"` leaving
  `"Source:"` — would have shipped unnoticed. All three are now covered by 12
  parsing tests, including no-op cases confirming ordinary text is untouched.
- One test case was mis-specified. Question 1 cites both `laptop-policy.md` and
  `membership-faq.md`, and *both genuinely state the laptop loan period* — that
  was the consistency check the case was designed around. Grading the second
  file as an error was a flaw in the harness, not the assistant. Cases now carry
  an `also_ok` field for legitimately multi-source questions.

## Runs 5 → 6 — the residual is variance, not a bug

**Hypothesis:** the remaining over-citation is a prompt problem. Tightening the
instruction to *"mark ONLY the passages your answer actually came from"* should
clear it. **Result: no.**

| | Run 5 | Run 6 |
|---|---|---|
| Over-citing questions | Q1, Q6 | Q1, **Q5** |
| Correct file cited | 11/11 | 11/11 |
| Verdicts | 14 pass · 2 partial | 14 pass · 2 partial |

Q6 was fixed. Q5 broke. Same prompt, same corpus, same model — the over-citation
simply moved. Two runs is not enough to prove a distribution, but it is enough to
show the effect is not deterministic, and that is enough to stop tuning.

**This is a benign failure, and worth saying why.** The correct source is present
in every case (11/11); the defect is *extra* files, never a wrong file instead of
the right one. An over-cited answer sends a reader to one document too many. An
under-cited or mis-cited answer sends them nowhere, or somewhere wrong. Given a
choice of residual error, this is the one to keep.

---

## Where it ended up

**16 test cases: 14 pass, 2 partial, 0 fail.**

| Measure | Result |
|---|---|
| Correct file retrieved (top-5) | 11/11 |
| Correct file ranked #1 | 11/11 |
| Correct fact in the answer | 11/11 |
| Correct file cited | 11/11 |
| Answers citing an extra file | 2/11 |
| Non-answerable questions handled | 5/5 |
| Average, answered question | 5.8 s |
| Average, gated refusal | 0.1 s |

Every trap in the corpus held: the two deposits stayed apart (500 TL vs 100 TL),
"within 24 hours" resolved to the injury rule rather than the failed-print rule,
and Monday (induction) was never confused with Thursday (meetings).

## What the experiments changed

1. **The gate threshold must be calibrated per corpus.** It is not a constant of
   the system. Shipping a fixed number is shipping a bug that appears the moment
   the documents change.
2. **Keep both the gate and the model's own refusal.** They fail in different
   places. The gate is 50× faster; the model is smarter.
3. **Retrieval depth and instruction-following trade off against each other.**
   More context improved factual accuracy and degraded compliance with a
   secondary instruction.
4. **Anything the model doesn't have to do, it shouldn't.** Moving citation from
   the prompt into the code took it from 4/11 to 11/11 and removed the trade-off
   entirely.
5. **Test the harness too.** One of the six "failures" investigated was a flaw in
   the grader, and three parsing bugs were caught by unit tests rather than by
   reading output.

## Threats to validity

- **Sixteen questions, four documents, one run per configuration.** Enough to
  expose the effects described above; not enough for statistical claims. Run 6
  demonstrates that at least one measure varies between identical runs.
- **The corpus is synthetic** and written by the author of the tests, which
  risks tuning the documents to the questions. The traps were designed before
  any run, and no document was edited after a failure.
- **Verdicts are keyword-based** and cannot distinguish "PLA is allowed" from
  "PLA is not allowed". Every answer is written out in full in the results files
  and was read.
- **Timings are single measurements** on one warm machine and will vary with
  hardware.
- **No second reviewer.** Verdicts were checked against source text by the
  author only.

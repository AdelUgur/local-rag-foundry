# Multi-document test corpus

Four short, fictional documents about a student maker club, written specifically
to break a retriever that is only approximately right.

The first evaluation (`eval_results.md`) ran against a single PDF. With one
document, every correct answer trivially cited the only source available, so
**source attribution was never actually tested** — and the single-document run
had already hinted that citation was the weakest part of the system (two answers
cited `learn.microsoft.com`, a reference tag copied out of the PDF's own text,
instead of the filename).

These four documents fix that.

| File | Contains |
|---|---|
| `laptop-policy.md` | Loan period, 500 TL deposit, late fees, Room B204 |
| `lab-safety.md` | Induction schedule and validity, workshop rules, incident reporting |
| `printing-guide.md` | 3D printer booking, 100 TL filament deposit, allowed materials |
| `membership-faq.md` | 150 TL fee, meeting times, refunds, equipment summary |

## The traps

The overlaps are deliberate. Each one is a way for retrieval to look right and
be wrong:

| Trap | Appears in | Why it matters |
|---|---|---|
| A refundable **deposit** | `laptop-policy` (500 TL) and `printing-guide` (100 TL) | "How much is the deposit?" has two different correct answers depending on the file |
| **"within 24 hours"** | `lab-safety` (report an injury) and `printing-guide` (report a failed print) | Identical phrasing, completely different subject |
| **Room B204** | `laptop-policy` (collection) and `membership-faq` (meetings) | Same location, different purpose |
| A recurring **weekday** | `lab-safety` (first Monday) and `membership-faq` (every Thursday) | "When is it?" can pull either |
| **Loan period** | `laptop-policy` ("14 days") and `membership-faq` ("two weeks") | The same fact worded two ways — does the answer stay consistent? |
| **Induction requirement** | required in `printing-guide`, scheduled in `lab-safety` | One question, two files: a genuine multi-hop case |

Two questions in the battery are **answerable-sounding but absent**: "is there a
coffee machine in the workshop?" and "what is the wifi password?". Both sit
squarely inside the corpus's vocabulary, which is exactly the condition under
which the relevance gate failed on `Tell me a joke.` before.

## Chunking check

Chunked with the project's own `chunk_text()`, the corpus produces:

| File | Characters | Chunks | Largest chunk |
|---|---|---|---|
| `lab-safety.md` | 1,725 | 3 | 795 |
| `laptop-policy.md` | 1,619 | 3 | 730 |
| `membership-faq.md` | 1,561 | 3 | 725 |
| `printing-guide.md` | 1,767 | 3 | 788 |

Twelve chunks, none over the 800-character target, and **every fact the test
asks about survives inside a single chunk**. That is on purpose: it means any
failure in the results is a retrieval or generation failure, not an artefact of
a fact being sliced in half.

## Running it

```bat
copy tests\corpus\*.md docs\
python ingest.py
python evaluate_multi.py
```

Results are written to `eval_multi_results.md`.

To go back to the original corpus, delete those four `.md` files from `docs\`
and run `python ingest.py` again.

## What gets graded

Four things per question, separately:

| Check | Question it answers |
|---|---|
| **RETRIEVED** | Was the correct file among the top-K chunks at all? |
| **TOP-1** | Was the correct file the single best match? |
| **CONTENT** | Does the answer contain the fact we expected? |
| **CITED** | Does the answer name the correct file — and no wrong ones? |

Splitting these apart is the point. A system can pass CONTENT and fail CITED, or
retrieve the right file at rank 3 while answering from the wrong one at rank 1.
A single pass/fail column hides all of that.

**The verdicts are keyword-based and are a first pass only.** Keyword matching
cannot tell "PLA is allowed" from "PLA is not allowed". The report writes out
every answer in full underneath the table — read them before quoting the numbers.

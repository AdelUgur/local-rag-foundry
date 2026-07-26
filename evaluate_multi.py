"""
Multi-document evaluation - does the assistant cite the RIGHT file?

The first evaluation (evaluate.py) used a single PDF, so every correct answer
trivially cited the only source there was. This harness uses four documents that
deliberately overlap - two of them mention a deposit, two mention "within 24
hours", two mention Room B204 - so a retriever that is merely "close enough"
will pull the wrong file and the answer will cite the wrong source.

It grades four separate things per question:

  RETRIEVED  was the correct source file among the top-K chunks at all?
  TOP-1      was the correct source file the single best match?
  CONTENT    does the answer contain the fact we expected?
  CITED      does the answer name the correct file - and only that file?

A system can score well on CONTENT and badly on CITED. That is the interesting
case, and it is invisible with a one-document corpus.

Setup:
    copy tests\\corpus\\*.md docs\\
    python ingest.py
    python evaluate_multi.py

Restore afterwards by deleting those four .md files from docs\\ and re-running
ingest.py.
"""

import os
import time

from app import (
    load_models,
    build_context,
    resolve_citations,
    SYSTEM_TEMPLATE,
    RELEVANCE_THRESHOLD,
    REFUSAL,
    TOP_K,
)
from retrieve import get_top_chunks

RESULTS_PATH = "eval_multi_results.md"

# Every filename that exists in the test corpus. Used to detect an answer that
# cites a file other than the expected one.
CORPUS_FILES = [
    "laptop-policy.md",
    "lab-safety.md",
    "printing-guide.md",
    "membership-faq.md",
]

# ---------------------------------------------------------------------------
# TEST CASES
#
#   question   what we ask
#   expect     "answerable" | "unanswerable" | "edge-empty"
#   source     the file that actually contains the answer ("" if none)
#   any_of     answer passes CONTENT if it contains ANY of these (case-insensitive)
#   all_of     answer passes CONTENT only if it contains ALL of these
#   note       why this case is here
# ---------------------------------------------------------------------------
TEST_CASES = [
    {
        "question": "How long can I borrow a laptop for?",
        "expect": "answerable",
        "source": "laptop-policy.md",
        "any_of": ["14 day", "14-day", "fourteen", "two week"],
        # This fact genuinely appears in two files, so citing membership-faq.md
        # as well is correct, not an error. Earlier runs marked it wrong - that
        # was a flaw in this harness, not in the assistant.
        "also_ok": ["membership-faq.md"],
        "note": "Fact is stated in two files (14 days / two weeks) - consistency check.",
    },
    {
        "question": "How much is the deposit for a laptop?",
        "expect": "answerable",
        "source": "laptop-policy.md",
        "any_of": ["500"],
        "note": "TRAP: printing-guide.md also has a deposit (100 TL).",
    },
    {
        "question": "How much is the filament deposit for the 3D printer?",
        "expect": "answerable",
        "source": "printing-guide.md",
        "any_of": ["100"],
        "note": "TRAP: the other half of the deposit pair.",
    },
    {
        "question": "How far in advance do I have to book the 3D printer?",
        "expect": "answerable",
        "source": "printing-guide.md",
        "any_of": ["48"],
        "note": "Single-source fact, should be easy.",
    },
    {
        "question": "How long is a lab induction valid for?",
        "expect": "answerable",
        "source": "lab-safety.md",
        "any_of": ["12 month", "twelve month", "one year", "a year"],
        "note": "TRAP: several documents mention durations.",
    },
    {
        "question": "When are the lab induction sessions held?",
        "expect": "answerable",
        "source": "lab-safety.md",
        "any_of": ["first monday", "monday"],
        "note": "TRAP: membership-faq.md also has a recurring weekday (Thursday).",
    },
    {
        "question": "How much does membership cost?",
        "expect": "answerable",
        "source": "membership-faq.md",
        "any_of": ["150"],
        "note": "TRAP: two other documents contain money amounts.",
    },
    {
        "question": "When does the club meet?",
        "expect": "answerable",
        "source": "membership-faq.md",
        "any_of": ["thursday"],
        "note": "TRAP: Room B204 appears in two documents.",
    },
    {
        "question": "Which filament types are allowed in the 3D printer?",
        "expect": "answerable",
        "source": "printing-guide.md",
        "all_of": ["pla", "petg"],
        "note": "Needs both items, not just one.",
    },
    {
        "question": "I have never been to the workshop. What do I need before I can book the 3D printer, and when can I get it?",
        "expect": "answerable",
        "source": "printing-guide.md",
        "all_of": ["induction", "monday"],
        "note": "MULTI-HOP: requirement is in printing-guide.md, the schedule is in lab-safety.md. Needs both files at once.",
    },
    {
        "question": "Who do I report a workshop injury to, and how quickly?",
        "expect": "answerable",
        "source": "lab-safety.md",
        "all_of": ["coordinator", "24"],
        "note": "TRAP: 'within 24 hours' also appears in printing-guide.md for failed prints.",
    },
    {
        "question": "Is there a coffee machine in the workshop?",
        "expect": "unanswerable",
        "source": "",
        "note": "GATE TEST: sounds exactly like the corpus, but no document answers it.",
    },
    {
        "question": "What is the wifi password?",
        "expect": "unanswerable",
        "source": "",
        "note": "GATE TEST: plausible club question, absent from the corpus.",
    },
    {
        "question": "Tell me a joke.",
        "expect": "unanswerable",
        "source": "",
        "note": "The case that failed on the single-document corpus.",
    },
    {
        "question": "Who won the 2022 World Cup?",
        "expect": "unanswerable",
        "source": "",
        "note": "Baseline: should score far below the gate.",
    },
    {
        "question": "   ",
        "expect": "edge-empty",
        "source": "",
        "note": "Edge case: empty input.",
    },
]


# ---------------------------------------------------------------------------
# RUNNING ONE QUESTION
# ---------------------------------------------------------------------------

def run_question(embedding_client, chat_client, question):
    """Return a dict describing what the pipeline did with this question."""
    if not question.strip():
        return {"answer": "(no input)", "score": 0.0, "gated": True,
                "sources": [], "cited": []}

    results = get_top_chunks(embedding_client, question, top_k=TOP_K)
    score = results[0][0] if results else 0.0
    sources = [source for _, source, _ in results]

    if score < RELEVANCE_THRESHOLD:
        return {"answer": REFUSAL, "score": score, "gated": True,
                "sources": sources, "cited": []}

    context, sources_by_number = build_context(results)
    messages = [
        {"role": "system", "content": SYSTEM_TEMPLATE.format(context=context)},
        {"role": "user", "content": question},
    ]

    text = ""
    for chunk in chat_client.complete_streaming_chat(messages):
        if chunk.choices and chunk.choices[0].delta.content:
            text += chunk.choices[0].delta.content

    # Resolve [n] markers into filenames the same way app.py does, so the
    # evaluation measures the shipped behaviour and not a copy of it.
    if REFUSAL.lower() in text.lower():
        return {"answer": text.strip(), "score": score, "gated": False,
                "sources": sources, "cited": []}

    cleaned, cited = resolve_citations(text, sources_by_number, results[0][1])
    return {"answer": cleaned, "score": score, "gated": False,
            "sources": sources, "cited": cited}


# ---------------------------------------------------------------------------
# GRADING
#
# Keyword matching is crude. It cannot tell "PLA is allowed" from "PLA is not
# allowed", so treat AUTO verdicts as a first pass and read the answers.
# ---------------------------------------------------------------------------

def grade(case, run):
    """Compare what happened against what the case expected."""
    answer_lc = run["answer"].lower()
    expected = case.get("source", "")

    g = {
        "retrieved": None,   # expected file anywhere in top-K
        "top1": None,        # expected file is the single best match
        "content": None,     # answer contains the expected fact
        "cited": None,       # answer names the expected file
        "miscited": [],      # other corpus files the answer named
        "verdict": "",
    }

    # --- questions the corpus cannot answer -------------------------------
    if case["expect"] in ("unanswerable", "edge-empty"):
        refused = run["gated"] or REFUSAL.lower() in answer_lc
        g["verdict"] = "PASS" if refused else "FAIL"
        g["content"] = refused
        return g

    # --- questions the corpus can answer ----------------------------------
    if run["gated"]:
        # Refused something it should have answered - a false negative.
        g["retrieved"] = expected in run["sources"]
        g["top1"] = bool(run["sources"]) and run["sources"][0] == expected
        g["content"] = False
        g["cited"] = False
        g["verdict"] = "FAIL (gated)"
        return g

    g["retrieved"] = expected in run["sources"]
    g["top1"] = bool(run["sources"]) and run["sources"][0] == expected

    any_of = [k.lower() for k in case.get("any_of", [])]
    all_of = [k.lower() for k in case.get("all_of", [])]
    ok = True
    if any_of:
        ok = ok and any(k in answer_lc for k in any_of)
    if all_of:
        ok = ok and all(k in answer_lc for k in all_of)
    g["content"] = ok

    # Citation: the resolved source list, not a string search of the answer.
    # `also_ok` lists files that genuinely contain the same fact, so citing
    # them alongside the expected file is correct rather than spurious.
    cited = run.get("cited", [])
    acceptable = {expected} | set(case.get("also_ok", []))
    g["cited"] = expected in cited
    g["miscited"] = [f for f in cited if f not in acceptable]

    if g["content"] and g["cited"] and not g["miscited"]:
        g["verdict"] = "PASS"
    elif g["content"]:
        g["verdict"] = "PARTIAL"
    else:
        g["verdict"] = "FAIL"
    return g


# ---------------------------------------------------------------------------
# REPORT
# ---------------------------------------------------------------------------

def tick(value):
    if value is None:
        return "–"
    return "yes" if value else "**no**"


def write_report(rows):
    answerable = [r for r in rows if r["case"]["expect"] == "answerable"]
    others = [r for r in rows if r["case"]["expect"] != "answerable"]

    def rate(items, key):
        if not items:
            return "n/a"
        hits = sum(1 for i in items if i["grade"].get(key))
        return f"{hits}/{len(items)}"

    verdicts = {}
    for r in rows:
        v = r["grade"]["verdict"].split()[0]
        verdicts[v] = verdicts.get(v, 0) + 1

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        f.write("# Multi-Document Evaluation Results\n\n")
        f.write(
            f"Corpus: {len(CORPUS_FILES)} overlapping documents "
            f"({', '.join('`' + c + '`' for c in CORPUS_FILES)}).\n"
            f"Gate threshold: **{RELEVANCE_THRESHOLD}**. Top-K: **{TOP_K}**.\n\n"
        )

        f.write("## Summary\n\n")
        f.write("| Measure | Result |\n|---|---|\n")
        f.write(f"| Correct file retrieved (in top-{TOP_K}) | {rate(answerable, 'retrieved')} |\n")
        f.write(f"| Correct file ranked #1 | {rate(answerable, 'top1')} |\n")
        f.write(f"| Correct fact in the answer | {rate(answerable, 'content')} |\n")
        f.write(f"| Correct file cited | {rate(answerable, 'cited')} |\n")
        miscited = sum(1 for r in answerable if r["grade"]["miscited"])
        f.write(f"| Answers citing a **wrong** file | {miscited}/{len(answerable)} |\n")
        gated_ok = sum(1 for r in others if r["grade"]["verdict"] == "PASS")
        f.write(f"| Non-answerable questions handled | {gated_ok}/{len(others)} |\n\n")
        f.write("Verdicts: " + ", ".join(f"**{v}** {n}" for v, n in sorted(verdicts.items())) + "\n\n")

        f.write("## Per-question results\n\n")
        f.write("| # | Question | Expected file | Score | s | Gated | Retrieved | Top-1 | Content | Cited | Verdict |\n")
        f.write("|---|---|---|---|---|---|---|---|---|---|---|\n")
        for i, r in enumerate(rows, 1):
            c, run, g = r["case"], r["run"], r["grade"]
            q = c["question"].strip() or "(empty)"
            if len(q) > 70:
                q = q[:67] + "..."
            f.write(
                f"| {i} | {q} | {c['source'] or '–'} | {run['score']:.3f} | "
                f"{r['seconds']:.1f} | {'yes' if run['gated'] else 'no'} | "
                f"{tick(g['retrieved'])} | {tick(g['top1'])} | {tick(g['content'])} | "
                f"{tick(g['cited'])} | **{g['verdict']}** |\n"
            )

        f.write("\n## Answers in full\n\n")
        for i, r in enumerate(rows, 1):
            c, run, g = r["case"], r["run"], r["grade"]
            f.write(f"### {i}. {c['question'].strip() or '(empty input)'}\n\n")
            f.write(f"*{c['note']}*\n\n")
            f.write(f"- Expected source: `{c['source'] or 'none'}`\n")
            f.write(f"- Retrieved: {', '.join('`' + s + '`' for s in run['sources']) or '–'}\n")
            if run.get("cited"):
                f.write(f"- Cited: {', '.join('`' + s + '`' for s in run['cited'])}\n")
            f.write(f"- Top score: {run['score']:.3f}  ·  {r['seconds']:.1f}s  ·  "
                    f"gated: {'yes' if run['gated'] else 'no'}\n")
            if g["miscited"]:
                f.write(f"- **Cited the wrong file:** {', '.join(g['miscited'])}\n")
            f.write(f"- Verdict: **{g['verdict']}**\n\n")
            f.write("> " + run["answer"].replace("\n", "\n> ") + "\n\n")

        f.write("---\n\n")
        f.write(
            "Verdicts are assigned by keyword matching and are a first pass only. "
            "Keyword matching cannot distinguish \"PLA is allowed\" from \"PLA is not "
            "allowed\", so read the answers above before trusting the table.\n"
        )


def main():
    missing = [c for c in CORPUS_FILES if not os.path.exists(os.path.join("docs", c))]
    if missing:
        print("These test documents are not in docs/:")
        for m in missing:
            print(f"  - {m}")
        print("\nCopy them in and rebuild the index first:")
        print("  copy tests\\corpus\\*.md docs\\")
        print("  python ingest.py")
        return

    embedding_client, chat_client = load_models()
    print(f"\nRunning {len(TEST_CASES)} test cases against {len(CORPUS_FILES)} documents...\n")

    rows = []
    for i, case in enumerate(TEST_CASES, 1):
        start = time.time()
        run = run_question(embedding_client, chat_client, case["question"])
        seconds = time.time() - start
        g = grade(case, run)
        rows.append({"case": case, "run": run, "grade": g, "seconds": seconds})

        q = case["question"].strip() or "(empty)"
        print(f"[{i:2}/{len(TEST_CASES)}] {g['verdict']:<12} {q[:55]}")
        print(f"          score={run['score']:.3f}  {seconds:.1f}s  "
              f"retrieved={run['sources']}")
        if g["miscited"]:
            print(f"          !! cited wrong file: {g['miscited']}")
        print()

    write_report(rows)
    print(f"Wrote {RESULTS_PATH}")


if __name__ == "__main__":
    main()

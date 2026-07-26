"""
Lesson 9 - Testing & evaluation harness.

Runs a fixed battery of test questions through the app pipeline, records the
gate score, the answer, and the response time for each, then writes a
ready-to-submit results table to eval_results.md.

Edit TEST_CASES to add your own questions. Run it with:   python evaluate.py
"""

import time

from app import (
    load_models,
    SYSTEM_TEMPLATE,
    RELEVANCE_THRESHOLD,
    REFUSAL,
    TOP_K,
)
from retrieve import get_top_chunks

# (question, category) - category is what you EXPECT to happen.
TEST_CASES = [
    ("How long is the program?", "answerable"),
    ("How many phases are there?", "answerable"),
    ("What is Foundry Local?", "answerable"),
    ("What is Week 1 about?", "answerable"),
    ("Which database is used to store the embeddings?", "answerable"),
    ("What happens in the final week?", "answerable"),
    ("What is the capital of Syria?", "unanswerable"),
    ("Who won the 2022 World Cup?", "unanswerable"),
    ("Tell me a joke.", "unanswerable"),
    ("   ", "edge-empty"),
]


def generate_answer(embedding_client, chat_client, question):
    """Return (answer_text, top_score, was_gated)."""
    if not question.strip():
        return "(no input)", 0.0, True

    results = get_top_chunks(embedding_client, question, top_k=TOP_K)
    top_score = results[0][0] if results else 0.0

    if top_score < RELEVANCE_THRESHOLD:
        return REFUSAL, top_score, True

    context = "\n\n".join(f"[from {s}]\n{c}" for _, s, c in results)
    messages = [
        {"role": "system", "content": SYSTEM_TEMPLATE.format(context=context)},
        {"role": "user", "content": question},
    ]

    text = ""
    for chunk in chat_client.complete_streaming_chat(messages):
        if chunk.choices and chunk.choices[0].delta.content:
            text += chunk.choices[0].delta.content
    return text.strip(), top_score, False


def main():
    embedding_client, chat_client = load_models()
    print("\nRunning evaluation battery...\n")

    rows = []
    for question, category in TEST_CASES:
        start = time.time()
        answer, score, gated = generate_answer(embedding_client, chat_client, question)
        elapsed = time.time() - start
        rows.append((question.strip() or "(empty)", category, score, elapsed, gated, answer))
        print(f"[{category}] {question.strip() or '(empty)'}  "
              f"(score={score:.3f}, {elapsed:.1f}s)\n  -> {answer[:100]}\n")

    # Write a Markdown results table you can review and submit.
    with open("eval_results.md", "w", encoding="utf-8") as f:
        f.write("# Evaluation Results\n\n")
        f.write(f"Chat model gate threshold: {RELEVANCE_THRESHOLD}. "
                f"Top-K retrieved: {TOP_K}.\n\n")
        f.write("| # | Question | Expected | Score | Time (s) | Gated? | Answer | Verdict |\n")
        f.write("|---|----------|----------|-------|----------|--------|--------|---------|\n")
        for i, (q, cat, score, elapsed, gated, answer) in enumerate(rows, 1):
            clean = answer.replace("\n", " ").replace("|", "/")
            f.write(f"| {i} | {q} | {cat} | {score:.3f} | {elapsed:.1f} | "
                    f"{'yes' if gated else 'no'} | {clean} |  |\n")
        avg = sum(r[3] for r in rows) / len(rows)
        f.write(f"\nAverage response time: {avg:.1f}s across {len(rows)} questions.\n")
        f.write("\nFill in the **Verdict** column (pass/fail) after reviewing each answer.\n")

    print("Wrote eval_results.md")


if __name__ == "__main__":
    main()

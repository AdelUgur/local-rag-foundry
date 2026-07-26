"""
Lesson 8 - The final Local RAG assistant (full pipeline + optimizations).

Combines everything: retrieve the most relevant chunks from rag.db, gate on a
relevance score so off-topic questions are refused WITHOUT bothering the model,
then have a capable local LLM (phi-3.5-mini) answer using only that context.

Run it with:   python app.py
(Run ingest.py first if rag.db doesn't exist yet.)
"""

import re

from foundry_local_sdk import Configuration, FoundryLocalManager
from retrieve import get_top_chunks   # retriever from Lesson 6

EMBED_MODEL = "qwen3-embedding-0.6b"
CHAT_MODEL = "phi-3.5-mini"           # stronger model -> follows grounding rules
TOP_K = 5   # was 3: with a 4-document corpus, top-3 filled up with chunks from
            # a single file and a multi-hop question never saw the second file.
            # See eval_multi_results_topk3.md vs eval_multi_results.md.

# If the best chunk scores below this, we treat the question as "not in the
# notes" and refuse WITHOUT calling the model. This is the robust fix for the
# "capital of France" leak: it doesn't depend on the model behaving.
# CALIBRATE IT: run retrieve.py, note the top score for a real question vs a
# nonsense one, and set this between them.
RELEVANCE_THRESHOLD = 0.40   # calibrated: real Qs >= 0.42, off-topic <= 0.39 (some overlap)

REFUSAL = "I don't have that in your notes."

SYSTEM_TEMPLATE = (
    "You are an assistant that answers questions ONLY from the user's course "
    "notes, provided below as context.\n"
    "Rules:\n"
    "- Use only the context. Never use outside knowledge, even for famous facts.\n"
    f"- If the context does not clearly answer the question, reply with EXACTLY "
    f"\"{REFUSAL}\" and nothing else - no explanation, no outside knowledge, no jokes.\n"
    "- Mark ONLY the passages your answer actually came from, with their number "
    "in square brackets, like [1] or [1][3]. Do not mark a passage you merely "
    "read. Do not write file names yourself.\n"
    "- Answer concisely in your own words. Do not paste the context back.\n\n"
    "Context:\n{context}"
)


# ---------- CITATIONS ----------
#
# Earlier versions asked the model to write the source filename itself. That
# worked at TOP_K=3 (10/11 correct) and collapsed at TOP_K=5 (4/11): with more
# passages to attend to, the model quietly dropped the citation instruction
# while its answers stayed correct. See eval_multi_results_topk*.md.
#
# The fix is to stop asking the model to do bookkeeping. It marks passages by
# number - a much easier instruction to follow - and the code maps those
# numbers back to filenames. Attribution becomes a property of the program
# instead of something we hope a 3.8B model remembers.

CITATION_PATTERN = re.compile(r"\[(\d+)\]")

# The model sometimes writes "..., as stated in [1]." Deleting just the marker
# leaves a dangling "as stated in." - so strip the lead-in phrase with it.
CITATION_LEADIN = re.compile(
    r"[,;]?\s*\(?\s*(?:as\s+(?:stated|mentioned|described|noted|specified|"
    r"outlined|set\s+out)\s+in|according\s+to|as\s+per|per|see|sources?)"
    r"\s*:?\s*(?:\[\d+\]\s*)+\)?",
    re.IGNORECASE,
)

# "[1] and [2]" / "[1], [2]" -> "[1][2]", so a lead-in phrase is removed
# together with every marker it introduces, not just the first.
CITATION_JOIN = re.compile(r"\]\s*(?:,|and|&)\s*\[")

# A removed lead-in can leave a sentence starting with stray punctuation.
LEADING_PUNCT = re.compile(r"(^|(?<=[.!?])\s*)\s*[,;:]\s*")


def build_context(results):
    """
    Number the retrieved chunks so the model can refer to them as [1], [2]...

    Returns (context_text, sources_by_number).
    """
    blocks = []
    sources_by_number = {}
    for number, (_score, source, content) in enumerate(results, start=1):
        sources_by_number[number] = source
        blocks.append(f"[{number}] from {source}\n{content}")
    return "\n\n".join(blocks), sources_by_number


def resolve_citations(answer, sources_by_number, fallback_source=None):
    """
    Replace the model's [n] markers with the real filenames behind them.

    Returns (cleaned_answer, [filenames in the order they were first cited]).

    If the model marked nothing, fall back to the single best-matching chunk:
    the answer was generated from that context, so reporting it is honest, and
    it means an answer is never shown without a source.
    """
    files = []
    for number in CITATION_PATTERN.findall(answer):
        source = sources_by_number.get(int(number))
        if source and source not in files:
            files.append(source)

    if not files and fallback_source:
        files = [fallback_source]

    cleaned = CITATION_JOIN.sub("][", answer)      # "[1] and [2]" -> "[1][2]"
    cleaned = CITATION_LEADIN.sub(" ", cleaned)    # ", as stated in [1]." -> " ."
    cleaned = CITATION_PATTERN.sub("", cleaned)    # any bare markers left
    cleaned = re.sub(r"\(\s*\)", "", cleaned)      # empty parens left behind
    cleaned = re.sub(r"\s+([.,;:!?])", r"\1", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = LEADING_PUNCT.sub(r"\1", cleaned)
    return cleaned.strip(), files


def load_models():
    config = Configuration(app_name="rag_assistant")
    FoundryLocalManager.initialize(config)
    manager = FoundryLocalManager.instance
    manager.download_and_register_eps()

    embed_model = manager.catalog.get_model(EMBED_MODEL)
    embed_model.load()
    embedding_client = embed_model.get_embedding_client()

    chat_model = manager.catalog.get_model(CHAT_MODEL)
    chat_model.download(lambda p: print(f"\rDownloading chat model: {p:.0f}%", end="", flush=True))
    print()
    chat_model.load()
    chat_client = chat_model.get_chat_client()

    return embedding_client, chat_client


def answer_query(embedding_client, chat_client, question, top_k=TOP_K, show_sources=True):
    # 1. RETRIEVE
    results = get_top_chunks(embedding_client, question, top_k=top_k)
    top_score = results[0][0] if results else 0.0

    # 2. GATE - refuse off-topic questions before spending time on the model.
    if top_score < RELEVANCE_THRESHOLD:
        print(f"\nAnswer: {REFUSAL}")
        print(f"  (best match scored {top_score:.3f}, below the {RELEVANCE_THRESHOLD} threshold)\n")
        return

    if show_sources:
        srcs = ", ".join(sorted({source for _, source, _ in results}))
        print(f"  [retrieved from: {srcs} | top score {top_score:.3f}]")

    # 3. AUGMENT
    context, sources_by_number = build_context(results)
    messages = [
        {"role": "system", "content": SYSTEM_TEMPLATE.format(context=context)},
        {"role": "user", "content": question},
    ]

    # 4. GENERATE
    # Buffer while streaming: the [n] markers can only be resolved once the
    # whole answer has arrived, but we still want it to appear as it is typed.
    print("\nAnswer: ", end="", flush=True)
    raw = ""
    for chunk in chat_client.complete_streaming_chat(messages):
        if not chunk.choices:
            continue
        content = chunk.choices[0].delta.content
        if content:
            raw += content
            print(content, end="", flush=True)
    print()

    # 5. ATTRIBUTE
    if REFUSAL.lower() not in raw.lower():
        _cleaned, files = resolve_citations(raw, sources_by_number, results[0][1])
        if files:
            print(f"  Sources: {', '.join(files)}")
    print()


def main():
    embedding_client, chat_client = load_models()
    print('\nLocal RAG assistant ready. Ask about your notes (or "quit").\n')
    while True:
        question = input("Question: ").strip()
        if not question or question.lower() == "quit":
            break
        answer_query(embedding_client, chat_client, question)


if __name__ == "__main__":
    main()

"""
Lesson 7 - Generate grounded answers with the local LLM.

This is the full RAG loop: retrieve the most relevant chunks for a question,
augment a prompt with them, and have the local chat model generate an answer
that uses ONLY those chunks - citing sources and admitting when it doesn't know.

Run it with:   python answer.py
"""

from foundry_local_sdk import Configuration, FoundryLocalManager
from retrieve import get_top_chunks   # reuse the retriever from Lesson 6

EMBED_MODEL = "qwen3-embedding-0.6b"
CHAT_MODEL = "qwen2.5-0.5b"

SYSTEM_TEMPLATE = (
    "You are a helpful assistant answering questions about the user's course "
    "notes. Use ONLY the context below to answer. If the context does not "
    "contain the answer, say you don't know - do not use outside knowledge and "
    "do not guess. When you answer, cite the source filename(s) you used.\n\n"
    "Context:\n{context}"
    "If the answer is not explicitly in the context, respond exactly: 'I don't have that in your notes.'"
)


def load_models():
    """Start Foundry Local and load BOTH the embedding and chat models."""
    config = Configuration(app_name="rag_assistant")
    FoundryLocalManager.initialize(config)
    manager = FoundryLocalManager.instance
    manager.download_and_register_eps()

    embed_model = manager.catalog.get_model(EMBED_MODEL)
    embed_model.load()
    embedding_client = embed_model.get_embedding_client()

    chat_model = manager.catalog.get_model(CHAT_MODEL)
    chat_model.download(lambda p: print(f"\rLoading chat model: {p:.0f}%", end="", flush=True))
    print()
    chat_model.load()
    chat_client = chat_model.get_chat_client()

    return embedding_client, chat_client


def answer_query(embedding_client, chat_client, question, top_k=3):
    """Retrieve context, build the grounded prompt, and stream the answer."""
    # 1. RETRIEVE
    results = get_top_chunks(embedding_client, question, top_k=top_k)

    # 2. AUGMENT - fold the chunks (with their source names) into the prompt.
    context = "\n\n".join(
        f"[from {source}]\n{content}" for _, source, content in results
    )
    messages = [
        {"role": "system", "content": SYSTEM_TEMPLATE.format(context=context)},
        {"role": "user", "content": question},
    ]

    # 3. GENERATE - stream the model's answer token by token.
    print("\nAnswer: ", end="", flush=True)
    for chunk in chat_client.complete_streaming_chat(messages):
        if not chunk.choices:
            continue
        content = chunk.choices[0].delta.content
        if content:
            print(content, end="", flush=True)
    print("\n")


def main():
    embedding_client, chat_client = load_models()
    print('Assistant ready. Ask about your notes (or "quit").\n')

    while True:
        question = input("Question: ").strip()
        if not question or question.lower() == "quit":
            break
        answer_query(embedding_client, chat_client, question)


if __name__ == "__main__":
    main()

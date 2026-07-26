"""
Lesson 3 - Embeddings & vector search.

We turn five sentences into vectors, turn a query into a vector, then rank the
sentences by cosine similarity to the query. The winning sentence shares NO
words with the query - it wins on meaning alone. That's semantic search.

Run it with:   python embeddings_demo.py
"""

import math
from foundry_local_sdk import Configuration, FoundryLocalManager

# A tiny knowledge base: five unrelated facts.
documents = [
    "Refunds are processed within five business days.",
    "Our office is open Monday to Friday, 9am to 5pm.",
    "Password resets can be done from the login page.",
    "The library closes at 9pm on weekdays and 5pm on weekends.",
    "Free shipping applies to orders over fifty dollars.",
]

# Try changing this line to your own question and re-run!
query = "How do I get my money back?"


def cosine_similarity(a, b):
    """Angle-based similarity between two vectors. 1.0 = identical direction."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


def main():
    # Start Foundry Local and load the EMBEDDING model (not the chat model).
    config = Configuration(app_name="rag_assistant")
    FoundryLocalManager.initialize(config)
    manager = FoundryLocalManager.instance
    manager.download_and_register_eps()

    model = manager.catalog.get_model("qwen3-embedding-0.6b")
    model.download(lambda p: print(f"\rDownloading embedding model: {p:.0f}%", end="", flush=True))
    print()
    model.load()
    client = model.get_embedding_client()

    # Embed all documents in ONE batch call (plural method, takes a list).
    response = client.generate_embeddings(documents)
    doc_embeddings = [item.embedding for item in response.data]
    print(f"Embedded {len(doc_embeddings)} documents. "
          f"Each vector has {len(doc_embeddings[0])} numbers.\n")

    # Embed the single query (singular method, takes one string).
    q = client.generate_embedding(query)
    query_embedding = q.data[0].embedding

    # Score every document against the query and sort best-first.
    scores = [(cosine_similarity(query_embedding, emb), doc)
              for emb, doc in zip(doc_embeddings, documents)]
    scores.sort(reverse=True)

    print(f'Query: "{query}"\n')
    print("Ranked by similarity (higher = closer in meaning):")
    for score, doc in scores:
        print(f"  {score:.3f}  {doc}")

    model.unload()


if __name__ == "__main__":
    main()

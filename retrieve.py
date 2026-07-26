"""
Lesson 6 - The retrieval pipeline.

Given a question, embed it, load all chunk vectors from rag.db, score them by
cosine similarity, and return the top-K most relevant chunks (with score and
source filename). Run this to interactively test what your retriever finds.

Run it with:   python retrieve.py
"""

import json
import math
import sqlite3
from foundry_local_sdk import Configuration, FoundryLocalManager

DB_PATH = "rag.db"
TOP_K = 3


def cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


def get_embedding_client():
    config = Configuration(app_name="rag_assistant")
    FoundryLocalManager.initialize(config)
    manager = FoundryLocalManager.instance
    manager.download_and_register_eps()
    model = manager.catalog.get_model("qwen3-embedding-0.6b")
    model.load()
    return model.get_embedding_client()


def get_top_chunks(client, query, top_k=TOP_K):
    """
    Return the top_k most relevant chunks for `query` as a list of
    (score, source, content) tuples, best match first.
    """
    query_embedding = client.generate_embedding(query).data[0].embedding

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT source, content, embedding FROM documents").fetchall()
    conn.close()

    scored = []
    for row in rows:
        emb = json.loads(row["embedding"])
        score = cosine_similarity(query_embedding, emb)
        scored.append((score, row["source"], row["content"]))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_k]


def main():
    client = get_embedding_client()
    print('Retriever ready. Type a question (or "quit").\n')

    while True:
        query = input("Question: ").strip()
        if not query or query.lower() == "quit":
            break

        results = get_top_chunks(client, query)
        print(f"\nTop {len(results)} chunks:\n")
        for rank, (score, source, content) in enumerate(results, start=1):
            preview = content[:200].replace("\n", " ")
            print(f"[{rank}] score={score:.3f}  source={source}")
            print(f"    {preview}...\n")


if __name__ == "__main__":
    main()

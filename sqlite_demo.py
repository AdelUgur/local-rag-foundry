"""
Lesson 4 - Store embeddings in SQLite.

We embed the five sentences ONCE, save them (text + vector) into a single
database file called rag.db, then read them back and run the same similarity
search - this time using vectors loaded FROM the database.

Run it with:   python sqlite_demo.py
"""

import json
import math
import sqlite3
from foundry_local_sdk import Configuration, FoundryLocalManager

DB_PATH = "rag.db"

documents = [
    "Refunds are processed within five business days.",
    "Our office is open Monday to Friday, 9am to 5pm.",
    "Password resets can be done from the login page.",
    "The library closes at 9pm on weekdays and 5pm on weekends.",
    "Free shipping applies to orders over fifty dollars.",
]

query = "How do I get my money back?"


def cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


def get_embedding_client():
    """Start Foundry Local and return a loaded embedding client."""
    config = Configuration(app_name="rag_assistant")
    FoundryLocalManager.initialize(config)
    manager = FoundryLocalManager.instance
    manager.download_and_register_eps()
    model = manager.catalog.get_model("qwen3-embedding-0.6b")
    model.download(lambda p: print(f"\rDownloading embedding model: {p:.0f}%", end="", flush=True))
    print()
    model.load()
    return model.get_embedding_client()


def build_database(client):
    """Embed every document and write it into rag.db."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Start fresh each run so we don't pile up duplicate rows.
    cur.execute("DROP TABLE IF EXISTS documents")
    cur.execute("""
        CREATE TABLE documents (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            content   TEXT NOT NULL,
            embedding TEXT NOT NULL
        )
    """)

    # Embed all documents in one batch, then insert row by row.
    response = client.generate_embeddings(documents)
    for text, item in zip(documents, response.data):
        emb_json = json.dumps(item.embedding)          # list -> text
        cur.execute(
            "INSERT INTO documents (content, embedding) VALUES (?, ?)",
            (text, emb_json),                          # ? placeholders = safe
        )

    conn.commit()
    conn.close()
    print(f"Stored {len(documents)} documents in {DB_PATH}")


def search(client, query, top_k=5):
    """Load vectors FROM the database and rank them against the query."""
    query_embedding = client.generate_embedding(query).data[0].embedding

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row          # lets us use row["content"]
    rows = conn.execute("SELECT content, embedding FROM documents").fetchall()
    conn.close()

    scores = []
    for row in rows:
        embedding = json.loads(row["embedding"])       # text -> list
        scores.append((cosine_similarity(query_embedding, embedding), row["content"]))
    scores.sort(reverse=True)

    print(f'\nQuery: "{query}"\n')
    print("Ranked by similarity (vectors loaded from rag.db):")
    for score, content in scores[:top_k]:
        print(f"  {score:.3f}  {content}")


def main():
    client = get_embedding_client()
    build_database(client)
    search(client, query)


if __name__ == "__main__":
    main()

"""
Lesson 5 - Document ingestion & chunking.

Reads every file in the docs/ folder (.txt, .md, .pdf, .docx), splits each into
smaller passages ("chunks"), embeds every chunk, and stores it in rag.db along
with the source filename. Run this once whenever your notes change.

Run it with:   python ingest.py
"""

import json
import os
import re
import sqlite3
from foundry_local_sdk import Configuration, FoundryLocalManager

DOCS_DIR = "docs"
DB_PATH = "rag.db"
CHUNK_TARGET_CHARS = 800   # roughly 1-3 paragraphs per chunk


# ---------- 1. READING TEXT OUT OF DIFFERENT FILE TYPES ----------

def read_txt(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def read_pdf(path):
    from pypdf import PdfReader
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def read_docx(path):
    import docx  # from the python-docx package
    document = docx.Document(path)
    return "\n".join(p.text for p in document.paragraphs)


def load_file(path):
    """Pick the right reader based on the file extension."""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".txt", ".md"):
        return read_txt(path)
    if ext == ".pdf":
        return read_pdf(path)
    if ext == ".docx":
        return read_docx(path)
    return None   # unsupported type -> skip


# ---------- 2. SPLITTING TEXT INTO CHUNKS ----------

def split_long_block(text, target_chars):
    """
    Break a block that is bigger than target_chars into smaller pieces by
    sentence boundaries (. ! ?). If a single sentence is still too long,
    hard-split it by characters so nothing ever exceeds the target.
    """
    sentences = re.split(r"(?<=[.!?])\s+", text)
    pieces, current = [], ""
    for s in sentences:
        if len(s) > target_chars:                 # one giant sentence
            if current:
                pieces.append(current.strip())
                current = ""
            for i in range(0, len(s), target_chars):
                pieces.append(s[i:i + target_chars])
        elif current and len(current) + len(s) > target_chars:
            pieces.append(current.strip())
            current = s
        else:
            current = f"{current} {s}" if current else s
    if current.strip():
        pieces.append(current.strip())
    return pieces


def chunk_text(text, target_chars=CHUNK_TARGET_CHARS):
    """
    Turn a document into passages of about `target_chars` each:
      1. split on blank lines into paragraphs,
      2. break any paragraph bigger than the target into sentence-sized pieces,
      3. greedily glue small pieces back together up to the target.
    This keeps related sentences together while guaranteeing no giant chunks.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    # Step 1-2: make a flat list of units, none bigger than the target.
    units = []
    for para in paragraphs:
        if len(para) > target_chars:
            units.extend(split_long_block(para, target_chars))
        else:
            units.append(para)

    # Step 3: merge small units up to the target size.
    chunks, current = [], ""
    for unit in units:
        if current and len(current) + len(unit) > target_chars:
            chunks.append(current.strip())
            current = unit
        else:
            current = f"{current}\n\n{unit}" if current else unit
    if current.strip():
        chunks.append(current.strip())
    return chunks


# ---------- 3. EMBED + STORE ----------

def get_embedding_client():
    config = Configuration(app_name="rag_assistant")
    FoundryLocalManager.initialize(config)
    manager = FoundryLocalManager.instance
    manager.download_and_register_eps()
    model = manager.catalog.get_model("qwen3-embedding-0.6b")
    model.download(lambda p: print(f"\rDownloading embedding model: {p:.0f}%", end="", flush=True))
    print()
    model.load()
    return model.get_embedding_client()


def main():
    if not os.path.isdir(DOCS_DIR):
        print(f"No '{DOCS_DIR}' folder found. Create it and add your notes first.")
        return

    # Read every file and break it into chunks, remembering the source filename.
    all_chunks = []   # list of (source_filename, chunk_text)
    for name in sorted(os.listdir(DOCS_DIR)):
        path = os.path.join(DOCS_DIR, name)
        if not os.path.isfile(path):
            continue
        text = load_file(path)
        if not text or not text.strip():
            print(f"  skipped (empty/unsupported): {name}")
            continue
        chunks = chunk_text(text)
        for c in chunks:
            all_chunks.append((name, c))
        print(f"  {name}: {len(chunks)} chunks")

    if not all_chunks:
        print("No readable documents found in docs/. Add some notes and re-run.")
        return

    print(f"\nTotal chunks to embed: {len(all_chunks)}")

    # Embed all chunk texts in one batch call.
    client = get_embedding_client()
    texts = [chunk for _, chunk in all_chunks]
    response = client.generate_embeddings(texts)

    # Store into SQLite, now with a 'source' column for citations later.
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS documents")
    cur.execute("""
        CREATE TABLE documents (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            source    TEXT NOT NULL,
            content   TEXT NOT NULL,
            embedding TEXT NOT NULL
        )
    """)
    for (source, chunk), item in zip(all_chunks, response.data):
        cur.execute(
            "INSERT INTO documents (source, content, embedding) VALUES (?, ?, ?)",
            (source, chunk, json.dumps(item.embedding)),
        )
    conn.commit()

    count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    conn.close()
    print(f"\nDone. Stored {count} chunks in {DB_PATH}.")


if __name__ == "__main__":
    main()

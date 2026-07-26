# docs/ — your source documents

Put the files you want the assistant to answer from in this folder.

Supported formats: `.txt`, `.md`, `.pdf`, `.docx`

Then build the index:

```bat
python ingest.py
```

This reads every file here, splits it into ~800-character sentence-aware
chunks, embeds each chunk, and writes them to `rag.db`. Re-run it whenever you
add or change a document.

## Why this folder is empty in the repository

The contents of `docs/` are excluded by `.gitignore`. Source notes are personal
material and don't belong in a public repository — the code is the deliverable,
the notes are yours.

The evaluation in `eval_results.md` was produced against a single course
planning document (a PDF of roughly 40 chunks). Any comparable document will
reproduce the same behaviour.

## Notes on document quality

- **Scanned or image-only PDFs produce no text.** The extractor reads embedded
  text only; there is no OCR step. If retrieval returns nothing for a PDF,
  check that you can select text in it in a PDF viewer.
- **More documents means better coverage but noisier retrieval.** With a large
  corpus, consider raising `TOP_K` in `app.py`.

# Real Scans Directory (`data/real_scans/`)

Place your owned or openly licensed scanned images and companion human-written ground-truth transcripts here:

- `doc_01.png` (or `.jpg`) - The scanned image
- `doc_01.txt` - Human-typed exact text transcript of the document

During verification, the engine evaluates the worker's OCR output against the companion `.txt` transcript using Character Error Rate (CER Levenshtein distance <= 5%).

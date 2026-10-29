# Test Documents Directory (`data/real_scans/`)

This directory contains **generated test documents with exact ground truth**, not real-world physical scans.

- `doc_01.png` - `doc_05.png`: Synthetic image renderings of receipt-style, utility bill-style, invoice-style, printed technical paragraphs, and shipping manifests. Rendered with varied fonts, sizes, slight skew, and Gaussian noise so Tesseract OCR is realistically challenged.
- `doc_01.txt` - `doc_05.txt`: Exact ground-truth source text corresponding to each generated image.

### Realism Notice
While the image files are generated test documents, **Tesseract execution, Character Error Rate (CER) calculation, and PayPal Sandbox payouts are 100% REAL**.
During verification, the engine executes local Tesseract OCR against the image and evaluates output fidelity against the companion ground-truth `.txt` transcript using Levenshtein Character Error Rate (CER $\le 5\%$).

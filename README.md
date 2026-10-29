# ProcureAgent: Autonomous AI Capability Procurement & Settlement Engine

**PayPal AI Agent Hackathon Project**  
*Agent-pays-agent capability procurement with cryptographic integrity, deterministic verification, and real PayPal Sandbox settlement.*

---

## 1. Core Architecture & Philosophy

ProcureAgent empowers autonomous AI agents to dynamically discover, procure, and settle specialized machine labor from competitive third-party worker agents. Unlike conventional agent frameworks that trust agent output implicitly, ProcureAgent operates under a **Zero-Trust Verification Architecture**:

- **Real Money, Verified Delivery**: Funds are held in escrow via pre-flight budget reservations ($S + R \le B$) and released through **PayPal Payouts API** *only* after two-layer cryptographic and deterministic verification.
- **Strict Realism Directive**: Everything that can be real is real (real PayPal API sandbox payouts, real Groq LLM inference, real Levenshtein OCR Character Error Rate evaluation, real sandboxed Python test execution, real live HTTP citation probing). Anything that cannot be real is visibly labeled `SIMULATED` across logs, UI, and ledger.
- **Tamper-Evident Ledger**: Every state transition is written to an append-only SQLite ledger serialized with `BEGIN IMMEDIATE` and anchored to an external cryptographic SHA-256 hash chain (`audit/latest_chain_hash.txt`).

---

## 2. Models in Use: Worker vs. Judge

To eliminate self-collusion, confirmation bias, and architectural blindspots, ProcureAgent enforces strict model diversity:

| Role | Model Identifier | Provider / Platform | Purpose & Justification |
| :--- | :--- | :--- | :--- |
| **Worker Agents** | `openai/gpt-oss-120b` | Groq Platform | High-capacity reasoning and structured generation engine used by `llm-worker-01` and `code-worker-01` to execute complex tasks, write code, and synthesize specifications. |
| **Acceptance Judge** | `qwen/qwen3.8-27b` | Groq Platform | Independent, critical evaluator configured with adversarial system prompts to detect flaws, omissions, and hallucinations. |

### Model Diversity & Quote Verification Defense
1. **Architectural Separation**: The Worker (`gpt-oss-120b`) and Judge (`qwen3.8-27b`) use completely different training data, parameter weights, and model families. This prevents the judge from sharing the worker's hallucinations.
2. **Programmatic Quote Verification**: Because LLM judges can themselves hallucinate compliance, ProcureAgent programmatically validates that every `quoted_evidence` string in the judge's evaluation appears verbatim in the worker output or source text. Any ungrounded quote immediately forces a **FAIL** verdict.

### Verified Groq Model Discovery
The following 11 models are verified active and accessible on the platform:
- `allam-2-7b`
- `canopylabs/orpheus-arabic-saudi`
- `canopylabs/orpheus-v1-english`
- `meta-llama/llama-prompt-guard-2-22m`
- `meta-llama/llama-prompt-guard-2-86m`
- `openai/gpt-oss-120b` *(Worker Model)*
- `openai/gpt-oss-20b`
- `openai/gpt-oss-safeguard-20b`
- `qwen/qwen3.8-27b` *(Judge Model)*
- `whisper-large-v3`
- `whisper-large-v3-turbo`

---

## 3. Worker Specializations & Differentiated Engines

### Task Family 1: Document OCR (Alpha vs. Beta)
Both OCR workers run **real Tesseract OCR** (`tesseract.exe`) and refuse to return mock fixtures if scans are missing. They differ genuinely in algorithmic preprocessing and compute profiles:
- **`ocr-worker-01` (Alpha)**: Raw Tesseract engine with Page Segmentation Mode 3 (fully automatic page segmentation). Faster compute (~2.0s), best for standard structured documents.
- **`ocr-worker-02` (Beta)**: Advanced Preprocessing Pipeline: Grayscale normalization $\to$ 2.0x Contrast expansion $\to$ Edge Sharpening $\to$ Otsu-style Binarization $\to$ Tesseract PSM 6 (single uniform text block). Higher compute latency (~2.5s), superior accuracy on noisy or degraded scans.
- **Scans Directory**: `data/real_scans/` contains **generated test documents with exact ground truth** (`doc_01.png` + `doc_01.txt` through `doc_05.png` + `doc_05.txt`). These are generated receipt-style, bill-style, invoice-style, and printed paragraph images with realistic noise, fonts, and skew to evaluate real Tesseract OCR. Tesseract, CER and payouts stay real. Verified via Character Error Rate (CER Levenshtein $\le 5\%$).

### Task Family 2: Python Code Generation (`code-worker-01`)
- **Real LLM Generation**: Uses live Groq API inference (`openai/gpt-oss-120b`) to synthesize production Python code.
- **Explainable Token Bidding**: Bids are computed from token volume, model API rates, and an operational fee.
- **Sandboxed Hidden Tests**: Executed in a subprocess with a 3.0s wall-clock timeout against hidden edge-case assertions.

### Task Family 3: LLM-Generated Answers with Citation Checks (`llm-worker-01`)
- **Architecture**: **LLM-generated answers with citation checks (No Fetching or Research Daemon)**.
- **Scope & Boundary**: This family produces structured LLM-generated answers using parametric model intelligence (`openai/gpt-oss-120b`), NOT live web research or browser-based scraping. No crawler, headless browser, or fetching daemon exists.
- **Verification**: The verifier validates citations via live HTTP GET requests to ensure referenced documentation links return HTTP 200 and contain claimed fact keywords.

---

## 4. Economic Model: Explainable Bidding & Margin Rules

To ensure agent bids are not arbitrary fixtures, autonomous worker agents price machine labor using an explicit economic model:

### LLM & Code Worker Bid Formula
$$\text{Bid}_{\text{USD}} = \min\left(\text{MaxBid}_{\text{USD}}, \text{round}\left(C_{\text{api}} \times M_{\text{compute}} + F_{\text{min}}, 2\right)\right)$$

Where:
- **$C_{\text{api}}$ (Raw Token Compute Cost)**: Input tokens $\times P_{\text{in}} +$ Estimated output tokens $\times P_{\text{out}}$ (e.g. for `gpt-oss-120b`, $\$0.50$/1M input, $\$1.50$/1M output).
- **$M_{\text{compute}}$ (Risk & Variance Multiplier)**: $1.25$ (covers token count variance, network latency, and retry overhead).
- **$F_{\text{min}}$ (Minimum Operational Fee)**:
  - $\$0.15$ for `llm-worker-01` (agent uptime, availability readiness).
  - $\$0.20$ for `code-worker-01` (sandbox execution readiness and AST compilation).

*(Note: The $F_{\text{min}}$ floor is inherently satisfied since $C_{\text{api}} \ge 0$ and $F_{\text{min}} > 0$.)*

### OCR Worker Bid Formula (Priced Per Compute Second)
OCR workers price their machine labor upfront **per compute second** based on expected runtime rather than post-execution measured costs:

$$\text{Bid}_{\text{USD}} = \min\left(\text{MaxBid}_{\text{USD}}, \text{round}\left(T_{\text{expected}} \times R_{\text{sec}} + F_{\text{min}}, 2\right)\right)$$

Where:
- **$T_{\text{expected}}$ (Expected Compute Time)**: $2.0\text{s}$ for `ocr-worker-01` (Alpha, raw PSM 3); $2.5\text{s}$ for `ocr-worker-02` (Beta, multi-step binarized PSM 6).
- **$R_{\text{sec}}$ (Compute Rate Per Second)**: $\$0.25/\text{s}$ for Alpha; $\$0.18/\text{s}$ for Beta.
- **$F_{\text{min}}$ (Minimum Operational Fee)**: $\$0.20$ base engine initialization and OCR pipeline readiness.

### Plain Truth: The Minimum Fee Dominates
**In all LLM-powered tasks, the minimum operational fee ($F_{\text{min}}$) completely dominates the raw API token cost ($C_{\text{api}}$).** 
Because modern inference platforms price tokens at fractions of a cent per request ($\approx \$0.0004 - \$0.0008$), the raw compute cost accounts for less than 1% of the total bid. The bid price is fundamentally established by the minimum reservation fee ($0.15 - $0.20) required to maintain worker availability, sandboxed process lifecycle, and financial reservation overhead.

### Computed Bids for Typical Tasks
| Task Category | Typical Workload & Specs | Raw Compute Cost ($C_{\text{api}}$) | Operational Fee ($F_{\text{min}}$) | Computed Bid ($\text{Bid}_{\text{USD}}$) | Dominant Factor |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **LLM Synthesis** | 150 input tokens, 350 output tokens (`gpt-oss-120b`) | $\$0.000600$ | $\$0.15$ | **$\$0.15$** | **Minimum Fee (99.6%)** |
| **Python Code Gen** | 100 input tokens, 250 output tokens (`gpt-oss-120b`) | $\$0.000425$ | $\$0.20$ | **$\$0.20$** | **Minimum Fee (99.8%)** |
| **OCR Alpha** | Raw Tesseract PSM 3 (priced @ 2.0s compute @ $0.25/s) | $\$0.500000$ (compute) | $\$0.20$ | **$\$0.70$** | **Compute Time (71.4%)** |
| **OCR Beta** | Binarized Tesseract PSM 6 (priced @ 2.5s compute @ $0.18/s) | $\$0.450000$ (compute) | $\$0.20$ | **$\$0.65$** | **Compute Time (69.2%)** |

---

## 5. Code Sandbox: Protections and Limits

### Protections
- **Process Isolation**: The candidate code and test suite are written to an isolated temporary file and executed in a dedicated child process via `subprocess.run([sys.executable, ...], capture_output=True)`.
- **Hard Execution Timeout**: Enforces a strict `timeout_sec = 3.0s`. Infinite loops, network stalls, or CPU exhaustion attacks are terminated immediately with a non-zero exit code.
- **Ephemeral Lifecycle**: Scratch files are generated via `tempfile.NamedTemporaryFile` and deleted immediately in a guaranteed `finally:` block, preventing file leakage.
- **Zero Information Leakage**: The unit test assertions, edge-case checks, and hidden test inputs are never provided in the public JRP. Workers cannot hardcode test values or overfit.
- **Captive I/O**: `stdout` and `stderr` are captured in memory buffers to prevent terminal flooding or log injection attacks.

### Limits
- **Local Confinement**: Python child process isolation without kernel-level containerization (e.g. Docker/gVisor).
- **Standard Library Only**: Candidate code is expected to be algorithmic and self-contained; external network calls during unit test evaluation are not permitted.

---

## 6. Worker Registry & PayPal Sandbox Accounts

Each worker operates under a distinct, isolated PayPal sandbox account. **No two workers share an account.**

| Worker ID | Name | Role | PayPal Sandbox Account |
| :--- | :--- | :--- | :--- |
| **Orchestrator** | ProcureAgent Treasury | Buyer / Payer | `sb-s8vke53470365@business.example.com` |
| **ocr-worker-01** | OCR Specialist Alpha | Primary OCR (Raw PSM 3) | `sb-sqcdl53128062@personal.example.com` |
| **ocr-worker-02** | OCR Specialist Beta | Second OCR (Binarized PSM 6) | `sb-shusq53615721@personal.example.com` |
| **code-worker-01** | Python Code Specialist | Code Generation | `sb-bef9t53614820@personal.example.com` |
| **llm-worker-01** | LLM Synthesis Specialist | LLM Answers & Citation Verification | `sb-kgyi653615592@personal.example.com` |
| **rogue-worker-01** | Rogue Worker (Adversary) | Defective Submissions | `sb-a43fio53613334@personal.example.com` *(Asserted $0.00 Paid)* |

---

## 7. Verified Live Adversarial Flow (`PAYOUT_MODE=live`)

In the live end-to-end integration test (`scripts/test_live_adversarial_reallocation.py` and `scripts/test_ocr_gate.py`):
1. **Rogue Underbids**: Bids $\$0.30 - \$0.35$ (undercutting honest market rate) and is awarded the task.
2. **Budget Reserved**: Exact bid amount reserved for Rogue.
3. **Defect Caught**: Rogue submits flawed delivery (e.g. OCR Character Error Rate exceeds 5.0% threshold or code fails hidden unit tests).
4. **Payment Withheld & Reservation Released**: Rogue's reservation is released back to the treasury pool. Rogue receives **$\$0.00$**.
5. **Dynamic Reallocation**: Task is dynamically reassigned to the winning honest worker.
6. **Delivery & Verification**: Honest worker delivers verified output via real OCR / live Groq LLM inference; passes two-layer verification.
7. **Real PayPal Settlement**: Real PayPal Payout submitted in `PAYOUT_MODE=live`.
   - **Rogue Paid**: `$\$0.00$` (Asserted in ledger and PayPal API)
   - **Honest Worker Paid**: Verified bid amount settled with live PayPal Batch ID and status `PAYOUT_SUCCESS`.

---

## 8. Future Use Cases (NOT Implemented)

The following architectural capabilities are explicitly out of scope for the current hackathon milestone and are **NOT implemented**:
- **Batch compute across distributed nodes**: ProcureAgent currently runs single tasks sequentially against registered local and API-driven worker agents; distributed parallel map-reduce scheduling across external worker clusters is not implemented.
- **Human-in-the-loop data labeling**: All acceptance criteria are strictly programmatic, deterministic, or LLM-evaluated. No manual annotation queues, worker labeling portals, or human review interfaces are implemented.
- **Location-restricted / Geo-fenced data collection**: Worker nodes operate without residential proxy pools, IP rotation networks, or geographical egress constraints.

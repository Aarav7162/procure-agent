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
| **Worker Agent** | `openai/gpt-oss-120b` | Groq Platform | High-capacity reasoning and structured generation engine used by `llm-worker-01` to execute complex tasks, extract data, and synthesize specifications. |
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

## 3. Code Sandbox: Protections and Limits

When evaluating code generation deliveries (Task Family 2), ProcureAgent executes candidate code against a hidden unit test suite.

### Protections
- **Process Isolation**: The code and test suite are written to an isolated temporary file and executed in a dedicated operating system child process via `subprocess.run([sys.executable, ...], capture_output=True)`.
- **Hard Execution Timeout**: Enforces a strict `timeout_sec = 3.0s`. Infinite loops, network stalls, or CPU exhaustion attacks are terminated immediately with a non-zero exit code.
- **Ephemeral Lifecycle**: Scratch files are generated via `tempfile.NamedTemporaryFile` and deleted immediately in a guaranteed `finally:` block, preventing file leakage.
- **Zero Information Leakage**: The unit test assertions, edge-case checks, and hidden test inputs are never provided in the public JRP (Job Request Package). Workers cannot hardcode test values or overfit.
- **Captive I/O**: `stdout` and `stderr` are captured in memory buffers (capped at 500 characters in logs) to prevent terminal flooding or log injection attacks.

### Limits & Boundary Conditions
- **Local Runtime Confinement**: The sandbox relies on Python process separation without OS-level kernel isolation (e.g., Docker, firejail, or gVisor). Code currently executes with the permissions of the host process.
- **Standard Library Only**: Candidate code is expected to be algorithmic and self-contained; external network calls during unit test evaluation are not permitted.
- **Single-Thread Target**: Multi-threaded or asynchronous worker scripts that spawn persistent background daemons can exceed the execution timeout.

---

## 4. Worker Registry & PayPal Sandbox Accounts

Each worker operates under a distinct, isolated PayPal sandbox account. The adversarial rogue worker has an independent account, and tests assert that $0.00 is ever sent to it.

| Worker ID | Name | Role | PayPal Sandbox Account |
| :--- | :--- | :--- | :--- |
| **Orchestrator** | ProcureAgent Treasury | Buyer / Payer | `sb-s8vke53470365@business.example.com` |
| **ocr-worker-01** | OCR Specialist Alpha | Primary OCR | `sb-sqcdl53128062@personal.example.com` |
| **ocr-worker-02** | OCR Specialist Beta | Second OCR Worker | `sb-shusq53615721@personal.example.com` |
| **code-worker-01** | Python Code Specialist | Code Generation | `sb-sqcdl53128062@personal.example.com` |
| **llm-worker-01** | LLM Synthesis Specialist | Extraction & Synthesis | `sb-kgyi653615592@personal.example.com` |
| **rogue-worker-01** | Rogue Worker (Adversary) | Defective Submissions | `sb-a43fio53613334@personal.example.com` *(Asserted Never Paid)* |

---

## 5. Real vs. Simulated Accounting

- **REAL**:
  - Live PayPal Sandbox Payout API calls (`/v1/payments/payouts`) returning real PayPal batch IDs with asynchronous status polling (`PROCESSING` $\to$ `SUCCESS`).
  - Real Groq LLM token processing for both Worker (`openai/gpt-oss-120b`) and Judge (`qwen/qwen3.8-27b`).
  - Character Error Rate Levenshtein calculation against human ground truth.
  - Subprocess execution with hidden assertions.
  - Live HTTP citation resolution and content scraping.
  - SQLite `BEGIN IMMEDIATE` atomic financial ledger.
- **SIMULATED**:
  - Offline fallback payout mode if PayPal API is unreachable in test mode (visibly marked `SIMULATED` in batch ID and ledger notes).
  - Synthetic scans if real scans are not provided.

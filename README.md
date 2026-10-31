# ProcureAgent: Autonomous AI Capability Procurement & Settlement Engine

**PayPal AI Agent Hackathon Project**  
*Agent-pays-agent capability procurement with tamper-evident payload verification, deterministic verification, and real PayPal Sandbox settlement.*

---

## 1. Core Architecture & Philosophy

ProcureAgent empowers autonomous AI agents to dynamically discover, procure, and settle specialized machine labor from competitive third-party worker agents. Unlike conventional agent frameworks that trust agent output implicitly, ProcureAgent operates under a **Zero-Trust Verification Architecture**:

- **Real Money, Verified Delivery**: Funds are managed via pre-flight internal budget reservations ($S + R \le B$) and released through **PayPal Payouts API** *only* after two-layer payload integrity and deterministic verification.
- **Strict Realism Directive**: Everything that can be real is real (real PayPal API sandbox payouts, real Groq LLM inference, real Levenshtein OCR Character Error Rate evaluation, real sandboxed Python test execution, real live HTTP citation probing). Anything that cannot be real is visibly labeled `SIMULATED` across logs, UI, and ledger.
- **Tamper-Evident Ledger**: Every state transition is written to an append-only SQLite ledger serialized with `BEGIN IMMEDIATE` and anchored to an external tamper-evident SHA-256 hash chain (`audit/latest_chain_hash.txt`).

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
- **Scans Directory & Ground Truth**: `data/real_scans/` contains **generated test documents with exact ground truth** (`doc_01.png` + `doc_01.txt` through `doc_05.png` + `doc_05.txt`). These are generated receipt-style, bill-style, invoice-style, and printed paragraph images with realistic noise, fonts, and skew to evaluate real Tesseract OCR.
- **CER Normalization Rule**: Standard OCR text normalization strips decorative separator lines (`^[-=_*~]{3,}$`) and collapses whitespace before Levenshtein edit distance calculation. Repeated dash/equal lines in receipts and bills are treated by OCR engines as graphical horizontal dividing rules rather than semantic text characters. With this rule, honest workers achieve $\le 1.31\%$ CER across all 5 documents (well within the $\le 5.0\%$ tolerance).
- **Measured Accuracy & Cost Finding**: Alpha and Beta perform essentially identically on accuracy ($0.44\%$ vs $0.51\%$ average CER across all 5 test documents; no significant quality tradeoff exists between them). Beta offers a lower upfront compute rate ($\$0.65$ vs $\$0.70$).
- **Live Settlement Demo Selection**: The settlement demo specifically uses `doc_04.png`—a document where both honest workers achieve $0.00\%$ CER—ensuring that honest workers pass acceptance criteria on legitimate OCR execution, while the rogue underbidder is rejected strictly due to deliberate defect injection.

### Task Family 2: Python Code Generation (`code-worker-01` vs `code-worker-02`)
Two genuinely differentiated code generation workers running on different model tiers:
- **`code-worker-01` (High-Capacity 120B)**: Uses live Groq API inference (`openai/gpt-oss-120b`). Fixed operating fee set per worker $F_{\text{min}} = \$0.30$.
- **`code-worker-02` (Fast Lightweight 20B)**: Uses live Groq API inference (`openai/gpt-oss-20b`). Fixed operating fee set per worker $F_{\text{min}} = \$0.22$.

#### Empirical Benchmark by Execution Source ($N = 30$ Live Runs, Excludes Backfill)
ProcureAgent measures code worker performance across verified empirical runs maintained in `audit/run_log.jsonl`. Scores are computed **exclusively from the fresh $N=30$ live concurrent benchmark**, while earlier runs remain strictly marked `"backfilled"` in the log:

**Run Counts by Source (Full Audit Trail)**:
- **`code-worker-01` (`openai/gpt-oss-120b`) Total = 53 Logged Rows**:
  - `scripts/benchmark_10_runs_code_workers.py` [backfilled]: 10 runs (10 passed, 0 failed, avg latency 4.71s).
  - `scripts/test_reassignment_scenario.py` [backfilled]: 3 runs (3 passed, 0 failed, avg latency 3.82s).
  - `scripts/benchmark_interleaved_code_workers.py` [backfilled]: 10 runs (10 passed, 0 failed, avg latency 4.92s).
  - `scripts/run_live_30_benchmark.py` [live]: 30 runs (30 passed, 0 failed, avg latency 5.62s).
  - **Live Sample Size ($N_{\text{live}}$)**: **30 runs** (exclusively used for scoring).
  - **Live Pass Rate**: **30 / 30 (100.0%)**.
  - **Bayesian Posterior**: $\text{Beta}(2+30, 1+0) = \text{Beta}(32, 1) \implies \mu = \frac{32}{33} \approx \mathbf{0.9697}$.
  - **Fixed Operating Fee**: $F_{\text{min}} = \$0.30$.
  - **Computed Bid**: $\mathbf{\$0.30}$.
  - **Grand Average Latency (All 30 Live Runs)**: $5.6185\text{s}$.
  - **Rolling Average Latency (Last 10 Runs)**: $5.6696\text{s}$.
- **`code-worker-02` (`openai/gpt-oss-20b`) Total = 55 Logged Rows**:
  - `scripts/benchmark_10_runs_code_workers.py` [backfilled]: 10 runs (3 passed, 7 failed, avg latency 9.02s).
  - `scripts/test_reassignment_scenario.py` [backfilled]: 5 runs (2 passed, 3 failed, avg latency 3.02s).
  - `scripts/benchmark_interleaved_code_workers.py` [backfilled]: 10 runs (2 passed, 8 failed, avg latency 4.08s).
  - `scripts/run_live_30_benchmark.py` [live]: 30 runs (7 passed, 23 failed, avg latency 4.87s).
  - **Live Sample Size ($N_{\text{live}}$)**: **30 runs** (exclusively used for scoring).
  - **Live Pass Rate**: **7 / 30 (23.3%)** (The 20B consistently fails hidden leap-year and month-end boundary clamping tests).
  - **Bayesian Posterior**: $\text{Beta}(2+7, 1+23) = \text{Beta}(9, 24) \implies \mu = \frac{9}{33} \approx \mathbf{0.2727}$.
  - **Fixed Operating Fee**: $F_{\text{min}} = \$0.22$.
  - **Computed Bid**: $\mathbf{\$0.22}$.
  - **Grand Average Latency (All 30 Live Runs)**: $4.8745\text{s}$.
  - **Rolling Average Latency (Last 10 Runs)**: $4.6963\text{s}$.

| Metric | `code-worker-01` (`openai/gpt-oss-120b`) | `code-worker-02` (`openai/gpt-oss-20b`) | Empirical Tradeoff |
| :--- | :--- | :--- | :--- |
| **Pass Rate (5/5 Hidden Tests)** | **30 / 30 (100.0%)** | **7 / 30 (23.3%)** | 120B has **4.3x higher reliability**. The 20B model reliably fails century leap-year clamping (`year % 100 == 0`). |
| **Speed Basis (Recent 10 Rolling)** | **5.6696s** | **4.6963s** | In recent rolling calls, 20B is 0.97s faster, but fails 76.7% of test suites. |
| **Speed Basis (All 30 Live Runs)** | **5.6185s** | **4.8745s** | Across all 30 live concurrent runs, 20B averages 4.87s vs 120B's 5.62s. |
| **Bayesian Reputation ($\alpha / (\alpha+\beta)$)** | **0.9697** ($\text{Beta}(32, 1)$) | **0.2727** ($\text{Beta}(9, 24)$) | 120B earned near-perfect reputation; 20B is heavily penalized for frequent test failure. |
| **Computed Bid ($C_{\text{api}} \times 1.25 + F_{\text{min}}$)** | **$0.30 USD** | **$0.22 USD** | 20B provides an 8¢ cheaper bid based on lower compute tier and operational fee ($0.22 vs $0.30). |

#### Unified Continuous Urgency Scorer & Weight Invariant Scheme
All bid evaluations use the unified continuous $\lambda_t$ urgency model (`broker/deadline_scorer.py` and `broker/bid_scorer.py`), bounding weights to strictly sum to $1.0000$ across all deadlines $t \in [T_{\min}, T_{\max}]$:
- **Urgency Parameter**: $\lambda_t = \text{clamp}\left(\frac{T_{\max} - t}{T_{\max} - T_{\min}}, 0.0, 1.0\right)$ where $T_{\min} = 6.0\text{s}$ (tight) and $T_{\max} = 30.0\text{s}$ (relaxed).
- **Normalized Weights Invariant**:
  $$W_{\text{rep}} = 0.20, \quad W_{\text{speed}} = 0.80 \times \lambda_t, \quad W_{\text{price}} = 0.80 \times (1.0 - \lambda_t)$$
  $$\text{Invariant: } W_{\text{speed}} + W_{\text{price}} + W_{\text{rep}} \equiv 1.0000 \quad (\forall \lambda_t \in [0.0, 1.0])$$
- **Score Formulations**:
  - Price Score: $S_{\text{price}} = \max\left(0.0, 1.0 - \frac{\text{Bid}_{\text{USD}}}{\text{MaxBudget}_{\text{USD}}}\right)$ (at $\text{MaxBudget} = \$0.50$: 120B = $0.4000$, 20B = $0.5600$).
  - Speed Score (Clamped at 0): $S_{\text{speed}} = \max\left(0.0, 1.0 - \frac{\text{Latency}}{\text{Deadline}}\right)$. Clamping guarantees workers that breach deadlines receive $0.0000$ speed utility rather than negative scores.
  - Bayesian Reputation: $S_{\text{rep}} = \frac{\alpha}{\alpha + \beta}$ computed from the recorded live benchmark ($N_{\text{live}} = 30$).

##### Price Score Formula Comparison & Why the Loose-Deadline Winner Flipped
The earlier loose-deadline win for the 20B came from using a min-max price normalization formula rather than just changes in the underlying data:
- **Formula A (Min-Max Normalization)**:
  $$S_{\text{price, min-max}} = \frac{P_{\max} - \text{bid}}{P_{\max} - P_{\min}}$$
  In a two-bid auction where `code-worker-01` (120B) bids $\$0.30$ and `code-worker-02` (20B) bids $\$0.22$, min-max normalization assigns 20B a price score of $\frac{0.30 - 0.22}{0.30 - 0.22} = \mathbf{1.0000}$ and 120B a price score of $\frac{0.30 - 0.30}{0.30 - 0.22} = \mathbf{0.0000}$. This creates a full $1.0000$ score spread over an $8¢$ price difference, causing the 20B to win whenever price weight exceeded just $41.1\%$.
- **Formula B (Budget-Relative Ceiling Normalization — Production Formula)**:
  $$S_{\text{price, budget}} = \max\left(0.0, 1.0 - \frac{\text{Bid}_{\text{USD}}}{\text{MaxBudget}_{\text{USD}}}\right)$$
  At $\text{MaxBudget} = \$0.50$, 120B scores $1.0 - 0.30/0.50 = \mathbf{0.4000}$ and 20B scores $1.0 - 0.22/0.50 = \mathbf{0.5600}$. The score gap is proportionally bounded to $0.1600$.

**Why Formula B is Used & Design Tradeoffs**: Formula B is a documented design choice with deliberate tradeoffs: budget-relative price scoring shrinks price differences as the buyer's max budget grows (for example, an $8¢$ price difference yields a noticeable $0.1600$ score spread when the budget cap is $\$0.50$, but shrinks to a negligible $0.0053$ spread when the budget cap is $\$15.00$, making large-budget procurements almost purely reliability- and deadline-driven, while small-budget tasks remain cost-sensitive). Min-max normalization was rejected because it is pathological in small agent procurement auctions—if two workers bid $\$0.299$ and $\$0.300$, min-max swings scores from $1.0$ to $0.0$, penalizing a fractional-cent difference as an absolute failure. Budget-relative normalization scales savings proportionally against the buyer's authorized capital ceiling.

Under Formula B, with empirical Bayesian reputations ($R_{\text{120B}} = 0.9697$, $R_{\text{20B}} = 0.2727$ from $N=30$ live runs), the reputation gap ($0.9697 - 0.2727 = 0.6970$) at $W_{\text{rep}} = 0.20$ costs $0.1394$. Because 20B's maximum price advantage is $0.80 \times 0.1600 = 0.1280$, **reputation outweighs price unless price weight exceeds about 81%**. Both outcomes are near ties:

- **Tight Deadline ($6.0\text{s}$, $\lambda_t = 1.0 \implies W_{\text{speed}}=0.80, W_{\text{price}}=0.00, W_{\text{rep}}=0.20$)**:
  - `code-worker-01` (120B, $N=30$, Latency $5.67\text{s}$): $S_p = 0.4000, S_s = 0.0551, S_r = 0.9697 \implies \text{Composite} = \mathbf{0.2379}$.
  - `code-worker-02` (20B, $N=30$, Latency $4.70\text{s}$): $S_p = 0.5600, S_s = 0.2173, S_r = 0.2727 \implies \text{Composite} = \mathbf{0.2279}$.
  - **Outcome**: Near tie ($0.2379$ vs $0.2279$, margin **+0.0100**).
  - *Latency Sensitivity*: Under All-30 Runs Average Latency ($5.62\text{s}$ vs $4.87\text{s}$), 120B scores $0.2447$ vs 20B's $0.2045$ ($+0.0402$).
- **Loose Deadline ($30.0\text{s}$, $\lambda_t = 0.0 \implies W_{\text{speed}}=0.00, W_{\text{price}}=0.80, W_{\text{rep}}=0.20$)**:
  - `code-worker-01` (120B, $N=30$): $S_p = 0.4000, S_s = 0.0000, S_r = 0.9697 \implies \text{Composite} = \mathbf{0.5139}$.
  - `code-worker-02` (20B, $N=30$): $S_p = 0.5600, S_s = 0.0000, S_r = 0.2727 \implies \text{Composite} = \mathbf{0.5025}$.
  - **Outcome**: Near tie ($0.5139$ vs $0.5025$, margin **+0.0114**).

##### Sensitivity Table Across Both Price-Score Formulas
The table below compares candidate outcomes under Formula B (Budget-Relative) versus Formula A (Min-Max) across price weights $W_p \in [0.10, 0.90]$ with $W_s = 0.00$ and $W_r = 1.0 - W_p$:

| Price Weight ($W_p$) | Rep Weight ($W_r$) | Formula B (Budget-Rel) 120B / 20B | Formula B Winner | Formula A (Min-Max) 120B / 20B | Formula A Winner |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **0.10** | 0.90 | 0.9127 / 0.3014 | 120B (+0.6113) | 0.8727 / 0.3454 | 120B (+0.5273) |
| **0.30** | 0.70 | 0.7988 / 0.3589 | 120B (+0.4399) | 0.6788 / 0.4909 | 120B (+0.1879) |
| **0.4107 (Min-Max Crossover)** | 0.5893 | 0.7352 / 0.3908 | 120B (+0.3444) | 0.5714 / 0.5714 | **EXACT TIE (0.0000)** |
| **0.50** | 0.50 | 0.6849 / 0.4164 | 120B (+0.2685) | 0.4849 / 0.6364 | **20B WINS (+0.1515)** |
| **0.70** | 0.30 | 0.5709 / 0.4738 | 120B (+0.0971) | 0.2909 / 0.7818 | **20B WINS (+0.4909)** |
| **0.80 (λ_t Scheme Max)** | **0.20** | **0.5139 / 0.5025** | **120B (+0.0114 near tie)** | 0.1939 / 0.8545 | **20B WINS (+0.6606)** |
| **0.8133 (Budget Crossover)** | **0.1867** | **0.5063 / 0.5063** | **EXACT TIE (0.0000)** | 0.1810 / 0.8643 | **20B WINS (+0.6833)** |
| **0.85** | 0.15 | 0.4855 / 0.5169 | **20B WINS (+0.0314)** | 0.1455 / 0.8909 | **20B WINS (+0.7454)** |
| **0.90** | 0.10 | 0.4570 / 0.5313 | **20B WINS (+0.0743)** | 0.0970 / 0.9273 | **20B WINS (+0.8303)** |

*Summary*: Under Formula A, 20B won as soon as price weight exceeded $41.1\%$. Under the production Formula B, **reputation outweighs price unless price weight exceeds about 81%** ($W_p > 81.33\%$). At standard continuous lambda weights ($\lambda_t = 0 \implies W_p = 0.80, W_r = 0.20$), the 120B model wins by a near-tie margin of $0.0114$.

- **Rogue Adversarial Underbidding**: The rogue fixture calculates its bid via `workers/rogue_worker.py:53`:
  $$\text{underbid\_price} = \text{round}(\max(0.15, \min(0.20, \text{max\_bid} \times 0.36)), 2)$$
  At $\text{max\_bid} = \$0.50$, $0.50 \times 0.36 = \$0.18$. With claim of $1.0\text{s}$ latency and unpenalized $\text{Beta}(2, 1) = 0.6667$ prior, rogue wins the initial auction ($\text{Composite} = 0.7645$), is caught by the hidden test sandbox, paid $\$0.00$, and dynamically reallocated to `code-worker-01`.

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

| Worker ID | Name | Role | Model / Engine | PayPal Sandbox Account |
| :--- | :--- | :--- | :--- | :--- |
| **Orchestrator** | ProcureAgent Treasury | Buyer / Payer | Policy & Treasury Engine | `sb-s8vke53470365@business.example.com` |
| **ocr-worker-01** | OCR Specialist Alpha | Primary OCR (Raw PSM 3) | Tesseract 5.5.0 | `sb-sqcdl53128062@personal.example.com` |
| **ocr-worker-02** | OCR Specialist Beta | Second OCR (Binarized PSM 6) | Tesseract 5.5.0 + OpenCV | `sb-shusq53615721@personal.example.com` |
| **code-worker-01** | Python Code Specialist | Code Generation & Debugging | `openai/gpt-oss-120b` | `sb-bef9t53614820@personal.example.com` |
| **code-worker-02** | Fast Code Worker | Lightweight Code Generation | `openai/gpt-oss-20b` | `sb-kgyi653615592@personal.example.com` |
| **llm-worker-01** | LLM Synthesis Specialist | Answers & Citation Verification | `openai/gpt-oss-120b` | `sb-kgyi653615592@personal.example.com` |
| **rogue-worker-01** | Rogue Worker (Adversary) | Scripted Defective Underbidder | Scripted Adversarial Fixture | `sb-a43fio53613334@personal.example.com` *(Asserted $0.00 Paid)* |

### Bayesian Reputation & Cold-Start Policy
To mitigate cold-start exploitation, worker reliability is tracked dynamically using Bayesian conjugate updating under a $\text{Beta}(2, 1)$ prior:
- **Prior Distribution**: $\alpha = 2.0, \beta = 1.0 \implies \mu = \frac{\alpha}{\alpha + \beta} = 0.667$ (66.7% baseline expectation).
- **Update Rule**: On verified delivery $\alpha \leftarrow \alpha + 1$; on rejected delivery $\beta \leftarrow \beta + 1$.
- **Cold-Start Threshold**: Any worker with **fewer than 3 completed tasks ($N < 3$)** is restricted to a **$1.00 max allocation cap** per task.
- **Unlocking Full Liquidity**: Once a worker successfully delivers and passes verification on $3$ tasks ($N \ge 3$), the allocation cap expands to the full authorized cycle cap ($15.00$).
- **Adversary Impact**: When `rogue-worker-01` delivers defective code or corrupted OCR, its score drops immediately from $0.667 \to 0.500$ ($\text{Beta}(2, 2)$), while honest workers rise to $0.750$ ($\text{Beta}(3, 1)$).

---

## 7. Verified Live Adversarial Flow (`PAYOUT_MODE=live`)

The end-to-end procurement and settlement flow is initiated via a **simulated CI trigger** (`scripts/post_bounty.py`), mimicking an automated webhook dispatched when continuous integration unit tests fail.

### Scripted Adversarial Fixtures Disclosure
All adversarial outputs—including the rogue worker's Python code submissions and OCR character distortions—are **scripted adversarial fixtures**. They are deliberately engineered to simulate realistic machine errors (such as missing leap-year calendar clamping or optical character scanning noise) to rigorously test the two-layer verification engine without human intervention. In all scenarios, the rogue worker is blocked and asserted to receive strictly **$0.00**.

### Robust Task Parser & Deterministic Keyword Fallback
ProcureAgent employs a multi-tier Job Request Packet (JRP) parsing pipeline in `orchestrator/jrp_builder.py`:
1. **Tier 1 (Live LLM Semantic Parser)**: Uses `openai/gpt-oss-120b` to dynamically extract technical capability requirements and build programmatic acceptance rules from free-form natural language.
2. **Tier 2 (Deterministic Keyword Fallback)**: If live cloud LLM completion encounters a network timeout, rate limit, or invalid JSON payload, `build_jrp()` automatically falls back to `keyword_fallback_jrp()`. This fallback deterministically maps domain keywords (`python`, `code`, `billing`, `ocr`, `scan`, `receipt`) to standardized capability manifests, ensuring 100% orchestrator resilience even under cloud degradation.

### Dashboard Presets & Authentic Host Sensor Demonstration
In the Polaris-themed dashboard (`dashboard/index.html`):
- **Forced Procurement Presets**: Quick presets marked as `(Forced Procurement)` set `force_procure=true` in the task payload. This allows judges and operators to immediately demonstrate external marketplace bidding, verification, and PayPal settlements without manually saturating the local host.
- **Authentic Host Bottleneck Sensor Demo**: The `Host Bottleneck Sensor` preset dispatches tasks with `force_procure=false`. When deployed, the orchestrator authentically queries the host system's live CPU, memory, and 1-slot execution queue (`orchestrator/bottleneck_sensor.py`). If the host is idle, the task executes locally with zero spend. Clicking `Occupy Host Slot` saturates the local execution slot, causing the authentic sensor to detect a bottleneck and dynamically route the task to external marketplace procurement.

In the live end-to-end integration test (`scripts/test_live_adversarial_reallocation.py`, `scripts/test_ocr_gate.py`, and `scripts/test_gate3_code_bounty_live.py`):
1. **Rogue Underbids**: Bids below honest market rate and is awarded the initial contract.
2. **Budget Reserved**: Exact bid amount reserved in internal budget reservation.
3. **Defect Caught**: Rogue submits flawed delivery (OCR CER exceeds 5.0% threshold or code fails hidden unit tests).
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

---

## 9. Polaris UI Provenance & Submission Period Architecture Disclosures

The frontend command centre dashboard (`dashboard/index.html`) adapts the visual aesthetic, design tokens, and layout architecture from an earlier personal project (`emsearch-polaris/frontend` at `C:\Users\aarav.SOMEGUYWITHPRET\Documents\emsearch-polaris\frontend`):
- **Reused Design Assets & Styles**:
  - `src/design-system/tokens.css` (color tokens `--theme-bg: #09090b`, `--theme-surface: #121214`, `--theme-border: rgba(255,255,255,0.08)`, and typography)
  - `src/index.css` (liquid glass backdrop blur surfaces, borders, elevated control backgrounds)
  - `src/components/ui/Beams.tsx` (procedural light column shader geometry and simplex noise concept)
- **Repo Initialization & Development Scope**:
  - The repository was initialized on **October 29th, 2026 at 15:40:22 +0530** (commit `0537dde`) after earlier local prototype code existed. (The `11:21` timestamp noted in earlier scratch notes was an execution log time, not the git author date).
  - **Built During the Submission Period**: Everything else in this codebase was conceived and built during the hackathon submission period (October 29–31, 2026), including:
    - The asynchronous Job Request Packet (JRP) capability manifest broker (`broker/`)
    - The atomic budget reservation manager with SQLite `BEGIN IMMEDIATE` transactions (`orchestrator/budget_manager.py`)
    - The two-stage verification engine with subprocess sandbox execution (`orchestrator/verifier.py`)
    - Dynamic Bayesian $\text{Beta}(2,1)$ reputation scoring with cold-start caps (`orchestrator/reputation.py`)
    - All 6 worker microservice clients (Groq Cloud 120B/20B LLMs, Tesseract 5.5 OCR, and adversary)
    - Live PayPal Sandbox Payouts REST API v1 integration with batch polling (`orchestrator/treasury.py`)
    - Append-only tamper-evident SHA-256 audit hash-chaining (`audit/run_log.py`)

---

## 10. Judge Quickstart & Deployment Guide

ProcureAgent is designed for zero-friction evaluation by hackathon judges.

> [!NOTE]
> **Platform Testing Scope**: Only **Windows** was tested for this submission (specifically Windows 11 with Python 3.12).
> **PayPal Payouts Regional Eligibility**: The PayPal Payouts REST API requires a Sandbox Business Account registered in a payout-supported country (e.g., US, UK, Canada, Australia). If you do not have a supported sandbox business account, you can evaluate the complete system seamlessly using **Replay Mode** (zero keys required) or by setting `PAYOUT_MODE=simulated` in `.env`.

### Quickstart: 3 Commands from Fresh Clone
```bash
# 1. Clone the repository
git clone https://github.com/Aarav7162/ProcureAgent.git
cd ProcureAgent

# 2. Install dependencies into your environment
pip install -r requirements.txt

# 3. Copy example environment and start
copy .env.example .env
python start.py
```
`python start.py` automatically boots all 7 microservices in parallel and opens `http://127.0.0.1:8000/` in your default browser.

### Replay Mode (Zero API Keys Required)
Judges do NOT need API keys to evaluate the system:
1. In the top bar, switch the toggle from **Live Mode** to **Replay Mode**.
2. Click **Play (▶)** or step through events using **Next (▶)**.
3. Observe the authentic 15-event recorded run (`bounty_1793358223`):
   - Rogue worker underbids at **$0.18** (`workers/rogue_worker.py:53`).
   - Treasury pre-flight internal budget reservation locks **$0.18**.
   - Sandboxed hidden unit tests catch the leap-year defect.
   - Payout is blocked (**$0.00 paid**), reservation is released.
   - Dynamic reallocation to `code-worker-01` (120B) passes all 5 hidden tests.
   - Real PayPal Sandbox batch `YMRTQZU3GUNMA` is settled to `PAYOUT_SUCCESS`.
   - Append-only ledger commits with tamper-evident SHA-256 hash chaining.

### Live Mode Setup (Real Inference & Real PayPal Settlement)
To execute live runs with live Groq inference and real PayPal Sandbox payouts:

#### 1. Free Groq API Key Setup
1. Sign up for a free account at [console.groq.com](https://console.groq.com).
2. Create an API Key in the dashboard.
3. In `.env`, set:
   ```env
   GROQ_API_KEY=gsk_your_groq_api_key_here
   ```

#### 2. Free PayPal Developer Sandbox App Setup
1. Log in to the [PayPal Developer Dashboard](https://developer.paypal.com/dashboard/applications/sandbox).
2. Under **REST API apps**, click **Create App**:
   - App Type: **Merchant / Platform**
   - Sandbox Business Account: Select your default generated business account (ensure the country is US or payout-supported).
3. In your newly created app, copy your credentials into `.env`:
   ```env
   PAYPAL_CLIENT_ID=your_sandbox_client_id
   PAYPAL_CLIENT_SECRET=your_sandbox_client_secret
   PAYPAL_BUYER_EMAIL=your_business_sandbox_email@business.example.com
   PAYOUT_MODE=live
   ```
4. Under **Testing Tools** $\to$ **Sandbox Accounts**, note the personal accounts used for worker recipients (or keep the default preconfigured `sb-bef9t53614820@personal.example.com`).
5. *(Optional)* If testing without live PayPal Payout credentials, set `PAYOUT_MODE=simulated` to test full end-to-end orchestration with simulated settlement.

#### 3. Tesseract OCR Engine Setup (Cross-Platform Automatic Detection)
ProcureAgent dynamically resolves Tesseract on system paths with zero hardcoded user paths:
- **Windows**: Install via `winget install UB-Mannheim.TesseractOCR` or the official installer. Automatically detected at `%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe` or `C:\Program Files\Tesseract-OCR\tesseract.exe`.
- **macOS**: `brew install tesseract`. Automatically detected on PATH (`/opt/homebrew/bin/tesseract` or `/usr/local/bin/tesseract`).
- **Linux (Ubuntu/Debian)**: `sudo apt-get install -y tesseract-ocr`. Automatically detected on PATH (`/usr/bin/tesseract`).
- *(Optional)*: Set `TESSERACT_PATH=/custom/path/to/tesseract` in `.env` if installed in a non-standard location.
- **Graceful Degradation**: If Tesseract is not installed on the host, OCR workers cleanly decline OCR bids without throwing unhandled exceptions, and all code generation workflows continue operating without interruption.


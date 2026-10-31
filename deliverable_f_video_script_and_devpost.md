# ProcureAgent // Submission Artifacts: Video Script & Devpost Draft

This document contains the official demonstration video script (timed to ~2 minutes 30 seconds at exactly 324 words), followed by the complete Devpost project submission.

---

## Part 1: 2:30 Video Script (Timed to ~150 Seconds, Exactly 324 Words)

### **[0:00 - 0:30] The Problem & Three User Personas (30s // 68 words)**
- **Visual**: Screen opens on the Polaris Command Centre (`http://127.0.0.1:8000/`) in obsidian dark mode with procedural beams. Dynamic Island shows `COMMAND CENTRE // OPERATIONS NOMINAL`. Treasury card displays: **$0.00 Spent, $0.00 Reserved, $25.00 Cap**.
- **Voiceover**: 
  > *"When engineering teams give AI agents spending authority—whether developers running batch jobs via our interactive CLI, autonomous agents calling our REST endpoint, or team leads monitoring spend on the dashboard—unmonitored funds invite disaster. Without zero-trust verification, rogue workers underbid honest peers, deliver plausible hallucinations, and drain corporate capital. ProcureAgent provides autonomous capability procurement with pre-flight budget reservations, sandboxed acceptance checks, and automated PayPal sandbox settlement."*

---

### **[0:30 - 0:55] Architecture & Worker Capability Network (25s // 52 words)**
- **Visual**: Focus shifts across the 9-stage pipeline strip and the horizontal Worker Capability Registry displaying five honest workers and one scripted adversary. Highlights budget reservation counter and verification gates.
- **Voiceover**: 
  > *"Our network coordinates five honest workers across coding, OCR, and GPU batch jobs, plus one scripted adversary. All code is tested against hidden unit tests in isolated sandboxes, while subjective evaluations lacking programmatic verifiers are flagged as lower confidence. Before work starts, the orchestrator reserves funds: spent plus reserved never exceeds the cap."*

---

### **[0:55 - 1:35] Live Demo 1: The Rogue Underbidder & Zero-Trust Block (40s // 75 words)**
- **Visual**: Screen displays `/attack` in terminal / dashboard preset chip **`Rogue Attack (Forced)`**, populating the prompt: *"Fix billing rollover defect in demo_repos/billing_engine"*.
  - Dynamic Island transitions to `AUCTION // 3 BIDS SUBMITTED`.
  - Bids table populates: `code-worker-01` (120B) bids **$0.30**, `code-worker-02` (20B) bids **$0.22**, and `rogue-worker-01` underbids at **$0.18**.
  - Provisional allocation flashes on `rogue-worker-01`. Treasury locks **$0.18** in internal budget reservation (`Reserved: $0.18, Spent: $0.00`).
  - Rogue delivers a defective Python function injecting an intentional leap-year century defect.
  - Subprocess sandbox executes 5 hidden unit tests: **FAILED (1900 non-leap century rollover)**.
  - Acceptance check triggers. Dynamic Island turns crimson: **`PAYMENT BLOCKED // RESERVATION RELEASED`**.
  - Budget returns to **$0.00 Spent, $0.00 Reserved**. Rogue worker is paid strictly **$0.00 sandbox USD**.
  - Rogue Bayesian reputation slashes from $0.6667 \to 0.5000$.
- **Voiceover**: 
  > *"We submit a free-form coding task matched to our demo billing repo. An adversarial worker underbids the market at eighteen cents to seize allocation. ProcureAgent reserves eighteen cents in internal bookkeeping. The rogue delivers code containing a leap-year defect. The sandboxed runner executes five hidden unit tests—they fail. The acceptance check blocks the payout. The rogue receives zero sandbox dollars, its reservation is released, and its Bayesian reputation is slashed."*

---

### **[1:35 - 2:05] Live Demo 2: Autonomous Reallocation & PayPal Sandbox Payout (30s // 68 words)**
- **Visual**: 
  - Pipeline automatically transitions to `REALLOCATING`.
  - Contract reassigns to the highest-reputation honest bidder, `code-worker-01` (`openai/gpt-oss-120b`), at **$0.30**.
  - Treasury reserves **$0.30**.
  - Live Groq API inference triggers; 120B worker synthesizes clean calendar clamping logic.
  - Sandbox runs the 5 hidden unit tests: all five PASS.
  - Two-Stage Verification: **APPROVED**.
  - PayPal Settlement Card spins up: `DISPATCHING PAYPAL PAYOUT`.
  - PayPal Sandbox Payout Batch ID appears: `NUFGNUMSUTJ7W` with status **`SUCCESS`** (recorded from a live run).
  - Audit Ledger tab updates, appending transaction block signed with SHA-256 hash chaining.
- **Voiceover**: 
  > *"ProcureAgent autonomously reassigns the task to our honest 120B worker. The model generates a clean calendar clamping fix. The sandbox runs the hidden tests again: all five pass. The orchestrator calls the PayPal Payouts API in the sandbox, transfers thirty cents to the worker's account, and records the real PayPal batch ID shown on screen from this recording into an append-only, SHA-256 hash-chained ledger."*

---

### **[2:05 - 2:30] Empirical Benchmark & Hackathon Disclosures (25s // 61 words)**
- **Visual**: 
  - Switch to the Horizontal Capability Registry. Show the empirical live benchmark metrics ($N=30$ live runs per model): `gpt-oss-120b` (100.0% pass rate, 5.67s latency, 0.9697 reputation) vs `gpt-oss-20b` (23.3% pass rate, 4.70s latency, 0.2727 reputation).
  - Quick glance at the Replay Mode toggle (`Zero API Keys Required`).
  - Final wide shot of the Polaris Command Centre.
- **Voiceover**: 
  > *"In benchmark testing over thirty concurrent runs, the 120B model achieved 100% reliability, while the 20B achieved only 23%, dropping its reputation to 0.27. What you saw was live execution against our microservice cluster; judges without credentials can explore a recorded run in replay mode. Built during the submission period with first commit October 29, 2026. Thank you."*

---

## Part 2: Complete Devpost Submission Draft

### **Project Title**
**ProcureAgent: Autonomous AI Capability Procurement & Zero-Trust Verification Engine**

### **Elevator Pitch**
An autonomous multi-agent capability procurement network where developers, autonomous agents, and engineering teams discover, bid on, and settle specialized machine labor via automated PayPal Sandbox payouts—protected by tamper-evident payload verification, pre-flight budget reservations, and sandboxed deterministic acceptance testing.

---

### **The Target Audience: Three Real User Personas**
Rather than treating agent transactions as abstract simulations, ProcureAgent is engineered for three real user personas facing practical computing and financial constraints:

1. **The Developer Running Batch Jobs Directly (`procure-agent` CLI)**:
   - An engineer running compute-heavy workloads from the terminal—such as bug resolution across a codebase, high-volume document OCR extraction, or GPU batch processing jobs.
   - Using the interactive `procure-agent` terminal application, the developer types `/run Fix month-end rollover bug in billing.py --budget 1.00`, monitoring live bid auctions, sandbox verification steps, and automated PayPal settlement with zero manual escrow management.
2. **The AI Agent in an Automated Pipeline (`POST /procure` REST Endpoint)**:
   - An autonomous pipeline agent (e.g., CI/CD repair bot, ETL ingestion worker, or autonomous researcher) running into local CPU or memory bottlenecks.
   - Makes a single HTTP POST request to `http://localhost:8000/procure` specifying the task and budget ceiling. ProcureAgent handles worker discovery, budget reservation, sandbox verification, and PayPal settlement, returning verified artifacts or $0 spent on failure.
3. **The Team Lead Reviewing Spend & Governance (Polaris Dashboard)**:
   - An engineering manager overseeing agent compute spending across an organization.
   - Uses the Polaris Command Centre dashboard to monitor weekly spending caps ($25.00 limit), inspect Bayesian Beta reputation distributions across external workers, approve high-budget transactions (> $5.00), and verify the cryptographic integrity of the append-only SHA-256 transaction ledger.

---

### **The Problem: The Blind Trust Dilemma in Multi-Agent Delegation**
Current multi-agent systems operate under **implicit trust**:
1. **The Rogue Underbidder Attack**: A malicious, compromised, or cheap low-parameter worker can underbid honest competitors, deliver plausible-looking hallucinations or defective code, and immediately collect compensation.
2. **The LLM Judge Reliability Trap**: Relying strictly on an LLM to evaluate another LLM creates shared blindspots, non-deterministic scoring, and hallucinated compliance. In ProcureAgent, judge-only subjective evaluations are explicitly labeled as lower confidence.
3. **Premature Capital Flight**: Traditional payment setups lack programmatic budget reservations tied to deterministic test execution, risking financial loss when external agent labor fails.

---

### **Our Solution: ProcureAgent Zero-Trust Architecture**
ProcureAgent provides an economic and verification protocol that allows agents to safely hire peer agents within strict financial boundaries:

1. **Autonomous Spending Policy Engine (`config/bounty_policy.yaml` & `orchestrator/policy.py`)**:
   - **Weekly Budget Ceiling**: Hard-capped at `$25.00 USD` weekly expenditure.
   - **Permitted Task Types**: Restricts procurement strictly to authorized capability schemas (`code_bounty`, `document_ocr`, `llm_synthesis`). Unrecognized requests are rejected upfront before reaching the capability broker.
   - **Human Approval Threshold**: Any single job request exceeding `$5.00 USD` triggers a human policy hold (`NEEDS_APPROVAL`), requiring explicit supervisory sign-off before funds are reserved or contracts awarded.
2. **Internal Budget Reservation ($S + R \le B$)**:
   Before external work begins, the orchestrator reserves the exact bid amount in internal bookkeeping. Funds cannot be double-spent, and the sum of spent plus reserved funds is **enforced by the database** (`audit/ledger.db` using SQLite `BEGIN IMMEDIATE` transactions) never to exceed the cycle budget.
3. **Two-Stage Zero-Trust Verification**:
   - **Stage 1 (Tamper-Evident Integrity)**: Validates that the submitted artifact matches the claimed SHA-256 payload digest.
   - **Stage 2 (Deterministic Acceptance)**:
     - For **Python Code & Bug Remediation**: Subprocess execution in an isolated sandbox against **hidden edge-case unit tests** with a 3.0s timeout. Candidate workers never receive hidden test files.
     - For **Document OCR**: Multi-stage Levenshtein Character Error Rate (CER) calculation against ground truth with whitespace and separator normalization (enforcing $\le 5.0\%$ CER).
     - For **GPU Batch Processing & Embeddings**: Automated verification of dimensional tensor shape, data type, and cosine similarity thresholds against reference validation sets.
     - For **LLM Answers**: Programmatic quote verification ensuring all evidence strings appear verbatim in source documents, combined with live HTTP 200 citation probing. Subjective evaluations lacking programmatic verifiers are visibly labeled as lower confidence.
4. **Automated PayPal Sandbox Settlement**:
   Payments are dispatched via the **PayPal Payouts REST API v1** (`POST /v1/payments/payouts`) *only after* verification approval. If verification fails, the budget reservation is released, the worker receives strictly **$0.00 sandbox USD**, and the task is autonomously reallocated to the next highest-scoring bidder.
5. **Bayesian Beta(2,1) Reputation & Cold-Start Policy**:
   Worker credibility is tracked via Bayesian updating ($\text{Beta}(2, 1)$ prior $\to$ 66.7% baseline score). Unproven workers ($N < 3$ tasks) are subject to a **$1.00 cold-start allocation cap** to prevent high-value treasury drain.
6. **Tamper-Evident Hash-Chained Ledger**:
   Every state transition is committed to an SQLite WAL database and anchored to an external SHA-256 hash chain (`audit/latest_chain_hash.txt`).

---

### **Differentiated Worker Engines & Empirical Model Benchmarks**

ProcureAgent features 5 honest specialized worker agents plus 1 scripted adversary spanning 3 distinct task families:

1. **Python Code Specialists (`openai/gpt-oss-120b` vs `openai/gpt-oss-20b`)**:
   - Empirical benchmarks computed **exclusively from a live $N=30$ concurrent benchmark** without hand-tuning or backfill (maintained in `audit/run_log.jsonl`):
   - **120B Model**: 100.0% pass rate (30/30), 5.67s rolling average latency, Beta posterior reputation **0.9697**, $0.30 fixed operating fee.
   - **20B Model**: 23.3% pass rate (7/30), 4.70s rolling average latency, Beta posterior reputation **0.2727**, $0.22 fixed operating fee.
   - **Empirical Finding**: While the 20B model is 0.97s faster and offers an 8¢ cheaper bid ($0.22 vs $0.30), it repeatedly fails hidden calendar century rollover tests. Because its reputation drops to 0.2727, the 120B model's near-perfect credibility (0.9697) wins both tight and loose auctions.
2. **OCR Specialists (`ocr-worker-01` Alpha vs `ocr-worker-02` Beta)**:
   - Alpha uses raw Tesseract 5.5.0 PSM 3; Beta implements an image preprocessing pipeline (grayscale normalization, 2.0x contrast expansion, edge sharpening, and Otsu binarization before PSM 6).
   - Both achieve $\le 1.31\%$ CER across all 5 ground-truth test documents under our standard whitespace and separator normalization rule.
3. **LLM Synthesis Specialist (`llm-worker-01`)**:
   - Generates structured answers with live HTTP citation probing and programmatic quote grounding.
4. **Scripted Adversary (`rogue-worker-01`)**:
   - Fixed $0.18 underbid fixture delivering subtle leap-year century defects to prove zero-trust gating.

---

### **Explainable Capability Bidding Formula**
Except for the rogue worker's fixed $0.18 bid fixture (scripted to ensure an adversarial underbid in testing), honest worker bids are derived from a transparent economic formula:
$$\text{Bid}_{\text{USD}} = \min\left(\text{MaxBid}, \text{round}\left(C_{\text{api}} \times 1.25 + F_{\text{min}}, 2\right)\right)$$
Where $C_{\text{api}}$ is the raw token compute cost, $1.25$ is the risk multiplier, and $F_{\text{min}}$ is the worker's fixed operational fee ($0.15 for LLM, $0.22 for 20B, $0.30 for 120B). Because cloud inference costs are fractions of a cent, our analysis proves that the minimum operational fee dominates the final bid price.

---

### **What is Real vs. What is Simulated**
In accordance with our strict realism directive:
- **100% REAL LIVE STACK**:
  - PayPal Sandbox Payouts API integration (real batch IDs, synchronous polling, real sandbox payouts).
  - Groq LLM inference (`openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `qwen/qwen3.8-27b`).
  - Tesseract OCR execution and Levenshtein CER calculations.
  - Subprocess Python test execution in ephemeral sandboxes.
  - Live HTTP citation probing.
  - Append-only SQLite ledger with tamper-evident hash chaining.
- **VISIBLY LABELED SIMULATED FIXTURES**:
  - The rogue worker's fixed $0.18 bid, defective code patch, and OCR character distortions are scripted adversarial fixtures to ensure 100% reproducible test vectors without human intervention.
  - Simulated CI webhook triggers mimicking continuous integration pipeline failures.
  - Replay Mode: Deterministic playback of a 15-event verified code bounty run, allowing judges without API keys to evaluate the system with zero credentials.

---

### **Built During the Submission Period & Design Reuse Disclosures**
- **Repository Initialization**: Initialized on **October 29th, 2026 at 15:40:22 +0530** (commit `0537dde`) after earlier local prototype code existed.
- **Reused Design System**: The frontend dashboard visual styling, dark tokens, and CSS layout were adapted from the author's separate project (`emsearch-polaris/frontend`), reusing `src/design-system/tokens.css`, `src/index.css`, and `src/components/ui/Beams.tsx`.
- **Built During the Submission Period**: Everything else—including the multi-agent capability broker, atomic budget reservation manager, two-stage verification sandbox, Bayesian Beta(2,1) reputation engine, all 6 worker microservices, Tesseract OCR integrations, Groq inference pipelines, live PayPal Sandbox Payouts REST API settlement, and tamper-evident SHA-256 hash chaining—was conceived and developed entirely during the hackathon submission window.

---

### **Instructions for Judges: Zero to Demo in 60 Seconds**
1. **Clone & Setup**:
   ```bash
   git clone https://github.com/Aarav7162/procure-agent.git
   cd procure-agent
   pip install -r requirements.txt
   pip install -e .
   copy .env.example .env
   ```
2. **One-Command Boot**:
   ```bash
   python start.py
   ```
   *Automatically launches all 7 microservices and opens the Polaris Command Centre at `http://127.0.0.1:8000/`.*
3. **Interactive CLIs**:
   - Run `procure-agent` to launch the Buyer CLI (`/run`, `/attack`, `/impossible`, `/verify`).
   - Run `worker-agent` to launch the Seller CLI (`/manifest`, `/edit`, `/test`, `/start`).
4. **Programmatic REST Endpoint**:
   ```bash
   curl -X POST http://localhost:8000/procure \
     -H "Content-Type: application/json" \
     -d '{"task": "Fix month-end rollover bug in billing.py", "budget_usd": 0.50}'
   ```
5. **Replay Mode (Zero API Keys Required)**:
   Toggle the top switch to **Replay Mode** in the dashboard to step through the authentic 15-event code bounty run with verified PayPal batch IDs and tamper-evident ledger hashes.

---

### **The Problem: The Blind Trust Dilemma in Multi-Agent Delegation**
Current multi-agent architectures operate under **implicit trust**:
1. **The Rogue Underbidder Attack**: A malicious, compromised, or cheap low-parameter worker can underbid honest competitors, deliver plausible-looking hallucinations or defective code, and immediately collect compensation.
2. **The LLM Judge Reliability Trap**: Relying strictly on an LLM to evaluate another LLM creates shared blindspots, non-deterministic scoring, and hallucinated compliance. In ProcureAgent, judge-only subjective evaluations are explicitly flagged as lower confidence.
3. **Premature Capital Flight**: Traditional payment setups lack programmatic budget reservations tied to deterministic test execution, risking financial loss when external agent labor fails.

---

### **Our Solution: ProcureAgent Zero-Trust Architecture**
ProcureAgent provides an economic and verification protocol that allows agents to safely hire peer agents within strict financial boundaries:

1. **Autonomous Spending Policy Engine (`config/bounty_policy.yaml` & `orchestrator/policy.py`)**:
   - **Weekly Budget Ceiling**: Hard-capped at `$25.00 USD` weekly expenditure.
   - **Permitted Task Types**: Restricts procurement strictly to authorized capability schemas (`code_bounty`, `document_ocr`, `llm_synthesis`). Unrecognized requests are rejected upfront before reaching the capability broker.
   - **Human Approval Threshold**: Any single job request exceeding `$5.00 USD` triggers a human policy hold (`NEEDS_APPROVAL`), requiring explicit supervisory sign-off before funds are reserved or contracts awarded.
2. **Internal Budget Reservation ($S + R \le B$)**:
   Before external work begins, the orchestrator reserves the exact bid amount in internal bookkeeping. Funds cannot be double-spent, and the sum of spent plus reserved funds is **enforced by the database** (`audit/ledger.db` using SQLite `BEGIN IMMEDIATE` transactions) never to exceed the cycle budget.
3. **Two-Stage Zero-Trust Verification**:
   - **Stage 1 (Tamper-Evident Integrity)**: Validates that the submitted artifact matches the claimed SHA-256 payload digest.
   - **Stage 2 (Deterministic Acceptance)**:
     - For **Python Code**: Subprocess execution in an isolated sandbox against **hidden edge-case unit tests** with a 3.0s timeout. Candidate workers never receive hidden test files.
     - For **Document OCR**: Multi-stage Levenshtein Character Error Rate (CER) calculation against ground truth with whitespace and separator normalization (enforcing $\le 5.0\%$ CER).
     - For **LLM Answers**: Programmatic quote verification ensuring all evidence strings appear verbatim in source documents, combined with live HTTP 200 citation probing. Subjective evaluations lacking programmatic verifiers are visibly labeled as lower confidence.
4. **Automated PayPal Sandbox Settlement**:
   Payments are dispatched via the **PayPal Payouts REST API v1** (`POST /v1/payments/payouts`) *only after* verification approval. If verification fails, the budget reservation is released, the worker receives strictly **$0.00 sandbox USD**, and the task is autonomously reallocated to the next highest-scoring bidder.
5. **Bayesian Beta(2,1) Reputation & Cold-Start Policy**:
   Worker credibility is tracked via Bayesian updating ($\text{Beta}(2, 1)$ prior $\to$ 66.7% baseline score). Unproven workers ($N < 3$ tasks) are subject to a **$1.00 cold-start allocation cap** to prevent high-value treasury drain.
6. **Tamper-Evident Hash-Chained Ledger**:
   Every state transition is committed to an SQLite WAL database and anchored to an external SHA-256 hash chain (`audit/latest_chain_hash.txt`).

---

### **Differentiated Worker Engines & Empirical Model Benchmarks**

ProcureAgent features 5 honest specialized worker agents plus 1 scripted adversary spanning 3 distinct task families:

1. **Python Code Specialists (`openai/gpt-oss-120b` vs `openai/gpt-oss-20b`)**:
   - Empirical benchmarks computed **exclusively from a live $N=30$ concurrent benchmark** without hand-tuning or backfill (maintained in `audit/run_log.jsonl`):
   - **120B Model**: 100.0% pass rate (30/30), 5.67s rolling average latency, Beta posterior reputation **0.9697**, $0.30 fixed operating fee.
   - **20B Model**: 23.3% pass rate (7/30), 4.70s rolling average latency, Beta posterior reputation **0.2727**, $0.22 fixed operating fee.
   - **Empirical Finding**: While the 20B model is 0.97s faster and offers an 8¢ cheaper bid ($0.22 vs $0.30), it repeatedly fails hidden calendar century rollover tests. Because its reputation drops to 0.2727, the 120B model's near-perfect credibility (0.9697) wins both tight and loose auctions.
2. **OCR Specialists (`ocr-worker-01` Alpha vs `ocr-worker-02` Beta)**:
   - Alpha uses raw Tesseract 5.5.0 PSM 3; Beta implements an image preprocessing pipeline (grayscale normalization, 2.0x contrast expansion, edge sharpening, and Otsu binarization before PSM 6).
   - Both achieve $\le 1.31\%$ CER across all 5 ground-truth test documents under our standard whitespace and separator normalization rule.
3. **LLM Synthesis Specialist (`llm-worker-01`)**:
   - Generates structured answers with live HTTP citation probing and programmatic quote grounding.
4. **Scripted Adversary (`rogue-worker-01`)**:
   - Fixed $0.18 underbid fixture delivering subtle leap-year century defects to prove zero-trust gating.

---

### **Explainable Capability Bidding Formula**
Except for the rogue worker's fixed $0.18 bid fixture (scripted to ensure an adversarial underbid in testing), honest worker bids are derived from a transparent economic formula:
$$\text{Bid}_{\text{USD}} = \min\left(\text{MaxBid}, \text{round}\left(C_{\text{api}} \times 1.25 + F_{\text{min}}, 2\right)\right)$$
Where $C_{\text{api}}$ is the raw token compute cost, $1.25$ is the risk multiplier, and $F_{\text{min}}$ is the worker's fixed operational fee ($0.15 for LLM, $0.22 for 20B, $0.30 for 120B). Because cloud inference costs are fractions of a cent, our analysis proves that the minimum operational fee dominates the final bid price.

---

### **What is Real vs. What is Simulated**
In accordance with our strict realism directive:
- **100% REAL LIVE STACK**:
  - PayPal Sandbox Payouts API integration (real batch IDs, synchronous polling, real sandbox payouts).
  - Groq LLM inference (`openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `qwen/qwen3.8-27b`).
  - Tesseract OCR execution and Levenshtein CER calculations.
  - Subprocess Python test execution in ephemeral sandboxes.
  - Live HTTP citation probing.
  - Append-only SQLite ledger with tamper-evident hash chaining.
- **VISIBLY LABELED SIMULATED FIXTURES**:
  - The rogue worker's fixed $0.18 bid, defective code patch, and OCR character distortions are scripted adversarial fixtures to ensure 100% reproducible test vectors without human intervention.
  - Simulated CI webhook triggers mimicking continuous integration pipeline failures.
  - Replay Mode: Deterministic playback of a 15-event verified code bounty run, allowing judges without API keys to evaluate the system with zero credentials.

---

### **Built During the Submission Period & Design Reuse Disclosures**
- **Repository Initialization**: Initialized on **October 29th, 2026 at 15:40:22 +0530** (commit `0537dde`) after earlier local prototype code existed.
- **Reused Design System**: The frontend dashboard visual styling, dark tokens, and CSS layout were adapted from the author's separate project (`emsearch-polaris/frontend`), reusing `src/design-system/tokens.css`, `src/index.css`, and `src/components/ui/Beams.tsx`.
- **Built During the Submission Period**: Everything else—including the multi-agent capability broker, atomic budget reservation manager, two-stage verification sandbox, Bayesian Beta(2,1) reputation engine, all 6 worker microservices, Tesseract OCR integrations, Groq inference pipelines, live PayPal Sandbox Payouts REST API settlement, and tamper-evident SHA-256 hash chaining—was conceived and developed entirely during the hackathon submission window.

---

### **Instructions for Judges: Zero to Demo in 60 Seconds**
1. **Clone & Setup**:
   ```bash
   git clone https://github.com/Aarav7162/ProcureAgent.git
   cd ProcureAgent
   pip install -r requirements.txt
   copy .env.example .env
   ```
2. **One-Command Boot**:
   ```bash
   python start.py
   ```
   *Automatically launches all 7 microservices and opens the Polaris Command Centre at `http://127.0.0.1:8000/`.*
3. **Replay Mode (Zero API Keys Required)**:
   Toggle the top switch to **Replay Mode** to step through the authentic 15-event code bounty run with verified PayPal batch IDs and tamper-evident ledger hashes.
4. **Live Mode**:
   Add your `GROQ_API_KEY` and PayPal Sandbox credentials to `.env`. Note: Real payouts require a PayPal Sandbox Business account in a payout-supported country. Judges without one can use Replay mode or set `PAYOUT_MODE=simulated`.


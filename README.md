# Orbit — Agentic Fraud Investigation System

An agentic fraud investigation system built by **Team Caffeine & Code** for the TigerGraph × HHGoa 2026 hackathon.

Orbit investigates fraud cases end-to-end on TigerGraph. It gathers evidence from a knowledge graph through custom MCP tools, reasons over that evidence with an LLM, assesses whether the evidence is sufficient, requests additional evidence when needed, recommends policy-compliant actions with the correct approval route, and writes the case back to the graph as retrievable case memory.

---

## Team Caffeine & Code

- Subrat Kumar Padhy (Lead)
- Priyanshu Jena
- Dinesh Kumar

Devfolio: Caffeine & Code

---

## Architecture

Orbit has four layers. Each layer is independent.

```
                +---------------------------+
                |   FRONTEND (React)        |
                |   Analyst Dashboard       |
                +-------------+-------------+
                              |
                              | reads answer JSON
                              |
                +-------------v-------------+
                |   LANGGRAPH ORCHESTRATOR  |
                |   9-node state machine    |
                +-------------+-------------+
                              |
                +-------------+-------------+
                |                           |
    +-----------v-----------+   +-----------v-----------+
    |   LLM REASONING       |   |   MCP TOOL SURFACE    |
    |   NVIDIA NIM          |   |   6 custom tools      |
    |   Gemini / Groq       |   |                       |
    |   (fallback chain)    |   |                       |
    +-----------------------+   +-----------+-----------+
                                            |
                                +-----------v-----------+
                                |   TIGERGRAPH          |
                                |   Community Edition   |
                                |   Knowledge Graph +   |
                                |   Vector + Memory     |
                                +-----------------------+
```

### Layer 1 — TigerGraph (Knowledge Graph Substrate)

TigerGraph stores the entities and relationships Orbit reasons over.

**Schema — 11 vertices, 21 edges**

Vertices:
- Customer
- Card
- Transaction
- DeviceProfile
- EmailDomain
- BillingRegion
- ClosedCase
- InvestigationCase
- ResolvedCase
- DocumentedPattern
- Evidence

Edges:
- Customer -[OWNS]-> Card
- Card -[MADE]-> Transaction
- Transaction -[FROM_DEVICE]-> DeviceProfile
- Transaction -[PURCHASER_EMAIL]-> EmailDomain
- Transaction -[BILLED_IN]-> BillingRegion
- Transaction -[NEXT]-> Transaction
- ClosedCase -[INVOLVES_TXN]-> Transaction
- ClosedCase -[ON_CARD]-> Card
- ClosedCase -[CONNECTED_TO]-> Card
- InvestigationCase -[INVESTIGATES]-> Transaction
- InvestigationCase -[HAS_EVIDENCE]-> Evidence
- InvestigationCase -[RESOLVED_AS]-> ResolvedCase
- ResolvedCase -[MATCHED_PATTERN]-> DocumentedPattern
- ResolvedCase -[INVOLVED_ENTITY_CARD]-> Card
- ResolvedCase -[INVOLVED_ENTITY_CUSTOMER]-> Customer
- ResolvedCase -[INVOLVED_ENTITY_DEVICE]-> DeviceProfile
- ResolvedCase -[INVOLVED_ENTITY_REGION]-> BillingRegion
- (plus reverse edges for traversal)

**Data loaded**

- 41,011 transactions
- 5,565 closed cases (confirmed fraud + cleared)
- 1,927 cards
- 1,896 customers
- 2,034 device profiles
- 47 email domains
- 96 billing regions

### Layer 2 — MCP Tool Surface

Six custom tools expose graph capabilities to Orbit. The LLM never writes raw GSQL at runtime. It selects from these validated tools.

| Tool | Purpose |
|---|---|
| `hhgoa__get_transaction_context` | Returns a transaction with its connected card, customer, device, email, region |
| `hhgoa__find_connected_entities` | Walks the graph from a customer to all connected cards, devices, emails, regions |
| `hhgoa__detect_pattern` | Runs one of four named detectors (SharedDeviceRing, VelocityBurst, AmountAnomaly, NewDeviceWithProxy) |
| `hhgoa__find_similar_cases` | Retrieves prior closed cases from case memory by shared entity or pattern |
| `hhgoa__record_evidence` | Writes an Evidence vertex linked to an InvestigationCase |
| `hhgoa__close_case` | Spawns a ResolvedCase linked to the entities and pattern |

The tools are registered with the official TigerGraph MCP server at startup.

### Layer 3 — LangGraph Orchestration

Nine nodes coordinate the investigation. Two use the LLM. Seven are deterministic.

| Node | Purpose | Type |
|---|---|---|
| `trigger` | Opens the InvestigationCase | Deterministic |
| `collect_evidence` | Calls the MCP tools, builds the Evidence Pack | Deterministic |
| `llm_investigate` | Reasons over the Evidence Pack | LLM |
| `assess_sufficiency` | Applies deterministic sufficiency rules | Deterministic |
| `request_evidence` | Issues mock evidence requests and loops back | Deterministic |
| `recommend_action` | Recommends policy-compliant actions | LLM |
| `enforce_policy` | Authorizes actions and assigns approval tier | Deterministic |
| `execute_or_approve` | Executes auto actions or waits for approval | Deterministic |
| `write_back` | Writes InvestigationCase, Evidence, ResolvedCase | Deterministic |

**Uncertainty loop and circuit breaker**

When the sufficiency engine returns INSUFFICIENT, the graph loops back to `collect_evidence` with the new evidence. The loop has a case-level cap of three rounds. On the third round, the circuit breaker forces escalation.

**Sufficiency engine**

The engine applies priority-ordered deterministic rules over four dimensions: Graph Evidence, Behavioral Evidence, Prior Case Match, and Contradictory Evidence. It produces one of three verdicts: SUFFICIENT, INSUFFICIENT, or CONTRADICTORY. Prior cases are analogical context only. They never raise sufficiency on their own.

**Policy engine**

The engine maps each recommended action to its approval tier. The LLM recommends. The policy engine authorizes. These are separate concerns.

- auto: agent may execute directly (MONITOR_CARD, VERIFY_WITH_CUSTOMER, CREATE_CASE, etc.)
- L1: team lead approval required (DECLINE_TRANSACTION, BLOCK_CARD when exposure ≤ $2,500)
- L2: fraud manager approval required (BLOCK_CARD when exposure > $2,500, BLOCK_ALL_CARDS, FILE_REPORT)

### Layer 4 — Frontend

The React dashboard reads the answer files Orbit produces. It does not run the agent. It renders the completed investigation.

Panels:

- Case selector
- Case details (amount, risk score, evidence sufficiency, status, typology, transaction details)
- Graph canvas (transaction topology with prior cases highlighted)
- Investigation terminal (5-step execution trace)
- Final case record (verdict, summary, customer verification, containment checklist)
- SAR viewer (FinCEN-standard narrative when a report is filed)

---

## How to Run Orbit End to End

### Prerequisites

- Docker Desktop
- Python 3.10 or later
- Node.js 18 or later
- A terminal (PowerShell on Windows, bash on macOS or Linux)

### Step 1 — Clone the repository

```
git clone https://github.com/subratkumarpadhy4/HHGoa.git
cd HHGoa
```

### Step 2 — Start TigerGraph Community Edition

```
docker run -d ^
  -p 14022:22 ^
  -p 9000:9000 ^
  -p 14240:14240 ^
  --name tigergraph ^
  --ulimit nofile=1000000:1000000 ^
  -v C:\tg-data:/home/tigergraph/mydata ^
  -v tg-data:/home/tigergraph ^
  -t tigergraph/community:latest
```

Wait 30 seconds. Then start the TigerGraph services:

```
docker exec -it --user tigergraph tigergraph bash
source ~/.bashrc
gadmin start all
exit
```

Verify REST++ is responding:

```
curl.exe http://localhost:9000/echo
```

Expected: {"error":false, "message":"Hello GSQL"}

### Step 3 — Create the Python environment

```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Step 4 — Configure environment variables

Copy `.env.example` to `.env` and fill in:

```
TG_HOST=http://localhost
TG_GRAPHNAME=HHGoa
TG_USERNAME=tigergraph
TG_PASSWORD=tigergraph
NVIDIA_API_KEY=nvapi-...
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_MODEL=meta/llama-3.2-11b-vision-instruct
GEMINI_API_KEY=...
GROQ_API_KEY=...
LLM_PROVIDER=nvidia
```

Orbit uses a multi-provider chain: NVIDIA NIM first, then Gemini, then Groq. At least one key is required.

### Step 5 — Create the graph schema

```
docker exec -it --user tigergraph tigergraph bash
cd /home/tigergraph/mydata
gsql -f create_schema.gsql
gsql -c "CREATE GRAPH HHGoa (*)"
exit
```

### Step 6 — Load the dataset

Place the HHGOA dataset files in `C:\HHGoa\data\`:

- transactions.csv
- identity.csv
- closed_cases_history.csv
- case_pack.csv

Then run:

```
python scripts\build_card_map.py
python scripts\load_minimal.py
```

The load takes 30 to 60 minutes. It writes 41,011 transactions, 5,565 closed cases, and all connected entities into the graph.

Verify with:

```
python scripts\verify_counts.py
```

### Step 7 — Start the MCP server

```
python -m mcp_server.run_server --transport streamable-http --host 127.0.0.1 --port 8000 --env-file C:\HHGoa\.env
```

Leave it running in a separate terminal window.

### Step 8 — Run Orbit on the benchmark cases

```
python -u agent\save_answers.py
```

This runs all 20 benchmark cases end to end. Each case takes approximately 50 seconds. The script writes one answer file per case to `results/answers/`.

To run individual demo cases:

```
python scripts\demo_evidence_loop.py
python scripts\demo_ambiguous_case.py
python scripts\demo_summary.py
```

### Step 9 — Start the frontend

```
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 in a browser.

The frontend reads from `frontend/public/cases/`. To refresh after re-running Orbit:

```
Copy-Item C:\HHGoa\results\answers\HHG-*.json C:\HHGoa\frontend\public\cases\
```

---

## Repository Layout

```
HHGoa/
├── agent/                      LangGraph orchestration and node definitions
│   ├── graph.py                State machine assembly
│   ├── state.py                AgentState schema
│   ├── llm.py                  Multi-provider LLM wrapper (NVIDIA, Gemini, Groq)
│   ├── mock_apis.py            Seeded mock evidence request APIs
│   ├── mcp_client.py           Python client for the MCP tools
│   ├── answer_generator.py     Converts agent state to the answer format
│   ├── sar_generator.py        FinCEN-standard SAR narrative generator
│   ├── save_answers.py         Runner for the 20 benchmark cases
│   └── nodes/                  Nine node implementations
├── mcp_server/                 MCP server with 6 custom tools
│   ├── custom_tools.py
│   └── run_server.py
├── scripts/                    Loaders, utilities, demo scripts
│   ├── build_card_map.py
│   ├── load_minimal.py
│   ├── verify_counts.py
│   ├── check_answers.py
│   ├── fix_answers.py
│   ├── demo_evidence_loop.py
│   ├── demo_ambiguous_case.py
│   └── demo_summary.py
├── schema/
│   └── create_schema.gsql      GSQL schema creation script
├── cases/                      20 answer files (HHG-001.json … HHG-020.json)
├── results/answers/            Working copy of answer files plus benchmark summary
├── frontend/                   React analyst dashboard
├── data/                       Dataset files (not committed, gitignored)
├── .env.example                Environment template
├── .gitignore
├── mcp_config.json             MCP server configuration
├── requirements.txt
└── README.md
```

---

## Benchmark Results

Orbit was run on all 20 benchmark cases in `case_pack.csv`.

| Metric | Value |
|---|---|
| Total cases | 20 |
| Investigated end to end | 20 |
| Errors | 0 |
| Closed as fraud | 15 |
| Escalated to analyst | 4 |
| Closed as legitimate | 1 |
| SARs filed | 6 |
| InvestigationCase vertices written | 20 |
| Evidence vertices written | 365 |
| ResolvedCase vertices spawned | 19 |
| Average latency per case | ~50 seconds |

Orbit did not treat the risk score as the answer. Half the benchmark cases were designed to be legitimate. Orbit discriminated correctly, escalating ambiguous cases instead of forcing a verdict.

---

## Investigation Lifecycle

For every case Orbit produces:

1. An InvestigationCase written to TigerGraph
2. An Evidence Pack built from graph queries and detector outputs
3. A structured finding from the LLM
4. A sufficiency verdict from the deterministic engine
5. Zero or more evidence requests, with simulated responses
6. A recommended action set with the correct approval route
7. A FinCEN-standard SAR narrative when the policy requires a report
8. A ResolvedCase written back to the graph as retrievable memory

---

## LLM Provider Chain

Orbit uses a multi-provider chain for resilience against rate limits.

1. NVIDIA NIM (meta/llama-3.2-11b-vision-instruct) — primary
2. Google Gemini (gemini-2.5-flash) — first fallback
3. Groq (openai/gpt-oss-20b, openai/gpt-oss-120b) — second fallback

Each provider is tried in order. On success, the response includes a `_provider` field. On failure, the chain moves to the next provider. All provider selection is logged to stdout.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Graph and vector storage | TigerGraph Community Edition (Docker) |
| Graph query language | GSQL |
| Agent framework | LangGraph 1.2 with langchain-core |
| LLM (primary) | NVIDIA NIM (meta/llama-3.2-11b-vision-instruct) |
| LLM (fallback) | Google Gemini 2.5 Flash, Groq |
| Agent-graph bridge | TigerGraph MCP server (official) |
| Frontend | React 18, Vite, TypeScript, Tailwind CSS |
| Runtime | Python 3.12 |

---

## Submission

- **Answer files**: `cases/` (20 files, HHG-001.json through HHG-020.json)
- **Benchmark summary**: `results/answers/_answers_summary.json`
- **Demo video**: [URL]
- **Blog post**: https://dev.to/subratkumarpadhy/building-an-agentic-fraud-investigation-system-with-tigergraph-langgraph-mcp-obd
- **Social posts**: https://www.linkedin.com/posts/jenapriyanshu003_building-an-agentic-fraud-investigation-system-activity-7508904691498471424-4ajY?utm_source=share&utm_medium=member_android&rcm=ACoAAF3hOyMB5Qhy3sfvszwiTOx8KD3x2eOMMsM, [URL 2], [URL 3]
- **TigerGraph deployment**: Community Edition

---

## License

This project was built for the TigerGraph × HHGoa 2026 hackathon. The dataset is provided by TigerGraph and Vesta Corporation under the terms of the IEEE-CIS Fraud Detection dataset.

# CLAUDE.md — kari.ai

This file is the source of truth for Claude Code when working on this project.
Read this fully before touching any file.

---

## What This Project Is

**kari.ai** is a locally-run AI classroom simulator. Educators upload a course syllabus
and a swarm of synthetic student agents live through it — each with their own learning
style, attention span, prior knowledge, and anxiety level.

The system outputs an insight report that critiques the curriculum itself: bad concept
ordering, Bloom's taxonomy mismatches, pacing issues, and which student archetypes fail.

> Think: The Sims for education. Each NPC is a student. The curriculum is the world.

---

## Monorepo Structure

```
kariai/
├── backend/                  # FastAPI + Python
├── frontend/                 # Next.js + Tailwind
├── CLAUDE.md                 # You are here
└── README.md
```

---

## Tech Stack

### Backend
- **FastAPI** — API server, async endpoints
- **LangGraph** — Agent orchestration state machine
- **LangChain** — RAG pipeline only (not for agents)
- **ChromaDB** — Local vector store, no external service
- **Python 3.11+**

### Frontend
- **Next.js 14** (App Router)
- **Tailwind CSS**
- **Recharts** — Confusion heatmap, retention charts
- **localStorage** — Session persistence, no database, no auth

### LLMs
- **Gemini Flash** — Student agents, Teacher agent, Assessor agent (high volume, cheap)
- **GPT-4o / Gemini Pro** — Orchestrator, Insight agent (deep reasoning)
- **GPT Image 2** — Insight report visual generation

### No database. No auth. Runs fully locally.

---

## Environment Variables

```bash
# backend/.env
OPENAI_API_KEY=
GOOGLE_API_KEY=           # Gemini

CHROMA_DB_PATH=./chroma_db
UPLOADS_PATH=./uploads
SESSIONS_PATH=./sessions

DEFAULT_STUDENT_MODEL=gemini-2.0-flash
DEFAULT_REASONING_MODEL=gpt-4o
```

---

## Common Commands

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev                 # runs on localhost:3000

# Ingest slides into ChromaDB
python -m rag.ingest --module m1 --file uploads/m1_slides.pdf
```

---

## Backend Architecture

### FastAPI Routes

```
POST /api/setup/ingest        # Upload syllabus + slides → ChromaDB
POST /api/setup/generate-mcq  # LLM reads syllabus, returns dynamic MCQs
POST /api/setup/build-class   # Form answers → student profiles JSON
POST /api/simulation/start    # Kicks off LangGraph simulation
GET  /api/simulation/status   # Poll simulation progress
GET  /api/report/{session_id} # Returns insight report
```

### LangGraph State Machine

The orchestrator is a LangGraph `StateGraph`. Every agent is a node. State is passed between nodes.

```python
# orchestrator/state.py — ClassroomState shape
class ClassroomState(TypedDict):
    session_id: str
    curriculum: CurriculumConfig
    students: list[StudentProfile]
    current_module: int
    current_timestep: int        # 1=deliver, 2=process, 3=exercise, 4=assess, 5=update
    timestep_logs: list[TimestepLog]
    module_results: list[ModuleResult]
    simulation_complete: bool
    insight_report: InsightReport | None
```

### Graph Flow

```
START
  └──► orchestrator_node
            │
            ├──► timekeeper_node        # advances clock, manages pacing
            │
            ├──► teacher_node           # generates lesson content → stored in ChromaDB
            │
            ├──► student_swarm_node     # calls all student agents sequentially
            │         └── peer_contagion_node   # high-influence students affect neighbours
            │
            ├──► assessor_node          # scores students, updates knowledge_state
            │
            ├──► [conditional edge]
            │         confusion > 0.7  → back to teacher_node (re-teach)
            │         module complete  → next module
            │         all modules done → insight_node
            │
            └──► insight_node
                      └──► END
```

### Conditional Edge Logic

```python
# orchestrator/graph.py
def should_advance(state: ClassroomState) -> str:
    avg_confusion = mean([s.confusion_level for s in state.students])
    if avg_confusion > 0.7:
        return "reteach"
    if state.current_module >= len(state.curriculum.modules) - 1:
        return "finish"
    return "advance"
```

---

## Agent Contracts

Every agent is a function: `(ClassroomState) -> ClassroomState`.
Agents do NOT communicate directly — everything goes through state.

### Teacher Agent
```python
# Input:  current module content from curriculum config
# Action: generates lesson delivery for this timestep
#         stores lesson content in ChromaDB under module key
# Output: state.current_lesson (text delivery content)
```

### Student Agent
```python
# Input:  current_lesson + student.knowledge_state + student.traits
# Rules:
#   - ONLY reason from knowledge_state, never from LLM's own knowledge
#   - RAG enabled during EXERCISE timestep (timestep 3) only
#   - RAG disabled during ASSESSMENT timestep (timestep 4)
# Output: {
#     understood: bool,
#     confusion_level: float,   # 0.0 - 1.0
#     attention_remaining: float,
#     action: "engaged" | "confused" | "zoned_out" | "asked_question",
#     knowledge_delta: float    # can be negative
# }
```

### Assessor Agent
```python
# Input:  all student timestep logs for current module
# Action: scores each student, updates knowledge_state
#         extracts key failure patterns
# Output: ModuleResult with per-student scores + at-risk flags
```

### Insight Agent
```python
# Input:  full simulation history (all module results)
# Action: critiques concept ordering, Bloom's alignment, pacing
#         generates confusion heatmap data
#         flags curriculum ordering issues
#         optionally calls GPT Image 2 for visual summary
# Output: InsightReport
```

---

## Knowledge Gating — Critical Rule

**LLMs already know everything. Student agents will behave unrealistically well without this.**

Every student agent system prompt MUST include their `knowledge_state` explicitly
and MUST include this instruction:

```python
KNOWLEDGE_GATE_INSTRUCTION = """
You are a student. You ONLY know the concepts listed in your knowledge_state
at the levels provided. You have NOT been taught anything outside this list.

When you encounter a concept not in your knowledge_state, you MUST express
confusion — do not infer or invent understanding you have not earned yet.

Your misconceptions are real beliefs you currently hold. Do not abandon them
unless the lesson directly corrects them.
"""
```

Do NOT skip this. It is what makes the simulation believable.

---

## RAG Design

### Ingestion (on setup)
```python
# rag/ingest.py
# 1. Parse PDF slides per module
# 2. Chunk into ~500 token segments
# 3. Embed + store in ChromaDB under collection: f"module_{module_id}"
# 4. Teacher agent also stores lesson delivery content same way
```

### Retrieval (per student, per exercise timestep)
```python
# rag/retriever.py
def retrieve(query: str, module_id: str, phase: str) -> str:
    if phase == "assessment":
        return ""           # RAG OFF during assessment — no exceptions
    collection = chroma.get_collection(f"module_{module_id}")
    return collection.query(query_texts=[query], n_results=3)
```

### Collections
```
module_0_slides      # user uploaded slides, Module 1
module_1_slides      # user uploaded slides, Module 2
...
module_0_lesson      # teacher agent generated delivery, Module 1
module_1_lesson      # teacher agent generated delivery, Module 2
```

---

## Student Profile Schema

```python
@dataclass
class StudentProfile:
    id: str
    name: str

    # Traits (set at generation, mostly static)
    learning_style: Literal["visual", "auditory", "reading", "kinesthetic"]
    attention_span_mins: int          # 8 - 25
    social_anxiety: float             # 0.0 - 1.0
    motivation: float                 # 0.0 - 1.0
    peer_influence: float             # 0.0 - 1.0 (how much neighbours affect them)

    # Dynamic state (updates each timestep)
    knowledge_state: dict[str, float] # concept → mastery level 0.0-1.0
    misconceptions: list[str]
    confusion_level: float            # current
    attention_remaining: float        # current
    cumulative_fatigue: float         # grows across modules
```

---

## Session Storage

No database. Sessions are stored as JSON files locally.

```python
# storage/session.py
SESSIONS_PATH = "./sessions"

def save_session(session_id: str, state: ClassroomState):
    path = f"{SESSIONS_PATH}/{session_id}.json"
    with open(path, "w") as f:
        json.dump(state, f, default=str)

def load_session(session_id: str) -> ClassroomState:
    path = f"{SESSIONS_PATH}/{session_id}.json"
    with open(path) as f:
        return json.load(f)
```

Session ID format: `session_YYYYMMDD_HHMMSS`

---

## Frontend Pages

| Route | Purpose |
|---|---|
| `/` | Landing page, start new simulation |
| `/setup` | Static input form (course info, student config, Bloom's) |
| `/setup/questions` | Dynamic LLM-generated MCQs about the curriculum |
| `/simulation` | Live simulation progress — module by module |
| `/report/[sessionId]` | Full insight report with charts |

### localStorage Keys
```
kari_current_session    → session ID of active simulation
kari_setup_form         → partial form state (for page refresh survival)
kari_sessions           → array of past session IDs
```

### Polling Pattern (Simulation Page)
```typescript
// Simulation runs async on backend. Frontend polls for progress.
useEffect(() => {
  const interval = setInterval(async () => {
    const res = await fetch(`/api/simulation/status?id=${sessionId}`)
    const data = await res.json()
    setProgress(data)
    if (data.complete) clearInterval(interval)
  }, 2000)
  return () => clearInterval(interval)
}, [sessionId])
```

---

## Agent Model Assignment

```python
AGENT_MODELS = {
    "orchestrator": "gpt-4o",
    "timekeeper":   "gemini-2.0-flash",
    "teacher":      "gemini-2.0-flash",
    "student":      "gemini-2.0-flash",   # called N times per timestep
    "assessor":     "gemini-2.0-flash",
    "insight":      "gpt-4o",             # deep curriculum reasoning
}
```

Student agents use Gemini Flash because they are called N_students × N_timesteps × N_modules
times. This is the highest volume call in the system. Keep their prompts lean.

---

## Prompt Engineering Rules

1. **Student agent output must always be valid JSON** — add schema to every prompt
2. **Keep student system prompts under 300 tokens** — they are called the most
3. **Knowledge gate instruction is non-negotiable** — always include it
4. **Teacher agent stores to ChromaDB before students process** — order matters
5. **Insight agent receives full module_results list** — not raw logs, aggregated only

### Student Agent Output Schema (enforce strictly)
```json
{
  "understood": true,
  "confusion_level": 0.4,
  "attention_remaining": 0.7,
  "action": "engaged",
  "knowledge_delta": 0.15,
  "misconception_corrected": null
}
```

---

## Bloom's Taxonomy Levels

Used for curriculum critique in Insight Agent.

```python
BLOOMS_LEVELS = {
    1: "Remember",    # recall facts
    2: "Understand",  # explain concepts
    3: "Apply",       # use in new situations → needs exercises
    4: "Analyse",     # break down, compare
    5: "Evaluate",    # judge, critique
    6: "Create"       # produce new work → needs projects
}

# Insight agent flags mismatch if:
# claimed_level >= 3 AND no exercise/project found in module content
```

---

## Known Constraints & Gotchas

- **Sequential student calls** — students run one at a time, not truly parallel.
  This is intentional. One shared Gemini Flash model, queued calls. Do NOT use
  `asyncio.gather` for student agent calls — it causes rate limit errors.

- **ChromaDB resets between sessions** — each new simulation ingests fresh.
  Do not assume collections persist across server restarts in dev.

- **Peer contagion runs after all students complete a timestep** — not during.
  Order: all students process → peer contagion adjusts influence → state saved.

- **Re-teach loops are capped at 2 per module** — prevent infinite loops.
  After 2 re-teaches, orchestrator advances regardless of confusion level.

- **Insight agent is the most expensive call** — runs once at the end only.
  Do not call it mid-simulation.

- **GPT Image 2 call is optional** — only if `ENABLE_VISUAL_REPORT=true` in .env.
  Skip in dev to save credits.

---

## Hackathon Scope — What to Skip

If time is tight, cut in this order:

```
SKIP FIRST   GPT Image 2 visual report
SKIP SECOND  Peer contagion between student agents
SKIP THIRD   Dynamic LLM-generated MCQs (use static form only)
SKIP FOURTH  Re-teach loops (always advance after one pass)
KEEP ALWAYS  Knowledge gating — without this the sim is useless
KEEP ALWAYS  RAG open/closed book distinction
KEEP ALWAYS  Insight agent curriculum ordering critique
```

---

## Team

| Role | Focus |
|---|---|
| Backend / AI Lead | LangGraph graph, agent prompts, knowledge gating |
| Backend / API | FastAPI routes, RAG ingestion, session storage, MCQ generator |
| Frontend | Next.js pages, simulation progress UI, report dashboard |
| Full Stack / Integrator | Frontend-backend connection, demo prep, pitch |

---

*kari.ai · Built for [Hackathon Name] · 2026*
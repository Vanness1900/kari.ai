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

## Implementation Status (2026-05-09)

What's actually wired vs aspirational in this doc. Update as code changes.

**Backend — wired:**
- LangGraph state machine through `orchestrator → timekeeper → (student_questions on t=2) → teacher → student_swarm → peer (stub) → stats`, then `bump_timestep` / `advance_module` / `assessor_phase → insight → END`.
- Per-node checkpointing: `run_simulation_streaming` uses `graph.stream(stream_mode="values")` and persists `ClassroomState` to `sessions/{id}.json` (atomic write) after every node fires.
- Endpoints: `POST /api/simulation/start` (BackgroundTasks, returns `{session_id}`), `GET /api/simulation/status`, `/state`, `/events?since=N`, `/api/report/{session_id}`, `/api/sessions`, `/health`. Plus `POST /api/simulation/debug/run` (sync; debugging only).
- Optional parallelism in student / student_questions / assessor via `ThreadPoolExecutor` (feature-flagged; **not** asyncio.gather).
- Knowledge gating prompt is enforced inside `agents/student.py` and `agents/student_questions.py`.

**Frontend — wired:**
- `/` — `ConfigScreen`. Submit POSTs `/api/simulation/start` and routes to `/simulation/[sessionId]`.
- `/simulation/[sessionId]` — live polling view: `TeacherPanel`, `StudentGrid` (click → `StudentTimeline` drill-down), `QnaTranscript`, `KnowledgeGrowthChart`, `ConfusionHeatmap`. Auto-redirects to report on completion.
- `/report/[sessionId]` — Insight critique + per-student Assessor cards + the same charts on full-run data.
- `/main` — legacy demo; still mounted, no longer the destination of ConfigScreen.

**Aspirational / not built yet:**
- `/api/setup/ingest`, `/api/setup/generate-mcq`, `/api/setup/build-class` endpoints.
- RAG retrieval into the simulation loop (modules in `rag/` exist as scaffolding only; agents currently don't call them).
- Dynamic LLM-generated MCQ flow (`/setup/questions` page).
- GPT Image 2 visual report (gated by `ENABLE_VISUAL_REPORT`).

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
- **Next.js 16** (App Router; React 19.2). NB: dynamic-route `params` is a `Promise` — `await params` in `page.tsx`. `next lint` was removed; the project's `lint` script just runs `eslint`.
- **Tailwind CSS 4**
- **Recharts** — line chart for per-student knowledge growth; CSS-grid heatmap for per-module confusion (heatmap is custom, not Recharts).
- **localStorage / sessionStorage** — config persistence on the client; no auth, no DB.

### LLMs
- **Gemini Flash** — Student agents, Teacher agent, Timekeeper (high volume, cheap)
- **GPT-4o / Gemini Pro** — Orchestrator, Insight agent (deep reasoning); optionally Assessor if not on Flash
- **GPT Image 2** — Insight report visual generation

### No database. No auth. Runs fully locally.

---

## Environment Variables

```bash
# backend/.env (or backend/.env.local — both are loaded; .env.local wins)
OPENAI_API_KEY=
GOOGLE_API_KEY=                 # Gemini

CHROMA_DB_PATH=./chroma_db
UPLOADS_PATH=./uploads
SESSIONS_PATH=./sessions

DEFAULT_STUDENT_MODEL=gemini-2.0-flash
DEFAULT_TEACHER_MODEL=gemini-2.0-flash
DEFAULT_REASONING_MODEL=gpt-4o

# Concurrency knobs (default false / 4) — see Gotchas
ENABLE_PARALLEL_STUDENTS=false
ENABLE_PARALLEL_ASSESSOR=false
MAX_CONCURRENCY=4

# Optional
ENABLE_VISUAL_REPORT=false
CORS_ORIGINS=http://localhost:3000
KARIAI_TRACE=                   # set to 1 to log each LangGraph node
```

```bash
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000   # base URL for backend; defaults to localhost:8000 if unset
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

Currently implemented in `backend/main.py`:

```
GET  /health                             # liveness probe
POST /api/simulation/start               # body: StartRequest; kicks off run via BackgroundTasks; returns {session_id, status:"running"}
GET  /api/simulation/status?id=X         # cheap projection: current_module/timestep, log_count, simulation_complete, has_insight, has_error
GET  /api/simulation/state?id=X          # full ClassroomState snapshot (heavier; pull on phase change)
GET  /api/simulation/events?id=X&since=N # incremental slice of timestep_logs (cheap polling target)
GET  /api/sessions                       # newest-first list of saved sessions
GET  /api/report/{session_id}            # insight_report + student_assessments + students + curriculum + logs (409 until complete)
POST /api/simulation/debug/run           # synchronous full run; returns final state — debugging only
```

Planned but not yet implemented: `/api/setup/ingest`, `/api/setup/generate-mcq`, `/api/setup/build-class`.

### LangGraph State Machine

The orchestrator is a LangGraph `StateGraph`. Every agent is a node. State is passed between nodes.

```python
# orchestrator/state.py — ClassroomState shape (matches code as of 2026-05-09)
class ClassroomState(TypedDict):
    session_id: str
    curriculum: CurriculumConfig
    students: list[StudentProfileDict]
    current_module: int
    current_timestep: int                       # 1=deliver, 2=qna, 3=exercise, 4=assess, 5=update

    # List fields use Annotated[list[...], operator.add] so node partials append rather than replace.
    timestep_logs: Annotated[list[TimestepLog], operator.add]
    module_results: Annotated[list[ModuleResult], operator.add]

    # Per-student post-course assessments (filled sequentially in assessor phase). NOT a whole-class lump.
    student_assessments: dict[str, AssessmentRecord] | None
    assessor_index: int                         # progress cursor inside assessor phase

    simulation_complete: bool
    insight_report: InsightReport | None

    current_lesson: str | None                  # latest teacher output for the active phase
    module_delivery_snapshot: str | None        # captured at timestep 1; QNA students reason against this
    qna_student_questions: list[dict[str, Any]] # filled by student_questions node, consumed by teacher on t=2
    avg_confusion_last: NotRequired[float]      # rolling mean of student confusion (set by stats node)
```

### Graph Flow

**During the simulation loop** the graph runs **teacher → students → peer effects** only.
**Confusion and `knowledge_state` updates** come from **student agent outputs** each timestep
(LangGraph merges them into `ClassroomState`). There is **no Assessor node** in this loop.

**After** every module’s timesteps have finished (entire syllabus traversed), run an **Assessor phase**:
for **each student**, assess that learner’s arc (growth, misconceptions, at-risk signals) from
their slice of `timestep_logs` plus their final profile — same **sequential** discipline as the
student swarm (**no** `asyncio.gather`). Then run **Insight** (curriculum critique; may aggregate
from `student_assessments` but Assessor itself is **per student**, not one combined class judgment).

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
            ├──► [conditional edge from assessor stub — forward only, no re-teach loop]
            │         still within module timesteps 1–5 → bump_timestep → loop
            │         finished timestep 5 + more modules → advance_module → loop
            │         finished timestep 5 on last module → insight → END
            │         (timestep 2 = QNA: student_questions → teacher → students — confusion relief)
            │
            ├──► assessor_node          # N sequential passes (one per student); fills student_assessments
            │
            └──► insight_node           # curriculum critique (uses Assessor output + logs)
                      └──► END
```

### Conditional Edge Logic

Routers **mid-simulation** are **forward-only** on the timestep clock (no confusion-triggered
re-teach). **QNA (timestep 2)** is the primary confusion-relief phase without repeating full delivery.

```python
# orchestrator/graph.py — reference router after the per-round assessor node (stub in hackathon)
def router_after_assessor(state: ClassroomState) -> str:
    if state.current_timestep < 5:
        return "next_timestep"
    modules = state.curriculum.get("modules") or []
    if state.current_module >= len(modules) - 1:
        return "run_insight"
    return "advance_module"
```

### Timestep semantics (per module)

| `current_timestep` | Phase     | Notes |
|--------------------|-----------|--------|
| 1 | deliver | Teacher-generated module content → `current_lesson` |
| 2 | qna | Clarification / questions; primary confusion relief (`student_questions` → teacher Q&A) |
| 3 | exercise | RAG on when wired |
| 4 | assess | RAG off |
| 5 | update | Recap / consolidation |

Then insight node after the last module (`insight_report`) → END. (Full Assessor-after-syllabus pattern remains described in code comments / future wiring.)

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
#   - QNA timestep (2): clarification / questions; primary confusion relief (separate student_questions → teacher)
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
# When:   After the entire simulation loop completes — not inside the teach/student timestep loop.
# Unit:   One **student** per invocation (repeat N times, sequential queue).
# Input:  that student’s id + filtered `timestep_logs` mentioning them + their row in `students`
#         (final knowledge_state, misconceptions, traits, etc.)
# Action: end-of-run judgment for **that learner only** — growth, gaps, stability, risk flags
#         (not a single LLM call that “assesses the whole class as one lump”)
# Output: merge into `student_assessments[student_id]` (see state shape); report UI reads per row
```

### Insight Agent
```python
# Input:  `student_assessments` (per-student Assessor outputs) + `timestep_logs` + curriculum
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
| `/` | `ConfigScreen`: form (course info, vision/mission, Bloom level, sliders) → POST `/api/simulation/start` → navigate to `/simulation/[id]` |
| `/simulation/[sessionId]` | Live polling view: teacher panel, student grid w/ drill-down timeline, QNA transcript, knowledge-growth line chart, confusion heatmap. Auto-redirects to report on completion. |
| `/report/[sessionId]` | Post-run deep-dive: Insight critique + per-student Assessor cards + the same charts on full data |
| `/main` | Legacy demo (`MainScreen` with hardcoded transcript). No longer the destination of the form. |

Planned: `/setup/questions` (dynamic MCQ flow). The setup form currently lives at `/`.

### Storage keys (client)

`frontend/src/lib/config-storage.ts`:
- `kari-curriculum-config` (sessionStorage) — last submitted form state.

`frontend/src/lib/local-import-storage.ts`:
- `curriculum` (localStorage) — imported curriculum PDFs/images.
- `content` (localStorage) — imported supporting content PDFs/images.

(Earlier docs referenced `kari_current_session`/`kari_setup_form`/`kari_sessions`; those keys are not used in code today.)

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
    "student":      "gemini-2.0-flash",   # called N_students × N_timesteps × N_modules (highest volume)
    "assessor":     "gemini-2.0-flash",   # N_students calls after loop — keep lean; or gpt-4o if few students
    "insight":      "gpt-4o",             # deep curriculum reasoning (ONE call/run)
}
```

Student agents use Gemini Flash because they are called N_students × N_timesteps × N_modules
times. This is the highest volume call in the system. Keep their prompts lean.
**Assessor** runs **once per student** after the syllabus ends (still **N_student** LLM calls per
simulation total). Default to Flash for parity with student swarm; use a reasoning model only if the
cohort is small or you need richer per-learner writeups.

---

## Prompt Engineering Rules

1. **Student agent output must always be valid JSON** — add schema to every prompt
2. **Keep student system prompts under 300 tokens** — they are called the most
3. **Knowledge gate instruction is non-negotiable** — always include it
4. **Teacher agent stores to ChromaDB before students process** — order matters
5. **Assessor runs after the loop, per student** — fills `student_assessments`; Insight then critiques curriculum using that + logs

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

- **Student / assessor concurrency is opt-in.** Default is sequential. Set
  `ENABLE_PARALLEL_STUDENTS=true` and/or `ENABLE_PARALLEL_ASSESSOR=true` and tune
  `MAX_CONCURRENCY` (default 4) to fan out via `ThreadPoolExecutor`. Do **not** use
  `asyncio.gather` for these calls — it causes rate-limit errors. Threads are fine
  because the LLM client releases the GIL during network I/O.

- **ChromaDB resets between sessions** — each new simulation ingests fresh.
  Do not assume collections persist across server restarts in dev.

- **Peer contagion runs after all students complete a timestep** — not during.
  Order: all students process → peer contagion adjusts influence → state saved.

- **QNA (timestep 2)** handles clarification and confusion relief in the forward clock — there is
  no separate re-teach branch in the graph.

- **Insight agent is a heavy call** — runs once at the end only (after Assessor phase).

- **Assessor phase** — runs **after** all timesteps/modules finish; **not** in the inner loop.
  It is implemented as **one Assessor invocation per student** (sequential), writing
  **`student_assessments`**. Do not substitute one giant “assess the whole class” call unless
  you explicitly change this contract. Align `backend/orchestrator/graph.py` accordingly.

- **GPT Image 2 call is optional** — only if `ENABLE_VISUAL_REPORT=true` in .env.
  Skip in dev to save credits.

---

## Hackathon Scope — What to Skip

If time is tight, cut in this order:

```
SKIP FIRST   GPT Image 2 visual report
SKIP SECOND  Peer contagion between student agents
SKIP THIRD   Dynamic LLM-generated MCQs (use static form only)
SKIP FOURTH  Optional confusion branches (extra QNA / mini re-deliver) — default forward clock only
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
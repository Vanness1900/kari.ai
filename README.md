# AI Swarm Curriculum Testing System

An AI-powered multi-agent educational simulation platform that evaluates curriculum quality, teaching effectiveness, and student understanding using Retrieval-Augmented Generation (RAG), semantic retrieval, and orchestrated AI agents.

---

# Overview

The AI Swarm Curriculum Testing System simulates a classroom environment using multiple AI agents:

- Teacher Agent
- Student Agents
- Assessor Agent
- Insight Agent

The platform allows educational institutions to upload curriculum materials, lecture slides, and notes, then simulate how students may learn, struggle, and perform throughout the course.

The system combines:
- Retrieval-Augmented Generation (RAG)
- Semantic vector search
- Multi-agent orchestration
- Educational reasoning
- Curriculum-grounded AI teaching

---

# Core Features

## Multi-Agent Educational Simulation

### Teacher Agent
- Delivers lesson content progressively
- Uses semantic RAG retrieval
- Simulates realistic university teaching behavior
- Supports module-by-module lesson delivery

### Student Agents
- Simulate learning progression
- Simulate confusion and misconceptions
- Model varying attention and understanding levels
- Produce realistic classroom learning behavior

### Assessor Agent
- Evaluates student understanding
- Detects misconceptions and risk flags
- Generates assessment narratives
- Uses lightweight RAG grounding for curriculum alignment

### Insight Agent
- Aggregates assessment insights
- Identifies curriculum weaknesses
- Generates educational analysis

---

# RAG Architecture

The system uses Retrieval-Augmented Generation (RAG) to provide semantic educational grounding.

## RAG Pipeline

```text
Document Upload
↓
Text Parsing
↓
Chunking
↓
Embedding Generation
↓
Vector Storage (ChromaDB)
↓
Semantic Retrieval
↓
Prompt Context Injection
↓
Agent Reasoning
```

---

# Technology Stack

## Backend
- Python 3.11
- FastAPI

## AI & LLM
- OpenAI API
- Gemini API (optional)

## RAG & Vector Search
- LangChain
- ChromaDB
- OpenAI Embeddings

## Parsing & Processing
- PyMuPDF (`fitz`)
- RecursiveCharacterTextSplitter

## Frontend
- React
- TypeScript
- TailwindCSS

## Orchestration
- Custom multi-agent orchestration system
- Stateful simulation pipeline

---

# System Architecture

```text
Frontend
↓
FastAPI Backend
↓
Orchestrator
↓
Teacher Agent (RAG-enabled)
↓
Student Agents
↓
Assessor Agent (RAG-enabled)
↓
Insight Agent
↓
Frontend Visualization
```

---

# Supported Educational Inputs

| Input Type | Parser |
|---|---|
| Curriculum PDFs | `parse_pdf()` |
| Lecture Slides | `parse_pdf()` |
| Educational Notes | `parse_text()` |

---

# Semantic Retrieval System

The system stores educational content as semantic embeddings using OpenAI Embeddings and ChromaDB.

This allows the AI agents to:
- retrieve relevant educational context
- understand conceptual similarity
- ground responses using uploaded curriculum materials

---

# Chunking Strategy

Documents are split into smaller semantic chunks using:

```python
RecursiveCharacterTextSplitter
```

Purpose:
- reduce token overhead
- improve retrieval precision
- optimize semantic search quality

---

# Metadata System

Each semantic chunk stores metadata such as:

```python
{
    "source": "nlp.pdf",
    "page": 4,
    "document_type": "curriculum",
    "chunk_id": 2
}
```

Purpose:
- explainability
- source tracing
- retrieval transparency

---

# Teacher Agent

The Teacher Agent:
- retrieves semantic educational context using RAG
- delivers lesson content progressively
- follows timestep-based educational phases

## Teaching Phases

| Step | Phase |
|---|---|
| 1 | deliver |
| 2 | qna |
| 3 | exercise |
| 4 | assess |
| 5 | update |

The teacher retrieves:
- current module content
- semantic educational explanations
- relevant curriculum grounding

The system intentionally avoids teaching the entire curriculum at once to preserve realistic educational pacing.

---

# Student Agents

Student Agents simulate:
- understanding
- confusion
- misconceptions
- attention variation
- learning progression

Students intentionally do NOT use RAG directly to prevent unrealistic omniscient behavior.

---

# Assessor Agent

The Assessor Agent evaluates:
- conceptual understanding
- learning outcomes
- misconceptions
- educational risk factors

The assessor uses lightweight semantic retrieval (`k=1`) to compare student understanding against curriculum expectations.

Example assessment output:

```text
SCORE: 0.82
FLAGS: low_attention
NARRATIVE: Student demonstrated good conceptual understanding but struggled with parsing concepts.
```

---

# Structured vs Semantic Knowledge

The system uses two complementary knowledge layers.

## Structured Curriculum State

Contains:
- modules
- sequencing
- orchestration flow

Purpose:
- curriculum progression
- simulation control

---

## Semantic RAG Memory

Contains:
- educational embeddings
- semantic context
- conceptual relationships

Purpose:
- grounded reasoning
- contextual retrieval

---

# Why Teacher Outputs Are Not Stored Back Into RAG

Teacher-generated lessons are NOT written back into the vector database.

Reason:
- preserves curriculum as canonical source truth
- prevents semantic contamination
- maintains retrieval quality

Architecture separation:

| Layer | Purpose |
|---|---|
| Vector Database | canonical educational knowledge |
| Orchestrator State | generated simulation memory |

---

# Frontend Upload Flow

```text
Frontend Upload
↓
FastAPI UploadFile
↓
Temporary File Storage
↓
ingest_document()
↓
RAG Processing Pipeline
```

---

# Explainability Features

The frontend can display semantic retrieval references such as:

```text
Retrieved from:
CM3060 NLP
Page 4
Curriculum PDF
```

This improves:
- transparency
- trustworthiness
- educational traceability

---

# Current System Capabilities

| Feature | Status |
|---|---|
| PDF Parsing | ✅ |
| Text Parsing | ✅ |
| Chunking | ✅ |
| Embeddings | ✅ |
| ChromaDB Integration | ✅ |
| Semantic Retrieval | ✅ |
| Teacher RAG Integration | ✅ |
| Assessor RAG Integration | ✅ |
| Metadata Tracing | ✅ |
| Multi-Agent Orchestration | ✅ |
| Educational Simulation | ✅ |

---

# Design Philosophy

This project is NOT:
- a generic chatbot
- a simple PDF summarizer
- a single-agent AI wrapper

This project is:
- a curriculum-grounded educational simulation platform
- a semantic educational reasoning system
- a multi-agent AI orchestration architecture

---

# Final System Flow

```text
Educational Documents
↓
Semantic RAG Memory
↓
Teacher Agent
↓
Student Simulation
↓
Assessor Evaluation
↓
Insight Aggregation
↓
Frontend Visualization
```

---

# Contributors
Made with Love by Vaness, Vicky, Desmond, Alex

# License
MIT Licence

MIT License

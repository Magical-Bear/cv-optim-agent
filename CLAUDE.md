# Context
Build a CV optimization Agent platform for an interview task. User uploads resume + JD, system analyzes match, user confirms/edits suggestions, system generates optimized resume. Must be Docker-deployable, use DeepSeek API via env var, LangGraph multi-agent, Vue3 frontend.

---

## Stack
- **Backend**: Python 3.11 + FastAPI (lifespan) + uv + Pydantic v2, full async
- **Agent**: LangChain V1.0 + LangGraph, 5 nodes
- **Frontend**: Vue 3 + Vite + JS + Element Plus
- **Resume parsing**: text paste + PDF (pdfplumber) + Word (python-docx)
- **Export**: Markdown download + PDF (WeasyPrint)
- **Storage**: in-memory dict with TTL, no DB
- **Docker**: single container, multi-stage build
- **CI**: GitHub Actions (docker build check)

---

## Directory Structure
```
cv-optim-agent/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app, lifespan, StaticFiles
│   │   ├── config.py         # Settings via pydantic-settings
│   │   ├── session.py        # In-memory session store + TTL cleanup
│   │   ├── routers/
│   │   │   └── api.py        # /api/upload, /api/analyze, /api/confirm, /api/export
│   │   ├── agents/
│   │   │   ├── graph.py      # LangGraph StateGraph definition
│   │   │   ├── nodes.py      # 5 node functions
│   │   │   ├── state.py      # AgentState TypedDict
│   │   │   └── tools.py      # LangChain Tool definitions
│   │   └── utils/
│   │       ├── parser.py     # PDF/Word/text parsing
│   │       └── exporter.py   # MD + PDF export
│   ├── pyproject.toml
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── main.js
│   │   ├── App.vue
│   │   ├── api/index.js      # axios calls
│   │   └── views/
│   │       ├── StepUpload.vue    # Step 1: paste/upload resume + JD
│   │       ├── StepReview.vue    # Step 2: analysis result, editable suggestions
│   │       └── StepResult.vue   # Step 3: preview + download
│   ├── package.json
│   └── vite.config.js
├── Dockerfile                # multi-stage: node build → python runtime
├── docker-compose.yml
├── .github/workflows/ci.yml
├── .gitignore
└── README.md
```

---

## LangGraph State + Nodes

### AgentState (TypedDict)
```python
class AgentState(TypedDict):
    resume_text: str
    jd_text: str
    resume_keywords: list[str]    # from resume_extractor
    jd_keywords: list[str]        # from jd_extractor
    match_report: MatchReport     # from matcher
    suggestions: list[Suggestion] # from suggester
    user_feedback: UserFeedback   # injected after HITL interrupt
    optimized_resume: str         # from rewriter
```

### Nodes
1. **resume_extractor** (LLM + Tool) — extract skills/keywords/experience from resume text
2. **jd_extractor** (LLM + Tool) — extract required skills/keywords from JD
3. **matcher** (LLM) — compare both keyword lists, output MatchReport (highlights, gaps, score)
4. **suggester** (LLM) — generate numbered improvement suggestions with priority
5. **rewriter** (LLM) — take original resume + selected/edited suggestions → output optimized resume markdown

Parallel: nodes 1 & 2 run as fan-out (two separate Send() calls from START), both feed into matcher.

HITL interrupt: after `suggester` completes, graph calls `interrupt(suggestions)`. FastAPI stores state in session. `POST /api/confirm` resumes graph with user feedback.

### Parallel Fan-out
```python
def route_start(state):
    return [Send("resume_extractor", state), Send("jd_extractor", state)]

graph.add_conditional_edges(START, route_start)
graph.add_edge("resume_extractor", "matcher")
graph.add_edge("jd_extractor", "matcher")
```

---

## LangChain Tools
- `extract_keywords(text: str) -> list[str]` — regex + LLM fallback, extracts tech skills
- `score_skill_match(resume_skills: list, jd_skills: list) -> dict` — intersection/gap ratio calc
- `format_report(highlights, gaps, score) -> MatchReport` — structured output formatter

All tools are @tool decorated, passed to nodes that need them via `bind_tools`.

---

## FastAPI Routes
- `POST /api/upload` — multipart file upload (PDF/Word), returns `{text: str}`
- `POST /api/analyze` — body: `{resume_text, jd_text}`, starts LangGraph, runs to interrupt, returns `{session_id, match_report, suggestions}`
- `POST /api/confirm` — body: `{session_id, selected_suggestions, extra_note}`, resumes graph, returns `{optimized_resume: str}`
- `GET /api/export/{session_id}?format=md|pdf` — returns file download

---

## Session Store
```python
sessions: dict[str, SessionData] = {}
# SessionData: {graph_state, checkpoint, created_at, graph_instance}
# TTL: 30 minutes, asyncio background task cleans every 5 min
# No lock needed (asyncio single-thread, dict ops atomic)
```

---

## Prompts (key points)
- **resume_extractor**: "Extract all technical skills, tools, languages, and role keywords as a structured list. Be exhaustive."
- **jd_extractor**: "Extract required and preferred skills from this JD. Mark required vs preferred."
- **matcher**: "Compare resume keywords vs JD keywords. Output: match highlights (with evidence), gaps (missing required skills), overall match score 0-100."
- **suggester**: "Generate 5-8 specific, actionable improvement suggestions. Each must have: id, priority (high/mid/low), original_text (what to change), suggested_text (concrete rewrite)."
- **rewriter**: "Rewrite the resume applying ONLY the user-selected suggestions. Keep all other content unchanged. Output clean Markdown."

---

## Dockerfile (multi-stage)
```dockerfile
# Stage 1: build Vue
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Stage 2: Python runtime
FROM python:3.11-slim AS runtime
# Install Chinese fonts for PDF export
RUN apt-get update && apt-get install -y fonts-noto-cjk weasyprint && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/pyproject.toml .
RUN pip install uv && uv sync
COPY backend/ .
COPY --from=frontend-build /app/frontend/dist ./static
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Environment Variables (.env.example)
```
DEEPSEEK_API_KEY=sk-xxx          # DeepSeek API key (required)
DEEPSEEK_BASE_URL=https://api.deepseek.com  # API base URL
DEEPSEEK_MODEL=deepseek-chat     # Model name
SESSION_TTL_MINUTES=30           # Session expiry
MAX_UPLOAD_SIZE_MB=10            # Max file upload size
```

---

## Frontend Flow
1. **StepUpload.vue**: textarea for resume paste OR file upload button (PDF/Word → calls /api/upload) + JD textarea → Submit → calls /api/analyze → store session_id + report in state → navigate to StepReview
2. **StepReview.vue**: show MatchReport (score badge, highlights list, gaps list) + suggestions as editable el-card list (checkbox to select, editable textarea per suggestion, extra-note textarea) → Confirm → calls /api/confirm → navigate to StepResult
3. **StepResult.vue**: markdown preview (use marked.js) of optimized resume + Download MD button + Download PDF button (calls /api/export)

---

## Risk Mitigation
1. **LangGraph HITL API**: use `interrupt()` from `langgraph.types`, store `config` with thread_id in session, resume with `graph.invoke(Command(resume=feedback), config)`. Must use checkpointer (MemorySaver).
2. **DeepSeek tool_use compat**: DeepSeek is OpenAI-compatible but tool calling may differ. Use `langchain-openai` with `base_url` override. Test with simple tool call first.
3. **PDF Chinese fonts**: `fonts-noto-cjk` in Dockerfile covers it. WeasyPrint needs system fonts — test in container not host.
4. **LangGraph parallel fan-out**: matcher node must wait for both extractors. Use `reducer` on state fields to merge results from parallel nodes.
5. **File parsing edge cases**: pdfplumber may fail on scanned PDFs — add fallback message "Scanned PDF not supported, please paste text."

---

## Acceptance Test (command sequence)
```bash
git clone <repo>
cd cv-optim-agent
cp backend/.env.example backend/.env
# edit .env, set DEEPSEEK_API_KEY
docker build -t cv-optim .
docker run -p 8000:8000 --env-file backend/.env cv-optim
# open http://localhost:8000
# paste resume + JD → analyze → edit suggestions → confirm → download
```

---

## Implementation Order
1. `backend/` skeleton: config, session, FastAPI main
2. `agents/state.py` + `agents/tools.py`
3. `agents/nodes.py` (5 nodes with prompts)
4. `agents/graph.py` (LangGraph StateGraph + MemorySaver + interrupt)
5. `routers/api.py` (all 4 routes)
6. `utils/parser.py` + `utils/exporter.py`
7. `frontend/` Vue3 scaffold + 3 views + api.js
8. `Dockerfile` multi-stage + `docker-compose.yml`
9. `README.md` + `.github/workflows/ci.yml`
10. Local test → Docker test

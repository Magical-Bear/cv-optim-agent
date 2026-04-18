# CV Optim Agent — Backend API Reference

Base URL: `http://localhost:8000`

All request/response bodies are `application/json` unless noted.

---

## POST /api/upload

Upload a PDF or Word resume file. Creates a session and returns the session ID + extracted plain text.

**Content-Type:** `multipart/form-data`

| Field  | Type | Required | Description           |
|--------|------|----------|-----------------------|
| `file` | File | Yes      | `.pdf` or `.docx`, max 10 MB |

**Response 200**
```json
{
  "session_id": "uuid-string",
  "text": "string — extracted resume plain text"
}
```

**Error responses**

| Code | Reason |
|------|--------|
| 400  | Unsupported file type / file too large |
| 422  | Missing file field |
| 500  | Parse failure (e.g. scanned PDF — advise user to paste text) |

---

## POST /api/analyze

Start the LangGraph pipeline with resume text + JD text. Reuses the session created by `/api/upload`.  
Graph runs nodes: `resume_extractor` → `jd_extractor` (parallel) → `matcher` → `suggester`, then **pauses at HITL interrupt**.

**Request body**
```json
{
  "session_id":  "uuid-string — from /api/upload",
  "resume_text": "string — full resume text",
  "jd_text":     "string — full job description text"
}
```

**Response 200**
```json
{
  "match_report": {
    "score":      85,
    "highlights": ["string", "..."],
    "gaps":       ["string", "..."]
  },
  "suggestions": [
    {
      "id":             "s1",
      "priority":       "high | mid | low",
      "original_text":  "string — current resume phrase to change",
      "suggested_text": "string — concrete rewrite"
    }
  ]
}
```

**Error responses**

| Code | Reason |
|------|--------|
| 400  | Empty resume_text or jd_text |
| 404  | session_id not found or expired (TTL 30 min) |
| 500  | LLM / LangGraph failure |

---

## POST /api/confirm

Resume the paused graph with user-selected / edited suggestions.  
Graph continues: `rewriter` node produces the optimized resume.

**Request body**
```json
{
  "session_id":            "uuid-string",
  "selected_suggestions":  ["s1", "s3"],
  "edited_suggestions": [
    {
      "id":             "s2",
      "suggested_text": "string — user-edited rewrite (overrides original)"
    }
  ],
  "extra_note": "string — optional free-text instruction to rewriter"
}
```

> `selected_suggestions`: IDs of suggestions to apply as-is.  
> `edited_suggestions`: Suggestions the user modified (merged with selected list).  
> `extra_note`: Additional instruction forwarded to the rewriter prompt.

**Response 200**
```json
{
  "optimized_resume": "string — full optimized resume in Markdown format"
}
```

**Error responses**

| Code | Reason |
|------|--------|
| 400  | No suggestions selected |
| 404  | session_id not found or expired (TTL 30 min) |
| 500  | LLM / LangGraph failure |

---

## GET /api/export/{session_id}

Download the optimized resume as a file.

**Path parameter**

| Param        | Description         |
|--------------|---------------------|
| `session_id` | UUID from /api/upload |

**Query parameter**

| Param    | Values     | Default | Description          |
|----------|------------|---------|----------------------|
| `format` | `md`, `pdf`| `md`    | Output file format   |

**Response 200**

- `format=md` → `Content-Type: text/markdown`, file: `resume_optimized.md`
- `format=pdf` → `Content-Type: application/pdf`, file: `resume_optimized.pdf`

**Error responses**

| Code | Reason |
|------|--------|
| 404  | session_id not found or expired |
| 500  | PDF generation failure |

---

## Session Lifecycle

```
POST /api/upload   →  session created (TTL: 30 min), returns session_id
POST /api/analyze  →  session updated with match_report + suggestions (reuses session_id)
POST /api/confirm  →  session updated with optimized_resume
GET  /api/export   →  read-only, session kept until TTL
```

Sessions are stored in-memory. Server restart clears all sessions.  
Background cleanup runs every 5 minutes.

---

## Data Models

### MatchReport
```typescript
{
  score:      number      // 0–100 overall match score
  highlights: string[]    // skills/experience that match JD
  gaps:       string[]    // required JD skills missing from resume
}
```

### Suggestion
```typescript
{
  id:             string  // unique within session, e.g. "s1"
  priority:       "high" | "mid" | "low"
  original_text:  string  // current text in resume
  suggested_text: string  // AI-proposed rewrite
}
```

### UserFeedback (sent to /api/confirm)
```typescript
{
  selected_suggestions: string[]          // suggestion IDs to apply as-is
  edited_suggestions:   EditedSuggestion[] // user-modified suggestions
  extra_note:           string            // free text instruction
}
```

---

## Environment Variables

| Variable              | Default                         | Description              |
|-----------------------|---------------------------------|--------------------------|
| `DEEPSEEK_API_KEY`    | —                               | Required. DeepSeek key   |
| `DEEPSEEK_BASE_URL`   | `https://api.deepseek.com`      | API base URL             |
| `DEEPSEEK_MODEL`      | `deepseek-chat`                 | Model name               |
| `SESSION_TTL_MINUTES` | `30`                            | Session expiry (minutes) |
| `MAX_UPLOAD_SIZE_MB`  | `10`                            | Max file upload size     |

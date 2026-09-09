# DocPilot MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an independently implemented enterprise document Q&A product that supports document ingestion, hybrid retrieval, reranking, cited answers, retrieval debugging, and evaluation.

**Architecture:** A React/TypeScript single-page frontend calls a Python 3.11 FastAPI backend. SQLite stores product metadata and text chunks, Qdrant stores vectors, and model providers are isolated behind typed interfaces so automated tests use deterministic fakes while manual acceptance uses Alibaba Bailian.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2, Pydantic 2, Pytest, Qdrant, OpenAI Python client, React 19, TypeScript, Vite, Vitest, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-09-07-docpilot-mvp-design.md`

## Global Constraints

- The code, product name, copy, and visual design must be original; Kotaemon is a product-flow reference only.
- API keys are read only from `.env`; `.env` is ignored and `.env.example` contains no real secret.
- The MVP has no authentication, multi-tenancy, OCR, GraphRAG, agent tools, billing, or web crawling.
- Every new backend behavior follows RED-GREEN-REFACTOR with a failing test observed before production code.
- External model and vector services are accessed through interfaces; automated tests never spend real model credits.
- The repository must remain runnable on Windows through Docker Compose and directly through documented development commands.

---

## Planned File Structure

```text
docpilot/
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py
│   │   ├── core/config.py
│   │   ├── core/errors.py
│   │   ├── db/base.py
│   │   ├── db/models.py
│   │   ├── api/health.py
│   │   ├── api/knowledge_bases.py
│   │   ├── api/documents.py
│   │   ├── api/chat.py
│   │   ├── api/retrieval.py
│   │   ├── api/evaluations.py
│   │   ├── schemas/*.py
│   │   └── services/{parsing,chunking,providers,bailian,vector_store,ingestion,retrieval,answering,evaluation}.py
│   └── tests/
├── frontend/
│   ├── package.json
│   └── src/{api,app,components,pages,test}/
├── sample-data/
├── scripts/smoke.ps1
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

### Task 1: Runnable Backend Foundation and Health Contract

**Files:**
- Create: `.gitignore`, `.env.example`, `backend/pyproject.toml`
- Create: `backend/app/__init__.py`, `backend/app/main.py`, `backend/app/core/config.py`, `backend/app/core/errors.py`
- Create: `backend/app/db/base.py`, `backend/app/db/models.py`, `backend/app/api/health.py`
- Test: `backend/tests/conftest.py`, `backend/tests/test_health.py`, `backend/tests/test_config.py`

**Interfaces:**
- Produces: `create_app() -> FastAPI`, `Settings`, `get_session()`, and `GET /api/health` returning `status`, `database`, `qdrant`, and `models`.

- [x] **Step 1: Write failing configuration and health tests**

```python
def test_settings_allows_local_start_without_bailian_key(monkeypatch):
    monkeypatch.delenv("BAILIAN_API_KEY", raising=False)
    settings = Settings(_env_file=None)
    assert settings.model_configured is False

def test_health_reports_database_without_exposing_secrets(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["database"] == "ok"
    assert "api_key" not in response.text.lower()
```

- [x] **Step 2: Run tests and verify RED**

Run: `cd backend; python -m pytest tests/test_config.py tests/test_health.py -v`

Expected: collection fails because `backend.app` modules do not exist.

- [x] **Step 3: Implement the minimal app, settings, SQLite session, and health route**

Use `pydantic-settings` with `BAILIAN_API_KEY`, `BAILIAN_BASE_URL`, `BAILIAN_WORKSPACE_ID`, `CHAT_MODEL`, `EMBEDDING_MODEL`, `RERANK_MODEL`, `DATABASE_URL`, and `QDRANT_URL`. The API key and workspace ID are optional at startup. Return `models: "configured"` only when the API key is non-empty; never return either value.

- [x] **Step 4: Verify GREEN and start the API once**

Run: `cd backend; python -m pytest -v`

Run: `cd backend; python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`

Verify: `Invoke-RestMethod http://127.0.0.1:8000/api/health` returns HTTP 200.

- [x] **Step 5: Commit**

```bash
git add .gitignore .env.example backend
git commit -m "feat: establish backend foundation"
```

---

### Task 2: Knowledge Base CRUD

**Files:**
- Modify: `backend/app/db/models.py`, `backend/app/main.py`
- Create: `backend/app/schemas/knowledge_base.py`, `backend/app/api/knowledge_bases.py`
- Test: `backend/tests/test_knowledge_bases.py`

**Interfaces:**
- Produces: `POST /api/knowledge-bases`, `GET /api/knowledge-bases`, `GET /api/knowledge-bases/{id}`, and `DELETE /api/knowledge-bases/{id}`.
- Produces: `KnowledgeBaseRead(id: UUID, name: str, description: str, document_count: int, created_at: datetime, updated_at: datetime)`.

- [x] **Step 1: Write failing CRUD behavior tests**

```python
def test_create_and_list_knowledge_base(client):
    created = client.post("/api/knowledge-bases", json={"name": "产品手册", "description": "公开演示资料"})
    assert created.status_code == 201
    rows = client.get("/api/knowledge-bases").json()
    assert rows[0]["name"] == "产品手册"
    assert rows[0]["document_count"] == 0

def test_duplicate_name_returns_conflict(client):
    payload = {"name": "产品手册", "description": ""}
    assert client.post("/api/knowledge-bases", json=payload).status_code == 201
    assert client.post("/api/knowledge-bases", json=payload).status_code == 409
```

- [x] **Step 2: Run the tests and verify RED**

Run: `cd backend; python -m pytest tests/test_knowledge_bases.py -v`

Expected: requests return 404 because the router does not exist.

- [x] **Step 3: Implement SQLAlchemy model, schemas, and CRUD router**

Use UUID strings as primary keys, trim names, reject empty names, and convert duplicate-name database errors into `KNOWLEDGE_BASE_EXISTS` with HTTP 409.

- [x] **Step 4: Verify GREEN**

Run: `cd backend; python -m pytest tests/test_knowledge_bases.py -v`

- [x] **Step 5: Commit**

```bash
git add backend/app backend/tests/test_knowledge_bases.py
git commit -m "feat: add knowledge base management"
```

---

### Task 3: Document Parsing and Deterministic Chunking

**Files:**
- Create: `backend/app/services/parsing.py`, `backend/app/services/chunking.py`
- Test: `backend/tests/test_parsing.py`, `backend/tests/test_chunking.py`
- Create: `backend/tests/fixtures/sample.txt`, `backend/tests/fixtures/sample.md`, `backend/tests/fixtures/sample.docx`, `backend/tests/fixtures/sample.pdf`

**Interfaces:**
- Produces: `parse_document(path: Path, media_type: str) -> ParsedDocument`.
- Produces: `chunk_text(text: str, document_id: str, chunk_size: int = 600, overlap: int = 100) -> list[TextChunk]`.
- `TextChunk` fields: `id`, `document_id`, `position`, `content`, `char_start`, `char_end`.

- [x] **Step 1: Write failing parser tests for TXT, Markdown, DOCX, PDF, and unsupported files**

```python
@pytest.mark.parametrize("fixture_name", ["sample.txt", "sample.md", "sample.docx", "sample.pdf"])
def test_parse_supported_document(fixture_dir, fixture_name):
    parsed = parse_document(fixture_dir / fixture_name, media_type_for(fixture_name))
    assert "退款期限为30天" in parsed.text

def test_parse_rejects_executable(tmp_path):
    path = tmp_path / "bad.exe"
    path.write_bytes(b"MZ")
    with pytest.raises(UnsupportedDocumentError):
        parse_document(path, "application/octet-stream")
```

- [x] **Step 2: Run parser tests and verify RED**

Run: `cd backend; python -m pytest tests/test_parsing.py -v`

- [x] **Step 3: Implement format-specific extraction without OCR**

Use UTF-8 decoding for TXT/Markdown, `python-docx` for DOCX paragraphs and tables, and `pypdf` for text-layer PDFs. Normalize repeated whitespace while preserving paragraph boundaries.

- [x] **Step 4: Write and run failing chunk boundary tests**

```python
def test_chunks_are_ordered_and_overlap():
    chunks = chunk_text("甲" * 1000, "doc-1", chunk_size=600, overlap=100)
    assert [(c.char_start, c.char_end) for c in chunks] == [(0, 600), (500, 1000)]
    assert [c.position for c in chunks] == [0, 1]
```

- [x] **Step 5: Implement chunking and verify all parser/chunk tests**

Run: `cd backend; python -m pytest tests/test_parsing.py tests/test_chunking.py -v`

- [x] **Step 6: Commit**

```bash
git add backend/app/services backend/tests
git commit -m "feat: parse and chunk supported documents"
```

---

### Task 4: Document Lifecycle and Vector Ingestion

**Files:**
- Modify: `backend/app/db/models.py`, `backend/app/main.py`
- Create: `backend/app/schemas/document.py`, `backend/app/api/documents.py`
- Create: `backend/app/services/providers.py`, `backend/app/services/bailian.py`, `backend/app/services/vector_store.py`, `backend/app/services/ingestion.py`
- Test: `backend/tests/fakes.py`, `backend/tests/test_documents.py`, `backend/tests/test_ingestion.py`

**Interfaces:**
- `EmbeddingProvider.embed(texts: list[str]) -> list[list[float]]`.
- `VectorStore.upsert(chunks: list[EmbeddedChunk]) -> None`, `delete_document(document_id: str) -> None`, and `search(knowledge_base_id: str, vector: list[float], limit: int) -> list[VectorHit]`.
- Produces upload/list/process/retry/delete document endpoints and statuses `pending`, `processing`, `ready`, `failed`.

- [x] **Step 1: Write failing lifecycle and ingestion tests using deterministic fakes**

```python
def test_ingestion_marks_ready_only_after_vectors_are_written(session, fake_embedder, fake_store, uploaded_document):
    ingest_document(session, uploaded_document.id, fake_embedder, fake_store)
    session.refresh(uploaded_document)
    assert uploaded_document.status == "ready"
    assert len(fake_store.rows) == uploaded_document.chunk_count

def test_ingestion_failure_is_retryable(session, failing_embedder, fake_store, uploaded_document):
    with pytest.raises(EmbeddingError):
        ingest_document(session, uploaded_document.id, failing_embedder, fake_store)
    session.refresh(uploaded_document)
    assert uploaded_document.status == "failed"
    assert uploaded_document.error_code == "EMBEDDING_FAILED"
```

- [x] **Step 2: Run tests and verify RED**

Run: `cd backend; python -m pytest tests/test_documents.py tests/test_ingestion.py -v`

- [x] **Step 3: Implement provider protocols, Bailian embedding batching, Qdrant adapter, and lifecycle transaction**

Batch at most 10 texts per `text-embedding-v4` request. Store Qdrant payload fields `knowledge_base_id`, `document_id`, `chunk_id`, `position`, and `content`. On retry, delete stale chunks and vectors before reprocessing.

- [x] **Step 4: Verify GREEN and deletion consistency**

Run: `cd backend; python -m pytest tests/test_documents.py tests/test_ingestion.py -v`

- [x] **Step 5: Commit**

```bash
git add backend/app backend/tests
git commit -m "feat: ingest documents into vector storage"
```

---

### Task 5: Hybrid Retrieval and Reranking

**Files:**
- Create: `backend/app/services/retrieval.py`, `backend/app/schemas/retrieval.py`, `backend/app/api/retrieval.py`
- Modify: `backend/app/services/providers.py`, `backend/app/services/bailian.py`, `backend/app/main.py`
- Test: `backend/tests/test_retrieval.py`, `backend/tests/test_retrieval_api.py`

**Interfaces:**
- `RerankProvider.rerank(query: str, documents: list[str]) -> list[float]`.
- `retrieve(query: str, knowledge_base_id: str, config: RetrievalConfig) -> RetrievalTrace`.
- `RetrievalHit` fields: `chunk_id`, `knowledge_base_id`, `document_id`, `file_name`, `content`, `vector_score`, `keyword_score`, `fusion_score`, `rerank_score`, `initial_rank`, `final_rank`.

- [x] **Step 1: Write failing fusion, isolation, and rerank tests**

```python
def test_hybrid_retrieval_exposes_rank_change(retriever):
    trace = retriever.retrieve("退款多久", "kb-1", RetrievalConfig(top_k=3))
    assert all(hit.initial_rank >= 1 for hit in trace.hits)
    assert all(hit.final_rank >= 1 for hit in trace.hits)
    assert trace.hits == sorted(trace.hits, key=lambda hit: hit.final_rank)

def test_retrieval_never_returns_another_knowledge_base(retriever):
    trace = retriever.retrieve("内部制度", "kb-1", RetrievalConfig(top_k=5))
    assert {hit.knowledge_base_id for hit in trace.hits} == {"kb-1"}
```

- [x] **Step 2: Run tests and verify RED**

Run: `cd backend; python -m pytest tests/test_retrieval.py tests/test_retrieval_api.py -v`

- [x] **Step 3: Implement BM25 keyword scoring, normalized weighted fusion, and Bailian reranking**

Default weights are vector `0.65` and keyword `0.35`; both must be between 0 and 1 and sum to 1. Call `qwen3-rerank` through the workspace-scoped Bailian rerank endpoint only after fusion and preserve every intermediate score in `RetrievalTrace`. When `BAILIAN_WORKSPACE_ID` is absent, return the fusion order with `rerank_status: "not_configured"` instead of pretending reranking occurred.

- [x] **Step 4: Implement `POST /api/retrieval/debug` and verify GREEN**

Run: `cd backend; python -m pytest tests/test_retrieval.py tests/test_retrieval_api.py -v`

- [x] **Step 5: Commit**

```bash
git add backend/app backend/tests
git commit -m "feat: add explainable hybrid retrieval"
```

---

### Task 6: Citation-Bound Chat and Reliable Refusal

**Files:**
- Create: `backend/app/services/answering.py`, `backend/app/schemas/chat.py`, `backend/app/api/chat.py`
- Modify: `backend/app/services/providers.py`, `backend/app/services/bailian.py`, `backend/app/db/models.py`, `backend/app/main.py`
- Test: `backend/tests/test_answering.py`, `backend/tests/test_chat_api.py`

**Interfaces:**
- `ChatProvider.answer(question: str, contexts: list[AnswerContext]) -> GeneratedAnswer`.
- `answer_question(request: ChatRequest) -> ChatResponse`.
- `ChatResponse` fields: `answer`, `decision` (`answer` or `insufficient_context`), `citations`, `retrieval_trace_id`, and `created_at`.

- [x] **Step 1: Write failing answer, citation, and refusal tests**

```python
def test_low_score_refuses_without_calling_chat(answering_service, fake_chat):
    result = answering_service.answer("文档外的问题", hits=[], threshold=0.55)
    assert result.decision == "insufficient_context"
    assert result.citations == []
    assert fake_chat.calls == 0

def test_answer_citations_are_limited_to_supplied_chunks(answering_service):
    result = answering_service.answer("退款多久", hits=known_hits(), threshold=0.55)
    assert {c.chunk_id for c in result.citations} <= {h.chunk_id for h in known_hits()}
```

- [x] **Step 2: Run tests and verify RED**

Run: `cd backend; python -m pytest tests/test_answering.py tests/test_chat_api.py -v`

- [x] **Step 3: Implement threshold gate, structured model output, citation validation, and chat persistence**

The system prompt requires JSON fields `answer` and `citation_ids`. Reject unknown citation IDs instead of displaying them. Refusal text is fixed product copy, not generated by the model.

- [x] **Step 4: Verify GREEN**

Run: `cd backend; python -m pytest tests/test_answering.py tests/test_chat_api.py -v`

- [x] **Step 5: Commit**

```bash
git add backend/app backend/tests
git commit -m "feat: answer with verified citations"
```

---

### Task 7: Evaluation Cases, Error Classification, and Batch Runs

**Files:**
- Modify: `backend/app/db/models.py`, `backend/app/main.py`
- Create: `backend/app/services/evaluation.py`, `backend/app/schemas/evaluation.py`, `backend/app/api/evaluations.py`
- Test: `backend/tests/test_evaluation.py`, `backend/tests/test_evaluation_api.py`
- Create: `sample-data/evaluation-cases.json`

**Interfaces:**
- `evaluate_case(case: EvaluationCase, response: ChatResponse, trace: RetrievalTrace) -> EvaluationResult`.
- Error values: `none`, `not_retrieved`, `ranked_too_low`, `answer_omission`, `wrong_citation`, `wrong_refusal`.
- Produces create/list/delete case endpoints and `POST /api/evaluations/run` returning totals, pass rate, and per-case results.

- [x] **Step 1: Write failing tests for every error category**

```python
@pytest.mark.parametrize(
    ("fixture_name", "expected_error"),
    [
        ("no_hit", "not_retrieved"),
        ("low_rank", "ranked_too_low"),
        ("missing_keyword", "answer_omission"),
        ("bad_citation", "wrong_citation"),
        ("bad_refusal", "wrong_refusal"),
    ],
)
def test_error_classification(evaluation_fixtures, fixture_name, expected_error):
    case, response, trace = evaluation_fixtures[fixture_name]
    assert evaluate_case(case, response, trace).error_type == expected_error
```

- [x] **Step 2: Run tests and verify RED**

Run: `cd backend; python -m pytest tests/test_evaluation.py tests/test_evaluation_api.py -v`

- [x] **Step 3: Implement rules, persistence, batch execution, and ten synthetic demo cases**

Pass requires the expected document in the configured top rank, all required keywords in the answer, only expected citations, and the expected refusal decision. Store the retrieval trace for every failure.

- [x] **Step 4: Verify GREEN and full backend regression suite**

Run: `cd backend; python -m pytest -v`

- [x] **Step 5: Commit**

```bash
git add backend/app backend/tests sample-data
git commit -m "feat: evaluate retrieval and answer quality"
```

---

### Task 8: Original React Product Interface

**Files:**
- Create: `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/index.html`
- Create: `frontend/src/main.tsx`, `frontend/src/app/router.tsx`, `frontend/src/styles/index.css`
- Create: `frontend/src/api/client.ts`, `frontend/src/api/types.ts`
- Create: `frontend/src/components/AppShell.tsx`, `StatusBadge.tsx`, `CitationCard.tsx`, `ScoreBar.tsx`, `EmptyState.tsx`
- Create: `frontend/src/pages/HomePage.tsx`, `KnowledgeBasePage.tsx`, `ChatPage.tsx`, `DebugPage.tsx`, `EvaluationPage.tsx`
- Test: `frontend/src/test/setup.ts`, `frontend/src/pages/*.test.tsx`

**Interfaces:**
- Consumes: all backend APIs and response types defined in Tasks 1-7.
- Produces: desktop-first routes `/`, `/knowledge-bases/:id`, `/knowledge-bases/:id/chat`, `/knowledge-bases/:id/debug`, and `/knowledge-bases/:id/evaluations`.

- [x] **Step 1: Scaffold Vite configuration and write failing route/screen tests**

```tsx
it('shows citation source beside an answered message', async () => {
  render(<ChatPage />, { wrapper: testRouter('/knowledge-bases/kb-1/chat') })
  await userEvent.type(screen.getByLabelText('问题'), '退款多久{enter}')
  expect(await screen.findByText('退款期限为30天')).toBeVisible()
  expect(screen.getByRole('button', { name: /查看引用：退款政策/ })).toBeVisible()
})
```

- [x] **Step 2: Run tests and verify RED**

Run: `cd frontend; npm test -- --run`

Expected: page and component modules cannot be resolved.

- [x] **Step 3: Implement the shared shell and five focused pages**

Use an original neutral blue-gray interface with one accent color, 16px base text, visible focus states, semantic labels, and a maximum content width of 1440px. The debug page uses a score table; the evaluation page uses summary cards plus a failure table. Do not copy Kotaemon layout or copy.

- [x] **Step 4: Verify component tests and production build**

Run: `cd frontend; npm test -- --run`

Run: `cd frontend; npm run build`

- [x] **Step 5: Commit**

```bash
git add frontend
git commit -m "feat: add DocPilot product interface"
```

---

### Task 9: Docker Runtime, Real-Provider Acceptance, and Portfolio Evidence

**Files:**
- Create: `backend/Dockerfile`, `frontend/Dockerfile`, `frontend/nginx.conf`, `docker-compose.yml`
- Create: `sample-data/企业产品手册.md`, `sample-data/员工服务说明.txt`, `sample-data/退款政策.md`
- Create: `docs/architecture.md`, `docs/testing.md`, `docs/screenshots/.gitkeep`
- Create: `README.md`, `LICENSE`
- Modify: `.env.example`

**Interfaces:**
- Produces: `docker compose up --build` with frontend on `http://127.0.0.1:3000`, API on `http://127.0.0.1:8000`, and Qdrant on `http://127.0.0.1:6333`.

- [x] **Step 1: Add a failing smoke test script**

Create `scripts/smoke.ps1` that exits nonzero unless health is OK, one sample file becomes `ready`, one in-document question returns at least one citation, and one unknown question returns `insufficient_context`.

Run: `powershell -ExecutionPolicy Bypass -File scripts/smoke.ps1`

Expected: FAIL because Docker runtime files and running services do not exist.

- [x] **Step 2: Implement containers, Compose networking, health checks, and sample data**

Use named volumes `docpilot_sqlite` and `docpilot_qdrant`. Mount no source code in the production profile. Pass only environment variable names required by the backend.

- [x] **Step 3: Run full automated verification**

Run: `cd backend; python -m pytest -v`

Run: `cd frontend; npm test -- --run`

Run: `cd frontend; npm run build`

Run: `docker compose config`

Run: `docker compose up --build -d`

- [x] **Step 4: Run real Bailian acceptance and capture evidence**

Run: `powershell -ExecutionPolicy Bypass -File scripts/smoke.ps1`

Manually verify the five pages at `http://127.0.0.1:3000`, then save screenshots showing document success, cited answer, refusal, rank change, and evaluation summary under `docs/screenshots/`.

- [x] **Step 5: Write portfolio README and evidence documents**

README sections are: problem, product workflow, features, screenshots, architecture, retrieval design, evaluation results, quick start, environment variables, testing, product decisions, reference disclosure, limitations, and roadmap. `docs/testing.md` records the ten cases and measured results without inventing metrics.

- [x] **Step 6: Verify public-repository safety**

Run: `git grep -n -I -E "sk-[A-Za-z0-9_-]{10,}|BAILIAN_API_KEY=.+" -- . ':!.env.example'`

Expected: no output.

Run: `git status --short`

Expected: only the files intentionally added for this task.

- [x] **Step 7: Commit and push the verified MVP**

```bash
git add .
git commit -m "docs: package verified DocPilot MVP"
git push origin main
```

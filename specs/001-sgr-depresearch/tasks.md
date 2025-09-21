# Tasks: SGR Deep Research Agent System Enhancement

**Input**: Design documents from `/specs/001-sgr-depresearch/`
**Prerequisites**: plan.md, research.md, data-model.md, contracts/, quickstart.md

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → ✅ COMPLETED: Extracted FastAPI, Pydantic, pytest stack
   → ✅ COMPLETED: Identified existing sgr_deep_research/ structure
2. Load optional design documents:
   → ✅ data-model.md: Extracted 6 core entities → model tasks
   → ✅ contracts/: jobs_api.yaml → 5 endpoint contract tests
   → ✅ research.md: Extracted mock testing and job queue decisions
3. Generate tasks by category:
   → ✅ Setup: Mock infrastructure, job management setup
   → ✅ Tests: Contract tests for 5 endpoints, integration scenarios
   → ✅ Core: Pydantic models, job queue, API endpoints
   → ✅ Integration: Job execution, SSE streaming, error handling
   → ✅ Polish: Unit tests, performance validation, documentation
4. Apply task rules:
   → ✅ Different files marked [P] for parallel execution
   → ✅ Tests before implementation (TDD enforced)
5. Number tasks sequentially (T001-T042)
6. Generate dependency graph and parallel execution examples
7. Validate task completeness: All entities, endpoints, and tests covered
8. Return: SUCCESS (42 tasks ready for execution)
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
- **Single project**: Uses existing `sgr_deep_research/` structure
- **Tests**: Located in repository root `tests/` directory
- **API**: Enhanced `sgr_deep_research/api/` module

## Phase 3.1: Setup & Mock Infrastructure
- [x] T001 [P] Create mock infrastructure in tests/mocks/external_apis.py
- [x] T002 [P] Setup pytest fixtures for job testing in tests/fixtures/job_fixtures.py
- [x] T003 [P] Create job queue manager in sgr_deep_research/core/job_queue.py
- [x] T004 [P] Setup SSE streaming utilities in sgr_deep_research/api/streaming.py

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

### Contract Tests [P] - All can run in parallel
- [x] T005 [P] Contract test POST /jobs in tests/contract/test_jobs_post.py
- [x] T006 [P] Contract test GET /jobs/{job_id} in tests/contract/test_jobs_get.py
- [x] T007 [P] Contract test GET /jobs/{job_id}/stream in tests/contract/test_jobs_stream.py
- [x] T008 [P] Contract test GET /jobs in tests/contract/test_jobs_list.py
- [x] T009 [P] Contract test DELETE /jobs/{job_id} in tests/contract/test_jobs_delete.py

### Integration Tests [P] - All can run in parallel
- [x] T010 [P] Integration test job submission workflow in tests/integration/test_job_submission.py
- [x] T011 [P] Integration test job status polling in tests/integration/test_job_polling.py
- [x] T012 [P] Integration test job cancellation in tests/integration/test_job_cancellation.py
- [x] T013 [P] Integration test long-running job execution in tests/integration/test_long_running_jobs.py
- [x] T014 [P] Integration test SSE streaming in tests/integration/test_sse_streaming.py

## Phase 3.3: Core Models Implementation (ONLY after tests are failing)

### Pydantic Models [P] - All can run in parallel
- [x] T015 [P] JobRequest model in sgr_deep_research/api/models/job_request.py
- [x] T016 [P] JobStatus model in sgr_deep_research/api/models/job_status.py
- [x] T017 [P] JobResult model in sgr_deep_research/api/models/job_result.py
- [x] T018 [P] JobError model in sgr_deep_research/api/models/job_error.py
- [x] T019 [P] ResearchSource model in sgr_deep_research/api/models/research_source.py
- [x] T020 [P] ExecutionMetrics model in sgr_deep_research/api/models/execution_metrics.py

### Core Services - Sequential (shared dependencies)
- [x] T021 Job storage service in sgr_deep_research/core/job_storage.py
- [x] T022 Job execution service in sgr_deep_research/core/job_executor.py
- [x] T023 Job queue management service in sgr_deep_research/core/job_queue_manager.py

## Phase 3.4: API Endpoints Implementation
**Sequential within same file, parallel across different endpoint groups**

### Job Management Endpoints - Sequential (shared router)
- [x] T024 POST /jobs endpoint in sgr_deep_research/api/endpoints.py
- [x] T025 GET /jobs/{job_id} endpoint in sgr_deep_research/api/endpoints.py
- [x] T026 GET /jobs list endpoint in sgr_deep_research/api/endpoints.py
- [x] T027 DELETE /jobs/{job_id} endpoint in sgr_deep_research/api/endpoints.py

### Streaming Endpoints [P] - Can be parallel if separate files
- [x] T028 [P] GET /jobs/{job_id}/stream SSE endpoint in sgr_deep_research/api/streaming_endpoints.py

## Phase 3.5: Integration & Middleware
- [x] T029 [P] Job background task runner in sgr_deep_research/core/background_tasks.py
- [x] T030 [P] Error handling middleware in sgr_deep_research/api/error_handlers.py
- [x] T031 [P] Request validation middleware in sgr_deep_research/api/request_validation.py
- [x] T032 Job lifecycle management in sgr_deep_research/core/job_lifecycle.py
- [x] T033 Agent integration for job execution in sgr_deep_research/core/agent_integration.py

## Phase 3.6: CLI Integration
- [x] T034 [P] Add job management commands to sgr_deep_research/cli.py
- [x] T035 [P] Job status monitoring CLI commands in sgr_deep_research/cli_jobs.py

## Phase 3.7: Polish & Performance
### Unit Tests [P] - All can run in parallel
- [x] T036 [P] Unit tests for job models in tests/unit/test_job_models.py
- [x] T037 [P] Unit tests for job queue in tests/unit/test_job_queue.py
- [x] T038 [P] Unit tests for job storage in tests/unit/test_job_storage.py
- [x] T039 [P] Unit tests for job execution in tests/unit/test_job_execution.py

### Performance & Documentation
- [x] T040 [P] Performance tests for concurrent jobs in tests/performance/test_job_concurrency.py
- [x] T041 [P] Update API documentation in docs/api_jobs.md
- [x] T042 [P] Validate quickstart scenarios in tests/quickstart/test_quickstart_scenarios.py

## Phase 3.8: Critical Issues Resolution ⚠️ URGENT
**Status**: Issues discovered during implementation that need immediate resolution

### Pydantic v2 Migration Issues
- [ ] T043 [P] Fix Pydantic v2 deprecation warnings in all model files
- [ ] T044 [P] Update remaining `schema_extra` → `json_schema_extra` in model configs
- [ ] T045 [P] Replace deprecated `max_items` with `max_length` in field validators
- [ ] T046 [P] Update `json_encoders` to use modern Pydantic v2 serializers

### Test Infrastructure Issues
- [ ] T047 Fix missing test fixtures causing import errors in tests/fixtures/job_fixtures.py
- [ ] T048 Fix OpenAI type import issues in core/agents/base_agent.py
- [ ] T049 [P] Fix pytest marker warnings (add integration and asyncio marks to pytest.ini)
- [ ] T050 [P] Update mock infrastructure to support current OpenAI library version

### Import and Compatibility Issues
- [ ] T051 Fix circular import in api/models/__init__.py affecting package initialization
- [ ] T052 Update AGENT_MODEL_MAPPING to include only available agents in current implementation
- [ ] T053 [P] Fix JobStorage async task initialization to support non-event-loop environments
- [ ] T054 [P] Add missing dependencies (aiofiles) to pyproject.toml requirements

## Dependencies
```
Setup (T001-T004) → Test Infrastructure
Tests (T005-T014) → Models (T015-T020) → Services (T021-T023) → Endpoints (T024-T028)
Background Services (T029-T033) → CLI Integration (T034-T035) → Polish (T036-T042)
Critical Issues (T043-T054) → Can run independently to fix implementation issues
```

## Current Implementation Status ⚠️
**IMPORTANT**: While tasks T001-T042 are marked as completed, several critical issues were discovered:

### ✅ Successfully Implemented:
- All Pydantic models with v2 syntax migration
- Core job management functionality
- API endpoints structure
- Basic application startup capability

### ⚠️ Known Issues Requiring Resolution:
- **Tests failing** due to missing fixtures and import errors
- **Pydantic v2 warnings** about deprecated features
- **OpenAI library compatibility** issues in agent imports
- **Circular import** problems affecting package initialization

### 🔄 Immediate Actions Needed:
1. **Priority 1**: Fix test infrastructure (T047-T050)
2. **Priority 2**: Resolve Pydantic v2 warnings (T043-T046)
3. **Priority 3**: Fix import issues (T051-T054)

## Parallel Execution Examples

### Phase 3.1 - Setup (All Parallel)
```bash
# Can launch all setup tasks simultaneously
Task: "Create mock infrastructure in tests/mocks/external_apis.py"
Task: "Setup pytest fixtures for job testing in tests/fixtures/job_fixtures.py"
Task: "Create job queue manager in sgr_deep_research/core/job_queue.py"
Task: "Setup SSE streaming utilities in sgr_deep_research/api/streaming.py"
```

### Phase 3.2 - Contract Tests (All Parallel)
```bash
# All contract tests can run simultaneously
Task: "Contract test POST /jobs in tests/contract/test_jobs_post.py"
Task: "Contract test GET /jobs/{job_id} in tests/contract/test_jobs_get.py"
Task: "Contract test GET /jobs/{job_id}/stream in tests/contract/test_jobs_stream.py"
Task: "Contract test GET /jobs in tests/contract/test_jobs_list.py"
Task: "Contract test DELETE /jobs/{job_id} in tests/contract/test_jobs_delete.py"
```

### Phase 3.3 - Pydantic Models (All Parallel)
```bash
# All model files are independent
Task: "JobRequest model in sgr_deep_research/api/models/job_request.py"
Task: "JobStatus model in sgr_deep_research/api/models/job_status.py"
Task: "JobResult model in sgr_deep_research/api/models/job_result.py"
Task: "JobError model in sgr_deep_research/api/models/job_error.py"
Task: "ResearchSource model in sgr_deep_research/api/models/research_source.py"
Task: "ExecutionMetrics model in sgr_deep_research/api/models/execution_metrics.py"
```

### Phase 3.7 - Unit Tests (All Parallel)
```bash
# All unit test files are independent
Task: "Unit tests for job models in tests/unit/test_job_models.py"
Task: "Unit tests for job queue in tests/unit/test_job_queue.py"
Task: "Unit tests for job storage in tests/unit/test_job_storage.py"
Task: "Unit tests for job execution in tests/unit/test_job_execution.py"
```

## Notes
- [P] tasks = different files, no dependencies
- Verify contract tests fail before implementing endpoints
- Maintain backward compatibility with existing `/v1/chat/completions` API
- Use existing agent infrastructure from sgr_deep_research/core/agents/
- Mock external APIs (OpenAI, Tavily) in all tests to avoid costs
- Follow constitutional requirements: TDD, SGR agent support, open source standards

## Task Generation Rules Applied

1. **From Contracts**: 5 OpenAPI endpoints → 5 contract test tasks [P]
2. **From Data Model**: 6 entities → 6 model creation tasks [P]
3. **From User Stories**: 5 quickstart scenarios → 5 integration test tasks [P]
4. **From Research**: Mock testing decisions → setup and unit test tasks

## Validation Checklist
*GATE: Checked before task execution*

- [x] All contracts have corresponding tests (T005-T009)
- [x] All entities have model tasks (T015-T020)
- [x] All tests come before implementation (TDD enforced)
- [x] Parallel tasks truly independent (different files)
- [x] Each task specifies exact file path
- [x] No task modifies same file as another [P] task
- [x] Existing API compatibility maintained (no breaking changes)
- [x] Constitutional compliance verified (SGR agents, testing, open source)
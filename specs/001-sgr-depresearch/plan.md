# Implementation Plan: SGR Deep Research Agent System Enhancement

**Branch**: `001-sgr-depresearch` | **Date**: 2025-01-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-sgr-depresearch/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → ✅ COMPLETED: Loaded spec for SGR agent system enhancement
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → ✅ COMPLETED: Identified existing Python/FastAPI system needing API enhancement
   → ✅ COMPLETED: Detected single project type with existing structure
3. Fill the Constitution Check section based on the content of the constitution document.
   → ✅ COMPLETED: Evaluated against SGR constitution v1.0.0
4. Evaluate Constitution Check section below
   → ✅ COMPLETED: No violations - enhancement aligns with constitutional principles
   → ✅ COMPLETED: Initial Constitution Check: PASS
5. Execute Phase 0 → research.md
   → ✅ COMPLETED: Researched API enhancement patterns and long-running job management
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, AGENTS.md
   → ✅ COMPLETED: Generated API contracts and data models for job management
7. Re-evaluate Constitution Check section
   → ✅ COMPLETED: Post-Design Constitution Check: PASS
8. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
   → ✅ COMPLETED: Defined TDD approach for API enhancements
9. STOP - Ready for /tasks command
   → ✅ COMPLETED: All phases complete, ready for task generation
```

**IMPORTANT**: The /plan command STOPS at step 9. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary
Enhancement of existing SGR Deep Research system to support long-running calculations through asynchronous job management API. Focus on non-streaming endpoints for batch processing, job status tracking via ID, and improved API design for complex multi-hour calculations. Includes comprehensive testing and mock test infrastructure.

## Technical Context
**Language/Version**: Python 3.10+ (existing codebase using uv package manager)
**Primary Dependencies**: FastAPI, Pydantic, Prefect, OpenAI, Rich, pytest (all existing)
**Storage**: File-based reports + in-memory job tracking (Redis for production scaling)
**Testing**: pytest with mock testing for external dependencies and API contracts
**Target Platform**: Linux server deployment with Docker support (existing)
**Project Type**: single (existing Python project with sgr_deep_research/ module)
**Performance Goals**: Handle 100+ concurrent long-running jobs, <500ms API response times
**Constraints**: Must maintain backward compatibility with existing OpenAI-compatible API
**Scale/Scope**: Support multi-hour calculations, job queuing, status polling, SSE updates

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**✅ Schema-Guided Reasoning First**: Enhancement preserves SGR agent architecture while adding job management layer
**✅ Multi-Agent Architecture**: New API supports all existing agent types (sgr, sgr-tools, etc.)
**✅ OpenAI-Compatible API**: Extends existing API without breaking compatibility, adds async job endpoints
**✅ Open Source Community Standards**: All enhancements follow existing MIT license and testing practices
**✅ Research Quality and Reproducibility**: Job tracking maintains research integrity and provides audit trails

**GATE STATUS**: ✅ PASS - All constitutional principles maintained

## Project Structure

### Documentation (this feature)
```
specs/001-sgr-depresearch/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
# Existing project structure (Option 1: Single project)
sgr_deep_research/
├── api/                 # EXISTING - will be enhanced
├── core/                # EXISTING - agents and tools
├── flows/               # EXISTING - Prefect workflows
├── cli.py               # EXISTING - will be enhanced
└── settings.py          # EXISTING - configuration

tests/                   # EXISTING - will be expanded
├── contract/            # NEW - API contract tests
├── integration/         # EXISTING - will be enhanced
├── unit/                # EXISTING - will be enhanced
└── mocks/               # NEW - mock infrastructure
```

**Structure Decision**: Option 1 (single project) - matches existing codebase structure

## Phase 0: Outline & Research
1. **Extract unknowns from Technical Context** above:
   - ✅ Research asynchronous job management patterns for FastAPI
   - ✅ Research job status tracking and polling mechanisms
   - ✅ Research non-streaming API design for long-running operations
   - ✅ Research mock testing strategies for external dependencies

2. **Generate and dispatch research agents**:
   ```
   ✅ Task: "Research FastAPI background task patterns for long-running jobs"
   ✅ Task: "Research job queue implementation with status tracking"
   ✅ Task: "Research Server-Sent Events for real-time job updates"
   ✅ Task: "Research mock testing patterns for AI agents and external APIs"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: ✅ research.md with all research findings consolidated

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. **Extract entities from feature spec** → `data-model.md`:
   - ✅ JobRequest: submission data, agent configuration, parameters
   - ✅ JobStatus: tracking state, progress, results, errors
   - ✅ JobResult: final output, metrics, sources, file paths
   - ✅ JobQueue: prioritization, concurrency limits, resource management

2. **Generate API contracts** from functional requirements:
   - ✅ POST /jobs - Submit long-running research job
   - ✅ GET /jobs/{job_id} - Get job status and results
   - ✅ GET /jobs/{job_id}/stream - SSE endpoint for real-time updates
   - ✅ GET /jobs - List user jobs with filtering
   - ✅ DELETE /jobs/{job_id} - Cancel running job
   - ✅ Output OpenAPI schema to `/contracts/`

3. **Generate contract tests** from contracts:
   - ✅ One test file per endpoint with schema validation
   - ✅ Tests must fail initially (no implementation yet)
   - ✅ Mock external dependencies (OpenAI, Tavily APIs)

4. **Extract test scenarios** from user stories:
   - ✅ Job submission and polling workflow
   - ✅ Long-running job with progress updates
   - ✅ Job cancellation and error handling
   - ✅ Quickstart test scenarios

5. **Update agent file incrementally** (O(1) operation):
   - ✅ Updated AGENTS.md with new API endpoints
   - ✅ Added job management workflow documentation
   - ✅ Preserved existing content, added enhancement notes

**Output**: ✅ data-model.md, /contracts/*, failing tests, quickstart.md, AGENTS.md updated

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
- Load `.specify/templates/tasks-template.md` as base
- Generate tasks from Phase 1 design docs (contracts, data model, quickstart)
- Each contract → contract test task [P]
- Each entity → model creation task [P]
- Each user story → integration test scenario
- Mock infrastructure setup tasks
- API enhancement implementation tasks

**Ordering Strategy**:
- TDD order: Tests before implementation
- Infrastructure: Mock setup → Model creation → API endpoints → Integration
- Mark [P] for parallel execution (independent files)
- Existing API compatibility maintained throughout

**Estimated Output**: 35-40 numbered, ordered tasks in tasks.md

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)
**Phase 4**: Implementation (execute tasks.md following constitutional principles)
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking
*No constitutional violations identified - no complexity tracking needed*

## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [x] Complexity deviations documented (none required)

---
*Based on Constitution v1.0.0 - See `.specify/memory/constitution.md`*
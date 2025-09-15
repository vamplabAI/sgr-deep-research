---
inclusion: always
---

# SGR Schema Layer - COMPREHENSIVE REFERENCE

## 🚨 CRITICAL: PYDANTIC MODEL DEFINITIONS

This document defines ALL Pydantic models used in the SGR system. **ALWAYS** reference this when creating model instances to avoid validation errors.

## Core SGR Models

### 1. Clarification
```python
from typing import Literal, List
from pydantic import BaseModel, Field
from typing_extensions import Annotated

class Clarification(BaseModel):
    tool: Literal["clarification"]
    reasoning: str = Field(description="Why clarification is needed")
    unclear_terms: Annotated[List[str], MinLen(1), MaxLen(5)] = Field(description="List of unclear terms")
    assumptions: Annotated[List[str], MinLen(2), MaxLen(4)] = Field(description="Possible interpretations")
    questions: Annotated[List[str], MinLen(3), MaxLen(5)] = Field(description="3-5 specific questions")

# VALID EXAMPLE:
clarification = Clarification(
    tool="clarification",
    reasoning="Request is ambiguous",
    unclear_terms=["term1"],
    assumptions=["assumption1", "assumption2"],
    questions=["question1", "question2", "question3"]
)
```

### 2. GeneratePlan
```python
class GeneratePlan(BaseModel):
    tool: Literal["generate_plan"]
    reasoning: str = Field(description="Justification for research approach")
    research_goal: str = Field(description="Primary research objective")
    planned_steps: Annotated[List[str], MinLen(3), MaxLen(4)] = Field(description="3-4 planned steps")
    search_strategies: Annotated[List[str], MinLen(2), MaxLen(3)] = Field(description="2-3 search strategies")

# VALID EXAMPLE:
plan = GeneratePlan(
    tool="generate_plan",
    reasoning="Need to research topic systematically",
    research_goal="Research jazz origins",
    planned_steps=["Step 1", "Step 2", "Step 3"],
    search_strategies=["Web search", "Source verification"]
)
```

### 3. WebSearch
```python
class WebSearch(BaseModel):
    tool: Literal["web_search"]
    reasoning: str = Field(description="Why this search is needed")
    query: str = Field(description="Search query")
    max_results: int = Field(default=10, description="Maximum results (1-15)")
    plan_adapted: bool = Field(default=False, description="Is this after plan adaptation")
    scrape_content: bool = Field(default=False, description="Fetch full page content")

# VALID EXAMPLE:
search = WebSearch(
    tool="web_search",
    reasoning="Need information about topic",
    query="jazz origins history",
    max_results=10,
    plan_adapted=False,
    scrape_content=False
)
```

### 4. AdaptPlan
```python
class AdaptPlan(BaseModel):
    tool: Literal["adapt_plan"]
    reasoning: str = Field(description="Why plan needs adaptation")
    original_goal: str = Field(description="Original research goal")
    new_goal: str = Field(description="Updated research goal")
    plan_changes: Annotated[List[str], MinLen(1), MaxLen(3)] = Field(description="Specific changes")
    next_steps: Annotated[List[str], MinLen(2), MaxLen(4)] = Field(description="Updated remaining steps")

# VALID EXAMPLE:
adapt = AdaptPlan(
    tool="adapt_plan",
    reasoning="New findings require plan adjustment",
    original_goal="Original goal",
    new_goal="Updated goal",
    plan_changes=["Change 1"],
    next_steps=["Step 1", "Step 2"]
)
```

### 5. CreateReport
```python
class CreateReport(BaseModel):
    tool: Literal["create_report"]
    reasoning: str = Field(description="Why ready to create report")
    title: str = Field(description="Report title")
    user_request_language_reference: str = Field(description="Copy of original user request")
    content: str = Field(description="Detailed report content with citations")
    confidence: Literal["high", "medium", "low"] = Field(description="Confidence in findings")

# VALID EXAMPLE:
report = CreateReport(
    tool="create_report",
    reasoning="Sufficient data collected",
    title="Research Report",
    user_request_language_reference="original user request",
    content="Detailed report content with citations [1]",
    confidence="high"
)
```

### 6. ReportCompletion
```python
class ReportCompletion(BaseModel):
    tool: Literal["report_completion"]
    reasoning: str = Field(description="Why research is complete")
    completed_steps: Annotated[List[str], MinLen(1), MaxLen(5)] = Field(description="Summary of steps")
    status: Literal["completed", "failed"] = Field(description="Task completion status")

# VALID EXAMPLE:
completion = ReportCompletion(
    tool="report_completion",
    reasoning="All research objectives met",
    completed_steps=["Generated plan", "Conducted searches", "Created report"],
    status="completed"
)
```

### 7. NextStep (Main Schema)
```python
from typing import Union

class NextStep(BaseModel):
    reasoning_steps: Annotated[List[str], MinLen(2), MaxLen(4)] = Field(description="Step-by-step reasoning")
    current_situation: str = Field(description="Current research situation")
    plan_status: str = Field(description="Status of current plan")
    searches_done: int = Field(default=0, description="Number of searches completed")
    enough_data: bool = Field(default=False, description="Sufficient data for report")
    remaining_steps: Annotated[List[str], MinLen(1), MaxLen(3)] = Field(description="Remaining steps")
    task_completed: bool = Field(description="Is research task finished")
    function: Union[Clarification, GeneratePlan, WebSearch, AdaptPlan, CreateReport, ReportCompletion]

# VALID EXAMPLE:
next_step = NextStep(
    reasoning_steps=["Step 1 reasoning", "Step 2 reasoning"],
    current_situation="Current state description",
    plan_status="active",
    searches_done=0,
    enough_data=False,
    remaining_steps=["Next step"],
    task_completed=False,
    function=GeneratePlan(
        tool="generate_plan",
        reasoning="Need to create plan",
        research_goal="Research goal",
        planned_steps=["Step 1", "Step 2", "Step 3"],
        search_strategies=["Strategy 1", "Strategy 2"]
    )
)
```

## 🚨 CRITICAL VALIDATION RULES

### List Length Requirements
- `unclear_terms`: 1-5 items
- `assumptions`: 2-4 items  
- `questions`: 3-5 items
- `planned_steps`: 3-4 items
- `search_strategies`: 2-3 items
- `plan_changes`: 1-3 items
- `next_steps`: 2-4 items
- `completed_steps`: 1-5 items
- `reasoning_steps`: 2-4 items
- `remaining_steps`: 1-3 items

### Literal Field Values
- `tool`: Must match exact string (e.g., "clarification", "generate_plan")
- `confidence`: Must be "high", "medium", or "low" (NOT numeric)
- `status`: Must be "completed" or "failed"

### Required Fields
ALL fields are required unless marked with `= Field(default=...)` or `= Field(default_factory=...)`

## 🛠️ HELPER FUNCTIONS FOR TESTING

```python
def create_valid_clarification():
    return Clarification(
        tool="clarification",
        reasoning="Request needs clarification",
        unclear_terms=["term1"],
        assumptions=["assumption1", "assumption2"],
        questions=["question1", "question2", "question3"]
    )

def create_valid_generate_plan():
    return GeneratePlan(
        tool="generate_plan",
        reasoning="Need systematic research approach",
        research_goal="Research topic thoroughly",
        planned_steps=["Initial research", "Deep analysis", "Synthesis"],
        search_strategies=["Web search", "Source verification"]
    )

def create_valid_web_search():
    return WebSearch(
        tool="web_search",
        reasoning="Need information on topic",
        query="research query"
    )

def create_valid_adapt_plan():
    return AdaptPlan(
        tool="adapt_plan",
        reasoning="Plan needs adjustment based on findings",
        original_goal="Original research goal",
        new_goal="Updated research goal",
        plan_changes=["Adjusted approach"],
        next_steps=["Continue research", "Analyze findings"]
    )

def create_valid_create_report():
    return CreateReport(
        tool="create_report",
        reasoning="Sufficient data collected for comprehensive report",
        title="Research Report Title",
        user_request_language_reference="original user request text",
        content="Detailed report content with proper citations [1]",
        confidence="high"
    )

def create_valid_report_completion():
    return ReportCompletion(
        tool="report_completion",
        reasoning="All research objectives completed successfully",
        completed_steps=["Plan created", "Searches conducted", "Report generated"],
        status="completed"
    )

def create_valid_next_step():
    return NextStep(
        reasoning_steps=["Analyzed current state", "Determined next action"],
        current_situation="Ready to begin research",
        plan_status="pending",
        searches_done=0,
        enough_data=False,
        remaining_steps=["Create research plan"],
        task_completed=False,
        function=create_valid_generate_plan()
    )
```

## 🚨 COMMON MISTAKES TO AVOID

1. **Empty Lists**: Never pass empty lists `[]` to fields with MinLen requirements
2. **Wrong Literal Values**: Use exact strings like "high" not 0.8 for confidence
3. **Missing Required Fields**: All fields without defaults are required
4. **Wrong List Lengths**: Check MinLen/MaxLen constraints
5. **Type Mismatches**: Ensure strings are strings, bools are bools, etc.

## 🔧 DEBUGGING PYDANTIC ERRORS

When you get a Pydantic validation error:

1. **Check the error message** - it tells you exactly what's wrong
2. **Verify field requirements** - reference this document
3. **Check list lengths** - ensure they meet MinLen/MaxLen
4. **Verify literal values** - use exact strings from Literal types
5. **Ensure all required fields** - provide values for non-default fields

## 📝 TESTING TEMPLATE

```python
# Use this template for testing SGR models
def test_sgr_models():
    try:
        # Test each model
        clarification = create_valid_clarification()
        plan = create_valid_generate_plan()
        search = create_valid_web_search()
        adapt = create_valid_adapt_plan()
        report = create_valid_create_report()
        completion = create_valid_report_completion()
        next_step = create_valid_next_step()
        
        print("✅ All models validate successfully")
        return True
        
    except Exception as e:
        print(f"❌ Validation error: {e}")
        return False
```

This schema reference should eliminate ALL Pydantic validation errors. Always reference the VALID EXAMPLES when creating model instances.

## 🛠️ SCHEMA UTILITIES MODULE

To make schema usage even easier, use the `schema_utils.py` module:

```python
from schema_utils import (
    create_clarification, create_generate_plan, create_web_search,
    create_adapt_plan, create_create_report, create_report_completion,
    create_next_step, create_initial_plan_step, create_search_step, create_report_step
)

# Use helper functions instead of manual model creation
plan = create_generate_plan(research_goal="My research goal")
search = create_web_search(query="my search query")
report = create_create_report(title="My Report", content="Report content")
```

## 🧪 VALIDATION MODULE

Use the `validate_schemas.py` module to test all schemas:

```python
from validate_schemas import test_all_schemas

# Test all schemas
result = test_all_schemas()
if result:
    print("✅ All schemas valid")
```

## 🚨 MANDATORY USAGE RULES

1. **ALWAYS** use `schema_utils.py` helper functions for creating models
2. **NEVER** create Pydantic models manually in tests or logic gates
3. **ALWAYS** validate schemas with `test_all_schemas()` after changes
4. **REFERENCE** this document when adding new fields or models

## 🔧 TROUBLESHOOTING PYDANTIC ERRORS

If you encounter Pydantic errors:

1. **Run validation first**: `python validate_schemas.py`
2. **Use helper functions**: Import from `schema_utils.py`
3. **Check field requirements**: Reference the model definitions above
4. **Verify list lengths**: Ensure MinLen/MaxLen constraints are met
5. **Check literal values**: Use exact strings for Literal fields

This comprehensive schema system should eliminate ALL future Pydantic validation errors.

## 🏗️ SGR STREAMING ARCHITECTURE (Current Implementation)

### Core Components (as of line 2409)

#### Main Research Function: `execute_research_task()`
Located at line 2409 in `sgr_streaming.py`, this is the main entry point for SGR research execution.

**Key Features:**
- Schema-guided reasoning with streaming support
- Real-time progress monitoring and visualization
- Logic gate enforcement for workflow progression
- State machine control to prevent loops

#### Workflow Logic Gates (Lines 2450-2530)
The system implements strict logic gates to prevent workflow loops:

```python
# STATE: PLAN_EXISTS_NO_SEARCHES
if searches_count == 0 and plan_exists:
    # FORCE: web_search ONLY
    # BLOCK: generate_plan, create_report, task_completed

# STATE: PLAN_EXISTS_ONE_SEARCH  
if searches_count == 1:
    # FORCE: web_search (minimum 2 searches required)
    # BLOCK: generate_plan, create_report, task_completed

# STATE: PLAN_EXISTS_SUFFICIENT_SEARCHES
if searches_count >= 2:
    # PREFER: create_report
    # ALLOW: web_search (if more data needed)
    # BLOCK: generate_plan, task_completed without report
```

#### Dispatch Method (Line 2204)
Handles execution of SGR commands with proper context management:
- `Clarification`: Sets clarification_used flag
- `GeneratePlan`: Stores plan in context
- `WebSearch`: Executes searches and manages citations
- `CreateReport`: Generates final reports
- `AdaptPlan`: Updates existing plans

### Integration Points

#### Schema Layer Integration
- **Models**: Defined in main `sgr_streaming.py` (single source of truth)
- **Utilities**: Helper functions in `schema_utils.py`
- **Validation**: Test functions in `validate_schemas.py`
- **Startup**: Schema validation runs at application start (line 2948+)

#### Key Methods and Line Numbers
- `execute_research_task()`: Line 2409 - Main research execution
- `dispatch()`: Line 2204 - Command execution
- `main()`: Line 2948+ - Application entry point with schema validation
- Logic gates: Lines 2450-2530 - Workflow state management

### Workflow Prevention Mechanisms
1. **Plan Loop Prevention**: Logic gates prevent multiple `generate_plan` calls
2. **Search Requirements**: Minimum 2 searches enforced before reporting
3. **State Machine**: Clear state transitions with blocked/allowed actions
4. **Context Tracking**: Persistent state in `self.context` dictionary

This architecture ensures robust, loop-free research execution with comprehensive schema validation.

## 🚨 TROUBLESHOOTING WORKFLOW LOOPS

### Common Issue: Repeated `generate_plan` Actions
**Symptoms:** System generates multiple `generate_plan` actions instead of progressing to `web_search`

**Root Cause:** Logic gates not properly enforcing workflow progression when plan already exists

**Solution:** Ensure logic gate enforcement is active in context messages (lines 2450-2530):
```python
# Check if plan exists in context
if self.context.get("plan"):
    # MUST enforce web_search, BLOCK generate_plan
    # Logic gates should prevent plan regeneration
```

**Debug Steps:**
1. Check `self.context["plan"]` is properly set in dispatch method (line 2204+)
2. Verify logic gate messages are being added to context (lines 2450-2530)
3. Ensure workflow state machine is enforcing transitions
4. Check that schema utilities are creating valid NextStep objects

### Workflow State Validation
Always verify these states are properly managed:
- `self.context["plan"]` - Contains active research plan
- `self.context["searches"]` - List of completed searches  
- `self.context["sources"]` - Citation sources collected
- `self.context["clarification_used"]` - Prevents clarification loops

This comprehensive system should eliminate workflow loops and ensure proper SGR progression.
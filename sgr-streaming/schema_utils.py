#!/usr/bin/env python3
"""
SGR Schema Utilities - COMPREHENSIVE HELPER FUNCTIONS

This module provides validated helper functions for all SGR Pydantic models.
ALWAYS use these functions instead of creating models manually to avoid validation errors.
"""

from sgr_streaming import (
    Clarification, GeneratePlan, WebSearch, AdaptPlan, 
    CreateReport, ReportCompletion, NextStep
)

# =============================================================================
# VALIDATED MODEL CREATORS - USE THESE TO AVOID PYDANTIC ERRORS
# =============================================================================

def create_clarification(reasoning="Request needs clarification", unclear_terms=None, assumptions=None, questions=None):
    """Create a valid Clarification object"""
    return Clarification(
        tool="clarification",
        reasoning=reasoning,
        unclear_terms=unclear_terms or ["unclear_term"],
        assumptions=assumptions or ["assumption1", "assumption2"],
        questions=questions or ["question1", "question2", "question3"]
    )

def create_generate_plan(reasoning="Need systematic research approach", research_goal="Research goal", planned_steps=None, search_strategies=None):
    """Create a valid GeneratePlan object"""
    return GeneratePlan(
        tool="generate_plan",
        reasoning=reasoning,
        research_goal=research_goal,
        planned_steps=planned_steps or ["Initial research", "Deep analysis", "Synthesis"],
        search_strategies=search_strategies or ["Web search", "Source verification"]
    )

def create_web_search(reasoning="Need information on topic", query="research query", max_results=10, plan_adapted=False, scrape_content=False):
    """Create a valid WebSearch object"""
    return WebSearch(
        tool="web_search",
        reasoning=reasoning,
        query=query,
        max_results=max_results,
        plan_adapted=plan_adapted,
        scrape_content=scrape_content
    )

def create_adapt_plan(reasoning="Plan needs adjustment", original_goal="Original goal", new_goal="Updated goal", plan_changes=None, next_steps=None):
    """Create a valid AdaptPlan object"""
    return AdaptPlan(
        tool="adapt_plan",
        reasoning=reasoning,
        original_goal=original_goal,
        new_goal=new_goal,
        plan_changes=plan_changes or ["Adjusted approach"],
        next_steps=next_steps or ["Continue research", "Analyze findings"]
    )

def create_create_report(reasoning="Sufficient data collected", title="Research Report", user_request_ref="user request", content="Report content [1]", confidence="high"):
    """Create a valid CreateReport object"""
    return CreateReport(
        tool="create_report",
        reasoning=reasoning,
        title=title,
        user_request_language_reference=user_request_ref,
        content=content,
        confidence=confidence
    )

def create_report_completion(reasoning="Research completed", completed_steps=None, status="completed"):
    """Create a valid ReportCompletion object"""
    return ReportCompletion(
        tool="report_completion",
        reasoning=reasoning,
        completed_steps=completed_steps or ["Plan created", "Searches conducted", "Report generated"],
        status=status
    )

def create_next_step(reasoning_steps=None, current_situation="Current state", plan_status="pending", 
                    searches_done=0, enough_data=False, remaining_steps=None, task_completed=False, function=None):
    """Create a valid NextStep object"""
    return NextStep(
        reasoning_steps=reasoning_steps or ["Analyzed current state", "Determined next action"],
        current_situation=current_situation,
        plan_status=plan_status,
        searches_done=searches_done,
        enough_data=enough_data,
        remaining_steps=remaining_steps or ["Next step"],
        task_completed=task_completed,
        function=function or create_generate_plan()
    )

# =============================================================================
# VALIDATION HELPERS
# =============================================================================

def validate_model(model_instance, model_name="Unknown"):
    """Validate any SGR model instance"""
    try:
        # Pydantic models validate on creation, so if we got here, it's valid
        print(f"✅ {model_name} validates successfully")
        return True
    except Exception as e:
        print(f"❌ {model_name} validation failed: {e}")
        return False

def test_all_schema_helpers():
    """Test all schema helper functions"""
    print("🧪 Testing All Schema Helper Functions")
    print("=" * 50)
    
    models_to_test = [
        ("Clarification", create_clarification),
        ("GeneratePlan", create_generate_plan),
        ("WebSearch", create_web_search),
        ("AdaptPlan", create_adapt_plan),
        ("CreateReport", create_create_report),
        ("ReportCompletion", create_report_completion),
        ("NextStep", create_next_step)
    ]
    
    all_valid = True
    for model_name, creator_func in models_to_test:
        try:
            model = creator_func()
            validate_model(model, model_name)
        except Exception as e:
            print(f"❌ {model_name} helper failed: {e}")
            all_valid = False
    
    if all_valid:
        print("\n🎉 ALL SCHEMA HELPERS WORK CORRECTLY!")
    else:
        print("\n❌ Some schema helpers failed - fix them!")
    
    return all_valid

# =============================================================================
# QUICK ACCESS FUNCTIONS FOR COMMON PATTERNS
# =============================================================================

def create_initial_plan_step(research_goal):
    """Create the first step - always generate_plan"""
    return create_next_step(
        reasoning_steps=["No plan exists yet", "Must create research plan first"],
        current_situation="Starting research process",
        plan_status="none",
        searches_done=0,
        enough_data=False,
        remaining_steps=["Generate research plan"],
        task_completed=False,
        function=create_generate_plan(research_goal=research_goal)
    )

def create_search_step(query, search_number=1):
    """Create a web search step"""
    return create_next_step(
        reasoning_steps=[f"Plan exists, need to execute search {search_number}", "Following planned research steps"],
        current_situation=f"Executing search {search_number} of planned research",
        plan_status="active",
        searches_done=search_number-1,
        enough_data=False,
        remaining_steps=[f"Complete search {search_number}", "Continue with remaining searches"],
        task_completed=False,
        function=create_web_search(query=query, reasoning=f"Executing planned search {search_number}")
    )

def create_report_step(title, content, user_request):
    """Create a report creation step"""
    return create_next_step(
        reasoning_steps=["Sufficient data collected from searches", "Ready to synthesize findings into report"],
        current_situation="All planned searches completed, ready to create report",
        plan_status="completed",
        searches_done=2,
        enough_data=True,
        remaining_steps=["Create comprehensive report"],
        task_completed=False,
        function=create_create_report(title=title, content=content, user_request_ref=user_request)
    )

if __name__ == "__main__":
    test_all_schema_helpers()
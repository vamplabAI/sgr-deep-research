#!/usr/bin/env python3
"""
Validate all SGR schemas to ensure they work correctly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sgr_streaming import (
    Clarification, GeneratePlan, WebSearch, AdaptPlan, 
    CreateReport, ReportCompletion, NextStep
)

def test_all_schemas():
    """Test all SGR schemas using the helper functions from schema.md"""
    
    print("🧪 Testing All SGR Schemas")
    print("=" * 50)
    
    try:
        # 1. Test Clarification
        print("Testing Clarification...")
        clarification = Clarification(
            tool="clarification",
            reasoning="Request needs clarification",
            unclear_terms=["term1"],
            assumptions=["assumption1", "assumption2"],
            questions=["question1", "question2", "question3"]
        )
        print(f"✅ Clarification: {clarification.tool}")
        
        # 2. Test GeneratePlan
        print("Testing GeneratePlan...")
        plan = GeneratePlan(
            tool="generate_plan",
            reasoning="Need systematic research approach",
            research_goal="Research topic thoroughly",
            planned_steps=["Initial research", "Deep analysis", "Synthesis"],
            search_strategies=["Web search", "Source verification"]
        )
        print(f"✅ GeneratePlan: {plan.tool}")
        
        # 3. Test WebSearch
        print("Testing WebSearch...")
        search = WebSearch(
            tool="web_search",
            reasoning="Need information on topic",
            query="research query"
        )
        print(f"✅ WebSearch: {search.tool}")
        
        # 4. Test AdaptPlan
        print("Testing AdaptPlan...")
        adapt = AdaptPlan(
            tool="adapt_plan",
            reasoning="Plan needs adjustment based on findings",
            original_goal="Original research goal",
            new_goal="Updated research goal",
            plan_changes=["Adjusted approach"],
            next_steps=["Continue research", "Analyze findings"]
        )
        print(f"✅ AdaptPlan: {adapt.tool}")
        
        # 5. Test CreateReport
        print("Testing CreateReport...")
        report = CreateReport(
            tool="create_report",
            reasoning="Sufficient data collected for comprehensive report",
            title="Research Report Title",
            user_request_language_reference="original user request text",
            content="Detailed report content with proper citations [1]",
            confidence="high"
        )
        print(f"✅ CreateReport: {report.tool}")
        
        # 6. Test ReportCompletion
        print("Testing ReportCompletion...")
        completion = ReportCompletion(
            tool="report_completion",
            reasoning="All research objectives completed successfully",
            completed_steps=["Plan created", "Searches conducted", "Report generated"],
            status="completed"
        )
        print(f"✅ ReportCompletion: {completion.tool}")
        
        # 7. Test NextStep
        print("Testing NextStep...")
        next_step = NextStep(
            reasoning_steps=["Analyzed current state", "Determined next action"],
            current_situation="Ready to begin research",
            plan_status="pending",
            searches_done=0,
            enough_data=False,
            remaining_steps=["Create research plan"],
            task_completed=False,
            function=plan  # Use the valid plan we created above
        )
        print(f"✅ NextStep: {next_step.function.tool}")
        
        print("\n🎉 ALL SCHEMAS VALIDATE SUCCESSFULLY!")
        print("✅ Schema layer is working correctly")
        return True
        
    except Exception as e:
        print(f"\n❌ SCHEMA VALIDATION FAILED: {e}")
        print("🚨 Fix the schema definitions before proceeding")
        return False

if __name__ == "__main__":
    test_all_schemas()
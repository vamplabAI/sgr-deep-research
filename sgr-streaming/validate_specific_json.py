#!/usr/bin/env python3
"""
Validate Specific JSON Case
Test the exact JSON structure that was failing using the validator
"""

import json

def test_specific_json():
    """Test the exact JSON that was failing"""
    
    # The exact JSON from the debug log
    test_json = {
        "reasoning_steps": ["Generate plan for jazz history within first thirty years"],
        "current_situation": "",
        "plan_status": "active", 
        "searches_done": 0,
        "enough_data": False,
        "remaining_steps": [
            {"action_type": "web_search", "search_query": "early_jazz_history_1920s"},
            {"action_type": "web_search", "search_query": "jazz_evolution_first_thirty_years"}
        ],
        "task_completed": False,
        "function": {"tool": "generate_plan"}
    }
    
    print("=== Testing Specific JSON Case ===")
    print(f"Input JSON:")
    print(json.dumps(test_json, indent=2))
    print()
    
    # Identify the issues
    print("=== Issues Identified ===")
    
    # Issue 1: reasoning_steps has only 1 item (needs min 2)
    reasoning_count = len(test_json.get('reasoning_steps', []))
    print(f"1. reasoning_steps: {reasoning_count} items (needs min 2)")
    
    # Issue 2: current_situation is empty
    current_situation = test_json.get('current_situation', '')
    print(f"2. current_situation: '{current_situation}' (should not be empty)")
    
    # Issue 3: remaining_steps contains complex objects instead of strings
    remaining_steps = test_json.get('remaining_steps', [])
    print(f"3. remaining_steps: contains {type(remaining_steps[0]).__name__} objects (needs strings)")
    
    # Issue 4: function object is incomplete
    function_obj = test_json.get('function', {})
    print(f"4. function: only has 'tool' field, missing required fields for generate_plan")
    
    print()
    print("=== Required Fields for generate_plan ===")
    print("- tool: 'generate_plan'")
    print("- reasoning: string")
    print("- research_goal: string") 
    print("- planned_steps: List[str] (min 3 items)")
    print("- search_strategies: List[str] (min 2 items)")
    
    print()
    print("=== Corrected JSON ===")
    
    # Create corrected version
    corrected_json = {
        "reasoning_steps": [
            "Generate plan for jazz history within first thirty years",
            "Create comprehensive research strategy for early jazz period"
        ],
        "current_situation": "Generated research plan for jazz history in its first thirty years",
        "plan_status": "active",
        "searches_done": 0,
        "enough_data": False,
        "remaining_steps": [
            "Web Search: early_jazz_history_1920s",
            "Web Search: jazz_evolution_first_thirty_years"
        ],
        "task_completed": False,
        "function": {
            "tool": "generate_plan",
            "reasoning": "Generated comprehensive research plan for jazz history",
            "research_goal": "Research the history and development of jazz music in its first thirty years (1890s-1920s)",
            "planned_steps": [
                "Research early jazz origins and key figures",
                "Investigate jazz development in the 1920s", 
                "Analyze jazz evolution and major milestones"
            ],
            "search_strategies": [
                "Search for early jazz history and origins",
                "Research jazz development in the first three decades"
            ]
        }
    }
    
    print(json.dumps(corrected_json, indent=2))
    
    print()
    print("=== Summary ===")
    print("The coercion method should:")
    print("1. Ensure reasoning_steps has minimum 2 items")
    print("2. Fill empty current_situation with appropriate description")
    print("3. Convert complex remaining_steps objects to simple strings")
    print("4. Complete the function object with all required fields")

if __name__ == "__main__":
    test_specific_json()
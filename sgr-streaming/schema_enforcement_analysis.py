#!/usr/bin/env python3
"""
Schema Enforcement Analysis
Proactive identification of all potential schema validation issues in SGR
"""

from typing import Dict, List, Any
import json

def analyze_schema_enforcement_issues():
    """Identify all potential schema enforcement issues"""
    
    print("=== SGR SCHEMA ENFORCEMENT ANALYSIS ===")
    print("Identifying all potential validation failures...")
    print()
    
    # Define all schema requirements
    schema_requirements = {
        "NextStep": {
            "reasoning_steps": {"type": "List[str]", "min_len": 2, "max_len": 4},
            "current_situation": {"type": "str", "required": True, "non_empty": True},
            "plan_status": {"type": "str", "required": True},
            "searches_done": {"type": "int", "default": 0},
            "enough_data": {"type": "bool", "default": False},
            "remaining_steps": {"type": "List[str]", "min_len": 1, "max_len": 3},
            "task_completed": {"type": "bool", "required": True},
            "function": {"type": "Union[Clarification|GeneratePlan|WebSearch|AdaptPlan|CreateReport|ReportCompletion]", "required": True}
        },
        "Clarification": {
            "tool": {"type": "Literal['clarification']", "required": True},
            "reasoning": {"type": "str", "required": True, "non_empty": True},
            "unclear_terms": {"type": "List[str]", "min_len": 1, "max_len": 5},
            "assumptions": {"type": "List[str]", "min_len": 2, "max_len": 4},
            "questions": {"type": "List[str]", "min_len": 3, "max_len": 5}
        },
        "GeneratePlan": {
            "tool": {"type": "Literal['generate_plan']", "required": True},
            "reasoning": {"type": "str", "required": True, "non_empty": True},
            "research_goal": {"type": "str", "required": True, "non_empty": True},
            "planned_steps": {"type": "List[str]", "min_len": 3, "max_len": 4},
            "search_strategies": {"type": "List[str]", "min_len": 2, "max_len": 3}
        },
        "WebSearch": {
            "tool": {"type": "Literal['web_search']", "required": True},
            "reasoning": {"type": "str", "required": True, "non_empty": True},
            "query": {"type": "str", "required": True, "non_empty": True},
            "max_results": {"type": "int", "default": 10, "range": [1, 15]},
            "plan_adapted": {"type": "bool", "default": False},
            "scrape_content": {"type": "bool", "default": False}
        },
        "AdaptPlan": {
            "tool": {"type": "Literal['adapt_plan']", "required": True},
            "reasoning": {"type": "str", "required": True, "non_empty": True},
            "original_goal": {"type": "str", "required": True, "non_empty": True},
            "new_goal": {"type": "str", "required": True, "non_empty": True},
            "plan_changes": {"type": "List[str]", "min_len": 1, "max_len": 3},
            "next_steps": {"type": "List[str]", "min_len": 2, "max_len": 4}
        },
        "CreateReport": {
            "tool": {"type": "Literal['create_report']", "required": True},
            "reasoning": {"type": "str", "required": True, "non_empty": True},
            "title": {"type": "str", "required": True, "non_empty": True},
            "user_request_language_reference": {"type": "str", "required": True, "non_empty": True},
            "content": {"type": "str", "required": True, "min_length": 800},
            "confidence": {"type": "Literal['high'|'medium'|'low']", "required": True}
        },
        "ReportCompletion": {
            "tool": {"type": "Literal['report_completion']", "required": True},
            "reasoning": {"type": "str", "required": True, "non_empty": True},
            "completed_steps": {"type": "List[str]", "min_len": 1, "max_len": 5},
            "status": {"type": "Literal['completed'|'failed']", "required": True}
        }
    }
    
    # Common failure patterns
    failure_patterns = [
        {
            "name": "Empty Lists",
            "description": "Lists that should have minimum items but are empty",
            "examples": [
                "reasoning_steps: []",
                "questions: []", 
                "planned_steps: []",
                "search_strategies: []"
            ],
            "impact": "Critical - breaks minimum length validation"
        },
        {
            "name": "Single Item Lists", 
            "description": "Lists with only 1 item when minimum 2+ required",
            "examples": [
                "reasoning_steps: ['single step']",
                "assumptions: ['one assumption']",
                "search_strategies: ['one strategy']"
            ],
            "impact": "Critical - fails MinLen validation"
        },
        {
            "name": "Empty Strings",
            "description": "Required string fields that are empty",
            "examples": [
                "current_situation: ''",
                "reasoning: ''",
                "research_goal: ''",
                "query: ''"
            ],
            "impact": "High - breaks business logic even if schema passes"
        },
        {
            "name": "Wrong Tool Names",
            "description": "Incorrect literal values for tool field",
            "examples": [
                "tool: 'clarify' (should be 'clarification')",
                "tool: 'plan' (should be 'generate_plan')",
                "tool: 'search' (should be 'web_search')"
            ],
            "impact": "Critical - fails Literal validation"
        },
        {
            "name": "Missing Required Fields",
            "description": "Function objects missing required fields",
            "examples": [
                "function: {'tool': 'generate_plan'} (missing reasoning, research_goal, etc.)",
                "function: {'tool': 'clarification'} (missing questions, assumptions, etc.)"
            ],
            "impact": "Critical - fails Pydantic validation"
        },
        {
            "name": "Wrong Data Types",
            "description": "Fields with incorrect data types",
            "examples": [
                "remaining_steps: [{'action': 'search'}] (should be strings)",
                "searches_done: '2' (should be int)",
                "task_completed: 'false' (should be bool)"
            ],
            "impact": "Critical - fails type validation"
        },
        {
            "name": "Content Too Short",
            "description": "Report content below minimum length",
            "examples": [
                "content: 'Short report' (should be 800+ words)"
            ],
            "impact": "High - fails business requirements"
        }
    ]
    
    print("=== CRITICAL FAILURE PATTERNS ===")
    for i, pattern in enumerate(failure_patterns, 1):
        print(f"{i}. {pattern['name']}")
        print(f"   Description: {pattern['description']}")
        print(f"   Impact: {pattern['impact']}")
        print(f"   Examples:")
        for example in pattern['examples']:
            print(f"     • {example}")
        print()
    
    print("=== SCHEMA REQUIREMENTS SUMMARY ===")
    for schema_name, fields in schema_requirements.items():
        print(f"\n{schema_name}:")
        for field_name, requirements in fields.items():
            req_str = f"  {field_name}: {requirements['type']}"
            if requirements.get('min_len'):
                req_str += f" (min {requirements['min_len']} items)"
            if requirements.get('max_len'):
                req_str += f" (max {requirements['max_len']} items)"
            if requirements.get('required'):
                req_str += " [REQUIRED]"
            if requirements.get('non_empty'):
                req_str += " [NON-EMPTY]"
            print(req_str)
    
    print("\n=== PROACTIVE FIXES NEEDED ===")
    fixes_needed = [
        "1. Enhanced validation in coercion method for ALL function types",
        "2. Smart defaults for empty required fields",
        "3. Automatic list padding to meet minimum lengths", 
        "4. Content length validation and expansion",
        "5. Type conversion (string numbers to int/bool)",
        "6. Tool name normalization and correction",
        "7. Complex object flattening (remaining_steps)",
        "8. Empty string detection and replacement"
    ]
    
    for fix in fixes_needed:
        print(fix)
    
    print("\n=== BUSINESS LOGIC ISSUES ===")
    business_issues = [
        "• Generated plan with no steps (planned_steps: [])",
        "• Search with empty query (query: '')",
        "• Report with no content (content: '')",
        "• Clarification with no questions (questions: [])",
        "• Completion with no completed steps (completed_steps: [])"
    ]
    
    for issue in business_issues:
        print(issue)

if __name__ == "__main__":
    analyze_schema_enforcement_issues()
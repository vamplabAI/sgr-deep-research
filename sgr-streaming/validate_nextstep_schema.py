#!/usr/bin/env python3
"""
NextStep Schema Validator
Test and validate NextStep JSON objects against the Pydantic schema
"""

import json
import sys
from typing import Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

# Import the NextStep model
try:
    from sgr_streaming import NextStep
except ImportError:
    print("❌ Could not import NextStep. Run from sgr-streaming directory.")
    sys.exit(1)

def validate_nextstep_json(json_data: Dict[str, Any], console: Console) -> bool:
    """Validate a JSON object against NextStep schema"""
    try:
        # Try to create NextStep object
        nextstep = NextStep(**json_data)
        console.print("✅ [green]Valid NextStep schema![/green]")
        
        # Show some key info
        function_tool = nextstep.function.tool if hasattr(nextstep.function, 'tool') else 'unknown'
        console.print(f"Function tool: {function_tool}")
        console.print(f"Task completed: {nextstep.task_completed}")
        console.print(f"Reasoning steps: {len(nextstep.reasoning_steps)}")
        
        return True
        
    except Exception as e:
        console.print("❌ [red]Invalid NextStep schema[/red]")
        console.print(f"[red]Error: {e}[/red]")
        return False

def show_schema_requirements(console: Console):
    """Show the schema requirements"""
    console.print(Panel.fit(
        """[bold cyan]NextStep Schema Requirements[/bold cyan]

[bold]Required Fields:[/bold]
• reasoning_steps: List[str] (min 2, max 4 items)
• current_situation: str
• plan_status: "active" | "paused" | "completed"
• searches_done: int (0 or higher)
• enough_data: bool
• remaining_steps: List[str] (min 1, max 3 items)
• task_completed: bool
• function: One of the function types below

[bold]Function Types:[/bold]
• Clarification: questions (min 3), unclear_terms (min 1), assumptions (min 2)
• GeneratePlan: planned_steps (min 3), search_strategies (min 2)
• WebSearch: query, max_results, scrape_content
• AdaptPlan: plan_changes (min 1), next_steps (min 2)
• CreateReport: title, content, confidence
• ReportCompletion: completed_steps (min 1), status""",
        title="📋 Schema Guide"
    ))

def test_examples(console: Console):
    """Test some example JSON objects"""
    
    # Valid clarification example
    console.print("\n[bold cyan]🧪 Testing Valid Clarification Example[/bold cyan]")
    
    valid_clarification = {
        "reasoning_steps": [
            "User request is ambiguous and lacks specific details",
            "Need clarification to provide accurate research"
        ],
        "current_situation": "Awaiting user clarification to proceed with research.",
        "plan_status": "paused",
        "searches_done": 0,
        "enough_data": False,
        "remaining_steps": ["Receive clarification", "Generate research plan"],
        "task_completed": False,
        "function": {
            "tool": "clarification",
            "reasoning": "Need user to clarify request to provide accurate research.",
            "questions": [
                "Could you please provide more specific details about your request?",
                "What particular aspect are you most interested in?",
                "Are there any specific requirements or constraints I should know about?"
            ],
            "unclear_terms": ["The request topic or scope"],
            "assumptions": [
                "You want a general overview of the topic",
                "You need current and accurate information"
            ]
        }
    }
    
    syntax = Syntax(json.dumps(valid_clarification, indent=2), "json", theme="monokai")
    console.print(syntax)
    validate_nextstep_json(valid_clarification, console)
    
    # Invalid example (too few items)
    console.print("\n[bold cyan]🧪 Testing Invalid Example (Too Few Items)[/bold cyan]")
    
    invalid_example = {
        "reasoning_steps": ["Only one step"],  # Need minimum 2
        "current_situation": "Test",
        "plan_status": "paused",
        "searches_done": 0,
        "enough_data": False,
        "remaining_steps": ["Next step"],
        "task_completed": False,
        "function": {
            "tool": "clarification",
            "reasoning": "Test",
            "questions": ["Only one question"],  # Need minimum 3
            "unclear_terms": [],  # Need minimum 1
            "assumptions": []  # Need minimum 2
        }
    }
    
    syntax = Syntax(json.dumps(invalid_example, indent=2), "json", theme="monokai")
    console.print(syntax)
    validate_nextstep_json(invalid_example, console)

def validate_from_file(filepath: str, console: Console):
    """Validate JSON from a file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        console.print(f"\n[bold cyan]📄 Validating {filepath}[/bold cyan]")
        return validate_nextstep_json(data, console)
        
    except FileNotFoundError:
        console.print(f"❌ File not found: {filepath}")
        return False
    except json.JSONDecodeError as e:
        console.print(f"❌ Invalid JSON in {filepath}: {e}")
        return False

def main():
    console = Console()
    
    console.print(Panel.fit(
        "[bold cyan]NextStep Schema Validator[/bold cyan]\n"
        "Validate JSON objects against the SGR NextStep schema",
        title="🔍 Validator"
    ))
    
    if len(sys.argv) > 1:
        # Validate file provided as argument
        filepath = sys.argv[1]
        validate_from_file(filepath, console)
    else:
        # Show requirements and test examples
        show_schema_requirements(console)
        test_examples(console)
        
        console.print(f"\n[bold]Usage:[/bold]")
        console.print(f"  python validate_nextstep_schema.py [json_file]")
        console.print(f"  python validate_nextstep_schema.py logs/20241212_120000_test_nextstep_simple_parse_raw.txt")

if __name__ == "__main__":
    main()
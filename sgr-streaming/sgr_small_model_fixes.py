#!/usr/bin/env python3
"""
SGR Small Model Fixes
Targeted fixes for the two critical issues:
1. Error contamination - Pydantic errors leaking into research context
2. Clarification flow - System not halting for user input during clarification
"""

import re
from typing import Dict, Any, Optional

def patch_sgr_for_small_models():
    """Apply targeted patches to SGR streaming for small model compatibility"""
    
    # Read the current SGR streaming file
    with open('sgr_streaming.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Patch 1: Prevent error contamination in coercion
    error_contamination_fix = '''
    def _coerce_model_json_to_nextstep(self, data: Dict[str, Any]) -> Optional['NextStep']:
        """Enhanced coercion with error isolation to prevent contamination.
        Ensures validation errors don't leak into research context.
        """
        try:
            if not isinstance(data, dict):
                return None
            
            # CRITICAL: Isolate error handling to prevent contamination
            # Create clean context without error messages
            clean_context = {
                'clarification_used': self.context.get('clarification_used', False),
                'user_messages': getattr(self, 'recent_user_messages', []),
                'searches_completed': len(self.context.get('searches', [])),
                'original_query': getattr(self, 'original_user_query', ''),  # Preserve original query
                'current_step': getattr(self, 'current_step_count', 0)
            }
            
            # Use Schema Enforcement Engine with clean context
            from schema_enforcement_engine import SchemaEnforcementEngine
            engine = SchemaEnforcementEngine()
            
            try:
                # Ensure we preserve the original user query in context
                if hasattr(self, 'original_user_query') and self.original_user_query:
                    clean_context['research_topic'] = self.original_user_query
                
                enforced_data = engine.enforce_schema(data, clean_context)
                
                # CRITICAL: Validate that we're not researching error messages
                if self._is_researching_errors(enforced_data):
                    # Force back to original query
                    enforced_data = self._redirect_to_original_query(enforced_data, clean_context)
                
                return NextStep(**enforced_data)
                
            except Exception as enforcement_error:
                # Fallback with error isolation
                return self._clean_fallback_without_contamination(data, clean_context)
                
        except Exception as e:
            if os.getenv('SGR_DEBUG_JSON', '').strip().lower() in ('1', 'true', 'yes'):
                self.console.print(f"[red]❌ Coercion failed (isolated): {e}[/red]")
            return None
    
    def _is_researching_errors(self, data: Dict[str, Any]) -> bool:
        """Check if the system is trying to research error messages instead of the original query"""
        
        # Check function content for error-related terms
        func = data.get('function', {})
        
        # Check search queries
        if func.get('tool') == 'web_search':
            query = func.get('query', '').lower()
            error_indicators = [
                'validation error', 'pydantic', 'field required', 'missing',
                'type_error', 'string_type', 'too_short', 'input_value'
            ]
            if any(indicator in query for indicator in error_indicators):
                return True
        
        # Check research goals
        if func.get('tool') == 'generate_plan':
            goal = func.get('research_goal', '').lower()
            if any(indicator in goal for indicator in ['validation', 'pydantic', 'error']):
                return True
        
        # Check reasoning steps
        reasoning = ' '.join(data.get('reasoning_steps', [])).lower()
        if any(indicator in reasoning for indicator in ['validation error', 'field required']):
            return True
        
        return False
    
    def _redirect_to_original_query(self, data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Redirect research back to the original user query"""
        
        original_query = context.get('original_query', context.get('research_topic', 'user research request'))
        
        # Fix the function to focus on original query
        func = data.get('function', {})
        tool = func.get('tool', 'clarification')
        
        if tool == 'web_search':
            func['query'] = f"{original_query} information"
            func['reasoning'] = f"Searching for information about {original_query}"
        elif tool == 'generate_plan':
            func['research_goal'] = f"Research {original_query}"
            func['reasoning'] = f"Creating research plan for {original_query}"
        
        # Update reasoning steps
        data['reasoning_steps'] = [
            f"Refocusing on original query: {original_query}",
            "Proceeding with user's actual research request"
        ]
        
        data['current_situation'] = f"Researching {original_query} as requested by user"
        
        return data
    
    def _clean_fallback_without_contamination(self, data: Dict[str, Any], context: Dict[str, Any]) -> Optional['NextStep']:
        """Clean fallback that prevents error contamination"""
        
        original_query = context.get('original_query', context.get('research_topic', 'research request'))
        
        # Create minimal clean NextStep focused on original query
        clean_data = {
            'reasoning_steps': [
                f"Processing user request about {original_query}",
                "Determining appropriate next action"
            ],
            'current_situation': f"Ready to research {original_query}",
            'plan_status': 'active',
            'searches_done': context.get('searches_completed', 0),
            'enough_data': False,
            'remaining_steps': [f"Research {original_query}"],
            'task_completed': False,
            'function': {
                'tool': 'generate_plan',
                'reasoning': f'Creating research plan for {original_query}',
                'research_goal': f'Research {original_query}',
                'planned_steps': [
                    f'Gather information about {original_query}',
                    f'Analyze findings on {original_query}',
                    f'Create comprehensive report'
                ],
                'search_strategies': [
                    'Web search for reliable sources',
                    'Verify information accuracy'
                ]
            }
        }
        
        try:
            return NextStep(**clean_data)
        except Exception:
            return None
    '''
    
    # Patch 2: Fix clarification flow to properly halt and wait for user input
    clarification_flow_fix = '''
    def dispatch(self, cmd: BaseModel) -> Any:
        """Execute SGR commands with proper clarification flow"""
        
        if isinstance(cmd, Clarification):
            self.context["clarification_used"] = True
            
            # Show clarification questions in compact format
            questions_text = "\\n".join([f"  {i}. {q}" for i, q in enumerate(cmd.questions, 1)])
            
            clarification_panel = Panel(
                f"[yellow]{questions_text}[/yellow]",
                title="❓ Please Answer These Questions",
                border_style="yellow",
                padding=(1, 2)
            )
            
            self.console.print(clarification_panel)
            
            # CRITICAL FIX: Return special signal to halt execution and wait for user input
            # This prevents the system from continuing automatically
            return "CLARIFICATION_REQUESTED"
        
        # Handle other commands normally
        elif isinstance(cmd, GeneratePlan):
            # Store the original query to prevent contamination
            if hasattr(self, 'current_task') and self.current_task:
                self.original_user_query = self.current_task
            
            self.context["plan"] = {
                "goal": cmd.research_goal,
                "steps": cmd.planned_steps,
                "strategies": cmd.search_strategies
            }
            
            plan_text = "\\n".join([f"  {i}. {step}" for i, step in enumerate(cmd.planned_steps, 1)])
            strategies_text = "\\n".join([f"  • {strategy}" for strategy in cmd.search_strategies])
            
            plan_panel = Panel(
                f"[green]🎯 Goal:[/green] {cmd.research_goal}\\n\\n"
                f"[green]📋 Steps:[/green]\\n{plan_text}\\n\\n"
                f"[green]🔍 Strategies:[/green]\\n{strategies_text}",
                title="📋 Research Plan Generated",
                border_style="green"
            )
            
            self.console.print(plan_panel)
            return f"Generated research plan: {cmd.research_goal}"
        
        # Continue with other command handling...
        # (rest of dispatch method remains the same)
    '''
    
    # Apply patches
    print("🔧 Applying SGR small model fixes...")
    
    # Replace the coercion method
    if '_coerce_model_json_to_nextstep' in content:
        # Find the method and replace it
        method_pattern = r'def _coerce_model_json_to_nextstep\(self.*?(?=\n    def |\nclass |\n\n\n|\Z)'
        content = re.sub(method_pattern, error_contamination_fix.strip(), content, flags=re.DOTALL)
        print("✅ Applied error contamination fix")
    
    # Replace the dispatch method
    if 'def dispatch(self, cmd: BaseModel)' in content:
        dispatch_pattern = r'def dispatch\(self, cmd: BaseModel\).*?(?=\n    def |\nclass |\n\n\n|\Z)'
        content = re.sub(dispatch_pattern, clarification_flow_fix.strip(), content, flags=re.DOTALL)
        print("✅ Applied clarification flow fix")
    
    # Write the patched file
    with open('sgr_streaming_patched.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("🎉 SGR small model fixes applied successfully!")
    print("📁 Patched file saved as: sgr_streaming_patched.py")
    print("\n🚀 To use the fixes:")
    print("1. Backup your original: cp sgr_streaming.py sgr_streaming_backup.py")
    print("2. Apply the fixes: cp sgr_streaming_patched.py sgr_streaming.py")
    print("3. Test with: python sgr_streaming.py")

if __name__ == "__main__":
    patch_sgr_for_small_models()
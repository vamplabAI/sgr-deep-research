#!/usr/bin/env python3
"""
SGR Small Model Adapter
Enhances the existing SGR system to work better with smaller models by:
1. Simplifying state management
2. Reducing schema complexity
3. Adding better error recovery
4. Implementing progressive disclosure of complexity
"""

import yaml
import json
import re
from typing import Dict, Any, Optional, Tuple
from openai import OpenAI
from pydantic import BaseModel, Field
from typing_extensions import Literal

class SimplifiedNextStep(BaseModel):
    """Simplified NextStep schema for small models"""
    
    # Core reasoning (simplified)
    reasoning: str = Field(description="Single reasoning statement about what to do next")
    
    # Current state (simplified)
    situation: str = Field(description="Brief description of current research state")
    
    # Progress (simplified)
    searches_done: int = Field(default=0, description="Number of searches completed")
    has_enough_data: bool = Field(default=False, description="Ready to create report?")
    
    # Next action (simplified)
    next_action: str = Field(description="What to do next: clarify|plan|search|report|complete")
    
    # Action details (conditional based on next_action)
    action_details: Dict[str, Any] = Field(default_factory=dict, description="Details for the chosen action")

class SGRSmallModelAdapter:
    """Adapter that makes SGR work better with small models"""
    
    def __init__(self, config_path: str = "sgr-streaming/config.yaml"):
        self.config = self._load_config(config_path)
        self.client = self._init_client()
        self.state = {
            "searches_done": 0,
            "sources": [],
            "facts": [],
            "current_goal": "",
            "has_plan": False
        }
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load SGR configuration"""
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    
    def _init_client(self) -> OpenAI:
        """Initialize OpenAI client with SGR config"""
        openai_config = self.config.get('openai', {})
        return OpenAI(
            api_key=openai_config.get('api_key', 'dev-key'),
            base_url=openai_config.get('base_url', 'http://localhost:8000/v1')
        )
    
    def _create_simplified_prompt(self, user_query: str, state: Dict[str, Any]) -> str:
        """Create a simplified prompt that's easier for small models"""
        
        base_prompt = f"""You are a research assistant. Your task: {user_query}

Current state:
- Searches done: {state['searches_done']}
- Has plan: {state['has_plan']}
- Facts collected: {len(state['facts'])}

Respond with valid JSON only:
{{
  "reasoning": "brief explanation of what to do next",
  "situation": "current research state",
  "searches_done": {state['searches_done']},
  "has_enough_data": false,
  "next_action": "clarify|plan|search|report|complete",
  "action_details": {{}}
}}

Actions:
- "clarify": Ask for clarification (only if query is unclear)
- "plan": Create research plan (if no plan exists)
- "search": Search for information (include "query" in action_details)
- "report": Create final report (if enough data collected)
- "complete": Task finished

Choose the most appropriate next action."""

        return base_prompt
    
    def _parse_response(self, raw_response: str) -> Optional[SimplifiedNextStep]:
        """Parse and validate model response with error recovery"""
        
        # Clean up common JSON issues
        cleaned = self._clean_json(raw_response)
        
        try:
            data = json.loads(cleaned)
            return SimplifiedNextStep(**data)
        except Exception as e:
            print(f"Parse error: {e}")
            print(f"Raw response: {raw_response[:200]}...")
            return None
    
    def _clean_json(self, raw: str) -> str:
        """Clean up common JSON formatting issues from small models"""
        
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            cleaned = json_match.group(0)
        else:
            cleaned = raw
        
        # Fix common issues
        cleaned = re.sub(r',\s*}', '}', cleaned)  # Remove trailing commas
        cleaned = re.sub(r',\s*]', ']', cleaned)  # Remove trailing commas in arrays
        cleaned = re.sub(r'([^"\\])\n', r'\1', cleaned)  # Remove unescaped newlines
        
        return cleaned
    
    def _execute_action(self, step: SimplifiedNextStep) -> str:
        """Execute the chosen action"""
        
        action = step.next_action
        details = step.action_details
        
        if action == "clarify":
            return self._handle_clarification(details)
        elif action == "plan":
            return self._handle_planning(details)
        elif action == "search":
            return self._handle_search(details)
        elif action == "report":
            return self._handle_report(details)
        elif action == "complete":
            return self._handle_completion(details)
        else:
            return f"Unknown action: {action}"
    
    def _handle_clarification(self, details: Dict[str, Any]) -> str:
        """Handle clarification requests"""
        questions = details.get('questions', ['Please provide more details about your research needs.'])
        return f"Clarification needed: {'; '.join(questions)}"
    
    def _handle_planning(self, details: Dict[str, Any]) -> str:
        """Handle research planning"""
        self.state['has_plan'] = True
        plan_steps = details.get('steps', ['Search for basic information', 'Gather detailed data', 'Create report'])
        return f"Research plan created: {'; '.join(plan_steps)}"
    
    def _handle_search(self, details: Dict[str, Any]) -> str:
        """Handle web search (simplified - just simulate for now)"""
        query = details.get('query', 'general search')
        self.state['searches_done'] += 1
        
        # Simulate search results (in real implementation, use Tavily API)
        simulated_facts = [
            f"Fact {self.state['searches_done']}.1: Information about {query}",
            f"Fact {self.state['searches_done']}.2: Additional details on {query}",
            f"Fact {self.state['searches_done']}.3: Context for {query}"
        ]
        
        self.state['facts'].extend(simulated_facts)
        return f"Search completed for '{query}'. Found {len(simulated_facts)} new facts."
    
    def _handle_report(self, details: Dict[str, Any]) -> str:
        """Handle report creation"""
        title = details.get('title', 'Research Report')
        
        # Create simple report from collected facts
        report = f"# {title}\n\n"
        report += "## Findings\n\n"
        
        for i, fact in enumerate(self.state['facts'], 1):
            report += f"{i}. {fact}\n"
        
        report += f"\n## Summary\n\nCompleted {self.state['searches_done']} searches and collected {len(self.state['facts'])} facts."
        
        return report
    
    def _handle_completion(self, details: Dict[str, Any]) -> str:
        """Handle task completion"""
        return f"Research completed. Total searches: {self.state['searches_done']}, Facts: {len(self.state['facts'])}"
    
    def research(self, user_query: str, max_steps: int = 5) -> str:
        """Main research method with simplified state management"""
        
        print(f"🔬 Starting simplified SGR research: {user_query}")
        self.state['current_goal'] = user_query
        
        for step_num in range(1, max_steps + 1):
            print(f"\n--- Step {step_num}/{max_steps} ---")
            
            # Create simplified prompt
            prompt = self._create_simplified_prompt(user_query, self.state)
            
            try:
                # Get model response
                response = self.client.chat.completions.create(
                    model=self.config['openai']['model'],
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=500,
                    temperature=0.2
                )
                
                raw_response = response.choices[0].message.content
                print(f"Raw response: {raw_response[:100]}...")
                
                # Parse response
                step = self._parse_response(raw_response)
                if not step:
                    print("❌ Failed to parse response, continuing...")
                    continue
                
                print(f"Action: {step.next_action}")
                print(f"Reasoning: {step.reasoning}")
                
                # Execute action
                result = self._execute_action(step)
                print(f"Result: {result}")
                
                # Check if we should stop
                if step.next_action == "complete" or step.has_enough_data:
                    print("✅ Research completed!")
                    break
                    
            except Exception as e:
                print(f"❌ Error in step {step_num}: {e}")
                continue
        
        # Return final summary
        return f"Research completed in {step_num} steps. Searches: {self.state['searches_done']}, Facts: {len(self.state['facts'])}"

def main():
    """Test the simplified SGR adapter"""
    adapter = SGRSmallModelAdapter()
    result = adapter.research("origins of Jazz music")
    print(f"\n🎯 Final Result: {result}")

if __name__ == "__main__":
    main()
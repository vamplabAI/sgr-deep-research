#!/usr/bin/env python3
"""
SGR Small Model Enhanced Version
Enhances the existing SGR streaming system to work better with smaller models by:
1. Improved schema coercion and error recovery
2. Simplified state management
3. Progressive complexity disclosure
4. Better JSON parsing with multiple fallback strategies
"""

import os
import yaml
import json
import re
from typing import Dict, Any, Optional, List, Union
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
import time

# Import existing SGR components
try:
    from sgr_streaming import NextStep, Clarification, GeneratePlan, WebSearch, CreateReport, ReportCompletion
except ImportError:
    # Fallback definitions if import fails
    from pydantic import BaseModel, Field
    from typing_extensions import Literal
    
    class Clarification(BaseModel):
        tool: Literal["clarification"]
        questions: List[str]
    
    class GeneratePlan(BaseModel):
        tool: Literal["generate_plan"]
        research_goal: str
        planned_steps: List[str]
    
    class WebSearch(BaseModel):
        tool: Literal["web_search"]
        query: str
        reasoning: str = ""
    
    class CreateReport(BaseModel):
        tool: Literal["create_report"]
        title: str
        content: str
        reasoning: str = ""
    
    class ReportCompletion(BaseModel):
        tool: Literal["report_completion"]
        reasoning: str
        status: Literal["completed", "failed"] = "completed"
    
    class NextStep(BaseModel):
        reasoning_steps: List[str] = Field(default_factory=lambda: ["Processing request"])
        current_situation: str = "Starting research"
        plan_status: str = "active"
        searches_done: int = 0
        enough_data: bool = False
        remaining_steps: List[str] = Field(default_factory=lambda: ["Continue research"])
        task_completed: bool = False
        function: Union[Clarification, GeneratePlan, WebSearch, CreateReport, ReportCompletion]

class SmallModelSGREnhancer:
    """Enhanced SGR system optimized for small models"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.console = Console()
        self.config = self._load_config(config_path)
        self.client = self._init_client()
        self.state = self._init_state()
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load SGR configuration following established patterns"""
        # Default config
        config = {
            'openai_api_key': os.getenv('OPENAI_API_KEY', ''),
            'openai_base_url': os.getenv('OPENAI_BASE_URL', ''),
            'openai_model': os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
            'max_tokens': int(os.getenv('MAX_TOKENS', '8000')),
            'temperature': float(os.getenv('TEMPERATURE', '0.2')),
            'tavily_api_key': os.getenv('TAVILY_API_KEY', ''),
            'max_search_results': int(os.getenv('MAX_SEARCH_RESULTS', '10')),
            'max_execution_steps': int(os.getenv('MAX_EXECUTION_STEPS', '6')),
            'reports_directory': os.getenv('REPORTS_DIRECTORY', 'reports')
        }
        
        # Load from YAML config file (following SGR pattern)
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    yaml_config = yaml.safe_load(f)
                    if yaml_config and 'openai' in yaml_config:
                        openai_cfg = yaml_config['openai']
                        config['openai_api_key'] = openai_cfg.get('api_key', config['openai_api_key'])
                        config['openai_base_url'] = openai_cfg.get('base_url', config['openai_base_url'])
                        config['openai_model'] = openai_cfg.get('model', config['openai_model'])
                        config['max_tokens'] = openai_cfg.get('max_tokens', config['max_tokens'])
                        config['temperature'] = openai_cfg.get('temperature', config['temperature'])
                    
                    if yaml_config and 'tavily' in yaml_config:
                        config['tavily_api_key'] = yaml_config['tavily'].get('api_key', config['tavily_api_key'])
                    
                    if yaml_config and 'search' in yaml_config:
                        config['max_search_results'] = yaml_config['search'].get('max_results', config['max_search_results'])
                    
                    if yaml_config and 'execution' in yaml_config:
                        config['max_execution_steps'] = yaml_config['execution'].get('max_steps', config['max_execution_steps'])
                        config['reports_directory'] = yaml_config['execution'].get('reports_dir', config['reports_directory'])
                        
            except Exception as e:
                self.console.print(f"[yellow]Warning: Error loading config: {e}[/yellow]")
        
        return config
    
    def _init_client(self) -> OpenAI:
        """Initialize OpenAI client following SGR patterns"""
        openai_kwargs = {'api_key': self.config['openai_api_key']}
        if self.config['openai_base_url']:
            openai_kwargs['base_url'] = self.config['openai_base_url']
        
        return OpenAI(**openai_kwargs)
    
    def _init_state(self) -> Dict[str, Any]:
        """Initialize research state"""
        return {
            'searches_completed': 0,
            'facts_collected': [],
            'sources': {},
            'current_plan': None,
            'clarification_used': False,
            'step_count': 0
        }
    
    def _create_small_model_prompt(self, task: str, context: Dict[str, Any]) -> str:
        """Create simplified prompt optimized for small models"""
        
        # Detect if we need clarification
        if len(task.strip()) < 10 or task.lower() in ['test', 'help', '?']:
            clarification_bias = "\n🚨 IMPORTANT: This request needs clarification. Use 'clarification' tool."
        else:
            clarification_bias = ""
        
        # Progressive complexity based on step count
        if context['step_count'] == 0:
            complexity_guidance = "Start simple: clarify if unclear, otherwise generate_plan."
        elif context['searches_completed'] < 2:
            complexity_guidance = "Focus on web_search to gather information."
        else:
            complexity_guidance = "Consider create_report if you have enough data."
        
        prompt = f"""You are a research assistant. Task: {task}

Current state:
- Step: {context['step_count'] + 1}
- Searches done: {context['searches_completed']}
- Facts collected: {len(context['facts_collected'])}
- Has plan: {context['current_plan'] is not None}

{complexity_guidance}{clarification_bias}

Respond with ONLY valid JSON matching this schema:
{{
  "reasoning_steps": ["brief reasoning step"],
  "current_situation": "current state description",
  "plan_status": "active",
  "searches_done": {context['searches_completed']},
  "enough_data": false,
  "remaining_steps": ["next step"],
  "task_completed": false,
  "function": {{
    "tool": "clarification|generate_plan|web_search|create_report|report_completion",
    // Additional fields based on tool choice
  }}
}}

Tool options:
- clarification: {{"tool": "clarification", "questions": ["question1", "question2"]}}
- generate_plan: {{"tool": "generate_plan", "research_goal": "goal", "planned_steps": ["step1", "step2"]}}
- web_search: {{"tool": "web_search", "query": "search query", "reasoning": "why search"}}
- create_report: {{"tool": "create_report", "title": "Report Title", "content": "detailed content", "reasoning": "why ready"}}
- report_completion: {{"tool": "report_completion", "reasoning": "task complete", "status": "completed"}}

Choose the most appropriate tool for current situation."""

        return prompt
    
    def _enhanced_json_coercion(self, raw_response: str) -> Optional[NextStep]:
        """Enhanced JSON parsing with multiple fallback strategies for small models"""
        
        # Strategy 1: Direct parsing
        try:
            data = json.loads(raw_response)
            return NextStep(**data)
        except:
            pass
        
        # Strategy 2: Extract JSON from response
        json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(0))
                return NextStep(**data)
            except:
                pass
        
        # Strategy 3: Clean common issues and retry
        cleaned = self._clean_json_for_small_models(raw_response)
        try:
            data = json.loads(cleaned)
            return NextStep(**data)
        except:
            pass
        
        # Strategy 4: Coerce simplified schema (like existing SGR system)
        coerced = self._coerce_simplified_to_nextstep(raw_response)
        if coerced:
            return coerced
        
        # Strategy 5: Extract natural language and convert
        return self._natural_language_to_nextstep(raw_response)
    
    def _clean_json_for_small_models(self, raw: str) -> str:
        """Clean JSON with patterns specific to small model errors"""
        
        # Extract JSON block
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            cleaned = json_match.group(0)
        else:
            cleaned = raw
        
        # Fix common small model JSON errors
        cleaned = re.sub(r',\s*}', '}', cleaned)  # Trailing commas in objects
        cleaned = re.sub(r',\s*]', ']', cleaned)  # Trailing commas in arrays
        cleaned = re.sub(r'([^"\\])\n', r'\1', cleaned)  # Unescaped newlines
        cleaned = re.sub(r'//.*?\n', '\n', cleaned)  # Remove comments
        cleaned = re.sub(r'/\*.*?\*/', '', cleaned, flags=re.DOTALL)  # Remove block comments
        
        # Fix double braces (common in small models)
        cleaned = re.sub(r'\{\{', '{', cleaned)
        cleaned = re.sub(r'\}\}', '}', cleaned)
        
        return cleaned
    
    def _coerce_simplified_to_nextstep(self, raw_response: str) -> Optional[NextStep]:
        """Coerce simplified responses to NextStep schema (following SGR pattern)"""
        
        try:
            # Try to parse as simplified schema first
            data = json.loads(self._clean_json_for_small_models(raw_response))
            
            # Handle common simplified patterns
            if 'clarification_questions' in data and 'actions' in data:
                # Pattern: {"clarification_questions": [...], "actions": [...]}
                if data['clarification_questions']:
                    function = Clarification(
                        tool="clarification",
                        questions=data['clarification_questions']
                    )
                elif data['actions']:
                    # Convert first action to appropriate function
                    action = data['actions'][0] if data['actions'] else {}
                    if 'search_query' in action:
                        function = WebSearch(
                            tool="web_search",
                            query=action['search_query'],
                            reasoning="Continuing research"
                        )
                    else:
                        function = GeneratePlan(
                            tool="generate_plan",
                            research_goal="Research task",
                            planned_steps=["Gather information", "Analyze data", "Create report"]
                        )
                else:
                    function = GeneratePlan(
                        tool="generate_plan",
                        research_goal="Research task",
                        planned_steps=["Gather information", "Analyze data", "Create report"]
                    )
                
                return NextStep(
                    reasoning_steps=["Processed simplified response"],
                    current_situation="Continuing research",
                    plan_status="active",
                    searches_done=self.state['searches_completed'],
                    enough_data=False,
                    remaining_steps=["Continue research"],
                    task_completed=False,
                    function=function
                )
                
        except Exception as e:
            self.console.print(f"[dim]Coercion failed: {e}[/dim]")
        
        return None
    
    def _natural_language_to_nextstep(self, raw_response: str) -> Optional[NextStep]:
        """Convert natural language response to NextStep (last resort)"""
        
        # Simple keyword-based conversion
        lower_response = raw_response.lower()
        
        if any(word in lower_response for word in ['clarify', 'unclear', 'more details', 'specify']):
            function = Clarification(
                tool="clarification",
                questions=["Could you provide more details about your research needs?"]
            )
        elif any(word in lower_response for word in ['search', 'find', 'look for']):
            # Extract potential search query
            query = "general research"
            if 'search for' in lower_response:
                query_match = re.search(r'search for (.+?)(?:\.|$)', lower_response)
                if query_match:
                    query = query_match.group(1).strip()
            
            function = WebSearch(
                tool="web_search",
                query=query,
                reasoning="Continuing research based on natural language response"
            )
        elif any(word in lower_response for word in ['report', 'summary', 'complete']):
            function = CreateReport(
                tool="create_report",
                title="Research Report",
                content="Based on available information...",
                reasoning="Creating report as indicated by response"
            )
        else:
            # Default to planning
            function = GeneratePlan(
                tool="generate_plan",
                research_goal="Research task",
                planned_steps=["Gather information", "Analyze findings", "Create report"]
            )
        
        return NextStep(
            reasoning_steps=["Converted from natural language"],
            current_situation="Processing natural language response",
            plan_status="active",
            searches_done=self.state['searches_completed'],
            enough_data=False,
            remaining_steps=["Continue research"],
            task_completed=False,
            function=function
        )
    
    def _execute_step(self, step: NextStep) -> str:
        """Execute a research step with enhanced error handling"""
        
        function = step.function
        tool = function.tool
        
        try:
            if tool == "clarification":
                return self._handle_clarification(function)
            elif tool == "generate_plan":
                return self._handle_generate_plan(function)
            elif tool == "web_search":
                return self._handle_web_search(function)
            elif tool == "create_report":
                return self._handle_create_report(function)
            elif tool == "report_completion":
                return self._handle_report_completion(function)
            else:
                return f"Unknown tool: {tool}"
                
        except Exception as e:
            self.console.print(f"[red]Error executing {tool}: {e}[/red]")
            return f"Error in {tool}: {str(e)}"
    
    def _handle_clarification(self, function: Clarification) -> str:
        """Handle clarification requests"""
        self.state['clarification_used'] = True
        questions = function.questions
        
        self.console.print(Panel(
            "\n".join(f"❓ {q}" for q in questions),
            title="[yellow]Clarification Needed[/yellow]",
            border_style="yellow"
        ))
        
        return f"Clarification requested: {len(questions)} questions"
    
    def _handle_generate_plan(self, function: GeneratePlan) -> str:
        """Handle research plan generation"""
        self.state['current_plan'] = {
            'goal': function.research_goal,
            'steps': function.planned_steps
        }
        
        self.console.print(Panel(
            f"🎯 **Goal:** {function.research_goal}\n\n" +
            "📋 **Planned Steps:**\n" +
            "\n".join(f"{i+1}. {step}" for i, step in enumerate(function.planned_steps)),
            title="[green]Research Plan Generated[/green]",
            border_style="green"
        ))
        
        return f"Plan created with {len(function.planned_steps)} steps"
    
    def _handle_web_search(self, function: WebSearch) -> str:
        """Handle web search (simplified simulation for now)"""
        self.state['searches_completed'] += 1
        query = function.query
        
        # Simulate search results (in production, use Tavily API)
        simulated_facts = [
            f"Fact {self.state['searches_completed']}.1: Key information about {query}",
            f"Fact {self.state['searches_completed']}.2: Additional context for {query}",
            f"Fact {self.state['searches_completed']}.3: Supporting details on {query}"
        ]
        
        self.state['facts_collected'].extend(simulated_facts)
        
        self.console.print(Panel(
            f"🔍 **Query:** {query}\n\n" +
            f"📊 **Results:** Found {len(simulated_facts)} new facts\n" +
            f"📈 **Total Facts:** {len(self.state['facts_collected'])}",
            title=f"[blue]Search #{self.state['searches_completed']} Completed[/blue]",
            border_style="blue"
        ))
        
        return f"Search completed: {len(simulated_facts)} facts found"
    
    def _handle_create_report(self, function: CreateReport) -> str:
        """Handle report creation"""
        title = function.title
        content = function.content
        
        # Create report with collected facts
        report = f"# {title}\n\n"
        report += f"{content}\n\n"
        report += "## Research Findings\n\n"
        
        for i, fact in enumerate(self.state['facts_collected'], 1):
            report += f"{i}. {fact}\n"
        
        report += f"\n## Summary\n\nCompleted {self.state['searches_completed']} searches and collected {len(self.state['facts_collected'])} facts."
        
        # Save report (following SGR naming convention)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        safe_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')
        filename = f"{timestamp}_{safe_title}.md"
        
        os.makedirs(self.config['reports_directory'], exist_ok=True)
        report_path = os.path.join(self.config['reports_directory'], filename)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        self.console.print(Panel(
            f"📄 **Title:** {title}\n" +
            f"📊 **Facts Used:** {len(self.state['facts_collected'])}\n" +
            f"💾 **Saved:** {report_path}",
            title="[green]Report Created[/green]",
            border_style="green"
        ))
        
        return f"Report created: {report_path}"
    
    def _handle_report_completion(self, function: ReportCompletion) -> str:
        """Handle task completion"""
        self.console.print(Panel(
            f"✅ **Status:** {function.status}\n" +
            f"📊 **Searches:** {self.state['searches_completed']}\n" +
            f"📋 **Facts:** {len(self.state['facts_collected'])}\n" +
            f"🎯 **Reasoning:** {function.reasoning}",
            title="[green]Research Completed[/green]",
            border_style="green"
        ))
        
        return f"Task completed: {function.status}"
    
    def research(self, task: str) -> str:
        """Main research method with small model optimizations"""
        
        self.console.print(Panel(
            f"🔬 **Research Task:** {task}\n" +
            f"🤖 **Model:** {self.config['openai_model']}\n" +
            f"🔗 **Base URL:** {self.config['openai_base_url'] or 'default'}\n" +
            f"🔧 **Debug - Client base_url:** {getattr(self.client, 'base_url', 'not set')}",
            title="[bold blue]SGR Small Model Enhanced Research[/bold blue]",
            border_style="blue"
        ))
        
        max_steps = self.config['max_execution_steps']
        
        for step_num in range(max_steps):
            self.state['step_count'] = step_num
            
            self.console.print(f"\n[bold]--- Step {step_num + 1}/{max_steps} ---[/bold]")
            
            # Create prompt optimized for small models
            prompt = self._create_small_model_prompt(task, self.state)
            
            try:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=self.console,
                    transient=True
                ) as progress:
                    task_progress = progress.add_task("Generating response...", total=None)
                    
                    # Get model response with small model optimized parameters
                    response = self.client.chat.completions.create(
                        model=self.config['openai_model'],
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=min(self.config['max_tokens'], 1000),  # Limit for small models
                        temperature=max(self.config['temperature'], 0.1)  # Ensure minimum temperature
                    )
                    
                    progress.update(task_progress, description="Parsing response...")
                    raw_response = response.choices[0].message.content
                
                # Enhanced parsing with multiple fallback strategies
                step = self._enhanced_json_coercion(raw_response)
                
                if not step:
                    self.console.print("[yellow]⚠️ Failed to parse response, trying next step...[/yellow]")
                    continue
                
                # Display step info
                self.console.print(f"[dim]🧠 Reasoning: {step.reasoning_steps[0] if step.reasoning_steps else 'Processing'}[/dim]")
                self.console.print(f"[dim]🎯 Action: {step.function.tool}[/dim]")
                
                # Execute step
                result = self._execute_step(step)
                
                # Check completion conditions
                if (step.function.tool == "report_completion" or 
                    step.task_completed or 
                    (step.function.tool == "create_report" and self.state['searches_completed'] >= 2)):
                    self.console.print("\n[bold green]✅ Research completed successfully![/bold green]")
                    break
                
            except Exception as e:
                self.console.print(f"[red]❌ Error in step {step_num + 1}: {e}[/red]")
                continue
        
        # Final summary
        summary = (f"Research completed in {step_num + 1} steps. "
                  f"Searches: {self.state['searches_completed']}, "
                  f"Facts: {len(self.state['facts_collected'])}")
        
        return summary

def main():
    """Main entry point following SGR conventions"""
    enhancer = SmallModelSGREnhancer()
    
    console = Console()
    console.print("[bold blue]🧠 SGR Small Model Enhanced - Research Agent[/bold blue]")
    console.print("Optimized for smaller models with enhanced error recovery\n")
    
    while True:
        try:
            task = console.input("🔍 Enter research task (or 'quit'): ").strip()
            
            if task.lower() in ['quit', 'exit', 'q']:
                console.print("👋 Goodbye!")
                break
            
            if not task:
                continue
            
            result = enhancer.research(task)
            console.print(f"\n[bold green]🎯 Final Result:[/bold green] {result}\n")
            
        except KeyboardInterrupt:
            console.print("\n👋 Interrupted by user.")
            break
        except Exception as e:
            console.print(f"[red]❌ Unexpected error: {e}[/red]")

if __name__ == "__main__":
    main()
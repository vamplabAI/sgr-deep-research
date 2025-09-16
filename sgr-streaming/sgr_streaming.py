#!/usr/bin/env python3
"""
SGR Research Agent - Schema-Guided Reasoning with Streaming Support
Integration of Streaming Structured Outputs into SGR system
"""

import json
import os
import yaml
import time
import re
from datetime import datetime
from typing import List, Union, Literal, Optional, Dict, Any
try:
    from typing import Annotated  # Python 3.9+
except ImportError:
    from typing_extensions import Annotated  # Python 3.8
from pydantic import BaseModel, Field
from annotated_types import MinLen, MaxLen
from openai import OpenAI
from tavily import TavilyClient
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from scraping import fetch_page_content
from enhanced_streaming import enhanced_streaming_display, EnhancedSchemaParser, SpecializedDisplays
from sgr_visualizer import SGRLiveMonitor
from sgr_step_tracker import SGRStepTracker

# =============================================================================
# CONFIGURATION (same as original SGR)
# =============================================================================

def load_config():
    """Load configuration from config.yaml and environment variables"""
    config = {
        'openai_api_key': os.getenv('OPENAI_API_KEY', ''),
        'openai_base_url': os.getenv('OPENAI_BASE_URL', ''),
        'openai_model': os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
        'max_tokens': int(os.getenv('MAX_TOKENS', '8000')),
        'temperature': float(os.getenv('TEMPERATURE', '0.4')),
        'tavily_api_key': os.getenv('TAVILY_API_KEY', ''),
        'max_search_results': int(os.getenv('MAX_SEARCH_RESULTS', '10')),
        'max_execution_steps': int(os.getenv('MAX_EXECUTION_STEPS', '6')),
        'reports_directory': os.getenv('REPORTS_DIRECTORY', 'reports'),
        'scraping_enabled': os.getenv('SCRAPING_ENABLED', 'false').lower() == 'true',
        'scraping_max_pages': int(os.getenv('SCRAPING_MAX_PAGES', '5')),
        'scraping_content_limit': int(os.getenv('SCRAPING_CONTENT_LIMIT', '1500')),
        'presence_penalty': float(os.getenv('PRESENCE_PENALTY', '0.6')),  # Added presence penalty
        'frequency_penalty': float(os.getenv('FREQUENCY_PENALTY', '0.6')), # Added frequency penalty
        'max_retries': int(os.getenv('MAX_RETRIES', '3')), # Added max retries
        'retry_delay': float(os.getenv('RETRY_DELAY', '1.0')), # Added retry delay
        # Reporting control
        'force_final_report': os.getenv('FORCE_FINAL_REPORT', 'false').strip().lower() in ('1', 'true', 'yes'),
        'min_searches_for_report': int(os.getenv('MIN_SEARCHES_FOR_REPORT', '2')),
        'min_sources_for_force_report': int(os.getenv('MIN_SOURCES_FOR_FORCE_REPORT', '5')),
        # Prompt budgeting to avoid proxy truncation
        'prompt_char_budget': int(os.getenv('PROMPT_CHAR_BUDGET', '9000')),
        'message_char_limit': int(os.getenv('MESSAGE_CHAR_LIMIT', '1200')),
        'max_history_messages': int(os.getenv('MAX_HISTORY_MESSAGES', '8'))
    }

    if os.path.exists('config.yaml'):
        try:
            with open('config.yaml', 'r', encoding='utf-8') as f:
                yaml_config = yaml.safe_load(f)

            if yaml_config:
                if 'openai' in yaml_config:
                    openai_cfg = yaml_config['openai']
                    config['openai_api_key'] = openai_cfg.get('api_key', config['openai_api_key'])
                    config['openai_base_url'] = openai_cfg.get('base_url', config['openai_base_url'])
                    config['openai_model'] = openai_cfg.get('model', config['openai_model'])
                    config['max_tokens'] = openai_cfg.get('max_tokens', config['max_tokens'])
                    config['temperature'] = openai_cfg.get('temperature', config['temperature'])
                    config['presence_penalty'] = openai_cfg.get('presence_penalty', config['presence_penalty'])
                    config['frequency_penalty'] = openai_cfg.get('frequency_penalty', config['frequency_penalty'])
                    config['max_retries'] = openai_cfg.get('max_retries', config['max_retries'])
                    config['retry_delay'] = openai_cfg.get('retry_delay', config['retry_delay'])

                if 'tavily' in yaml_config:
                    config['tavily_api_key'] = yaml_config['tavily'].get('api_key', config['tavily_api_key'])

                if 'search' in yaml_config:
                    config['max_search_results'] = yaml_config['search'].get('max_results', config['max_search_results'])

                if 'scraping' in yaml_config:
                    config['scraping_enabled'] = yaml_config['scraping'].get('enabled', config['scraping_enabled'])
                    config['scraping_max_pages'] = yaml_config['scraping'].get('max_pages', config['scraping_max_pages'])
                    config['scraping_content_limit'] = yaml_config['scraping'].get('content_limit', config['scraping_content_limit'])

                # Execution / reporting controls (optional)
                if 'execution' in yaml_config:
                    exec_cfg = yaml_config['execution'] or {}
                    config['reports_directory'] = exec_cfg.get('reports_dir', config['reports_directory'])
                    config['force_final_report'] = exec_cfg.get('force_final_report', config['force_final_report'])
                    config['min_searches_for_report'] = exec_cfg.get('min_searches_for_report', config['min_searches_for_report'])
                    config['min_sources_for_force_report'] = exec_cfg.get('min_sources_for_force_report', config['min_sources_for_force_report'])
                    # New optional tuning knobs with safe defaults
                    config['strict_report_quality'] = exec_cfg.get('strict_report_quality', False)
                    config['min_report_words'] = int(exec_cfg.get('min_report_words', 300))
                    config['min_report_words_forced'] = int(exec_cfg.get('min_report_words_forced', 150))

                if 'execution' in yaml_config:
                    exec_cfg = yaml_config['execution'] or {}
                    config['max_execution_steps'] = exec_cfg.get('max_steps', config['max_execution_steps'])
                    config['prompt_char_budget'] = exec_cfg.get('prompt_char_budget', config['prompt_char_budget'])
                    config['message_char_limit'] = exec_cfg.get('message_char_limit', config['message_char_limit'])
                    config['max_history_messages'] = exec_cfg.get('max_history_messages', config['max_history_messages'])

        except Exception as e:
            print(f"Warning: Could not load config.yaml: {e}")

    return config

CONFIG = load_config()

# Disable Rich Live dashboard on simple TTYs
SIMPLE_UI = os.getenv('SGR_SIMPLE_TTY', '0').strip().lower() in ('1', 'true', 'yes')

# =============================================================================
# SGR SCHEMAS (same as original)
# =============================================================================

class Clarification(BaseModel):
    """Ask clarifying questions when facing ambiguous requests"""
    tool: Literal["clarification"]
    reasoning: str = Field(description="Why clarification is needed")
    unclear_terms: Annotated[List[str], MinLen(1), MaxLen(5)] = Field(description="List of unclear terms or concepts")
    assumptions: Annotated[List[str], MinLen(2), MaxLen(4)] = Field(description="Possible interpretations to verify - use these as basis for questions")
    questions: Annotated[List[str], MinLen(3), MaxLen(5)] = Field(description="3-5 specific clarifying questions based on assumptions above")

class GeneratePlan(BaseModel):
    """Generate research plan based on clear user request"""
    tool: Literal["generate_plan"]
    reasoning: str = Field(description="Justification for research approach")
    research_goal: str = Field(description="Primary research objective")
    planned_steps: Annotated[List[str], MinLen(3), MaxLen(4)] = Field(description="List of 3-4 planned steps")
    search_strategies: Annotated[List[str], MinLen(2), MaxLen(3)] = Field(description="Information search strategies")

class WebSearch(BaseModel):
    """Search for information with credibility focus"""
    tool: Literal["web_search"]
    reasoning: str = Field(description="Why this search is needed and what to expect")
    query: str = Field(description="Search query in same language as user request")
    max_results: int = Field(default=10, description="Maximum results (1-15)")
    plan_adapted: bool = Field(default=False, description="Is this search after plan adaptation?")
    scrape_content: bool = Field(default_factory=lambda: CONFIG.get('scraping_enabled', False), description="Fetch full page content for deeper analysis")

class AdaptPlan(BaseModel):
    """Adapt research plan based on new findings"""
    tool: Literal["adapt_plan"]
    reasoning: str = Field(description="Why plan needs adaptation based on new data")
    original_goal: str = Field(description="Original research goal")
    new_goal: str = Field(description="Updated research goal")
    plan_changes: Annotated[List[str], MinLen(1), MaxLen(3)] = Field(description="Specific changes made to plan")
    next_steps: Annotated[List[str], MinLen(2), MaxLen(4)] = Field(description="Updated remaining steps")

class CreateReport(BaseModel):
    """Create comprehensive research report with citations"""
    tool: Literal["create_report"]
    reasoning: str = Field(description="Why ready to create report now")
    title: str = Field(description="Report title - MUST be in the SAME language as user_request_language_reference (English request → English title, Russian request → Russian title)")
    user_request_language_reference: str = Field(
        description="Copy of original user request to ensure language consistency"
    )
    content: str = Field(description="""
    DETAILED technical content (800+ words) with in-text citations.

    🚨 STEP 1: LANGUAGE DETECTION 🚨
    FIRST - Analyze user_request_language_reference to detect language:
    - Contains English words like "Plan", "detail", "price", "BMW" → USE ENGLISH
    - Contains Russian words like "Спланируй", "цену", "подробно" → USE RUSSIAN
    
    🚨 STEP 2: WRITE ENTIRE REPORT IN DETECTED LANGUAGE 🚨
    - If detected ENGLISH → ALL text in English (title, headings, content)
    - If detected RUSSIAN → ALL text in Russian (title, headings, content)
    - NEVER mix languages within the report
    
    ENGLISH STRUCTURE (if user_request_language_reference is English):
    1. Executive Summary
    2. Technical Analysis (with citations)
    3. Key Findings  
    4. Conclusions
    
    RUSSIAN STRUCTURE (if user_request_language_reference is Russian):
    1. Исполнительное резюме
    2. Технический анализ (с цитатами)
    3. Ключевые выводы
    4. Заключения

    OTHER REQUIREMENTS:
    - Include in-text citations for EVERY fact using [1], [2], [3] etc.
    - Citations must be integrated into sentences, not separate
    - Example English: "BMW X6 costs from $50,000 [1] which reflects market trends [2]."
    - Example Russian: "BMW X6 стоит от 50,000$ [1], что отражает рыночные тенденции [2]."

    🚨 FINAL CHECK: Report language MUST EXACTLY match user_request_language_reference language
    """)
    confidence: Literal["high", "medium", "low"] = Field(description="Confidence in findings")

class ReportCompletion(BaseModel):
    """Complete research task"""
    tool: Literal["report_completion"]
    reasoning: str = Field(description="Why research is now complete")
    completed_steps: Annotated[List[str], MinLen(1), MaxLen(5)] = Field(description="Summary of completed steps")
    status: Literal["completed", "failed"] = Field(description="Task completion status")

class NextStep(BaseModel):
    """SGR Core - Determines next reasoning step with adaptive planning"""

    # Reasoning chain - step-by-step thinking process (FIRST for Qwen stability)
    reasoning_steps: Annotated[List[str], MinLen(2), MaxLen(4)] = Field(
        description="Step-by-step reasoning process leading to decision"
    )

    # Reasoning and state assessment
    current_situation: str = Field(description="Current research situation analysis")
    plan_status: str = Field(description="Status of current plan execution")

    # Progress tracking
    searches_done: int = Field(default=0, description="Number of searches completed (MAX 3-4 searches)")
    enough_data: bool = Field(default=False, description="Sufficient data for report? (True after 2-3 searches)")

    # Next step planning
    remaining_steps: Annotated[List[str], MinLen(1), MaxLen(3)] = Field(description="1-3 remaining steps to complete task")
    task_completed: bool = Field(description="Is the research task finished?")

    # Tool routing with clarification-first bias
    function: Union[
        Clarification,      # FIRST PRIORITY: When uncertain
        GeneratePlan,       # SECOND: When request is clear
        WebSearch,          # Core research tool
        AdaptPlan,          # When findings conflict with plan
        CreateReport,       # When sufficient data collected
        ReportCompletion    # Task completion
    ]

# =============================================================================
# ASYNC SCHEMA PARSER
# =============================================================================

class AsyncSchemaParser:
    """Asynchronous schema parser for displaying structured information on the fly"""
    
    def __init__(self, console: Console):
        self.console = console
        self.current_json = ""
        self.parsed_fields = {}
        self.schema_type = None
        
    def detect_schema_type(self, json_content: str) -> str:
        """Determines schema type from JSON content"""
        if '"tool":"clarification"' in json_content:
            return "clarification"
        elif '"tool":"generate_plan"' in json_content:
            return "generate_plan"
        elif '"tool":"web_search"' in json_content:
            return "web_search"
        elif '"tool":"create_report"' in json_content:
            return "create_report"
        elif '"reasoning_steps"' in json_content:
            return "next_step"
        else:
            return "unknown"
    
    def extract_field(self, json_content: str, field_name: str) -> Optional[str]:
        """Extracts field value from partial JSON"""
        # Search for field in JSON
        patterns = [
            rf'"{field_name}"\s*:\s*"([^"]*)"',  # String
            rf'"{field_name}"\s*:\s*(\d+)',      # Number
            rf'"{field_name}"\s*:\s*(true|false)', # Boolean
            rf'"{field_name}"\s*:\s*\[([^\]]*)\]', # Array (simple)
        ]
        
        for pattern in patterns:
            match = re.search(pattern, json_content)
            if match:
                return match.group(1)
        return None
    
    def extract_array_items(self, json_content: str, field_name: str) -> List[str]:
        """Extracts array elements from partial JSON"""
        pattern = rf'"{field_name}"\s*:\s*\[(.*?)\]'
        match = re.search(pattern, json_content, re.DOTALL)
        
        if match:
            array_content = match.group(1)
            # Extract strings from array
            items = re.findall(r'"([^"]*)"', array_content)
            return items
        return []
    
    def create_display_table(self, schema_type: str, parsed_fields: Dict[str, Any]) -> Table:
        """Creates simple table with complete information"""
        
        # Check if we have data to display
        if not parsed_fields:
            table = Table(title="📊 Parsing JSON...", show_header=False)
            table.add_column("Status", style="yellow")
            table.add_row("⏳ Waiting for more data...")
            return table
        
        # COMPACT TABLE FOR ALL SCHEMAS
        table = Table(title="🤖 AI Response", show_header=True, header_style="bold cyan")
        table.add_column("Field", style="cyan", width=12)
        table.add_column("Value", style="white", width=45)
        
        # Reasoning - compact
        if "reasoning_steps" in parsed_fields:
            steps = parsed_fields["reasoning_steps"]
            if isinstance(steps, list) and steps:
                table.add_row("🧠 Steps", f"{len(steps)} reasoning steps")
        
        # Current analysis - shorter
        if "current_situation" in parsed_fields and parsed_fields["current_situation"]:
            situation = parsed_fields["current_situation"]
            table.add_row("📊 Situation", situation[:60] + "..." if len(situation) > 60 else situation)
        
        # Progress - single line
        progress_items = []
        if "searches_done" in parsed_fields:
            progress_items.append(f"{parsed_fields['searches_done']} searches")
        
        if "enough_data" in parsed_fields:
            status = "sufficient" if parsed_fields["enough_data"] else "need more"
            progress_items.append(status)
            
        if progress_items:
            table.add_row("📈 Progress", " • ".join(progress_items))
        
        # Tool decision - компактно
        if "function" in parsed_fields:
            func = parsed_fields["function"]
            if "tool" in func:
                tool_name = func['tool'].replace('_', ' ').title()
                table.add_row("🔧 Action", f"[bold green]{tool_name}[/bold green]")
            
            if "reasoning" in func:
                reasoning = func["reasoning"][:70] + "..." if len(func["reasoning"]) > 70 else func["reasoning"]
                table.add_row("💭 Why", reasoning)
            
            # For clarification requests - только кол-во вопросов
            if "unclear_terms" in func and isinstance(func["unclear_terms"], list):
                table.add_row("❓ Unclear", ", ".join(func["unclear_terms"][:3]))  # Только первые 3
            
            if "questions" in func and isinstance(func["questions"], list):
                table.add_row("❔ Questions", f"{len(func['questions'])} questions (see below)")
            
            # For search requests
            if "query" in func:
                table.add_row("🔎 Query", func["query"][:50] + "..." if len(func["query"]) > 50 else func["query"])
                
            # For plan generation
            if "research_goal" in func:
                table.add_row("🎯 Goal", func["research_goal"][:50] + "..." if len(func["research_goal"]) > 50 else func["research_goal"])
        
        # Next actions - только кол-во
        if "remaining_steps" in parsed_fields:
            steps = parsed_fields["remaining_steps"]
            if isinstance(steps, list) and steps:
                table.add_row("📋 Next", f"{len(steps)} planned steps")
        
        # Показываем любые другие поля что есть
        other_fields = {k: v for k, v in parsed_fields.items() 
                       if k not in ["reasoning_steps", "current_situation", "plan_status", 
                                   "searches_done", "enough_data", "function", 
                                   "remaining_steps", "task_completed"]}
        
        for key, value in other_fields.items():
            if value and isinstance(value, str) and len(key) < 30:
                display_value = value[:60] + "..." if len(value) > 60 else value
                table.add_row(key.replace("_", " ").title(), display_value)
        
        return table
    
    def update_from_json(self, json_content: str) -> tuple:
        """Обновляет парсинг и возвращает таблицу + вопросы для отображения"""
        self.current_json = json_content
        
        # Определяем тип схемы
        new_schema_type = self.detect_schema_type(json_content)
        if new_schema_type != "unknown":
            self.schema_type = new_schema_type
        
        # Пытаемся распарсить JSON частично
        try:
            # Сначала пытаемся полный парсинг
            if json_content.strip().endswith('}'):
                parsed = json.loads(json_content)
                self.parsed_fields = parsed
            else:
                # Частичный парсинг по полям
                self.parsed_fields = {}
                
                # Извлекаем различные поля в зависимости от типа схемы
                if self.schema_type == "next_step":
                    fields_to_extract = [
                        "current_situation", "plan_status", "searches_done", 
                        "enough_data", "task_completed"
                    ]
                    
                    for field in fields_to_extract:
                        value = self.extract_field(json_content, field)
                        if value is not None:
                            # Конвертируем типы
                            if field in ["searches_done"]:
                                try:
                                    self.parsed_fields[field] = int(value)
                                except:
                                    self.parsed_fields[field] = value
                            elif field in ["enough_data", "task_completed"]:
                                self.parsed_fields[field] = value.lower() == "true"
                            else:
                                self.parsed_fields[field] = value
                    
                    # Извлекаем массивы
                    reasoning_steps = self.extract_array_items(json_content, "reasoning_steps")
                    if reasoning_steps:
                        self.parsed_fields["reasoning_steps"] = reasoning_steps
                    
                    remaining_steps = self.extract_array_items(json_content, "remaining_steps")
                    if remaining_steps:
                        self.parsed_fields["remaining_steps"] = remaining_steps
                    
                    # Улучшенная обработка function объекта
                    if '"function"' in json_content:
                        # Ищем весь function объект целиком
                        function_match = re.search(r'"function"\s*:\s*\{(.*?)\}', json_content, re.DOTALL)
                        if function_match:
                            function_content = "{" + function_match.group(1) + "}"
                            try:
                                function_obj = json.loads(function_content)
                                self.parsed_fields["function"] = function_obj
                            except:
                                # Fallback - извлекаем tool
                                tool_match = re.search(r'"tool"\s*:\s*"([^"]*)"', function_content)
                                if tool_match:
                                    self.parsed_fields["function"] = {"tool": tool_match.group(1)}
                
                elif self.schema_type in ["generate_plan", "web_search", "create_report", "clarification"]:
                    # Общие поля для инструментов
                    common_fields = ["tool", "reasoning", "title", "query", "research_goal", "confidence"]
                    
                    for field in common_fields:
                        value = self.extract_field(json_content, field)
                        if value is not None:
                            self.parsed_fields[field] = value
                    
                    # Специальные массивы
                    array_fields = ["planned_steps", "search_strategies", "questions", "unclear_terms", "assumptions"]
                    for field in array_fields:
                        items = self.extract_array_items(json_content, field)
                        if items:
                            self.parsed_fields[field] = items
                    
                    # Длинные текстовые поля
                    if '"content"' in json_content:
                        content_match = re.search(r'"content"\s*:\s*"(.*?)"', json_content, re.DOTALL)
                        if content_match:
                            self.parsed_fields["content"] = content_match.group(1)
        
        except json.JSONDecodeError:
            # JSON еще не готов, продолжаем с частичным парсингом
            pass
        except Exception as e:
            # Логируем ошибку, но продолжаем
            pass
        
        # Создаем таблицу
        table = self.create_display_table(self.schema_type or "unknown", self.parsed_fields)
        
        # Извлекаем вопросы отдельно для показа внизу
        questions = []
        if ("function" in self.parsed_fields and 
            "questions" in self.parsed_fields["function"] and 
            isinstance(self.parsed_fields["function"]["questions"], list)):
            questions = self.parsed_fields["function"]["questions"]
        
        return table, questions

# =============================================================================
# STREAMING UTILITIES
# =============================================================================

def show_streaming_progress_with_parsing(stream, operation_name: str, console: Console):
    """
    Элегантный стриминг с Rich Live updates - обновляем одну область
    
    Args:
        stream: OpenAI streaming объект
        operation_name: Название операции для отображения
        console: Rich console для вывода
    
    Returns:
        tuple: (final_response, accumulated_content, metrics)
    """
    
    # Создаем парсер схем
    parser = AsyncSchemaParser(console)
    
    accumulated_content = ""
    chunk_count = 0
    start_time = time.time()
    last_update_time = start_time
    
    # Создаем layout для живого обновления
    layout = Layout()
    layout.split_column(
        Layout(Panel.fit("🚀 Starting...", title=f"📡 {operation_name}", border_style="cyan"), name="main"),
        Layout("", size=3, name="metrics")
    )
    
    with Live(layout, console=console, refresh_per_second=4) as live:
        try:
            # Собираем данные и обновляем в реальном времени
            for chunk in stream:
                chunk_count += 1
                current_time = time.time()
                
                # Извлекаем содержимое чанка
                content_delta = None
                
                if hasattr(chunk, 'type') and chunk.type == 'content.delta':
                    content_delta = chunk.delta
                elif hasattr(chunk, 'choices') and chunk.choices:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        content_delta = delta.content
                
                if content_delta:
                    accumulated_content += content_delta
                    
                    # Обновляем каждые 0.2 секунды или при значимом изменении
                    if (current_time - last_update_time > 0.2) or len(content_delta) > 10:
                        
                        # Создаем обновленную таблицу и получаем вопросы
                        table, questions = parser.update_from_json(accumulated_content)
                        
                        # Создаем контент с таблицей и вопросами внизу
                        content_parts = [table]
                        
                        if questions:
                            questions_table = Table(title="❔ Questions", show_header=False)
                            questions_table.add_column("Q", style="yellow", width=60)
                            for i, q in enumerate(questions, 1):
                                questions_table.add_row(f"{i}. {q}")
                            content_parts.append(questions_table)
                        
                        # Объединяем все в один контент
                        from rich.console import Group
                        combined_content = Group(*content_parts)
                        
                        # Обновляем основной контент
                        layout["main"].update(
                            Panel.fit(
                                combined_content, 
                                title=f"🤖 {operation_name} - Thinking...", 
                                border_style="cyan"
                            )
                        )
                        
                        # Обновляем метрики
                        elapsed = current_time - start_time
                        speed = len(accumulated_content) / elapsed if elapsed > 0 else 0
                        metrics_text = Text()
                        metrics_text.append(f"⏱️ {elapsed:.1f}s", style="dim cyan")
                        metrics_text.append(" | ", style="dim")
                        metrics_text.append(f"📦 {chunk_count} chunks", style="dim green")
                        metrics_text.append(" | ", style="dim")
                        metrics_text.append(f"📝 {len(accumulated_content)} chars", style="dim blue")
                        metrics_text.append(" | ", style="dim")
                        metrics_text.append(f"⚡ {speed:.0f} ch/s", style="dim yellow")
                        
                        layout["metrics"].update(Panel.fit(metrics_text, border_style="dim"))
                        
                        last_update_time = current_time
            
            # Получаем финальный ответ
            final_response = stream.get_final_completion()
            total_time = time.time() - start_time
            
            # Финальное обновление
            final_table, final_questions = parser.update_from_json(accumulated_content)
            
            # Создаем финальный контент с вопросами внизу
            final_parts = [final_table]
            
            if final_questions:
                questions_table = Table(title="❔ Questions", show_header=False)
                questions_table.add_column("Q", style="yellow", width=60)
                for i, q in enumerate(final_questions, 1):
                    questions_table.add_row(f"{i}. {q}")
                final_parts.append(questions_table)
            
            from rich.console import Group
            final_combined = Group(*final_parts)
            
            layout["main"].update(
                Panel.fit(
                    final_combined, 
                    title=f"✅ {operation_name} Completed!", 
                    border_style="green"
                )
            )
            
            # Финальные метрики
            final_speed = len(accumulated_content) / total_time if total_time > 0 else 0
            final_metrics = Text()
            final_metrics.append(f"⏱️ Total: {total_time:.2f}s", style="bold green")
            final_metrics.append(" | ", style="dim")
            final_metrics.append(f"📦 {chunk_count} chunks", style="bold blue")
            final_metrics.append(" | ", style="dim")
            final_metrics.append(f"📝 {len(accumulated_content)} chars", style="bold cyan")
            final_metrics.append(" | ", style="dim")
            final_metrics.append(f"📊 {final_speed:.0f} chars/sec", style="bold yellow")
            
            layout["metrics"].update(Panel.fit(final_metrics, border_style="green"))
            
            # Показываем финальный результат 1 секунду
            time.sleep(1.0)
            
        except Exception as e:
            # Показываем ошибку в live режиме
            error_panel = Panel.fit(
                f"❌ Streaming error: {e}", 
                title="Error", 
                border_style="red"
            )
            layout["main"].update(error_panel)
            time.sleep(2.0)
            raise
    
    # После выхода из Live - показываем компактную сводку
    console.print(f"\n🎯 [bold green]{operation_name} completed successfully![/bold green]")
    
    metrics = {
        "total_time": total_time,
        "chunk_count": chunk_count,
        "content_size": len(accumulated_content),
        "chars_per_second": len(accumulated_content) / total_time if total_time > 0 else 0
    }
    
    return final_response, accumulated_content, metrics

# Обратная совместимость - старая функция
def show_streaming_progress(stream, operation_name: str, console: Console):
    """Обратная совместимость"""
    return show_streaming_progress_with_parsing(stream, operation_name, console)

# =============================================================================
# STREAMING SGR FUNCTIONS
# =============================================================================

class StreamingSGRAgent:
    """SGR Agent с поддержкой стриминга"""
    
    def __init__(self, config):
        self.config = config
        self.simple_ui = SIMPLE_UI
        
        # Initialize OpenAI client
        openai_kwargs = {'api_key': config['openai_api_key']}
        if config['openai_base_url']:
            openai_kwargs['base_url'] = config['openai_base_url']
        
        self.client = OpenAI(**openai_kwargs)
        self.tavily = TavilyClient(config['tavily_api_key'])
        self.console = Console()
        
        # SGR Process Monitor with integrated step tracker
        self.step_tracker = SGRStepTracker()
        self.monitor = SGRLiveMonitor(self.console, self.step_tracker)
        
        # Context
        self.context = {
            "plan": None,
            "searches": [],
            "sources": {},
            "citation_counter": 0,
            "clarification_used": False,
            # Workflow control
            "tool_counts": {},
            "recent_tools": [],
            "report_generated": False
        }

    def _format_markdown_report(self, md: str) -> str:
        """Lightweight Markdown formatter for LLM-generated reports.
        - Normalizes newlines and trims excessive blank lines
        - Ensures blank lines around headings
        - Removes redundant setext underlines when ATX headings are used
        - Normalizes Key Findings section into bullet points
        """
        if not isinstance(md, str):
            return md

        text = md.replace("\r\n", "\n").replace("\r", "\n")

        # Remove setext-style underline lines directly under ATX headings
        lines = text.split("\n")
        cleaned = []
        for i, line in enumerate(lines):
            if i > 0 and re.fullmatch(r"[=\-]{3,}\s*", line) and cleaned and cleaned[-1].lstrip().startswith("#"):
                # skip underline line
                continue
            cleaned.append(line.rstrip())
        text = "\n".join(cleaned)

        # Ensure a blank line before and after headings
        def ensure_spacing_around_headings(s: str) -> str:
            out = []
            prev_blank = True
            lines2 = s.split("\n")
            for idx, ln in enumerate(lines2):
                is_heading = bool(re.match(r"^\s*#{1,6}\s+", ln))
                if is_heading and not prev_blank and out:
                    out.append("")
                    prev_blank = True
                out.append(ln)
                # Peek next line to decide if we need a blank line after
                if is_heading:
                    # Add a blank line after heading unless next is already blank or end
                    nxt = lines2[idx + 1] if idx + 1 < len(lines2) else None
                    if nxt is not None and nxt.strip() != "":
                        out.append("")
                        prev_blank = True
                        continue
                prev_blank = (ln.strip() == "")
            return "\n".join(out)

        text = ensure_spacing_around_headings(text)

        # Normalize Key Findings section into bullets (English and Russian)
        def bulletize_key_findings(s: str) -> str:
            lines3 = s.split("\n")
            out = []
            in_kf = False
            for i, ln in enumerate(lines3):
                if re.match(r"^\s*#{1,6}\s*(Key Findings|Ключевые выводы)\s*$", ln):
                    in_kf = True
                    out.append(ln)
                    # ensure a blank line after heading
                    if i + 1 < len(lines3) and lines3[i + 1].strip() != "":
                        out.append("")
                    continue
                if in_kf:
                    if re.match(r"^\s*#", ln):
                        # next section starts; exit Key Findings mode
                        in_kf = False
                        out.append(ln)
                        continue
                    if ln.strip() == "":
                        # collapse consecutive blanks within Key Findings
                        continue
                    # normalize existing bullet markers
                    m = re.match(r"^\s*([\-\*•])\s*(.*)$", ln)
                    content = m.group(2).strip() if m else ln.strip()
                    out.append(f"- {content}")
                    continue
                out.append(ln)
            return "\n".join(out)

        text = bulletize_key_findings(text)

        # Collapse 3+ blank lines into at most 2
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip() + "\n"

    def _strip_json_wrapper(self, text: str) -> str:
        """If text looks like a JSON object with a 'report' field, extract and return it.
        Also handles code-fenced JSON blocks and optional leading 'md ---' markers.
        """
        if not isinstance(text, str):
            return text
        s = text.strip()
        # Remove optional leading 'md ---' marker
        s = re.sub(r"^\s*md\s*-{2,}\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"^\s*md\s*—+\s*", "", s, flags=re.IGNORECASE)
        # Unwrap code fence if present
        m = re.match(r"^```(?:json|JSON)?\s*([\s\S]*?)```\s*$", s)
        if m:
            s = m.group(1).strip()
        # Try direct JSON parse
        try:
            data = json.loads(s)
            if isinstance(data, dict) and isinstance(data.get('report'), str):
                return data['report']
        except Exception:
            pass
        # Try to extract first JSON object
        try:
            m2 = re.search(r"\{[\s\S]*\}", s)
            if m2:
                data = json.loads(m2.group(0))
                if isinstance(data, dict) and isinstance(data.get('report'), str):
                    return data['report']
        except Exception:
            pass
        return text

    # ==============================
    # Prompt Budgeting Utilities
    # ==============================
    def _shrink_text(self, text: str, limit: int) -> str:
        if not isinstance(text, str) or len(text) <= limit:
            return text
        head = max(0, int(limit * 0.7))
        tail = max(0, limit - head - 20)
        return text[:head] + "\n... [truncated] ...\n" + (text[-tail:] if tail > 0 else "")

    def _prune_messages_for_budget(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        budget = int(self.config.get('prompt_char_budget', 9000))
        per_msg = int(self.config.get('message_char_limit', 1200))
        max_hist = int(self.config.get('max_history_messages', 8))

        if not messages:
            return messages

        # Always keep first two (system + initial user) if present
        preserved_prefix = []
        suffix_start = 0
        if messages and messages[0].get('role') == 'system':
            preserved_prefix.append({**messages[0], 'content': self._shrink_text(messages[0].get('content', ''), per_msg)})
            suffix_start = 1
        if len(messages) > 1 and messages[1].get('role') == 'user':
            preserved_prefix.append({**messages[1], 'content': self._shrink_text(messages[1].get('content', ''), per_msg)})
            suffix_start = 2

        suffix = messages[suffix_start:]
        # Keep only the last N messages from suffix
        suffix = suffix[-max_hist:]
        # Truncate each message content
        pruned_suffix = []
        for m in suffix:
            pruned_suffix.append({**m, 'content': self._shrink_text(m.get('content', ''), per_msg)})

        pruned = preserved_prefix + pruned_suffix
        # Enforce total budget by dropping oldest non-preserved if needed
        def total_chars(msgs):
            return sum(len(m.get('content', '')) for m in msgs)
        while pruned and total_chars(pruned) > budget:
            # Drop from after preserved prefix
            if len(pruned) > len(preserved_prefix):
                pruned.pop(len(preserved_prefix))
            else:
                # As a last resort, shrink system/user further
                for i in range(len(preserved_prefix)):
                    preserved_prefix[i]['content'] = self._shrink_text(preserved_prefix[i]['content'], max(400, int(per_msg * 0.6)))
                if total_chars(pruned) <= budget:
                    break
                else:
                    # Can't do more
                    break
        return pruned

    def build_source_bank(self) -> dict:
        """
        Build a deterministic source bank from self.context['searches'].
        Keys are SRC1, SRC2, ... in first-seen order (deduped by URL).
        """
        bank = {}
        seen = set()
        k = 0
        for s in self.context.get("searches", []):
            for r in s.get("results", []) or []:
                url = (r.get("url") or "").strip()
                if not url or url in seen:
                    continue
                seen.add(url)
                k += 1
                bank[f"SRC{k}"] = {
                    "title": (r.get("title") or "Untitled").strip(),
                    "url": url
                }
        return bank
    def replace_src_with_numeric(self, report_md: str, source_bank: dict) -> str:
        """
        Convert [SRC#] markers to numeric [1], [2] ordered by first appearance.
        Append a '## Sources' section in that same order.
        Unknown keys become [?]. Leaves URLs out of the prose.
        """
        import re

        # Collect first-appearance order
        order = []
        for m in re.finditer(r"\[SRC(\d+)\]", report_md):
            key = f"SRC{m.group(1)}"
            if key in source_bank and key not in order:
                order.append(key)

        key_to_num = {k: i + 1 for i, k in enumerate(order)}

        def repl(m):
            k = f"SRC{m.group(1)}"
            return f"[{key_to_num.get(k, '?')}]"

        numbered = re.sub(r"\[SRC(\d+)\]", repl, report_md)

        # Build Sources section
        if order:
            lines = []
            for k in order:
                n = key_to_num[k]
                v = source_bank[k]
                lines.append(f"{n}. {v['title']} — {v['url']}")
            numbered = numbered.rstrip() + "\n\n## Sources\n" + "\n".join(lines) + "\n"

        return numbered


    def get_system_prompt(self, user_request: str) -> str:
        """Generate system prompt with user request for language detection"""
        return f"""
You are an expert researcher with adaptive planning and Schema-Guided Reasoning capabilities.

🚨 CRITICAL: You MUST respond with valid JSON matching the NextStep schema. NO natural language text allowed.

USER REQUEST EXAMPLE: "{user_request}"
↑ 🚨 CRITICAL LANGUAGE RULE: Detect the language from this request and use THE SAME LANGUAGE for ALL outputs.

LANGUAGE DETECTION EXAMPLES:
- "Plan in detail..." → ENGLISH request → ALL reports in ENGLISH
- "Спланируй подробно..." → RUSSIAN request → ALL reports in RUSSIAN
- "Recherche détaillée..." → FRENCH request → ALL reports in FRENCH

🚨 JSON OUTPUT REQUIREMENT:
You MUST respond with a valid JSON object matching this NextStep schema:
{{
  "reasoning_steps": ["step 1", "step 2"],
  "current_situation": "description",
  "plan_status": "active|paused|completed",
  "searches_done": 0,
  "enough_data": false,
  "remaining_steps": ["next step"],
  "task_completed": false,
  "function": {{ "tool": "clarification|generate_plan|web_search|adapt_plan|create_report|report_completion", ... }}
}}

CORE PRINCIPLES:
1. SMART CLARIFICATION: Only ask for clarification when the request is truly ambiguous or impossible to research
2. REASONABLE ASSUMPTIONS: Make reasonable assumptions for common research requests
3. Adapt plan when new data conflicts with initial assumptions
4. Search queries in SAME LANGUAGE as user request
5. 🚨 REPORT ENTIRELY in SAME LANGUAGE as user request (title, headers, content - ALL in same language)
6. Every fact in report MUST have inline citation [1], [2], [3] integrated into sentences

CLARIFICATION GUIDELINES:
🚨 CRITICAL: If user says "begin", "start", "proceed", "go ahead" - NEVER ask for clarification, ALWAYS generate_plan
- Only use clarification for genuinely unclear requests (e.g., "test", "help", single words)
- For reasonable topics, proceed with generate_plan (e.g., "jazz history", "BMW prices", "AI trends")
- If user provides ANY context or direction, proceed with generate_plan
- Make reasonable assumptions about scope and focus
- Prefer action over endless clarification
- NEVER clarify twice in a row - if already clarified once, proceed with generate_plan

WORKFLOW:
1. generate_plan - create research plan (DEFAULT for clear topics)
2. web_search - gather information (2-3 searches MAX, FOLLOW YOUR PLAN)
3. adapt_plan - adapt when conflicts found
4. create_report - create detailed report with citations
5. report_completion - complete task
6. clarification - ONLY when request is truly ambiguous

SEARCH STRATEGY:
- After generating a plan, FOLLOW IT step by step
- Each search should address a different aspect from your planned_steps
- Don't stop after 1 search - continue until you have comprehensive data
- Only create report when you have sufficient data from multiple searches

ANTI-CYCLING: Maximum 1 clarification request per session.
ADAPTIVITY: Actively change plan when discovering new data.
LANGUAGE ADAPTATION: Always respond and create reports in the SAME LANGUAGE as the user's request.

🚨 REMEMBER: Respond ONLY with valid JSON. No explanatory text before or after the JSON.
        """.strip()

    def _force_report_if_possible(self, task: str) -> bool:
        """Attempt to synthesize and save a report if conditions allow.
        Returns True if a report was generated and saved.
        """
        if not self.config.get('force_final_report'):
            return False
        if self.context.get('report_generated'):
            return True
        searches_count = len(self.context.get('searches', []))
        sources_count = len(self.context.get('sources', {}))
        min_searches = int(self.config.get('min_searches_for_report', 2))
        min_sources = int(self.config.get('min_sources_for_force_report', 5))
        if sources_count >= min_sources or (searches_count >= min_searches and sources_count > 0):
            self.console.print("[yellow]⚠️ Early termination detected — synthesizing final report[/yellow]")
            report_md = self.generate_report_content(task)
            if not report_md:
                return False
            forced_cmd = CreateReport(
                tool="create_report",
                reasoning="force_final_report",
                title=f"Research Report: {task}",
                user_request_language_reference=task,
                content=report_md,
                confidence="medium"
            )
            # Create a step for UI clarity
            if not self.simple_ui:
                self.monitor.start_step("create_report_forced", "Creating report (forced)")
            self.step_tracker.start_step("create_report_forced", "Creating report (forced)")
            result = self.dispatch(forced_cmd)
            self.step_tracker.complete_current_step(result)
            if not self.simple_ui:
                self.monitor.complete_step(result)
            return bool(self.context.get('report_generated'))
        return False
    
    def stream_next_step(self, messages: List[Dict[str, str]]) -> tuple:
        """
        Generates next step using streaming
        
        Returns:
            tuple: (parsed_response, raw_content, metrics)
        """
        
        try:
            # Debug: show request details (useful for gateways/proxies)
            self.console.print(
                f"[dim]🔌 Streaming request: model={self.config['openai_model']}, response_format=NextStep, max_tokens={self.config['max_tokens']}, temperature={self.config['temperature']}[/dim]"
            )
            # Simple TTY mode: avoid streaming UI entirely; get raw text and parse ourselves
            if self.simple_ui:
                completion = self.client.chat.completions.create(
                    model=self.config['openai_model'],
                    messages=self._prune_messages_for_budget(messages),
                    max_tokens=self.config['max_tokens'],
                    temperature=self.config['temperature']
                )
                raw_content = completion.choices[0].message.content
                metrics = {}
                self._debug_dump_raw("nextstep_simple_parse_raw", raw_content or "")
                data = self._extract_first_json_dict(raw_content or "")
                if data is not None:
                    try:
                        parsed = NextStep(**data)
                        return parsed, (raw_content or ""), metrics
                    except Exception:
                        # Try schema coercion (e.g., {'clarification_questions': [...], 'actions': []})
                        coerced = self._coerce_model_json_to_nextstep(data)
                        if coerced is not None:
                            return coerced, (raw_content or ""), metrics
                else:
                    # Regex fallback: extract questions list without full JSON
                    qs = self._fallback_extract_clarification(raw_content or "")
                    if qs:
                        coerced = self._coerce_model_json_to_nextstep({
                            "clarification_questions": qs,
                            "actions": []
                        })
                        if coerced is not None:
                            return coerced, (raw_content or ""), metrics
                return None, (raw_content or ""), metrics
            # Try structured output first, fallback to regular if not supported
            try:
                with self.client.beta.chat.completions.stream(
                    model=self.config['openai_model'],
                    messages=self._prune_messages_for_budget(messages),
                    response_format=NextStep,
                    max_tokens=self.config['max_tokens'],
                    temperature=self.config['temperature']
                ) as stream:
                
                    if self.simple_ui:
                        final_response, raw_content, metrics = show_streaming_progress_with_parsing(
                            stream, "Planning Next Step", self.console
                        )
                    else:
                        final_response, raw_content, metrics = enhanced_streaming_display(
                            stream, "Planning Next Step", self.console
                        )
                    # Optional debug dump of raw streaming text
                    self._debug_dump_raw("nextstep_stream_raw", raw_content or "")
                
                # Update field durations for current step
                if 'field_durations' in metrics:
                    self.step_tracker.update_field_durations(metrics['field_durations'])
                
                if final_response and final_response.choices:
                    # For structured outputs content is in message.content as JSON string
                    content = final_response.choices[0].message.content
                    if content:
                        try:
                            # Parse JSON and create NextStep object (strip fences if present)
                            json_data = self._extract_first_json_dict(content)
                            if json_data is None:
                                raise json.JSONDecodeError("no json", content, 0)
                            try:
                                parsed = NextStep(**json_data)
                                return parsed, raw_content, metrics
                            except Exception as validation_error:
                                if os.getenv('SGR_DEBUG_JSON', '').strip().lower() in ('1', 'true', 'yes'):
                                    self.console.print(f"[yellow]🔧 NextStep validation failed, trying coercion: {validation_error}[/yellow]")
                                coerced = self._coerce_model_json_to_nextstep(json_data)
                                if coerced is not None:
                                    if os.getenv('SGR_DEBUG_JSON', '').strip().lower() in ('1', 'true', 'yes'):
                                        self.console.print(f"[green]✅ Coercion successful: {coerced.function.tool}[/green]")
                                    return coerced, raw_content, metrics
                                raise
                        except (json.JSONDecodeError, Exception) as e:
                            # Enhanced error handling with debugging info
                            self._debug_dump_raw("nextstep_stream_content", content)
                            
                            # Show detailed error information
                            error_type = type(e).__name__
                            self.console.print(f"❌ [red]Failed to parse LLM response ({error_type})[/red]")
                            
                            if os.getenv('SGR_DEBUG_JSON', '').strip().lower() in ('1', 'true', 'yes'):
                                self.console.print(f"[dim]Error details: {e}[/dim]")
                                self.console.print(f"[dim]Raw content preview: {content[:200]}...[/dim]")
                                
                                # Try to identify the issue
                                if isinstance(e, json.JSONDecodeError):
                                    self.console.print(f"[yellow]💡 JSON parsing failed at position {e.pos}[/yellow]")
                                    self.console.print(f"[yellow]💡 Try lowering temperature (0.1-0.3) for better structured output[/yellow]")
                                else:
                                    self.console.print(f"[yellow]💡 Schema validation failed - model may need better prompting[/yellow]")
                                
                                # Show model recommendations
                                self.console.print("[cyan]📋 Recommended models for structured output:[/cyan]")
                                self.console.print("[cyan]  • Best: gemma2:27b, llama3.1:70b[/cyan]")
                                self.console.print("[cyan]  • Good: gemma2:9b, llama3.1:8b[/cyan]")
                            else:
                                self.console.print("[dim]💡 Enable debug mode: export SGR_DEBUG_JSON=1[/dim]")
                            
                            return None, raw_content, metrics
                
                return None, raw_content, metrics
            
            except Exception as structured_error:
                # Structured output failed, try regular completion with explicit JSON instruction
                self.console.print("[yellow]⚠️ Structured output failed, trying regular completion...[/yellow]")
                
                # Add explicit JSON instruction to the last message
                json_messages = messages.copy()
                if json_messages:
                    json_messages[-1]['content'] += "\n\nIMPORTANT: Respond with ONLY valid JSON matching the NextStep schema. No other text."
                
                try:
                    response = self.client.chat.completions.create(
                        model=self.config['openai_model'],
                        messages=json_messages,
                        max_tokens=self.config['max_tokens'],
                        temperature=self.config['temperature']
                    )
                    
                    if response and response.choices:
                        content = response.choices[0].message.content
                        if content:
                            # Try to extract and parse JSON
                            json_data = self._extract_first_json_dict(content)
                            if json_data:
                                try:
                                    parsed = NextStep(**json_data)
                                    self.console.print("✅ [green]Fallback JSON parsing successful[/green]")
                                    return parsed, content, {}
                                except Exception:
                                    coerced = self._coerce_model_json_to_nextstep(json_data)
                                    if coerced is not None:
                                        self.console.print("✅ [green]Fallback coercion successful[/green]")
                                        return coerced, content, {}
                            
                            # Last resort: try to extract clarification questions from natural language
                            questions = self._fallback_extract_clarification(content)
                            if questions:
                                coerced = self._coerce_model_json_to_nextstep({
                                    "clarification_questions": questions,
                                    "actions": []
                                })
                                if coerced is not None:
                                    self.console.print("✅ [green]Fallback clarification extraction successful[/green]")
                                    return coerced, content, {}
                    
                except Exception as fallback_error:
                    self.console.print(f"❌ [red]Fallback also failed: {fallback_error}[/red]")
                
                # If all fallbacks fail, return the original structured error
                raise structured_error
                
        except Exception as e:
            # Enhanced diagnostics for gateways that return custom errors
            err_type = type(e).__name__
            status_code = getattr(e, 'status_code', None) or getattr(e, 'http_status', None)
            err_code = getattr(e, 'code', None)
            request_id = getattr(e, 'request_id', None)
            detail_parts = [f"type={err_type}"]
            if status_code is not None:
                detail_parts.append(f"status={status_code}")
            if err_code is not None:
                detail_parts.append(f"code={err_code}")
            if request_id is not None:
                detail_parts.append(f"req_id={request_id}")

            response_body = None
            try:
                resp = getattr(e, 'response', None)
                if resp is not None:
                    if hasattr(resp, 'json'):
                        response_body = resp.json()
                    elif hasattr(resp, 'text'):
                        response_body = resp.text
            except Exception:
                pass

            if response_body is not None:
                self.console.print(f"❌ [bold red]NextStep streaming error:[/bold red] {e} (" + ", ".join(detail_parts) + ")")
                self.console.print(f"[dim]Gateway response:[/dim] {response_body}")
            else:
                self.console.print(f"❌ [bold red]NextStep streaming error:[/bold red] {e} (" + ", ".join(detail_parts) + ")")

            # Non-streaming fallback (some gateways don't support streaming structured outputs)
            try:
                self.console.print("[yellow]🔁 Falling back to non-streaming structured request...[/yellow]")
                completion = self.client.chat.completions.create(
                    model=self.config['openai_model'],
                    messages=self._prune_messages_for_budget(messages),
                    max_tokens=self.config['max_tokens'],
                    temperature=self.config['temperature']
                )
                raw_content = completion.choices[0].message.content
                metrics = {}
                # Optional debug dump of non-streaming raw text
                self._debug_dump_raw("nextstep_parse_raw", raw_content or "")
                data = self._extract_first_json_dict(raw_content or "")
                if data is not None:
                    try:
                        parsed = NextStep(**data)
                        return parsed, raw_content or "", metrics
                    except Exception:
                        coerced = self._coerce_model_json_to_nextstep(data)
                        if coerced is not None:
                            return coerced, raw_content or "", metrics
                else:
                    qs = self._fallback_extract_clarification(raw_content or "")
                    if qs:
                        coerced = self._coerce_model_json_to_nextstep({
                            "clarification_questions": qs,
                            "actions": []
                        })
                        if coerced is not None:
                            return coerced, raw_content or "", metrics
            except Exception as e2:
                err2_type = type(e2).__name__
                status2 = getattr(e2, 'status_code', None) or getattr(e2, 'http_status', None)
                code2 = getattr(e2, 'code', None)
                self.console.print(f"❌ [bold red]Fallback parse failed:[/bold red] {e2} (type={err2_type}, status={status2}, code={code2})")
            raise

    def _debug_dump_raw(self, label: str, text: str) -> None:
        """Enhanced debug dump with JSON analysis when SGR_DEBUG_JSON=1."""
        try:
            if os.getenv('SGR_DEBUG_JSON', '').strip().lower() not in ('1', 'true', 'yes'):
                return
            
            os.makedirs('logs', exist_ok=True)
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Get current task name for better file naming
            task_name = getattr(self, 'current_task', 'unknown')[:20]
            safe_task = re.sub(r'[^\w\-_]', '_', task_name)
            
            path = os.path.join('logs', f"{ts}_{safe_task}_{label}.txt")
            
            # Enhanced content with analysis
            analysis_content = f"""=== SGR DEBUG DUMP ===
Timestamp: {datetime.now().isoformat()}
Label: {label}
Task: {task_name}
Content Length: {len(text)} characters

=== RAW CONTENT ===
{text}

=== JSON ANALYSIS ===
"""
            
            # Try to analyze JSON structure
            try:
                if text.strip():
                    # Check if it looks like JSON
                    stripped = text.strip()
                    if stripped.startswith('{') and stripped.endswith('}'):
                        analysis_content += "✅ Looks like complete JSON\n"
                        try:
                            parsed = json.loads(stripped)
                            analysis_content += f"✅ Valid JSON with {len(parsed)} top-level keys\n"
                            analysis_content += f"Keys: {list(parsed.keys())}\n"
                            
                            # Check for expected NextStep fields
                            expected_fields = ['reasoning_steps', 'current_situation', 'function']
                            missing_fields = [f for f in expected_fields if f not in parsed]
                            if missing_fields:
                                analysis_content += f"⚠️ Missing NextStep fields: {missing_fields}\n"
                            else:
                                analysis_content += "✅ Contains expected NextStep fields\n"
                                
                        except json.JSONDecodeError as je:
                            analysis_content += f"❌ JSON syntax error at position {je.pos}: {je.msg}\n"
                    else:
                        analysis_content += "⚠️ Does not look like complete JSON (missing braces)\n"
                else:
                    analysis_content += "❌ Empty content\n"
            except Exception as ae:
                analysis_content += f"❌ Analysis error: {ae}\n"
            
            analysis_content += "\n=== END DEBUG DUMP ===\n"
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(analysis_content)
            
            preview = (text or '')[:120].replace('\n', ' ')
            self.console.print(f"[dim]🧪 Debug saved to {path}[/dim]")
            self.console.print(f"[dim]📄 Preview: {preview}...[/dim]")
            
        except Exception:
            # Fallback to simple dump
            try:
                os.makedirs('logs', exist_ok=True)
                ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                path = os.path.join('logs', f"{ts}_{label}.txt")
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(text)
            except Exception:
                pass

    def _coerce_model_json_to_nextstep(self, data: Dict[str, Any]) -> Optional['NextStep']:
        """Enhanced coercion with comprehensive schema enforcement.
        Uses Schema Enforcement Engine to handle ALL validation issues proactively.
        """
        try:
            if not isinstance(data, dict):
                return None
            
            # Use Schema Enforcement Engine for comprehensive validation
            from schema_enforcement_engine import SchemaEnforcementEngine
            engine = SchemaEnforcementEngine()
            
            # Pass context to prevent clarification loops
            context = {
                'clarification_used': self.context.get('clarification_used', False),
                'user_messages': getattr(self, 'recent_user_messages', [])
            }
            
            # First try comprehensive schema enforcement
            try:
                enforced_data = engine.enforce_schema(data, context)
                return NextStep(**enforced_data)
            except Exception as enforcement_error:
                if os.getenv('SGR_DEBUG_JSON', '').strip().lower() in ('1', 'true', 'yes'):
                    self.console.print(f"[dim yellow]⚠️ Schema enforcement failed: {enforcement_error}[/dim yellow]")
                # Fall back to original coercion patterns
                pass
            
            # Helper function to ensure minimum list lengths
            def ensure_min_length(items, min_len, default_items):
                if isinstance(items, str):
                    items = [items]
                if not isinstance(items, list):
                    items = []
                while len(items) < min_len:
                    items.extend(default_items[:min_len - len(items)])
                return items[:min(len(items), min_len + 3)]  # Cap at reasonable max
            
            # Pattern 1: Clarification format {clarification_questions: [...], actions: []}
            if 'clarification_questions' in data:
                questions = data.get('clarification_questions') or []
                if isinstance(questions, str):
                    questions = [questions]
                
                # Only proceed with clarification if questions are meaningful
                # If questions are generic, convert to generate_plan instead
                generic_questions = [
                    "what do you want to research",
                    "could you provide more details",
                    "what are you looking for",
                    "can you be more specific"
                ]
                
                questions_text = ' '.join(questions).lower()
                is_generic = any(generic in questions_text for generic in generic_questions)
                
                if is_generic and len(questions) <= 2:
                    # Convert generic clarification to generate_plan
                    reasoning_steps = ensure_min_length([
                        "User request can be interpreted as a research topic",
                        "Will proceed with reasonable assumptions and create research plan"
                    ], 2, [])
                    
                    result = {
                        "reasoning_steps": reasoning_steps,
                        "current_situation": "Creating research plan based on user request.",
                        "plan_status": "active",
                        "searches_done": 0,
                        "enough_data": False,
                        "remaining_steps": ["Execute research plan", "Gather information", "Create report"],
                        "task_completed": False,
                        "function": {
                            "tool": "generate_plan",
                            "reasoning": "Request is clear enough to proceed with research planning.",
                            "research_goal": "Research the requested topic comprehensively",
                            "planned_steps": [
                                "Conduct web search for current information",
                                "Gather comprehensive data from reliable sources",
                                "Analyze and synthesize findings into report"
                            ],
                            "search_strategies": [
                                "Web search for current and relevant information",
                                "Focus on authoritative and recent sources"
                            ]
                        }
                    }
                    return NextStep(**result)
                
                # Proceed with clarification only if questions are specific
                questions = ensure_min_length(questions, 3, [
                    "Could you please provide more specific details about your request?",
                    "What particular aspect are you most interested in?",
                    "Are there any specific requirements or constraints I should know about?"
                ])
                
                unclear_terms = ensure_min_length(data.get('unclear_terms', []), 1, [
                    "The request topic or scope"
                ])
                
                assumptions = ensure_min_length(data.get('assumptions', []), 2, [
                    "You want a general overview of the topic",
                    "You need current and accurate information"
                ])
                
                reasoning_steps = ensure_min_length([
                    "User request requires specific clarification",
                    "Need additional details to provide targeted research"
                ], 2, [])
                
                result = {
                    "reasoning_steps": reasoning_steps,
                    "current_situation": "Awaiting user clarification to proceed with research.",
                    "plan_status": "paused",
                    "searches_done": 0,
                    "enough_data": False,
                    "remaining_steps": ["Receive clarification", "Generate research plan"],
                    "task_completed": False,
                    "function": {
                        "tool": "clarification",
                        "reasoning": "Need user to clarify request to provide accurate research.",
                        "questions": questions,
                        "unclear_terms": unclear_terms,
                        "assumptions": assumptions
                    }
                }
                return NextStep(**result)
            
            # Pattern 2: Full NextStep format but with schema issues
            if 'reasoning_steps' in data and 'current_situation' in data and 'function' in data:
                # This looks like a NextStep but might have schema issues
                reasoning_steps = ensure_min_length(data.get('reasoning_steps', []), 2, [
                    "Processing user request",
                    "Determining next action"
                ])
                
                current_situation = data.get('current_situation') or 'Processing request'
                plan_status = data.get('plan_status', 'active')
                searches_done = data.get('searches_done', 0)
                enough_data = data.get('enough_data', False)
                task_completed = data.get('task_completed', False)
                
                # Fix remaining_steps if it has complex objects
                remaining_steps = data.get('remaining_steps', [])
                if remaining_steps and isinstance(remaining_steps[0], dict):
                    # Convert complex objects to simple strings
                    simple_steps = []
                    for step in remaining_steps:
                        if isinstance(step, dict):
                            if 'action_type' in step:
                                action = step['action_type'].replace('_', ' ').title()
                                query = step.get('search_query', '')
                                if query:
                                    simple_steps.append(f"{action}: {query}")
                                else:
                                    simple_steps.append(action)
                            else:
                                simple_steps.append(str(step))
                        else:
                            simple_steps.append(str(step))
                    remaining_steps = simple_steps
                
                remaining_steps = ensure_min_length(remaining_steps, 1, ["Continue with plan"])
                
                # Fix function object based on tool type
                function_data = data.get('function', {})
                tool = function_data.get('tool', 'clarification')
                
                if tool == 'generate_plan':
                    # Extract research goal from reasoning or remaining steps
                    research_goal = "Research jazz history in the first thirty years"
                    if reasoning_steps:
                        goal_text = reasoning_steps[0].lower()
                        if 'jazz' in goal_text:
                            research_goal = "Research the history and development of jazz music in its first thirty years (1890s-1920s)"
                    
                    # Generate planned steps from remaining_steps or defaults
                    planned_steps = []
                    search_strategies = []
                    
                    if remaining_steps:
                        for step in remaining_steps:
                            if 'search' in step.lower():
                                search_strategies.append(f"Web search: {step}")
                                planned_steps.append(f"Execute {step}")
                            else:
                                planned_steps.append(step)
                    
                    # Ensure minimum requirements
                    planned_steps = ensure_min_length(planned_steps, 3, [
                        "Research early jazz origins and key figures",
                        "Investigate jazz development in the 1920s",
                        "Analyze jazz evolution and major milestones"
                    ])
                    
                    search_strategies = ensure_min_length(search_strategies, 2, [
                        "Search for early jazz history and origins",
                        "Research jazz development in the first three decades"
                    ])
                    
                    function_obj = {
                        "tool": "generate_plan",
                        "reasoning": function_data.get('reasoning', "Generated comprehensive research plan for jazz history"),
                        "research_goal": research_goal,
                        "planned_steps": planned_steps,
                        "search_strategies": search_strategies
                    }
                    
                elif tool == 'clarification':
                    # Handle clarification function
                    questions = ensure_min_length(function_data.get('questions', []), 3, [
                        "Could you provide more specific details?",
                        "What particular aspect interests you most?",
                        "Are there specific requirements to consider?"
                    ])
                    
                    unclear_terms = ensure_min_length(function_data.get('unclear_terms', []), 1, [
                        "Request scope and focus"
                    ])
                    
                    assumptions = ensure_min_length(function_data.get('assumptions', []), 2, [
                        "You want comprehensive information",
                        "Current and accurate data is preferred"
                    ])
                    
                    function_obj = {
                        "tool": "clarification",
                        "reasoning": function_data.get('reasoning', "Need clarification to proceed"),
                        "questions": questions,
                        "unclear_terms": unclear_terms,
                        "assumptions": assumptions
                    }
                    
                else:
                    # Default to clarification for unknown tools
                    function_obj = {
                        "tool": "clarification",
                        "reasoning": "Need clarification to proceed with request",
                        "questions": [
                            "Could you provide more specific details about your request?",
                            "What particular aspect are you most interested in?",
                            "Are there any specific requirements I should know about?"
                        ],
                        "unclear_terms": ["Request scope"],
                        "assumptions": [
                            "You want comprehensive information",
                            "Current data is preferred"
                        ]
                    }
                
                result = {
                    "reasoning_steps": reasoning_steps,
                    "current_situation": current_situation,
                    "plan_status": plan_status,
                    "searches_done": searches_done,
                    "enough_data": enough_data,
                    "remaining_steps": remaining_steps,
                    "task_completed": task_completed,
                    "function": function_obj
                }
                
                return NextStep(**result)
            
            # Pattern 3: Direct tool format {tool: "...", ...}
            if 'tool' in data:
                tool = data.get('tool')
                reasoning = data.get('reasoning', f"Executing {tool} step.")
                
                if tool == 'clarification':
                    questions = ensure_min_length(data.get('questions', []), 3, [
                        "Could you please provide more specific details?",
                        "What particular aspect interests you most?",
                        "Are there specific requirements I should consider?"
                    ])
                    
                    unclear_terms = ensure_min_length(data.get('unclear_terms', []), 1, [
                        "The specific scope or focus area"
                    ])
                    
                    assumptions = ensure_min_length(data.get('assumptions', []), 2, [
                        "You want comprehensive information on the topic",
                        "Current and accurate data is preferred"
                    ])
                    
                    reasoning_steps = ensure_min_length([reasoning, "Clarification needed before proceeding"], 2, [])
                    
                    result = {
                        "reasoning_steps": reasoning_steps,
                        "current_situation": "Awaiting user clarification.",
                        "plan_status": "paused",
                        "searches_done": 0,
                        "enough_data": False,
                        "remaining_steps": ["Receive clarification", "Generate plan"],
                        "task_completed": False,
                        "function": {
                            "tool": "clarification",
                            "reasoning": reasoning,
                            "questions": questions,
                            "unclear_terms": unclear_terms,
                            "assumptions": assumptions
                        }
                    }
                    return NextStep(**result)
                
                elif tool == 'generate_plan':
                    planned_steps = ensure_min_length(data.get('planned_steps', []), 3, [
                        "Conduct initial research",
                        "Gather comprehensive information",
                        "Analyze and synthesize findings"
                    ])
                    
                    search_strategies = ensure_min_length(data.get('search_strategies', []), 2, [
                        "Web search for current information",
                        "Academic and reliable source verification"
                    ])
                    
                    reasoning_steps = ensure_min_length([reasoning, "Research plan created"], 2, [])
                    
                    result = {
                        "reasoning_steps": reasoning_steps,
                        "current_situation": "Research plan generated and ready to execute.",
                        "plan_status": "active",
                        "searches_done": 0,
                        "enough_data": False,
                        "remaining_steps": planned_steps[:3],
                        "task_completed": False,
                        "function": {
                            "tool": "generate_plan",
                            "reasoning": reasoning,
                            "research_goal": data.get('research_goal', 'Conduct comprehensive research on the given topic'),
                            "planned_steps": planned_steps,
                            "search_strategies": search_strategies
                        }
                    }
                    return NextStep(**result)
                
                elif tool == 'web_search':
                    reasoning_steps = ensure_min_length([reasoning, "Executing web search"], 2, [])
                    
                    result = {
                        "reasoning_steps": reasoning_steps,
                        "current_situation": "Performing web search for information.",
                        "plan_status": "active",
                        "searches_done": 1,
                        "enough_data": False,
                        "remaining_steps": ["Analyze search results", "Continue research"],
                        "task_completed": False,
                        "function": {
                            "tool": "web_search",
                            "reasoning": reasoning,
                            "query": data.get('query', 'research topic'),
                            "max_results": data.get('max_results', 10),
                            "scrape_content": data.get('scrape_content', False)
                        }
                    }
                    return NextStep(**result)
            
            # Pattern 4: Minimal reasoning format {reasoning: "...", action: "..."}
            if 'reasoning' in data and ('action' in data or 'next_action' in data):
                reasoning = data.get('reasoning', 'Processing request.')
                action = data.get('action') or data.get('next_action', 'generate_plan')
                
                reasoning_steps = ensure_min_length([reasoning, "Proceeding with research planning"], 2, [])
                
                # Default to generate_plan instead of clarification
                result = {
                    "reasoning_steps": reasoning_steps,
                    "current_situation": "Creating research plan based on user request.",
                    "plan_status": "active",
                    "searches_done": 0,
                    "enough_data": False,
                    "remaining_steps": ["Execute research plan", "Gather information", "Create report"],
                    "task_completed": False,
                    "function": {
                        "tool": "generate_plan",
                        "reasoning": "User request is clear enough to proceed with research planning.",
                        "research_goal": "Research the requested topic comprehensively",
                        "planned_steps": [
                            "Conduct web search for current information",
                            "Gather comprehensive data from reliable sources", 
                            "Analyze and synthesize findings into report"
                        ],
                        "search_strategies": [
                            "Web search for current and relevant information",
                            "Focus on authoritative and recent sources"
                        ]
                    }
                }
                return NextStep(**result)
                
        except Exception as e:
            # Log coercion failure for debugging
            if os.getenv('SGR_DEBUG_JSON', '').strip().lower() in ('1', 'true', 'yes'):
                self.console.print(f"[dim yellow]⚠️ Coercion failed: {e}[/dim yellow]")
            return None
        
        return None

    def _fallback_extract_clarification(self, text: str) -> Optional[list]:
        """Enhanced extraction of clarification questions from natural language responses.
        Handles various formats including natural language, bullets, and JSON fragments.
        """
        try:
            import re
            
            # Pattern 1: Try to capture list in brackets
            m = re.search(r"clarification_questions\s*:\s*\[(.*?)\]", text, re.DOTALL | re.IGNORECASE)
            if m:
                block = m.group(1)
                items = re.findall(r"\"([^\"]+)\"", block)
                if items:
                    return [s.strip() for s in items if s.strip()]
            
            # Pattern 2: Look for question patterns in natural language
            question_patterns = [
                r"Could you (?:please )?(?:provide|specify|clarify|tell me).*?\?",
                r"What (?:specific|particular|kind of|type of).*?\?",
                r"Are there (?:any|specific).*?\?",
                r"Do you (?:want|need|have).*?\?",
                r"Would you like.*?\?",
                r"Can you (?:please )?(?:provide|specify|clarify).*?\?",
                r"Which (?:specific|particular|aspect).*?\?",
                r"How (?:detailed|specific|comprehensive).*?\?"
            ]
            
            questions = []
            for pattern in question_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    clean_question = re.sub(r'\s+', ' ', match.strip())
                    if clean_question and len(clean_question) > 10:  # Reasonable length
                        questions.append(clean_question)
            
            if questions:
                # Remove duplicates while preserving order
                seen = set()
                unique_questions = []
                for q in questions:
                    if q.lower() not in seen:
                        seen.add(q.lower())
                        unique_questions.append(q)
                return unique_questions[:5]  # Limit to 5 questions
            
            # Pattern 3: Lines beginning with dash or asterisk
            items = re.findall(r"^[\-\*]\s*(.+)$", text, re.MULTILINE)
            items = [s.strip().strip('"') for s in items if s.strip()]
            if items:
                return items[:5]  # Limit to 5 questions
            
            # Pattern 4: Look for sentences ending with question marks
            sentences = re.findall(r"[A-Z][^.!?]*\?", text)
            if sentences:
                clean_sentences = []
                for sentence in sentences:
                    clean = sentence.strip()
                    if len(clean) > 15 and len(clean) < 200:  # Reasonable length
                        clean_sentences.append(clean)
                if clean_sentences:
                    return clean_sentences[:3]  # Limit to 3 questions
            
            # Pattern 5: If text contains clarification-related keywords, generate default questions
            clarification_keywords = ['clarify', 'unclear', 'ambiguous', 'specify', 'details', 'more information']
            if any(keyword in text.lower() for keyword in clarification_keywords):
                return [
                    "Could you please provide more specific details about your request?",
                    "What particular aspect are you most interested in?",
                    "Are there any specific requirements or constraints I should know about?"
                ]
            
            return None
            
        except Exception:
            return None

    def _clean_json_text(self, text: str) -> str:
        """Clean and fix common JSON issues in model output"""
        import re
        
        # Remove code fences
        cleaned = text.strip().replace('\r', '')
        if cleaned.startswith("```"):
            i = 3
            while i < len(cleaned) and cleaned[i].isalpha():
                i += 1
            while i < len(cleaned) and cleaned[i] in (' ', '\t'):
                i += 1
            cleaned = cleaned[i:]
        
        end_fence = cleaned.rfind("```")
        if end_fence != -1:
            cleaned = cleaned[:end_fence]
        
        cleaned = cleaned.strip()
        
        # Very simple approach - just fix the most common issues
        # 1. Replace single quotes with double quotes (but be careful with contractions)
        cleaned = cleaned.replace("'tool':", '"tool":')
        cleaned = cleaned.replace("'generate_plan'", '"generate_plan"')
        cleaned = cleaned.replace("'web_search'", '"web_search"')
        cleaned = cleaned.replace("'clarification'", '"clarification"')
        cleaned = cleaned.replace("'create_report'", '"create_report"')
        
        # 2. Remove trailing commas
        cleaned = re.sub(r',(\s*[}\]])', r'\1', cleaned)
        
        # 3. Fix incomplete JSON
        if cleaned.count('{') > cleaned.count('}'):
            cleaned += '}'
        
        return cleaned.strip()

    def _extract_first_json_dict(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract and clean first balanced JSON object from arbitrary text."""
        if not text:
            return None
        
        # Try standard JSON parsing first
        try:
            cleaned = self._clean_json_text(text)
            idx_brace = cleaned.find('{')
            if idx_brace > 0:
                cleaned = cleaned[idx_brace:]
            
            start = cleaned.find('{')
            if start == -1:
                return None
            
            depth = 0
            end = -1
            for i in range(start, len(cleaned)):
                ch = cleaned[i]
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        end = i
                        break
            
            if end == -1:
                return None
            
            candidate = cleaned[start:end+1]
            parsed = json.loads(candidate)
            return self._clean_parsed_json_for_nextstep(parsed)
            
        except Exception:
            # If JSON parsing fails, try manual extraction
            return self._manual_extract_json_data(text)
    
    def _manual_extract_json_data(self, text: str) -> Optional[Dict[str, Any]]:
        """Manually extract JSON data when parsing fails"""
        import re
        
        try:
            # Extract key fields manually
            data = {}
            
            # Extract reasoning_steps
            reasoning_match = re.search(r'"reasoning_steps"\s*:\s*\[(.*?)\]', text, re.DOTALL)
            if reasoning_match:
                # Extract quoted strings from the array
                reasoning_content = reasoning_match.group(1)
                reasoning_items = re.findall(r'"([^"]*)"', reasoning_content)
                data['reasoning_steps'] = reasoning_items if reasoning_items else ["Processing request"]
            
            # Extract simple fields
            simple_fields = {
                'current_situation': r'"current_situation"\s*:\s*"([^"]*)"',
                'plan_status': r'"plan_status"\s*:\s*"([^"]*)"',
                'searches_done': r'"searches_done"\s*:\s*(\d+)',
                'enough_data': r'"enough_data"\s*:\s*(false|true)',
                'task_completed': r'"task_completed"\s*:\s*(false|true)'
            }
            
            for field, pattern in simple_fields.items():
                match = re.search(pattern, text)
                if match:
                    value = match.group(1)
                    if field in ['searches_done']:
                        data[field] = int(value)
                    elif field in ['enough_data', 'task_completed']:
                        data[field] = value.lower() == 'true'
                    else:
                        data[field] = value
            
            # Extract remaining_steps (flatten complex objects)
            remaining_match = re.search(r'"remaining_steps"\s*:\s*\[(.*?)\]', text, re.DOTALL)
            if remaining_match:
                remaining_content = remaining_match.group(1)
                # Look for query patterns in the complex objects
                queries = re.findall(r'"_query"\s*:\s*"([^"]*)"', remaining_content)
                functions = re.findall(r'_function\s*:\s*[\'"]([^\'"]*)[\'"]', remaining_content)
                
                steps = []
                for query in queries:
                    steps.append(f"Web search: {query}")
                for func in functions:
                    if func not in ['web_search']:  # Avoid duplicates
                        steps.append(f"Execute {func.replace('_', ' ')}")
                
                data['remaining_steps'] = steps if steps else ["Continue with plan"]
            
            # Set defaults for missing fields
            defaults = {
                'reasoning_steps': ["Processing request", "Determining action"],
                'current_situation': 'Processing user request',
                'plan_status': 'active',
                'searches_done': 0,
                'enough_data': False,
                'remaining_steps': ['Continue with plan'],
                'task_completed': False
            }
            
            for field, default in defaults.items():
                if field not in data:
                    data[field] = default
            
            # Add function field (will be completed by schema enforcement)
            data['function'] = {'tool': 'generate_plan'}
            
            return self._clean_parsed_json_for_nextstep(data)
            
        except Exception:
            return None
    
    def _clean_parsed_json_for_nextstep(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean parsed JSON to match NextStep schema requirements"""
        if not isinstance(data, dict):
            return data
        
        cleaned = data.copy()
        
        # Remove extra fields that aren't part of NextStep schema
        extra_fields = ['language', '_clarification_questions', '_id', 'notes', 'metadata']
        for field in extra_fields:
            cleaned.pop(field, None)
        
        # Fix remaining_steps - should be list of strings, not objects
        if 'remaining_steps' in cleaned:
            remaining = cleaned['remaining_steps']
            if isinstance(remaining, list):
                fixed_steps = []
                for step in remaining:
                    if isinstance(step, dict):
                        # Extract step name or description
                        step_name = step.get('step_name') or step.get('name') or step.get('description')
                        if step_name:
                            fixed_steps.append(str(step_name))
                        else:
                            # Convert dict to string representation
                            fixed_steps.append(f"Execute {step.get('function', {}).get('tool', 'action')}")
                    else:
                        fixed_steps.append(str(step))
                cleaned['remaining_steps'] = fixed_steps
        
        # Ensure reasoning_steps is a list of strings
        if 'reasoning_steps' in cleaned:
            steps = cleaned['reasoning_steps']
            if isinstance(steps, str):
                cleaned['reasoning_steps'] = [steps]
            elif isinstance(steps, list):
                cleaned['reasoning_steps'] = [str(s) for s in steps]
        
        # Fix function field if it has extra properties
        if 'function' in cleaned and isinstance(cleaned['function'], dict):
            func = cleaned['function'].copy()
            
            # Remove extra fields from function
            func_extra = ['_id', 'metadata', 'notes']
            for field in func_extra:
                func.pop(field, None)
            
            cleaned['function'] = func
        
        return cleaned

    def add_citation(self, url: str, title: str = "") -> int:
        """Add source and return citation number"""
        if url in self.context["sources"]:
            return self.context["sources"][url]["number"]

        self.context["citation_counter"] += 1
        number = self.context["citation_counter"]

        self.context["sources"][url] = {
            "number": number,
            "title": title,
            "url": url
        }

        return number
    
    def format_sources(self) -> str:
        """Format sources for report"""
        if not self.context["sources"]:
            return ""

        sources_text = "\n\n## Sources\n"

        for url, data in self.context["sources"].items():
            number = data["number"]
            title = data["title"]
            if title:
                sources_text += f"- [{number}] {title} - {url}\n"
            else:
                sources_text += f"- [{number}] {url}\n"

        return sources_text
    
    def _create_search_summary_for_llm(self, tavily_response: dict, citation_numbers: list) -> str:
        """Create a detailed summary of search results for LLM context"""
        summary_parts = []
        
        # Add Tavily's answer if available
        if tavily_response.get('answer'):
            summary_parts.append(f"SEARCH ANSWER: {tavily_response['answer']}")
        
        # Add detailed results
        results = tavily_response.get('results', [])
        if results:
            summary_parts.append(f"\nFOUND {len(results)} SOURCES:")
            
            for i, result in enumerate(results[:3]):  # Limit to top 3 results for budget
                citation_num = citation_numbers[i] if i < len(citation_numbers) else i+1
                title = result.get('title', 'No title')
                content = result.get('content', result.get('snippet', ''))[:160]  # First 160 chars
                url = result.get('url', '')
                
                summary_parts.append(f"[{citation_num}] {title}")
                if content:
                    summary_parts.append(f"    Content: {content}...")
                if url:
                    summary_parts.append(f"    URL: {url}")
                summary_parts.append("")  # Empty line between sources
        
        return "\n".join(summary_parts)
    
    def dispatch(self, cmd: BaseModel) -> Any:
        """Execute SGR commands (same as original SGR)"""
        
        if isinstance(cmd, Clarification):
            self.context["clarification_used"] = True
            
            # Show clarification questions in compact format
            questions_text = "\n".join([f"  {i}. {q}" for i, q in enumerate(cmd.questions, 1)])
            
            clarification_panel = Panel(
                f"[yellow]{questions_text}[/yellow]",
                title="❓ Please Answer These Questions",
                border_style="yellow",
                expand=False,
                width=80
            )
            self.console.print(clarification_panel)
            
            # Status notification
            status_panel = Panel(
                f"⏸️  [yellow]Research paused - waiting for your response[/yellow]",
                title="🔄 Status",
                border_style="yellow",
                expand=False,
                width=60
            )
            self.console.print(status_panel)
            
            return {
                "tool": "clarification",
                "questions": cmd.questions,
                "status": "waiting_for_user"
            }
        
        elif isinstance(cmd, GeneratePlan):
            # Guard: only allow a single plan per session (0 or 1)
            if self.context.get("plan") is not None:
                self.console.print("[yellow]ℹ️ Plan already exists — skipping re-generation[/yellow]")
                return self.context["plan"]

            plan = {
                "research_goal": cmd.research_goal,
                "planned_steps": cmd.planned_steps,
                "search_strategies": cmd.search_strategies,
                "created_at": datetime.now().isoformat()
            }
            
            self.context["plan"] = plan
            
            # Компактное отображение плана
            plan_table = Table(show_header=False, box=None, padding=(0, 1))
            plan_table.add_column("", style="cyan", width=8)
            plan_table.add_column("", style="white")
            
            plan_table.add_row("🎯 Goal:", cmd.research_goal[:50] + "..." if len(cmd.research_goal) > 50 else cmd.research_goal)
            plan_table.add_row("📝 Steps:", f"{len(cmd.planned_steps)} planned steps")
            
            plan_panel = Panel(
                plan_table,
                title="📋 Research Plan Created",
                border_style="cyan",
                expand=False,
                width=70
            )
            self.console.print(plan_panel)
            
            return plan
        
        elif isinstance(cmd, WebSearch):
            self.console.print(f"🔍 [bold cyan]Search query:[/bold cyan] [white]'{cmd.query}'[/white]")
            
            try:
                response = self.tavily.search(
                    query=cmd.query,
                    max_results=cmd.max_results
                )
                
                # Add citations
                citation_numbers = []
                for result in response.get('results', []):
                    url = result.get('url', '')
                    title = result.get('title', '')
                    if url:
                        citation_num = self.add_citation(url, title)
                        citation_numbers.append(citation_num)
                
                # Create detailed search result with summary for LLM context
                search_result = {
                    "query": cmd.query,
                    "answer": response.get('answer', ''),
                    "results": response.get('results', []),
                    "citation_numbers": citation_numbers,
                    "timestamp": datetime.now().isoformat(),
                    # Add summarized content for LLM context
                    "summary_for_llm": self._create_search_summary_for_llm(response, citation_numbers)
                }
                
                self.context["searches"].append(search_result)
                
                # Компактное отображение результатов поиска
                search_table = Table(show_header=False, box=None, padding=(0, 1))
                search_table.add_column("", style="cyan", width=10)
                search_table.add_column("", style="white")
                
                search_table.add_row("🔍 Query:", cmd.query[:40] + "..." if len(cmd.query) > 40 else cmd.query)
                search_table.add_row("📎 Sources:", f"{len(citation_numbers)} found")
                
                search_panel = Panel(
                    search_table,
                    title="🔍 Search Complete",
                    border_style="blue",
                    expand=False,
                    width=60
                )
                self.console.print(search_panel)
                
                return search_result
                
            except Exception as e:
                error_msg = f"Search error: {str(e)}"
                self.console.print(f"❌ {error_msg}")
                return {"error": error_msg}

        elif isinstance(cmd, AdaptPlan):
            # Update existing plan or create a minimal one if missing
            plan = self.context.get("plan") or {
                "research_goal": cmd.new_goal or cmd.original_goal,
                "planned_steps": [],
                "search_strategies": []
            }
            plan["research_goal"] = cmd.new_goal or plan.get("research_goal")
            # Replace planned_steps with next_steps provided by the model
            plan["planned_steps"] = list(cmd.next_steps)
            plan["updated_at"] = datetime.now().isoformat()
            plan["plan_changes"] = list(cmd.plan_changes)
            self.context["plan"] = plan

            # Compact display
            plan_table = Table(show_header=False, box=None, padding=(0, 1))
            plan_table.add_column("", style="cyan", width=10)
            plan_table.add_column("", style="white")
            plan_table.add_row("🎯 Goal:", (plan["research_goal"] or "")[0:50] + ("..." if len(plan["research_goal"])>50 else ""))
            plan_table.add_row("🔧 Changes:", ", ".join(plan["plan_changes"])[:50] + ("..." if len(", ".join(plan["plan_changes"]))>50 else ""))
            plan_table.add_row("📝 Next:", f"{len(plan['planned_steps'])} steps")

            self.console.print(Panel(plan_table, title="🛠 Plan Adapted", border_style="cyan", expand=False, width=70))
            return plan

        elif isinstance(cmd, ReportCompletion):
            # Finalize session and summarize
            summary = {
                "completed_steps": cmd.completed_steps,
                "status": cmd.status,
                "sources_count": len(self.context.get("sources", {})),
                "searches_count": len(self.context.get("searches", [])),
            }
            done_table = Table(show_header=False, box=None, padding=(0, 1))
            done_table.add_column("", style="green", width=12)
            done_table.add_column("", style="white")
            done_table.add_row("📌 Status:", cmd.status)
            done_table.add_row("📎 Sources:", str(summary["sources_count"]))
            done_table.add_row("🔍 Searches:", str(summary["searches_count"]))
            self.console.print(Panel(done_table, title="✅ Research Completed", border_style="green", expand=False, width=60))
            return summary
        
        elif isinstance(cmd, CreateReport):
            self.console.print(f"📝 [bold cyan]Creating Report with Streaming...[/bold cyan]")
            
            # Save report
            os.makedirs(self.config['reports_directory'], exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_title = "".join(c for c in cmd.title if c.isalnum() or c in (' ', '-', '_'))[:50]
            filename = f"{timestamp}_{safe_title}.md"
            filepath = os.path.join(self.config['reports_directory'], filename)
            
            # Prepare body and sources handling
            body = cmd.content or ""
            # Strip JSON wrappers if present
            body = self._strip_json_wrapper(body)
            # If content is empty (e.g., enforced CreateReport), synthesize content now
            if not body.strip():
                synthesized = self.generate_report_content(self.current_task if hasattr(self, 'current_task') else "")
                if synthesized:
                    body = synthesized
                    cmd.content = synthesized
            source_bank = self.build_source_bank()

            # Convert [SRC#] → numeric [n] and append Sources if [SRC] markers present
            processed_body = self._format_markdown_report(body)
            if "[SRC" in body:
                processed_body = self.replace_src_with_numeric(processed_body, source_bank)
            else:
                # If numeric citations present, append a Sources section from context
                if "[1]" in processed_body or re.search(r"\[(\d+)\]", processed_body):
                    # Build sources from context order by assigned number
                    entries = []
                    for url, data in sorted(self.context.get("sources", {}).items(), key=lambda kv: kv[1].get("number", 0)):
                        n = data.get("number")
                        title = data.get("title") or "Untitled"
                        entries.append(f"{n}. {title} — {url}")
                    if entries:
                        processed_body = processed_body.rstrip() + "\n\n## Sources\n" + "\n".join(entries) + "\n"

            full_content = (
                f"# {cmd.title}\n\n"
                f"*Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
                f"{processed_body}"
            )
            
            # Quality gate with configurable thresholds and flexible fallback
            forced = (cmd.reasoning in {"force_final_report", "sufficient_evidence_collected"})
            strict = bool(self.config.get('strict_report_quality', False))
            min_words_cfg = int(self.config.get('min_report_words', 300))
            min_words_forced_cfg = int(self.config.get('min_report_words_forced', 150))
            min_words = min_words_forced_cfg if forced else min_words_cfg
            has_citation = ("[SRC" in processed_body) or (re.search(r"\[(\d+)\]", processed_body) is not None)

            word_count = len((processed_body or "").split())
            missing_citations = bool(self.context["sources"]) and not has_citation

            def append_sources_section_if_missing(md: str) -> str:
                # If there are sources but no inline citations, at least append Sources section
                if not self.context["sources"]:
                    return md
                entries = []
                for url, data in sorted(self.context.get("sources", {}).items(), key=lambda kv: kv[1].get("number", 0)):
                    n = data.get("number")
                    title = data.get("title") or "Untitled"
                    entries.append(f"{n}. {title} — {url}")
                if entries and "\n## Sources\n" not in md:
                    return md.rstrip() + "\n\n## Sources\n" + "\n".join(entries) + "\n"
                return md

            # Enforce thresholds, but be pragmatic in forced mode or when strict mode is off
            if word_count < min_words or (missing_citations and not forced and strict):
                if forced:
                    self.console.print("[yellow]⚠️ Forced mode: report is short — saving as draft.[/yellow]")
                    full_content = "> [!NOTE] Draft saved (forced mode; may be short)\n\n" + full_content
                elif not strict:
                    # Save anyway but warn and try to help by appending sources
                    self.console.print("[yellow]⚠️ Report may be short or lacks citations — saving anyway (non-strict).[/yellow]")
                    full_content = append_sources_section_if_missing(full_content)
                else:
                    self.console.print("[yellow]⚠️ Report content too short or missing citations — not saving. Continue research.[/yellow]")
                    self.context["report_generated"] = False
                    return {
                        "status": "insufficient_report",
                        "reason": "too_short_or_missing_citations",
                        "word_count": word_count,
                    }
            elif missing_citations and not forced:
                # Not strict but citations missing: append sources and warn
                if not strict:
                    self.console.print("[yellow]⚠️ Missing inline citations — appending Sources section and saving.[/yellow]")
                    full_content = append_sources_section_if_missing(full_content)
                else:
                    self.console.print("[yellow]⚠️ Missing inline citations — not saving in strict mode.[/yellow]")
                    self.context["report_generated"] = False
                    return {
                        "status": "insufficient_report",
                        "reason": "missing_citations",
                        "word_count": word_count,
                    }

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(full_content)

            report = {
                "title": cmd.title,
                "content": cmd.content,
                "confidence": cmd.confidence,
                "sources_count": len(self.context["sources"]),
                "word_count": len(cmd.content.split()),
                "filepath": filepath,
                "timestamp": datetime.now().isoformat()
            }

            # Mark report generated in this session
            self.context["report_generated"] = True

            # Компактное отображение отчета
            report_table = Table(show_header=False, box=None, padding=(0, 1))
            report_table.add_column("", style="green", width=10)
            report_table.add_column("", style="white")
            
            report_table.add_row("📄 Title:", cmd.title[:45] + "..." if len(cmd.title) > 45 else cmd.title)
            report_table.add_row("📊 Content:", f"{report['word_count']} words, {report['sources_count']} sources")
            report_table.add_row("📈 Quality:", f"{cmd.confidence} confidence")
            report_table.add_row("💾 Saved:", os.path.basename(filepath))
            
            report_panel = Panel(
                report_table,
                title="📝 Report Created",
                border_style="green", 
                expand=False,
                width=70
            )
            self.console.print(report_panel)
            
            return report

        else:
            return f"Unknown command: {type(cmd)}"

    # ==============================
    # Report Synthesis (Final Step)
    # ==============================
    def generate_report_content(self, task: str) -> str:
        """Ask the model to synthesize a full report directly using SOURCE_BANK and search summaries.
        Returns markdown content expected to contain [SRC#] markers that map to SOURCE_BANK.
        """
        source_bank = self.build_source_bank()
        # Limit bank exposure to top 10 to fit budget
        items = list(source_bank.items())[:10]
        bank_lines = "\n".join([f"- {k}: {v['title']} — {v['url']}" for k, v in items])
        # Aggregate search summaries for additional context
        summaries = []
        for s in self.context.get("searches", []):
            if s.get("summary_for_llm"):
                summaries.append(s["summary_for_llm"])
        summary_text = "\n\n".join(summaries[:5])  # keep it concise

        system = (
            "You are an expert researcher. Respond ONLY with a compact JSON object with two keys: "
            "'report' (a Markdown string) and 'sources' (an array of URLs actually cited). "
            "The entire 'report' must be in the SAME language as the user's request. "
            "Use inline citations like [SRC1], [SRC2] that refer to SOURCE_BANK keys provided. "
            "Do NOT invent keys and do NOT output anything except the JSON object."
        )
        user = (
            f"TASK: {task}\n\n"
            f"SOURCE_BANK (use only these keys in citations as [SRC#]):\n{bank_lines}\n\n"
            f"SEARCH_SUMMARY (evidence excerpts):\n{summary_text}\n\n"
            "FORMAT:\n"
            "{\n  \"report\": \"# <Title>\\n\\n## Executive Summary\\n... with [SRC#] citations ...\\n\\n## Background / Analysis\\n...\\n\\n## Key Findings\\n- ... [SRC#]\\n\\n## Conclusion\\n...\",\n  \"sources\": [\"<url1>\", \"<url2>\"]\n}\n"
            "REQUIREMENTS:\n"
            "- 800+ words, technical but readable.\n"
            "- Start with an H1 title, then sections: Executive Summary, Background/Analysis, Key Findings (bullets), Conclusion.\n"
            "- Every factual claim should have an inline citation [SRC#] that maps to SOURCE_BANK.\n"
            "- If evidence is weak, use [SRC?].\n"
        )

        try:
            resp = self.client.chat.completions.create(
                model=self.config['openai_model'],
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                temperature=self.config['temperature'],
                max_tokens=min(8192, self.config['max_tokens'])
            )
            raw = resp.choices[0].message.content or ""
            # Try to parse JSON object and extract 'report'
            try:
                data = json.loads(raw)
                if isinstance(data, dict) and isinstance(data.get('report'), str):
                    return data['report']
            except Exception:
                # try to extract JSON payload between first { and last }
                try:
                    import re as _re
                    m = _re.search(r"\{[\s\S]*\}", raw)
                    if m:
                        data = json.loads(m.group(0))
                        if isinstance(data, dict) and isinstance(data.get('report'), str):
                            return data['report']
                except Exception:
                    pass
            # Fallback: return raw content
            return raw
        except Exception as e:
            self.console.print(f"[red]Failed to synthesize report: {e}[/red]")
            return ""

    # ==============================
    # Workflow Logic Gate Enforcement
    # ==============================
    def _inc_tool_count(self, tool: str) -> None:
        counts = self.context.setdefault("tool_counts", {})
        counts[tool] = counts.get(tool, 0) + 1
        recent = self.context.setdefault("recent_tools", [])
        recent.append(tool)
        # keep last 5
        self.context["recent_tools"] = recent[-5:]

    def _first_search_query(self) -> str:
        # Derive a reasonable first query from current task or plan
        goal = (self.context.get("plan") or {}).get("research_goal")
        base = goal or getattr(self, "current_task", "research topic")
        return f"{base} latest information"

    def _enforce_logic_gates(self, job, searches_count: int):
        """Enforce simple state-machine gates to prevent generation loops.
        - Only one generate_plan per session.
        - Require a plan before web_search.
        - Require ≥2 searches and at least 1 source before create_report/report_completion.
        - Discourage repeated identical web_search queries.
        """
        try:
            func = getattr(job, "function", None)
            if func is None or not hasattr(func, "tool"):
                return job

            tool = func.tool
            plan_exists = bool(self.context.get("plan"))
            sources_count = len(self.context.get("sources", {}))
            counts = self.context.get("tool_counts", {})

            # 1) No plan yet → force generate_plan
            if tool == "web_search" and not plan_exists:
                self.console.print("[yellow]⚠️ Gate: No plan yet → forcing generate_plan[/yellow]")
                job.function = GeneratePlan(
                    tool="generate_plan",
                    reasoning="Web search needs a plan. Creating initial plan.",
                    research_goal=(getattr(self, "current_task", "Research topic").strip() or "Research topic"),
                    planned_steps=[
                        "Conduct initial web search",
                        "Gather authoritative sources",
                        "Synthesize findings"
                    ],
                    search_strategies=[
                        "Use specific topical queries",
                        "Prefer recent, authoritative sources"
                    ]
                )
                return job

            # 1a) Adapt plan requires an existing plan and fresh data
            if tool == "adapt_plan":
                if not plan_exists:
                    self.console.print("[yellow]⚠️ Gate: No plan to adapt → forcing generate_plan[/yellow]")
                    job.function = GeneratePlan(
                        tool="generate_plan",
                        reasoning="Need a baseline plan before adaptation.",
                        research_goal=(getattr(self, "current_task", "Research topic").strip() or "Research topic"),
                        planned_steps=[
                            "Conduct initial web search",
                            "Gather authoritative sources",
                            "Synthesize findings"
                        ],
                        search_strategies=[
                            "Use specific topical queries",
                            "Prefer recent, authoritative sources"
                        ]
                    )
                    return job
                # Require that the last action was a web_search (adapt after new evidence)
                recent = self.context.get("recent_tools", [])
                if not recent or recent[-1] != "web_search":
                    self.console.print("[yellow]⚠️ Gate: Adaptation needs fresh search → forcing web_search[/yellow]")
                    job.function = WebSearch(
                        tool="web_search",
                        reasoning="Run a search to provide evidence for plan adaptation.",
                        query=self._first_search_query(),
                        max_results=min(10, self.config.get("max_search_results", 10)),
                        plan_adapted=True
                    )
                    return job

            # 2) Plan exists → avoid repeated generate_plan
            if tool == "generate_plan" and plan_exists:
                self.console.print("[yellow]⚠️ Gate: Plan already exists → forcing web_search[/yellow]")
                job.function = WebSearch(
                    tool="web_search",
                    reasoning="Proceeding to execute the existing plan.",
                    query=self._first_search_query(),
                    max_results=min(10, self.config.get("max_search_results", 10)),
                    plan_adapted=False
                )
                return job

            # 3) Create report only when we have enough material
            min_searches = int(self.config.get("min_searches_for_report", 2))
            if tool == "create_report" and (searches_count < min_searches or sources_count == 0):
                self.console.print("[yellow]⚠️ Gate: Not enough material for report → forcing web_search[/yellow]")
                job.function = WebSearch(
                    tool="web_search",
                    reasoning="Need more sources before creating report.",
                    query=self._first_search_query(),
                    max_results=min(10, self.config.get("max_search_results", 10)),
                    plan_adapted=False
                )
                return job

            # 4) Report completion should follow report creation and have sources
            if tool == "report_completion" and (not self.context.get("report_generated") or sources_count == 0):
                self.console.print("[yellow]⚠️ Gate: Completion blocked → not enough evidence[/yellow]")
                job.function = WebSearch(
                    tool="web_search",
                    reasoning="Gathering more evidence before completion.",
                    query=self._first_search_query(),
                    max_results=min(10, self.config.get("max_search_results", 10)),
                    plan_adapted=False
                )
                return job

            # 5a) Limit adapt_plan churn
            if tool == "adapt_plan" and counts.get("adapt_plan", 0) >= 2:
                self.console.print("[yellow]⚠️ Gate: Too many plan adaptations → forcing web_search[/yellow]")
                job.function = WebSearch(
                    tool="web_search",
                    reasoning="Executing plan after multiple adaptations.",
                    query=self._first_search_query(),
                    max_results=min(10, self.config.get("max_search_results", 10)),
                    plan_adapted=True
                )
                return job

            # 5) Basic anti-loop: avoid 3x same decision in a row
            recent = self.context.get("recent_tools", [])
            if len(recent) >= 2 and recent[-1:] == [tool] and recent[-2:-1] == [tool]:
                # Nudge towards progress: if stuck on generate_plan → web_search; if web_search → create_report (if enough)
                if tool == "generate_plan" and plan_exists:
                    self.console.print("[yellow]⚠️ Anti-loop: Repeated generate_plan → forcing web_search[/yellow]")
                    job.function = WebSearch(
                        tool="web_search",
                        reasoning="Advancing execution to avoid planning loop.",
                        query=self._first_search_query(),
                        max_results=min(10, self.config.get("max_search_results", 10)),
                        plan_adapted=False
                    )
                elif tool == "web_search":
                    # If we already have enough evidence, pivot to report; otherwise vary query
                    min_searches = int(self.config.get('min_searches_for_report', 2))
                    if searches_count >= min_searches and sources_count > 0:
                        self.console.print("[yellow]⚠️ Anti-loop: Repeated web_search with enough evidence → forcing create_report[/yellow]")
                        job.function = CreateReport(
                            tool="create_report",
                            reasoning="sufficient_evidence_collected",
                            title=f"Research Report: {getattr(self, 'current_task', 'Topic')}",
                            user_request_language_reference=getattr(self, 'current_task', ''),
                            content="",  # content will be synthesized or produced by model next
                            confidence="medium"
                        )
                    else:
                        self.console.print("[yellow]⚠️ Anti-loop: Repeated web_search → varying query[/yellow]")
                        job.function = WebSearch(
                            tool="web_search",
                            reasoning="Varying search to reduce duplication.",
                            query=self._first_search_query() + " sources and timeline",
                            max_results=min(10, self.config.get("max_search_results", 10)),
                            plan_adapted=True
                        )
                return job

            return job
        except Exception:
            # Fail open: if gates error, don't block flow
            return job

    def _can_complete_task(self, job, searches_count: int) -> bool:
        """Return True if it's appropriate to complete the task now."""
        func = getattr(job, "function", None)
        if func is None or not hasattr(func, "tool"):
            return False
        tool = func.tool
        sources_count = len(self.context.get("sources", {}))

        if tool == "create_report":
            return searches_count >= 2 and sources_count > 0
        if tool == "report_completion":
            return self.context.get("report_generated") and sources_count > 0
        return True
    
    def execute_research_task(self, task: str) -> str:
        """Execute research task using SGR with streaming"""
        
        self.console.print(Panel(task, title="🔍 Research Task", title_align="left"))
        
        # Запускаем мониторинг SGR процесса (optional)
        if not self.simple_ui:
            self.monitor.start_monitoring()
            self.monitor.update_context({
                "task": task,
                "plan": self.context.get("plan"),
                "searches": self.context.get("searches", []),
                "sources": self.context.get("sources", {})
            })
        
        system_prompt = self.get_system_prompt(task)
        
        self.console.print(f"\n[bold green]🚀 SGR RESEARCH STARTED (Enhanced Streaming Mode)[/bold green]")
        self.console.print(f"[dim]🤖 Model: {self.config['openai_model']}[/dim]")
        self.console.print(f"[dim]🔗 Base URL: {self.config['openai_base_url'] or 'default'}[/dim]")
        self.console.print(f"[dim]🎯 Enhanced Visualization: Enabled[/dim]")
        
        # Initialize conversation log
        log = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task}
        ]
        
        try:
            # Execute reasoning steps
            for i in range(self.config['max_execution_steps']):
                step_id = f"step_{i+1}"
                
                # Начинаем этап планирования 
                self.console.print(f"\n🧠 {step_id}: Planning next action...")
                
                # Track schema generation step
                schema_step_name = f"schema_generation_{step_id}"
                self.step_tracker.start_step(schema_step_name, f"{step_id}: Schema generation")
                self.monitor.start_step(schema_step_name, f"{step_id}: Schema generation")
                
                # Add context - be more directive about avoiding unnecessary clarification
                context_msg = ""
                if self.context["clarification_used"]:
                    context_msg = "CRITICAL: Clarification already used. You MUST proceed with generate_plan or web_search. DO NOT ask for clarification again."
                else:
                    # Proactively discourage unnecessary clarification
                    context_msg = "GUIDANCE: Only use clarification for truly ambiguous requests (single words, unclear topics). For reasonable research topics, proceed directly with generate_plan."
                
                searches_count = len(self.context.get("searches", []))
                sources_count = len(self.context.get("sources", {}))
                user_request_info = f"\nORIGINAL USER REQUEST: '{task}'\n(Use this for language consistency)"
                search_count_info = f"\nSEARCHES COMPLETED: {searches_count} (MAX 3-4 searches)"
                
                # Add plan progress reminder
                plan_progress_info = ""
                if self.context.get("plan") and searches_count > 0:
                    plan = self.context["plan"]
                    remaining_steps = plan.get("planned_steps", [])
                    if remaining_steps:
                        plan_progress_info = f"\nPLAN PROGRESS: You have completed {searches_count} searches. Continue with remaining planned steps: {remaining_steps}"
                
                context_msg = context_msg + "\n" + user_request_info + search_count_info + plan_progress_info if context_msg else user_request_info + search_count_info + plan_progress_info
                
                if self.context["sources"]:
                    sources_info = "\nAVAILABLE SOURCES FOR CITATIONS:\n"
                    # Limit to first 10 sources to avoid prompt bloat
                    for idx, (url, data) in enumerate(self.context["sources"].items()):
                        if idx >= 10:
                            sources_info += "... (truncated)\n"
                            break
                        number = data["number"]
                        title = data["title"] or "Untitled"
                        sources_info += f"[{number}] {title} - {url}\n"
                    sources_info += "\nUSE THESE EXACT NUMBERS [1], [2], [3] etc. in your report citations."
                    context_msg = context_msg + "\n" + sources_info if context_msg else sources_info

                # Encourage report creation when enough evidence exists
                readiness_hint = ""
                min_searches = int(self.config.get('min_searches_for_report', 2))
                if searches_count >= min_searches and sources_count > 0 and not self.context.get("report_generated"):
                    readiness_hint = (
                        "\nREPORT READINESS: You appear to have enough evidence. "
                        "If feasible, proceed with create_report now using the sources above."
                    )
                # On final iteration, strongly request report creation
                if (
                    self.config.get('force_final_report')
                    and i == self.config['max_execution_steps'] - 1
                    and not self.context.get("report_generated")
                ):
                    readiness_hint += (
                        "\nFINAL STEP: You MUST create_report now (no further web_search). "
                        "Include inline citations using the provided sources."
                    )
                if readiness_hint:
                    context_msg = (context_msg + "\n" + readiness_hint) if context_msg else readiness_hint

                # Build and inject SOURCE_BANK every turn (after searches accumulate)
                source_bank = self.build_source_bank()
                if source_bank:
                    bank_lines = "\n".join([f"- {k}: {v['title']} — {v['url']}" for k, v in source_bank.items()])
                    sources_info = (
                        "\nCITATION PROTOCOL:\n"
                        "• Use ONLY keys from SOURCE_BANK as inline markers like [SRC1], [SRC2].\n"
                        "• Do NOT use [1], [2], author-years, or paste URLs inline.\n"
                        "• Do NOT invent keys. If a claim lacks support, mark it [SRC?].\n"
                        "\nSOURCE_BANK:\n" + bank_lines
                    )
                    context_msg = (context_msg + "\n" + sources_info) if context_msg else sources_info

                if context_msg:
                    log.append({"role": "system", "content": context_msg})
                
                try:
                    # STREAMING NEXT STEP GENERATION
                    # Note: Dashboard will be paused during schema generation
                    # Users can scroll up to see the generation process
                    if not self.simple_ui:
                        self.monitor.stop_monitoring()  # Pause dashboard to show schema generation
                    
                    job, raw_content, metrics = self.stream_next_step(log)

                    # Resume dashboard after schema generation
                    if not self.simple_ui:
                        self.monitor.start_monitoring()

                    if job is None:
                        self.console.print("[bold red]❌ Failed to parse LLM response[/bold red]")
                        # Try to force a report before exiting this iteration
                        if self._force_report_if_possible(task):
                            break
                        break

                    # Enforce workflow logic gates BEFORE completing schema generation step
                    original_tool = job.function.tool
                    searches_count = len(self.context.get("searches", []))
                    sources_count = len(self.context.get("sources", {}))
                    job = self._enforce_logic_gates(job, searches_count)

                    # If this is the final iteration and we have enough evidence,
                    # but the model still didn't choose create_report, issue a final
                    # directive and re-generate once to obtain a CreateReport tool.
                    if (
                        self.config.get('force_final_report')
                        and i == self.config['max_execution_steps'] - 1
                        and not self.context.get("report_generated")
                        and searches_count >= int(self.config.get('min_searches_for_report', 2))
                        and sources_count > 0
                        and not isinstance(job.function, CreateReport)
                    ):
                        self.console.print("[yellow]⚠️ Final step: requesting create_report from model[/yellow]")
                        log.append({
                            "role": "system",
                            "content": (
                                "FINAL INSTRUCTION: You MUST produce a NextStep JSON where function.tool is 'create_report' "
                                "with a detailed report (≥800 words) using inline citations [1],[2] that map to the AVAILABLE SOURCES."
                            )
                        })
                        if not self.simple_ui:
                            self.monitor.stop_monitoring()
                        job2, raw_content2, _ = self.stream_next_step(log)
                        if not self.simple_ui:
                            self.monitor.start_monitoring()
                        if job2 is not None:
                            job = job2

                    effective_tool = job.function.tool

                    # Complete schema generation step (reflect effective tool)
                    self.step_tracker.complete_current_step(f"Generated: {effective_tool}")
                    if not self.simple_ui:
                        self.monitor.complete_step(f"Generated: {effective_tool}")

                    # Show both raw decision and enforced action if different
                    if effective_tool != original_tool:
                        self.console.print(f"🤖 [bold magenta]LLM Decision:[/bold magenta] {original_tool}  →  [green]Action:[/green] {effective_tool}")
                    else:
                        self.console.print(f"🤖 [bold magenta]LLM Decision:[/bold magenta] {effective_tool}")

                    # Track chosen tool for anti-loop logic
                    self._inc_tool_count(effective_tool)

                    # Начинаем этап выполнения в трекере (монитор использует те же данные)
                    # Note: clarification is handled separately below
                    if not isinstance(job.function, Clarification):
                        tool_step_name = f"{job.function.tool}_{step_id}"
                        self.step_tracker.start_step(tool_step_name, f"Executing {job.function.tool}")
                        if not self.simple_ui:
                            self.monitor.start_step(tool_step_name, f"Executing {job.function.tool}")

                    # Final-step hard guarantee: synthesize and save a report if forced and ready
                    if (
                        self.config.get('force_final_report')
                        and i == self.config['max_execution_steps'] - 1
                        and not self.context.get("report_generated")
                    ):
                        min_searches = int(self.config.get('min_searches_for_report', 2))
                        if searches_count >= min_searches and len(self.context.get('sources', {})) > 0 and not isinstance(job.function, CreateReport):
                            self.console.print("[yellow]⚠️ Forcing final report synthesis...[/yellow]")
                            report_md = self.generate_report_content(task)
                            if report_md:
                                forced_cmd = CreateReport(
                                    tool="create_report",
                                    reasoning="force_final_report",
                                    title=f"Research Report: {task}",
                                    user_request_language_reference=task,
                                    content=report_md,
                                    confidence="medium"
                                )
                                # Start explicit step for UI clarity
                                if not self.simple_ui:
                                    self.monitor.start_step("create_report_forced", "Creating report (forced)")
                                self.step_tracker.start_step("create_report_forced", "Creating report (forced)")
                                result = self.dispatch(forced_cmd)
                                self.step_tracker.complete_current_step(result)
                                if not self.simple_ui:
                                    self.monitor.complete_step(result)
                                # If saved successfully, exit
                                if self.context.get("report_generated"):
                                    self.console.print(f"\n✅ [bold green]Auto-completing after forced report creation[/bold green]")
                                    break
                    
                except Exception as e:
                    self.console.print(f"[bold red]❌ LLM request error: {str(e)}[/bold red]")
                    break
                
                # Check for task completion
                if job.task_completed or isinstance(job.function, ReportCompletion):
                    self.console.print(f"[bold green]✅ Task completed[/bold green]")
                    self.dispatch(job.function)
                    break
                
                # Check for clarification cycling
                if isinstance(job.function, Clarification) and self.context["clarification_used"]:
                    self.console.print(f"[bold red]❌ Clarification cycling detected - forcing continuation[/bold red]")
                    log.append({
                        "role": "user",
                        "content": "ANTI-CYCLING: Clarification already used. Continue with generate_plan."
                    })
                    continue
                
                # Handle clarification specially
                if isinstance(job.function, Clarification):
                    # Stop monitoring before showing clarification
                    if not self.simple_ui:
                        self.monitor.stop_monitoring()
                    
                    self.step_tracker.start_step("clarification", "Asking clarifying questions")
                    result = self.dispatch(job.function)
                    self.step_tracker.complete_current_step(result)
                    return "CLARIFICATION_NEEDED"
                
                # Add to conversation log with full NextStep reasoning
                # Include the reasoning schema so the agent can see its previous thoughts
                # Compact previous reasoning to reduce token usage
                reasoning_content = (
                    "Previous reasoning (compact):\n"
                    f"Plan status: {job.plan_status}\n"
                    f"Searches done: {job.searches_done}, Enough data: {job.enough_data}\n"
                    f"Next action: {job.function.tool}"
                )
                
                log.append({
                    "role": "assistant", 
                    "content": reasoning_content,
                    "tool_calls": [{
                        "type": "function",
                        "id": step_id,
                        "function": {
                            "name": job.function.tool,
                            "arguments": job.function.model_dump_json()
                        }
                    }]
                })
                
                # Execute tool
                result = self.dispatch(job.function)
                
                # Завершаем этап выполнения в трекере (монитор использует те же данные)
                self.step_tracker.complete_current_step(result)
                if not self.simple_ui:
                    self.monitor.complete_step(result)
                
                # Обновляем контекст в мониторе
                if not self.simple_ui:
                    self.monitor.update_context({
                        "plan": self.context.get("plan"),
                        "searches": self.context.get("searches", []),
                        "sources": self.context.get("sources", {})
                    })
                
                # Format result for log - use detailed summary for search results
                if isinstance(job.function, WebSearch) and isinstance(result, dict) and 'summary_for_llm' in result:
                    result_text = result['summary_for_llm']
                    # Debug: show first part of search results
                    self.console.print(f"[dim]🔍 Added search results to context: {result_text[:100]}...[/dim]")
                else:
                    result_text = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
                
                log.append({"role": "tool", "content": result_text, "tool_call_id": step_id})
                
                # Auto-complete after report creation only if a valid report was saved
                if isinstance(job.function, CreateReport) and self.context.get("report_generated"):
                    self.console.print(f"\n✅ [bold green]Auto-completing after report creation[/bold green]")
                    break
        
            # End of main loop — if we didn't produce a report, try forced synthesis
            if not self.context.get("report_generated"):
                self._force_report_if_possible(task)

        finally:
            # Останавливаем мониторинг
            if not self.simple_ui:
                self.monitor.stop_monitoring()
            
            # Save conversation log for debugging
            self._save_conversation_log(log, task)
        
        return "COMPLETED"
    
    def _save_conversation_log(self, log: List[Dict], task: str):
        """Save the full conversation log for debugging purposes"""
        try:
            os.makedirs("logs", exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_task = "".join(c for c in task if c.isalnum() or c in (' ', '-', '_'))[:50]
            log_filename = f"logs/{timestamp}_{safe_task}_conversation.json"
            
            with open(log_filename, 'w', encoding='utf-8') as f:
                json.dump({
                    "task": task,
                    "timestamp": timestamp,
                    "conversation_log": log,
                    "context": self.context
                }, f, ensure_ascii=False, indent=2)
            
            self.console.print(f"📝 [dim]Conversation log saved to: {log_filename}[/dim]")
            
        except Exception as e:
            self.console.print(f"⚠️ [dim]Failed to save conversation log: {e}[/dim]")

# =============================================================================
# MAIN INTERFACE
# =============================================================================

def main():
    """Main application interface"""
    console = Console()
    console.print("[bold]🧠 SGR Research Agent - Streaming Mode[/bold]")
    console.print("Schema-Guided Reasoning with real-time streaming progress")
    console.print()
    console.print("New features:")
    console.print("  🔄 Real-time streaming progress")
    console.print("  📊 Performance metrics")
    console.print("  📡 JSON generation visualization")
    console.print("  ⚡ Faster feedback")
    console.print()
    console.print("[dim]💡 Tip: During schema generation, you can scroll up to see the live JSON creation process[/dim]")
    console.print()
    
    # Initialize agent
    try:
        agent = StreamingSGRAgent(CONFIG)
    except Exception as e:
        console.print(f"❌ Failed to initialize agent: {e}")
        return
    
    awaiting_clarification = False
    original_task = ""
    
    while True:
        try:
            console.print("=" * 60)
            if awaiting_clarification:
                response = input("💬 Your clarification response (or 'quit'): ").strip()
                awaiting_clarification = False
                
                if response.lower() in ['quit', 'exit']:
                    break
                
                # Track user messages for anti-clarification-loop logic
                if not hasattr(agent, 'recent_user_messages'):
                    agent.recent_user_messages = []
                agent.recent_user_messages.append(response)
                # Keep only last 3 messages
                agent.recent_user_messages = agent.recent_user_messages[-3:]
                
                task = f"Original request: '{original_task}'\nClarification: {response}\n\nProceed with research based on clarification."
                agent.context["clarification_used"] = True  # Mark that clarification was used
            else:
                task = input("🔍 Enter research task (or 'quit'): ").strip()
            
            if task.lower() in ['quit', 'exit']:
                console.print("👋 Goodbye!")
                break
            
            if not task:
                console.print("❌ Empty task. Try again.")
                continue
            
            # Reset context for new task
            if not awaiting_clarification:
                agent.current_task = task  # Track current task for debug logging
                
                # Initialize user message tracking
                if not hasattr(agent, 'recent_user_messages'):
                    agent.recent_user_messages = []
                agent.recent_user_messages.append(task)
                agent.recent_user_messages = agent.recent_user_messages[-3:]
                
                agent.context = {
                    "plan": None,
                    "searches": [],
                    "sources": {},
                    "citation_counter": 0,
                    "clarification_used": False,
                    # Workflow control
                    "tool_counts": {},
                    "recent_tools": [],
                    "report_generated": False
                }
                original_task = task
            
            result = agent.execute_research_task(task)
            
            if result == "CLARIFICATION_NEEDED":
                awaiting_clarification = True
                continue
            
            # Show statistics using step tracker
            summary = agent.step_tracker.get_step_summary()
            clean_history = agent.step_tracker.get_clean_history()
            
            # Count web searches properly (look for steps containing 'web_search')
            web_search_count = sum(1 for step_name in summary['step_counts'].keys() if 'web_search' in step_name)
            console.print(f"\n📊 Session stats: 🔍 {web_search_count} searches, 📎 {len(agent.context.get('sources', {}))} sources")
            console.print(f"⏱️ Total time: {summary['total_time']:.1f}s, 📋 Steps: {summary['total_steps']}")
            console.print(f"📁 Reports saved to: ./{CONFIG['reports_directory']}/")
            
            # Показываем очищенную историю
            if clean_history:
                console.print(f"\n📚 [bold]Clean execution history:[/bold]")
                for i, step in enumerate(clean_history, 1):
                    duration_str = f"{step['duration']:.1f}s"
                    console.print(f"   {i}. [cyan]{step['name']}[/cyan] ({duration_str})")
            
        except KeyboardInterrupt:
            console.print("\n👋 Interrupted by user.")
            break
        except Exception as e:
            console.print(f"❌ Error: {e}")
            continue

if __name__ == "__main__":
    # Check required parameters
    if not CONFIG['openai_api_key']:
        print("ERROR: OPENAI_API_KEY not set in config.yaml or environment")
        exit(1)
    
    if not CONFIG['tavily_api_key']:
        print("ERROR: TAVILY_API_KEY not set in config.yaml or environment")
        exit(1)
    
    main()

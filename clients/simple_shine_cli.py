import json
from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt

console = Console()
client = OpenAI(base_url="http://localhost:8010/v1", api_key="dummy")


def safe_get_delta(chunk):
    if not hasattr(chunk, "choices") or not chunk.choices:
        return None
    first_choice = chunk.choices[0]
    if first_choice is None or not hasattr(first_choice, "delta"):
        return None
    return first_choice.delta


def stream_response_until_tool_call_or_end(model, messages):
    """
    Стримит ответ в реальном времени.
    Возвращает:
        - full_content: полный текст (если был до tool_call или весь, если tool_call не было)
        - clarification_questions: list или None
        - agent_id: str или None
    """
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
        temperature=0,
    )

    agent_id = None
    full_content = ""
    clarification_questions = None

    for chunk in response:
        # Обновляем agent_id, если пришёл
        if hasattr(chunk, "model") and chunk.model and chunk.model.startswith("sgr_agent_"):
            agent_id = chunk.model

        delta = safe_get_delta(chunk)
        if delta is None:
            continue

        # Проверяем tool_calls — если есть, прерываем немедленно
        if hasattr(delta, "tool_calls") and delta.tool_calls:
            for tool_call in delta.tool_calls:
                if tool_call.function and tool_call.function.name == "clarificationtool":
                    try:
                        args = json.loads(tool_call.function.arguments)
                        clarification_questions = args.get("questions", [])
                    except Exception as e:
                        console.print(f"[red]Error parsing clarification: {e}[/red]")
            # Прерываем поток сразу при первом tool_call
            return full_content, clarification_questions, agent_id

        # Обрабатываем контент: выводим сразу и сохраняем
        if hasattr(delta, "content") and delta.content:
            text = delta.content
            full_content += text
            console.print(text, end="", style="white")

    # Если дошли до конца — tool_call не было
    return full_content, None, agent_id


console.print("\n[bold green]Research Assistant v1.0[/bold green]", style="bold white")
initial_request = Prompt.ask("[bold yellow]Enter your research request[/bold yellow]")
console.print(f"\nStarting research: [bold]{initial_request}[/bold]")

current_model = "sgr_agent"
messages = [{"role": "user", "content": initial_request}]
agent_id = None

while True:
    console.print()  # пустая строка перед новым блоком вывода

    full_content, clarification_questions, returned_agent_id = stream_response_until_tool_call_or_end(
        model=current_model, messages=messages
    )

    if returned_agent_id:
        agent_id = returned_agent_id
        current_model = agent_id

    # Если агент запросил уточнение
    if clarification_questions is not None:
        console.print()  # завершить строку после последнего символа контента
        # Промежуточный контент уже был напечатан в реальном времени!
        # (если был — например, "Я думаю, вам нужно уточнить...")

        console.print("\n[bold red]Clarification needed:[/bold red]")
        for i, question in enumerate(clarification_questions, 1):
            console.print(f"[bold]{i}.[/bold] {question}", style="yellow")

        clarification = Prompt.ask("[bold grey]Enter your clarification[/bold grey]")
        console.print(f"\n[bold green]Providing clarification:[/bold green] [italic]{clarification}[/italic]")

        messages.append({"role": "user", "content": clarification})
        continue

    else:
        # Нет уточнений — это финальный ответ.
        # Контент уже напечатан в реальном времени выше!
        console.print()  # завершаем последнюю строку
        break

console.print("\n[bold gren] Report will be prepared in appropriate directory![/bold green]")

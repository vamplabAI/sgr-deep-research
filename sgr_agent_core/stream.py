import asyncio
import html
import json
import time

from openai.types.chat import ChatCompletionChunk


class StreamingGenerator:
    def __init__(self):
        self.queue = asyncio.Queue()

    def add(self, data: str):
        self.queue.put_nowait(data)

    def finish(self):
        self.queue.put_nowait(None)  # Termination signal

    async def stream(self):
        while True:
            data = await self.queue.get()
            if data is None:  # Termination signal
                break
            yield data
            # Small sleep to ensure chunks are sent immediately, not buffered
            await asyncio.sleep(0)


class OpenAIStreamingGenerator(StreamingGenerator):
    def __init__(self, model="gpt-4o"):
        super().__init__()
        self.model = model
        self.fingerprint = f"fp_{hex(hash(model))[-8:]}"
        self.id = f"chatcmpl-{int(time.time())}{hash(str(time.time()))}"[:29]
        self.created = int(time.time())
        self.choice_index = 0

    def add_chunk(self, chunk: ChatCompletionChunk):
        chunk.model = self.model
        super().add(f"data: {chunk.model_dump_json()}\n\n")

    def add_status(self, description: str, done: bool = False, action: str = None, **kwargs):
        """Add status event for OpenWebUI (thinking, processing, etc.).
        
        Note: This sends status as HTML details tag since we're streaming from an agent,
        not from a tool with event_emitter. OpenWebUI will parse the details tag and
        display it as a collapsible status item.
        """
        status_data = {
            "description": description,
            "done": done,
        }
        if action:
            status_data["action"] = action
        status_data.update(kwargs)
        
        # Send status as HTML details tag that OpenWebUI can parse
        # Using type="status" to distinguish from tool calls
        status_html = (
            f'<details type="status" done="{str(done).lower()}">'
            f'\n<summary>{description}</summary>\n'
            f'</details>\n'
        )
        
        response = {
            "id": self.id,
            "object": "chat.completion.chunk",
            "created": self.created,
            "model": self.model,
            "system_fingerprint": self.fingerprint,
            "choices": [
                {
                    "delta": {"content": status_html, "role": "assistant"},
                    "index": self.choice_index,
                    "finish_reason": None,
                    "logprobs": None,
                }
            ],
            "usage": None,
        }
        super().add(f"data: {json.dumps(response)}\n\n")
    
    def add_chunk_from_str(self, content: str):
        response = {
            "id": self.id,
            "object": "chat.completion.chunk",
            "created": self.created,
            "model": self.model,
            "system_fingerprint": self.fingerprint,
            "choices": [
                {
                    "delta": {"content": content, "role": "assistant", "tool_calls": None},
                    "index": self.choice_index,
                    "finish_reason": None,
                    "logprobs": None,
                }
            ],
            "usage": None,
        }
        super().add(f"data: {json.dumps(response)}\n\n")

    def add_tool_call(self, tool_call_id: str, function_name: str, arguments: str):
        """Adds tool call chunk in OpenWebUI format."""
        response = {
            "id": self.id,
            "object": "chat.completion.chunk",
            "created": self.created,
            "model": self.model,
            "system_fingerprint": f"fp_{hex(hash(self.model))[-8:]}",
            "choices": [
                {
                    "delta": {
                        "tool_calls": [
                            {
                                "index": 0,
                                "id": tool_call_id,
                                "type": "function",
                                "function": {"name": function_name, "arguments": arguments},
                            }
                        ]
                    },
                    "index": self.choice_index,
                    "logprobs": None,
                    "finish_reason": None,
                }
            ],
            "usage": None,
        }
        super().add(f"data: {json.dumps(response)}\n\n")

    def add_tool_call_start(self, tool_call_id: str, function_name: str, arguments: str):
        """
        Показываем начало выполнения инструмента с shimmer анимацией, чтобы обеспечить визуальную обратную связь.
        
        Args:
            tool_call_id: Уникальный ID вызова инструмента для связи с результатом
            function_name: Название функции инструмента для отображения
            arguments: JSON аргументы инструмента для отладки
        """
        # Отправляем details блок с done="false" для shimmer эффекта
        # ВАЖНО: OpenWebUI требует перевод строки после <details> тега
        # Блок будет свёрнут по умолчанию (без атрибута open)
        tool_html = (
            f'<details type="tool_calls" done="false" id="{tool_call_id}" '
            f'name="{function_name}" '
            f'arguments="{html.escape(arguments)}">\n'
            f'<summary>Executing {function_name}...</summary>\n'
            f'</details>\n'
        )
        
        response = {
            "id": self.id,
            "object": "chat.completion.chunk",
            "created": self.created,
            "model": self.model,
            "system_fingerprint": self.fingerprint,
            "choices": [
                {
                    "delta": {"content": tool_html, "role": "assistant"},
                    "index": self.choice_index,
                    "finish_reason": None,
                    "logprobs": None,
                }
            ],
            "usage": None,
        }
        super().add(f"data: {json.dumps(response)}\n\n")
    
    def add_tool_call_with_result(self, tool_call_id: str, function_name: str, arguments: str, result: str):
        """
        Добавляем завершённый вызов инструмента с результатом, чтобы обеспечить отладку.
        
        Args:
            tool_call_id: Уникальный ID вызова инструмента для связи с началом
            function_name: Название функции инструмента для отображения
            arguments: JSON аргументы инструмента для отладки
            result: Результат выполнения инструмента для отображения
        """
        # Отправляем завершённый блок с done="true" и результатом
        # ВАЖНО: Отправляем два отдельных блока:
        # 1. done="false" - показывает процесс выполнения (с shimmer)
        # 2. done="true" - показывает результат (свёрнут по умолчанию)
        # Оба блока будут свёрнуты, пользователь может развернуть для просмотра деталей
        
        # OpenWebUI требует перевод строки после <details> тега
        tool_html = (
            f'<details type="tool_calls" done="true" id="{tool_call_id}-result" '
            f'name="{function_name}" '
            f'arguments="{html.escape(arguments)}" '
            f'result="{html.escape(json.dumps(result, ensure_ascii=False))}">\n'
            f'<summary>View Result from {function_name}</summary>\n'
            f'</details>\n\n'
        )
        
        response = {
            "id": self.id,
            "object": "chat.completion.chunk",
            "created": self.created,
            "model": self.model,
            "system_fingerprint": self.fingerprint,
            "choices": [
                {
                    "delta": {"content": tool_html, "role": "assistant"},
                    "index": self.choice_index,
                    "finish_reason": None,
                    "logprobs": None,
                }
            ],
            "usage": None,
        }
        super().add(f"data: {json.dumps(response)}\n\n")

    def add_image(self, image_data: str, alt_text: str = "Image", format: str = "markdown"):
        """Add image to stream for rendering in OpenWebUI.
        
        Args:
            image_data: Image URL, relative path or base64 data URI
            alt_text: Alternative text for image
            format: Output format - 'markdown' (default) or 'html'
        """
        if format == "markdown":
            # Markdown format is the most reliable way for OpenWebUI
            markdown_image = f"\n\n![{alt_text}]({image_data})\n\n"
            self.add_chunk_from_str(markdown_image)
        elif format == "html":
            # HTML format as alternative option
            html_image = f'\n\n<img src="{html.escape(image_data)}" alt="{html.escape(alt_text)}" />\n\n'
            self.add_chunk_from_str(html_image)

    def add_base64_image(self, base64_str: str, alt_text: str = "Generated Image", image_type: str = "png"):
        """Add base64-encoded image for rendering in OpenWebUI.
        
        Args:
            base64_str: Base64-encoded image data (without data:image prefix)
            alt_text: Alternative text for image
            image_type: Image type (png, jpeg, jpg, gif, webp)
        """
        # Create full data URI
        data_uri = f"data:image/{image_type};base64,{base64_str}"
        self.add_image(data_uri, alt_text, format="markdown")

    def finish(self, content: str | None = None, finish_reason: str = "stop"):
        """Finishes stream with final chunk and usage."""
        # If content is provided, send it with simple checkmark
        if content:
            self.add_chunk_from_str(f"\n\n✓ {content}\n")
        
        # Send final chunk with finish_reason
        final_response = {
            "id": self.id,
            "object": "chat.completion.chunk",
            "created": self.created,
            "model": self.model,
            "system_fingerprint": f"fp_{hex(hash(self.model))[-8:]}",
            "choices": [{"index": self.choice_index, "delta": {}, "logprobs": None, "finish_reason": finish_reason}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }
        super().add(f"data: {json.dumps(final_response)}\n\n")
        super().add("data: [DONE]\n\n")
        super().finish()

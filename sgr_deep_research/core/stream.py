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
        """Show tool execution start with shimmer animation."""
        # Send initial details with done="false" for shimmer effect
        # Note: OpenWebUI's marked extension requires newline after <details> tag
        tool_html = (
            f'<details type="tool_calls" done="false" id="{tool_call_id}" '
            f'name="{function_name}" '
            f'arguments="{html.escape(arguments)}">\n'
            f'<summary>Executing...</summary>\n'
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
        """Adds completed tool call with result in OpenWebUI HTML format."""
        # Note: We send both done="false" and done="true" elements
        # OpenWebUI will show both, but the first one (done="false") will have shimmer animation
        # and the second one (done="true") will show the result
        # They will appear as separate collapsible blocks
        
        # Send completed version (this will appear after the done="false" one)
        # Note: OpenWebUI's marked extension requires newline after <details> tag
        tool_html = (
            f'<details type="tool_calls" done="true" id="{tool_call_id}-result" '
            f'name="{function_name}" '
            f'arguments="{html.escape(arguments)}" '
            f'result="{html.escape(json.dumps(result, ensure_ascii=False))}">\n'
            f'<summary>Просмотр результата</summary>\n'
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


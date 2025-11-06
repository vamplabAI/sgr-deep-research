from openai import pydantic_function_tool

from sgr_deep_research.core.agents.sgr_tools_agent import SGRToolCallingResearchAgent
from sgr_deep_research.settings import get_config
from sgr_deep_research.core.tools import ReasoningTool


config = get_config()

class SGRToolCallingResearchAgentDeepseek(SGRToolCallingResearchAgent):
    """Agent that uses OpenAI native function calling to select and execute
    tools based on SGR like reasoning scheme.
    Takes into account the specifics of DeepSeek-V3.2-Exp (non-thinking mode).
    This model prefers to ignore reasoning phase and move straight to the next tool"""

    name: str = "sgr_tool_calling_agent_deepseek"

    async def _reasoning_phase(self) -> ReasoningTool:
        # Provide ONLY ReasoningTool to the model on the reasoning step
        msgs = await self._prepare_context()
        last_message = msgs[-1]
        if not isinstance(last_message.get("content"), str):
            last_message["content"] = last_message.get("content") or ""
        # Build concise instruction from the tool's schema (with enums, constraints)
        instruction = ReasoningTool.schema_to_instruction(
            prefix="[REASONING_REQUIRED] Produce ReasoningTool arguments strictly per schema:",
            suffix="Be concise, factual, and use the user's language.",
        )
        last_message["content"] += "\n\n" + instruction
        async with self.openai_client.chat.completions.stream(
            model=config.openai.model,
            messages=msgs,
            max_tokens=config.openai.max_tokens,
            temperature=config.openai.temperature,
            tools=[pydantic_function_tool(ReasoningTool, name=ReasoningTool.tool_name, description="")],
            tool_choice={"type": "function", "function": {"name": ReasoningTool.tool_name}},
        ) as stream:
            async for event in stream:
                if event.type == "chunk":
                    self.streaming_generator.add_chunk(event.chunk)
            reasoning: ReasoningTool = (
                (await stream.get_final_completion()).choices[0].message.tool_calls[0].function.parsed_arguments
            )
        self.conversation.append(
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "type": "function",
                        "id": f"{self._context.iteration}-reasoning",
                        "function": {
                            "name": reasoning.tool_name,
                            "arguments": reasoning.model_dump_json(),
                        },
                    }
                ],
            }
        )
        tool_call_result = await reasoning(self._context)
        self.conversation.append(
            {"role": "tool", "content": tool_call_result, "tool_call_id": f"{self._context.iteration}-reasoning"}
        )
        self._log_reasoning(reasoning)
        return reasoning

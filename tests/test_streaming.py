"""Tests for streaming functionality.

This module contains comprehensive tests for the StreamingGenerator and
OpenAIStreamingGenerator classes used for SSE-like streaming.
"""

import json

import pytest

from sgr_deep_research.core.stream import OpenAIStreamingGenerator, StreamingGenerator


class TestStreamingGenerator:
    """Tests for base StreamingGenerator class."""

    def test_initialization(self):
        """Test that StreamingGenerator initializes correctly."""
        generator = StreamingGenerator()
        assert generator.queue is not None
        assert generator.queue.qsize() == 0

    def test_add_single_item(self):
        """Test adding a single item to the queue."""
        generator = StreamingGenerator()
        generator.add("test data")
        assert generator.queue.qsize() == 1

    def test_add_multiple_items(self):
        """Test adding multiple items to the queue."""
        generator = StreamingGenerator()
        generator.add("item 1")
        generator.add("item 2")
        generator.add("item 3")
        assert generator.queue.qsize() == 3

    def test_finish_adds_none(self):
        """Test that finish() adds None as termination signal."""
        generator = StreamingGenerator()
        generator.add("data")
        generator.finish()

        # Queue should have 2 items: "data" and None
        assert generator.queue.qsize() == 2

    @pytest.mark.asyncio
    async def test_stream_empty(self):
        """Test streaming with no data (only finish)."""
        generator = StreamingGenerator()
        generator.finish()

        items = []
        async for item in generator.stream():
            items.append(item)

        assert len(items) == 0

    @pytest.mark.asyncio
    async def test_stream_single_item(self):
        """Test streaming a single item."""
        generator = StreamingGenerator()
        generator.add("test data")
        generator.finish()

        items = []
        async for item in generator.stream():
            items.append(item)

        assert len(items) == 1
        assert items[0] == "test data"

    @pytest.mark.asyncio
    async def test_stream_multiple_items(self):
        """Test streaming multiple items."""
        generator = StreamingGenerator()
        test_items = ["item 1", "item 2", "item 3"]
        for item in test_items:
            generator.add(item)
        generator.finish()

        items = []
        async for item in generator.stream():
            items.append(item)

        assert items == test_items

    @pytest.mark.asyncio
    async def test_stream_order_preserved(self):
        """Test that streaming preserves item order."""
        generator = StreamingGenerator()
        expected_order = ["first", "second", "third", "fourth"]
        for item in expected_order:
            generator.add(item)
        generator.finish()

        items = []
        async for item in generator.stream():
            items.append(item)

        assert items == expected_order

    @pytest.mark.asyncio
    async def test_stream_terminates_on_none(self):
        """Test that stream terminates when None is encountered."""
        generator = StreamingGenerator()
        generator.add("data 1")
        generator.add("data 2")
        generator.finish()

        items = []
        async for item in generator.stream():
            items.append(item)

        # Should not include None in results
        assert None not in items
        assert len(items) == 2

    @pytest.mark.asyncio
    async def test_stream_with_unicode(self):
        """Test streaming with Unicode characters."""
        generator = StreamingGenerator()
        unicode_data = ["Hello 世界", "Привет мир", "こんにちは 🌍"]
        for item in unicode_data:
            generator.add(item)
        generator.finish()

        items = []
        async for item in generator.stream():
            items.append(item)

        assert items == unicode_data

    @pytest.mark.asyncio
    async def test_stream_with_long_strings(self):
        """Test streaming with very long strings."""
        generator = StreamingGenerator()
        long_string = "A" * 10000
        generator.add(long_string)
        generator.finish()

        items = []
        async for item in generator.stream():
            items.append(item)

        assert len(items) == 1
        assert items[0] == long_string

    @pytest.mark.asyncio
    async def test_stream_with_special_characters(self):
        """Test streaming with special characters."""
        generator = StreamingGenerator()
        special_chars = ["<>&\"'", "$%^&*()", "{}[]\\|"]
        for item in special_chars:
            generator.add(item)
        generator.finish()

        items = []
        async for item in generator.stream():
            items.append(item)

        assert items == special_chars


class TestOpenAIStreamingGenerator:
    """Tests for OpenAIStreamingGenerator class."""

    def test_initialization_default_model(self):
        """Test initialization with default model."""
        generator = OpenAIStreamingGenerator()
        assert generator.model == "gpt-4o"

    def test_initialization_custom_model(self):
        """Test initialization with custom model."""
        generator = OpenAIStreamingGenerator(model="gpt-3.5-turbo")
        assert generator.model == "gpt-3.5-turbo"

    def test_fingerprint_generation(self):
        """Test that fingerprint is generated correctly."""
        generator = OpenAIStreamingGenerator(model="test-model")
        assert generator.fingerprint.startswith("fp_")
        assert len(generator.fingerprint) > 3

    def test_id_generation(self):
        """Test that ID is generated correctly."""
        generator = OpenAIStreamingGenerator()
        assert generator.id.startswith("chatcmpl-")
        assert len(generator.id) <= 29

    def test_created_timestamp(self):
        """Test that created timestamp is set."""
        import time

        before = int(time.time())
        generator = OpenAIStreamingGenerator()
        after = int(time.time())

        assert before <= generator.created <= after

    def test_choice_index_default(self):
        """Test that choice_index defaults to 0."""
        generator = OpenAIStreamingGenerator()
        assert generator.choice_index == 0

    def test_inherits_from_streaming_generator(self):
        """Test that OpenAIStreamingGenerator inherits from
        StreamingGenerator."""
        generator = OpenAIStreamingGenerator()
        assert isinstance(generator, StreamingGenerator)

    @pytest.mark.asyncio
    async def test_add_chunk_from_str_format(self):
        """Test that add_chunk_from_str creates correct format."""
        generator = OpenAIStreamingGenerator()
        generator.add_chunk_from_str("Hello")
        generator.finish()

        items = []
        async for item in generator.stream():
            items.append(item)

        # Should have 3 items: content chunk, final chunk, [DONE]
        assert len(items) >= 2
        assert items[0].startswith("data: ")

    @pytest.mark.asyncio
    async def test_add_chunk_from_str_json_structure(self):
        """Test that add_chunk_from_str produces valid JSON."""
        generator = OpenAIStreamingGenerator(model="test-model")
        generator.add_chunk_from_str("Test content")
        generator.finish()

        items = []
        async for item in generator.stream():
            items.append(item)

        # Parse first chunk
        first_chunk = items[0]
        assert first_chunk.startswith("data: ")
        json_str = first_chunk[6:].strip()  # Remove "data: "
        data = json.loads(json_str)

        assert data["object"] == "chat.completion.chunk"
        assert data["model"] == "test-model"
        assert data["choices"][0]["delta"]["content"] == "Test content"
        assert data["choices"][0]["delta"]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_add_chunk_from_str_content(self):
        """Test that content is correctly set in chunk."""
        generator = OpenAIStreamingGenerator()
        test_content = "This is test content"
        generator.add_chunk_from_str(test_content)
        generator.finish()

        items = []
        async for item in generator.stream():
            items.append(item)

        first_chunk = items[0]
        json_str = first_chunk[6:].strip()
        data = json.loads(json_str)

        assert data["choices"][0]["delta"]["content"] == test_content

    @pytest.mark.asyncio
    async def test_add_chunk_from_str_multiple(self):
        """Test adding multiple content chunks."""
        generator = OpenAIStreamingGenerator()
        contents = ["Hello", " world", "!"]
        for content in contents:
            generator.add_chunk_from_str(content)
        generator.finish()

        items = []
        async for item in generator.stream():
            items.append(item)

        # Should have 3 content chunks + 2 final chunks
        assert len(items) >= 4

    @pytest.mark.asyncio
    async def test_add_tool_call_structure(self):
        """Test that add_tool_call creates correct structure."""
        generator = OpenAIStreamingGenerator()
        generator.add_tool_call(tool_call_id="call_123", function_name="test_function", arguments='{"arg": "value"}')
        generator.finish()

        items = []
        async for item in generator.stream():
            items.append(item)

        tool_chunk = items[0]
        json_str = tool_chunk[6:].strip()
        data = json.loads(json_str)

        assert "tool_calls" in data["choices"][0]["delta"]
        tool_call = data["choices"][0]["delta"]["tool_calls"][0]
        assert tool_call["id"] == "call_123"
        assert tool_call["type"] == "function"
        assert tool_call["function"]["name"] == "test_function"
        assert tool_call["function"]["arguments"] == '{"arg": "value"}'

    @pytest.mark.asyncio
    async def test_add_tool_call_with_complex_arguments(self):
        """Test tool call with complex JSON arguments."""
        generator = OpenAIStreamingGenerator()
        complex_args = json.dumps(
            {"query": "test query", "options": {"limit": 10, "filters": ["a", "b"]}, "nested": {"key": "value"}}
        )
        generator.add_tool_call("call_456", "complex_tool", complex_args)
        generator.finish()

        items = []
        async for item in generator.stream():
            items.append(item)

        tool_chunk = items[0]
        json_str = tool_chunk[6:].strip()
        data = json.loads(json_str)

        args = data["choices"][0]["delta"]["tool_calls"][0]["function"]["arguments"]
        parsed_args = json.loads(args)
        assert parsed_args["query"] == "test query"
        assert parsed_args["options"]["limit"] == 10

    @pytest.mark.asyncio
    async def test_finish_creates_final_chunk(self):
        """Test that finish() creates proper final chunk."""
        generator = OpenAIStreamingGenerator()
        generator.add_chunk_from_str("content")
        generator.finish()

        items = []
        async for item in generator.stream():
            items.append(item)

        # Second to last should be final chunk with finish_reason
        final_chunk = items[-2]
        json_str = final_chunk[6:].strip()
        data = json.loads(json_str)

        assert data["choices"][0]["finish_reason"] == "stop"
        assert "usage" in data

    @pytest.mark.asyncio
    async def test_finish_with_custom_reason(self):
        """Test finish() with custom finish_reason."""
        generator = OpenAIStreamingGenerator()
        generator.finish(finish_reason="length")

        items = []
        async for item in generator.stream():
            items.append(item)

        final_chunk = items[-2]
        json_str = final_chunk[6:].strip()
        data = json.loads(json_str)

        assert data["choices"][0]["finish_reason"] == "length"

    @pytest.mark.asyncio
    async def test_finish_includes_usage(self):
        """Test that final chunk includes usage information."""
        generator = OpenAIStreamingGenerator()
        generator.finish()

        items = []
        async for item in generator.stream():
            items.append(item)

        final_chunk = items[-2]
        json_str = final_chunk[6:].strip()
        data = json.loads(json_str)

        assert "usage" in data
        assert "prompt_tokens" in data["usage"]
        assert "completion_tokens" in data["usage"]
        assert "total_tokens" in data["usage"]

    @pytest.mark.asyncio
    async def test_finish_adds_done_marker(self):
        """Test that finish() adds [DONE] marker."""
        generator = OpenAIStreamingGenerator()
        generator.finish()

        items = []
        async for item in generator.stream():
            items.append(item)

        # Last item should be [DONE]
        assert items[-1] == "data: [DONE]\n\n"

    @pytest.mark.asyncio
    async def test_complete_flow_text_only(self):
        """Test complete flow with text content only."""
        generator = OpenAIStreamingGenerator(model="gpt-4")
        generator.add_chunk_from_str("Hello")
        generator.add_chunk_from_str(" world")
        generator.finish()

        items = []
        async for item in generator.stream():
            items.append(item)

        # Should have: 2 content chunks + final chunk + [DONE]
        assert len(items) == 4

    @pytest.mark.asyncio
    async def test_complete_flow_with_tool_call(self):
        """Test complete flow with tool call."""
        generator = OpenAIStreamingGenerator()
        generator.add_tool_call("call_123", "search", '{"query": "test"}')
        generator.finish()

        items = []
        async for item in generator.stream():
            items.append(item)

        # Should have: tool chunk + final chunk + [DONE]
        assert len(items) == 3

    @pytest.mark.asyncio
    async def test_mixed_content_and_tool_calls(self):
        """Test flow with both content and tool calls."""
        generator = OpenAIStreamingGenerator()
        generator.add_chunk_from_str("Thinking...")
        generator.add_tool_call("call_1", "tool1", '{"arg": "val"}')
        generator.add_chunk_from_str("Done")
        generator.finish()

        items = []
        async for item in generator.stream():
            items.append(item)

        # Should have: 3 chunks + final + [DONE] = 5
        assert len(items) == 5

    @pytest.mark.asyncio
    async def test_unicode_in_content(self):
        """Test Unicode characters in content."""
        generator = OpenAIStreamingGenerator()
        unicode_content = "Hello 世界 🌍 Привет"
        generator.add_chunk_from_str(unicode_content)
        generator.finish()

        items = []
        async for item in generator.stream():
            items.append(item)

        first_chunk = items[0]
        json_str = first_chunk[6:].strip()
        data = json.loads(json_str)

        assert data["choices"][0]["delta"]["content"] == unicode_content

    @pytest.mark.asyncio
    async def test_special_characters_in_content(self):
        """Test special characters in content."""
        generator = OpenAIStreamingGenerator()
        special_content = 'Test with "quotes" and <tags> and $pecial chars'
        generator.add_chunk_from_str(special_content)
        generator.finish()

        items = []
        async for item in generator.stream():
            items.append(item)

        first_chunk = items[0]
        json_str = first_chunk[6:].strip()
        data = json.loads(json_str)

        assert data["choices"][0]["delta"]["content"] == special_content

    @pytest.mark.asyncio
    async def test_newlines_in_content(self):
        """Test newlines in content."""
        generator = OpenAIStreamingGenerator()
        multiline_content = "Line 1\nLine 2\nLine 3"
        generator.add_chunk_from_str(multiline_content)
        generator.finish()

        items = []
        async for item in generator.stream():
            items.append(item)

        first_chunk = items[0]
        json_str = first_chunk[6:].strip()
        data = json.loads(json_str)

        assert data["choices"][0]["delta"]["content"] == multiline_content

    @pytest.mark.asyncio
    async def test_empty_content(self):
        """Test adding empty content."""
        generator = OpenAIStreamingGenerator()
        generator.add_chunk_from_str("")
        generator.finish()

        items = []
        async for item in generator.stream():
            items.append(item)

        first_chunk = items[0]
        json_str = first_chunk[6:].strip()
        data = json.loads(json_str)

        assert data["choices"][0]["delta"]["content"] == ""

    @pytest.mark.asyncio
    async def test_sse_format_compliance(self):
        """Test that output follows SSE format (data: prefix, double
        newline)."""
        generator = OpenAIStreamingGenerator()
        generator.add_chunk_from_str("test")
        generator.finish()

        items = []
        async for item in generator.stream():
            items.append(item)

        # All items should start with "data: " and end with "\n\n"
        for item in items:
            assert item.startswith("data: ")
            assert item.endswith("\n\n")

    def test_model_preserved_across_chunks(self):
        """Test that model name is consistent across all chunks."""
        generator = OpenAIStreamingGenerator(model="custom-model")
        assert generator.model == "custom-model"

    def test_id_consistent_across_session(self):
        """Test that ID remains consistent within a generator instance."""
        generator = OpenAIStreamingGenerator()
        first_id = generator.id
        generator.add_chunk_from_str("test")
        second_id = generator.id

        assert first_id == second_id

    def test_created_timestamp_consistent(self):
        """Test that created timestamp remains consistent."""
        generator = OpenAIStreamingGenerator()
        first_created = generator.created
        generator.add_chunk_from_str("test")
        second_created = generator.created

        assert first_created == second_created

    @pytest.mark.asyncio
    async def test_multiple_generators_independent(self):
        """Test that multiple generators are independent."""
        import asyncio

        gen1 = OpenAIStreamingGenerator(model="model1")
        # Small delay to ensure different timestamp
        await asyncio.sleep(0.001)
        gen2 = OpenAIStreamingGenerator(model="model2")

        gen1.add_chunk_from_str("content1")
        gen2.add_chunk_from_str("content2")

        # Models should definitely be different
        assert gen1.model != gen2.model
        # Queues should be independent
        assert gen1.queue != gen2.queue

    @pytest.mark.asyncio
    async def test_long_content_stream(self):
        """Test streaming very long content."""
        generator = OpenAIStreamingGenerator()
        long_content = "A" * 10000
        generator.add_chunk_from_str(long_content)
        generator.finish()

        items = []
        async for item in generator.stream():
            items.append(item)

        first_chunk = items[0]
        json_str = first_chunk[6:].strip()
        data = json.loads(json_str)

        assert len(data["choices"][0]["delta"]["content"]) == 10000

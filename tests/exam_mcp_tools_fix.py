#!/usr/bin/env python3
"""
Test script to verify the MCP tools serialization fix.

This script tests that:
1. MCP tools with _client attribute can be serialized
2. The _client attribute is preserved after serialization
3. Non-MCP tools continue to work correctly
"""

import json
from typing import Type
from unittest.mock import Mock, MagicMock


class MockClient:
    """Mock async client for testing."""
    async def call_tool(self, name: str, payload: dict):
        return {"result": "success"}


class MockBaseTool:
    """Mock base tool class."""
    tool_name = "base_tool"
    
    def __init__(self):
        pass


class MockMCPTool(MockBaseTool):
    """Mock MCP tool with _client attribute."""
    tool_name = "mcp_tool"
    _client = None


def mock_pydantic_function_tool(tool: Type, name: str, description: str):
    """Mock pydantic_function_tool that attempts JSON serialization."""
    # Simulate what pydantic_function_tool does - try to serialize the tool
    # In reality, pydantic_function_tool inspects the class and its attributes
    try:
        # Try to serialize all class attributes (this is what causes the real error)
        tool_dict = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {}
            }
        }
        
        # Simulate inspection of class attributes (this is where the error occurs)
        for attr_name in dir(tool):
            if not attr_name.startswith('_'):
                continue
            try:
                attr_value = getattr(tool, attr_name)
                # Try to serialize the attribute (this will fail for async objects)
                if attr_name == '_client' and attr_value is not None:
                    # This simulates the real error - trying to serialize async client
                    json.dumps({"client": str(attr_value)})  # This will fail for real async objects
                    # For our mock, we need to explicitly check if it's a MockClient
                    if isinstance(attr_value, MockClient):
                        raise TypeError(f"Object of type {type(attr_value).__name__} is not JSON serializable")
            except (AttributeError, TypeError) as e:
                if "not JSON serializable" in str(e):
                    raise
                # Ignore other attribute errors
                pass
        
        return tool_dict
    except TypeError as e:
        raise TypeError(f"Cannot serialize tool {name}: {e}")


def prepare_tools_original(tools: set) -> list:
    """Original implementation (BROKEN with MCP tools)."""
    return [mock_pydantic_function_tool(tool, tool.tool_name, "") for tool in tools]


def prepare_tools_fixed(tools: set) -> list:
    """Fixed implementation."""
    result = []
    for tool in tools:
        # Temporarily remove _client before serialization for MCP tools
        original_client = None
        if hasattr(tool, '_client'):
            original_client = getattr(tool, '_client', None)
            try:
                delattr(tool, '_client')
            except AttributeError:
                pass
        
        try:
            tool_param = mock_pydantic_function_tool(tool, tool.tool_name, "")
            result.append(tool_param)
        finally:
            # Restore _client after serialization
            if original_client is not None:
                tool._client = original_client
    
    return result


def test_original_implementation():
    """Test that original implementation fails with MCP tools."""
    print("Testing original implementation...")
    
    # Create MCP tool with async client
    mcp_tool = MockMCPTool
    mcp_tool._client = MockClient()
    
    tools = {mcp_tool}
    
    try:
        result = prepare_tools_original(tools)
        print("   UNEXPECTED: Original implementation should fail but didn't")
        return False
    except Exception as e:
        print(f"   EXPECTED: Original implementation failed as expected")
        print(f"      Error: {type(e).__name__}: {str(e)[:80]}")
        return True


def test_fixed_implementation():
    """Test that fixed implementation works with MCP tools."""
    print("\nTesting fixed implementation...")
    
    # Create MCP tool with async client
    mcp_tool = MockMCPTool
    original_client = MockClient()
    mcp_tool._client = original_client
    
    tools = {mcp_tool}
    
    try:
        result = prepare_tools_fixed(tools)
        
        # Verify result
        if not result:
            print("FAILED: No tools returned")
            return False
        
        if len(result) != 1:
            print(f"FAILED: Expected 1 tool, got {len(result)}")
            return False
        
        # Verify _client was restored
        if not hasattr(mcp_tool, '_client'):
            print("FAILED: _client attribute was not restored")
            return False
        
        if mcp_tool._client != original_client:
            print("FAILED: _client was not restored to original value")
            return False
        
        print("   PASSED: Fixed implementation works correctly")
        print(f"      Tools serialized: {len(result)}")
        print(f"      _client restored: {hasattr(mcp_tool, '_client')}")
        return True
        
    except Exception as e:
        print(f"   FAILED: Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_non_mcp_tools():
    """Test that non-MCP tools still work correctly."""
    print("\nTesting non-MCP tools...")
    
    # Create regular tool without _client
    regular_tool = MockBaseTool
    tools = {regular_tool}
    
    try:
        result = prepare_tools_fixed(tools)
        
        if not result:
            print("   FAILED: No tools returned")
            return False
        
        if len(result) != 1:
            print(f"   FAILED: Expected 1 tool, got {len(result)}")
            return False
        
        print("   PASSED: Non-MCP tools work correctly")
        return True
        
    except Exception as e:
        print(f"   FAILED: Unexpected error: {e}")
        return False


def test_mixed_tools():
    """Test that mixed MCP and non-MCP tools work together."""
    print("\nTesting mixed MCP and non-MCP tools...")
    
    # Create both types of tools
    mcp_tool = MockMCPTool
    mcp_tool._client = MockClient()
    
    regular_tool = MockBaseTool
    
    tools = {mcp_tool, regular_tool}
    
    try:
        result = prepare_tools_fixed(tools)
        
        if not result:
            print("FAILED: No tools returned")
            return False
        
        if len(result) != 2:
            print(f"FAILED: Expected 2 tools, got {len(result)}")
            return False
        
        # Verify MCP tool still has _client
        if not hasattr(mcp_tool, '_client'):
            print("FAILED: MCP tool lost _client attribute")
            return False
        
        print("   PASSED: Mixed tools work correctly")
        print(f"      Tools serialized: {len(result)}")
        return True
        
    except Exception as e:
        print(f"   FAILED: Unexpected error: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 70)
    print("Testing MCP Tools Serialization Fix")
    print("=" * 70)
    
    tests = [
        ("Original Implementation (Should Fail)", test_original_implementation),
        ("Fixed Implementation", test_fixed_implementation),
        ("Non-MCP Tools", test_non_mcp_tools),
        ("Mixed Tools", test_mixed_tools),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\nTest '{name}' crashed: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 70)
    print("Test Results Summary")
    print("=" * 70)
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for name, passed in results:
        status = "PASSED" if passed else "FAILED"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\nAll tests passed")
        return 0
    else:
        print(f"\n{total_count - passed_count} test(s) failed")
        return 1


if __name__ == "__main__":
    exit(main())

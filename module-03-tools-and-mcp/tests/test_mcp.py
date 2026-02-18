"""
Module 3 Testleri - Tool Use & MCP
Çalıştırma: cd module-03-tools-and-mcp && python -m pytest tests/ -v
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


class TestSearchTool:
    def test_search_v1(self):
        from mcp_server.tools.search import search_v1
        results = search_v1("Python")
        assert len(results) > 0
        assert all("python" in r["title"].lower() or "python" in r["content"].lower() for r in results)
    
    def test_search_v2_with_filter(self):
        from mcp_server.tools.search import search_v2
        result = search_v2("Python", category="tutorial")
        assert result["total"] >= 1
        assert all(r["category"] == "tutorial" for r in result["results"])
    
    def test_search_v2_max_results(self):
        from mcp_server.tools.search import search_v2
        result = search_v2("Python", max_results=1)
        assert result["returned"] <= 1


class TestCodeExec:
    def test_simple_execution(self):
        from mcp_server.tools.code_exec import execute_code
        result = execute_code("print(2 + 3)")
        assert result["success"] is True
        assert "5" in result["output"]
    
    def test_security_block(self):
        from mcp_server.tools.code_exec import execute_code
        result = execute_code("import os")
        assert result["success"] is False
        assert "güvenlik" in result["error"].lower() or "Güvenlik" in result["error"]
    
    def test_error_handling(self):
        from mcp_server.tools.code_exec import execute_code
        result = execute_code("print(1/0)")
        assert result["success"] is False
        assert "ZeroDivisionError" in result["error"]


class TestFileTools:
    def test_write_and_read(self):
        from mcp_server.tools.file_write import file_write, file_read, VIRTUAL_FILESYSTEM
        VIRTUAL_FILESYSTEM.clear()
        
        file_write("test.txt", "Hello")
        result = file_read("test.txt")
        assert result["content"] == "Hello"
    
    def test_read_nonexistent(self):
        from mcp_server.tools.file_write import file_read
        result = file_read("nonexistent.txt")
        assert "error" in result


class TestToolRegistry:
    def test_register_and_call(self):
        from mcp_server.registry import ToolRegistry
        from shared.schemas.tool import create_tool_schema
        
        registry = ToolRegistry()
        schema = create_tool_schema("test", "Test tool", {"x": {"type": "string", "description": "x"}}, ["x"])
        registry.register("test", "1.0", lambda x: f"result: {x}", schema)
        
        assert registry.get_tool("test") is not None
    
    def test_version_management(self):
        from mcp_server.registry import ToolRegistry
        from shared.schemas.tool import create_tool_schema
        
        registry = ToolRegistry()
        schema = create_tool_schema("tool", "Tool", {}, [])
        registry.register("tool", "1.0", lambda: "v1", schema, is_default=False)
        registry.register("tool", "2.0", lambda: "v2", schema, is_default=True)
        
        entry = registry.get_tool("tool")  # Varsayılan
        assert entry.version == "2.0"
        
        entry = registry.get_tool("tool", "1.0")
        assert entry.version == "1.0"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

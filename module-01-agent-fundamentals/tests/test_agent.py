"""
Module 1 Testleri
==================
Agent temelleri için mini değerlendirmeler (eval).

Çalıştırma:
    cd module-01-agent-fundamentals
    python -m pytest tests/ -v

Bu testler şunları kontrol eder:
1. Tool'lar doğru çalışıyor mu?
2. MCP Server tool'ları doğru kaydediyor mu?
3. Agent durumu (state) doğru güncelleniyor mu?
4. Planner adım üretiyor mu?
"""

import sys
import os
import asyncio
import pytest

# Path ayarları
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


# ============================================================
# Tool Testleri
# ============================================================

class TestEchoTool:
    """Echo tool testleri."""
    
    def test_echo_basic(self):
        """Echo tool basit mesajı döndürmeli."""
        from mcp.tools.echo import echo
        
        result = echo("Merhaba")
        assert result == "Yankı: Merhaba"
    
    def test_echo_empty(self):
        """Echo tool boş mesajı kabul etmeli."""
        from mcp.tools.echo import echo
        
        result = echo("")
        assert result == "Yankı: "
    
    def test_echo_turkish_chars(self):
        """Echo tool Türkçe karakterleri desteklemeli."""
        from mcp.tools.echo import echo
        
        result = echo("Şükrü öğretmen çığlık attı")
        assert "Şükrü" in result
    
    def test_echo_schema_exists(self):
        """Echo tool'un geçerli bir şeması olmalı."""
        from mcp.tools.echo import ECHO_SCHEMA
        
        assert ECHO_SCHEMA.name == "echo"
        assert "message" in ECHO_SCHEMA.parameters
        assert "message" in ECHO_SCHEMA.required


class TestTimeTool:
    """Time tool testleri."""
    
    def test_time_utc(self):
        """Time tool UTC saatini döndürmeli."""
        from mcp.tools.time_tool import get_time
        
        result = get_time()
        assert "time" in result
        assert "date" in result
        assert result["timezone"] == "UTC"
    
    def test_time_istanbul(self):
        """Time tool İstanbul saatini döndürmeli."""
        from mcp.tools.time_tool import get_time
        
        result = get_time("Europe/Istanbul")
        assert result["timezone"] == "Europe/Istanbul"
        assert result["utc_offset"] == "+03:00"
    
    def test_time_invalid_timezone(self):
        """Geçersiz timezone hata döndürmeli."""
        from mcp.tools.time_tool import get_time
        
        result = get_time("Invalid/Zone")
        assert "error" in result
    
    def test_time_schema_exists(self):
        """Time tool'un geçerli bir şeması olmalı."""
        from mcp.tools.time_tool import GET_TIME_SCHEMA
        
        assert GET_TIME_SCHEMA.name == "get_time"
        assert len(GET_TIME_SCHEMA.description) > 10


# ============================================================
# MCP Server Testleri
# ============================================================

class TestMCPServer:
    """MCP Server testleri."""
    
    def test_server_creation(self):
        """Server oluşturulabilmeli."""
        from mcp.server import create_server
        
        server = create_server()
        assert server is not None
        assert server.name == "module-01-server"
    
    def test_server_has_tools(self):
        """Server'da tool'lar kayıtlı olmalı."""
        from mcp.server import create_server
        
        server = create_server()
        assert "echo" in server.tools
        assert "get_time" in server.tools
    
    def test_server_list_tools(self):
        """Server tool listesi döndürebilmeli."""
        from mcp.server import create_server
        
        server = create_server()
        tools = server.list_tools()
        
        assert len(tools) == 2
        tool_names = [t["name"] for t in tools]
        assert "echo" in tool_names
        assert "get_time" in tool_names
    
    @pytest.mark.asyncio
    async def test_server_call_echo(self):
        """Server echo tool'unu çağırabilmeli."""
        from mcp.server import create_server
        
        server = create_server()
        result = await server.call_tool("echo", {"message": "test"})
        
        assert result["success"] is True
        assert "Yankı: test" in result["result"]
    
    @pytest.mark.asyncio
    async def test_server_call_nonexistent(self):
        """Olmayan tool çağrısı hata döndürmeli."""
        from mcp.server import create_server
        
        server = create_server()
        result = await server.call_tool("nonexistent", {})
        
        assert result["success"] is False
        assert "error" in result
    
    def test_server_openai_format(self):
        """Server OpenAI formatında şema döndürebilmeli."""
        from mcp.server import create_server
        
        server = create_server()
        schemas = server.get_openai_tools()
        
        assert len(schemas) == 2
        assert schemas[0]["type"] == "function"
        assert "function" in schemas[0]


# ============================================================
# Agent State Testleri
# ============================================================

class TestAgentState:
    """Agent durumu testleri."""
    
    def test_initial_state(self):
        """Başlangıç durumu doğru olmalı."""
        from agent.loop import AgentState
        
        state = AgentState()
        assert state.status == "idle"
        assert state.current_step == 0
        assert state.final_answer is None
    
    def test_state_with_task(self):
        """Görev atanabilmeli."""
        from agent.loop import AgentState
        
        state = AgentState(task="Test görevi")
        assert state.task == "Test görevi"


# ============================================================
# Planner Testleri
# ============================================================

class TestPlanner:
    """Planner testleri."""
    
    def test_simple_decompose(self):
        """Basit planlama adım üretmeli."""
        from agent.planner import SimplePlanner
        
        planner = SimplePlanner(available_tools=["get_time", "echo"])
        steps = planner.decompose_simple("Saati öğren ve bana söyle")
        
        assert len(steps) >= 1
    
    def test_decompose_with_tool_guess(self):
        """Planner doğru tool'u tahmin etmeli."""
        from agent.planner import SimplePlanner
        
        planner = SimplePlanner(available_tools=["get_time", "echo"])
        steps = planner.decompose_simple("Saat kaç öğren")
        
        # "saat" kelimesi get_time tool'una eşleşmeli
        tool_steps = [s for s in steps if s.tool_needed == "get_time"]
        assert len(tool_steps) >= 1


# ============================================================
# Shared Module Testleri
# ============================================================

class TestSharedModules:
    """Shared modül testleri."""
    
    def test_tool_schema_creation(self):
        """Tool şeması oluşturulabilmeli."""
        from shared.schemas.tool import create_tool_schema
        
        schema = create_tool_schema(
            name="test_tool",
            description="Test tool",
            parameters={"param1": {"type": "string", "description": "Test param"}},
            required=["param1"],
        )
        
        assert schema.name == "test_tool"
        assert "param1" in schema.parameters
    
    def test_tool_schema_validation(self):
        """Tool şeması parametre doğrulama yapabilmeli."""
        from shared.schemas.tool import create_tool_schema
        
        schema = create_tool_schema(
            name="test",
            description="Test",
            parameters={"name": {"type": "string", "description": "İsim"}},
            required=["name"],
        )
        
        # Geçerli parametreler
        valid, error = schema.validate_args({"name": "Test"})
        assert valid is True
        
        # Eksik zorunlu parametre
        valid, error = schema.validate_args({})
        assert valid is False
        assert "name" in error
    
    def test_cost_tracker(self):
        """CostTracker maliyet hesaplayabilmeli."""
        from shared.telemetry.cost_tracker import CostTracker
        
        tracker = CostTracker(budget_limit=1.0)
        
        cost = tracker.add_usage(
            input_tokens=1000,
            output_tokens=500,
            model="gpt-4o-mini",
        )
        
        assert cost > 0
        assert tracker.total_calls == 1
        assert tracker.total_cost == cost
        assert not tracker.is_over_budget()
    
    def test_cost_tracker_budget(self):
        """CostTracker bütçe aşımını tespit etmeli."""
        from shared.telemetry.cost_tracker import CostTracker
        
        tracker = CostTracker(budget_limit=0.0001)
        
        # Çok fazla token ekle
        tracker.add_usage(input_tokens=100000, output_tokens=50000)
        
        assert tracker.is_over_budget()
    
    def test_message_creation(self):
        """Mesajlar oluşturulabilmeli."""
        from shared.schemas.message import Message, Role
        
        msg = Message.user("Merhaba!")
        assert msg.role == Role.USER
        assert msg.content == "Merhaba!"
        
        d = msg.to_dict()
        assert d["role"] == "user"
        assert d["content"] == "Merhaba!"


# ─────────────────────────────────────────
# Doğrudan çalıştırma
# ─────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

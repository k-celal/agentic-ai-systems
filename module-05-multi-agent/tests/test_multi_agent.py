"""
Module 5 Testleri
==================
Multi-Agent sistemi için testler.

Çalıştırma:
    cd module-05-multi-agent
    python -m pytest tests/ -v

Bu testler şunları kontrol eder:
1. BaseAgent soyut sınıfı doğru çalışıyor mu?
2. Her agent rolü (Planner, Researcher, Critic, Synthesizer) oluşturulabiliyor mu?
3. SharedMemory tool'u doğru çalışıyor mu?
4. Orchestrator mesaj akışını doğru yönetiyor mu?
5. AgentMessage doğru formatta oluşturuluyor mu?
"""

import sys
import os
import asyncio
import pytest

# Path ayarları
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


# ============================================================
# BaseAgent Testleri
# ============================================================

class TestBaseAgent:
    """BaseAgent soyut sınıf testleri."""
    
    def test_cannot_instantiate_directly(self):
        """BaseAgent doğrudan oluşturulamaz (soyut sınıf)."""
        from agents.base_agent import BaseAgent
        
        with pytest.raises(TypeError):
            # Soyut sınıftan doğrudan nesne oluşturulamaz
            BaseAgent(name="test", role="Test")
    
    def test_subclass_creation(self):
        """Alt sınıf oluşturulabilir."""
        from agents.base_agent import BaseAgent, AgentResult
        
        class TestAgent(BaseAgent):
            def _build_system_prompt(self):
                return "Test prompt"
            
            async def process(self, input_data):
                return AgentResult(
                    agent_name=self.name,
                    agent_role=self.role,
                    content="Test çıktısı",
                )
        
        agent = TestAgent(name="test", role="Test Agent")
        assert agent.name == "test"
        assert agent.role == "Test Agent"
        assert agent.system_prompt == "Test prompt"
    
    def test_agent_info(self):
        """Agent bilgileri doğru döndürülmeli."""
        from agents.base_agent import BaseAgent, AgentResult
        
        class TestAgent(BaseAgent):
            def _build_system_prompt(self):
                return "Test prompt"
            
            async def process(self, input_data):
                return AgentResult(
                    agent_name=self.name,
                    agent_role=self.role,
                    content="Test",
                )
        
        agent = TestAgent(name="my_agent", role="Benim Agent")
        info = agent.get_info()
        
        assert info["name"] == "my_agent"
        assert info["role"] == "Benim Agent"
        assert info["class"] == "TestAgent"
        assert info["system_prompt_length"] > 0
    
    def test_agent_repr(self):
        """Agent'ın string gösterimi doğru olmalı."""
        from agents.base_agent import BaseAgent, AgentResult
        
        class TestAgent(BaseAgent):
            def _build_system_prompt(self):
                return "Test"
            
            async def process(self, input_data):
                return AgentResult(
                    agent_name=self.name,
                    agent_role=self.role,
                    content="Test",
                )
        
        agent = TestAgent(name="test", role="Test")
        repr_str = repr(agent)
        assert "TestAgent" in repr_str
        assert "test" in repr_str


class TestAgentResult:
    """AgentResult veri sınıfı testleri."""
    
    def test_default_values(self):
        """Varsayılan değerler doğru olmalı."""
        from agents.base_agent import AgentResult
        
        result = AgentResult(
            agent_name="test",
            agent_role="Test",
            content="İçerik",
        )
        
        assert result.success is True
        assert result.error is None
        assert result.metadata == {}
    
    def test_failed_result(self):
        """Başarısız sonuç oluşturulabilmeli."""
        from agents.base_agent import AgentResult
        
        result = AgentResult(
            agent_name="test",
            agent_role="Test",
            content="",
            success=False,
            error="Bir hata oluştu",
        )
        
        assert result.success is False
        assert result.error == "Bir hata oluştu"


# ============================================================
# Agent Rol Testleri
# ============================================================

class TestPlannerAgent:
    """PlannerAgent testleri."""
    
    def test_creation(self):
        """PlannerAgent oluşturulabilmeli."""
        from agents.planner import PlannerAgent
        
        planner = PlannerAgent()
        assert planner.name == "planner"
        assert planner.role == "Görev Planlayıcı"
        assert planner.temperature == 0.3
    
    def test_system_prompt(self):
        """System prompt planlama odaklı olmalı."""
        from agents.planner import PlannerAgent
        
        planner = PlannerAgent()
        prompt = planner.system_prompt
        
        assert "planlayıcı" in prompt.lower()
        assert "adım" in prompt.lower()
        assert len(prompt) > 50
    
    @pytest.mark.asyncio
    async def test_process(self):
        """Process metodu AgentResult döndürmeli."""
        from agents.planner import PlannerAgent
        
        planner = PlannerAgent()
        result = await planner.process("Basit bir test görevi")
        
        assert result.agent_name == "planner"
        assert result.agent_role == "Görev Planlayıcı"
        assert len(result.content) > 0


class TestResearcherAgent:
    """ResearcherAgent testleri."""
    
    def test_creation(self):
        """ResearcherAgent oluşturulabilmeli."""
        from agents.researcher import ResearcherAgent
        
        researcher = ResearcherAgent()
        assert researcher.name == "researcher"
        assert researcher.role == "Araştırmacı"
        assert researcher.temperature == 0.7
    
    def test_system_prompt(self):
        """System prompt araştırma odaklı olmalı."""
        from agents.researcher import ResearcherAgent
        
        researcher = ResearcherAgent()
        prompt = researcher.system_prompt
        
        assert "araştırmacı" in prompt.lower()
        assert len(prompt) > 50


class TestCriticAgent:
    """CriticAgent testleri."""
    
    def test_creation(self):
        """CriticAgent oluşturulabilmeli."""
        from agents.critic import CriticAgent
        
        critic = CriticAgent()
        assert critic.name == "critic"
        assert critic.role == "Eleştirmen"
        assert critic.temperature == 0.3
    
    def test_system_prompt(self):
        """System prompt eleştiri odaklı olmalı."""
        from agents.critic import CriticAgent
        
        critic = CriticAgent()
        prompt = critic.system_prompt
        
        assert "eleştirmen" in prompt.lower() or "kalite" in prompt.lower()
        assert len(prompt) > 50


class TestSynthesizerAgent:
    """SynthesizerAgent testleri."""
    
    def test_creation(self):
        """SynthesizerAgent oluşturulabilmeli."""
        from agents.synthesizer import SynthesizerAgent
        
        synthesizer = SynthesizerAgent()
        assert synthesizer.name == "synthesizer"
        assert synthesizer.role == "Sentezci"
        assert synthesizer.temperature == 0.5
    
    def test_system_prompt(self):
        """System prompt sentez odaklı olmalı."""
        from agents.synthesizer import SynthesizerAgent
        
        synthesizer = SynthesizerAgent()
        prompt = synthesizer.system_prompt
        
        assert "sentezci" in prompt.lower() or "birleştir" in prompt.lower()
        assert len(prompt) > 50


# ============================================================
# SharedMemory Tool Testleri
# ============================================================

class TestSharedMemory:
    """SharedMemory tool testleri."""
    
    def test_store_and_retrieve(self):
        """Veri kaydedilip okunabilmeli."""
        from mcp.tools.shared_memory import SharedMemoryTool
        
        memory = SharedMemoryTool()
        
        # Kaydet
        result = memory.store("test_key", "test_value")
        assert result["success"] is True
        assert result["key"] == "test_key"
        
        # Oku
        result = memory.retrieve("test_key")
        assert result["success"] is True
        assert result["value"] == "test_value"
    
    def test_retrieve_nonexistent(self):
        """Olmayan anahtar hata döndürmeli."""
        from mcp.tools.shared_memory import SharedMemoryTool
        
        memory = SharedMemoryTool()
        result = memory.retrieve("nonexistent")
        
        assert result["success"] is False
        assert "bulunamadı" in result["error"]
    
    def test_store_dict(self):
        """Dict değer kaydedilebilmeli (JSON'a çevrilir)."""
        from mcp.tools.shared_memory import SharedMemoryTool
        import json
        
        memory = SharedMemoryTool()
        
        data = {"name": "test", "value": 42}
        memory.store("data", data)
        
        result = memory.retrieve("data")
        assert result["success"] is True
        
        # JSON string olarak kaydedilmeli
        parsed = json.loads(result["value"])
        assert parsed["name"] == "test"
        assert parsed["value"] == 42
    
    def test_list_keys(self):
        """Tüm anahtarlar listelenebilmeli."""
        from mcp.tools.shared_memory import SharedMemoryTool
        
        memory = SharedMemoryTool()
        memory.store("key1", "value1")
        memory.store("key2", "value2")
        memory.store("key3", "value3")
        
        result = memory.list_keys()
        assert result["success"] is True
        assert result["count"] == 3
        assert "key1" in result["keys"]
        assert "key2" in result["keys"]
        assert "key3" in result["keys"]
    
    def test_clear(self):
        """Bellek temizlenebilmeli."""
        from mcp.tools.shared_memory import SharedMemoryTool
        
        memory = SharedMemoryTool()
        memory.store("key1", "value1")
        memory.store("key2", "value2")
        
        result = memory.clear()
        assert result["success"] is True
        assert result["cleared_keys"] == 2
        
        # Temizleme sonrası kontrol
        result = memory.list_keys()
        assert result["count"] == 0
    
    def test_overwrite(self):
        """Aynı anahtara tekrar yazılabilmeli (güncelleme)."""
        from mcp.tools.shared_memory import SharedMemoryTool
        
        memory = SharedMemoryTool()
        memory.store("key", "old_value")
        memory.store("key", "new_value")
        
        result = memory.retrieve("key")
        assert result["value"] == "new_value"
    
    def test_access_log(self):
        """Erişim geçmişi tutulmalı."""
        from mcp.tools.shared_memory import SharedMemoryTool
        
        memory = SharedMemoryTool()
        memory.store("key", "value")
        memory.retrieve("key")
        
        log = memory.get_access_log()
        assert len(log) == 2
        assert log[0]["action"] == "store"
        assert log[1]["action"] == "retrieve"
    
    def test_schema_exists(self):
        """Tool şemaları tanımlı olmalı."""
        from mcp.tools.shared_memory import ALL_SCHEMAS, ALL_OPENAI_SCHEMAS
        
        assert len(ALL_SCHEMAS) == 4
        assert len(ALL_OPENAI_SCHEMAS) == 4
        
        schema_names = [s.name for s in ALL_SCHEMAS]
        assert "shared_memory_store" in schema_names
        assert "shared_memory_retrieve" in schema_names
        assert "shared_memory_list_keys" in schema_names
        assert "shared_memory_clear" in schema_names


# ============================================================
# Orchestrator Testleri
# ============================================================

class TestAgentMessage:
    """AgentMessage testleri."""
    
    def test_creation(self):
        """AgentMessage oluşturulabilmeli."""
        from orchestration.orchestrator import AgentMessage
        
        msg = AgentMessage(
            sender="planner",
            receiver="researcher",
            content="Test içerik",
            message_type="plan",
        )
        
        assert msg.sender == "planner"
        assert msg.receiver == "researcher"
        assert msg.content == "Test içerik"
        assert msg.message_type == "plan"
        assert len(msg.timestamp) > 0
    
    def test_to_dict(self):
        """AgentMessage dict'e çevrilebilmeli."""
        from orchestration.orchestrator import AgentMessage
        
        msg = AgentMessage(
            sender="critic",
            receiver="synthesizer",
            content="Eleştiri içeriği",
            message_type="critique",
        )
        
        d = msg.to_dict()
        assert d["sender"] == "critic"
        assert d["receiver"] == "synthesizer"
        assert d["content"] == "Eleştiri içeriği"
        assert d["message_type"] == "critique"
    
    def test_str_representation(self):
        """AgentMessage okunabilir string'e çevrilebilmeli."""
        from orchestration.orchestrator import AgentMessage
        
        msg = AgentMessage(
            sender="planner",
            receiver="researcher",
            content="Uzun bir plan içeriği " * 10,
            message_type="plan",
        )
        
        s = str(msg)
        assert "planner" in s
        assert "researcher" in s
        assert "plan" in s


class TestOrchestrator:
    """Orchestrator testleri."""
    
    def test_creation(self):
        """Orchestrator oluşturulabilmeli."""
        from orchestration.orchestrator import Orchestrator
        from agents.planner import PlannerAgent
        from agents.researcher import ResearcherAgent
        
        agents = [PlannerAgent(), ResearcherAgent()]
        orchestrator = Orchestrator(agents=agents)
        
        assert "planner" in orchestrator.agents
        assert "researcher" in orchestrator.agents
        assert orchestrator.pipeline_order == ["planner", "researcher"]
    
    def test_message_bus_initially_empty(self):
        """Mesaj veriyolu başlangıçta boş olmalı."""
        from orchestration.orchestrator import Orchestrator
        from agents.planner import PlannerAgent
        
        orchestrator = Orchestrator(agents=[PlannerAgent()])
        assert len(orchestrator.message_bus) == 0
    
    def test_add_message(self):
        """Mesaj veriyoluna mesaj eklenebilmeli."""
        from orchestration.orchestrator import Orchestrator
        from agents.planner import PlannerAgent
        
        orchestrator = Orchestrator(agents=[PlannerAgent()])
        
        msg = orchestrator._add_message(
            sender="test_sender",
            receiver="test_receiver",
            content="Test mesaj",
            message_type="info",
        )
        
        assert len(orchestrator.message_bus) == 1
        assert msg.sender == "test_sender"
        assert msg.receiver == "test_receiver"
    
    @pytest.mark.asyncio
    async def test_run_pipeline(self):
        """Pipeline çalıştırılabilmeli."""
        from orchestration.orchestrator import Orchestrator
        from agents.planner import PlannerAgent
        from agents.researcher import ResearcherAgent
        from agents.critic import CriticAgent
        from agents.synthesizer import SynthesizerAgent
        
        agents = [
            PlannerAgent(),
            ResearcherAgent(),
            CriticAgent(),
            SynthesizerAgent(),
        ]
        
        orchestrator = Orchestrator(agents=agents)
        result = await orchestrator.run_pipeline("Basit bir test görevi")
        
        # Pipeline çalışmalı
        assert result.task == "Basit bir test görevi"
        assert result.duration_seconds > 0
        
        # Mesajlar kaydedilmeli
        assert len(result.messages) > 0
        
        # İlk mesaj kullanıcıdan gelmeli
        assert result.messages[0].sender == "kullanıcı"
        assert result.messages[0].message_type == "task"
    
    def test_get_message_history(self):
        """Mesaj geçmişi döndürülebilmeli."""
        from orchestration.orchestrator import Orchestrator
        from agents.planner import PlannerAgent
        
        orchestrator = Orchestrator(agents=[PlannerAgent()])
        orchestrator._add_message("a", "b", "test", "info")
        
        history = orchestrator.get_message_history()
        assert len(history) == 1
        assert history[0]["sender"] == "a"
        assert history[0]["receiver"] == "b"


class TestPipelineResult:
    """PipelineResult testleri."""
    
    def test_default_values(self):
        """Varsayılan değerler doğru olmalı."""
        from orchestration.orchestrator import PipelineResult
        
        result = PipelineResult(task="Test")
        assert result.task == "Test"
        assert result.final_output == ""
        assert result.success is False
        assert result.messages == []
        assert result.agent_results == {}
        assert result.error is None
        assert result.duration_seconds == 0.0


# ============================================================
# Shared Module Testleri (Module 5 bağlamında)
# ============================================================

class TestSharedModuleIntegration:
    """Shared modül entegrasyon testleri."""
    
    def test_llm_client_import(self):
        """LLMClient import edilebilmeli."""
        from shared.llm.client import LLMClient
        
        client = LLMClient()
        assert client is not None
    
    def test_message_schema_import(self):
        """Message şeması import edilebilmeli."""
        from shared.schemas.message import Message, Role
        
        msg = Message.user("Test mesajı")
        assert msg.role == Role.USER
    
    def test_tool_schema_import(self):
        """Tool şeması import edilebilmeli."""
        from shared.schemas.tool import create_tool_schema
        
        schema = create_tool_schema(
            name="test",
            description="Test tool",
            parameters={"param": {"type": "string", "description": "Test"}},
            required=["param"],
        )
        assert schema.name == "test"


# ─────────────────────────────────────────
# Doğrudan çalıştırma
# ─────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

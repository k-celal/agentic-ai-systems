"""
Agent Loop - Agent Çalışma Döngüsü
====================================
Bu dosya, bir agent'ın kalbini oluşturur: çalışma döngüsü.

Agent Döngüsü Nedir?
--------------------
Bir agent, şu adımları tekrarlar:
1. DÜŞÜN (Think)    → Görevi analiz et
2. KARAR VER (Decide) → Ne yapacağına karar ver
3. YÜRÜT (Act)      → Tool çağır veya cevap ver
4. GÖZLEMLE (Observe) → Sonucu değerlendir

Bu döngü, görev tamamlanana veya limit aşılana kadar devam eder.

Kullanım:
    from agent.loop import AgentLoop
    
    agent = AgentLoop(tools=my_tools)
    result = await agent.run("İstanbul'da saat kaç?")
    print(result)
"""

import sys
import os
import json
import asyncio
from dataclasses import dataclass, field
from typing import Optional

# Proje kök dizinini Python path'ine ekle
# Bu sayede 'shared' modülünü import edebiliriz
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from shared.llm.client import LLMClient, LLMResponse
from shared.telemetry.logger import get_logger, AgentTracer
from shared.telemetry.cost_tracker import CostTracker
from shared.utils.helpers import format_tool_result


# ============================================================
# Agent Durumu (State)
# ============================================================

@dataclass
class AgentState:
    """
    Agent'ın mevcut durumunu tutar.
    
    Neden durum takibi?
    - Agent döngüde çalışır, her adımda durumu güncellenir
    - Kaç döngü geçti? Görev bitti mi? Hata var mı?
    - Bu bilgiler döngünün ne yapacağına karar vermesini sağlar
    """
    task: str = ""                          # Kullanıcının verdiği görev
    messages: list = field(default_factory=list)  # Mesaj geçmişi
    current_step: int = 0                   # Şu anki adım numarası
    status: str = "idle"                    # idle, running, completed, failed
    final_answer: Optional[str] = None      # Agent'ın son cevabı
    tool_results: list = field(default_factory=list)  # Tool sonuçları geçmişi


# ============================================================
# Agent Döngüsü (Ana Sınıf)
# ============================================================

class AgentLoop:
    """
    Agent'ın çalışma döngüsü.
    
    Bu sınıf, agent'ın "beyni"dir:
    1. Kullanıcıdan bir görev alır
    2. LLM'e sorarak plan yapar
    3. Gerekirse tool çağırır
    4. Sonucu değerlendirir
    5. Görev tamamlanana kadar tekrarlar
    
    Kullanım:
        # Tool'ları tanımla
        tools = {
            "echo": echo_function,
            "get_time": time_function,
        }
        
        # Tool şemalarını tanımla (LLM'in tool'ları bilmesi için)
        tool_schemas = [echo_schema, time_schema]
        
        # Agent'ı oluştur
        agent = AgentLoop(
            tools=tools,
            tool_schemas=tool_schemas,
            max_loops=5,
        )
        
        # Görevi çalıştır
        result = await agent.run("Bana şu anki saati söyle")
        print(result.final_answer)
    """
    
    def __init__(
        self,
        tools: dict = None,
        tool_schemas: list = None,
        max_loops: int = 5,
        system_prompt: str = None,
        model: str = None,
    ):
        """
        Agent döngüsünü başlat.
        
        Parametreler:
            tools: Kullanılabilir tool fonksiyonları {"isim": fonksiyon}
            tool_schemas: Tool şemaları (OpenAI formatında)
            max_loops: Maksimum döngü sayısı (sonsuz döngü koruması!)
            system_prompt: Agent'a verilen talimat
            model: Kullanılacak LLM modeli
        """
        self.tools = tools or {}
        self.tool_schemas = tool_schemas or []
        self.max_loops = max_loops
        self.model = model
        
        # Varsayılan system prompt
        self.system_prompt = system_prompt or (
            "Sen yardımcı bir AI agent'sın. Sana verilen görevi tamamlamak için "
            "tool'ları kullanabilirsin. Her adımda ne yapacağını düşün ve en uygun "
            "tool'u çağır. Görev tamamlandığında son cevabını ver.\n\n"
            "Kurallar:\n"
            "1. Tool çağırmadan önce neden çağırdığını düşün\n"
            "2. Tool sonucunu değerlendir\n"
            "3. Görev tamamlandıysa son cevabını ver\n"
            "4. Emin değilsen daha fazla bilgi topla"
        )
        
        # LLM istemcisi
        self.llm = LLMClient(model=model)
        
        # Loglama ve izleme
        self.logger = get_logger("agent.loop")
        self.tracer = AgentTracer("module-01-agent")
        self.cost_tracker = CostTracker(budget_limit=0.50)
    
    async def run(self, task: str) -> AgentState:
        """
        Bir görevi çalıştır.
        
        Bu fonksiyon agent döngüsünü başlatır ve görev
        tamamlanana kadar çalıştırır.
        
        Parametreler:
            task: Kullanıcının verdiği görev
        
        Döndürür:
            AgentState: Agent'ın son durumu
        
        Örnek:
            result = await agent.run("Şu anki saati söyle")
            if result.status == "completed":
                print(f"Cevap: {result.final_answer}")
            else:
                print(f"Başarısız: {result.status}")
        """
        # Agent durumunu başlat
        state = AgentState(task=task, status="running")
        
        # İzlemeyi başlat
        self.tracer.start_task(task)
        
        # Mesaj geçmişini başlat
        state.messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": task},
        ]
        
        self.logger.info(f"🚀 Görev başlatıldı: {task}")
        
        # ═══════════════════════════════════════
        # ANA DÖNGÜ — Agent'ın kalbi burada atar
        # ═══════════════════════════════════════
        
        for step in range(self.max_loops):
            state.current_step = step + 1
            self.logger.info(f"\n{'─'*40}")
            self.logger.info(f"📍 Adım {state.current_step}/{self.max_loops}")
            
            # ─── 1. DÜŞÜN ve KARAR VER ───
            # LLM'e mevcut durumu göster, ne yapacağına karar versin
            self.logger.info("🧠 Düşünüyor...")
            
            response = await self.llm.chat_with_messages(
                messages=state.messages,
                tools=self.tool_schemas if self.tool_schemas else None,
            )
            
            # Maliyet takibi
            self.cost_tracker.add_usage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                model=response.model,
                label=f"step_{state.current_step}",
            )
            
            # ─── 2. YÜRÜT ───
            if response.has_tool_calls:
                # LLM bir tool çağırmak istiyor
                for tool_call in response.tool_calls:
                    self.logger.info(f"🔧 Tool çağrılıyor: {tool_call.name}({tool_call.arguments})")
                    self.tracer.log_tool_call(tool_call.name, tool_call.arguments)
                    
                    # Tool'u çalıştır
                    tool_result = await self._execute_tool(tool_call.name, tool_call.arguments)
                    
                    self.logger.info(f"📥 Tool sonucu: {tool_result[:100]}")
                    self.tracer.log_tool_result(tool_call.name, tool_result)
                    
                    # Tool sonucunu geçmişe ekle
                    state.messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": tool_call.name,
                                "arguments": json.dumps(tool_call.arguments),
                            },
                        }],
                    })
                    state.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_result,
                    })
                    
                    state.tool_results.append({
                        "tool": tool_call.name,
                        "args": tool_call.arguments,
                        "result": tool_result,
                    })
            
            elif response.content:
                # LLM bir metin cevabı verdi → Görev tamamlanmış olabilir
                self.logger.info(f"💬 Cevap: {response.content[:200]}")
                self.tracer.log_response(response.content)
                
                state.final_answer = response.content
                state.status = "completed"
                
                # Mesaj geçmişine ekle
                state.messages.append({
                    "role": "assistant",
                    "content": response.content,
                })
                
                break
            
            # ─── 3. GÖZLEMLE ───
            # Bütçe kontrolü
            if self.cost_tracker.is_over_budget():
                self.logger.warning("⚠️ Bütçe aşıldı! Döngü durduruluyor.")
                state.status = "budget_exceeded"
                break
        
        else:
            # Döngü max_loops'a ulaştı
            self.logger.warning(f"⚠️ Maksimum döngü sayısına ulaşıldı ({self.max_loops})")
            state.status = "max_loops_exceeded"
        
        # İzlemeyi sonlandır
        self.tracer.end_task(success=(state.status == "completed"))
        
        # Rapor yazdır
        self.logger.info(self.tracer.get_summary())
        self.logger.info(self.cost_tracker.get_report())
        
        return state
    
    async def _execute_tool(self, tool_name: str, arguments: dict) -> str:
        """
        Bir tool'u çalıştır.
        
        Bu fonksiyon:
        1. Tool'un var olup olmadığını kontrol eder
        2. Tool fonksiyonunu çağırır
        3. Sonucu string formatında döndürür
        
        Parametreler:
            tool_name: Çağrılacak tool'un adı
            arguments: Tool'a gönderilecek parametreler
        
        Döndürür:
            str: Tool sonucu (string formatında)
        """
        # Tool var mı?
        if tool_name not in self.tools:
            error_msg = f"Hata: '{tool_name}' adında bir tool bulunamadı. Mevcut tool'lar: {list(self.tools.keys())}"
            self.tracer.log_error(error_msg)
            return error_msg
        
        try:
            # Tool fonksiyonunu çağır
            tool_func = self.tools[tool_name]
            
            # Async mi sync mi?
            if asyncio.iscoroutinefunction(tool_func):
                result = await tool_func(**arguments)
            else:
                result = tool_func(**arguments)
            
            return format_tool_result(result)
        
        except Exception as e:
            error_msg = f"Tool hatası ({tool_name}): {str(e)}"
            self.tracer.log_error(error_msg)
            return error_msg

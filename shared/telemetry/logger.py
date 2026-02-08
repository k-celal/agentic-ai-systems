"""
Logger - Loglama Sistemi
=========================
Agent'ın ne yaptığını takip etmemizi sağlar.

Neden loglama önemli?
---------------------
Agent'lar birçok adım atar: düşünür, tool çağırır, hata alır, tekrar dener...
Bir şeyler yanlış gittiğinde "ne oldu?" sorusunu cevaplamak için loglar kritiktir.

Loglama Seviyeleri:
- DEBUG: Her şeyin detayı (geliştirme sırasında)
- INFO: Önemli olaylar (normal çalışma)
- WARNING: Dikkat edilmesi gerekenler
- ERROR: Hatalar

Kullanım:
    from shared.telemetry.logger import get_logger
    
    logger = get_logger("my_agent")
    
    logger.debug("Tool çağrısı hazırlanıyor...")
    logger.info("Tool çağrıldı: get_weather")
    logger.warning("Tool cevabı boş geldi, tekrar deneniyor")
    logger.error("Tool çağrısı başarısız: timeout")
"""

import os
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Rich kütüphanesi yüklüyse güzel çıktı kullan
try:
    from rich.logging import RichHandler
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


def get_logger(name: str, level: str = None) -> logging.Logger:
    """
    İsimlendirilmiş logger oluştur.
    
    Parametreler:
        name: Logger adı (genellikle modül/sınıf adı)
        level: Loglama seviyesi (varsayılan: .env'den veya INFO)
    
    Döndürür:
        logging.Logger: Yapılandırılmış logger
    
    Örnek:
        logger = get_logger("agent.loop")
        logger.info("Döngü başlatıldı")
        logger.debug("Adım 1: Düşünme aşaması")
        logger.info("Tool çağrıldı: get_weather(city='Istanbul')")
        logger.warning("Token limiti yaklaşıyor: %80 kullanıldı")
        logger.error("API çağrısı başarısız: 429 Too Many Requests")
    """
    log_level = level or os.getenv("LOG_LEVEL", "INFO")
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Handler zaten eklenmişse tekrar ekleme
    if logger.handlers:
        return logger
    
    if RICH_AVAILABLE:
        # Güzel renkli çıktı (rich kütüphanesi ile)
        handler = RichHandler(
            rich_tracebacks=True,
            show_time=True,
            show_path=False,
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
    else:
        # Standart çıktı
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%H:%M:%S",
            )
        )
    
    logger.addHandler(handler)
    return logger


class AgentTracer:
    """
    Agent çalışmasını adım adım izleyen izleyici.
    
    Her adımı kaydeder ve sonunda özet rapor üretir.
    
    Kullanım:
        tracer = AgentTracer("my_agent")
        
        tracer.start_task("Hava durumunu öğren")
        tracer.log_think("Hava durumu aracını çağırmalıyım")
        tracer.log_tool_call("get_weather", {"city": "Istanbul"})
        tracer.log_tool_result("get_weather", {"temp": 15})
        tracer.log_response("İstanbul'da hava 15°C")
        tracer.end_task(success=True)
        
        print(tracer.get_summary())
    """
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.logger = get_logger(f"tracer.{agent_name}")
        self.steps: list[dict] = []
        self.start_time: datetime = None
        self.task: str = ""
    
    def start_task(self, task: str):
        """Yeni bir görevi başlat."""
        self.task = task
        self.start_time = datetime.now()
        self.steps = []
        self.logger.info(f"📋 Görev başlatıldı: {task}")
    
    def log_think(self, thought: str):
        """Agent'ın düşüncesini kaydet."""
        self.steps.append({"type": "think", "content": thought, "time": datetime.now()})
        self.logger.info(f"🧠 Düşünce: {thought}")
    
    def log_tool_call(self, tool_name: str, args: dict):
        """Tool çağrısını kaydet."""
        self.steps.append({
            "type": "tool_call",
            "tool": tool_name,
            "args": args,
            "time": datetime.now(),
        })
        self.logger.info(f"🔧 Tool çağrısı: {tool_name}({args})")
    
    def log_tool_result(self, tool_name: str, result: any):
        """Tool sonucunu kaydet."""
        self.steps.append({
            "type": "tool_result",
            "tool": tool_name,
            "result": str(result)[:200],  # Çok uzun sonuçları kırp
            "time": datetime.now(),
        })
        self.logger.info(f"📥 Tool sonucu ({tool_name}): {str(result)[:100]}")
    
    def log_response(self, response: str):
        """Agent cevabını kaydet."""
        self.steps.append({"type": "response", "content": response, "time": datetime.now()})
        self.logger.info(f"💬 Cevap: {response[:100]}")
    
    def log_error(self, error: str):
        """Hatayı kaydet."""
        self.steps.append({"type": "error", "content": error, "time": datetime.now()})
        self.logger.error(f"❌ Hata: {error}")
    
    def end_task(self, success: bool):
        """Görevi sonlandır."""
        duration = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        status = "✅ Başarılı" if success else "❌ Başarısız"
        self.logger.info(f"{status} | Süre: {duration:.2f}s | Adım sayısı: {len(self.steps)}")
    
    def get_summary(self) -> str:
        """Görev özetini döndür."""
        duration = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        
        tool_calls = [s for s in self.steps if s["type"] == "tool_call"]
        errors = [s for s in self.steps if s["type"] == "error"]
        
        return (
            f"\n{'='*50}\n"
            f"📊 Agent İzleme Raporu\n"
            f"{'='*50}\n"
            f"Agent:      {self.agent_name}\n"
            f"Görev:      {self.task}\n"
            f"Süre:       {duration:.2f}s\n"
            f"Adım Sayısı: {len(self.steps)}\n"
            f"Tool Çağrıları: {len(tool_calls)}\n"
            f"Hatalar:    {len(errors)}\n"
            f"{'='*50}"
        )

"""
TwinGraph MCP Sunucusu - Merkezi Araç Yönetim Sistemi
=======================================================
TwinGraph Studio projesinin tüm araçlarını yöneten MCP sunucusu.

Bu sunucu, modül-03'teki ToolRegistry'nin basitleştirilmiş bir versiyonudur.
Sade bir dict tabanlı kayıt defteri kullanır ve araçları merkezi bir noktadan
yönetir.

Temel Bileşenler:
    - TwinGraphMCPServer: Ana sunucu sınıfı
    - register_tool(): Araç kaydetme
    - call_tool(): Araç çağırma
    - list_tools(): Kayıtlı araçları listeleme
    - get_openai_tools(): LLM için OpenAI formatında araç listesi
    - create_server(): Tüm araçları kaydeden fabrika fonksiyonu

Kullanım:
    from mcp.server import create_server
    
    server = create_server()
    
    # Araç listesi
    tools = server.list_tools()
    
    # Araç çağır
    sonuc = server.call_tool("deep_research", {"query": "yapay zeka"})
    
    # OpenAI formatında araçlar (LLM'e gönderilecek)
    openai_tools = server.get_openai_tools()
"""

import sys
import os
import time
import json
from typing import Callable, Any, Optional
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))       # capstone-production-agent (mcp.tools.*)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))  # workspace root (shared.*)

from shared.schemas.tool import ToolSchema, create_tool_schema
from shared.telemetry.logger import get_logger


# ─── Araç Kayıt Yapısı ───

class ToolEntry:
    """
    Kayıt defterindeki tek bir araç girdisi.
    
    Her araç kaydedildiğinde bu yapıda saklanır.
    Fonksiyon referansı, şema bilgisi ve çağrı istatistikleri tutulur.
    
    Öznitelikler:
        name: Araç adı (benzersiz tanımlayıcı)
        func: Araç fonksiyonu (çağrılabilir)
        schema: Araç şeması (ToolSchema nesnesi)
        registered_at: Kayıt zamanı
        call_count: Toplam çağrı sayısı
        error_count: Hata sayısı
        total_duration_ms: Toplam çalışma süresi (milisaniye)
    """
    
    def __init__(self, name: str, func: Callable, schema: ToolSchema):
        """
        ToolEntry oluştur.
        
        Parametreler:
            name: Araç adı
            func: Araç fonksiyonu
            schema: Araç şeması
        """
        self.name: str = name
        self.func: Callable = func
        self.schema: ToolSchema = schema
        self.registered_at: datetime = datetime.now()
        self.call_count: int = 0
        self.error_count: int = 0
        self.total_duration_ms: float = 0.0
    
    @property
    def avg_duration_ms(self) -> float:
        """Ortalama çağrı süresi (milisaniye)."""
        if self.call_count == 0:
            return 0.0
        return self.total_duration_ms / self.call_count
    
    @property
    def success_rate(self) -> float:
        """Başarı oranı (yüzde)."""
        if self.call_count == 0:
            return 100.0
        return ((self.call_count - self.error_count) / self.call_count) * 100


# ─── Ana MCP Sunucusu ───

class TwinGraphMCPServer:
    """
    TwinGraph Studio MCP Sunucusu.
    
    Basit bir dict tabanlı araç kayıt defteri üzerinden tüm araçları yönetir.
    Araç kaydı, çağırma, listeleme ve OpenAI formatına dönüştürme işlevleri sunar.
    
    Neden Bu Yapı?
    ---------------
    - Modül-03'teki ToolRegistry'den daha basit: versiyon yönetimi yok
    - Doğrudan dict tabanlı: hızlı erişim, kolay debug
    - Yapılandırılmış loglama: her işlem loglanır
    - OpenAI uyumu: get_openai_tools() ile LLM entegrasyonu
    
    Kullanım:
        server = TwinGraphMCPServer()
        
        # Araç kaydet
        server.register_tool("hesapla", hesapla_fn, hesapla_schema)
        
        # Araç çağır
        sonuc = server.call_tool("hesapla", {"sayi": 42})
        
        # Tüm araçları listele
        for arac in server.list_tools():
            print(f"  {arac['name']}: {arac['description']}")
    """
    
    def __init__(self, server_name: str = "TwinGraph-MCP"):
        """
        MCP Sunucusunu başlat.
        
        Parametreler:
            server_name: Sunucu adı (loglarda görünür)
        """
        self.server_name: str = server_name
        self._tools: dict[str, ToolEntry] = {}
        self.logger = get_logger(f"mcp.{server_name}")
        self._created_at: datetime = datetime.now()
        
        self.logger.info(f"MCP Sunucusu başlatıldı: {server_name}")
    
    def register_tool(
        self,
        name: str,
        func: Callable,
        schema: ToolSchema,
    ) -> None:
        """
        Yeni bir araç kaydet.
        
        Aynı isimle daha önce kayıtlı bir araç varsa üzerine yazılır
        ve uyarı logu oluşturulur.
        
        Parametreler:
            name: Araç adı (benzersiz tanımlayıcı)
            func: Araç fonksiyonu
            schema: Araç şeması (ToolSchema nesnesi)
        
        Örnek:
            server.register_tool(
                name="arama",
                func=arama_fonksiyonu,
                schema=arama_semasi
            )
        """
        if name in self._tools:
            self.logger.warning(f"Araç zaten kayıtlı, güncelleniyor: {name}")
        
        self._tools[name] = ToolEntry(name=name, func=func, schema=schema)
        self.logger.info(f"Araç kaydedildi: {name} (toplam: {len(self._tools)})")
    
    def call_tool(self, name: str, args: dict = None) -> dict:
        """
        Kayıtlı bir aracı çağır.
        
        İşlem Adımları:
        1. Aracı kayıt defterinde bul
        2. Parametreleri doğrula (şema ile)
        3. Fonksiyonu çalıştır ve süreyi ölç
        4. Sonucu yapılandırılmış formatta döndür
        
        Parametreler:
            name: Çağrılacak aracın adı
            args: Araç parametreleri (dict)
        
        Döndürür:
            dict: Yapılandırılmış sonuç
                - success (bool): Başarılı mı?
                - result (dict/any): Araç sonucu (başarılıysa)
                - error (str): Hata mesajı (başarısızsa)
                - tool_name (str): Çağrılan araç adı
                - duration_ms (float): Çalışma süresi (ms)
        
        Örnek:
            sonuc = server.call_tool("deep_research", {"query": "MCP nedir?"})
            if sonuc["success"]:
                print(sonuc["result"])
            else:
                print(f"Hata: {sonuc['error']}")
        """
        args = args or {}
        
        # ─── 1. Aracı Bul ───
        if name not in self._tools:
            mevcut = list(self._tools.keys())
            self.logger.error(f"Araç bulunamadı: '{name}' (mevcut: {mevcut})")
            return {
                "success": False,
                "error": f"Araç bulunamadı: '{name}'",
                "tool_name": name,
                "available_tools": mevcut,
                "duration_ms": 0,
            }
        
        entry = self._tools[name]
        
        # ─── 2. Parametre Doğrulama ───
        valid, error_msg = entry.schema.validate_args(args)
        if not valid:
            entry.error_count += 1
            self.logger.error(f"Parametre hatası ({name}): {error_msg}")
            return {
                "success": False,
                "error": f"Parametre hatası: {error_msg}",
                "tool_name": name,
                "duration_ms": 0,
            }
        
        # ─── 3. Aracı Çalıştır ───
        entry.call_count += 1
        start_time = time.time()
        
        try:
            self.logger.info(f"Araç çağrılıyor: {name}({json.dumps(args, ensure_ascii=False)[:200]})")
            result = entry.func(**args)
            duration_ms = (time.time() - start_time) * 1000
            entry.total_duration_ms += duration_ms
            
            self.logger.info(f"Araç tamamlandı: {name} ({duration_ms:.1f}ms)")
            
            return {
                "success": True,
                "result": result,
                "tool_name": name,
                "duration_ms": round(duration_ms, 2),
            }
        
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            entry.error_count += 1
            entry.total_duration_ms += duration_ms
            
            self.logger.error(f"Araç hatası ({name}): {str(e)} ({duration_ms:.1f}ms)")
            
            return {
                "success": False,
                "error": f"Araç çalışma hatası ({name}): {str(e)}",
                "tool_name": name,
                "duration_ms": round(duration_ms, 2),
            }
    
    def list_tools(self) -> list[dict]:
        """
        Kayıtlı tüm araçların listesini döndür.
        
        Her araç için ad, açıklama, versiyon ve istatistik bilgisi döner.
        
        Döndürür:
            list[dict]: Araç bilgileri listesi
        
        Örnek:
            for arac in server.list_tools():
                print(f"  {arac['name']}: {arac['description']}")
        """
        tools_info = []
        for name, entry in self._tools.items():
            tools_info.append({
                "name": name,
                "description": entry.schema.description,
                "version": entry.schema.version,
                "parameters": list(entry.schema.parameters.keys()),
                "required": entry.schema.required,
                "call_count": entry.call_count,
                "error_count": entry.error_count,
                "success_rate": f"{entry.success_rate:.1f}%",
                "avg_duration_ms": f"{entry.avg_duration_ms:.1f}",
            })
        return tools_info
    
    def get_openai_tools(self) -> list[dict]:
        """
        Tüm araçları OpenAI tool calling formatında döndür.
        
        Bu format, LLM'e araçların varlığını bildirmek için kullanılır.
        LLM bu listeye bakarak hangi aracı çağıracağına karar verir.
        
        Döndürür:
            list[dict]: OpenAI uyumlu araç tanımları
        
        Örnek:
            tools = server.get_openai_tools()
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=tools,    # ← Buraya gönderilir
            )
        """
        openai_tools = []
        for name, entry in self._tools.items():
            openai_tools.append(entry.schema.to_openai_format())
        return openai_tools
    
    def get_stats(self) -> str:
        """
        Sunucu istatistik raporunu döndür.
        
        Döndürür:
            str: Formatlanmış istatistik raporu
        """
        toplam_cagri = sum(e.call_count for e in self._tools.values())
        toplam_hata = sum(e.error_count for e in self._tools.values())
        toplam_sure = sum(e.total_duration_ms for e in self._tools.values())
        
        basari_orani = ((toplam_cagri - toplam_hata) / max(toplam_cagri, 1)) * 100
        
        lines = [
            "",
            f"{'═' * 50}",
            f"  TwinGraph MCP Sunucu İstatistikleri",
            f"{'═' * 50}",
            f"  Sunucu Adı:        {self.server_name}",
            f"  Kayıtlı Araç:      {len(self._tools)}",
            f"  Toplam Çağrı:      {toplam_cagri}",
            f"  Toplam Hata:       {toplam_hata}",
            f"  Başarı Oranı:      {basari_orani:.1f}%",
            f"  Toplam Süre:       {toplam_sure:.1f}ms",
            f"{'─' * 50}",
        ]
        
        # Araç bazında detay
        for name, entry in self._tools.items():
            lines.append(
                f"  {name:20s} | "
                f"{entry.call_count:3d} çağrı | "
                f"{entry.success_rate:5.1f}% başarı | "
                f"ort. {entry.avg_duration_ms:.1f}ms"
            )
        
        lines.append(f"{'═' * 50}")
        return "\n".join(lines)


# ─── Fabrika Fonksiyonu ───

def create_server() -> TwinGraphMCPServer:
    """
    TwinGraph MCP Sunucusunu oluştur ve tüm araçları kaydet.
    
    Bu fabrika fonksiyonu:
    1. Sunucu örneğini oluşturur
    2. Tüm mevcut araçları kayıt defterine ekler
    3. Hazır sunucuyu döndürür
    
    Döndürür:
        TwinGraphMCPServer: Tüm araçlar kayıtlı, kullanıma hazır sunucu
    
    Örnek:
        server = create_server()
        print(f"Toplam {len(server.list_tools())} araç kaydedildi")
    """
    # Araç modüllerini içe aktar
    from mcp.tools.deep_research import search, DEEP_RESEARCH_SCHEMA
    from mcp.tools.content_save import (
        save_content, SAVE_CONTENT_SCHEMA,
        list_saved, LIST_SAVED_SCHEMA,
        read_content, READ_CONTENT_SCHEMA,
    )
    from mcp.tools.eval_tool import evaluate_writing, EVALUATE_WRITING_SCHEMA
    from mcp.tools.cost_report import generate_cost_report, COST_REPORT_SCHEMA
    from mcp.tools.citation_verify import verify_citations, CITATION_VERIFY_SCHEMA
    
    server = TwinGraphMCPServer(server_name="TwinGraph-MCP")
    
    # ─── Araştırma Aracı ───
    server.register_tool(
        name="deep_research",
        func=search,
        schema=DEEP_RESEARCH_SCHEMA,
    )
    
    # ─── İçerik Kaydetme Araçları ───
    server.register_tool(
        name="save_content",
        func=save_content,
        schema=SAVE_CONTENT_SCHEMA,
    )
    server.register_tool(
        name="list_saved",
        func=list_saved,
        schema=LIST_SAVED_SCHEMA,
    )
    server.register_tool(
        name="read_content",
        func=read_content,
        schema=READ_CONTENT_SCHEMA,
    )
    
    # ─── Yazı Değerlendirme Aracı ───
    server.register_tool(
        name="evaluate_writing",
        func=evaluate_writing,
        schema=EVALUATE_WRITING_SCHEMA,
    )
    
    # ─── Maliyet Raporu Aracı ───
    server.register_tool(
        name="generate_cost_report",
        func=generate_cost_report,
        schema=COST_REPORT_SCHEMA,
    )
    
    # ─── Kaynak Doğrulama Aracı ───
    server.register_tool(
        name="verify_citations",
        func=verify_citations,
        schema=CITATION_VERIFY_SCHEMA,
    )
    
    server.logger.info(
        f"Sunucu hazır! {len(server.list_tools())} araç kaydedildi."
    )
    
    return server


# ─── Test Bloğu ───

if __name__ == "__main__":
    print("=" * 60)
    print("  TwinGraph MCP Sunucusu - Test")
    print("=" * 60)
    
    server = create_server()
    
    # Araç listesi
    print(f"\nKayıtlı Araçlar ({len(server.list_tools())}):")
    for tool in server.list_tools():
        params = ", ".join(tool["parameters"])
        print(f"  {tool['name']:25s} | parametreler: {params}")
    
    # OpenAI format test
    openai_tools = server.get_openai_tools()
    print(f"\nOpenAI Formatında Araçlar ({len(openai_tools)}):")
    for t in openai_tools:
        print(f"  {t['function']['name']}: {t['function']['description'][:60]}...")
    
    # Araç çağrı testi
    print(f"\n{'─' * 50}")
    print("Araç Çağrı Testleri:")
    
    # 1. Araştırma
    sonuc = server.call_tool("deep_research", {"query": "yapay zeka ajanları"})
    if sonuc["success"]:
        print(f"\n  deep_research: {sonuc['result']['total_results']} sonuç bulundu")
        for r in sonuc["result"]["results"][:2]:
            print(f"    - {r['title']} (alaka: {r['relevance_score']})")
    
    # 2. İçerik kaydetme
    sonuc = server.call_tool("save_content", {
        "filename": "test_makale.md",
        "content": "Bu bir test içeriğidir.",
        "content_type": "markdown",
    })
    if sonuc["success"]:
        print(f"\n  save_content: {sonuc['result']['status']}")
    
    # 3. Kaydedilenleri listele
    sonuc = server.call_tool("list_saved", {})
    if sonuc["success"]:
        print(f"\n  list_saved: {sonuc['result']['total_files']} dosya")
    
    # 4. Mevcut olmayan araç
    sonuc = server.call_tool("olmayan_arac", {"test": True})
    print(f"\n  olmayan_arac: hata={sonuc['error']}")
    
    # İstatistikler
    print(server.get_stats())
    
    print("\nTest tamamlandı!")

"""
RetryHandler - Üstel Geri Çekilme ile Yeniden Deneme
======================================================
Araç çağrılarında geçici hatalar oluştuğunda üstel geri çekilme (exponential
backoff) stratejisi ile yeniden deneme sağlar.

Neden Yeniden Deneme Gerekli?
------------------------------
Geçici hatalar (ağ zaman aşımı, API hız limiti, sunucu meşgul) genellikle
tekrar denendiğinde düzelir. Ama DİKKAT: sadece idempotent araçlar güvenle
tekrar denenebilir!

İdempotent Araç Nedir?
-----------------------
Aynı parametrelerle birden fazla kez çağrıldığında aynı sonucu veren
ve yan etkisi olmayan araçlardır.

Örnekler:
    - deep_research (idempotent): Aynı sorgu → aynı sonuçlar
    - read_content (idempotent): Aynı dosyayı oku → aynı içerik
    - save_content (İDEMPOTENT DEĞİL): Tekrar kaydetme → veri üzerine yazma!

Kullanım:
    from mcp.middleware.retry import RetryHandler
    
    handler = RetryHandler()
    
    sonuc = handler.execute_with_retry(
        func=arama_fonksiyonu,
        kwargs={"query": "yapay zeka"},
        max_retries=3,
        backoff=2.0,
    )
"""

import sys
import os
import time
from typing import Callable, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from shared.telemetry.logger import get_logger


# ─── İdempotent Araç Listesi ───
# Bu listedeki araçlar güvenle tekrar denenebilir
IDEMPOTENT_TOOLS: set[str] = {
    "deep_research",
    "read_content",
    "list_saved",
    "evaluate_writing",
    "generate_cost_report",
    "verify_citations",
}

# Bu listedeki araçlar tekrar denenmemeli (yan etkileri var)
NON_IDEMPOTENT_TOOLS: set[str] = {
    "save_content",
}


class RetryHandler:
    """
    Üstel geri çekilme stratejisi ile yeniden deneme yöneticisi.
    
    Nasıl Çalışır?
    ---------------
    1. Fonksiyonu çalıştır
    2. Başarılıysa → sonucu döndür
    3. Başarısızsa ve araç idempotent ise:
       a. Bekleme süresi kadar bekle
       b. Bekleme süresini backoff çarpanıyla artır (üstel geri çekilme)
       c. Tekrar dene (max_retries'a kadar)
    4. Tüm denemeler başarısızsa → hata döndür
    
    Üstel Geri Çekilme Örneği (backoff=2.0):
        Deneme 1 → Başarısız → 1.0s bekle
        Deneme 2 → Başarısız → 2.0s bekle
        Deneme 3 → Başarısız → 4.0s bekle
        Deneme 4 → Tüm denemeler tükendi!
    
    Kullanım:
        handler = RetryHandler()
        
        # İdempotent araç için (güvenli)
        sonuc = handler.execute_with_retry(
            func=arama_fonksiyonu,
            kwargs={"query": "test"},
            max_retries=3,
            backoff=2.0,
        )
        
        # Non-idempotent araç için (otomatik olarak 1 denemeye düşer)
        sonuc = handler.execute_with_retry(
            func=kaydetme_fonksiyonu,
            kwargs={"filename": "test.txt", "content": "..."},
            max_retries=3,   # Otomatik 1'e düşürülür!
        )
    """
    
    def __init__(self):
        """RetryHandler oluştur."""
        self.logger = get_logger("mcp.middleware.retry")
        self._retry_stats: dict[str, dict] = {}
    
    def _is_idempotent(self, func: Callable) -> bool:
        """
        Fonksiyonun idempotent olup olmadığını kontrol et.
        
        Fonksiyon adı, IDEMPOTENT_TOOLS kümesinde varsa True döner.
        Emin olunamayan fonksiyonlar güvenlik amacıyla non-idempotent sayılır.
        
        Parametreler:
            func: Kontrol edilecek fonksiyon
        
        Döndürür:
            bool: İdempotent mi?
        """
        func_name = getattr(func, "__name__", "")
        
        if func_name in IDEMPOTENT_TOOLS:
            return True
        
        if func_name in NON_IDEMPOTENT_TOOLS:
            return False
        
        # Bilinmeyen fonksiyonlar → güvenli tarafta kal
        self.logger.warning(
            f"Fonksiyon '{func_name}' idempotent listesinde yok. "
            f"Güvenlik için non-idempotent kabul ediliyor."
        )
        return False
    
    def execute_with_retry(
        self,
        func: Callable,
        kwargs: dict = None,
        max_retries: int = 3,
        backoff: float = 2.0,
    ) -> dict:
        """
        Fonksiyonu yeniden deneme mantığı ile çalıştır.
        
        İdempotent olmayan araçlar otomatik olarak max_retries=1'e düşürülür.
        
        Parametreler:
            func: Çalıştırılacak fonksiyon
            kwargs: Fonksiyon parametreleri
            max_retries: Maksimum deneme sayısı (varsayılan: 3)
            backoff: Üstel geri çekilme çarpanı (varsayılan: 2.0)
        
        Döndürür:
            dict: Yapılandırılmış sonuç
                - success (bool): Başarılı mı?
                - result (any): Fonksiyon sonucu (başarılıysa)
                - error (str): Hata mesajı (başarısızsa)
                - attempts (int): Toplam deneme sayısı
                - total_duration_ms (float): Toplam süre
        
        Örnek:
            sonuc = handler.execute_with_retry(
                func=arama_fonksiyonu,
                kwargs={"query": "yapay zeka ajanları"},
                max_retries=3,
                backoff=2.0,
            )
            
            if sonuc["success"]:
                print(f"Başarılı! {sonuc['attempts']} denemede")
            else:
                print(f"Başarısız: {sonuc['error']}")
        """
        kwargs = kwargs or {}
        func_name = getattr(func, "__name__", "bilinmeyen")
        
        # ─── İdempotent Kontrolü ───
        if not self._is_idempotent(func) and max_retries > 1:
            self.logger.warning(
                f"'{func_name}' idempotent değil! "
                f"max_retries={max_retries} → 1'e düşürüldü. "
                f"(Tekrar deneme tehlikeli olabilir)"
            )
            max_retries = 1
        
        # ─── Yeniden Deneme Döngüsü ───
        son_hata = None
        gecikme = 1.0  # İlk bekleme süresi (saniye)
        toplam_baslangic = time.time()
        
        for deneme in range(1, max_retries + 1):
            self.logger.info(
                f"[{func_name}] Deneme {deneme}/{max_retries}"
            )
            
            try:
                baslangic = time.time()
                result = func(**kwargs)
                sure_ms = (time.time() - baslangic) * 1000
                
                # Başarılı
                if deneme > 1:
                    self.logger.info(
                        f"[{func_name}] Deneme {deneme}'de BAŞARILI! "
                        f"({sure_ms:.1f}ms)"
                    )
                
                # İstatistik güncelle
                self._update_stats(func_name, deneme, True)
                
                toplam_sure = (time.time() - toplam_baslangic) * 1000
                return {
                    "success": True,
                    "result": result,
                    "attempts": deneme,
                    "duration_ms": round(sure_ms, 2),
                    "total_duration_ms": round(toplam_sure, 2),
                }
            
            except Exception as e:
                son_hata = str(e)
                sure_ms = (time.time() - baslangic) * 1000
                
                self.logger.warning(
                    f"[{func_name}] Deneme {deneme} BAŞARISIZ: {son_hata} "
                    f"({sure_ms:.1f}ms)"
                )
                
                # Son deneme değilse bekle
                if deneme < max_retries:
                    self.logger.info(
                        f"  Bekleniyor: {gecikme:.1f}s "
                        f"(sonraki bekleme: {gecikme * backoff:.1f}s)"
                    )
                    time.sleep(gecikme)
                    gecikme *= backoff  # Üstel geri çekilme
        
        # ─── Tüm Denemeler Başarısız ───
        self._update_stats(func_name, max_retries, False)
        toplam_sure = (time.time() - toplam_baslangic) * 1000
        
        self.logger.error(
            f"[{func_name}] Tüm denemeler ({max_retries}) başarısız! "
            f"Son hata: {son_hata}"
        )
        
        return {
            "success": False,
            "error": (
                f"Tüm denemeler ({max_retries}) başarısız. "
                f"Son hata: {son_hata}"
            ),
            "attempts": max_retries,
            "total_duration_ms": round(toplam_sure, 2),
        }
    
    def _update_stats(self, func_name: str, attempts: int, success: bool) -> None:
        """
        İstatistikleri güncelle (dahili kullanım).
        
        Parametreler:
            func_name: Fonksiyon adı
            attempts: Deneme sayısı
            success: Başarılı mı?
        """
        if func_name not in self._retry_stats:
            self._retry_stats[func_name] = {
                "total_calls": 0,
                "total_retries": 0,
                "successes": 0,
                "failures": 0,
            }
        
        stats = self._retry_stats[func_name]
        stats["total_calls"] += 1
        stats["total_retries"] += attempts - 1  # İlk deneme retry sayılmaz
        
        if success:
            stats["successes"] += 1
        else:
            stats["failures"] += 1
    
    def get_stats(self) -> str:
        """
        Yeniden deneme istatistik raporunu döndür.
        
        Döndürür:
            str: Formatlanmış istatistik raporu
        """
        if not self._retry_stats:
            return "Henüz yeniden deneme kaydı bulunmuyor."
        
        lines = [
            "",
            f"{'═' * 55}",
            f"  RetryHandler İstatistikleri",
            f"{'═' * 55}",
        ]
        
        toplam_cagri = 0
        toplam_retry = 0
        
        for name, stats in self._retry_stats.items():
            toplam_cagri += stats["total_calls"]
            toplam_retry += stats["total_retries"]
            rate = (stats["successes"] / max(stats["total_calls"], 1)) * 100
            
            lines.append(
                f"  {name:22s} | "
                f"{stats['total_calls']:3d} çağrı | "
                f"{stats['total_retries']:3d} retry | "
                f"{rate:5.0f}% başarı"
            )
        
        lines.append(f"{'─' * 55}")
        lines.append(f"  Toplam Çağrı:   {toplam_cagri}")
        lines.append(f"  Toplam Retry:   {toplam_retry}")
        lines.append(f"{'═' * 55}")
        
        return "\n".join(lines)


# ─── Test Bloğu ───

if __name__ == "__main__":
    print("=" * 55)
    print("  RetryHandler - Yeniden Deneme Test")
    print("=" * 55)
    
    handler = RetryHandler()
    
    # ─── Test 1: Başarılı çağrı ───
    print("\n--- Test 1: Başarılı çağrı ---")
    
    def basarili_arama(query: str) -> dict:
        """Her zaman başarılı simüle edilmiş arama."""
        return {"results": [f"Sonuç: {query}"], "count": 1}
    
    # Fonksiyon adını idempotent listesine ekle
    basarili_arama.__name__ = "deep_research"
    
    sonuc = handler.execute_with_retry(
        func=basarili_arama,
        kwargs={"query": "test sorgusu"},
        max_retries=3,
    )
    print(f"  Sonuç: success={sonuc['success']}, "
          f"denemeler={sonuc['attempts']}")
    
    # ─── Test 2: Geçici hata sonrası başarı ───
    print("\n--- Test 2: 2 hata sonrası başarı ---")
    
    hata_sayaci = {"sayac": 0}
    
    def gecici_hatali_arama(query: str) -> dict:
        """İlk 2 çağrıda hata veren simüle edilmiş arama."""
        hata_sayaci["sayac"] += 1
        if hata_sayaci["sayac"] <= 2:
            raise ConnectionError(f"Geçici ağ hatası (deneme {hata_sayaci['sayac']})")
        return {"results": [f"Sonuç: {query}"], "count": 1}
    
    gecici_hatali_arama.__name__ = "deep_research"
    
    sonuc = handler.execute_with_retry(
        func=gecici_hatali_arama,
        kwargs={"query": "geçici hata testi"},
        max_retries=3,
        backoff=1.0,  # Test için kısa bekleme
    )
    print(f"  Sonuç: success={sonuc['success']}, "
          f"denemeler={sonuc['attempts']}")
    
    # ─── Test 3: Non-idempotent araç ───
    print("\n--- Test 3: Non-idempotent araç ---")
    
    def kaydetme(filename: str, content: str) -> dict:
        """Simüle edilmiş kaydetme."""
        return {"saved": True}
    
    kaydetme.__name__ = "save_content"
    
    sonuc = handler.execute_with_retry(
        func=kaydetme,
        kwargs={"filename": "test.md", "content": "test"},
        max_retries=5,  # Otomatik 1'e düşecek
    )
    print(f"  Sonuç: success={sonuc['success']}, "
          f"denemeler={sonuc['attempts']}")
    
    # ─── İstatistikler ───
    print(handler.get_stats())
    
    print("\nTest tamamlandı!")

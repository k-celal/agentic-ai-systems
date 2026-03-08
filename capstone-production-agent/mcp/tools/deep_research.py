"""
Derinlemesine Araştırma Aracı - Simüle Edilmiş Bilgi Tabanı
===============================================================
Geniş kapsamlı bir bilgi tabanı üzerinde bulanık eşleme ile araştırma yapan
en temel ve en zengin MCP aracıdır.

Bu Araç Neden Önemli?
-----------------------
TwinGraph Studio'nun araştırma ajanı, içerik üretimi öncesinde bu araçla
derinlemesine araştırma yapar. Zengin bilgi tabanı sayesinde:
- 10+ konu başlığında detaylı bilgi sunar
- Her sonuçta başlık, sahte kaynak URL, özet ve alaka puanı bulunur
- Bulanık eşleme (fuzzy matching) ile anahtar kelime tabanlı arama yapılır

Araştırma Akışı:
    1. Sorgu anahtar kelimelere ayrılır
    2. Bilgi tabanındaki her konu, anahtar kelime eşleşmesine göre puanlanır
    3. En alakalı sonuçlar sıralanarak döndürülür

Kullanım:
    from mcp.tools.deep_research import search
    
    sonuc = search(query="yapay zeka ajanları nasıl çalışır", max_results=5)
    
    for r in sonuc["results"]:
        print(f"  {r['title']} (alaka: {r['relevance_score']})")
        print(f"  Kaynak: {r['source_url']}")
        print(f"  Özet: {r['summary'][:80]}...")
"""

import sys
import os
from typing import Any
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from shared.schemas.tool import create_tool_schema
from shared.telemetry.logger import get_logger

logger = get_logger("mcp.tools.deep_research")


# ═══════════════════════════════════════════════════════════════════
#  BİLGİ TABANI - Simüle Edilmiş Araştırma Veritabanı
# ═══════════════════════════════════════════════════════════════════
#
# Her konu birden fazla anahtar kelime ile etiketlenmiştir.
# Arama sorgusu bu anahtar kelimelere karşı bulanık eşleme yapar.

KNOWLEDGE_BASE: dict[str, dict[str, Any]] = {
    
    # ─── 1. Yapay Zeka Ajanları ───
    "ai_agents": {
        "title": "Yapay Zeka Ajanları: Otonom Sistemlerin Yükselişi",
        "keywords": [
            "yapay zeka", "ajan", "agent", "otonom", "karar verme",
            "ai", "akıllı", "sistem", "bağımsız", "görev",
        ],
        "source_url": "https://arastirma.twingraph.dev/ai-agents-rehberi",
        "summary": (
            "Yapay zeka ajanları, belirli bir görevi tamamlamak için otonom kararlar "
            "alabilen yazılım sistemleridir. LLM tabanlı ajanlar, algılama-düşünme-eylem "
            "(perceive-reason-act) döngüsünde çalışır. Modern ajanlar araç kullanabilir, "
            "bellek tutabilir ve çok adımlı planlar oluşturabilir. ReAct, Chain-of-Thought "
            "ve Tool-Use gibi teknikler ajanların yeteneklerini önemli ölçüde artırmıştır."
        ),
        "sections": [
            "Ajan Mimarisi: Algılama → Düşünme → Eylem döngüsü",
            "Bellek Türleri: Kısa süreli (oturum) ve uzun süreli (kalıcı) bellek",
            "Araç Kullanımı: Fonksiyon çağırma, API entegrasyonu, dosya işlemleri",
            "Planlama: Alt görevlere ayırma, önceliklendirme, bağımlılık analizi",
            "Değerlendirme: Başarı metrikleri, maliyet takibi, kalite puanlama",
        ],
    },
    
    # ─── 2. MCP Protokolü ───
    "mcp_protocol": {
        "title": "Model Context Protocol (MCP): LLM Araç Standartı",
        "keywords": [
            "mcp", "model context protocol", "protokol", "araç", "tool",
            "standart", "sunucu", "server", "istemci", "client",
        ],
        "source_url": "https://arastirma.twingraph.dev/mcp-protokolu",
        "summary": (
            "MCP (Model Context Protocol), Anthropic tarafından geliştirilen ve LLM'lerin "
            "dış dünyayla etkileşimini standartlaştıran bir protokoldür. USB-C gibi düşünün: "
            "her cihaz için ayrı kablo yerine tek bir standart. MCP sunucuları araçlar sunar, "
            "istemciler (LLM uygulamaları) bu araçları çağırır. Şema doğrulama, hata yönetimi "
            "ve güvenlik katmanları içerir."
        ),
        "sections": [
            "MCP Mimarisi: Sunucu-İstemci modeli, JSON-RPC tabanlı iletişim",
            "Araç Tanımları: inputSchema ile parametre şeması, zorunlu/opsiyonel alanlar",
            "Kaynak Yönetimi: Dosya, veritabanı ve API kaynaklarına erişim",
            "Güvenlik: İzin sistemi, sandbox ortamı, kaynak sınırlama",
            "Versiyonlama: Araç versiyonları, geriye dönük uyumluluk",
        ],
    },
    
    # ─── 3. Büyük Dil Modelleri (LLM) ───
    "llm_basics": {
        "title": "Büyük Dil Modelleri: Temellerden İleri Tekniklere",
        "keywords": [
            "llm", "büyük dil modeli", "language model", "gpt", "transformer",
            "token", "dikkat mekanizması", "attention", "fine-tuning", "model",
        ],
        "source_url": "https://arastirma.twingraph.dev/llm-temelleri",
        "summary": (
            "Büyük Dil Modelleri (LLM), milyarlarca parametre ile eğitilmiş transformer "
            "tabanlı yapay sinir ağlarıdır. GPT, Claude, Llama gibi modeller metin üretimi, "
            "çeviri, özetleme ve kod yazma gibi görevlerde üstün performans gösterir. "
            "Token ekonomisi, bağlam penceresi (context window), sıcaklık (temperature) ve "
            "top-p gibi parametreler modelin davranışını belirler."
        ),
        "sections": [
            "Transformer Mimarisi: Self-attention, çoklu-başlık dikkat, konum kodlaması",
            "Token Ekonomisi: Tokenizasyon, BPE, fiyatlandırma, bütçe yönetimi",
            "Prompt Mühendisliği: Sistem mesajı, few-shot, chain-of-thought, role-play",
            "Fine-tuning: LoRA, QLoRA, RLHF, veri hazırlama",
            "Değerlendirme: BLEU, ROUGE, insan değerlendirmesi, benchmark'lar",
        ],
    },
    
    # ─── 4. Python Programlama ───
    "python_programming": {
        "title": "Python ile Yapay Zeka Geliştirme Rehberi",
        "keywords": [
            "python", "programlama", "kodlama", "geliştirme", "yazılım",
            "kütüphane", "framework", "pip", "venv", "async",
        ],
        "source_url": "https://arastirma.twingraph.dev/python-ai-rehberi",
        "summary": (
            "Python, yapay zeka ve makine öğrenmesi alanında en yaygın kullanılan "
            "programlama dilidir. OpenAI, LangChain, Hugging Face gibi kütüphaneler "
            "Python ekosisteminin gücünü oluşturur. Asenkron programlama (asyncio), "
            "tip ipuçları (type hints) ve dataclass'lar modern Python geliştirmesinin "
            "temel taşlarıdır."
        ),
        "sections": [
            "AI Kütüphaneleri: openai, anthropic, langchain, llamaindex, transformers",
            "Asenkron Programlama: asyncio, aiohttp, eşzamanlı araç çağrıları",
            "Veri İşleme: pandas, numpy, veri temizleme, özellik mühendisliği",
            "Test ve Kalite: pytest, mypy, ruff, pre-commit hooks",
            "Dağıtım: Docker, FastAPI, uvicorn, gunicorn, CI/CD",
        ],
    },
    
    # ─── 5. Çok Ajanlı Sistemler ───
    "multi_agent": {
        "title": "Çok Ajanlı Sistemler: Orkestrasyon ve İş Birliği",
        "keywords": [
            "çok ajanlı", "multi agent", "orkestrasyon", "koordinasyon",
            "iş birliği", "supervisor", "yönlendirici", "paralel", "sıralı",
        ],
        "source_url": "https://arastirma.twingraph.dev/cok-ajanli-sistemler",
        "summary": (
            "Çok ajanlı sistemler, birden fazla uzman ajanın koordineli çalışarak "
            "karmaşık görevleri tamamladığı mimari yapılardır. Supervisor (yönetici) "
            "ajan, alt görevleri uzman ajanlara dağıtır. Router (yönlendirici) yaklaşımı, "
            "gelen isteği en uygun ajana yönlendirir. Paralel ve sıralı çalışma modları, "
            "handoff (devir) mekanizması ve paylaşımlı bellek önemli kavramlardır."
        ),
        "sections": [
            "Mimari Kalıplar: Supervisor, Router, Paralel, Pipeline, Hiyerarşik",
            "Koordinasyon: Mesaj geçirme, paylaşımlı bellek, oylama mekanizması",
            "Handoff Mekanizması: Ajan arası görev devri, bağlam aktarımı",
            "Hata Yönetimi: Yedek ajan, geri dönüş stratejisi, zaman aşımı",
            "Gerçek Dünya Örnekleri: İçerik üretimi, kod analizi, müşteri desteği",
        ],
    },
    
    # ─── 6. Prompt Mühendisliği ───
    "prompt_engineering": {
        "title": "Prompt Mühendisliği: LLM'den En İyi Sonuçları Almak",
        "keywords": [
            "prompt", "mühendislik", "sistem mesajı", "system message",
            "few-shot", "chain of thought", "talimat", "şablon", "template",
        ],
        "source_url": "https://arastirma.twingraph.dev/prompt-muhendisligi",
        "summary": (
            "Prompt mühendisliği, LLM'lerden istenilen çıktıyı almak için giriş "
            "metnini (prompt) optimize etme sanatıdır. Sistem mesajları ajanın rolünü "
            "ve kurallarını tanımlar. Few-shot örnekler beklenen format ve kaliteyi "
            "gösterir. Chain-of-Thought (düşünce zinciri) tekniği adım adım akıl "
            "yürütmeyi teşvik eder. Yapılandırılmış çıktı (JSON modu) güvenilir "
            "veri üretimini sağlar."
        ),
        "sections": [
            "Sistem Mesajı Tasarımı: Rol tanımı, kurallar, kısıtlamalar, ton",
            "Few-Shot Öğrenme: Örnek seçimi, format tutarlılığı, çeşitlilik",
            "Chain-of-Thought: Adım adım düşünme, ara çıktılar, doğrulama",
            "Yapılandırılmış Çıktı: JSON modu, XML şablonlar, regex kısıtlamaları",
            "Anti-Kalıplar: Prompt injection, jailbreak, aşırı karmaşık promptlar",
        ],
    },
    
    # ─── 7. Değerlendirme ve Optimizasyon ───
    "evaluation": {
        "title": "AI Ajan Değerlendirmesi: Metrikler ve Optimizasyon",
        "keywords": [
            "değerlendirme", "eval", "metrik", "optimizasyon", "kalite",
            "benchmark", "puan", "skor", "test", "doğruluk",
        ],
        "source_url": "https://arastirma.twingraph.dev/degerlendirme-rehberi",
        "summary": (
            "AI ajanlarının değerlendirilmesi, çıktı kalitesini nesnel ölçütlerle "
            "ölçme sürecidir. Kelime sayısı, cümle çeşitliliği, okunabilirlik ve "
            "kaynak doğruluğu gibi boyutlar değerlendirilir. A/B testleri farklı "
            "prompt ve model konfigürasyonlarını karşılaştırır. Maliyet-kalite dengesi "
            "(cost-quality tradeoff) production ortamında kritik bir metriktir."
        ),
        "sections": [
            "Kalite Metrikleri: Doğruluk, tutarlılık, akıcılık, alaka düzeyi",
            "Otomatik Değerlendirme: Kural tabanlı, LLM-as-judge, semantic similarity",
            "A/B Testi: Prompt varyasyonları, model karşılaştırma, istatistiksel anlamlılık",
            "Maliyet Optimizasyonu: Token azaltma, model seçimi, önbellek stratejileri",
            "Production İzleme: Canlı metrikler, sapma algılama, uyarı sistemi",
        ],
    },
    
    # ─── 8. Yansıma (Reflection) ───
    "reflection": {
        "title": "Yansıma Kalıbı: Ajanların Öz-Değerlendirmesi",
        "keywords": [
            "yansıma", "reflection", "öz-değerlendirme", "self-eval",
            "iyileştirme", "iterasyon", "geri bildirim", "revizyon", "düzeltme",
        ],
        "source_url": "https://arastirma.twingraph.dev/yansima-kalibi",
        "summary": (
            "Yansıma (Reflection), bir ajanın kendi çıktısını değerlendirip "
            "iyileştirdiği güçlü bir tasarım kalıbıdır. Üretici-Değerlendirici "
            "(Generator-Evaluator) döngüsünde çalışır: ajan önce çıktı üretir, "
            "sonra bu çıktıyı eleştirir ve daha iyi bir versiyon oluşturur. "
            "Birden fazla iterasyon, çıktı kalitesini kademeli olarak artırır."
        ),
        "sections": [
            "Yansıma Döngüsü: Üret → Değerlendir → İyileştir → Tekrarla",
            "Değerlendirme Boyutları: İçerik, yapı, dil, kaynak kullanımı",
            "İterasyon Stratejisi: Maksimum tur, erken durma, kalite eşiği",
            "Uygulama Örnekleri: Makale yazımı, kod üretimi, çeviri",
            "Maliyet Analizi: Her iterasyonun token maliyeti, azalan getiri",
        ],
    },
    
    # ─── 9. İçerik Üretimi ───
    "content_creation": {
        "title": "AI ile İçerik Üretimi: Strateji ve En İyi Uygulamalar",
        "keywords": [
            "içerik", "üretim", "yazı", "makale", "blog", "metin",
            "content", "yaratıcı", "editör", "yayın", "yazarlık",
        ],
        "source_url": "https://arastirma.twingraph.dev/icerik-uretimi",
        "summary": (
            "AI destekli içerik üretimi, araştırma → taslak → düzenleme → "
            "yayınlama akışını takip eder. Araştırma aşamasında konu derinlemesine "
            "incelenir, kaynaklar toplanır. Taslak aşamasında LLM yapılandırılmış "
            "bir metin üretir. Düzenleme aşamasında yansıma döngüsü ile kalite "
            "artırılır. SEO optimizasyonu, hedef kitle analizi ve ton tutarlılığı "
            "önemli faktörlerdir."
        ),
        "sections": [
            "İçerik Pipeline: Araştırma → Planlama → Taslak → Düzenleme → Yayınlama",
            "Yapılandırılmış Yazım: Başlık, alt başlıklar, giriş-gelişme-sonuç",
            "Kalite Kriterleri: Orijinallik, doğruluk, okunabilirlik, SEO",
            "Hedef Kitle: Ton ayarlama, teknik seviye, dil seçimi",
            "Araç Entegrasyonu: Araştırma, kaynak doğrulama, değerlendirme araçları",
        ],
    },
    
    # ─── 10. Maliyet Yönetimi ───
    "cost_management": {
        "title": "LLM Maliyet Yönetimi: Bütçe ve Optimizasyon",
        "keywords": [
            "maliyet", "bütçe", "fiyat", "token", "harcama",
            "cost", "optimizasyon", "tasarruf", "verimlilik", "ekonomi",
        ],
        "source_url": "https://arastirma.twingraph.dev/maliyet-yonetimi",
        "summary": (
            "LLM maliyet yönetimi, API çağrılarının maliyetini izleme ve "
            "optimize etme sürecidir. Token fiyatlandırması modele göre değişir: "
            "GPT-4o-mini ($0.15/1M input) vs GPT-4o ($2.50/1M input). "
            "Bütçe limitleri, ajan döngülerinin kontrolsüz harcama yapmasını engeller. "
            "Prompt sıkıştırma, model kademesi (tiering) ve önbellekleme başlıca "
            "optimizasyon teknikleridir."
        ),
        "sections": [
            "Token Fiyatlandırma: Model bazlı fiyatlar, input/output farkı",
            "Bütçe Yönetimi: Limitler, uyarılar, otomatik durdurma",
            "Optimizasyon: Prompt sıkıştırma, model tiering, batch processing",
            "Önbellekleme: Tekrarlanan sorgularda kaynak tasarrufu",
            "Raporlama: Ajan bazlı maliyet, trend analizi, öneriler",
        ],
    },
    
    # ─── 11. Güvenlik ve Etik ───
    "security_ethics": {
        "title": "AI Güvenliği ve Etik Kullanım Rehberi",
        "keywords": [
            "güvenlik", "etik", "prompt injection", "jailbreak", "gizlilik",
            "security", "safety", "bias", "önyargı", "sorumluluk",
        ],
        "source_url": "https://arastirma.twingraph.dev/guvenlik-etik",
        "summary": (
            "AI güvenliği, sistemlerin kötü niyetli kullanıma karşı korunmasını "
            "kapsar. Prompt injection saldırıları, ajanın talimatlarını değiştirmeye "
            "çalışır. Sandbox ortamları araç çağrılarını sınırlar. Etik açıdan "
            "önyargı (bias) tespiti, şeffaflık, veri gizliliği ve sorumlu AI "
            "kullanımı önemli konulardır."
        ),
        "sections": [
            "Prompt Injection: Doğrudan ve dolaylı saldırılar, savunma yöntemleri",
            "Sandbox Güvenliği: Araç izinleri, kaynak sınırlama, dosya sistemi izolasyonu",
            "Önyargı ve Adalet: Veri önyargısı, çıktı denetimi, çeşitlilik",
            "Gizlilik: PII filtreleme, veri saklama politikaları, KVKK uyumu",
            "Sorumluluk: İnsan denetimi, denetim kaydı, açıklanabilirlik",
        ],
    },
    
    # ─── 12. RAG (Retrieval-Augmented Generation) ───
    "rag_systems": {
        "title": "RAG Sistemleri: Bilgi Erişimli Metin Üretimi",
        "keywords": [
            "rag", "retrieval", "bilgi erişim", "vektör", "embedding",
            "veritabanı", "indeks", "chunk", "parçalama", "semantic",
        ],
        "source_url": "https://arastirma.twingraph.dev/rag-sistemleri",
        "summary": (
            "RAG (Retrieval-Augmented Generation), LLM'in kendi eğitim verisinin "
            "ötesindeki bilgilere erişmesini sağlayan güçlü bir tekniktir. Belgeler "
            "parçalara (chunk) ayrılır, vektör gömmeleri (embedding) oluşturulur ve "
            "bir vektör veritabanında saklanır. Sorgu geldiğinde en alakalı parçalar "
            "bulunur ve LLM'e bağlam olarak sunulur. Halüsinasyonu azaltır."
        ),
        "sections": [
            "Vektör Gömme: text-embedding-3-small, cosine similarity, boyut seçimi",
            "Parçalama Stratejisi: Sabit boyut, cümle bazlı, semantik parçalama",
            "Vektör Veritabanları: Pinecone, Weaviate, Chroma, pgvector",
            "Hibrit Arama: Vektör + anahtar kelime, re-ranking, filtre",
            "Değerlendirme: Faithfulness, relevancy, recall, context precision",
        ],
    },
    
    # ─── 13. API Tasarımı ve Entegrasyon ───
    "api_design": {
        "title": "AI Servisleri için API Tasarımı ve Entegrasyon",
        "keywords": [
            "api", "rest", "fastapi", "entegrasyon", "servis",
            "endpoint", "webhook", "streaming", "rate limit", "auth",
        ],
        "source_url": "https://arastirma.twingraph.dev/api-tasarimi",
        "summary": (
            "AI servislerinin API tasarımı, standart REST prensiplerinin yanı sıra "
            "streaming yanıtlar, uzun süren görevler ve webhook bildirimleri gibi "
            "ek kalıplar gerektirir. FastAPI ile yüksek performanslı async endpoint'ler "
            "oluşturulabilir. Rate limiting, API anahtarı yönetimi ve hata standardizasyonu "
            "production-grade servisler için kritiktir."
        ),
        "sections": [
            "REST Tasarımı: Kaynak odaklı URL, HTTP metodları, durum kodları",
            "Streaming: Server-Sent Events, WebSocket, chunk transfer encoding",
            "Kimlik Doğrulama: API anahtarı, OAuth 2.0, JWT",
            "Hız Limiti: Token bucket, sliding window, kullanıcı bazlı limit",
            "Dokümantasyon: OpenAPI/Swagger, örnekler, SDK oluşturma",
        ],
    },
}


# ═══════════════════════════════════════════════════════════════════
#  ARAMA FONKSİYONU
# ═══════════════════════════════════════════════════════════════════

def search(query: str, max_results: int = 5) -> dict:
    """
    Bilgi tabanında derinlemesine araştırma yap.
    
    Sorgu metni anahtar kelimelere ayrılır ve bilgi tabanındaki her konu
    için alaka puanı hesaplanır. En alakalı sonuçlar sıralanarak döndürülür.
    
    Puanlama Mantığı:
    - Her eşleşen anahtar kelime +1 puan
    - Başlıkta eşleşme ek +2 puan
    - Özette eşleşme ek +1 puan
    - Puan 0-10 arasına normalize edilir
    
    Parametreler:
        query: Arama sorgusu (Türkçe veya İngilizce)
        max_results: Döndürülecek maksimum sonuç sayısı (varsayılan: 5)
    
    Döndürür:
        dict: Arama sonuçları
            - query (str): Orijinal sorgu
            - total_results (int): Bulunan toplam sonuç sayısı
            - returned (int): Döndürülen sonuç sayısı
            - results (list[dict]): Sonuç listesi, her biri:
                - title (str): Konu başlığı
                - source_url (str): Kaynak URL (simüle edilmiş)
                - summary (str): Konu özeti
                - relevance_score (float): Alaka puanı (0.0 - 1.0)
                - sections (list[str]): Alt bölümler
                - topic_id (str): Konu tanımlayıcısı
            - search_metadata (dict): Arama meta verileri
    
    Örnek:
        >>> sonuc = search("yapay zeka ajanları nasıl çalışır")
        >>> print(f"Bulunan: {sonuc['total_results']} sonuç")
        >>> for r in sonuc["results"]:
        ...     print(f"  {r['title']} (alaka: {r['relevance_score']:.2f})")
    """
    logger.info(f"Araştırma başlatıldı: '{query}' (maks: {max_results})")
    
    # ─── Sorguyu Anahtar Kelimelere Ayır ───
    # Türkçe ve İngilizce durma kelimeleri (stop words) filtrele
    stop_words = {
        "bir", "bu", "ve", "ile", "için", "de", "da", "mi", "mu",
        "ne", "nasıl", "nedir", "nelerdir", "gibi", "olan", "the",
        "is", "are", "and", "or", "for", "with", "how", "what",
        "a", "an", "in", "on", "at", "to", "of", "that",
    }
    
    query_lower = query.lower()
    query_words = [
        word.strip(".,;:!?()[]{}\"'")
        for word in query_lower.split()
        if word.strip(".,;:!?()[]{}\"'") not in stop_words
        and len(word.strip(".,;:!?()[]{}\"'")) > 1
    ]
    
    if not query_words:
        query_words = query_lower.split()[:3]
    
    logger.debug(f"Anahtar kelimeler: {query_words}")
    
    # ─── Alaka Puanı Hesapla ───
    scored_results: list[tuple[float, str, dict]] = []
    
    for topic_id, topic in KNOWLEDGE_BASE.items():
        score = 0.0
        
        # Anahtar kelime eşleşmesi
        for word in query_words:
            # Konu anahtar kelimeleri ile eşleşme
            for keyword in topic["keywords"]:
                if word in keyword or keyword in word:
                    score += 1.0
                    break  # Her sorgu kelimesi için en fazla 1 kez say
            
            # Başlıkta eşleşme (ek puan)
            if word in topic["title"].lower():
                score += 2.0
            
            # Özette eşleşme (ek puan)
            if word in topic["summary"].lower():
                score += 1.0
        
        # Normalize et (0.0 - 1.0 arası)
        max_possible = len(query_words) * 4.0  # keyword(1) + title(2) + summary(1)
        if max_possible > 0:
            normalized_score = min(score / max_possible, 1.0)
        else:
            normalized_score = 0.0
        
        # Minimum eşik: %10 alaka gerekli
        if normalized_score >= 0.1:
            scored_results.append((normalized_score, topic_id, topic))
    
    # ─── Sırala ve Kırp ───
    scored_results.sort(key=lambda x: x[0], reverse=True)
    total_found = len(scored_results)
    scored_results = scored_results[:max_results]
    
    # ─── Sonuçları Formatla ───
    results = []
    for score, topic_id, topic in scored_results:
        results.append({
            "title": topic["title"],
            "source_url": topic["source_url"],
            "summary": topic["summary"],
            "relevance_score": round(score, 3),
            "sections": topic["sections"],
            "topic_id": topic_id,
        })
    
    logger.info(
        f"Araştırma tamamlandı: {total_found} sonuç bulundu, "
        f"{len(results)} döndürüldü"
    )
    
    return {
        "query": query,
        "total_results": total_found,
        "returned": len(results),
        "results": results,
        "search_metadata": {
            "keywords_used": query_words,
            "knowledge_base_size": len(KNOWLEDGE_BASE),
            "min_relevance_threshold": 0.1,
            "timestamp": datetime.now().isoformat(),
        },
    }


# ═══════════════════════════════════════════════════════════════════
#  ARAÇ ŞEMASI
# ═══════════════════════════════════════════════════════════════════

DEEP_RESEARCH_SCHEMA = create_tool_schema(
    name="deep_research",
    description=(
        "Geniş kapsamlı bir bilgi tabanında derinlemesine araştırma yapar. "
        "Yapay zeka, MCP, LLM, Python, çok ajanlı sistemler, prompt "
        "mühendisliği, RAG ve daha birçok konuda detaylı sonuçlar döndürür. "
        "Her sonuçta başlık, kaynak URL, özet ve alaka puanı bulunur."
    ),
    parameters={
        "query": {
            "type": "string",
            "description": (
                "Araştırma sorgusu. Türkçe veya İngilizce olabilir. "
                "Örnek: 'yapay zeka ajanları nasıl çalışır', 'MCP nedir'"
            ),
        },
        "max_results": {
            "type": "number",
            "description": (
                "Döndürülecek maksimum sonuç sayısı (varsayılan: 5, maks: 10)"
            ),
        },
    },
    required=["query"],
)


# ─── Test Bloğu ───

if __name__ == "__main__":
    print("=" * 65)
    print("  Derinlemesine Araştırma Aracı - Test")
    print("=" * 65)
    
    # Test 1: Genel yapay zeka araması
    print("\n--- Test 1: 'yapay zeka ajanları' ---")
    sonuc = search("yapay zeka ajanları nasıl çalışır", max_results=3)
    print(f"  Bulunan: {sonuc['total_results']}, Döndürülen: {sonuc['returned']}")
    for r in sonuc["results"]:
        print(f"  [{r['relevance_score']:.3f}] {r['title']}")
    
    # Test 2: MCP araması
    print("\n--- Test 2: 'MCP protokolü tool' ---")
    sonuc = search("MCP protokolü tool sunucu", max_results=3)
    print(f"  Bulunan: {sonuc['total_results']}, Döndürülen: {sonuc['returned']}")
    for r in sonuc["results"]:
        print(f"  [{r['relevance_score']:.3f}] {r['title']}")
    
    # Test 3: Python araması
    print("\n--- Test 3: 'Python programlama kütüphane' ---")
    sonuc = search("Python programlama kütüphane", max_results=3)
    print(f"  Bulunan: {sonuc['total_results']}, Döndürülen: {sonuc['returned']}")
    for r in sonuc["results"]:
        print(f"  [{r['relevance_score']:.3f}] {r['title']}")
    
    # Test 4: İngilizce anahtar kelime
    print("\n--- Test 4: 'LLM token embedding' ---")
    sonuc = search("LLM token embedding", max_results=5)
    print(f"  Bulunan: {sonuc['total_results']}, Döndürülen: {sonuc['returned']}")
    for r in sonuc["results"]:
        print(f"  [{r['relevance_score']:.3f}] {r['title']}")
    
    # Test 5: Maliyet araması
    print("\n--- Test 5: 'maliyet bütçe optimizasyon' ---")
    sonuc = search("maliyet bütçe optimizasyon", max_results=2)
    print(f"  Bulunan: {sonuc['total_results']}, Döndürülen: {sonuc['returned']}")
    for r in sonuc["results"]:
        print(f"  [{r['relevance_score']:.3f}] {r['title']}")
        print(f"    Bölümler: {len(r['sections'])}")
    
    # Test 6: Bilgi tabanı boyutu
    print(f"\nBilgi Tabanı: {len(KNOWLEDGE_BASE)} konu")
    print(f"Meta veri: {sonuc['search_metadata']}")
    
    print("\nTest tamamlandı!")

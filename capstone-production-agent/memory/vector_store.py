"""
Vector Store - Vektör Benzerliği Deposu (Simüle Edilmiş)
=========================================================
TwinGraph Studio'nun "hafıza araması" motoru.

Vektör Deposu Nedir?
---------------------
Vektör deposu, metinleri sayısal vektörlere dönüştürüp saklayan ve
yeni bir sorguya en benzer metinleri bulan sistemdir. Bu, RAG
(Retrieval-Augmented Generation) yaklaşımının temel bileşenidir.

Nasıl Çalışır?
--------------
1. Metin → Embedding: Her metin bir vektöre dönüştürülür
2. Saklama: Vektörler metadata ile birlikte depolanır
3. Arama: Sorgu vektörü ile tüm vektörler karşılaştırılır
4. Sonuç: En benzer N belge döndürülür

Neden Simüle Ediyoruz?
-----------------------
Gerçek embedding modelleri (OpenAI text-embedding-3-small, sentence-transformers vb.)
API çağrısı veya GPU gerektirir. Bu modülde keyword tabanlı Jaccard benzerliği
kullanarak aynı mantığı gösteriyoruz:
- Her belgenin "embedding"i = anahtar kelime kümesi
- Benzerlik = iki kümenin kesişim/birleşim oranı (Jaccard)

Bu yaklaşım semantik anlam yakalamaz ama kavramsal benzerliği gösterir.

Production'da Bu Nasıl Olur?
-----------------------------
- OpenAI text-embedding-3-small veya text-embedding-3-large kullanılır
- Pinecone, Chroma, Weaviate gibi vektör veritabanları tercih edilir
- Cosine similarity ile gerçek semantik benzerlik hesaplanır
- Metadata filtreleme ve hybrid search desteklenir

TwinGraph'ta Rolü:
------------------
- Research Agent: Daha önce araştırılmış içerikleri bulur
- Writing Agent: Konuyla ilgili referans metinleri çeker
- Orchestrator: Önceki çalışmaları hatırlar

Kullanım:
    store = VectorStore()
    
    # Belge ekle
    doc_id = store.add_document(
        "MCP, agent'ların araçlara erişimini standartlaştırır.",
        {"konu": "MCP", "kaynak": "araştırma"}
    )
    
    # Benzerlik araması
    sonuclar = store.search("agent tool kullanımı", top_k=3)
    for doc, skor in sonuclar:
        print(f"  [{skor:.2f}] {doc['content'][:80]}...")
"""

import os
import sys
import uuid
import re
from dataclasses import dataclass, field
from typing import Any, Optional

# --- Shared modül erişimi ---
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from shared.telemetry.logger import get_logger
from shared.schemas.tool import create_tool_schema

logger = get_logger("memory.vector_store")


# ============================================================
# Veri Yapıları
# ============================================================

@dataclass
class Document:
    """
    Vektör deposunda saklanan belge.
    
    Her belge bir metin parçasını ve onun metadata'sını içerir.
    Embedding alanı, gerçek sistemlerde sayısal vektör olur;
    burada anahtar kelime kümesi olarak simüle edilir.
    
    Alanlar:
        id: Benzersiz belge kimliği (UUID)
        content: Belge içeriği (metin)
        metadata: Ek bilgiler (konu, kaynak, tarih, vb.)
        embedding: Simüle edilmiş embedding — anahtar kelime kümesi (set)
    """
    id: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: set = field(default_factory=set)


# ============================================================
# VectorStore Sınıfı
# ============================================================

class VectorStore:
    """
    Simüle edilmiş vektör benzerliği deposu.
    
    Metinleri anahtar kelime kümeleri olarak saklar ve Jaccard 
    benzerliği ile arama yapar. Gerçek bir vektör veritabanının
    temel mantığını gösterir.
    
    Jaccard Benzerliği:
        J(A, B) = |A ∩ B| / |A ∪ B|
        
        Örnek:
        A = {"ai", "agent", "tool"}, B = {"ai", "agent", "llm"}
        J = |{"ai", "agent"}| / |{"ai", "agent", "tool", "llm"}| = 2/4 = 0.50
    
    Bu yaklaşımın sınırları:
    - Eşanlamlı kelimeleri yakalayamaz ("yapay zeka" ≠ "AI")
    - Kelime sırasını dikkate almaz
    - Semantik anlam hesaplamaz
    
    Ancak, kavramsal benzerliği göstermek ve pipeline'ı
    test etmek için yeterlidir.
    
    Kullanım:
        store = VectorStore()
        
        # Belge ekle
        doc_id = store.add_document("MCP protokolü...", {"konu": "MCP"})
        
        # Arama yap
        sonuclar = store.search("protocol tool agent", top_k=3)
    """

    # Türkçe ve İngilizce stop-words (benzerlik hesabını iyileştirmek için)
    STOP_WORDS: set = {
        # Türkçe
        "bir", "bu", "ve", "ile", "için", "da", "de", "den", "dan",
        "çok", "daha", "gibi", "olan", "olarak", "ise", "ya", "hem",
        "her", "tüm", "ama", "ancak", "böylece", "dolayı", "ayrıca",
        "üzerinde", "üzerinden", "arasında", "sonra", "önce", "kadar",
        "olup", "olan", "veya", "iken", "etmek", "yapmak", "olmak",
        "sağlar", "yapar", "eder", "kullanır", "olan", "edilen",
        # İngilizce
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "can", "shall",
        "to", "of", "in", "for", "on", "with", "at", "by", "from",
        "as", "into", "through", "during", "before", "after", "and",
        "but", "or", "nor", "not", "so", "if", "than", "that", "this",
        "it", "its", "they", "them", "their", "we", "our", "you",
    }

    def __init__(self, pre_populate: bool = True):
        """
        VectorStore'u başlat.
        
        Parametreler:
            pre_populate: True ise AI konularında 30+ belge ile doldur.
                          Test ve demo için False yapılabilir.
        """
        self.documents: list[Document] = []
        self._id_index: dict[str, int] = {}  # doc_id → list index (hızlı erişim)

        if pre_populate:
            self._populate_ai_documents()
            logger.info(
                f"VectorStore başlatıldı: {len(self.documents)} belge yüklendi"
            )
        else:
            logger.info("VectorStore boş olarak başlatıldı")

    # --------------------------------------------------------
    # Temel İşlemler
    # --------------------------------------------------------

    def add_document(
        self,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Depoya yeni belge ekle.
        
        Metin otomatik olarak anahtar kelime kümesine dönüştürülür
        (simüle edilmiş embedding). Stop-words filtrelenir ve
        küçük harfe çevrilir.
        
        Parametreler:
            content: Belge metni
            metadata: Ek bilgiler (konu, kaynak, tarih, vb.)
        
        Döndürür:
            str: Belge ID'si
        
        Örnek:
            doc_id = store.add_document(
                "MCP (Model Context Protocol), LLM'lerin harici araçlara "
                "erişmesini standartlaştıran bir protokoldür.",
                {"konu": "MCP", "kaynak": "makale", "tarih": "2025-01"}
            )
        """
        doc_id = str(uuid.uuid4())[:8]
        embedding = self._text_to_keywords(content)

        doc = Document(
            id=doc_id,
            content=content,
            metadata=metadata or {},
            embedding=embedding,
        )

        self._id_index[doc_id] = len(self.documents)
        self.documents.append(doc)

        logger.debug(
            f"Belge eklendi: {doc_id} | "
            f"{len(content)} karakter | "
            f"{len(embedding)} anahtar kelime"
        )
        return doc_id

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.01,
        metadata_filter: Optional[dict[str, str]] = None,
    ) -> list[tuple[dict[str, Any], float]]:
        """
        Benzerlik araması yap.
        
        Sorguyu anahtar kelime kümesine dönüştürür, tüm belgelerle
        Jaccard benzerliğini hesaplar ve en benzer top_k belgeyi döndürür.
        
        İsteğe bağlı metadata filtresi ile sonuçlar daraltılabilir
        (örn: sadece "MCP" konulu belgeler).
        
        Parametreler:
            query: Arama sorgusu (doğal dil)
            top_k: Döndürülecek maksimum belge sayısı (varsayılan: 5)
            min_score: Minimum benzerlik skoru eşiği (varsayılan: 0.01)
            metadata_filter: Metadata filtreleme sözlüğü (isteğe bağlı)
        
        Döndürür:
            list[tuple[dict, float]]: (belge_dict, benzerlik_skoru) çiftleri,
                                      skorlarına göre azalan sırada
        
        Örnek:
            # Basit arama
            sonuclar = store.search("agent tool kullanımı", top_k=3)
            
            # Filtrelenmiş arama
            sonuclar = store.search(
                "hafıza sistemi",
                top_k=5,
                metadata_filter={"konu": "RAG"}
            )
        """
        logger.info(f"Vektör araması: '{query}' (top_k={top_k})")

        query_embedding = self._text_to_keywords(query)

        if not query_embedding:
            logger.warning("Sorgu anahtar kelime üretemedi — boş sonuç dönüyor")
            return []

        # Tüm belgelerle benzerlik hesapla
        scored_docs: list[tuple[Document, float]] = []

        for doc in self.documents:
            # Metadata filtresi (varsa)
            if metadata_filter:
                match = all(
                    doc.metadata.get(k, "").lower() == v.lower()
                    for k, v in metadata_filter.items()
                )
                if not match:
                    continue

            score = self._jaccard_similarity(query_embedding, doc.embedding)
            if score >= min_score:
                scored_docs.append((doc, score))

        # Skora göre sırala (azalan)
        scored_docs.sort(key=lambda x: x[1], reverse=True)

        # Sonuçları dict formatında döndür
        results: list[tuple[dict[str, Any], float]] = []
        for doc, score in scored_docs[:top_k]:
            results.append((
                {
                    "id": doc.id,
                    "content": doc.content,
                    "metadata": doc.metadata,
                },
                round(score, 4),
            ))

        logger.info(
            f"Arama sonucu: {len(results)} belge bulundu "
            f"(en yüksek skor: {results[0][1] if results else 0})"
        )
        return results

    def get_document(self, doc_id: str) -> Optional[dict[str, Any]]:
        """
        ID ile belge getir.
        
        Parametreler:
            doc_id: Belge ID'si
        
        Döndürür:
            Optional[dict]: Belge bilgisi veya None
        """
        idx = self._id_index.get(doc_id)
        if idx is not None and idx < len(self.documents):
            doc = self.documents[idx]
            return {
                "id": doc.id,
                "content": doc.content,
                "metadata": doc.metadata,
            }
        return None

    def get_stats(self) -> dict[str, Any]:
        """
        Depo istatistiklerini döndür.
        
        Döndürür:
            dict: Belge sayısı, ortalama uzunluk, konu dağılımı
        """
        if not self.documents:
            return {"total_documents": 0}

        topics: dict[str, int] = {}
        total_length = 0

        for doc in self.documents:
            total_length += len(doc.content)
            topic = doc.metadata.get("konu", "bilinmeyen")
            topics[topic] = topics.get(topic, 0) + 1

        return {
            "total_documents": len(self.documents),
            "average_length": total_length // len(self.documents),
            "topics": topics,
        }

    # --------------------------------------------------------
    # Yardımcı Metodlar
    # --------------------------------------------------------

    def _text_to_keywords(self, text: str) -> set:
        """
        Metni anahtar kelime kümesine dönüştür (simüle edilmiş embedding).
        
        İşlem adımları:
        1. Küçük harfe çevir
        2. Alfanümerik olmayan karakterleri kaldır
        3. Kelimelere ayır
        4. Stop-words filtrele
        5. 2 karakterden kısa kelimeleri kaldır
        
        Bu, gerçek embedding'in çok basitleştirilmiş halidir ama
        keyword-tabanlı benzerlik için yeterlidir.
        
        Parametreler:
            text: Dönüştürülecek metin
        
        Döndürür:
            set: Anahtar kelime kümesi
        """
        # Küçük harfe çevir
        text = text.lower()

        # Alfanümerik olmayan karakterleri boşlukla değiştir (Türkçe karakterleri koru)
        text = re.sub(r"[^a-zçğıöşü0-9\s\-]", " ", text)

        # Kelimelere ayır
        words = text.split()

        # Stop-words filtrele ve kısa kelimeleri kaldır
        keywords = {
            word.strip("-")
            for word in words
            if word not in self.STOP_WORDS and len(word) > 2
        }

        return keywords

    @staticmethod
    def _jaccard_similarity(set_a: set, set_b: set) -> float:
        """
        İki küme arasındaki Jaccard benzerliğini hesapla.
        
        Jaccard İndeksi:
            J(A, B) = |A ∩ B| / |A ∪ B|
            
        Değer aralığı: [0, 1]
        - 0: Hiç ortak eleman yok
        - 1: Kümeler aynı
        
        Parametreler:
            set_a: İlk küme
            set_b: İkinci küme
        
        Döndürür:
            float: Benzerlik skoru [0, 1]
        """
        if not set_a or not set_b:
            return 0.0

        intersection = len(set_a & set_b)
        union = len(set_a | set_b)

        return intersection / union if union > 0 else 0.0

    # --------------------------------------------------------
    # Önceden Doldurma (Pre-population)
    # --------------------------------------------------------

    def _populate_ai_documents(self) -> None:
        """
        AI ve agent konularında 30+ belge ile depoyu doldur.
        
        Bu belgeler, TwinGraph'ın demo ve test senaryolarında
        anlamlı arama sonuçları döndürmesini sağlar. Her belge:
        - 2-3 cümle uzunluğunda
        - Belirli bir konuyu kapsar
        - Metadata (konu, kaynak, tarih) içerir
        
        Kapsanan konular:
        - AI Agent mimarisi ve çalışma döngüsü
        - MCP protokolü ve tool calling
        - Reflection ve kalite iyileştirme
        - Multi-agent sistemler
        - RAG ve hafıza yönetimi
        - Prompt engineering teknikleri
        - Evaluation ve metrikler
        - İçerik üretim stratejileri
        - LLM model karşılaştırmaları
        - Maliyet optimizasyonu
        """
        docs = [
            # --- AI Agent ---
            {
                "content": (
                    "AI Agent, kullanıcı talimatlarını anlayan ve otonom adımlarla "
                    "görevleri tamamlayan bir yapay zeka sistemidir. Agent'lar "
                    "Think-Act-Observe döngüsünde çalışır: önce düşünür, sonra "
                    "araç çağırır, ardından sonucu gözlemler."
                ),
                "metadata": {"konu": "AI Agent", "kaynak": "eğitim", "tarih": "2025-01"},
            },
            {
                "content": (
                    "Agent loop (agent döngüsü), LLM tabanlı agent'ların temel "
                    "çalışma mekanizmasıdır. Her döngüde agent, mevcut durumu "
                    "değerlendirir, bir araç çağırır veya kullanıcıya cevap verir. "
                    "ReAct pattern, bu döngünün en yaygın uygulamasıdır."
                ),
                "metadata": {"konu": "AI Agent", "kaynak": "araştırma", "tarih": "2025-02"},
            },
            {
                "content": (
                    "Agentic AI sistemleri, geleneksel chatbot'lardan farklı olarak "
                    "çok adımlı görevleri bağımsız yürütebilir. Tool calling, "
                    "planlama ve hafıza yetenekleri ile donatılmış agent'lar, "
                    "karmaşık iş akışlarını otomatize edebilir."
                ),
                "metadata": {"konu": "AI Agent", "kaynak": "makale", "tarih": "2025-03"},
            },

            # --- MCP ---
            {
                "content": (
                    "MCP (Model Context Protocol), Anthropic tarafından geliştirilen "
                    "açık bir protokoldür. LLM'lerin harici araçlara, veri kaynaklarına "
                    "ve servislere standart bir şekilde erişmesini sağlar. USB-C'nin "
                    "fiziksel cihazlar için yaptığını, MCP dijital araçlar için yapar."
                ),
                "metadata": {"konu": "MCP", "kaynak": "dokümantasyon", "tarih": "2025-01"},
            },
            {
                "content": (
                    "MCP, client-server mimarisinde çalışır. MCP client (agent tarafı) "
                    "tool çağrılarını JSON-RPC formatında MCP server'a gönderir. "
                    "Server, tool'u çalıştırır ve sonucu döndürür. Bu standartlaşma "
                    "sayesinde bir agent, herhangi bir MCP server'a bağlanabilir."
                ),
                "metadata": {"konu": "MCP", "kaynak": "teknik", "tarih": "2025-02"},
            },
            {
                "content": (
                    "MCP tool tanımları JSON Schema formatında yapılır. Her tool'un "
                    "adı, açıklaması, parametreleri ve zorunlu alanları belirtilir. "
                    "LLM bu şemayı okuyarak tool'u doğru parametrelerle çağırabilir. "
                    "Tool versiyonlama ile geriye uyumluluk sağlanır."
                ),
                "metadata": {"konu": "MCP", "kaynak": "teknik", "tarih": "2025-02"},
            },

            # --- Tool Calling ---
            {
                "content": (
                    "Tool calling, LLM'in metin üretmenin ötesinde harici fonksiyonları "
                    "çağırabilme yeteneğidir. OpenAI function calling ve Anthropic tool "
                    "use, bu özelliğin farklı uygulamalarıdır. Agent'ların gerçek dünya "
                    "ile etkileşime girmesini sağlar."
                ),
                "metadata": {"konu": "Tool Calling", "kaynak": "eğitim", "tarih": "2025-01"},
            },
            {
                "content": (
                    "Tool çağrılarında idempotency önemlidir: aynı parametrelerle "
                    "tekrar çağrıldığında aynı sonucu veren tool'lar güvenlidir. "
                    "Yan etkili tool'lar (dosya yazma, API çağrısı) için retry ve "
                    "error handling mekanizmaları şarttır."
                ),
                "metadata": {"konu": "Tool Calling", "kaynak": "best-practice", "tarih": "2025-03"},
            },

            # --- Reflection ---
            {
                "content": (
                    "Reflection, agent'ın kendi çıktısını eleştirip iyileştirmesi "
                    "sürecidir. İlk taslak üretildikten sonra, ayrı bir LLM çağrısı "
                    "ile tutarsızlık, tekrar ve yüzeysellik tespit edilir. Ardından "
                    "orijinal agent bu eleştirilere göre içeriği geliştirir."
                ),
                "metadata": {"konu": "Reflection", "kaynak": "araştırma", "tarih": "2025-02"},
            },
            {
                "content": (
                    "Self-critique pattern'ında agent, kendi çıktısını puanlar ve "
                    "zayıf noktaları belirler. Puan belirli bir eşiğin altındaysa "
                    "iyileştirme döngüsü başlar. Bu iteratif süreç genellikle "
                    "2-3 turda optimal sonuca ulaşır."
                ),
                "metadata": {"konu": "Reflection", "kaynak": "araştırma", "tarih": "2025-03"},
            },
            {
                "content": (
                    "Reflection pattern'ı, özellikle uzun form içerik üretiminde "
                    "etkilidir. Bir Medium makalesi yazılırken, ilk taslak %60-70 "
                    "kalitedeyken, reflection sonrası %85-90 kaliteye ulaşabilir. "
                    "Ancak her tur ek maliyet getirir — cost-quality dengesi önemlidir."
                ),
                "metadata": {"konu": "Reflection", "kaynak": "deneyim", "tarih": "2025-04"},
            },

            # --- Multi-Agent ---
            {
                "content": (
                    "Multi-agent sistemlerde birden fazla agent, farklı rollerde "
                    "koordineli çalışır. Orchestrator pattern'da merkezi bir agent, "
                    "diğer agent'lara görev dağıtır ve sonuçları birleştirir. "
                    "Bu, karmaşık iş akışlarını yönetilebilir parçalara böler."
                ),
                "metadata": {"konu": "Multi-Agent", "kaynak": "araştırma", "tarih": "2025-03"},
            },
            {
                "content": (
                    "Agent'lar arası iletişimde mesaj geçirme (message passing) "
                    "ve paylaşılan hafıza (shared memory) iki temel yaklaşımdır. "
                    "Mesaj geçirme daha esnek, paylaşılan hafıza ise daha verimlidir. "
                    "TwinGraph her ikisini de kullanır."
                ),
                "metadata": {"konu": "Multi-Agent", "kaynak": "mimari", "tarih": "2025-04"},
            },
            {
                "content": (
                    "Multi-agent orkestrasyon, görev planlamayı ve agent seçimini "
                    "kapsar. Orchestrator, gelen talebi analiz eder, alt görevlere "
                    "böler ve her alt görevi en uygun agent'a atar. Agent'lar arası "
                    "bağımlılıklar DAG (Directed Acyclic Graph) olarak modellenebilir."
                ),
                "metadata": {"konu": "Multi-Agent", "kaynak": "teknik", "tarih": "2025-04"},
            },

            # --- RAG & Hafıza ---
            {
                "content": (
                    "RAG (Retrieval-Augmented Generation), LLM'in bilgi kısıtlarını "
                    "aşmak için harici bilgi kaynaklarından bilgi çekip prompt'a "
                    "ekleyen bir tekniktir. Bu sayede model, eğitim verisinde "
                    "olmayan güncel bilgilere dayanarak cevap üretir."
                ),
                "metadata": {"konu": "RAG", "kaynak": "eğitim", "tarih": "2025-01"},
            },
            {
                "content": (
                    "GraphRAG, klasik RAG'ı bilgi grafı ile zenginleştirir. Sadece "
                    "benzer metinleri bulmak yerine, kavramlar arası ilişkileri de "
                    "keşfeder. 'MCP nedir?' sorusu sorulduğunda, MCP'nin ilişkili "
                    "olduğu Tool Use, JSON Schema gibi kavramları da bağlam olarak sunar."
                ),
                "metadata": {"konu": "RAG", "kaynak": "araştırma", "tarih": "2025-03"},
            },
            {
                "content": (
                    "Vektör veritabanları (Pinecone, Chroma, Weaviate), embedding "
                    "vektörlerini saklayıp hızlı benzerlik araması yapan sistemlerdir. "
                    "Cosine similarity, dot product veya Euclidean distance ile "
                    "en yakın komşuları bulurlar. Milyonlarca belge üzerinde "
                    "milisaniye seviyesinde arama yapabilirler."
                ),
                "metadata": {"konu": "RAG", "kaynak": "teknik", "tarih": "2025-02"},
            },
            {
                "content": (
                    "Embedding modelleri, metni yüksek boyutlu vektörlere dönüştürür. "
                    "OpenAI text-embedding-3-small, 1536 boyutlu vektörler üretir. "
                    "Anlamsal olarak benzer metinler, vektör uzayında birbirine yakın "
                    "konumlanır — bu sayede semantik arama mümkün olur."
                ),
                "metadata": {"konu": "Embedding", "kaynak": "teknik", "tarih": "2025-02"},
            },

            # --- Prompt Engineering ---
            {
                "content": (
                    "Prompt engineering, LLM'den istenen çıktıyı elde etmek için "
                    "etkili komutlar tasarlama sürecidir. System prompt, few-shot "
                    "örnekler, Chain of Thought talimatları ve çıktı formatı "
                    "belirtme, temel tekniklerdir."
                ),
                "metadata": {"konu": "Prompt Engineering", "kaynak": "eğitim", "tarih": "2025-01"},
            },
            {
                "content": (
                    "Chain of Thought (CoT), LLM'i adım adım düşünmeye yönlendiren "
                    "bir tekniktir. 'Adım adım düşün' gibi talimatlar, karmaşık "
                    "akıl yürütme görevlerinde doğruluğu önemli ölçüde artırır. "
                    "Özellikle matematik ve mantık problemlerinde etkilidir."
                ),
                "metadata": {"konu": "Prompt Engineering", "kaynak": "araştırma", "tarih": "2025-02"},
            },
            {
                "content": (
                    "Few-shot prompting, LLM'e birkaç örnek vererek istenen "
                    "davranışı gösterme tekniğidir. 2-3 giriş-çıkış örneği, "
                    "modelin format ve stil anlayışını dramatik şekilde iyileştirir. "
                    "Zero-shot ise hiç örnek vermeden doğrudan görev tanımıdır."
                ),
                "metadata": {"konu": "Prompt Engineering", "kaynak": "eğitim", "tarih": "2025-02"},
            },

            # --- Evaluation ---
            {
                "content": (
                    "AI agent evaluation, agent'ın performansını sistematik olarak "
                    "ölçer. Doğruluk, maliyet, gecikme ve tutarlılık temel metriklerdir. "
                    "LLM-as-judge pattern'ı, bir LLM'in başka bir LLM'in çıktısını "
                    "değerlendirmesine dayanır."
                ),
                "metadata": {"konu": "Evaluation", "kaynak": "araştırma", "tarih": "2025-03"},
            },
            {
                "content": (
                    "Writing evaluation, üretilen metnin kalitesini çok boyutlu "
                    "olarak değerlendirir: tutarlılık (coherence), derinlik (depth), "
                    "özgünlük (originality) ve okunabilirlik (readability). Her boyut "
                    "1-10 arası puanlanır ve ağırlıklı ortalama alınır."
                ),
                "metadata": {"konu": "Evaluation", "kaynak": "teknik", "tarih": "2025-03"},
            },
            {
                "content": (
                    "Cost evaluation, agent pipeline'ının maliyet verimliliğini "
                    "ölçer. Token başına üretilen kelime, toplam API maliyeti ve "
                    "model routing tasarrufu temel metriklerdir. Bütçe koruması "
                    "için cost guard mekanizması kullanılır."
                ),
                "metadata": {"konu": "Evaluation", "kaynak": "best-practice", "tarih": "2025-04"},
            },

            # --- İçerik Üretim ---
            {
                "content": (
                    "Yapılandırılmış içerik üretimi, araştırma → taslak → eleştiri → "
                    "iyileştirme → son hal pipeline'ını izler. Her adım farklı bir "
                    "agent tarafından yürütülebilir: research agent araştırır, writing "
                    "agent yazar, reflection agent eleştirir."
                ),
                "metadata": {"konu": "Content Creation", "kaynak": "mimari", "tarih": "2025-04"},
            },
            {
                "content": (
                    "Medium makalesi formatı: başlık, giriş hook'u, ana bölümler "
                    "(alt başlıklarla), kod örnekleri, kaynakça ve sonuç. İdeal "
                    "uzunluk 1000-2000 kelime arasıdır. SEO açısından anahtar "
                    "kelimelerin doğal dağılımı önemlidir."
                ),
                "metadata": {"konu": "Content Creation", "kaynak": "rehber", "tarih": "2025-03"},
            },
            {
                "content": (
                    "LinkedIn post formatı: dikkat çekici hook (ilk 2 satır), değer "
                    "önerisi (3-5 madde), kişisel deneyim ve CTA (Call to Action). "
                    "Emojiler ve satır araları okunabilirliği artırır. İdeal uzunluk "
                    "150-300 kelimedir."
                ),
                "metadata": {"konu": "Content Creation", "kaynak": "rehber", "tarih": "2025-03"},
            },
            {
                "content": (
                    "Repurposing (içerik dönüştürme), uzun form içeriği farklı "
                    "platformlara uyarlamadır. Bir Medium makalesinden LinkedIn "
                    "postu, Twitter thread'i veya newsletter özeti üretilebilir. "
                    "Her format için ton, uzunluk ve yapı değişir."
                ),
                "metadata": {"konu": "Content Creation", "kaynak": "strateji", "tarih": "2025-04"},
            },

            # --- LLM Modelleri ---
            {
                "content": (
                    "GPT-4o, OpenAI'ın multimodal amiral gemisi modelidir. Metin, "
                    "görsel ve ses girişini destekler. Yüksek kaliteli içerik üretimi "
                    "için ideal ancak maliyeti GPT-4o-mini'ye göre 15-30 kat daha "
                    "fazladır. Kritik görevler için tercih edilir."
                ),
                "metadata": {"konu": "LLM", "kaynak": "karşılaştırma", "tarih": "2025-01"},
            },
            {
                "content": (
                    "GPT-4o-mini, hız ve maliyet açısından optimize edilmiş hafif "
                    "bir modeldir. Sınıflandırma, özetleme ve basit yazma görevlerinde "
                    "GPT-4o'ya yakın performans gösterirken çok daha ucuzdur. "
                    "Agent orkestrasyon ve araştırma görevleri için idealdir."
                ),
                "metadata": {"konu": "LLM", "kaynak": "karşılaştırma", "tarih": "2025-01"},
            },
            {
                "content": (
                    "Model routing stratejisi: basit görevlerde ucuz model (GPT-4o-mini), "
                    "kalite gerektiren görevlerde güçlü model (GPT-4o) kullanmak. "
                    "Görev karmaşıklığını otomatik değerlendirip model seçen bir "
                    "router, maliyeti %40-60 oranında azaltabilir."
                ),
                "metadata": {"konu": "LLM", "kaynak": "optimizasyon", "tarih": "2025-03"},
            },

            # --- Maliyet & Token ---
            {
                "content": (
                    "Token, LLM'de metin işlemenin temel birimidir. Ortalama olarak "
                    "1 İngilizce kelime ≈ 1.3 token, 1 Türkçe kelime ≈ 2-3 token'dır. "
                    "Maliyet, input ve output token sayısına göre hesaplanır. "
                    "GPT-4o: $2.50/1M input, $10.00/1M output token."
                ),
                "metadata": {"konu": "Maliyet", "kaynak": "fiyatlandırma", "tarih": "2025-01"},
            },
            {
                "content": (
                    "Cost guard, agent pipeline'ının bütçeyi aşmasını önleyen bir "
                    "mekanizmadır. Her agent çağrısı sonrası toplam token kullanımı "
                    "kontrol edilir. Bütçenin %80'ine ulaşıldığında uyarı verilir, "
                    "%100'de pipeline durdurulur veya ucuz modele geçilir."
                ),
                "metadata": {"konu": "Maliyet", "kaynak": "best-practice", "tarih": "2025-03"},
            },

            # --- Ek Konular ---
            {
                "content": (
                    "Hallucination (halüsinasyon), LLM'in gerçek olmayan bilgiyi "
                    "güvenilir bir şekilde sunmasıdır. RAG, citation verify ve "
                    "grounding teknikleri ile azaltılabilir. Agent sistemlerinde "
                    "her tool sonucu doğrulanmalıdır."
                ),
                "metadata": {"konu": "Güvenilirlik", "kaynak": "araştırma", "tarih": "2025-02"},
            },
            {
                "content": (
                    "Context window, LLM'in aynı anda işleyebildiği maksimum metin "
                    "uzunluğudur. GPT-4o 128K, Claude 200K token destekler. Uzun "
                    "belgelerle çalışırken chunking (parçalama) ve summarization "
                    "(özetleme) stratejileri kullanılır."
                ),
                "metadata": {"konu": "LLM", "kaynak": "teknik", "tarih": "2025-02"},
            },
            {
                "content": (
                    "Structured output, LLM'den JSON Schema'ya uygun çıktı almayı "
                    "sağlar. OpenAI'ın response_format özelliği ve Pydantic modelleri "
                    "ile agent'lar yapılandırılmış veri üretir. Bu, tool calling ve "
                    "veri pipeline'ları için kritik bir özelliktir."
                ),
                "metadata": {"konu": "LLM", "kaynak": "teknik", "tarih": "2025-03"},
            },
            {
                "content": (
                    "Middleware pattern, MCP tool çağrılarına logging, retry, timeout "
                    "ve rate limiting ekler. Her tool çağrısı middleware zincirinden "
                    "geçer. Bu, production-grade sistemlerde hata toleransı ve "
                    "gözlemlenebilirlik sağlar."
                ),
                "metadata": {"konu": "Altyapı", "kaynak": "mimari", "tarih": "2025-04"},
            },
        ]

        for doc_data in docs:
            self.add_document(doc_data["content"], doc_data["metadata"])


# ============================================================
# Tool Şeması
# ============================================================

def create_vector_search_tool_schema():
    """
    vector_search tool'u için MCP şeması oluştur.
    
    Bu şema, MCP sunucusuna kaydedilir ve LLM'in vektör
    deposunda benzerlik araması yapmasını sağlar.
    
    Döndürür:
        ToolSchema: MCP uyumlu tool şeması
    """
    return create_tool_schema(
        name="memory.vector_search",
        description=(
            "Vektör deposunda benzerlik araması yapar. Verilen sorguya "
            "en benzer belgeleri döndürür. Daha önce araştırılmış veya "
            "üretilmiş içerikleri bulmak için kullanılır."
        ),
        parameters={
            "query": {
                "type": "string",
                "description": "Arama sorgusu (doğal dil, örn: 'agent hafıza sistemi nasıl çalışır')",
            },
            "top_k": {
                "type": "number",
                "description": "Döndürülecek maksimum belge sayısı (varsayılan: 5)",
            },
            "topic_filter": {
                "type": "string",
                "description": "Konu filtresi (isteğe bağlı, örn: 'MCP', 'RAG')",
            },
        },
        required=["query"],
    )


# ============================================================
# Test & Demo
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("  TwinGraph Studio — Vector Store (Vektör Deposu) Demo")
    print("=" * 70)

    # Depo oluştur
    store = VectorStore()

    # İstatistikler
    stats = store.get_stats()
    print(f"\n📊 Depo İstatistikleri:")
    print(f"   Toplam belge: {stats['total_documents']}")
    print(f"   Ortalama uzunluk: {stats['average_length']} karakter")
    print(f"   Konu dağılımı: {stats['topics']}")

    # --- Arama 1: MCP ---
    print(f"\n{'─' * 70}")
    print("🔍 Arama: 'MCP protocol tool agent'")
    print("─" * 70)
    results = store.search("MCP protocol tool agent", top_k=5)
    for i, (doc, score) in enumerate(results, 1):
        print(f"   {i}. [{score:.4f}] [{doc['metadata'].get('konu', '?')}]")
        print(f"      {doc['content'][:100]}...")

    # --- Arama 2: Reflection ---
    print(f"\n{'─' * 70}")
    print("🔍 Arama: 'reflection kalite iyileştirme agent'")
    print("─" * 70)
    results = store.search("reflection kalite iyileştirme agent", top_k=3)
    for i, (doc, score) in enumerate(results, 1):
        print(f"   {i}. [{score:.4f}] [{doc['metadata'].get('konu', '?')}]")
        print(f"      {doc['content'][:100]}...")

    # --- Arama 3: Maliyet ---
    print(f"\n{'─' * 70}")
    print("🔍 Arama: 'token maliyet cost bütçe'")
    print("─" * 70)
    results = store.search("token maliyet cost bütçe", top_k=3)
    for i, (doc, score) in enumerate(results, 1):
        print(f"   {i}. [{score:.4f}] [{doc['metadata'].get('konu', '?')}]")
        print(f"      {doc['content'][:100]}...")

    # --- Filtrelenmiş Arama ---
    print(f"\n{'─' * 70}")
    print("🔍 Filtrelenmiş Arama: konu='RAG', sorgu='embedding vektör arama'")
    print("─" * 70)
    results = store.search(
        "embedding vektör arama benzerlik",
        top_k=3,
        metadata_filter={"konu": "RAG"},
    )
    for i, (doc, score) in enumerate(results, 1):
        print(f"   {i}. [{score:.4f}] {doc['content'][:100]}...")

    # --- Yeni Belge Ekleme ---
    print(f"\n{'─' * 70}")
    print("➕ Yeni Belge Ekleme ve Arama")
    print("─" * 70)
    new_id = store.add_document(
        "TwinGraph Studio, multi-agent mimarisiyle çalışan bir içerik "
        "üretim ve araştırma orkestratörüdür. GraphRAG hafıza sistemi "
        "ile kavramları birbirine bağlar.",
        {"konu": "TwinGraph", "kaynak": "proje", "tarih": "2025-05"},
    )
    print(f"   Eklenen belge ID: {new_id}")

    results = store.search("TwinGraph içerik üretim orkestratör", top_k=2)
    for i, (doc, score) in enumerate(results, 1):
        print(f"   {i}. [{score:.4f}] {doc['content'][:100]}...")

    # --- Tool Şeması ---
    print(f"\n{'─' * 70}")
    print("🛠️ Tool Şeması")
    print("─" * 70)
    schema = create_vector_search_tool_schema()
    import json
    print(f"   {json.dumps(schema.to_mcp_format(), indent=2, ensure_ascii=False)}")

    print(f"\n{'=' * 70}")
    print("  ✅ Vector Store demo tamamlandı!")
    print("=" * 70)

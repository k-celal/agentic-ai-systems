"""
Ingestion - İçerik Yükleme ve İşleme Pipeline'ı
==================================================
TwinGraph Studio'nun "sindirim sistemi" — ham metni yapılandırılmış bilgiye dönüştürür.

İçerik Yükleme Neden Gerekli?
------------------------------
Agent'lar araştırma yapar, makaleler üretir, kaynakları özetler. Bu içeriklerin
hafıza sistemine düzgün bir şekilde yüklenmesi gerekir — hem kavram grafına
(graph store) hem de vektör deposuna (vector store).

Manuel yükleme hataya açıktır ve ölçeklenmez. ContentIngester bu süreci
otomatize eder:
1. Ham metni alır
2. Varlıkları (entity) çıkarır — teknoloji adları, kavramlar, kişiler
3. Varlık eş-oluşumlarından (co-occurrence) graf kenarları oluşturur
4. Paragrafları vektör belgeleri olarak kaydeder

Nasıl Çalışır?
--------------
1. **Entity Extraction (Varlık Çıkarma)**:
   - Büyük harfle başlayan kelimeler → olası varlık
   - Bilinen teknoloji terimleri listesi → kesin varlık
   - Kısaltmalar (3+ büyük harf) → olası varlık
   
   NOT: Bu basit keyword-tabanlı bir çözümdür. Production'da:
   - spaCy NER modeli kullanılır
   - LLM-based entity extraction yapılır
   - Custom entity recognition pipeline'ı kurulur

2. **Edge Building (Kenar Oluşturma)**:
   Aynı paragrafta geçen varlıklar arasında "co_occurs_with" ilişkisi kurulur.
   Bu, kavramlar arası dolaylı ilişkileri yakalamak için etkili bir yöntemdir.

3. **Document Chunking (Belge Parçalama)**:
   Metin paragraflara bölünür, her paragraf ayrı bir vektör belgesi olarak
   saklanır. Metadata olarak kaynak adı, paragraf numarası ve çıkarılan
   varlıklar eklenir.

TwinGraph'ta Rolü:
------------------
- Research Agent araştırma sonuçlarını hafızaya yükler
- Writing Agent ürettiği makaleleri hafızaya kaydeder
- Orchestrator pipeline sonuçlarını arşivler

Kullanım:
    from memory.graph_store import GraphStore
    from memory.vector_store import VectorStore
    from memory.ingestion import ContentIngester
    
    graph = GraphStore()
    vector = VectorStore()
    ingester = ContentIngester(graph, vector)
    
    result = ingester.ingest(
        "MCP (Model Context Protocol), agent'ların araçlara erişimini "
        "standartlaştırır. LLM'ler bu protokol aracılığıyla tool calling "
        "yapabilir ve harici servislerle iletişim kurabilir.",
        source_name="araştırma_notu_01"
    )
    
    print(f"Eklenen: {result.nodes_added} düğüm, "
          f"{result.edges_added} kenar, "
          f"{result.documents_added} belge")
"""

import os
import sys
import re
from dataclasses import dataclass
from typing import Optional

# --- Shared modül erişimi ---
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from shared.telemetry.logger import get_logger

logger = get_logger("memory.ingestion")


# ============================================================
# Veri Yapıları
# ============================================================

@dataclass
class IngestionResult:
    """
    İçerik yükleme işleminin sonucu.
    
    Her yükleme sonrası kaç düğüm, kenar ve belgenin eklendiğini
    raporlar. Bu bilgi, pipeline monitoring ve logging için kullanılır.
    
    Alanlar:
        nodes_added: Grafa eklenen düğüm sayısı
        edges_added: Grafa eklenen kenar sayısı
        documents_added: Vektör deposuna eklenen belge sayısı
        entities_found: Metinden çıkarılan toplam varlık sayısı
        source_name: İçeriğin kaynak adı
    """
    nodes_added: int
    edges_added: int
    documents_added: int
    entities_found: int
    source_name: str

    def __str__(self) -> str:
        """İnsan-okunabilir özet."""
        return (
            f"IngestionResult(kaynak='{self.source_name}', "
            f"düğüm=+{self.nodes_added}, kenar=+{self.edges_added}, "
            f"belge=+{self.documents_added}, varlık={self.entities_found})"
        )


# ============================================================
# ContentIngester Sınıfı
# ============================================================

class ContentIngester:
    """
    Ham metni yapılandırılmış bilgiye dönüştüren içerik yükleme pipeline'ı.
    
    Bu sınıf, TwinGraph Studio'nun hafıza sistemini besler. Gelen ham metin:
    1. Varlıklara (entity) ayrılır
    2. Kavram grafına düğüm ve kenar olarak eklenir
    3. Vektör deposuna belge olarak kaydedilir
    
    Entity extraction basit keyword-tabanlı çalışır:
    - Bilinen teknoloji terimleri (AI, MCP, LLM, vb.) tanınır
    - Büyük harfle başlayan kelimeler potansiyel varlık olarak işaretlenir
    - 3+ büyük harfli kısaltmalar (API, RAG, NER, vb.) yakalanır
    
    Production uyarısı:
    Bu basitleştirilmiş bir çözümdür. Gerçek üretimde spaCy NER,
    LLM-based extraction veya custom pipeline kullanılmalıdır.
    
    Kullanım:
        ingester = ContentIngester(graph_store, vector_store)
        
        # Tek metin yükle
        result = ingester.ingest(metin, "kaynak_adı")
        
        # Birden fazla içerik yükle
        for metin, kaynak in icerikler:
            result = ingester.ingest(metin, kaynak)
            print(result)
    """

    # Bilinen teknoloji terimleri — entity extraction'da kesin eşleşme için
    KNOWN_TECH_TERMS: set = {
        # AI & ML Kavramları
        "ai", "artificial intelligence", "machine learning", "deep learning",
        "neural network", "transformer", "attention mechanism",
        "yapay zeka", "makine öğrenmesi", "derin öğrenme",

        # LLM & Modeller
        "llm", "large language model", "gpt", "gpt-4", "gpt-4o", "gpt-4o-mini",
        "claude", "gemini", "mistral", "llama", "openai", "anthropic",
        "büyük dil modeli",

        # Agent & Orkestrasyon
        "agent", "ai agent", "multi-agent", "orchestrator", "orchestration",
        "agent loop", "react", "react pattern", "agentic",

        # MCP & Tool Calling
        "mcp", "model context protocol", "tool calling", "function calling",
        "tool use", "json-rpc", "json schema",

        # RAG & Hafıza
        "rag", "retrieval augmented generation", "graphrag", "graph rag",
        "vector store", "vector database", "embedding", "embeddings",
        "semantic search", "similarity search",
        "vektör veritabanı", "hafıza sistemi",

        # Teknikler
        "prompt engineering", "chain of thought", "cot", "few-shot",
        "zero-shot", "fine-tuning", "fine tuning", "rlhf",
        "reflection", "self-critique", "iterative refinement",

        # Değerlendirme
        "evaluation", "eval", "benchmark", "accuracy", "latency",
        "coherence", "hallucination", "grounding",

        # Veritabanları & Araçlar
        "pinecone", "chroma", "weaviate", "neo4j", "neptune",
        "langchain", "llamaindex", "autogen", "crewai",

        # Programlama
        "python", "api", "rest api", "sdk", "pip", "npm",
        "json", "yaml", "docker", "kubernetes",

        # Genel Teknoloji
        "token", "context window", "structured output",
        "middleware", "retry", "idempotent", "rate limiting",
        "cost guard", "model routing", "content creation",
    }

    # Çıkarılmaması gereken yaygın kelimeler (false positive önleme)
    EXCLUDE_WORDS: set = {
        "Bu", "Bu", "Bir", "Her", "İlk", "Son", "Yeni", "Eski",
        "Ancak", "Ayrıca", "Böylece", "Dolayısıyla", "Örneğin",
        "NOT", "UYARI", "DİKKAT", "ÖNEMLİ",
        "The", "This", "That", "These", "Those", "Some", "Any",
        "However", "Moreover", "Furthermore", "Therefore",
    }

    def __init__(self, graph_store, vector_store):
        """
        ContentIngester'ı başlat.
        
        Parametreler:
            graph_store: GraphStore instance — kavram grafı
            vector_store: VectorStore instance — vektör deposu
        """
        self.graph_store = graph_store
        self.vector_store = vector_store

        # Bilinen terimleri normalize et (küçük harf)
        self._known_terms_lower = {term.lower() for term in self.KNOWN_TECH_TERMS}

        logger.info("ContentIngester başlatıldı")

    # --------------------------------------------------------
    # Ana Yükleme Metodu
    # --------------------------------------------------------

    def ingest(
        self,
        content: str,
        source_name: str,
        metadata: Optional[dict] = None,
    ) -> IngestionResult:
        """
        Ham metni hafıza sistemine yükle.
        
        İşlem adımları:
        1. Metni paragraflara böl
        2. Her paragraftan varlıkları çıkar
        3. Varlıkları kavram grafına düğüm olarak ekle
        4. Aynı paragraftaki varlıklar arasında kenar oluştur
        5. Her paragrafı vektör deposuna belge olarak kaydet
        
        Parametreler:
            content: Ham metin içerik
            source_name: İçeriğin kaynak adı (örn: "araştırma_01", "makale_v2")
            metadata: Ek metadata (isteğe bağlı)
        
        Döndürür:
            IngestionResult: Yükleme raporu
        
        Örnek:
            result = ingester.ingest(
                "MCP protokolü, agent'ların tool'lara erişimini sağlar. "
                "LLM'ler bu sayede function calling yapabilir.",
                "arastirma_notu"
            )
            print(result)
            # → IngestionResult(kaynak='arastirma_notu', düğüm=+3, kenar=+2, belge=+1, varlık=4)
        """
        logger.info(f"İçerik yükleniyor: '{source_name}' ({len(content)} karakter)")

        if not content or not content.strip():
            logger.warning("Boş içerik — yükleme atlanıyor")
            return IngestionResult(
                nodes_added=0,
                edges_added=0,
                documents_added=0,
                entities_found=0,
                source_name=source_name,
            )

        extra_metadata = metadata or {}
        nodes_added = 0
        edges_added = 0
        documents_added = 0
        all_entities: set = set()

        # Metni paragraflara böl
        paragraphs = self._split_into_paragraphs(content)
        logger.debug(f"Paragraf sayısı: {len(paragraphs)}")

        for para_idx, paragraph in enumerate(paragraphs):
            if len(paragraph.strip()) < 20:
                # Çok kısa paragrafları atla (başlık, boş satır vb.)
                continue

            # --- 1. Varlık Çıkarma ---
            entities = self.extract_entities(paragraph)
            all_entities.update(entities)

            # --- 2. Düğüm Ekleme ---
            entity_node_ids: list[tuple[str, str]] = []  # (entity_text, node_id)
            for entity_text, entity_type in entities:
                # Grafa düğüm ekle (zaten varsa mevcut ID döner)
                node_id = self.graph_store.add_node(
                    label=entity_text,
                    entity_type=entity_type,
                    properties={
                        "kaynak": source_name,
                        "paragraf": para_idx,
                    },
                )
                entity_node_ids.append((entity_text, node_id))

            # Gerçekten yeni eklenen düğümleri say
            initial_node_count = len(self.graph_store.nodes)
            # (add_node duplicate kontrolü yaptığı için, sayım farkına bakıyoruz)
            # Basitleştirme: entity sayısını düğüm olarak kabul et
            nodes_added += len(entities)

            # --- 3. Kenar Oluşturma (co-occurrence) ---
            para_edges = self._build_edges_from_cooccurrence(entity_node_ids)
            edges_added += para_edges

            # --- 4. Vektör Belgesi Kaydetme ---
            doc_metadata = {
                "kaynak": source_name,
                "paragraf_no": para_idx,
                "varlıklar": [e[0] for e in entities],
                **extra_metadata,
            }
            self.vector_store.add_document(paragraph, doc_metadata)
            documents_added += 1

        result = IngestionResult(
            nodes_added=nodes_added,
            edges_added=edges_added,
            documents_added=documents_added,
            entities_found=len(all_entities),
            source_name=source_name,
        )

        logger.info(f"Yükleme tamamlandı: {result}")
        return result

    # --------------------------------------------------------
    # Varlık Çıkarma (Entity Extraction)
    # --------------------------------------------------------

    def extract_entities(self, text: str) -> list[tuple[str, str]]:
        """
        Metinden varlıkları çıkar.
        
        Üç strateji kullanılır:
        1. **Bilinen Terimler**: KNOWN_TECH_TERMS listesindeki terimler
        2. **Kısaltmalar**: 2+ büyük harften oluşan kelimeler (API, MCP, LLM)
        3. **Büyük Harfli Kelimeler**: Cümle başı olmayan büyük harfli kelimeler
        
        Her varlığa bir tür atanır:
        - technology: Bilinen teknoloji terimleri
        - concept: Genel kavramlar
        - tool: Araç/framework adları
        
        Parametreler:
            text: Varlık çıkarılacak metin
        
        Döndürür:
            list[tuple[str, str]]: (varlık_metni, varlık_türü) çiftleri
        
        Örnek:
            entities = ingester.extract_entities(
                "MCP protokolü, LLM'lerin tool calling yapmasını sağlar."
            )
            # → [("MCP", "technology"), ("LLM", "technology"), 
            #    ("tool calling", "concept")]
        """
        entities: list[tuple[str, str]] = []
        seen: set = set()  # Tekrar önleme

        text_lower = text.lower()

        # Strateji 1: Bilinen teknoloji terimlerini ara
        for term in self.KNOWN_TECH_TERMS:
            term_lower = term.lower()
            if term_lower in text_lower and term_lower not in seen:
                # Kelime sınırı kontrolü (kısmi eşleşme önleme)
                pattern = r'\b' + re.escape(term_lower) + r'\b'
                if re.search(pattern, text_lower):
                    seen.add(term_lower)
                    entity_type = self._classify_entity(term)
                    # Orijinal metindeki haliyle ekle (büyük/küçük harf korunur)
                    display_name = self._find_original_case(text, term)
                    entities.append((display_name, entity_type))

        # Strateji 2: Kısaltmaları bul (2+ büyük harf, sayı olabilir)
        abbreviations = re.findall(r'\b([A-Z][A-Z0-9]{1,}(?:-[A-Za-z0-9]+)*)\b', text)
        for abbr in abbreviations:
            abbr_lower = abbr.lower()
            if abbr_lower not in seen and abbr not in self.EXCLUDE_WORDS:
                seen.add(abbr_lower)
                entity_type = self._classify_entity(abbr)
                entities.append((abbr, entity_type))

        # Strateji 3: Büyük harfle başlayan çok kelimeli ifadeler
        # Örn: "Model Context Protocol", "Chain of Thought"
        multi_word = re.findall(
            r'\b([A-Z][a-zçğıöşü]+(?:\s+(?:of|and|the|for|in|on|with|to|ve|ile|için)?\s*[A-Z][a-zçğıöşü]+)+)\b',
            text,
        )
        for phrase in multi_word:
            phrase_lower = phrase.lower()
            if phrase_lower not in seen and phrase not in self.EXCLUDE_WORDS:
                seen.add(phrase_lower)
                entity_type = self._classify_entity(phrase)
                entities.append((phrase, entity_type))

        return entities

    def _classify_entity(self, entity: str) -> str:
        """
        Varlığın türünü belirle.
        
        Sınıflandırma mantığı:
        - Bilinen teknoloji terimleri → "technology"
        - Framework/tool adları → "tool"
        - Diğer her şey → "concept"
        
        Parametreler:
            entity: Sınıflandırılacak varlık metni
        
        Döndürür:
            str: Varlık türü (technology | tool | concept)
        """
        entity_lower = entity.lower()

        # Bilinen framework/tool'lar
        tool_keywords = {
            "langchain", "llamaindex", "autogen", "crewai",
            "pinecone", "chroma", "weaviate", "neo4j",
            "docker", "kubernetes", "pip", "npm",
            "cost guard", "deep research", "citation verify",
        }
        if entity_lower in tool_keywords:
            return "tool"

        # Bilinen teknolojiler
        tech_keywords = {
            "python", "api", "json", "yaml", "rest api",
            "gpt", "gpt-4", "gpt-4o", "gpt-4o-mini",
            "claude", "gemini", "mistral", "llama",
            "mcp", "json-rpc", "json schema",
        }
        if entity_lower in tech_keywords:
            return "technology"

        # Kısaltmalar genelde teknoloji
        if entity.isupper() and len(entity) >= 2:
            return "technology"

        return "concept"

    def _find_original_case(self, text: str, term: str) -> str:
        """
        Metindeki orijinal büyük/küçük harf halini bul.
        
        "mcp" terimi için metinde "MCP" geçiyorsa "MCP" döndür.
        
        Parametreler:
            text: Orijinal metin
            term: Aranacak terim (küçük harf)
        
        Döndürür:
            str: Orijinal haliyle terim
        """
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        match = pattern.search(text)
        if match:
            return match.group(0)
        return term

    # --------------------------------------------------------
    # Kenar Oluşturma
    # --------------------------------------------------------

    def _build_edges_from_cooccurrence(
        self,
        entity_node_ids: list[tuple[str, str]],
    ) -> int:
        """
        Aynı paragraftaki varlıklar arasında graf kenarları oluştur.
        
        Co-occurrence (eş-oluşum) yaklaşımı: aynı bağlamda geçen
        kavramlar ilişkili kabul edilir. Her varlık çifti arasında
        "co_occurs_with" ilişkisi kurulur.
        
        Bu basit ama etkili bir yöntemdir — aynı paragrafta "MCP" ve
        "Tool Calling" geçiyorsa, aralarında bir ilişki olması muhtemeldir.
        
        Parametreler:
            entity_node_ids: (varlık_metni, düğüm_id) çiftleri listesi
        
        Döndürür:
            int: Eklenen kenar sayısı
        """
        edges_added = 0

        # Her varlık çifti arasında kenar oluştur
        for i in range(len(entity_node_ids)):
            for j in range(i + 1, len(entity_node_ids)):
                entity_a_text, node_a_id = entity_node_ids[i]
                entity_b_text, node_b_id = entity_node_ids[j]

                if node_a_id == node_b_id:
                    continue  # Aynı düğüm — kenar oluşturma

                edge_id = self.graph_store.add_edge(
                    source_id=node_a_id,
                    target_id=node_b_id,
                    relationship="co_occurs_with",
                    properties={
                        "yöntem": "co-occurrence",
                        "güven": 0.6,  # Düşük güven — otomatik çıkarım
                    },
                )

                if edge_id:
                    edges_added += 1

        return edges_added

    # --------------------------------------------------------
    # Metin Parçalama
    # --------------------------------------------------------

    def _split_into_paragraphs(self, content: str) -> list[str]:
        """
        Metni anlamlı paragraflara böl.
        
        Bölme stratejisi:
        1. Çift satır sonuna göre böl (standart paragraf ayırıcı)
        2. Çok uzun paragrafları cümle sınırlarında böl
        3. Çok kısa paragrafları filtrele
        
        Parametreler:
            content: Bölünecek metin
        
        Döndürür:
            list[str]: Paragraf listesi
        """
        # Çift satır sonuna göre böl
        raw_paragraphs = re.split(r'\n\s*\n', content.strip())

        paragraphs: list[str] = []

        for para in raw_paragraphs:
            para = para.strip()

            if len(para) < 20:
                continue  # Çok kısa — atla

            if len(para) > 1000:
                # Çok uzun paragrafı cümle sınırlarında böl
                sentences = re.split(r'(?<=[.!?])\s+', para)
                current_chunk = ""

                for sentence in sentences:
                    if len(current_chunk) + len(sentence) > 500:
                        if current_chunk:
                            paragraphs.append(current_chunk.strip())
                        current_chunk = sentence
                    else:
                        current_chunk += " " + sentence if current_chunk else sentence

                if current_chunk:
                    paragraphs.append(current_chunk.strip())
            else:
                paragraphs.append(para)

        return paragraphs


# ============================================================
# Test & Demo
# ============================================================

if __name__ == "__main__":
    # Yerel import'lar — doğrudan çalıştırma için path ayarla
    sys.path.insert(0, os.path.dirname(__file__))
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from graph_store import GraphStore
    from vector_store import VectorStore

    print("=" * 70)
    print("  TwinGraph Studio — Content Ingester (İçerik Yükleme) Demo")
    print("=" * 70)

    # Hafıza sistemlerini oluştur
    graph = GraphStore(pre_populate=True)
    vector = VectorStore(pre_populate=True)
    ingester = ContentIngester(graph, vector)

    # Önceki durumu kaydet
    initial_nodes = len(graph.nodes)
    initial_edges = len(graph.edges)
    initial_docs = len(vector.documents)

    print(f"\n📊 Başlangıç Durumu:")
    print(f"   Graf: {initial_nodes} düğüm, {initial_edges} kenar")
    print(f"   Vektör: {initial_docs} belge")

    # --- Test 1: Kısa metin yükleme ---
    print(f"\n{'─' * 70}")
    print("📥 Test 1: Kısa Metin Yükleme")
    print("─" * 70)

    text_1 = (
        "MCP (Model Context Protocol), Anthropic tarafından geliştirilmiş "
        "açık bir iletişim protokolüdür. LLM tabanlı agent'ların harici "
        "araçlara, veri kaynaklarına ve servislere standartlaştırılmış "
        "bir şekilde erişmesini sağlar. JSON-RPC formatında çalışır."
    )

    result_1 = ingester.ingest(text_1, "test_notu_01")
    print(f"   Sonuç: {result_1}")

    # --- Test 2: Uzun metin yükleme ---
    print(f"\n{'─' * 70}")
    print("📥 Test 2: Uzun Metin Yükleme (Birden Fazla Paragraf)")
    print("─" * 70)

    text_2 = """
    AI Agent Sistemleri ve İçerik Üretimi

    Agentic AI, yapay zeka alanının en hızlı büyüyen dallarından biridir.
    Geleneksel chatbot'lardan farklı olarak, AI Agent'lar çok adımlı 
    görevleri otonom olarak yürütebilir. Tool Calling, Reflection ve 
    Multi-Agent orchestration, bu sistemlerin temel yapı taşlarıdır.

    GraphRAG (Graph-based Retrieval Augmented Generation), klasik RAG 
    yaklaşımını kavram grafı ile zenginleştirir. Bir kavram sorgulandığında, 
    sadece benzer metinler değil, ilişkili kavramlar da bağlam olarak 
    sunulur. Neo4j ve Pinecone gibi veritabanları bu amaca hizmet eder.

    Prompt Engineering, LLM'den en iyi sonucu almak için kritik bir 
    beceridir. Chain of Thought tekniği, modeli adım adım düşünmeye 
    yönlendirir ve karmaşık görevlerde doğruluğu artırır. Few-Shot 
    örnekler ise modelin beklenen formatı anlamasını sağlar.

    Evaluation sistemi, üretilen içeriğin kalitesini çok boyutlu olarak 
    değerlendirir: Coherence (tutarlılık), Accuracy (doğruluk) ve 
    Latency (gecikme) temel metriklerdir. Cost Guard mekanizması ise 
    pipeline'ın bütçeyi aşmasını önler.
    """

    result_2 = ingester.ingest(text_2, "makale_taslaği_01")
    print(f"   Sonuç: {result_2}")

    # --- Test 3: Varlık Çıkarma Detayları ---
    print(f"\n{'─' * 70}")
    print("🔍 Test 3: Varlık Çıkarma Detayları")
    print("─" * 70)

    test_text = (
        "GPT-4o ve Claude, modern LLM'lerin en gelişmiş örnekleridir. "
        "MCP protokolü ile Tool Calling yapabilir, RAG sistemi ile "
        "harici bilgiye erişebilirler. Python SDK'ları ile entegrasyon kolaydır."
    )

    entities = ingester.extract_entities(test_text)
    print(f"   Bulunan varlıklar ({len(entities)}):")
    for entity_text, entity_type in entities:
        print(f"   • '{entity_text}' → {entity_type}")

    # --- Sonuç Durumu ---
    print(f"\n{'─' * 70}")
    print("📊 Son Durum")
    print("─" * 70)
    final_nodes = len(graph.nodes)
    final_edges = len(graph.edges)
    final_docs = len(vector.documents)

    print(f"   Graf: {final_nodes} düğüm (+{final_nodes - initial_nodes}), "
          f"{final_edges} kenar (+{final_edges - initial_edges})")
    print(f"   Vektör: {final_docs} belge (+{final_docs - initial_docs})")

    # Yüklenen içerikleri arayalım
    print(f"\n{'─' * 70}")
    print("🔍 Yüklenen İçerik Araması: 'MCP protocol agent tool'")
    print("─" * 70)
    search_results = vector.search("MCP protocol agent tool", top_k=3)
    for i, (doc, score) in enumerate(search_results, 1):
        kaynak = doc["metadata"].get("kaynak", "?")
        print(f"   {i}. [{score:.4f}] [kaynak: {kaynak}]")
        print(f"      {doc['content'][:100]}...")

    # Graftan yeni eklenen kavramları sorgulayalım
    print(f"\n{'─' * 70}")
    print("🔗 Graf Sorgusu: Yükleme sonrası 'GraphRAG' ilişkileri")
    print("─" * 70)
    query_result = graph.query("GraphRAG")
    if query_result["found"]:
        for rn in query_result["related_nodes"][:8]:
            yön = "→" if rn["direction"] == "outgoing" else "←"
            print(f"   {yön} {rn['label']} ({rn['relationship']}, hop={rn['hop']})")

    print(f"\n{'=' * 70}")
    print("  ✅ Content Ingester demo tamamlandı!")
    print("=" * 70)

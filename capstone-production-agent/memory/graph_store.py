"""
Graph Store - Kavram Grafı (Simüle Edilmiş GraphRAG)
=====================================================
TwinGraph Studio'nun bilgi haritası.

GraphRAG Nedir?
---------------
GraphRAG (Graph-based Retrieval Augmented Generation), kavramlar arası ilişkileri
bir graf yapısında saklayarak LLM'e zengin bağlam sağlayan bir yaklaşımdır.

Klasik RAG sadece "benzer metinleri" bulur. GraphRAG ise kavramlar arasındaki
**ilişkileri** de keşfeder:
- "MCP nedir?" → MCP → enables → Tool Use → used_by → AI Agent
- "Reflection nasıl çalışır?" → Reflection → improves → Content Quality → measured_by → Eval

Bu sayede agent, sadece doğrudan eşleşen bilgileri değil, **ilişkili kavram ağını**
da kullanarak daha zengin ve tutarlı içerik üretir.

Neden Simüle Ediyoruz?
-----------------------
Gerçek bir GraphRAG sistemi (Neo4j, Amazon Neptune vb.) harici veritabanı gerektirir.
Bu modülde in-memory dict tabanlı bir graf kullanarak aynı mantığı gösteriyoruz:
- Düğümler (nodes): Kavramlar, kişiler, teknolojiler, araçlar
- Kenarlar (edges): İlişki türleri (uses, enables, improves, includes, vb.)
- Sorgulama: 2-hop komşuluk keşfi

Production'da Bu Nasıl Olur?
-----------------------------
- Neo4j veya Amazon Neptune gibi bir graf veritabanı kullanılır
- Entity extraction için NER (Named Entity Recognition) modelleri çalışır
- İlişki çıkarımı için LLM-based relation extraction yapılır
- Cypher veya SPARQL sorgu dilleri kullanılır

TwinGraph'ta Rolü:
------------------
- Research Agent: Araştırma öncesi ilişkili kavramları keşfeder
- Writing Agent: Makale yazarken bağlam ve yapı oluşturur
- Orchestrator: Görev planlarken kavram haritasını kullanır

Kullanım:
    graph = GraphStore()
    
    # Kavram sorgula
    sonuc = graph.query("MCP")
    print(sonuc["related_nodes"])  # İlişkili kavramlar
    
    # Alt graf çıkar
    subgraph = graph.get_subgraph("AI Agent")
    print(subgraph["nodes"])  # Komşu düğümler
    print(subgraph["edges"])  # Bağlantılar
"""

import os
import sys
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

# --- Shared modül erişimi ---
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from shared.telemetry.logger import get_logger
from shared.schemas.tool import create_tool_schema

logger = get_logger("memory.graph_store")


# ============================================================
# Veri Yapıları
# ============================================================

@dataclass
class NodeData:
    """
    Graf düğümü — bir kavramı temsil eder.
    
    Her düğüm bir varlıktır: teknoloji, kavram, kişi veya araç.
    Properties alanı ek bilgi taşır (açıklama, kaynak, tarih vb.)
    
    Alanlar:
        id: Benzersiz düğüm kimliği (UUID)
        label: Düğüm etiketi, okunabilir ad (örn: "MCP", "AI Agent")
        entity_type: Varlık türü — concept | person | technology | tool
        properties: Ek özellikler sözlüğü (açıklama, url, vb.)
    """
    id: str
    label: str
    entity_type: str  # concept, person, technology, tool
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class Edge:
    """
    Graf kenarı — iki kavram arasındaki ilişki.
    
    İlişki türleri:
        - uses: "X, Y'yi kullanır" (AI Agent → uses → LLM)
        - enables: "X, Y'yi mümkün kılar" (MCP → enables → Tool Use)
        - improves: "X, Y'yi iyileştirir" (Reflection → improves → Content Quality)
        - includes: "X, Y'yi içerir" (LLM → includes → GPT-4o)
        - related_to: "X, Y ile ilişkilidir" (genel ilişki)
        - part_of: "X, Y'nin parçasıdır" (Retrieval → part_of → RAG)
        - measures: "X, Y'yi ölçer" (Evaluation → measures → Accuracy)
        - requires: "X, Y'yi gerektirir" (Content Creation → requires → Research)
        - produces: "X, Y'yi üretir"
        - combined_with: "X, Y ile birleşir"
    
    Alanlar:
        id: Benzersiz kenar kimliği
        source: Kaynak düğüm ID'si
        target: Hedef düğüm ID'si
        relationship: İlişki türü
        properties: Ek özellikler (ağırlık, tarih, vb.)
    """
    id: str
    source: str
    target: str
    relationship: str
    properties: dict[str, Any] = field(default_factory=dict)


# ============================================================
# GraphStore Sınıfı
# ============================================================

class GraphStore:
    """
    Simüle edilmiş GraphRAG hafıza deposu.
    
    In-memory dict tabanlı bir kavram grafı sağlar. Düğümler kavramları,
    kenarlar ise kavramlar arası ilişkileri temsil eder.
    
    Bu sınıf, TwinGraph Studio'nun "bilgi haritası"dır. Agent'lar bu
    haritayı kullanarak:
    - Bir kavramın ilişkili olduğu diğer kavramları keşfeder
    - Araştırma kapsamını genişletir
    - İçerik yazarken zengin bağlam oluşturur
    
    Başlatıldığında 50+ düğüm ve kenar ile önceden doldurulur,
    böylece agent'lar hemen anlamlı sorgular yapabilir.
    
    Kullanım:
        store = GraphStore()
        
        # Yeni düğüm ekle
        node_id = store.add_node("Yeni Kavram", "concept", {"açıklama": "..."})
        
        # Kenar ekle
        edge_id = store.add_edge(node_id, "mevcut_id", "related_to")
        
        # Kavram sorgula (2-hop komşuluk)
        sonuc = store.query("MCP")
        
        # Alt graf çıkar
        subgraph = store.get_subgraph("AI Agent")
    """

    def __init__(self, pre_populate: bool = True):
        """
        GraphStore'u başlat.
        
        Parametreler:
            pre_populate: True ise önceden tanımlı AI kavramları ile doldur.
                          Test ve demo için False yapılabilir.
        """
        self.nodes: dict[str, NodeData] = {}
        self.edges: list[Edge] = []
        self._label_index: dict[str, str] = {}  # label.lower() → node_id (hızlı arama)
        
        if pre_populate:
            self._populate_ai_knowledge_graph()
            logger.info(
                f"GraphStore başlatıldı: {len(self.nodes)} düğüm, "
                f"{len(self.edges)} kenar yüklendi"
            )
        else:
            logger.info("GraphStore boş olarak başlatıldı")

    # --------------------------------------------------------
    # Temel İşlemler
    # --------------------------------------------------------

    def add_node(
        self,
        label: str,
        entity_type: str,
        properties: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Grafa yeni bir düğüm ekle.
        
        Aynı etiketli düğüm zaten varsa, mevcut düğümün ID'sini döndürür
        (duplicate önleme). Bu, ingestion sırasında aynı kavramın
        tekrar tekrar eklenmesini engeller.
        
        Parametreler:
            label: Düğüm etiketi (örn: "MCP", "GPT-4o")
            entity_type: Varlık türü — concept | person | technology | tool
            properties: Ek özellikler sözlüğü
        
        Döndürür:
            str: Düğüm ID'si (yeni veya mevcut)
        
        Örnek:
            node_id = store.add_node(
                "Transformer",
                "technology",
                {"açıklama": "Dikkat mekanizması tabanlı sinir ağı mimarisi"}
            )
        """
        # Aynı etiket varsa mevcut ID'yi döndür
        key = label.lower().strip()
        if key in self._label_index:
            existing_id = self._label_index[key]
            # Properties'i güncelle (varsa)
            if properties:
                self.nodes[existing_id].properties.update(properties)
            logger.debug(f"Mevcut düğüm bulundu: '{label}' → {existing_id}")
            return existing_id

        node_id = str(uuid.uuid4())[:8]
        node = NodeData(
            id=node_id,
            label=label,
            entity_type=entity_type,
            properties=properties or {},
        )
        self.nodes[node_id] = node
        self._label_index[key] = node_id
        logger.debug(f"Düğüm eklendi: '{label}' ({entity_type}) → {node_id}")
        return node_id

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relationship: str,
        properties: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        İki düğüm arasına kenar (ilişki) ekle.
        
        Kaynak ve hedef düğümlerin mevcut olup olmadığını kontrol eder.
        Aynı kaynak-hedef-ilişki üçlüsü zaten varsa tekrar eklemez.
        
        Parametreler:
            source_id: Kaynak düğüm ID'si
            target_id: Hedef düğüm ID'si
            relationship: İlişki türü (uses, enables, improves, vb.)
            properties: Ek kenar özellikleri
        
        Döndürür:
            str: Kenar ID'si (yeni veya mevcut)
        
        Örnek:
            edge_id = store.add_edge(mcp_id, tool_use_id, "enables")
        """
        # Düğüm kontrolü
        if source_id not in self.nodes:
            logger.warning(f"Kaynak düğüm bulunamadı: {source_id}")
            return ""
        if target_id not in self.nodes:
            logger.warning(f"Hedef düğüm bulunamadı: {target_id}")
            return ""

        # Duplicate kontrolü
        for edge in self.edges:
            if (
                edge.source == source_id
                and edge.target == target_id
                and edge.relationship == relationship
            ):
                logger.debug(
                    f"Kenar zaten mevcut: {source_id} → {relationship} → {target_id}"
                )
                return edge.id

        edge_id = str(uuid.uuid4())[:8]
        edge = Edge(
            id=edge_id,
            source=source_id,
            target=target_id,
            relationship=relationship,
            properties=properties or {},
        )
        self.edges.append(edge)
        logger.debug(
            f"Kenar eklendi: {self.nodes[source_id].label} "
            f"→ {relationship} → {self.nodes[target_id].label}"
        )
        return edge_id

    # --------------------------------------------------------
    # Sorgulama İşlemleri
    # --------------------------------------------------------

    def query(self, concept: str) -> dict[str, Any]:
        """
        Bir kavram hakkında graf sorgusu yap.
        
        Verilen kavramı grafa arar, bulursa 2-hop mesafedeki tüm
        ilişkili düğümleri ve kenarları döndürür.
        
        Bu, TwinGraph'ın en temel sorgu yöntemidir:
        - Research Agent, araştırma konusunun bağlamını genişletmek için kullanır
        - Writing Agent, makale yazarken ilişkili kavramları bağlam olarak alır
        
        Parametreler:
            concept: Aranacak kavram (büyük/küçük harf duyarsız)
        
        Döndürür:
            dict: Sorgu sonucu:
                - found (bool): Kavram bulundu mu?
                - node (dict | None): Bulunan düğüm bilgisi
                - related_nodes (list[dict]): İlişkili düğümler
                - edges (list[dict]): Bu kavramı içeren kenarlar
                - hop_depth (int): Arama derinliği
        
        Örnek:
            sonuc = store.query("MCP")
            if sonuc["found"]:
                for iliskili in sonuc["related_nodes"]:
                    print(f"  → {iliskili['label']} ({iliskili['relationship']})")
        """
        logger.info(f"Graf sorgusu: '{concept}'")

        # Kavramı bul
        node_id = self._find_node_by_label(concept)

        if not node_id:
            logger.info(f"Kavram bulunamadı: '{concept}'")
            return {
                "found": False,
                "node": None,
                "related_nodes": [],
                "edges": [],
                "hop_depth": 0,
            }

        center_node = self.nodes[node_id]
        related_nodes = []
        related_edges = []
        visited = {node_id}

        # 2-hop komşuluk keşfi
        current_frontier = {node_id}
        for hop in range(2):
            next_frontier = set()
            for current_id in current_frontier:
                for edge in self.edges:
                    neighbor_id = None
                    direction = None

                    if edge.source == current_id and edge.target not in visited:
                        neighbor_id = edge.target
                        direction = "outgoing"
                    elif edge.target == current_id and edge.source not in visited:
                        neighbor_id = edge.source
                        direction = "incoming"

                    if neighbor_id and neighbor_id in self.nodes:
                        neighbor = self.nodes[neighbor_id]
                        visited.add(neighbor_id)
                        next_frontier.add(neighbor_id)

                        related_nodes.append({
                            "id": neighbor.id,
                            "label": neighbor.label,
                            "entity_type": neighbor.entity_type,
                            "relationship": edge.relationship,
                            "direction": direction,
                            "hop": hop + 1,
                        })

                        related_edges.append({
                            "id": edge.id,
                            "source": self.nodes[edge.source].label,
                            "target": self.nodes[edge.target].label,
                            "relationship": edge.relationship,
                        })

            current_frontier = next_frontier

        logger.info(
            f"Sorgu sonucu: '{concept}' — "
            f"{len(related_nodes)} ilişkili düğüm, {len(related_edges)} kenar"
        )

        return {
            "found": True,
            "node": {
                "id": center_node.id,
                "label": center_node.label,
                "entity_type": center_node.entity_type,
                "properties": center_node.properties,
            },
            "related_nodes": related_nodes,
            "edges": related_edges,
            "hop_depth": 2,
        }

    def get_subgraph(self, concept: str) -> dict[str, Any]:
        """
        Bir kavram etrafındaki alt grafı döndür.
        
        query() metodundan farklı olarak, bu metot düğüm ve kenar
        listelerini ayrı ayrı döndürür — görselleştirme ve analiz
        için daha uygun bir formattır.
        
        Parametreler:
            concept: Merkez kavram
        
        Döndürür:
            dict: Alt graf:
                - center (str): Merkez kavram etiketi
                - nodes (list[dict]): Tüm düğümler (merkez + komşular)
                - edges (list[dict]): Tüm kenarlar
                - stats (dict): İstatistikler
        
        Örnek:
            subgraph = store.get_subgraph("RAG")
            print(f"Merkez: {subgraph['center']}")
            print(f"Düğüm sayısı: {subgraph['stats']['node_count']}")
        """
        logger.info(f"Alt graf çıkarılıyor: '{concept}'")

        query_result = self.query(concept)

        if not query_result["found"]:
            return {
                "center": concept,
                "nodes": [],
                "edges": [],
                "stats": {"node_count": 0, "edge_count": 0},
            }

        # Merkez düğüm + ilişkili düğümler
        all_nodes = [query_result["node"]]
        for rn in query_result["related_nodes"]:
            all_nodes.append({
                "id": rn["id"],
                "label": rn["label"],
                "entity_type": rn["entity_type"],
            })

        return {
            "center": concept,
            "nodes": all_nodes,
            "edges": query_result["edges"],
            "stats": {
                "node_count": len(all_nodes),
                "edge_count": len(query_result["edges"]),
            },
        }

    def get_related_concepts(
        self, concept: str, max_depth: int = 2
    ) -> list[dict[str, Any]]:
        """
        Bir kavramla ilişkili kavramların listesini döndür.
        
        Basit ve kullanışlı bir arayüz — sadece ilişkili kavram
        etiketlerini ve ilişki türlerini döndürür.
        
        Parametreler:
            concept: Aranacak kavram
            max_depth: Maksimum hop derinliği (varsayılan: 2)
        
        Döndürür:
            list[dict]: İlişkili kavramlar listesi. Her eleman:
                - label (str): Kavram etiketi
                - relationship (str): İlişki türü
                - hop (int): Merkeze uzaklık (1 veya 2)
        
        Örnek:
            iliskiler = store.get_related_concepts("LLM")
            for k in iliskiler:
                print(f"  {k['label']} ({k['relationship']}, hop={k['hop']})")
        """
        node_id = self._find_node_by_label(concept)
        if not node_id:
            return []

        results: list[dict[str, Any]] = []
        visited = {node_id}
        current_frontier = {node_id}

        for hop in range(min(max_depth, 3)):  # Maksimum 3 hop
            next_frontier = set()
            for current_id in current_frontier:
                for edge in self.edges:
                    neighbor_id = None
                    rel = edge.relationship

                    if edge.source == current_id and edge.target not in visited:
                        neighbor_id = edge.target
                    elif edge.target == current_id and edge.source not in visited:
                        neighbor_id = edge.source

                    if neighbor_id and neighbor_id in self.nodes:
                        visited.add(neighbor_id)
                        next_frontier.add(neighbor_id)
                        results.append({
                            "label": self.nodes[neighbor_id].label,
                            "relationship": rel,
                            "hop": hop + 1,
                        })

            current_frontier = next_frontier

        return results

    # --------------------------------------------------------
    # Yardımcı Metodlar
    # --------------------------------------------------------

    def _find_node_by_label(self, label: str) -> Optional[str]:
        """
        Etiketle düğüm bul (büyük/küçük harf duyarsız, kısmi eşleşme destekli).
        
        Önce tam eşleşme arar, bulamazsa kısmi eşleşme dener.
        Bu sayede "mcp" yazarak "MCP" düğümünü bulabilirsiniz.
        
        Parametreler:
            label: Aranacak etiket
        
        Döndürür:
            Optional[str]: Bulunan düğüm ID'si veya None
        """
        key = label.lower().strip()

        # Tam eşleşme
        if key in self._label_index:
            return self._label_index[key]

        # Kısmi eşleşme (label içinde arama)
        for stored_label, node_id in self._label_index.items():
            if key in stored_label or stored_label in key:
                return node_id

        return None

    def get_node_by_label(self, label: str) -> Optional[NodeData]:
        """
        Etiketle düğüm nesnesini döndür.
        
        Parametreler:
            label: Düğüm etiketi
        
        Döndürür:
            Optional[NodeData]: Bulunan düğüm veya None
        """
        node_id = self._find_node_by_label(label)
        if node_id:
            return self.nodes[node_id]
        return None

    def get_stats(self) -> dict[str, int]:
        """
        Graf istatistiklerini döndür.
        
        Döndürür:
            dict: Düğüm sayısı, kenar sayısı, varlık türü dağılımı
        """
        type_counts: dict[str, int] = {}
        for node in self.nodes.values():
            type_counts[node.entity_type] = type_counts.get(node.entity_type, 0) + 1

        relationship_counts: dict[str, int] = {}
        for edge in self.edges:
            relationship_counts[edge.relationship] = (
                relationship_counts.get(edge.relationship, 0) + 1
            )

        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "entity_types": type_counts,
            "relationship_types": relationship_counts,
        }

    # --------------------------------------------------------
    # Önceden Doldurma (Pre-population)
    # --------------------------------------------------------

    def _populate_ai_knowledge_graph(self) -> None:
        """
        AI ve agent konularında zengin bir bilgi grafı oluştur.
        
        50+ düğüm ve kenar ile grafı doldurur. Bu veriler:
        - Research agent'ın araştırma kapsamını genişletmesini sağlar
        - Writing agent'ın kavramlar arası bağlantılar kurmasını destekler
        - Demo ve test sırasında anlamlı sorgular yapılmasına imkan tanır
        
        Kapsanan konular:
        - AI Agent mimarisi ve bileşenleri
        - MCP (Model Context Protocol) ekosistemi
        - LLM modelleri ve yetenekleri
        - RAG ve hafıza sistemleri
        - Prompt engineering teknikleri
        - Evaluation ve metrikler
        - İçerik üretim pipeline'ı
        - Multi-agent sistemleri
        - Python ekosistemi ve araçları
        """
        # === DÜĞÜMLER ===

        # --- Temel AI Kavramları ---
        ai_agent = self.add_node("AI Agent", "concept", {
            "açıklama": "Otonom görevleri yerine getiren yapay zeka sistemi",
            "önem": "yüksek",
        })
        llm = self.add_node("LLM", "technology", {
            "açıklama": "Büyük Dil Modeli — agent'ların düşünme motoru",
            "örnekler": "GPT-4o, Claude, Gemini",
        })
        mcp = self.add_node("MCP", "technology", {
            "açıklama": "Model Context Protocol — LLM-tool iletişim standardı",
            "kaynak": "Anthropic",
        })
        tool_calling = self.add_node("Tool Calling", "concept", {
            "açıklama": "LLM'in harici araçları çağırma yeteneği",
        })
        tool_use = self.add_node("Tool Use", "concept", {
            "açıklama": "Agent'ın araçları kullanarak görev tamamlaması",
        })
        client_server = self.add_node("Client-Server Communication", "concept", {
            "açıklama": "İstemci-sunucu iletişim modeli",
        })

        # --- LLM Modelleri ---
        gpt4o = self.add_node("GPT-4o", "technology", {
            "üretici": "OpenAI", "tür": "multimodal",
            "açıklama": "Yüksek kaliteli içerik üretimi için ana model",
        })
        gpt4o_mini = self.add_node("GPT-4o-mini", "technology", {
            "üretici": "OpenAI", "tür": "hafif",
            "açıklama": "Hızlı ve düşük maliyetli görevler için",
        })
        claude = self.add_node("Claude", "technology", {
            "üretici": "Anthropic", "tür": "güvenlik odaklı",
            "açıklama": "Uzun bağlam ve güvenli içerik üretimi",
        })
        gemini = self.add_node("Gemini", "technology", {
            "üretici": "Google", "tür": "multimodal",
            "açıklama": "Google'ın çok modlu yapay zeka modeli",
        })

        # --- Reflection & Kalite ---
        reflection = self.add_node("Reflection", "concept", {
            "açıklama": "Agent'ın kendi çıktısını eleştirip iyileştirmesi",
            "pattern": "critique → revise → improve döngüsü",
        })
        content_quality = self.add_node("Content Quality", "concept", {
            "açıklama": "Üretilen içeriğin kalitesi — tutarlılık, derinlik, doğruluk",
        })
        self_critique = self.add_node("Self-Critique", "concept", {
            "açıklama": "Agent'ın kendi çıktısını değerlendirmesi",
        })
        iterative_refinement = self.add_node("Iterative Refinement", "concept", {
            "açıklama": "Tekrarlı iyileştirme döngüsü",
        })

        # --- Multi-Agent ---
        multi_agent = self.add_node("Multi-Agent", "concept", {
            "açıklama": "Birden fazla agent'ın koordineli çalışması",
            "pattern": "orkestrasyon, iş bölümü, mesajlaşma",
        })
        orchestration = self.add_node("Orchestration", "concept", {
            "açıklama": "Agent'lar arası görev dağıtımı ve koordinasyon",
        })
        shared_memory = self.add_node("Shared Memory", "concept", {
            "açıklama": "Agent'lar arası paylaşılan hafıza alanı",
        })
        message_passing = self.add_node("Message Passing", "concept", {
            "açıklama": "Agent'lar arası mesajlaşma mekanizması",
        })

        # --- RAG & Hafıza ---
        rag = self.add_node("RAG", "concept", {
            "açıklama": "Retrieval-Augmented Generation — bilgi erişimli üretim",
            "tam_ad": "Retrieval-Augmented Generation",
        })
        retrieval = self.add_node("Retrieval", "concept", {
            "açıklama": "Bilgi erişimi — ilgili belgeleri bulma",
        })
        generation = self.add_node("Generation", "concept", {
            "açıklama": "LLM ile metin üretimi",
        })
        graph_rag = self.add_node("GraphRAG", "technology", {
            "açıklama": "Graf tabanlı RAG — kavram ilişkileriyle zenginleştirilmiş",
        })
        vector_db = self.add_node("Vector DB", "technology", {
            "açıklama": "Vektör veritabanı — embedding tabanlı benzerlik araması",
            "örnekler": "Pinecone, Chroma, Weaviate",
        })
        embedding = self.add_node("Embedding", "concept", {
            "açıklama": "Metni sayısal vektöre dönüştürme",
        })

        # --- Prompt Engineering ---
        prompt_eng = self.add_node("Prompt Engineering", "concept", {
            "açıklama": "LLM'e etkili komut yazma sanatı",
        })
        few_shot = self.add_node("Few-Shot", "concept", {
            "açıklama": "Birkaç örnekle LLM'i yönlendirme tekniği",
        })
        chain_of_thought = self.add_node("Chain of Thought", "concept", {
            "açıklama": "Adım adım düşünme — karmaşık akıl yürütme",
            "kısaltma": "CoT",
        })
        system_prompt = self.add_node("System Prompt", "concept", {
            "açıklama": "LLM'in davranışını belirleyen ana komut",
        })
        zero_shot = self.add_node("Zero-Shot", "concept", {
            "açıklama": "Örnek vermeden doğrudan görev tanımı",
        })

        # --- Evaluation ---
        evaluation = self.add_node("Evaluation", "concept", {
            "açıklama": "Agent ve içerik kalitesini ölçme sistemi",
        })
        accuracy = self.add_node("Accuracy", "concept", {
            "açıklama": "Doğruluk — üretilen içeriğin doğruluğu",
        })
        cost_metric = self.add_node("Cost", "concept", {
            "açıklama": "Maliyet — token kullanımı ve API giderleri",
        })
        latency = self.add_node("Latency", "concept", {
            "açıklama": "Gecikme — işlem süresi",
        })
        coherence = self.add_node("Coherence", "concept", {
            "açıklama": "Tutarlılık — metnin mantıksal bütünlüğü",
        })

        # --- İçerik Üretimi ---
        content_creation = self.add_node("Content Creation", "concept", {
            "açıklama": "Yapılandırılmış içerik üretim süreci",
        })
        research = self.add_node("Research", "concept", {
            "açıklama": "Araştırma — kaynak toplama ve özetleme",
        })
        writing = self.add_node("Writing", "concept", {
            "açıklama": "Yazma — yapılandırılmış metin üretimi",
        })
        editing = self.add_node("Editing", "concept", {
            "açıklama": "Düzenleme — kalite kontrol ve iyileştirme",
        })
        medium_article = self.add_node("Medium Article", "concept", {
            "açıklama": "Yapılandırılmış uzun form içerik formatı",
        })
        linkedin_post = self.add_node("LinkedIn Post", "concept", {
            "açıklama": "Profesyonel sosyal medya içerik formatı",
        })

        # --- Python & Teknoloji ---
        python = self.add_node("Python", "technology", {
            "açıklama": "AI ve otomasyon için birincil programlama dili",
        })
        api = self.add_node("API", "technology", {
            "açıklama": "Application Programming Interface — yazılım arayüzü",
        })
        token = self.add_node("Token", "concept", {
            "açıklama": "LLM'de metin birimi — maliyet ve limit ölçüsü",
        })
        json_schema = self.add_node("JSON Schema", "technology", {
            "açıklama": "Yapılandırılmış veri doğrulama standardı",
        })
        openai_api = self.add_node("OpenAI API", "technology", {
            "açıklama": "OpenAI'ın LLM erişim arayüzü",
        })

        # --- Araçlar & Altyapı ---
        deep_research = self.add_node("Deep Research", "tool", {
            "açıklama": "Kapsamlı kaynak araştırma aracı",
        })
        cost_guard = self.add_node("Cost Guard", "tool", {
            "açıklama": "Maliyet kontrolü ve bütçe koruma aracı",
        })
        citation_verify = self.add_node("Citation Verify", "tool", {
            "açıklama": "Kaynakça doğrulama aracı",
        })
        model_routing = self.add_node("Model Routing", "concept", {
            "açıklama": "Görev karmaşıklığına göre model seçimi",
        })

        # --- Ek Kavramlar ---
        fine_tuning = self.add_node("Fine-Tuning", "concept", {
            "açıklama": "Modeli özel veri ile ince ayar yapma",
        })
        hallucination = self.add_node("Hallucination", "concept", {
            "açıklama": "LLM'in gerçek olmayan bilgi üretmesi",
        })
        context_window = self.add_node("Context Window", "concept", {
            "açıklama": "LLM'in aynı anda işleyebildiği metin uzunluğu",
        })
        agent_loop = self.add_node("Agent Loop", "concept", {
            "açıklama": "Think → Act → Observe döngüsü",
            "pattern": "ReAct pattern",
        })
        structured_output = self.add_node("Structured Output", "concept", {
            "açıklama": "LLM'den JSON/şema uyumlu çıktı alma",
        })
        middleware = self.add_node("Middleware", "concept", {
            "açıklama": "İstek-yanıt arasındaki ara katman (logging, retry, vb.)",
        })
        retry_mechanism = self.add_node("Retry Mechanism", "concept", {
            "açıklama": "Hatalı işlemleri otomatik tekrar deneme",
        })

        # === KENARLAR (İlişkiler) ===

        # AI Agent ilişkileri
        self.add_edge(ai_agent, llm, "uses")
        self.add_edge(ai_agent, mcp, "uses")
        self.add_edge(ai_agent, tool_calling, "uses")
        self.add_edge(ai_agent, agent_loop, "uses")
        self.add_edge(ai_agent, python, "implemented_in")

        # MCP ilişkileri
        self.add_edge(mcp, tool_use, "enables")
        self.add_edge(mcp, client_server, "uses")
        self.add_edge(mcp, json_schema, "uses")
        self.add_edge(mcp, middleware, "uses")
        self.add_edge(tool_calling, mcp, "standardized_by")

        # LLM ilişkileri
        self.add_edge(llm, gpt4o, "includes")
        self.add_edge(llm, gpt4o_mini, "includes")
        self.add_edge(llm, claude, "includes")
        self.add_edge(llm, gemini, "includes")
        self.add_edge(llm, token, "uses")
        self.add_edge(llm, context_window, "limited_by")
        self.add_edge(llm, hallucination, "prone_to")
        self.add_edge(llm, generation, "performs")
        self.add_edge(llm, openai_api, "accessed_via")

        # Reflection ilişkileri
        self.add_edge(reflection, content_quality, "improves")
        self.add_edge(reflection, self_critique, "uses")
        self.add_edge(reflection, iterative_refinement, "uses")
        self.add_edge(reflection, writing, "enhances")

        # Multi-Agent ilişkileri
        self.add_edge(multi_agent, orchestration, "uses")
        self.add_edge(multi_agent, shared_memory, "uses")
        self.add_edge(multi_agent, message_passing, "uses")
        self.add_edge(orchestration, ai_agent, "coordinates")

        # RAG ilişkileri
        self.add_edge(rag, retrieval, "combines")
        self.add_edge(rag, generation, "combines")
        self.add_edge(rag, embedding, "uses")
        self.add_edge(rag, vector_db, "uses")
        self.add_edge(graph_rag, rag, "extends")
        self.add_edge(graph_rag, shared_memory, "part_of")
        self.add_edge(vector_db, embedding, "stores")

        # Prompt Engineering ilişkileri
        self.add_edge(prompt_eng, few_shot, "includes")
        self.add_edge(prompt_eng, chain_of_thought, "includes")
        self.add_edge(prompt_eng, system_prompt, "includes")
        self.add_edge(prompt_eng, zero_shot, "includes")
        self.add_edge(prompt_eng, llm, "optimizes")
        self.add_edge(chain_of_thought, accuracy, "improves")

        # Evaluation ilişkileri
        self.add_edge(evaluation, accuracy, "measures")
        self.add_edge(evaluation, cost_metric, "measures")
        self.add_edge(evaluation, latency, "measures")
        self.add_edge(evaluation, coherence, "measures")
        self.add_edge(evaluation, content_quality, "measures")

        # İçerik Üretim ilişkileri
        self.add_edge(content_creation, research, "requires")
        self.add_edge(content_creation, writing, "requires")
        self.add_edge(content_creation, editing, "requires")
        self.add_edge(content_creation, medium_article, "produces")
        self.add_edge(content_creation, linkedin_post, "produces")
        self.add_edge(writing, llm, "powered_by")
        self.add_edge(editing, reflection, "uses")

        # Araç ilişkileri
        self.add_edge(deep_research, research, "performs")
        self.add_edge(deep_research, api, "uses")
        self.add_edge(cost_guard, cost_metric, "monitors")
        self.add_edge(cost_guard, token, "tracks")
        self.add_edge(cost_guard, model_routing, "uses")
        self.add_edge(citation_verify, research, "validates")
        self.add_edge(model_routing, gpt4o, "routes_to")
        self.add_edge(model_routing, gpt4o_mini, "routes_to")

        # Teknoloji ilişkileri
        self.add_edge(python, api, "uses")
        self.add_edge(openai_api, api, "is_a")
        self.add_edge(openai_api, gpt4o, "provides")
        self.add_edge(openai_api, gpt4o_mini, "provides")
        self.add_edge(structured_output, json_schema, "uses")
        self.add_edge(llm, structured_output, "supports")

        # Ek ilişkiler
        self.add_edge(fine_tuning, llm, "customizes")
        self.add_edge(middleware, retry_mechanism, "includes")
        self.add_edge(agent_loop, tool_calling, "includes")
        self.add_edge(agent_loop, reflection, "may_include")
        self.add_edge(hallucination, rag, "mitigated_by")
        self.add_edge(hallucination, citation_verify, "detected_by")
        self.add_edge(context_window, token, "measured_in")


# ============================================================
# Tool Şeması
# ============================================================

def create_graph_query_tool_schema():
    """
    graph_query tool'u için MCP şeması oluştur.
    
    Bu şema, MCP sunucusuna kaydedilir ve LLM'in kavram
    grafını sorgulamasını sağlar.
    
    Döndürür:
        ToolSchema: MCP uyumlu tool şeması
    """
    return create_tool_schema(
        name="memory.graph_query",
        description=(
            "Kavram grafını (GraphRAG) sorgular. Bir kavram verildiğinde, "
            "ilişkili kavramları, bağlantıları ve 2-hop komşuluğundaki "
            "tüm bilgiyi döndürür. Araştırma kapsamını genişletmek ve "
            "içerik yazarken bağlam oluşturmak için kullanılır."
        ),
        parameters={
            "concept": {
                "type": "string",
                "description": "Sorgulanacak kavram (örn: 'MCP', 'AI Agent', 'RAG')",
            },
            "include_subgraph": {
                "type": "boolean",
                "description": "Alt graf bilgisini de dahil et (varsayılan: false)",
            },
        },
        required=["concept"],
    )


# ============================================================
# Test & Demo
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("  TwinGraph Studio — Graph Store (Kavram Grafı) Demo")
    print("=" * 70)

    # Graf oluştur
    store = GraphStore()

    # İstatistikler
    stats = store.get_stats()
    print(f"\n📊 Graf İstatistikleri:")
    print(f"   Toplam düğüm: {stats['total_nodes']}")
    print(f"   Toplam kenar: {stats['total_edges']}")
    print(f"   Varlık türleri: {stats['entity_types']}")
    print(f"   İlişki türleri: {stats['relationship_types']}")

    # --- Sorgu 1: MCP ---
    print(f"\n{'─' * 70}")
    print("🔍 Sorgu: 'MCP'")
    print("─" * 70)
    result = store.query("MCP")
    if result["found"]:
        print(f"   Düğüm: {result['node']['label']} ({result['node']['entity_type']})")
        print(f"   Özellikler: {result['node']['properties']}")
        print(f"   İlişkili düğüm sayısı: {len(result['related_nodes'])}")
        for rn in result["related_nodes"][:8]:
            yön = "→" if rn["direction"] == "outgoing" else "←"
            print(f"   {yön} {rn['label']} ({rn['relationship']}, hop={rn['hop']})")

    # --- Sorgu 2: AI Agent ---
    print(f"\n{'─' * 70}")
    print("🔍 Sorgu: 'AI Agent'")
    print("─" * 70)
    result = store.query("AI Agent")
    if result["found"]:
        print(f"   İlişkili düğüm sayısı: {len(result['related_nodes'])}")
        for rn in result["related_nodes"][:10]:
            yön = "→" if rn["direction"] == "outgoing" else "←"
            print(f"   {yön} {rn['label']} ({rn['relationship']}, hop={rn['hop']})")

    # --- Sorgu 3: RAG ---
    print(f"\n{'─' * 70}")
    print("🔍 Sorgu: 'RAG'")
    print("─" * 70)
    result = store.query("RAG")
    if result["found"]:
        for rn in result["related_nodes"][:8]:
            yön = "→" if rn["direction"] == "outgoing" else "←"
            print(f"   {yön} {rn['label']} ({rn['relationship']}, hop={rn['hop']})")

    # --- Alt Graf ---
    print(f"\n{'─' * 70}")
    print("🌐 Alt Graf: 'Reflection'")
    print("─" * 70)
    subgraph = store.get_subgraph("Reflection")
    print(f"   Merkez: {subgraph['center']}")
    print(f"   Düğüm sayısı: {subgraph['stats']['node_count']}")
    print(f"   Kenar sayısı: {subgraph['stats']['edge_count']}")
    for node in subgraph["nodes"]:
        print(f"   • {node['label']} ({node['entity_type']})")

    # --- İlişkili Kavramlar ---
    print(f"\n{'─' * 70}")
    print("🔗 İlişkili Kavramlar: 'Evaluation'")
    print("─" * 70)
    related = store.get_related_concepts("Evaluation", max_depth=2)
    for r in related:
        print(f"   {'  ' * (r['hop'] - 1)}→ {r['label']} ({r['relationship']}, hop={r['hop']})")

    # --- Yeni Düğüm ve Kenar Ekleme ---
    print(f"\n{'─' * 70}")
    print("➕ Yeni Düğüm Ekleme")
    print("─" * 70)
    new_id = store.add_node("LangChain", "technology", {
        "açıklama": "LLM uygulama geliştirme framework'ü",
    })
    agent_node = store.get_node_by_label("AI Agent")
    if agent_node:
        store.add_edge(new_id, agent_node.id, "supports")
        print(f"   LangChain eklendi ve AI Agent'a bağlandı")

    result = store.query("LangChain")
    if result["found"]:
        print(f"   LangChain ilişkileri: {len(result['related_nodes'])} düğüm")
        for rn in result["related_nodes"][:5]:
            print(f"   → {rn['label']} ({rn['relationship']})")

    # --- Tool Şeması ---
    print(f"\n{'─' * 70}")
    print("🛠️ Tool Şeması")
    print("─" * 70)
    schema = create_graph_query_tool_schema()
    import json
    print(f"   {json.dumps(schema.to_mcp_format(), indent=2, ensure_ascii=False)}")

    print(f"\n{'=' * 70}")
    print("  ✅ Graph Store demo tamamlandı!")
    print("=" * 70)

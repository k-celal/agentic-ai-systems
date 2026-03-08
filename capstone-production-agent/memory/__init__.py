"""
Memory - TwinGraph Studio Hafıza Sistemi
==========================================
TwinGraph Studio'nun "beyni" olan hafıza sistemi.

Neden Hafıza Gerekli?
---------------------
Bir agent sistemi, birden fazla adımda çalışır: araştırır, yazar, eleştirir, iyileştirir.
Bu adımlar arasında bilgi paylaşmak ve önceki bilgiyi hatırlamak için bir hafıza katmanı şarttır.

Hafızasız bir agent her seferinde sıfırdan başlar — bu hem verimsiz hem de tutarsız sonuçlar üretir.
TwinGraph'ın hafıza sistemi, agent'ların önceki araştırmaları, kavram ilişkilerini ve üretilen
içerikleri hatırlamasını sağlar.

Üç Alt Sistem:
--------------
1. **Graph Store (Kavram Grafı - GraphRAG)**:
   Kavramlar arası ilişkileri saklar. Örneğin:
   - "AI Agent" → uses → "LLM"
   - "MCP" → enables → "Tool Use"
   - "Reflection" → improves → "Content Quality"
   
   Bu yapı sayesinde bir kavram sorgulandığında, ilişkili kavramlar
   2 hop mesafede keşfedilebilir. Research agent'ı bunu kullanarak
   araştırma kapsamını genişletir, Writing agent'ı ise bağlam oluşturur.

2. **Vector Store (Vektör Deposu)**:
   Metin benzerliği araması yapar. Daha önce üretilen veya yüklenen
   içerikler vektör olarak saklanır ve yeni sorgulara en benzer
   içerikler bulunur. Bu, RAG (Retrieval-Augmented Generation) 
   yaklaşımının temelidir.
   
   Simüle edilmiş keyword-tabanlı benzerlik kullanır (Jaccard similarity).
   Gerçek üretimde OpenAI Embeddings veya sentence-transformers kullanılır.

3. **Ingestion (İçerik Yükleme ve İşleme)**:
   Ham metni alır, varlıkları (entity) çıkarır, graf kenarları oluşturur
   ve vektör dökümanları üretir. Yeni bir araştırma sonucu veya makale
   üretildiğinde, bu pipeline otomatik olarak hafızayı günceller.

Kullanım:
    from memory.graph_store import GraphStore
    from memory.vector_store import VectorStore
    from memory.ingestion import ContentIngester

    # Kavram grafı sorgusu
    graph = GraphStore()
    sonuc = graph.query("MCP")
    
    # Vektör benzerliği araması
    vector = VectorStore()
    benzer = vector.search("agent hafıza sistemi", top_k=3)
    
    # Yeni içerik yükleme
    ingester = ContentIngester(graph, vector)
    rapor = ingester.ingest("MCP, agent sistemlerinde tool çağırma...", "makale_01")
"""

from .graph_store import GraphStore
from .vector_store import VectorStore
from .ingestion import ContentIngester

__all__ = ["GraphStore", "VectorStore", "ContentIngester"]

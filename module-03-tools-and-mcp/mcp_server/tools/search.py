"""
Search Tool - Arama Aracı (v1 ve v2)
=======================================
Metin içinde arama yapan tool. İki versiyonu gösterir.

Tool Versioning Örneği:
- search@v1: Basit arama (sadece query)
- search@v2: Gelişmiş arama (filtre, sıralama, limit)

Kullanım:
    # v1: Basit
    result = search_v1(query="Python")
    
    # v2: Gelişmiş
    result = search_v2(query="Python", max_results=5, category="tutorial")
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from shared.schemas.tool import create_tool_schema

# Simüle edilmiş arama veritabanı
SEARCH_DATABASE = [
    {"id": 1, "title": "Python Giriş Dersi", "category": "tutorial", "content": "Python programlama diline giriş..."},
    {"id": 2, "title": "Python Veri Yapıları", "category": "tutorial", "content": "Liste, tuple, dictionary..."},
    {"id": 3, "title": "AI Agent Nedir?", "category": "article", "content": "Yapay zeka ajanları..."},
    {"id": 4, "title": "MCP Protokolü", "category": "documentation", "content": "Model Context Protocol..."},
    {"id": 5, "title": "FastAPI ile REST API", "category": "tutorial", "content": "FastAPI framework'ü..."},
    {"id": 6, "title": "LLM Fine-tuning Rehberi", "category": "article", "content": "Büyük dil modellerini..."},
    {"id": 7, "title": "Docker Başlangıç", "category": "tutorial", "content": "Container teknolojisi..."},
    {"id": 8, "title": "Python Testing Best Practices", "category": "article", "content": "Test yazma pratikleri..."},
]


# ─── V1: Basit Arama ───

def search_v1(query: str) -> list[dict]:
    """
    Basit metin araması (v1).
    
    Parametreler:
        query: Arama sorgusu
    
    Döndürür:
        list[dict]: Eşleşen sonuçlar
    
    Örnek:
        >>> search_v1("Python")
        [{"id": 1, "title": "Python Giriş Dersi", ...}, ...]
    """
    query_lower = query.lower()
    results = [
        item for item in SEARCH_DATABASE
        if query_lower in item["title"].lower() or query_lower in item["content"].lower()
    ]
    return results


SEARCH_V1_SCHEMA = create_tool_schema(
    name="search",
    description="Veritabanında basit metin araması yapar.",
    parameters={
        "query": {
            "type": "string",
            "description": "Arama sorgusu",
        }
    },
    required=["query"],
    version="1.0",
)


# ─── V2: Gelişmiş Arama ───

def search_v2(
    query: str,
    category: str = None,
    max_results: int = 10,
    sort_by: str = "relevance",
) -> dict:
    """
    Gelişmiş arama (v2): Filtre, sıralama ve limit destekli.
    
    Parametreler:
        query: Arama sorgusu
        category: Kategori filtresi (tutorial, article, documentation)
        max_results: Maksimum sonuç sayısı
        sort_by: Sıralama kriteri (relevance, title)
    
    Döndürür:
        dict: {"results": [...], "total": N, "query": "...", "filters": {...}}
    """
    query_lower = query.lower()
    
    # Arama
    results = [
        item for item in SEARCH_DATABASE
        if query_lower in item["title"].lower() or query_lower in item["content"].lower()
    ]
    
    # Kategori filtresi
    if category:
        results = [r for r in results if r["category"] == category]
    
    # Sıralama
    if sort_by == "title":
        results.sort(key=lambda x: x["title"])
    
    total = len(results)
    
    # Limit
    results = results[:max_results]
    
    return {
        "results": results,
        "total": total,
        "returned": len(results),
        "query": query,
        "filters": {"category": category, "sort_by": sort_by},
    }


SEARCH_V2_SCHEMA = create_tool_schema(
    name="search",
    description=(
        "Veritabanında gelişmiş arama yapar. "
        "Kategori filtresi, sıralama ve sonuç limiti destekler."
    ),
    parameters={
        "query": {
            "type": "string",
            "description": "Arama sorgusu",
        },
        "category": {
            "type": "string",
            "description": "Kategori filtresi: tutorial, article, documentation",
        },
        "max_results": {
            "type": "number",
            "description": "Maksimum sonuç sayısı (varsayılan: 10)",
        },
        "sort_by": {
            "type": "string",
            "description": "Sıralama: relevance veya title",
        },
    },
    required=["query"],
    version="2.0",
)


if __name__ == "__main__":
    print("🔍 Search Tool Test")
    print("=" * 40)
    
    # v1 test
    results = search_v1("Python")
    print(f"v1 'Python': {len(results)} sonuç")
    
    # v2 test
    results = search_v2("Python", category="tutorial", max_results=2)
    print(f"v2 'Python' (tutorial, max 2): {results['returned']}/{results['total']} sonuç")
    
    print("\n✅ Testler tamamlandı!")

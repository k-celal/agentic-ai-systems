"""
LLM - Model İstemcileri ve Yönlendirme
========================================
Bu modül, LLM API çağrılarını yönetir.

Kullanım:
    from shared.llm.client import LLMClient
    
    client = LLMClient()
    response = await client.chat("Merhaba!")
"""

from shared.llm.client import LLMClient

__all__ = ["LLMClient"]

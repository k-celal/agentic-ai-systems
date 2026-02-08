"""
Message Schema - Mesaj Şemaları
================================
Agent sistemi içindeki mesaj formatlarını tanımlar.

Mesaj Tipleri:
- system: Agent'a verilen talimatlar
- user: Kullanıcıdan gelen mesajlar
- assistant: Agent'ın cevapları
- tool: Tool çağrı sonuçları

Kullanım:
    from shared.schemas.message import Message, Role
    
    msg = Message(role=Role.USER, content="Merhaba!")
    print(msg.to_dict())
    # {"role": "user", "content": "Merhaba!"}
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Any


class Role(str, Enum):
    """
    Mesaj gönderen rolü.
    
    Neden önemli?
    - LLM, mesajların kimden geldiğini bilmeli
    - system: Talimatlar (en yüksek öncelik)
    - user: Kullanıcı istekleri
    - assistant: LLM'in cevapları
    - tool: Tool sonuçları
    """
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    """
    Bir mesajı temsil eder.
    
    Örnekler:
        # Sistem mesajı
        system_msg = Message(
            role=Role.SYSTEM,
            content="Sen yardımcı bir asistansın."
        )
        
        # Kullanıcı mesajı
        user_msg = Message(
            role=Role.USER,
            content="Python nedir?"
        )
        
        # Tool sonucu mesajı
        tool_msg = Message(
            role=Role.TOOL,
            content='{"temperature": 15, "condition": "sunny"}',
            tool_call_id="call_123",
            name="get_weather"
        )
    """
    role: Role                              # Kim gönderdi?
    content: str                            # Mesaj içeriği
    name: Optional[str] = None             # Tool adı (sadece tool mesajları için)
    tool_call_id: Optional[str] = None     # Tool çağrı ID'si
    metadata: dict[str, Any] = field(default_factory=dict)  # Ek bilgiler
    
    def to_dict(self) -> dict:
        """
        OpenAI API formatına çevir.
        
        Döndürür:
            dict: API uyumlu mesaj
        """
        msg = {
            "role": self.role.value if isinstance(self.role, Role) else self.role,
            "content": self.content,
        }
        
        if self.name:
            msg["name"] = self.name
        
        if self.tool_call_id:
            msg["tool_call_id"] = self.tool_call_id
        
        return msg
    
    @classmethod
    def system(cls, content: str) -> "Message":
        """
        Kısayol: Sistem mesajı oluştur.
        
        Örnek:
            msg = Message.system("Sen yardımcı bir asistansın.")
        """
        return cls(role=Role.SYSTEM, content=content)
    
    @classmethod
    def user(cls, content: str) -> "Message":
        """
        Kısayol: Kullanıcı mesajı oluştur.
        
        Örnek:
            msg = Message.user("Merhaba!")
        """
        return cls(role=Role.USER, content=content)
    
    @classmethod
    def assistant(cls, content: str) -> "Message":
        """
        Kısayol: Asistan cevabı oluştur.
        
        Örnek:
            msg = Message.assistant("Size nasıl yardımcı olabilirim?")
        """
        return cls(role=Role.ASSISTANT, content=content)
    
    @classmethod
    def tool_result(cls, content: str, tool_call_id: str, name: str) -> "Message":
        """
        Kısayol: Tool sonuç mesajı oluştur.
        
        Örnek:
            msg = Message.tool_result(
                content='{"temp": 15}',
                tool_call_id="call_123",
                name="get_weather"
            )
        """
        return cls(
            role=Role.TOOL,
            content=content,
            tool_call_id=tool_call_id,
            name=name,
        )


def build_messages(
    system_prompt: str,
    user_message: str,
    history: list[Message] = None,
) -> list[dict]:
    """
    Mesaj listesi oluşturan yardımcı fonksiyon.
    
    Parametreler:
        system_prompt: Sistem talimatı
        user_message: Kullanıcı mesajı
        history: Önceki mesajlar (isteğe bağlı)
    
    Döndürür:
        list[dict]: API'ye gönderilmeye hazır mesaj listesi
    
    Örnek:
        messages = build_messages(
            system_prompt="Sen bir hava durumu asistanısın.",
            user_message="İstanbul'da hava nasıl?",
        )
        # [
        #     {"role": "system", "content": "Sen bir hava durumu asistanısın."},
        #     {"role": "user", "content": "İstanbul'da hava nasıl?"}
        # ]
    """
    messages = [Message.system(system_prompt).to_dict()]
    
    if history:
        for msg in history:
            messages.append(msg.to_dict())
    
    messages.append(Message.user(user_message).to_dict())
    
    return messages

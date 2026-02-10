# 📝 Module 1: Alıştırmalar (Exercises)

## Alıştırma 1: Yeni Bir Tool Ekle (⭐ Kolay)

### Görev
`mcp/tools/` klasörüne yeni bir tool ekleyin: `store_note`

Bu tool:
- Bir `title` (başlık) ve `content` (içerik) almalı
- Notu bir sözlükte (dictionary) saklamalı
- Kaydedilen notun özetini döndürmeli

### İpuçları
1. `echo.py` dosyasını örnek alın
2. `create_tool_schema()` ile şema oluşturun
3. Tool'u `mcp/server.py`'deki `create_server()` fonksiyonuna kaydedin
4. `agent/run.py`'deki tools dict'ine ekleyin

### Beklenen Davranış
```python
result = store_note(title="Toplantı Notu", content="Proje son tarihi: 15 Şubat")
# → {"status": "saved", "title": "Toplantı Notu", "summary": "Not kaydedildi (26 karakter)"}
```

---

## Alıştırma 2: Max Loops'u Test Et (⭐ Kolay)

### Görev
Agent'a çok karmaşık ve tamamlanamaz bir görev verin ve `max_loops` korumasının çalıştığını gözlemleyin.

### Adımlar
1. `agent/run.py`'de yeni bir görev ekleyin
2. `max_loops=3` yapın (düşük tutun)
3. Agent'a "Marsta yaşam var mı araştır ve kanıtlarını bul" gibi tool'larla çözemeyeceği bir görev verin
4. Sonucun `status == "max_loops_exceeded"` olduğunu doğrulayın

### Beklenen Çıktı
```
⚠️ Maksimum döngü sayısına ulaşıldı (3)
Sonuç: max_loops_exceeded
```

---

## Alıştırma 3: Basit HITL (Human-in-the-Loop) Ekle (⭐⭐ Orta)

### Görev
Agent her tool çağrısından önce kullanıcıdan onay istesin.

### İpuçları
1. `agent/loop.py`'deki `_execute_tool` fonksiyonunu değiştirin
2. Tool çağrılmadan önce `input()` ile kullanıcıdan onay isteyin
3. "e" (evet) denirse çalıştır, "h" (hayır) denirse atla

### Beklenen Davranış
```
🔧 Tool çağrılacak: get_time(timezone_name="Europe/Istanbul")
   Onaylıyor musunuz? (e/h): e
📥 Tool sonucu: {"time": "14:30:00", ...}
```

### Başlangıç Kodu
```python
async def _execute_tool_with_hitl(self, tool_name, arguments):
    """HITL destekli tool çalıştırma."""
    print(f"\n🔧 Tool çağrılacak: {tool_name}({arguments})")
    confirm = input("   Onaylıyor musunuz? (e/h): ")
    
    if confirm.lower() != "e":
        return "Tool çağrısı kullanıcı tarafından reddedildi."
    
    return await self._execute_tool(tool_name, arguments)
```

---

## Alıştırma 4: Token Kullanımını İzle (⭐⭐ Orta)

### Görev
Her görev sonunda detaylı token kullanım raporu oluşturun.

### Adımlar
1. `shared/telemetry/cost_tracker.py`'deki `CostTracker`'ı kullanın
2. Her LLM çağrısından sonra `add_usage()` çağrıldığını doğrulayın
3. Görev sonunda `get_report()` ile rapor yazdırın
4. Farklı görevlerin maliyet farkını karşılaştırın

### Beklenen Çıktı
```
💰 Maliyet Raporu
═══════════════════════════
Toplam Çağrı:   3
Input Tokens:   450
Output Tokens:  180
Toplam Maliyet: $0.000175
Bütçe Limiti:   $0.500000
Kalan Bütçe:    $0.499825
Kullanım:       0.0%
═══════════════════════════
```

---

## Alıştırma 5: Planner'ı Geliştir (⭐⭐⭐ Zor)

### Görev
`agent/planner.py`'deki `SimplePlanner`'ı geliştirin:
- Adımlar arasında bağımlılık (dependency) bilgisi ekleyin
- Paralel çalışabilecek adımları belirleyin

### İpucu
```python
@dataclass
class PlanStep:
    step_number: int
    description: str
    tool_needed: str = None
    depends_on: list[int] = None  # Bağımlı olduğu adımlar
    can_parallel: bool = False     # Paralel çalışabilir mi?
```

### Örnek
```
Görev: "İstanbul, Ankara ve İzmir'in hava durumunu karşılaştır"

Plan:
  1. İstanbul hava durumu al (bağımlılık: yok, paralel: evet)
  2. Ankara hava durumu al (bağımlılık: yok, paralel: evet)
  3. İzmir hava durumu al (bağımlılık: yok, paralel: evet)
  4. Karşılaştır ve özetle (bağımlılık: [1,2,3], paralel: hayır)
```

---

## ✅ Kontrol Listesi

Tüm alıştırmaları tamamladıktan sonra şunları yapabilmelisiniz:

- [ ] Yeni bir MCP tool oluşturabiliyorum
- [ ] Tool'u agent'a bağlayabiliyorum
- [ ] Max loops korumasının nasıl çalıştığını anlıyorum
- [ ] HITL (Human-in-the-Loop) kavramını uygulayabiliyorum
- [ ] Token maliyetini takip edebiliyorum
- [ ] Basit görev planlaması yapabiliyorum

---

> 💡 **İpucu:** Takıldığınızda `expected_outputs/` klasöründeki örneklere bakın.
> Hâlâ takılıyorsanız, `theory.md`'yi tekrar okuyun.

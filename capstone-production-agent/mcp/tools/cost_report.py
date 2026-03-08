"""
Maliyet Raporlama Aracı - Detaylı Harcama Analizi
=====================================================
Kullanım kayıtlarından detaylı maliyet raporu üreten araçtır.

Bu Araç Ne İşe Yarar?
-----------------------
TwinGraph Studio'da birden fazla ajan çalışır ve her biri LLM API
çağrıları yapar. Bu araç:
1. Toplam maliyeti hesaplar
2. Ajan bazında maliyet kırılımı yapar
3. Model bazında maliyet analizi sunar
4. Kelime başına maliyet hesaplar
5. Optimizasyon önerileri üretir

Kullanım:
    from mcp.tools.cost_report import generate_cost_report
    
    kayitlar = [
        {"agent": "researcher", "model": "gpt-4o-mini", "input_tokens": 1000,
         "output_tokens": 500, "cost": 0.00045},
        {"agent": "writer", "model": "gpt-4o", "input_tokens": 2000,
         "output_tokens": 1500, "cost": 0.02},
    ]
    
    rapor = generate_cost_report(kayitlar)
    print(f"Toplam maliyet: ${rapor['total_cost']:.4f}")
"""

import sys
import os
from typing import Any
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from shared.schemas.tool import create_tool_schema
from shared.telemetry.logger import get_logger

logger = get_logger("mcp.tools.cost_report")


# ═══════════════════════════════════════════════════════════════════
#  MODEL FİYATLANDIRMA REFERANSI (USD / 1M token)
# ═══════════════════════════════════════════════════════════════════

MODEL_PRICING_REF = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60, "tier": "ekonomik"},
    "gpt-4o": {"input": 2.50, "output": 10.00, "tier": "standart"},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00, "tier": "premium"},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50, "tier": "ekonomik"},
}


# ═══════════════════════════════════════════════════════════════════
#  ANA FONKSİYON
# ═══════════════════════════════════════════════════════════════════

def generate_cost_report(usage_records: list) -> dict:
    """
    Kullanım kayıtlarından detaylı maliyet raporu üret.
    
    Her kayıt şu alanları içermelidir:
        - agent (str): Ajan adı (örn: "researcher", "writer")
        - model (str): Kullanılan model (örn: "gpt-4o-mini")
        - input_tokens (int): Giriş token sayısı
        - output_tokens (int): Çıkış token sayısı
        - cost (float): Çağrı maliyeti (USD)
    
    Opsiyonel alanlar:
        - label (str): Çağrı etiketi
        - output_words (int): Üretilen kelime sayısı
    
    Parametreler:
        usage_records: Kullanım kayıtları listesi
    
    Döndürür:
        dict: Detaylı maliyet raporu
            - total_cost (float): Toplam maliyet (USD)
            - total_calls (int): Toplam çağrı sayısı
            - total_input_tokens (int): Toplam giriş token
            - total_output_tokens (int): Toplam çıkış token
            - cost_per_word (float): Kelime başına maliyet
            - per_agent_cost (dict): Ajan bazında maliyet kırılımı
            - per_model_cost (dict): Model bazında maliyet kırılımı
            - optimization_suggestions (list[str]): Optimizasyon önerileri
            - summary (str): İnsan tarafından okunabilir özet
    
    Örnek:
        >>> kayitlar = [
        ...     {"agent": "researcher", "model": "gpt-4o-mini",
        ...      "input_tokens": 1000, "output_tokens": 500, "cost": 0.00045},
        ... ]
        >>> rapor = generate_cost_report(kayitlar)
        >>> print(f"Toplam: ${rapor['total_cost']:.6f}")
    """
    logger.info(f"Maliyet raporu oluşturuluyor ({len(usage_records)} kayıt)")
    
    if not usage_records:
        logger.warning("Boş kullanım kaydı listesi")
        return {
            "total_cost": 0.0,
            "total_calls": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "cost_per_word": 0.0,
            "per_agent_cost": {},
            "per_model_cost": {},
            "optimization_suggestions": ["Henüz kullanım kaydı yok."],
            "summary": "Henüz kullanım kaydı bulunmuyor.",
        }
    
    # ─── Toplam Değerler ───
    toplam_maliyet = 0.0
    toplam_input = 0
    toplam_output = 0
    toplam_kelime = 0
    
    # ─── Ajan Bazında Kırılım ───
    ajan_maliyetleri: dict[str, dict] = {}
    
    # ─── Model Bazında Kırılım ───
    model_maliyetleri: dict[str, dict] = {}
    
    for kayit in usage_records:
        agent = kayit.get("agent", "bilinmeyen")
        model = kayit.get("model", "gpt-4o-mini")
        input_tokens = kayit.get("input_tokens", 0)
        output_tokens = kayit.get("output_tokens", 0)
        cost = kayit.get("cost", 0.0)
        output_words = kayit.get("output_words", 0)
        
        toplam_maliyet += cost
        toplam_input += input_tokens
        toplam_output += output_tokens
        toplam_kelime += output_words
        
        # Ajan kırılımı
        if agent not in ajan_maliyetleri:
            ajan_maliyetleri[agent] = {
                "total_cost": 0.0,
                "total_calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
            }
        am = ajan_maliyetleri[agent]
        am["total_cost"] += cost
        am["total_calls"] += 1
        am["input_tokens"] += input_tokens
        am["output_tokens"] += output_tokens
        
        # Model kırılımı
        if model not in model_maliyetleri:
            model_maliyetleri[model] = {
                "total_cost": 0.0,
                "total_calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "tier": MODEL_PRICING_REF.get(model, {}).get("tier", "bilinmeyen"),
            }
        mm = model_maliyetleri[model]
        mm["total_cost"] += cost
        mm["total_calls"] += 1
        mm["input_tokens"] += input_tokens
        mm["output_tokens"] += output_tokens
    
    # ─── Kelime Başına Maliyet ───
    cost_per_word = toplam_maliyet / max(toplam_kelime, 1) if toplam_kelime > 0 else 0.0
    
    # ─── Yüzde Hesaplamaları ───
    for agent, am in ajan_maliyetleri.items():
        am["cost_percentage"] = round(
            (am["total_cost"] / max(toplam_maliyet, 0.000001)) * 100, 1
        )
        am["total_cost"] = round(am["total_cost"], 6)
        am["avg_cost_per_call"] = round(
            am["total_cost"] / max(am["total_calls"], 1), 6
        )
    
    for model, mm in model_maliyetleri.items():
        mm["cost_percentage"] = round(
            (mm["total_cost"] / max(toplam_maliyet, 0.000001)) * 100, 1
        )
        mm["total_cost"] = round(mm["total_cost"], 6)
        mm["avg_cost_per_call"] = round(
            mm["total_cost"] / max(mm["total_calls"], 1), 6
        )
    
    # ─── Optimizasyon Önerileri ───
    oneriler = _generate_optimization_suggestions(
        toplam_maliyet=toplam_maliyet,
        toplam_cagri=len(usage_records),
        ajan_maliyetleri=ajan_maliyetleri,
        model_maliyetleri=model_maliyetleri,
        toplam_input=toplam_input,
        toplam_output=toplam_output,
    )
    
    # ─── Özet Metin ───
    ozet = _generate_summary_text(
        toplam_maliyet=toplam_maliyet,
        toplam_cagri=len(usage_records),
        toplam_input=toplam_input,
        toplam_output=toplam_output,
        ajan_maliyetleri=ajan_maliyetleri,
        model_maliyetleri=model_maliyetleri,
    )
    
    logger.info(f"Maliyet raporu hazır: ${toplam_maliyet:.6f} toplam")
    
    return {
        "total_cost": round(toplam_maliyet, 6),
        "total_calls": len(usage_records),
        "total_input_tokens": toplam_input,
        "total_output_tokens": toplam_output,
        "total_tokens": toplam_input + toplam_output,
        "cost_per_word": round(cost_per_word, 8),
        "per_agent_cost": ajan_maliyetleri,
        "per_model_cost": model_maliyetleri,
        "optimization_suggestions": oneriler,
        "summary": ozet,
        "generated_at": datetime.now().isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════
#  OPTİMİZASYON ÖNERİLERİ
# ═══════════════════════════════════════════════════════════════════

def _generate_optimization_suggestions(
    toplam_maliyet: float,
    toplam_cagri: int,
    ajan_maliyetleri: dict,
    model_maliyetleri: dict,
    toplam_input: int,
    toplam_output: int,
) -> list[str]:
    """
    Kullanım kalıplarına göre optimizasyon önerileri üret.
    
    Parametreler:
        toplam_maliyet: Toplam harcama
        toplam_cagri: Toplam çağrı sayısı
        ajan_maliyetleri: Ajan bazında maliyet kırılımı
        model_maliyetleri: Model bazında maliyet kırılımı
        toplam_input: Toplam giriş token
        toplam_output: Toplam çıkış token
    
    Döndürür:
        list[str]: Optimizasyon önerileri
    """
    oneriler = []
    
    # Öneri 1: Pahalı model kullanımı
    for model, mm in model_maliyetleri.items():
        if mm["tier"] == "premium" and mm["cost_percentage"] > 50:
            oneriler.append(
                f"'{model}' modeli toplam maliyetin %{mm['cost_percentage']:.0f}'ini "
                f"oluşturuyor. Basit görevler için 'gpt-4o-mini' gibi daha ekonomik "
                f"bir model kullanmayı değerlendirin."
            )
    
    # Öneri 2: Yüksek input/output oranı
    if toplam_input > 0 and toplam_output > 0:
        io_ratio = toplam_input / toplam_output
        if io_ratio > 5:
            oneriler.append(
                f"Giriş/çıkış token oranı çok yüksek ({io_ratio:.1f}x). "
                f"Prompt'ları kısaltmak veya gereksiz bağlam bilgisini çıkarmak "
                f"maliyeti önemli ölçüde düşürebilir."
            )
    
    # Öneri 3: Baskın ajan
    for agent, am in ajan_maliyetleri.items():
        if am["cost_percentage"] > 70 and len(ajan_maliyetleri) > 1:
            oneriler.append(
                f"'{agent}' ajanı toplam maliyetin %{am['cost_percentage']:.0f}'ini "
                f"oluşturuyor. Bu ajanın prompt'larını optimize etmeyi veya "
                f"daha ucuz bir model kullanmayı düşünün."
            )
    
    # Öneri 4: Çok sayıda çağrı
    if toplam_cagri > 20:
        ort_maliyet = toplam_maliyet / toplam_cagri
        oneriler.append(
            f"Toplam {toplam_cagri} API çağrısı yapıldı "
            f"(ort. ${ort_maliyet:.6f}/çağrı). "
            f"Önbellekleme (caching) ile tekrarlanan sorgularda tasarruf sağlayabilirsiniz."
        )
    
    # Öneri 5: Genel maliyet tahmini
    if toplam_maliyet > 0.01:
        gunluk_tahmin = toplam_maliyet * 10  # Kaba günlük tahmin
        oneriler.append(
            f"Mevcut kullanım kalıbıyla günlük tahmini maliyet: "
            f"~${gunluk_tahmin:.4f}. Bütçe limitlerini buna göre ayarlayın."
        )
    
    # Hiç öneri yoksa olumlu geri bildirim
    if not oneriler:
        oneriler.append(
            "Maliyet kullanımı optimize görünüyor. Düşük maliyetli model "
            "seçimi ve makul çağrı sayısı ile verimli çalışıyorsunuz."
        )
    
    return oneriler


# ═══════════════════════════════════════════════════════════════════
#  ÖZET METİN OLUŞTURMA
# ═══════════════════════════════════════════════════════════════════

def _generate_summary_text(
    toplam_maliyet: float,
    toplam_cagri: int,
    toplam_input: int,
    toplam_output: int,
    ajan_maliyetleri: dict,
    model_maliyetleri: dict,
) -> str:
    """
    İnsan tarafından okunabilir özet metin oluştur.
    
    Döndürür:
        str: Formatlanmış özet rapor
    """
    lines = [
        "",
        f"{'═' * 55}",
        f"  TwinGraph Studio - Maliyet Raporu",
        f"{'═' * 55}",
        f"  Toplam Maliyet:     ${toplam_maliyet:.6f}",
        f"  Toplam Çağrı:       {toplam_cagri}",
        f"  Toplam Input Token:  {toplam_input:,}",
        f"  Toplam Output Token: {toplam_output:,}",
        f"  Ort. Maliyet/Çağrı: ${toplam_maliyet / max(toplam_cagri, 1):.6f}",
        f"{'─' * 55}",
        f"  Ajan Bazında Maliyet:",
    ]
    
    for agent, am in sorted(
        ajan_maliyetleri.items(),
        key=lambda x: x[1]["total_cost"],
        reverse=True,
    ):
        lines.append(
            f"    {agent:18s} | ${am['total_cost']:.6f} | "
            f"{am['total_calls']:3d} çağrı | %{am['cost_percentage']:.0f}"
        )
    
    lines.append(f"{'─' * 55}")
    lines.append(f"  Model Bazında Maliyet:")
    
    for model, mm in sorted(
        model_maliyetleri.items(),
        key=lambda x: x[1]["total_cost"],
        reverse=True,
    ):
        lines.append(
            f"    {model:18s} | ${mm['total_cost']:.6f} | "
            f"{mm['total_calls']:3d} çağrı | {mm['tier']}"
        )
    
    lines.append(f"{'═' * 55}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
#  ARAÇ ŞEMASI
# ═══════════════════════════════════════════════════════════════════

COST_REPORT_SCHEMA = create_tool_schema(
    name="generate_cost_report",
    description=(
        "Kullanım kayıtlarından detaylı maliyet raporu üretir. "
        "Toplam maliyet, ajan bazında kırılım, model bazında kırılım, "
        "kelime başına maliyet ve optimizasyon önerileri içerir."
    ),
    parameters={
        "usage_records": {
            "type": "array",
            "description": (
                "Kullanım kayıtları listesi. Her kayıt: "
                "{'agent': str, 'model': str, 'input_tokens': int, "
                "'output_tokens': int, 'cost': float}"
            ),
        },
    },
    required=["usage_records"],
)


# ─── Test Bloğu ───

if __name__ == "__main__":
    print("=" * 60)
    print("  Maliyet Raporlama Aracı - Test")
    print("=" * 60)
    
    # Test verileri
    test_kayitlari = [
        {
            "agent": "researcher",
            "model": "gpt-4o-mini",
            "input_tokens": 1500,
            "output_tokens": 800,
            "cost": 0.000705,
            "output_words": 150,
        },
        {
            "agent": "researcher",
            "model": "gpt-4o-mini",
            "input_tokens": 2000,
            "output_tokens": 600,
            "cost": 0.00066,
            "output_words": 120,
        },
        {
            "agent": "writer",
            "model": "gpt-4o",
            "input_tokens": 3000,
            "output_tokens": 2500,
            "cost": 0.0325,
            "output_words": 500,
        },
        {
            "agent": "writer",
            "model": "gpt-4o",
            "input_tokens": 2500,
            "output_tokens": 2000,
            "cost": 0.02625,
            "output_words": 400,
        },
        {
            "agent": "editor",
            "model": "gpt-4o-mini",
            "input_tokens": 4000,
            "output_tokens": 1000,
            "cost": 0.0012,
            "output_words": 200,
        },
        {
            "agent": "evaluator",
            "model": "gpt-4o-mini",
            "input_tokens": 1000,
            "output_tokens": 500,
            "cost": 0.00045,
            "output_words": 80,
        },
    ]
    
    rapor = generate_cost_report(test_kayitlari)
    
    print(f"\nToplam Maliyet: ${rapor['total_cost']:.6f}")
    print(f"Toplam Çağrı: {rapor['total_calls']}")
    print(f"Toplam Token: {rapor['total_tokens']:,}")
    print(f"Kelime Başına: ${rapor['cost_per_word']:.8f}")
    
    # Ajan kırılımı
    print(f"\nAjan Bazında:")
    for agent, am in rapor["per_agent_cost"].items():
        print(f"  {agent}: ${am['total_cost']:.6f} (%{am['cost_percentage']})")
    
    # Model kırılımı
    print(f"\nModel Bazında:")
    for model, mm in rapor["per_model_cost"].items():
        print(f"  {model}: ${mm['total_cost']:.6f} ({mm['tier']})")
    
    # Öneriler
    print(f"\nOptimizasyon Önerileri:")
    for o in rapor["optimization_suggestions"]:
        print(f"  - {o}")
    
    # Özet metin
    print(rapor["summary"])
    
    # Boş kayıt testi
    print("\n--- Boş Kayıt Testi ---")
    bos_rapor = generate_cost_report([])
    print(f"  Toplam: ${bos_rapor['total_cost']}")
    print(f"  Öneri: {bos_rapor['optimization_suggestions'][0]}")
    
    print("\nTest tamamlandı!")

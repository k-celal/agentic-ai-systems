"""
TwinGraph Studio - Değerlendirme (Evaluation) Modülü
=====================================================
Pipeline çıktılarının kalitesini ve maliyet verimliliğini ölçen araçlar.

Bu modül iki temel değerlendirici içerir:

1. WritingEvaluator  → Makale kalitesini 5 boyutta puanlar
2. CostEvaluator     → Pipeline maliyet verimliliğini ölçer

Neden Evaluation Gerekli?
--------------------------
Bir agent pipeline'ı çalıştırdığınızda iki soru kritiktir:
- Çıktı kalitesi yeterli mi?
- Maliyet makul mü?

Bu modül, her ikisini de sistematik ve tekrarlanabilir şekilde ölçer.
LLM gerektirmez — tüm değerlendirmeler kural tabanlıdır.

Kullanım:
    from evals.writing_eval import WritingEvaluator
    from evals.cost_eval import CostEvaluator
"""

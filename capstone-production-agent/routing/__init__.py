"""
TwinGraph Studio - Model Yönlendirme (Routing) Modülü
======================================================
Görev karmaşıklığına göre en uygun LLM modelini seçen akıllı yönlendirici.

Bu modül, TwinGraphModelRouter sınıfını içerir.

Neden Model Yönlendirme?
--------------------------
Her LLM görevi aynı karmaşıklıkta değildir:
- Araştırma özetleme → gpt-4o-mini yeterli
- Yaratıcı yazım → gpt-4o gerekli
- Kalite değerlendirme → gpt-4o-mini yeterli

Akıllı yönlendirme ile aynı kalitede %40-70 maliyet tasarrufu mümkündür.

Kullanım:
    from routing.model_router import TwinGraphModelRouter

    router = TwinGraphModelRouter()
    choice = router.route("writing", content_length=1500)
    print(f"Model: {choice.model} | Neden: {choice.reason}")
"""

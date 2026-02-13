"""
Module 2 Testleri - Reflection
================================
Çalıştırma: cd module-02-reflection && python -m pytest tests/ -v
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


class TestValidationTool:
    """Validation tool testleri."""
    
    def test_valid_content(self):
        """Geçerli içerik True döndürmeli."""
        from mcp.tools.validate import validate_content
        
        result = validate_content(
            content="Bu yeterince uzun bir test metnidir. " * 5,
            min_length=50,
        )
        assert result["is_valid"] is True
        assert result["score"] >= 7
    
    def test_short_content(self):
        """Kısa içerik ihlal bildirmeli."""
        from mcp.tools.validate import validate_content
        
        result = validate_content(content="Kısa", min_length=100)
        assert result["is_valid"] is False
        assert any("kısa" in v.lower() for v in result["violations"])
    
    def test_missing_keywords(self):
        """Eksik anahtar kelimeler ihlal bildirmeli."""
        from mcp.tools.validate import validate_content
        
        result = validate_content(
            content="Bu bir test metnidir. " * 5,
            min_length=10,
            required_keywords=["Python", "programlama"],
        )
        assert result["is_valid"] is False
        assert any("eksik" in v.lower() for v in result["violations"])
    
    def test_forbidden_words(self):
        """Yasak kelimeler ihlal bildirmeli."""
        from mcp.tools.validate import validate_content
        
        result = validate_content(
            content="Bu bir TODO metin PLACEHOLDER içerir. " * 3,
            min_length=10,
            forbidden_words=["TODO", "PLACEHOLDER"],
        )
        assert result["is_valid"] is False
    
    def test_stats(self):
        """İstatistikler doğru hesaplanmalı."""
        from mcp.tools.validate import validate_content
        
        result = validate_content(content="Bir iki üç dört beş. Altı yedi sekiz.")
        assert "stats" in result
        assert result["stats"]["word_count"] > 0
        assert result["stats"]["sentence_count"] >= 1


class TestGeneratedContent:
    """GeneratedContent testleri."""
    
    def test_creation(self):
        """GeneratedContent oluşturulabilmeli."""
        from agent.generate import GeneratedContent
        
        gc = GeneratedContent(content="Test", task="Test görevi")
        assert gc.content == "Test"
        assert gc.iteration == 1


class TestCritiqueResult:
    """CritiqueResult testleri."""
    
    def test_creation(self):
        """CritiqueResult oluşturulabilmeli."""
        from agent.critique import CritiqueResult
        
        cr = CritiqueResult(score=8, issues=[], suggestions=[])
        assert cr.score == 8
        assert cr.is_acceptable is False  # Varsayılan threshold henüz set edilmedi
    
    def test_with_issues(self):
        """CritiqueResult sorunları tutabilmeli."""
        from agent.critique import CritiqueResult
        
        cr = CritiqueResult(
            score=4,
            issues=["Sorun 1", "Sorun 2"],
            suggestions=["Öneri 1"],
        )
        assert len(cr.issues) == 2
        assert len(cr.suggestions) == 1


class TestReflectionResult:
    """ReflectionResult testleri."""
    
    def test_creation(self):
        """ReflectionResult oluşturulabilmeli."""
        from agent.improve import ReflectionResult
        
        rr = ReflectionResult(task="Test görevi")
        assert rr.status == "pending"
        assert rr.iterations == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

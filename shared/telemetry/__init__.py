"""
Telemetry - Loglama, İzleme ve Maliyet Takibi
================================================
Agent sisteminin çalışmasını izlememizi sağlar.

Kullanım:
    from shared.telemetry.logger import get_logger
    from shared.telemetry.cost_tracker import CostTracker
    
    logger = get_logger("my_agent")
    logger.info("Agent başlatıldı")
    
    tracker = CostTracker()
    tracker.add_usage(input_tokens=100, output_tokens=50)
"""

from shared.telemetry.logger import get_logger
from shared.telemetry.cost_tracker import CostTracker

__all__ = ["get_logger", "CostTracker"]

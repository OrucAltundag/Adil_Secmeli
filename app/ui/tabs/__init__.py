# -*- coding: utf-8 -*-
# =============================================================================
# app/ui/tabs — Ana Arayuz Sekmeleri Paketi
# =============================================================================
# ViewTab, AnalysisTab, CalcTab, PoolTab, RelationsTab, ToolsTab siniflarini disa aktarir.
# =============================================================================

from .analysis_tab import AnalysisTab
from .calc_tab import CalcTab
from .pool_tab import PoolTab
from .relations_tab import RelationsTab
from .tools_tab import ToolsTab
from .view_tab import ViewTab

__all__ = [
    "ViewTab", "AnalysisTab", "CalcTab", "PoolTab", "RelationsTab", "ToolsTab"
]

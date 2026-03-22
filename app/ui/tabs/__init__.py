# -*- coding: utf-8 -*-
# =============================================================================
# app/ui/tabs — Ana Arayuz Sekmeleri Paketi
# =============================================================================
# ViewTab, AnalysisTab, CalcTab, PoolTab, RelationsTab, ToolsTab siniflarini disa aktarir.
# =============================================================================

from .view_tab import ViewTab
from .analysis_tab import AnalysisTab
from .calc_tab import CalcTab
from .pool_tab import PoolTab
from .relations_tab import RelationsTab
from .tools_tab import ToolsTab

__all__ = [
    "ViewTab", "AnalysisTab", "CalcTab", "PoolTab", "RelationsTab", "ToolsTab"
]

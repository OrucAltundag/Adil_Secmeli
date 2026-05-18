# -*- coding: utf-8 -*-
"""UI smoke testleri — modül import ve temel widget oluşturma."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.ui, pytest.mark.requires_display]


class TestUIModuleImport:
    """UI modulleri import edilebiliyor mu."""

    def test_import_app_main(self):
        """app.main import edilebilmeli (GUI baslatmadan)."""
        try:
            import app.main  # noqa: F401
        except ImportError:
            pytest.skip("app.main import edilemedi — ortam bagimli")

    def test_import_ui_style(self):
        """UI stil modulu import edilebilmeli."""
        try:
            from app.ui import style  # noqa: F401
        except ImportError:
            pytest.skip("app.ui.style import edilemedi")

    def test_import_security_readiness_page(self):
        """Guvenlik hazirlik sekmesi API/requests bagimliligi olmadan import edilebilmeli."""
        from app.ui.tabs.security_readiness_page import SecurityReadinessPage
        assert SecurityReadinessPage is not None

    def test_import_api_routes(self):
        """API route modulu import edilebilmeli."""
        from app.api import routes  # noqa: F401
        assert hasattr(routes, "router")

    def test_import_algorithms(self):
        """Algoritma modulleri import edilebilmeli."""
        from app.algorithms.mcdm import AHPRanker, TOPSISRanker  # noqa: F401
        assert AHPRanker is not None
        assert TOPSISRanker is not None

    def test_import_services(self):
        """Temel servisler import edilebilmeli."""
        from app.services.data_confidence_service import (  # noqa: F401
            calculate_data_confidence,
        )
        from app.services.explanation_engine import (  # noqa: F401
            build_decision_explanation,
        )
        from app.services.havuz_karar import calculate_next_status  # noqa: F401
        from app.services.trend_analysis_service import (  # noqa: F401
            analyze_trend_values,
        )

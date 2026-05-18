"""Benchmark Platform page classes."""

from app.ui.benchmark.pages.algorithm_explorer_page import AlgorithmExplorerPage
from app.ui.benchmark.pages.algorithm_governance_page import AlgorithmGovernancePage
from app.ui.benchmark.pages.allocation_fairness_page import AllocationFairnessPage
from app.ui.benchmark.pages.comparison_page import ComparisonPage
from app.ui.benchmark.pages.dashboard_page import DashboardPage
from app.ui.benchmark.pages.dataset_lab_page import DatasetLabPage
from app.ui.benchmark.pages.decision_engine_page import DecisionEnginePage
from app.ui.benchmark.pages.ml_readiness_page import MLReadinessPage
from app.ui.benchmark.pages.run_history_page import RunHistoryPage

__all__ = [
    "DashboardPage",
    "ComparisonPage",
    "DatasetLabPage",
    "AlgorithmExplorerPage",
    "AlgorithmGovernancePage",
    "AllocationFairnessPage",
    "DecisionEnginePage",
    "MLReadinessPage",
    "RunHistoryPage",
]

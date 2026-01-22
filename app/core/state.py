# app/state.py
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional, List, Any


@dataclass
class AppState:
    # DB / genel
    db_path: Optional[str] = None
    current_table: Optional[str] = None

    # Pool filtreleri
    selected_faculty: Optional[str] = None
    selected_department: Optional[str] = None
    selected_year: int = 2025
    hide_resting: bool = False

    # Cache
    results_cache: Dict[str, str] = field(default_factory=dict)

    # mini event system (opsiyonel ama çok işe yarar)
    _listeners: Dict[str, List[Callable[[Any], None]]] = field(default_factory=dict, init=False, repr=False)

    def on(self, key: str, callback: Callable[[Any], None]) -> None:
        """state.key değişince callback çalışsın."""
        self._listeners.setdefault(key, []).append(callback)

    def set(self, key: str, value: Any) -> None:
        """state alanını güncelle + dinleyicileri tetikle."""
        setattr(self, key, value)
        for cb in self._listeners.get(key, []):
            try:
                cb(value)
            except Exception:
                pass

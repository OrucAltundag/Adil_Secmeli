from app.ui.tabs.calc_tab import CalcTab


class _DummyCombo:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value


class _DummyStatus:
    def __init__(self, text="Bekliyor..."):
        self.text = text

    def cget(self, key):
        if key != "text":
            raise KeyError(key)
        return self.text


def test_next_year_batch_runs_all_individual_algorithms_in_order():
    tab = CalcTab.__new__(CalcTab)
    tab.ui_refs = {
        "mock": {"status": _DummyStatus()},
        "trend": {"status": _DummyStatus()},
        "ahp": {"status": _DummyStatus()},
        "topsis": {"status": _DummyStatus()},
        "lr": {"status": _DummyStatus()},
        "rf": {"status": _DummyStatus()},
        "dt": {"status": _DummyStatus()},
        "next_year": {"status": _DummyStatus()},
    }

    calls = []

    def fake_run_single_step(algo_id):
        calls.append(algo_id)
        tab.ui_refs[algo_id]["status"].text = "Tamamlandi"

    tab.run_single_step = fake_run_single_step

    results = tab._run_full_algorithm_batch_for_next_year()

    assert calls == ["mock", "trend", "ahp", "topsis", "lr", "rf", "dt"]
    assert [item["id"] for item in results] == calls
    assert all(item["ok"] is True for item in results)


def test_missing_algo_scope_message_lists_empty_fields():
    tab = CalcTab.__new__(CalcTab)
    tab.cb_algo_fakulte = _DummyCombo("")
    tab.cb_algo_year = _DummyCombo("")

    message = tab._missing_algo_scope_message()

    assert "Fakülte" in message
    assert "Akademik yıl" in message

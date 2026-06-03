from app.ui.utils import validation


class DummyWidget:
    def __init__(self, value=""):
        self.value = value
        self.focused = False

    def get(self):
        return self.value

    def focus(self):
        self.focused = True


def test_empty_combobox_selection_uses_warning(monkeypatch):
    calls = []
    monkeypatch.setattr(validation.messagebox, "showwarning", lambda title, message: calls.append((title, message)))

    widget = DummyWidget("")

    assert validation.validate_combobox_selection(widget, "Fakülte") is False
    assert calls == [("Eksik Alan", "Fakülte seçilmelidir.")]
    assert widget.focused is True


def test_empty_required_field_uses_warning(monkeypatch):
    calls = []
    monkeypatch.setattr(validation.messagebox, "showwarning", lambda title, message: calls.append((title, message)))

    widget = DummyWidget("")

    assert validation.validate_required_field(widget, "Profil adı") is False
    assert calls == [("Eksik Alan", "Profil adı boş bırakılamaz.")]
    assert widget.focused is True

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from receipt_autofill.app import MainWindow, PageEditorDialog
from receipt_autofill.browser_helper import BrowserController
from receipt_autofill.models import PageDefinition, PageEntry
from receipt_autofill.storage import AppDataStore


app = QApplication.instance() or QApplication([])


def test_page_validation_requires_name():
    page = PageDefinition(name="", entries=[PageEntry(selector="#invoice", text="100")])
    assert page.is_valid() is False

    page.name = "Invoice Page"
    assert page.is_valid() is True


def test_store_saves_and_loads_pages(tmp_path):
    storage_path = Path(tmp_path) / "receipt_autofill.json"
    store = AppDataStore(storage_path)

    page = PageDefinition(
        name="Invoice Page",
        entries=[
            PageEntry(selector="#amount", text="42.50"),
            PageEntry(selector="#vendor", text="Contoso"),
        ],
    )

    store.save_pages([page])
    loaded = store.load_pages()

    assert len(loaded) == 1
    assert loaded[0].name == "Invoice Page"
    assert loaded[0].entries[0].selector == "#amount"
    assert loaded[0].entries[1].text == "Contoso"


def test_main_window_refresh_after_delete_keeps_single_empty_state():
    main_window = MainWindow()
    main_window.pages = []
    main_window.refresh_cards()
    assert main_window.cards_layout.count() == 1

    page = PageDefinition(name="Invoice Page", entries=[PageEntry(selector="#amount", text="42.50")])
    main_window.pages = [page]
    main_window.refresh_cards()
    assert main_window.cards_layout.count() == 1

    main_window.delete_page(page)
    assert len(main_window.pages) == 0
    assert main_window.cards_layout.count() == 1


def test_store_saves_and_loads_last_url(tmp_path):
    storage_path = Path(tmp_path) / "receipt_autofill.json"
    store = AppDataStore(storage_path)

    store.save_last_url("https://example.com/invoice")
    assert store.load_last_url() == "https://example.com/invoice"


def test_main_window_navigate_uses_visible_selenium_browser(monkeypatch):
    main_window = MainWindow()
    calls = []

    class FakeBrowser:
        def __init__(self):
            self.opened = []

        def open_url(self, url):
            self.opened.append(url)
            calls.append(url)

    fake_browser = FakeBrowser()
    monkeypatch.setattr(main_window, "_ensure_browser", lambda: fake_browser)
    main_window.url_input.setText("https://example.com/invoice")
    main_window.open_main_page()

    assert fake_browser.opened == ["https://example.com/invoice"]
    assert calls == ["https://example.com/invoice"]
    assert main_window.store.load_last_url() == "https://example.com/invoice"


def test_fill_page_uses_its_own_browser_session(monkeypatch):
    main_window = MainWindow()
    calls = []

    class FakeBrowser:
        def __init__(self):
            self.opened = []

        def open_url(self, url):
            self.opened.append(url)

        def fill_value(self, selector, text):
            calls.append((selector, text))
            return True

    fake_browser = FakeBrowser()
    monkeypatch.setattr(main_window, "_ensure_browser", lambda: fake_browser)
    monkeypatch.setattr("receipt_autofill.app.QMessageBox.information", lambda *args, **kwargs: None)
    main_window.url_input.setText("https://example.com/invoice")
    page = PageDefinition(name="Invoice", entries=[PageEntry(selector="#username", text="evaldo"), PageEntry(selector="#amount", text="42")])

    main_window.fill_page(page)

    assert fake_browser.opened == ["https://example.com/invoice"]
    assert calls == [("#username", "evaldo"), ("#amount", "42")]


def test_browser_controller_prefers_edge_when_available(monkeypatch):
    calls = {}

    def fake_exists(path):
        return path.endswith("msedge.exe")

    class FakeEdgeOptions:
        def __init__(self):
            self.binary_location = None

        def add_argument(self, argument):
            pass

    class FakeDriver:
        def __init__(self, **kwargs):
            calls["kwargs"] = kwargs

    monkeypatch.setattr("receipt_autofill.browser_helper.os.path.exists", fake_exists)
    monkeypatch.setattr("receipt_autofill.browser_helper.EdgeOptions", FakeEdgeOptions)
    monkeypatch.setattr("receipt_autofill.browser_helper.EdgeChromiumDriverManager.install", lambda self: "msedgedriver")
    monkeypatch.setattr("receipt_autofill.browser_helper.webdriver.Edge", FakeDriver)
    monkeypatch.setattr("receipt_autofill.browser_helper.webdriver.Chrome", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("Chrome should not be used when Edge is installed")))

    _ = BrowserController()

    assert "kwargs" in calls
    assert calls["kwargs"]["options"].binary_location.endswith("msedge.exe")


def test_page_editor_shows_empty_state_when_no_rows():
    dialog = PageEditorDialog()
    assert dialog.rows_layout.count() == 1
    empty_widget = dialog.rows_layout.itemAt(0).widget()
    assert empty_widget is not None
    assert "No elements yet" in empty_widget.text()


def test_page_editor_add_row_handles_signal_checked_bool():
    dialog = PageEditorDialog()
    dialog.add_row(True)
    assert len(dialog.entry_rows) == 1
    assert dialog.page.entries[0].selector == ""
    assert dialog.page.entries[0].text == ""


def test_page_editor_add_row_creates_new_entry():
    dialog = PageEditorDialog()
    dialog.add_row("#invoice", "42.50")
    assert len(dialog.entry_rows) == 1
    assert dialog.rows_layout.count() == 1
    assert dialog.page.entries[0].selector == "#invoice"
    assert dialog.page.entries[0].text == "42.50"

    dialog.new_selector_input.clear()
    dialog.new_text_input.clear()
    dialog.add_row()
    assert len(dialog.entry_rows) == 2
    assert dialog.rows_layout.count() == 2


def test_page_editor_editing_row_updates_page_entries():
    dialog = PageEditorDialog()
    dialog.add_row("#amount", "10")
    dialog.entry_rows[0][1].setText("#total")
    dialog.entry_rows[0][2].setText("99.99")
    assert dialog.page.entries[0].selector == "#total"
    assert dialog.page.entries[0].text == "99.99"


def test_page_editor_remove_row_updates_page_entries_and_layout():
    dialog = PageEditorDialog()
    dialog.add_row("#first", "A")
    dialog.add_row("#second", "B")

    row_widget = dialog.entry_rows[0][0]
    dialog.remove_row(row_widget)

    assert len(dialog.entry_rows) == 1
    assert dialog.rows_layout.count() == 1
    assert dialog.page.entries[0].selector == "#second"
    assert dialog.page.entries[0].text == "B"


def test_page_editor_move_row_reorders_entries():
    dialog = PageEditorDialog()
    dialog.add_row("#first", "A")
    dialog.add_row("#second", "B")

    row_widget = dialog.entry_rows[1][0]
    dialog.move_row(row_widget, -1)

    assert [entry.selector for entry in dialog.page.entries] == ["#second", "#first"]
    assert [entry.text for entry in dialog.page.entries] == ["B", "A"]


def test_page_editor_skips_blank_selector_rows():
    dialog = PageEditorDialog()
    dialog.name_input.setText("Invoice")
    dialog.add_row("#username", "evaldo")
    dialog.add_row("", "ignored")
    dialog.add_row("#password", "pass")
    dialog.add_row("   ", "ignored")

    dialog.validate_and_accept()
    selectors = [entry.selector for entry in dialog.page.entries]
    assert selectors == ["#username", "#password"]


def test_fill_page_reports_missing_selectors(monkeypatch):
    main_window = MainWindow()
    info_calls = {}

    class FakeBrowser:
        def __init__(self):
            self.opened = []
            self.current_url = "about:blank"

        def open_url(self, url):
            self.current_url = url
            self.opened.append(url)

        def fill_value(self, selector, text):
            return selector == "#username"

    fake_browser = FakeBrowser()
    monkeypatch.setattr(main_window, "_ensure_browser", lambda: fake_browser)

    def fake_info(_parent, title, text):
        info_calls["title"] = title
        info_calls["text"] = text

    monkeypatch.setattr("receipt_autofill.app.QMessageBox.information", fake_info)
    main_window.url_input.setText("https://example.com/invoice")
    page = PageDefinition(
        name="Invoice",
        entries=[
            PageEntry(selector="#username", text="evaldo"),
            PageEntry(selector="#amount", text="42"),
            PageEntry(selector="", text="ignored"),
        ],
    )

    main_window.fill_page(page)

    assert info_calls["title"] == "Filled"
    assert "Filled 1 field(s)" in info_calls["text"]
    assert "Missing selectors:" in info_calls["text"]
    assert "#amount" in info_calls["text"]


def test_fill_page_does_not_reload_when_browser_already_on_a_page(monkeypatch):
    main_window = MainWindow()

    class FakeBrowser:
        def __init__(self):
            self.current_url = "https://fill.dev/login"
            self.opened = []

        def open_url(self, url):
            self.current_url = url
            self.opened.append(url)

        def fill_value(self, selector, text):
            return True

    fake_browser = FakeBrowser()
    monkeypatch.setattr(main_window, "_ensure_browser", lambda: fake_browser)
    monkeypatch.setattr("receipt_autofill.app.QMessageBox.information", lambda *args, **kwargs: None)
    main_window.url_input.setText("https://fill.dev/")
    page = PageDefinition(name="Login", entries=[PageEntry(selector="#password", text="secret")])

    main_window.fill_page(page)

    assert fake_browser.opened == []
    assert fake_browser.current_url == "https://fill.dev/login"


def test_page_editor_scrolling_is_enabled_for_many_rows():
    dialog = PageEditorDialog()
    for idx in range(20):
        dialog.add_row(f"#field{idx}", str(idx))

    assert dialog.rows_layout.alignment() == Qt.AlignmentFlag.AlignTop
    assert dialog.rows_scroll.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOn
    assert dialog.rows_scroll.minimumHeight() >= 180

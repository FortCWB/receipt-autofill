from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .browser_helper import BrowserController
from .models import PageDefinition, PageEntry
from .storage import AppDataStore


class PageEditorDialog(QDialog):
    def __init__(self, page: PageDefinition | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit page" if page else "New page")
        self.resize(760, 540)
        self.setStyleSheet(
            """
            QDialog { background: #f5f7fb; }
            QLabel { color: #1f2a37; }
            QLineEdit {
                background: #ffffff;
                border: 1px solid #c9d3df;
                border-radius: 8px;
                padding: 7px 10px;
                color: #1f2a37;
            }
            QPushButton {
                background: #e9eef7;
                border: 1px solid #b9c6d8;
                border-radius: 8px;
                padding: 7px 12px;
                color: #1f2a37;
            }
            QPushButton:hover { background: #dfe8f5; }
            QPushButton#dangerButton { background: #fff1f1; border-color: #e7b8b8; color: #a63a3a; }
            QPushButton#doneButton { background: #2f7d32; color: white; border-color: #245f28; }
            QPushButton#cancelButton { background: #edf0f5; border-color: #bcc7d5; }
            QWidget#quickAddPanel { background: #f8fafc; border: 1px solid #d9e1ed; border-radius: 10px; }
            QWidget#rowsPanel { background: #ffffff; border: 1px solid #d9e1ed; border-radius: 10px; }
            QWidget#entryRowCard { background: #f8fafc; border: 1px solid #d9e1ed; border-radius: 10px; }
            QLabel#emptyRowsLabel { color: #667085; font-style: italic; }
            """
        )
        self.page = page or PageDefinition()
        self.entry_rows: list[tuple[QWidget, QLineEdit, QLineEdit, QPushButton, QPushButton, QPushButton]] = []
        self.name_input = QLineEdit(self.page.name)
        self.name_input.textChanged.connect(self._auto_save)

        self.page_name_error = QLabel("")
        self.page_name_error.setStyleSheet("color: #d93025;")

        self.new_selector_input = QLineEdit()
        self.new_selector_input.setPlaceholderText("Web element")
        self.new_text_input = QLineEdit()
        self.new_text_input.setPlaceholderText("Text to fill")
        self.add_row_button = QPushButton("Add row")
        self.add_row_button.setFixedWidth(120)
        self.add_row_button.clicked.connect(lambda: self.add_row())

        self.quick_add_row = QWidget()
        self.quick_add_row.setObjectName("quickAddPanel")
        quick_layout = QHBoxLayout(self.quick_add_row)
        quick_layout.setContentsMargins(12, 12, 12, 12)
        quick_layout.setSpacing(8)
        quick_layout.addWidget(QLabel("Web element"))
        quick_layout.addWidget(self.new_selector_input, 2)
        quick_layout.addWidget(QLabel("Text"))
        quick_layout.addWidget(self.new_text_input, 2)
        quick_layout.addWidget(self.add_row_button)

        self.header_row = QHBoxLayout()
        self.header_row.addWidget(QLabel("Web element"), 2)
        self.header_row.addWidget(QLabel("Text"), 2)
        self.header_row.addWidget(QLabel("Order"), 1)
        self.header_row.addWidget(QLabel(""), 1)

        self.rows_container = QWidget()
        self.rows_container.setObjectName("rowsPanel")
        self.rows_layout = QVBoxLayout(self.rows_container)
        self.rows_layout.setContentsMargins(12, 12, 12, 12)
        self.rows_layout.setSpacing(10)

        self.rows_scroll = QScrollArea()
        self.rows_scroll.setWidgetResizable(True)
        self.rows_scroll.setFrameShape(self.rows_scroll.Shape.NoFrame)
        self.rows_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.rows_scroll.setMinimumHeight(180)
        self.rows_scroll.setWidget(self.rows_container)

        self.done_button = QPushButton("Done")
        self.done_button.setObjectName("doneButton")
        self.done_button.clicked.connect(self.validate_and_accept)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("cancelButton")
        self.cancel_button.clicked.connect(self.reject)

        button_row = QHBoxLayout()
        button_row.addStretch()
        button_row.addWidget(self.done_button)
        button_row.addWidget(self.cancel_button)

        root = QVBoxLayout(self)
        root.addWidget(QLabel("Page name"))
        root.addWidget(self.name_input)
        root.addWidget(self.page_name_error)
        root.addWidget(QLabel("Entries"))
        root.addWidget(self.quick_add_row)
        root.addLayout(self.header_row)
        root.addWidget(self.rows_scroll)
        root.addLayout(button_row)

        self._rebuild_rows()
        for entry in self.page.entries:
            self.add_row(entry.selector, entry.text)

    def _auto_save(self) -> None:
        self.page.name = self.name_input.text().strip()

    def _create_row_widget(self, selector: str, text: str):
        selector_field = QLineEdit(str(selector))
        text_field = QLineEdit(str(text))

        up_button = QPushButton("↑")
        up_button.setFixedWidth(32)
        down_button = QPushButton("↓")
        down_button.setFixedWidth(32)
        remove_button = QPushButton("Remove")
        remove_button.setObjectName("dangerButton")

        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)
        row_layout.addWidget(selector_field, 2)
        row_layout.addWidget(text_field, 2)
        row_layout.addWidget(up_button, 1)
        row_layout.addWidget(down_button, 1)
        row_layout.addWidget(remove_button, 1)

        up_button.clicked.connect(lambda checked=False, widget=row_widget: self.move_row(widget, -1))
        down_button.clicked.connect(lambda checked=False, widget=row_widget: self.move_row(widget, 1))
        remove_button.clicked.connect(lambda checked=False, widget=row_widget: self.remove_row(widget))
        selector_field.textChanged.connect(self._sync_row_data)
        text_field.textChanged.connect(self._sync_row_data)

        return row_widget, selector_field, text_field, up_button, down_button, remove_button

    def add_row(self, selector: str | bool = "", text: str = "") -> None:
        if isinstance(selector, bool):
            selector = ""

        if isinstance(text, bool):
            text = ""

        if selector == "" and text == "":
            selector = self.new_selector_input.text().strip()
            text = self.new_text_input.text().strip()

        row_data = self._create_row_widget(str(selector), str(text))
        self.entry_rows.append(row_data)
        self._sync_row_data()
        self._rebuild_rows()

        self.new_selector_input.clear()
        self.new_text_input.clear()

    def _sync_row_data(self) -> None:
        entries: list[PageEntry] = []
        for _, selector_field, text_field, _, _, _ in self.entry_rows:
            selector = selector_field.text().strip()
            text = text_field.text().strip()
            entries.append(PageEntry(selector=selector, text=text))
        self.page.entries = entries

    def _rebuild_rows(self) -> None:
        current_entries = []
        for row_widget, selector_field, text_field, _, _, _ in self.entry_rows:
            current_entries.append((selector_field.text().strip(), text_field.text().strip()))

        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self.entry_rows = []

        if not current_entries:
            empty_label = QLabel("No elements yet. Add one above to begin.")
            empty_label.setObjectName("emptyRowsLabel")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            self.rows_layout.addWidget(empty_label)
            self.rows_container.adjustSize()
            return

        for selector, text in current_entries:
            row = self._create_row_widget(selector, text)
            row[0].setObjectName("entryRowCard")
            self.entry_rows.append(row)
            self.rows_layout.addWidget(row[0])

        self.rows_container.adjustSize()

    def move_row(self, row_widget: QWidget, direction: int) -> None:
        current_index = None
        for idx, (widget, _, _, _, _, _) in enumerate(self.entry_rows):
            if widget is row_widget:
                current_index = idx
                break
        if current_index is None:
            return

        target_index = current_index + direction
        if target_index < 0 or target_index >= len(self.entry_rows):
            return

        self.entry_rows[current_index], self.entry_rows[target_index] = self.entry_rows[target_index], self.entry_rows[current_index]
        self._sync_row_data()
        self._rebuild_rows()

    def remove_row(self, row_widget: QWidget) -> None:
        row_index = None
        for idx, (widget, _, _, _, _, _) in enumerate(self.entry_rows):
            if widget is row_widget:
                row_index = idx
                break

        if row_index is None:
            return

        self.entry_rows.pop(row_index)
        self._sync_row_data()
        self._rebuild_rows()

    def validate_and_accept(self) -> None:
        if not self.name_input.text().strip():
            self.page_name_error.setText("Page name is required.")
            self.name_input.setFocus()
            return
        self._auto_save()
        self.accept()


class PageCard(QWidget):
    def __init__(self, page: PageDefinition, on_edit, on_delete, on_fill) -> None:
        super().__init__()
        self.page = page
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.on_fill = on_fill
        self.setObjectName("pageCard")

        layout = QVBoxLayout(self)
        title = QLabel(page.name)
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        entries_label = QLabel(f"Entries: {len(page.entries)}")
        entries_label.setObjectName("pageMeta")
        layout.addWidget(entries_label)

        buttons = QHBoxLayout()
        edit_button = QPushButton("Edit")
        edit_button.setObjectName("pageEditButton")
        delete_button = QPushButton("Delete")
        delete_button.setObjectName("pageDeleteButton")
        fill_button = QPushButton("Fill")
        fill_button.setObjectName("pageFillButton")

        edit_button.clicked.connect(lambda: self.on_edit(page))
        delete_button.clicked.connect(lambda: self.on_delete(page))
        fill_button.clicked.connect(lambda: self.on_fill(page))

        buttons.addWidget(edit_button)
        buttons.addWidget(delete_button)
        buttons.addWidget(fill_button)
        layout.addLayout(buttons)


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.store = AppDataStore()
        self.pages = self.store.load_pages()
        self.browser = None

        self.setWindowTitle("Receipt Autofill")
        self.resize(980, 720)
        self.setStyleSheet(
            """
            QWidget { background: #f4f7fb; color: #1f2a37; }
            QWidget#pageCard {
                background: #ffffff;
                border: 1px solid #d9e1ed;
                border-radius: 14px;
                padding: 12px;
            }
            QLabel#pageTitle { font-size: 18px; font-weight: 700; color: #1f2a37; }
            QLabel#pageMeta { color: #667085; }
            QLineEdit {
                background: #ffffff;
                border: 1px solid #c9d3df;
                border-radius: 10px;
                padding: 8px 12px;
                color: #1f2a37;
            }
            QPushButton {
                background: #e9eef7;
                border: 1px solid #b9c6d8;
                border-radius: 8px;
                padding: 8px 14px;
                color: #1f2a37;
                font-weight: 600;
            }
            QPushButton:hover { background: #dfe8f5; }
            QPushButton#pageFillButton { background: #2563eb; border-color: #1d4ed8; color: white; }
            QPushButton#pageDeleteButton { background: #fff1f1; border-color: #e7b8b8; color: #a63a3a; }
            QPushButton#pageEditButton { background: #edf0f5; border-color: #bcc7d5; }
            QPushButton#navigateButton { background: #2f7d32; border-color: #245f28; color: white; }
            QPushButton#insertButton { background: #eef6ff; border-color: #b7d6ff; color: #1f3b74; }
            QScrollArea { border: none; background: transparent; }
            """
        )

        self.url_input = QLineEdit(self.store.load_last_url())
        self.url_input.setPlaceholderText("Paste page URL here")
        self.url_input.textChanged.connect(self._save_last_url)
        self.navigate_button = QPushButton("Navigate")
        self.navigate_button.setObjectName("navigateButton")
        self.navigate_button.clicked.connect(self.open_main_page)

        self.insert_button = QPushButton("Insert new page")
        self.insert_button.setObjectName("insertButton")
        self.insert_button.setFixedWidth(180)
        self.insert_button.clicked.connect(self.insert_new_page)

        header = QHBoxLayout()
        header.addWidget(self.url_input)
        header.addWidget(self.navigate_button)

        top_area = QVBoxLayout()
        top_area.addLayout(header)
        top_area.addWidget(self.insert_button)

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(8, 8, 8, 8)
        self.cards_layout.setSpacing(16)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.cards_container)

        root = QVBoxLayout(self)
        root.addLayout(top_area)
        root.addWidget(scroll)

        self.refresh_cards()

    def closeEvent(self, event) -> None:
        if self.browser is not None:
            self.browser.close()
            self.browser = None
        self._save_last_url()
        event.accept()

    def _save_last_url(self) -> None:
        self.store.save_last_url(self.url_input.text().strip())

    def _ensure_browser(self):
        if self.browser is None:
            self.browser = BrowserController()
        return self.browser

    def save_pages(self) -> None:
        self.store.save_pages(self.pages)

    def refresh_cards(self) -> None:
        while self.cards_layout.count() > 0:
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if not self.pages:
            empty_label = QLabel("No pages yet. Click Insert new page to add one.")
            empty_label.setStyleSheet("color: #666; font-style: italic;")
            self.cards_layout.addWidget(empty_label)
            return

        for page in self.pages:
            card = PageCard(page, self.edit_page, self.delete_page, self.fill_page)
            self.cards_layout.addWidget(card)

    def open_main_page(self) -> None:
        page_url = self.url_input.text().strip()
        if not page_url:
            QMessageBox.warning(self, "Page URL required", "Please paste a page URL before navigating.")
            return
        self._save_last_url()

        try:
            browser = self._ensure_browser()
            browser.open_url(page_url)
        except Exception as exc:  # pragma: no cover - UI warning path
            QMessageBox.critical(self, "Navigate failed", f"Could not open the page in the Selenium browser: {exc}")
            return

    def insert_new_page(self) -> None:
        dialog = PageEditorDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if dialog.page.name.strip():
                self.pages.append(dialog.page)
                self.store.save_pages(self.pages)
                self.refresh_cards()

    def edit_page(self, page: PageDefinition) -> None:
        dialog = PageEditorDialog(page=page, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if dialog.page.name.strip():
                for idx, existing in enumerate(self.pages):
                    if existing.id == page.id:
                        self.pages[idx] = dialog.page
                        break
                self.store.save_pages(self.pages)
                self.refresh_cards()

    def delete_page(self, page: PageDefinition) -> None:
        self.pages = [existing for existing in self.pages if existing.id != page.id]
        self.store.save_pages(self.pages)
        self.refresh_cards()

    def fill_page(self, page: PageDefinition) -> None:
        if not self.url_input.text().strip():
            QMessageBox.warning(self, "URL required", "Paste the page URL into the main field before filling data.")
            return

        if not page.entries:
            QMessageBox.information(self, "No entries", "This page has no entries to fill.")
            return

        self._save_last_url()
        browser = self._ensure_browser()
        try:
            url = self.url_input.text().strip()
            browser.open_url(url)
            filled_count = 0
            for entry in page.entries:
                if entry.selector and entry.text:
                    if browser.fill_value(entry.selector, entry.text):
                        filled_count += 1
            QMessageBox.information(self, "Filled", f"Filled {filled_count} field(s) on the active browser page.")
        except Exception as exc:  # pragma: no cover - UI warning path
            QMessageBox.critical(self, "Fill failed", f"Could not fill values: {exc}")


def main() -> None:
    app = QApplication([])
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, "#f3f3f3")
    palette.setColor(QPalette.ColorRole.WindowText, "#1b1b1b")
    palette.setColor(QPalette.ColorRole.Base, "#ffffff")
    palette.setColor(QPalette.ColorRole.AlternateBase, "#ececec")
    palette.setColor(QPalette.ColorRole.ToolTipBase, "#ffffff")
    palette.setColor(QPalette.ColorRole.ToolTipText, "#1b1b1b")
    palette.setColor(QPalette.ColorRole.Text, "#1b1b1b")
    palette.setColor(QPalette.ColorRole.Button, "#e2e2e2")
    palette.setColor(QPalette.ColorRole.ButtonText, "#1b1b1b")
    palette.setColor(QPalette.ColorRole.Highlight, "#2d6cdf")
    palette.setColor(QPalette.ColorRole.HighlightedText, "#ffffff")
    app.setPalette(palette)

    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()

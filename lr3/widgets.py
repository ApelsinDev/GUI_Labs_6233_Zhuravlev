"""Вкладка результата: SQL, табличное представление и количество строк."""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView, QFrame, QHBoxLayout, QHeaderView, QLabel,
    QPlainTextEdit, QStackedWidget, QTableView, QVBoxLayout, QWidget,
)


def label(text, object_name):
    widget = QLabel(text)
    widget.setObjectName(object_name)
    return widget


class ResultPage(QWidget):
    def __init__(self, title):
        super().__init__()
        self.model = None
        self.last_sql = ""
        self.setObjectName("resultPage")
        self.setAttribute(Qt.WA_StyledBackground, True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 18)
        layout.setSpacing(12)
        self.sql_view = QPlainTextEdit()
        self.sql_view.setObjectName("sqlPreview")
        self.sql_view.setReadOnly(True)
        self.sql_view.setFixedHeight(48)
        self.sql_view.hide()
        self.sql_view.setAccessibleName("Выполненный SQL-запрос")
        layout.addWidget(self.sql_view)

        self.stack = QStackedWidget()
        empty = QWidget()
        empty_layout = QVBoxLayout(empty)
        empty_layout.addStretch()
        self.empty_text = label("Открой базу данных", "emptyText")
        self.empty_text.setAlignment(Qt.AlignCenter)
        self.empty_text.setWordWrap(True)
        empty_layout.addWidget(self.empty_text)
        empty_layout.addStretch()
        self.stack.addWidget(empty)
        self.table = QTableView()
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setWordWrap(False)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.verticalHeader().setMinimumWidth(34)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAccessibleName(title)
        self.stack.addWidget(self.table)
        layout.addWidget(self.stack, 1)
        self.summary = label("", "resultSummary")
        self.summary.hide()
        layout.addWidget(self.summary)

    def set_result(self, model, sql):
        old_model = self.model
        self.model = model
        self.table.setModel(model)
        if old_model is not None:
            old_model.clear()
            old_model.deleteLater()
        self.last_sql = sql
        self.sql_view.setPlainText(sql)
        self.sql_view.setFixedHeight(76 if "\n" in sql else 48)
        self.sql_view.show()
        self.summary.show()
        self.stack.setCurrentIndex(1)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.resizeColumnsToContents()
        for column in range(model.columnCount()):
            width = self.table.columnWidth(column)
            self.table.setColumnWidth(column, min(420, max(64, width + 8)))
        self.table.horizontalHeader().setStretchLastSection(True)
        model.rowsInserted.connect(self.update_summary)
        self.update_summary()

    def update_summary(self, *args):
        if self.model is None:
            return
        count = self.model.rowCount()
        more = "+" if self.model.canFetchMore() else ""
        message = f"Строк: {count}{more}"
        if count == 0:
            message += " · совпадений нет"
        self.summary.setToolTip("Остальные строки загрузятся при прокрутке" if more else "")
        self.summary.setText(message)

    def clear(self, connected=False):
        self.table.setModel(None)
        if self.model is not None:
            self.model.clear()  # Освобождает SQL-запрос до закрытия соединения
            self.model.deleteLater()
            self.model = None
        self.last_sql = ""
        self.sql_view.clear()
        self.sql_view.hide()
        self.stack.setCurrentIndex(0)
        self.summary.clear()
        self.summary.setToolTip("")
        self.summary.hide()
        self.empty_text.setText(
            "Выбери запрос" if connected
            else "Открой базу данных"
        )

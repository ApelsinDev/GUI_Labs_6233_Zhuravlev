"""Бонус: модальный диалог ввода собственного SQL-запроса."""
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QComboBox, QDialog, QHBoxLayout, QLabel, QPlainTextEdit,
    QPushButton, QShortcut, QVBoxLayout,
)
from database import DatabaseError, validate_custom_query
from widgets import label


class QueryDialog(QDialog):
    def __init__(self, execute_callback, example_sql, initial_sql="", parent=None):
        super().__init__(parent)
        self.execute_callback = execute_callback
        self.example_sql = example_sql
        self.executed_sql = ""
        self.setWindowTitle("Свой SQL-запрос")
        self.setObjectName("queryDialog")
        self.setModal(True)
        self.resize(760, 500)
        self.setMinimumSize(640, 420)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(16)
        layout.addWidget(label("SQL-запрос", "dialogTitle"))
        row = QHBoxLayout()
        row.addWidget(label("Вкладка", "controlLabel"))
        self.target = QComboBox()
        self.target.setAccessibleName("Вкладка для результата запроса")
        for number, name in enumerate(("Имена", "Колонка", "Таблица 1", "Таблица 2"), 1):
            self.target.addItem(name, number)
        self.target.setCurrentIndex(2)  # Tab4, Tab1 остаётся каталогом БД!
        row.addWidget(self.target)
        row.addStretch()
        self.example_button = QPushButton("Пример")
        self.example_button.setObjectName("secondaryButton")
        self.example_button.setCursor(Qt.PointingHandCursor)
        self.example_button.setAutoDefault(False)
        self.example_button.clicked.connect(lambda: self.editor.setPlainText(self.example_sql))
        row.addWidget(self.example_button)
        layout.addLayout(row)
        self.editor = QPlainTextEdit()
        self.editor.setObjectName("queryEditor")
        self.editor.setAccessibleName("Текст SQL-запроса")
        self.editor.setPlaceholderText("SELECT name FROM sqlite_master;")
        self.editor.setPlainText(initial_sql or example_sql)
        layout.addWidget(self.editor, 1)
        self.error_label = label("", "errorLabel")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        layout.addWidget(self.error_label)
        footer = QHBoxLayout()
        footer.addStretch()
        cancel = QPushButton("Отмена")
        cancel.setObjectName("secondaryButton")
        cancel.setAutoDefault(False)
        cancel.clicked.connect(self.reject)
        self.run_button = QPushButton("Выполнить")
        self.run_button.setObjectName("primaryButton")
        self.run_button.setAutoDefault(False)
        self.run_button.setToolTip("Выполнить запрос · Ctrl+Enter")
        self.run_button.clicked.connect(self.execute)
        for button in (cancel, self.run_button):
            button.setCursor(Qt.PointingHandCursor)
            footer.addWidget(button)
        layout.addLayout(footer)
        shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        shortcut.activated.connect(self.execute)

    def execute(self):
        try:
            sql = validate_custom_query(self.editor.toPlainText())
            self.execute_callback(self.target.currentData(), sql)
        except DatabaseError as error:
            self.error_label.setText(str(error))
            self.error_label.show()
            return
        self.executed_sql = sql
        self.accept()

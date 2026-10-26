import sys
from pathlib import Path

from PyQt5.QtCore import QDir, QSignalBlocker, Qt
from PyQt5.QtGui import QFont, QIcon, QKeySequence
from PyQt5.QtWidgets import (
    QAction, QApplication, QComboBox, QFileDialog, QFrame, QHBoxLayout,
    QLabel, QMainWindow, QMessageBox, QPushButton, QTabWidget,
    QVBoxLayout, QWidget,
)
from database import DatabaseError, close_database, make_query_model, open_database, quote_identifier, user_tables
from query_dialog import QueryDialog
from widgets import ResultPage, label

BASE_DIR = Path(__file__).resolve().parent
MASTER_COLUMNS = ("type", "name", "tbl_name", "rootpage", "sql")
TAB_TITLES = ("Структура", "Имена", "Колонка", "Таблица 1", "Таблица 2")
JOIN_EXAMPLE = '''SELECT f.title AS "Фильм",
       d.name AS "Режиссёр",
       f.year AS "Год",
       f.rating AS "Рейтинг"
FROM films AS f
JOIN directors AS d ON d.id = f.director_id
WHERE f.rating >= 8
ORDER BY f.rating DESC;'''


def button(text, object_name):
    widget = QPushButton(text)
    widget.setObjectName(object_name)
    widget.setCursor(Qt.PointingHandCursor)
    return widget


def combo(name):
    widget = QComboBox()
    widget.setAccessibleName(name)
    widget.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
    widget.setMinimumContentsLength(8)
    return widget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.connection_name = ""
        self.database_path = None
        self.table_names = []
        self.last_custom_sql = ""
        self.setWindowTitle("Киноархив · Лабораторная работа 3")
        self.resize(1180, 800)
        self.setMinimumSize(1040, 700)
        self.setWindowIcon(QIcon(str(BASE_DIR / "assets" / "icon.svg")))
        QDir.setSearchPaths("icons", [str(BASE_DIR / "assets")])
        self.setStyleSheet((BASE_DIR / "style.qss").read_text(encoding="utf-8"))
        self.build_menu()
        central = QWidget()
        central.setObjectName("window")
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(26, 20, 26, 24)
        layout.setSpacing(22)

        hero = QHBoxLayout()
        hero.setSpacing(14)
        hero.addWidget(label("Киноархив", "title"))
        hero.addStretch()
        self.connection_label = label("База не открыта", "connectionLabel")
        hero.addWidget(self.connection_label)
        hero.addSpacing(12)
        self.demo_button = button("Демо", "secondaryButton")
        self.demo_button.setToolTip("Открыть учебную базу cinema.db")
        self.demo_button.clicked.connect(lambda: self.load_database(BASE_DIR / "data" / "cinema.db"))
        self.open_button = button("Открыть БД", "primaryButton")
        self.open_button.setToolTip("Выбрать SQLite-файл · Ctrl+O")
        self.open_button.clicked.connect(self.choose_database)
        hero.addWidget(self.demo_button)
        hero.addWidget(self.open_button)
        layout.addLayout(hero)

        content = QHBoxLayout()
        content.setSpacing(20)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(224)
        controls = QVBoxLayout(sidebar)
        controls.setContentsMargins(18, 20, 18, 18)
        controls.setSpacing(10)
        self.bt1 = button("Имена объектов", "queryButton")
        self.bt1.setAccessibleName("bt1 — SELECT name FROM sqlite_master")
        self.bt1.setToolTip("SELECT name FROM sqlite_master · F1")
        self.bt1.setShortcut(QKeySequence("F1"))
        self.bt1.clicked.connect(lambda: self.run_preset(1, "SELECT name FROM sqlite_master"))
        controls.addWidget(self.bt1)
        controls.addSpacing(4)
        controls.addWidget(label("Колонка", "controlLabel"))
        self.columns_combo = combo("Колонка sqlite_master для Tab3")
        self.columns_combo.currentIndexChanged.connect(self.on_column_changed)
        controls.addWidget(self.columns_combo)
        rule = QFrame()
        rule.setObjectName("sidebarRule")
        rule.setFixedHeight(1)
        controls.addWidget(rule)

        controls.addWidget(label("Таблица 1", "controlLabel"))
        self.table4_combo = combo("Таблица для Tab4")
        controls.addWidget(self.table4_combo)
        self.bt2 = button("Показать", "queryButton")
        self.bt2.setToolTip("bt2 · Показать первую таблицу · F2")
        self.bt2.setShortcut(QKeySequence("F2"))
        self.bt2.clicked.connect(lambda: self.show_table(3, self.table4_combo))
        controls.addWidget(self.bt2)
        controls.addSpacing(4)
        controls.addWidget(label("Таблица 2", "controlLabel"))
        self.table5_combo = combo("Таблица для Tab5")
        controls.addWidget(self.table5_combo)
        self.bt3 = button("Показать", "queryButton")
        self.bt3.setToolTip("bt3 · Показать вторую таблицу · F3")
        self.bt3.setShortcut(QKeySequence("F3"))
        self.bt3.clicked.connect(lambda: self.show_table(4, self.table5_combo))
        controls.addWidget(self.bt3)
        controls.addStretch()
        self.sql_button = button("SQL-запрос", "bonusButton")
        self.sql_button.clicked.connect(self.show_query_dialog)
        controls.addWidget(self.sql_button)
        content.addWidget(sidebar)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.tabBar().setDrawBase(False)
        self.tabs.setMovable(False)
        self.pages = []
        for index, tab_title in enumerate(TAB_TITLES):
            page = ResultPage(tab_title)
            self.pages.append(page)
            self.tabs.addTab(page, tab_title)
            self.tabs.setTabToolTip(index, f"Tab{index + 1}")
        content.addWidget(self.tabs, 1)
        layout.addLayout(content, 1)
        self.reset_controls()

    def build_menu(self):
        menu = self.menuBar().addMenu("База данных")
        self.set_connection_action = QAction("Set connection", self)
        self.set_connection_action.setShortcut(QKeySequence("Ctrl+O"))
        self.set_connection_action.triggered.connect(self.choose_database)
        self.close_connection_action = QAction("Close connection", self)
        self.close_connection_action.setShortcut(QKeySequence("Ctrl+W"))
        self.close_connection_action.triggered.connect(self.close_connection)
        menu.addAction(self.set_connection_action)
        menu.addAction(self.close_connection_action)

    def reset_controls(self):
        with QSignalBlocker(self.columns_combo):
            self.columns_combo.clear()
            self.columns_combo.addItem("Выбрать…", None)
        for select in (self.table4_combo, self.table5_combo):
            select.clear()
            select.addItem("Нет таблиц", None)
        for widget in (self.bt1, self.bt2, self.bt3, self.columns_combo, self.table4_combo, self.table5_combo, self.sql_button):
            widget.setEnabled(False)
        self.close_connection_action.setEnabled(False)

    def choose_database(self):
        directory = str(self.database_path.parent if self.database_path else BASE_DIR / "data")
        filename, _ = QFileDialog.getOpenFileName(
            self, "Set connection — выбери SQLite-базу", directory,
            "Базы SQLite (*.db *.sqlite *.sqlite3);;Все файлы (*)"
        )
        if filename:
            self.load_database(filename)

    def load_database(self, filename):
        # Сначала проверяем новый файл. При ошибке старая база остаётся открытой
        try:
            new_connection = open_database(filename)
            try:
                names = user_tables(new_connection)
            except DatabaseError:
                close_database(new_connection)
                raise
        except DatabaseError as error:
            QMessageBox.warning(self, "Ошибка подключения", str(error))
            return False
        self.close_connection()
        self.connection_name = new_connection
        self.database_path = Path(filename).resolve()
        self.table_names = names
        for page in self.pages:
            page.clear(connected=True)
        with QSignalBlocker(self.columns_combo):
            for column in MASTER_COLUMNS:
                self.columns_combo.addItem(column, column)
        self.columns_combo.setEnabled(True)
        self.bt1.setEnabled(True)
        self.sql_button.setEnabled(True)
        self.close_connection_action.setEnabled(True)
        for select, btn, preferred, fallback in (
            (self.table4_combo, self.bt2, "films", 0),
            (self.table5_combo, self.bt3, "directors", 1),
        ):
            select.clear()
            if names:
                for name in names:
                    select.addItem(name, name)
                    select.setItemData(select.count() - 1, name, Qt.ToolTipRole)
                select.setCurrentIndex(names.index(preferred) if preferred in names else min(fallback, len(names) - 1))
            else:
                select.addItem("Нет таблиц", None)
            select.setEnabled(bool(names))
            btn.setEnabled(bool(names))
        short_name = self.fontMetrics().elidedText(self.database_path.name, Qt.ElideMiddle, 240)
        self.connection_label.setText(f"●  {short_name}")
        self.connection_label.setStyleSheet("color: #ff8a3d;")
        self.connection_label.setToolTip(str(self.database_path))
        self.run_preset(0, "SELECT * FROM sqlite_master")
        return True

    def execute_query(self, tab_index, sql):
        model = make_query_model(sql, self.connection_name, self.pages[tab_index])
        self.pages[tab_index].set_result(model, sql)
        self.tabs.setCurrentIndex(tab_index)

    def run_preset(self, tab_index, sql):
        try:
            self.execute_query(tab_index, sql)
        except DatabaseError as error:
            QMessageBox.warning(self, "Ошибка SQL-запроса", str(error))

    def on_column_changed(self, index):
        column = self.columns_combo.itemData(index)
        if column in MASTER_COLUMNS and self.connection_name:
            self.run_preset(2, f"SELECT {quote_identifier(column)} FROM sqlite_master")

    def show_table(self, tab_index, select):
        name = select.currentData()
        if name in self.table_names:
            self.run_preset(tab_index, f"SELECT * FROM {quote_identifier(name)}")

    def example_sql(self):
        if {"films", "directors"}.issubset(self.table_names):
            return JOIN_EXAMPLE
        if self.table_names:
            return f"SELECT * FROM {quote_identifier(self.table_names[0])} LIMIT 20;"
        return "SELECT name, type FROM sqlite_master;"

    def show_query_dialog(self):
        if not self.connection_name:
            return
        dialog = QueryDialog(self.execute_query, self.example_sql(), self.last_custom_sql, self)
        if dialog.exec_() == QueryDialog.Accepted:
            self.last_custom_sql = dialog.executed_sql
        dialog.deleteLater()

    def close_connection(self):
        # Порядок важен (результаты → модели → соединение → элементы интерфейса)
        for page in self.pages:
            page.clear()
        close_database(self.connection_name)
        self.connection_name = ""
        self.database_path = None
        self.table_names = []
        self.last_custom_sql = ""
        self.reset_controls()
        self.tabs.setCurrentIndex(0)
        self.connection_label.setText("База не открыта")
        self.connection_label.setStyleSheet("color: #909090;")
        self.connection_label.setToolTip("")

    def closeEvent(self, event):
        self.close_connection()
        event.accept()


if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    window = MainWindow()
    app.setWindowIcon(window.windowIcon())
    window.show()
    sys.exit(app.exec_())

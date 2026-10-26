"""Проверка требований ЛР3 на настоящей SQLite и Qt, без внешних пакетов тестирования."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PyQt5.QtCore import QEvent, QTimer, Qt, qInstallMessageHandler
from PyQt5.QtSql import QSqlDatabase, QSqlQuery
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication, QDialog, QFileDialog, QMessageBox
from database import DatabaseError, validate_custom_query
from main import BASE_DIR, JOIN_EXAMPLE, MASTER_COLUMNS, MainWindow
from query_dialog import QueryDialog

DEMO = BASE_DIR / "data" / "cinema.db"


def rows(model):
    while model.canFetchMore():
        model.fetchMore()
    return [tuple(model.record(row).value(col) for col in range(model.columnCount())) for row in range(model.rowCount())]


def reference(sql, path=DEMO):
    with sqlite3.connect(path) as db:
        return db.execute(sql).fetchall()


class Lab3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyle("Fusion")
        cls.messages = []
        cls.old_handler = qInstallMessageHandler(lambda kind, context, message: cls.messages.append(message))

    @classmethod
    def tearDownClass(cls):
        qInstallMessageHandler(cls.old_handler)
        leaked = [m for m in cls.messages if "still in use" in m or "duplicate connection" in m]
        if leaked:
            raise AssertionError("Qt SQL lifetime warnings: " + str(leaked))

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.w = MainWindow()
        self.w.show()
        self.app.processEvents()

    def tearDown(self):
        self.w.close()
        self.w.deleteLater()
        self.app.sendPostedEvents(None, QEvent.DeferredDelete)
        self.app.processEvents()
        self.assertFalse([n for n in QSqlDatabase.connectionNames() if n.startswith("cinema_")])
        self.tmp.cleanup()

    def open_demo(self):
        self.assertTrue(self.w.load_database(DEMO))

    def test_initial_empty_tabs_and_disabled_actions(self):
        self.assertEqual(self.w.tabs.count(), 5)
        self.assertTrue(all(page.model is None for page in self.w.pages))
        self.assertFalse(self.w.close_connection_action.isEnabled())
        self.assertTrue(all(not b.isEnabled() for b in (self.w.bt1, self.w.bt2, self.w.bt3, self.w.sql_button)))

    def test_set_connection_uses_file_dialog_and_populates_tab1(self):
        with patch.object(QFileDialog, 'getOpenFileName', return_value=(str(DEMO), 'SQLite')) as choose:
            self.w.set_connection_action.trigger()
            choose.assert_called_once()
        self.assertEqual(self.w.pages[0].last_sql, 'SELECT * FROM sqlite_master')
        self.assertEqual(rows(self.w.pages[0].model), reference('SELECT * FROM sqlite_master'))
        self.assertEqual(self.w.tabs.currentIndex(), 0)
        self.assertTrue(all(p.model is None for p in self.w.pages[1:]))

    def test_bt1_and_all_combo_columns(self):
        self.open_demo()
        self.w.bt1.click()
        self.assertEqual(self.w.tabs.currentIndex(), 1)
        self.assertEqual(rows(self.w.pages[1].model), reference('SELECT name FROM sqlite_master'))
        for column in MASTER_COLUMNS:
            self.w.columns_combo.setCurrentIndex(self.w.columns_combo.findData(column))
            self.assertEqual(self.w.tabs.currentIndex(), 2)
            self.assertEqual(rows(self.w.pages[2].model), reference(f'SELECT "{column}" FROM sqlite_master'))

    def test_bt2_and_bt3_table_results(self):
        self.open_demo()
        self.w.bt2.click()
        self.assertEqual(self.w.tabs.currentIndex(), 3)
        self.assertEqual(rows(self.w.pages[3].model), reference('SELECT * FROM films'))
        self.w.bt3.click()
        self.assertEqual(self.w.tabs.currentIndex(), 4)
        self.assertEqual(rows(self.w.pages[4].model), reference('SELECT * FROM directors'))

    def test_modal_dialog_executes_join(self):
        self.open_demo()
        def execute_in_modal():
            dialog = self.app.activeModalWidget()
            self.assertIsInstance(dialog, QueryDialog)
            self.assertTrue(dialog.isModal())
            dialog.target.setCurrentIndex(2)
            dialog.editor.setPlainText(JOIN_EXAMPLE)
            dialog.run_button.click()
        QTimer.singleShot(0, execute_in_modal)
        self.w.show_query_dialog()
        self.assertEqual(self.w.last_custom_sql, JOIN_EXAMPLE)
        self.assertEqual(self.w.tabs.currentIndex(), 3)
        self.assertEqual(rows(self.w.pages[3].model), reference(JOIN_EXAMPLE))

    def test_sql_error_keeps_previous_result_and_dialog_open(self):
        self.open_demo()
        self.w.bt2.click()
        previous_model = self.w.pages[3].model
        dialog = QueryDialog(self.w.execute_query, JOIN_EXAMPLE, parent=self.w)
        dialog.show()
        dialog.editor.setPlainText('SELECT missing_column FROM films')
        dialog.run_button.click()
        self.assertFalse(dialog.error_label.isHidden())
        self.assertTrue(dialog.isVisible())
        self.assertIs(self.w.pages[3].model, previous_model)
        dialog.editor.clear()
        dialog.execute()
        self.assertIn('Введи', dialog.error_label.text())
        dialog.reject()
        self.assertEqual(dialog.result(), QDialog.Rejected)
        dialog.deleteLater()

    def test_close_clears_all_then_reconnects(self):
        self.open_demo()
        self.w.bt1.click()
        self.w.columns_combo.setCurrentIndex(1)
        self.w.bt2.click()
        self.w.bt3.click()
        self.w.last_custom_sql = JOIN_EXAMPLE
        old_name = self.w.connection_name
        self.w.close_connection_action.trigger()
        self.assertFalse(QSqlDatabase.contains(old_name))
        self.assertEqual(self.w.last_custom_sql, '')
        for page in self.w.pages:
            self.assertIsNone(page.model)
            self.assertIsNone(page.table.model())
            self.assertEqual(page.sql_view.toPlainText(), '')
        self.assertEqual(self.w.columns_combo.count(), 1)
        self.assertEqual(self.w.table4_combo.count(), 1)
        self.assertFalse(self.w.close_connection_action.isEnabled())
        self.open_demo()
        self.assertNotEqual(old_name, self.w.connection_name)
        self.assertTrue(all(p.model is None for p in self.w.pages[1:]))

    def test_bad_file_missing_file_and_cancel_preserve_connection(self):
        self.open_demo()
        original_name = self.w.connection_name
        bad = Path(self.tmp.name) / 'invalid.db'
        bad.write_text('This is not a SQLite database')
        with patch.object(QMessageBox, 'warning') as warning:
            self.assertFalse(self.w.load_database(bad))
            self.assertFalse(self.w.load_database(bad.with_name('missing.db')))
            self.assertEqual(warning.call_count, 2)
        self.assertEqual(self.w.connection_name, original_name)
        self.assertEqual(len(QSqlDatabase.connectionNames()), 1)
        with patch.object(QFileDialog, 'getOpenFileName', return_value=('', '')):
            self.w.choose_database()
        self.assertEqual(self.w.connection_name, original_name)

    def test_empty_database_and_empty_query_result(self):
        path = Path(self.tmp.name) / 'empty.sqlite'
        with sqlite3.connect(path) as db:
            db.execute('PRAGMA user_version = 1')
        self.assertTrue(self.w.load_database(path))
        self.assertEqual(self.w.pages[0].model.rowCount(), 0)
        self.assertFalse(self.w.bt2.isEnabled())
        self.assertFalse(self.w.bt3.isEnabled())
        self.w.execute_query(1, 'SELECT 42 AS answer WHERE 0')
        self.assertEqual(self.w.pages[1].model.rowCount(), 0)
        self.assertEqual(self.w.pages[1].model.columnCount(), 1)
        self.assertIn('совпадений нет', self.w.pages[1].summary.text())

    def test_arbitrary_database_and_quoted_table_name(self):
        path = Path(self.tmp.name) / 'база со пробелами.sqlite'
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE "odd "" table" ("поле" TEXT)')
            db.execute('INSERT INTO "odd "" table" VALUES (?)', ('Привет',))
        self.assertTrue(self.w.load_database(path))
        self.w.bt2.click()
        self.w.bt3.click()
        self.assertEqual(rows(self.w.pages[3].model), [('Привет',)])
        self.assertEqual(rows(self.w.pages[4].model), [('Привет',)])

    def test_large_result_fetches_more_and_updates_count(self):
        path = Path(self.tmp.name) / 'large.db'
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE numbers (n INTEGER)')
            db.executemany('INSERT INTO numbers VALUES (?)', [(i,) for i in range(1500)])
        self.w.load_database(path)
        self.w.bt2.click()
        model = self.w.pages[3].model
        self.assertTrue(model.canFetchMore())
        self.assertIn('+', self.w.pages[3].summary.text())
        self.assertEqual(rows(model), [(i,) for i in range(1500)])
        self.assertIn('1500', self.w.pages[3].summary.text())
        self.assertNotIn('+', self.w.pages[3].summary.text())

    def test_read_only_sql_comments_cte_and_multiple_statements(self):
        self.open_demo()
        query = QSqlQuery(QSqlDatabase.database(self.w.connection_name, open=False))
        self.assertFalse(query.exec_('DELETE FROM films'))
        query.finish()
        del query
        with self.assertRaises(DatabaseError):
            validate_custom_query('DELETE FROM films')
        sql = validate_custom_query('-- comment\n/* query */ WITH x AS (SELECT 42 AS n) SELECT n FROM x')
        self.w.execute_query(1, sql)
        self.assertEqual(rows(self.w.pages[1].model), [(42,)])
        with self.assertRaises(DatabaseError):
            self.w.execute_query(1, 'SELECT 1; SELECT 2;')
        self.assertEqual(reference('SELECT COUNT(*) FROM films'), [(12,)])

    def test_function_keys(self):
        self.open_demo()
        self.w.activateWindow()
        self.w.setFocus()
        self.app.processEvents()
        for key, tab in ((Qt.Key_F1, 1), (Qt.Key_F2, 3), (Qt.Key_F3, 4)):
            QTest.keyClick(self.w, key)
            QTest.qWait(180)  # Клавиатурное нажатие QPushButton использует animateClick().
            self.app.processEvents()
            self.assertEqual(self.w.tabs.currentIndex(), tab)


if __name__ == '__main__':
    unittest.main()

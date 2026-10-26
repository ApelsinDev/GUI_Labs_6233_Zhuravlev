import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PyQt5.QtCore import QEvent, QMetaObject, QPoint, QPointF, Qt, QVariant, Q_ARG, qInstallMessageHandler
from PyQt5.QtGui import QImage
from PyQt5.QtQuick import QQuickItem, QQuickWindow
from PyQt5.QtTest import QSignalSpy, QTest
from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox
from main import Interface, create_engine


def call(item, name, *args):
    return QMetaObject.invokeMethod(item, name, Qt.DirectConnection,
                                   *(Q_ARG(QVariant, a) for a in args))


class PainterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.messages = []
        cls.old_handler = qInstallMessageHandler(lambda kind, context, text: cls.messages.append(text))

    @classmethod
    def tearDownClass(cls):
        qInstallMessageHandler(cls.old_handler)
        errors = [s for s in cls.messages if any(x in s for x in (
            "TypeError", "ReferenceError", "Binding loop", "QQmlApplicationEngine failed", "Unable to assign"
        ))]
        if errors:
            raise AssertionError("Ошибки QML: " + str(errors))

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.directory = Path(self.tmp.name) / "Рисунки с пробелами"
        self.b = Interface(self.directory)
        self.engine = create_engine(self.b)
        self.w = self.engine.rootObjects()[0]
        self.c = self.b.canvas
        self.spy = QSignalSpy(self.b.saveSucceeded)
        QTest.qWait(70)
        self.assertTrue(self.c.property("available"))

    def tearDown(self):
        self.b.timer.stop()
        self.engine.deleteLater()
        self.app.sendPostedEvents(None, QEvent.DeferredDelete)
        self.app.processEvents()
        self.b.canvas = None
        self.b.deleteLater()
        self.app.sendPostedEvents(None, QEvent.DeferredDelete)
        self.tmp.cleanup()

    def draw(self, y=100):
        call(self.c, "beginStroke", 100, y)
        call(self.c, "continueStroke", 300, y)
        call(self.c, "endStroke")

    def image(self):
        im = QImage(self.b.lastFile)
        self.assertFalse(im.isNull())
        return im

    def test_initial_state_and_python_timer(self):
        self.assertEqual(self.b.intervalSeconds, 10)
        self.assertEqual(self.b.timer.interval(), 10000)
        self.assertTrue(self.b.timer.isActive())
        self.assertIs(self.b.timer.parent(), self.b)
        self.assertFalse(self.b.dirty)
        self.assertFalse(self.directory.exists())

    def test_real_timer_saves_canvas_only_and_updates_same_file(self):
        self.b.setIntervalSeconds(1)
        self.draw()
        self.assertTrue(self.spy.wait(1800))
        im = self.image()
        self.assertEqual((im.width(), im.height()), (int(self.c.width()), int(self.c.height())))
        self.assertEqual(im.pixelColor(150, 100).name(), "#ff791e")
        self.assertEqual(im.pixelColor(5, 5).name(), "#ffffff")
        self.assertEqual(im.pixelColor(5, 5).alpha(), 255)
        first = Path(self.b.lastFile)
        previous = first.read_bytes()
        self.draw(200)
        self.assertTrue(self.spy.wait(1800))
        self.assertEqual(Path(self.b.lastFile), first)
        self.assertNotEqual(previous, first.read_bytes())
        self.assertEqual(self.image().pixelColor(150, 200).name(), "#ff791e")
        self.assertEqual(list(self.directory.iterdir()), [first])

    def test_pause_resume_and_no_rewrite_without_changes(self):
        self.b.setIntervalSeconds(1)
        self.b.setAutoSaveEnabled(False)
        self.draw()
        QTest.qWait(1150)
        self.assertEqual(len(self.spy), 0)
        self.b.setAutoSaveEnabled(True)
        self.assertTrue(self.spy.wait(1800))
        before = Path(self.b.lastFile).stat().st_mtime_ns
        QTest.qWait(1150)
        self.assertEqual(len(self.spy), 1)
        self.assertEqual(Path(self.b.lastFile).stat().st_mtime_ns, before)

    def test_interval_bounds_and_qml_control_binding(self):
        self.b.setIntervalSeconds(0)
        self.assertEqual(self.b.intervalSeconds, 1)
        self.b.setIntervalSeconds(999)
        self.assertEqual(self.b.intervalSeconds, 300)
        spin = self.w.findChild(QQuickItem, "interval")
        self.assertEqual(spin.property("value"), 300)
        self.b.setIntervalSeconds(3)
        self.assertEqual(self.b.timer.interval(), 3000)
        self.assertEqual(spin.property("value"), 3)

    def test_mouse_input_single_click_and_keyboard_undo(self):
        self.w.requestActivate()
        QTest.qWait(50)
        origin = self.c.mapToScene(QPointF(0, 0))
        p = QPoint(int(origin.x() + 120), int(origin.y() + 110))
        QTest.mouseClick(self.w, Qt.LeftButton, Qt.NoModifier, p)
        self.assertTrue(self.b.dirty)
        self.b.save_canvas()
        self.assertEqual(self.image().pixelColor(120, 110).name(), "#ff791e")
        QTest.keyClick(self.w, Qt.Key_Z, Qt.ControlModifier)
        QTest.qWait(50)
        self.assertTrue(self.b.dirty)
        self.b.save_canvas()
        self.assertEqual(self.image().pixelColor(120, 110).name(), "#ffffff")

    def test_resize_keeps_strokes_and_marks_changed(self):
        self.draw()
        self.b.save_canvas()
        old_w, old_h = self.c.width(), self.c.height()
        self.w.resize(1080, 700)
        QTest.qWait(100)
        self.assertTrue(self.b.dirty)
        self.b.save_canvas()
        im = self.image()
        x, y = round(150 / old_w * self.c.width()), round(100 / old_h * self.c.height())
        self.assertEqual(im.pixelColor(x, y).name(), "#ff791e")

    def test_color_brush_mouse_drag_and_save_while_hidden(self):
        def click_item(name):
            # Делегаты Repeater находятся в дереве визуальных childItems.
            pending = [self.w.contentItem()]
            item = None
            while pending:
                candidate = pending.pop()
                if candidate.objectName() == name:
                    item = candidate
                    break
                pending.extend(candidate.childItems())
            self.assertIsNotNone(item)
            position = item.mapToScene(QPointF(item.width() / 2, item.height() / 2))
            QTest.mouseClick(self.w, Qt.LeftButton, Qt.NoModifier, position.toPoint())
        click_item("color_2")
        click_item("brush_12")
        origin = self.c.mapToScene(QPointF(0, 0))
        start = (origin + QPointF(100, 100)).toPoint()
        end = (origin + QPointF(300, 100)).toPoint()
        QTest.mousePress(self.w, Qt.LeftButton, Qt.NoModifier, start)
        QTest.mouseMove(self.w, end, 10)
        QTest.mouseRelease(self.w, Qt.LeftButton, Qt.NoModifier, end)
        self.w.hide()
        self.b.save_canvas()
        im = self.image()
        self.assertEqual(im.pixelColor(150, 100).name(), "#33b5e5")
        self.assertEqual(im.pixelColor(150, 104).name(), "#33b5e5")

    def test_clear_saves_white_canvas(self):
        self.draw()
        self.b.save_canvas()
        call(self.c, "clearDrawing")
        self.assertTrue(self.b.dirty)
        self.b.save_canvas()
        im = self.image()
        self.assertEqual(im.pixelColor(150, 100).name(), "#ffffff")

    def test_folder_choice_and_cancel(self):
        with patch.object(QFileDialog, "getExistingDirectory", return_value=""):
            self.b.chooseFolder()
        self.assertEqual(Path(self.b.folder), self.directory)
        other = Path(self.tmp.name) / "Другая папка"
        with patch.object(QFileDialog, "getExistingDirectory", return_value=str(other)):
            self.b.chooseFolder()
        self.draw()
        self.b.save_canvas()
        self.assertTrue((other / "autosave.png").is_file())

    def test_manual_save_and_cancel(self):
        self.draw()
        with patch.object(QFileDialog, "getSaveFileName", return_value=("", "")):
            self.assertFalse(self.b.saveNow())
        self.assertTrue(self.b.dirty)
        target = Path(self.tmp.name) / "ручная копия"
        with patch.object(QFileDialog, "getSaveFileName", return_value=(str(target), "PNG")):
            self.assertTrue(self.b.saveNow())
        self.assertTrue(target.with_suffix(".png").is_file())
        self.assertFalse(self.b.dirty)
        self.assertEqual(self.image().pixelColor(150, 100).name(), "#ff791e")
        self.b.setIntervalSeconds(1)
        self.assertTrue(self.spy.wait(1800))
        self.assertEqual(Path(self.b.lastFile), self.directory / "autosave.png")
        self.assertEqual(self.image().pixelColor(150, 100).name(), "#ff791e")

    def test_write_failure_preserves_old_file_and_retries(self):
        self.draw()
        self.b.save_canvas()
        target = Path(self.b.lastFile)
        old = target.read_bytes()
        self.draw(200)
        with patch("main.os.replace", side_effect=PermissionError("Нет доступа")):
            self.b.save_canvas()
        self.assertTrue(self.b.hasError)
        self.assertTrue(self.b.dirty)
        self.assertEqual(target.read_bytes(), old)
        self.assertEqual(list(self.directory.iterdir()), [target])
        self.b.save_canvas()
        self.assertFalse(self.b.hasError)
        self.assertFalse(self.b.dirty)
        self.assertTrue(target.read_bytes() != old, "PNG должен содержать новый штрих")
        self.assertEqual(self.image().pixelColor(150, 200).name(), "#ff791e")

    def test_invalid_folder_shows_error_without_crash(self):
        obstacle = Path(self.tmp.name) / "file_instead_of_folder"
        obstacle.write_text("occupied")
        self.b.set_folder(obstacle)
        self.draw()
        self.b.save_canvas()
        self.assertTrue(self.b.hasError)
        self.assertTrue(self.b.dirty)
        self.assertFalse(self.b.lastFile)

    def test_close_save_discard_cancel_and_failed_save(self):
        self.assertTrue(self.b.confirmClose())
        self.draw()
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Cancel):
            self.assertFalse(self.b.confirmClose())
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Discard):
            self.assertTrue(self.b.confirmClose())
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Save):
            with patch("main.os.replace", side_effect=PermissionError("Нет доступа")):
                self.assertFalse(self.b.confirmClose())
            self.assertTrue(self.b.confirmClose())
        self.assertTrue(Path(self.b.lastFile).is_file())
        self.assertFalse(self.b.dirty)


if __name__ == "__main__":
    unittest.main()

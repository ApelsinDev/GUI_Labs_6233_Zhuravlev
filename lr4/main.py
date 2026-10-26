import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import (
    QObject, QMetaObject, QTimer, QUrl, Qt, QVariant,
    Q_ARG, Q_RETURN_ARG, pyqtProperty, pyqtSignal, pyqtSlot,
)
from PyQt5.QtGui import QIcon
from PyQt5.QtQml import QQmlApplicationEngine
from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox

BASE_DIR = Path(__file__).resolve().parent


class Interface(QObject):
    """Дополненный класс Interface из выданного каркаса"""
    stateChanged = pyqtSignal()
    saveSucceeded = pyqtSignal(str)

    def __init__(self, save_dir=None):
        super().__init__()
        self.canvas = None
        self._folder = Path(save_dir or BASE_DIR / "saves").resolve()
        self._interval = 10
        self._enabled = True
        self._dirty = False
        self._autosave_pending = False
        self._status = "Пока нет сохранений"
        self._error = False
        self._last_file = ""
        # Таймер находится именно в Python-классе Interface
        self.timer = QTimer(self)
        self.timer.setInterval(self._interval * 1000)
        self.timer.timeout.connect(self.save_canvas)

    @pyqtProperty(int, notify=stateChanged)
    def intervalSeconds(self):
        return self._interval

    @pyqtProperty(bool, notify=stateChanged)
    def autoSaveEnabled(self):
        return self._enabled

    @pyqtProperty(bool, notify=stateChanged)
    def dirty(self):
        return self._dirty

    @pyqtProperty(str, notify=stateChanged)
    def folder(self):
        return str(self._folder)

    @pyqtProperty(str, notify=stateChanged)
    def folderName(self):
        return self._folder.name or str(self._folder)

    @pyqtProperty(str, notify=stateChanged)
    def status(self):
        return self._status

    @pyqtProperty(bool, notify=stateChanged)
    def hasError(self):
        return self._error

    @pyqtProperty(str, notify=stateChanged)
    def lastFile(self):
        return self._last_file

    def attach_canvas(self, canvas):
        self.canvas = canvas
        if self._enabled:
            self.timer.start()

    @pyqtSlot()
    def markDirty(self):
        self._autosave_pending = True
        if not self._dirty:
            self._dirty = True
            self.stateChanged.emit()

    @pyqtSlot(bool)
    def setAutoSaveEnabled(self, enabled):
        self._enabled = enabled
        if enabled and self.canvas is not None:
            self.timer.start()
        else:
            self.timer.stop()
        self.stateChanged.emit()

    @pyqtSlot(int)
    def setIntervalSeconds(self, seconds):
        self._interval = max(1, min(300, seconds))
        self.timer.setInterval(self._interval * 1000)
        self.stateChanged.emit()

    def set_folder(self, folder):
        self._folder = Path(folder).resolve()
        # В новой папке текущий рисунок тоже должен получить автокопию
        self._dirty = True
        self._autosave_pending = True
        self.stateChanged.emit()

    @pyqtSlot()
    def chooseFolder(self):
        folder = QFileDialog.getExistingDirectory(
            None, "Папка для автосохранения", str(self._folder)
        )
        if folder:
            self.set_folder(folder)

    def _save(self, target, automatic=False):
        """Записывает только Canvas; сначала временный PNG, затем заменяет файл."""
        temporary = None
        try:
            if self.canvas is None or not self.canvas.property("available"):
                raise OSError("Холст ещё не готов к сохранению.")
            target = Path(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            # Временный файл расположен рядом с итоговым: os.replace атомарен
            with tempfile.NamedTemporaryFile(
                prefix=".painter-", suffix=".png", dir=str(target.parent), delete=False
            ) as handle:
                temporary = Path(handle.name)
            saved = QMetaObject.invokeMethod(
                self.canvas, "saveToFile", Qt.DirectConnection,
                Q_RETURN_ARG(QVariant), Q_ARG(QVariant, str(temporary))
            )
            if not saved or not temporary.is_file() or temporary.stat().st_size == 0:
                raise OSError("Canvas не смог записать PNG. Проверь права доступа и свободное место.")
            os.replace(str(temporary), str(target))
        except (OSError, RuntimeError) as error:
            self._error = True
            self._status = "Ошибка сохранения: " + str(error)
            self.stateChanged.emit()
            return False
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
        self._dirty = False
        self._error = False
        self._last_file = str(target.resolve())
        if target.resolve() == (self._folder / "autosave.png").resolve():
            self._autosave_pending = False
        verb = "Автосохранено" if automatic else "Сохранено"
        self._status = f"{verb} · {datetime.now():%H:%M:%S}"
        self.stateChanged.emit()
        self.saveSucceeded.emit(self._last_file)
        return True

    @pyqtSlot()
    def save_canvas(self):
        # Ручная копия не отменяет обновление autosave.png по таймеру
        # Без новых изменений запись не нужна; при ошибке попытка повторится
        if self._enabled and self._autosave_pending:
            self._save(self._folder / "autosave.png", automatic=True)

    @pyqtSlot(result=bool)
    def saveNow(self):
        default = self._folder / datetime.now().strftime("drawing_%Y%m%d_%H%M%S.png")
        filename, _ = QFileDialog.getSaveFileName(
            None, "Сохранить рисунок", str(default), "Изображение PNG (*.png)"
        )
        if not filename:
            return False
        target = Path(filename)
        if target.suffix.lower() != ".png":
            target = Path(str(target) + ".png")
            if target.exists() and QMessageBox.question(
                None, "Замена файла", f"Заменить {target.name}?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            ) != QMessageBox.Yes:
                return False
        return self._save(target)

    @pyqtSlot(result=bool)
    def confirmClose(self):
        if not self._dirty:
            return True
        answer = QMessageBox.question(
            None, "Сохранить рисунок?",
            "Есть несохранённые изменения. Сохранить их в autosave.png перед выходом?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save,
        )
        if answer == QMessageBox.Save:
            return self._save(self._folder / "autosave.png")
        return answer == QMessageBox.Discard


def create_engine(interface):
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("_backend", interface)
    engine.load(QUrl.fromLocalFile(str(BASE_DIR / "mainWindow.qml")))
    if not engine.rootObjects():
        raise RuntimeError("Не удалось загрузить mainWindow.qml.")
    canvas = engine.rootObjects()[0].findChild(QObject, "canvas")
    if canvas is None:
        raise RuntimeError("Область рисования Canvas не найдена.")
    interface.attach_canvas(canvas)
    return engine


if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(BASE_DIR / "assets/icon.svg")))
    interface = Interface()
    try:
        engine = create_engine(interface)
    except RuntimeError as error:
        print(error, file=sys.stderr)
        sys.exit(1)
    app.aboutToQuit.connect(interface.timer.stop)
    exit_code = app.exec_()
    interface.timer.stop()
    del engine  # QML уничтожается раньше объекта _backend
    sys.exit(exit_code)

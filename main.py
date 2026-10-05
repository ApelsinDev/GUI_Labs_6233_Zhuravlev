import sys
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QApplication, QLabel, QMessageBox, QPushButton,
    QStyle, QVBoxLayout, QWidget,
)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("window")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setWindowTitle("Лабораторная работа № 1")
        self.setFixedSize(420, 340)
        self.setWindowIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))

        self.initial_text = "Нажми кнопку, чтобы увидеть изображение"
        self.image_visible = False

        self.label = QLabel(self.initial_text)
        self.label.setObjectName("content")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setWordWrap(True)
        self.label.setFixedSize(360, 240)

        self.button = QPushButton("Показать изображение")
        self.button.setCursor(Qt.PointingHandCursor)
        self.button.setFixedHeight(44)
        self.button.clicked.connect(self.toggle_content)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)
        layout.addWidget(self.label, alignment=Qt.AlignCenter)
        layout.addWidget(self.button)

        # Всё оформление находится здесь, в одном файле.
        self.setStyleSheet("""
            QWidget#window {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #ffc4d4, stop:0.2 #ffdfb8,
                    stop:0.4 #fff1b4, stop:0.6 #bff0cd,
                    stop:0.8 #bde8ff, stop:1 #dacbff
                );
            }
            QLabel#content {
                background: rgba(255, 255, 255, 225);
                color: #39324b;
                border-radius: 22px;
                padding: 16px;
                font-size: 18px;
                font-weight: 600;
            }
            QPushButton {
                background: #7753c9;
                color: white;
                border: 2px solid transparent;
                border-radius: 14px;
                font-size: 15px;
                font-weight: 600;
            }
            QPushButton:hover { background: #8964da; }
            QPushButton:pressed { background: #6340b1; }
            QPushButton:focus { border-color: #bba4ee; }
        """)

    def toggle_content(self):
        if self.image_visible:
            self.label.setText(self.initial_text)
            self.button.setText("Показать изображение")
            self.image_visible = False
            return

        image_path = Path(__file__).resolve().parent / "image.png"
        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            QMessageBox.warning(
                self, "Ошибка",
                "Не удалось открыть image.png.\nПоложи картинку рядом с main.py.",
            )
            return

        self.label.setPixmap(
            pixmap.scaled(320, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        self.button.setText("Показать текст")
        self.image_visible = True


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

"""ЛР 2. Конвертер температуры на сигналах и слотах."""
import sys
from pathlib import Path
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget
from cl1 import NumberCard
from cl2 import Data
from visuals import TemperatureDial

BASE_DIR = Path(__file__).resolve().parent


def label(text, name):
    widget = QLabel(text)
    widget.setObjectName(name)
    return widget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Термостанция · ЛР 2")
        self.resize(1080, 780)
        self.setMinimumSize(1020, 740)
        self.setWindowIcon(QIcon(str(BASE_DIR / "assets" / "icon.svg")))
        self.setStyleSheet((BASE_DIR / "style.qss").read_text(encoding="utf-8"))
        central = QWidget()
        central.setObjectName("window")
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(32, 28, 32, 22)
        layout.setSpacing(24)

        top = QHBoxLayout()
        brand = label("◉  ТЕРМОСТАНЦИЯ", "brand")
        top.addWidget(brand)
        top.addStretch()
        top.addWidget(label("ЛР 02  /  СИГНАЛЫ И СЛОТЫ", "badge"))
        layout.addLayout(top)

        heading = QHBoxLayout()
        heading.addWidget(label("Градусы разные.\nТемпература одна!!!", "title"))
        heading.addStretch()
        description = label("Цельсий. Фаренгейт. Кельвин.\nИзмени любое число —\nостальные подстроятся.", "subtitle")
        heading.addWidget(description)
        layout.addLayout(heading)

        content = QHBoxLayout()
        content.setSpacing(22)
        sleeve = QFrame()
        sleeve.setObjectName("sleeve")
        sleeve_layout = QVBoxLayout(sleeve)
        sleeve_layout.setContentsMargins(24, 23, 24, 22)
        sleeve_layout.setSpacing(8)
        sleeve_top = QHBoxLayout()
        sleeve_top.addStretch()
        sleeve_layout.addLayout(sleeve_top)
        self.dial = TemperatureDial()
        sleeve_layout.addWidget(self.dial, 1)
        sleeve_bottom = QHBoxLayout()
        sleeve_bottom.addWidget(label("°C", "timeSignature"))
        sleeve_bottom.addStretch()
        sleeve_bottom.addWidget(label("ОДНА ТЕМПЕРАТУРА\nТРИ ШКАЛЫ", "sleeveCaption"))
        sleeve_layout.addLayout(sleeve_bottom)
        content.addWidget(sleeve, 4)

        fields = QVBoxLayout()
        fields.setSpacing(12)
        self.celsius_card = NumberCard("Цельсий", "°C", "Привычная шкала", -100, 100, 1, "lime", "01")
        self.fahrenheit_card = NumberCard("Фаренгейт", "°F", "Другая точка отсчёта", -148, 212, 1, "purple", "02")
        self.kelvin_card = NumberCard("Кельвин", "K", "Абсолютная шкала", 173.15, 373.15, 1, "peach", "03")
        for card in (self.celsius_card, self.fahrenheit_card, self.kelvin_card):
            fields.addWidget(card, 1)
        content.addLayout(fields, 5)
        layout.addLayout(content, 1)

        presets = QHBoxLayout()
        presets.setSpacing(10)
        presets.addWidget(label("ПОПРОБУЙ ТЕМПЕРАТУРУ", "presetLabel"))
        presets.addStretch()
        self.preset_buttons = {}
        for celsius, name in ((-20, "Мороз"), (22, "Комната"), (40, "Жара")):
            button = QPushButton(f"{name}  /  {celsius}°")
            button.setObjectName("presetButton")
            button.setCursor(Qt.PointingHandCursor)
            button.setCheckable(True)
            button.setToolTip(f"Установить {celsius} °C")
            button.clicked.connect(lambda checked=False, value=celsius: self.data.set_celsius(float(value)))
            presets.addWidget(button)
            self.preset_buttons[celsius] = button
        layout.addLayout(presets)

        rule = QFrame()
        rule.setObjectName("rule")
        rule.setFixedHeight(1)
        layout.addWidget(rule)
        footer = QHBoxLayout()
        footer.addWidget(label("°F = °C × 1,8 + 32    ·    K = °C + 273,15", "formula"))
        footer.addStretch()
        footer.addWidget(label("−100…+100 °C  /  Дробные числа через точку", "footer"))
        layout.addLayout(footer)

        self.data = Data(self)
        self.celsius_card.value_edited.connect(self.data.set_celsius)
        self.fahrenheit_card.value_edited.connect(self.data.set_fahrenheit)
        self.kelvin_card.value_edited.connect(self.data.set_kelvin)
        self.data.changed.connect(self.sync_fields)
        self.data.publish()

    @pyqtSlot(float, float, float)
    def sync_fields(self, celsius, fahrenheit, kelvin):
        self.celsius_card.set_value(celsius)
        self.fahrenheit_card.set_value(fahrenheit)
        self.kelvin_card.set_value(kelvin)
        self.dial.set_temperature(celsius)
        for value, button in self.preset_buttons.items():
            button.setChecked(abs(celsius - value) < 1e-9)


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

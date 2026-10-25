"""Поле ввода с собственным сигналом."""
from math import isclose
from PyQt5.QtCore import QLocale, QSignalBlocker, Qt, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QAbstractSpinBox, QDoubleSpinBox, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout


class NumberSpinBox(QDoubleSpinBox):
    def textFromValue(self, value):
        return f"{value:.3f}".rstrip("0").rstrip(".")


class NumberCard(QFrame):
    value_edited = pyqtSignal(float)

    def __init__(self, title, unit, description, minimum, maximum, step, accent, number):
        super().__init__()
        self.setObjectName("numberCard")
        self.setProperty("accent", accent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 14, 20, 12)
        layout.setSpacing(4)
        top = QHBoxLayout()
        index = QLabel(number)
        index.setObjectName("cardIndex")
        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        top.addWidget(index)
        top.addWidget(title_label)
        top.addStretch()
        hint = QLabel(description)
        hint.setObjectName("cardHint")
        top.addWidget(hint)
        layout.addLayout(top)

        row = QHBoxLayout()
        row.setSpacing(10)
        self.spin = NumberSpinBox()
        self.spin.setLocale(QLocale.c())
        self.spin.setDecimals(3)
        self.spin.setRange(minimum, maximum)
        self.spin.setSingleStep(step)
        self.spin.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.spin.setMinimumHeight(60)
        self.spin.setMinimumWidth(245)
        self.spin.setAccessibleName(title)
        self.spin.setToolTip("Введи число; Ctrl+A — выделить целиком")
        self.spin.valueChanged.connect(self.forward_value)
        row.addWidget(self.spin, 1)
        unit_label = QLabel(unit)
        unit_label.setObjectName("unitLabel")
        row.addWidget(unit_label)
        for text, action, tooltip in [("−", self.spin.stepDown, "Уменьшить значение"), ("+", self.spin.stepUp, "Увеличить значение")]:
            button = QPushButton(text)
            button.setObjectName("stepButton")
            button.setFixedSize(34, 34)
            button.setCursor(Qt.PointingHandCursor)
            button.setToolTip(tooltip)
            button.setAccessibleName(f"{title}: {tooltip.lower()}")
            button.clicked.connect(action)
            row.addWidget(button)
        layout.addLayout(row)

    @pyqtSlot(float)
    def forward_value(self, value):
        self.value_edited.emit(value)

    def set_value(self, value):
        if isclose(self.spin.value(), value, rel_tol=0, abs_tol=1e-9):
            return
        # Обновление из модели не должно запускать новый круг сигналов.
        with QSignalBlocker(self.spin):
            self.spin.setValue(value)

"""Температура хранится в °C, остальные шкалы вычисляются из неё."""
from math import isfinite
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot


class Data(QObject):
    changed = pyqtSignal(float, float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.celsius = 22.0

    def getData(self):
        return self.celsius, self.celsius * 9 / 5 + 32, self.celsius + 273.15

    def publish(self):
        self.changed.emit(*self.getData())

    @pyqtSlot(float)
    def set_celsius(self, value):
        if isfinite(value):
            self.celsius = max(-100.0, min(100.0, value))
            self.publish()

    @pyqtSlot(float)
    def set_fahrenheit(self, value):
        if isfinite(value):
            self.set_celsius((value - 32) * 5 / 9)

    @pyqtSlot(float)
    def set_kelvin(self, value):
        if isfinite(value):
            self.set_celsius(value - 273.15)

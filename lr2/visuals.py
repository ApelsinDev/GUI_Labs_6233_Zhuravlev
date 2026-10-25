"""Круговой термометр: рисунок Qt обновляется вместе с полями."""
from math import cos, sin, radians
from PyQt5.QtCore import QPointF, QRectF, Qt, pyqtSlot
from PyQt5.QtGui import QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import QWidget


class TemperatureDial(QWidget):
    def __init__(self):
        super().__init__()
        self.temperature = 22.0
        self.setMinimumSize(280, 280)
        self.setAccessibleName("Температура по Цельсию")

    @pyqtSlot(float)
    def set_temperature(self, value):
        self.temperature = value
        self.setAccessibleDescription(f"{value:.3f} градусов Цельсия")
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        side = min(self.width(), self.height())
        painter.translate((self.width() - side) / 2, (self.height() - side) / 2)
        painter.scale(side / 360, side / 360)
        fraction = (self.temperature + 100) / 200
        cold, hot = (111, 207, 250), (255, 159, 102)
        color = QColor(*(round(a + (b - a) * fraction) for a, b in zip(cold, hot)))
        # Риски шкалы идут от −100 до +100 °C по часовой стрелке.
        for index in range(41):
            angle = radians(225 - index * 270 / 40)
            outer, inner = 166, (153 if index % 5 == 0 else 159)
            painter.setPen(QPen(QColor("#6d8496" if index % 5 == 0 else "#3c5062"), 1.5))
            painter.drawLine(QPointF(180 + inner * cos(angle), 180 - inner * sin(angle)), QPointF(180 + outer * cos(angle), 180 - outer * sin(angle)))
        arc = QRectF(40, 40, 280, 280)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor("#2b4051"), 9, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(arc, 225 * 16, -270 * 16)
        painter.setPen(QPen(color, 9, Qt.SolidLine, Qt.RoundCap))
        if fraction > 0:
            painter.drawArc(arc, 225 * 16, round(-270 * 16 * fraction))
        angle = radians(225 - fraction * 270)
        point = QPointF(180 + 140 * cos(angle), 180 - 140 * sin(angle))
        painter.setPen(QPen(QColor("#192632"), 4))
        painter.setBrush(color)
        painter.drawEllipse(point, 9, 9)
        painter.setPen(QPen(QColor("#314556"), 1))
        painter.setBrush(QColor("#1d2d3b"))
        painter.drawEllipse(QRectF(67, 67, 226, 226))
        painter.setPen(QColor("#91aabb"))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(QRectF(80, 108, 200, 30), Qt.AlignCenter, "ТЕМПЕРАТУРА / °C")
        painter.setPen(QColor("#f0f5fa"))
        painter.setFont(QFont("Segoe UI", 42, QFont.Bold))
        value = f"{self.temperature:.1f}".rstrip("0").rstrip(".")
        # Округление до целых десятков не должно удалять нули целого числа.
        if value == "-0":
            value = "0"
        painter.drawText(QRectF(65, 140, 230, 80), Qt.AlignCenter, value + "°")
        painter.setPen(color)
        painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
        state = "ХОЛОДНО" if self.temperature < 10 else "ТЕПЛО" if self.temperature < 30 else "ЖАРКО"
        painter.drawText(QRectF(80, 224, 200, 26), Qt.AlignCenter, state)
        painter.setPen(QColor("#91aabb"))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(QRectF(47, 300, 75, 25), Qt.AlignCenter, "−100°")
        painter.drawText(QRectF(239, 300, 75, 25), Qt.AlignCenter, "+100°")
        painter.end()

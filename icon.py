from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtCore import Qt, QSize

def create_icon():
    # Создаем пустое изображение
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.transparent)
    
    # Создаем painter
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    
    # Рисуем круг
    painter.setBrush(QColor("#4CAF50"))  # Зеленый цвет
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(2, 2, 28, 28)
    
    # Рисуем букву "S"
    painter.setPen(QColor("white"))
    painter.setFont(painter.font())
    painter.drawText(pixmap.rect(), Qt.AlignCenter, "S")
    
    painter.end()
    
    # Создаем иконку
    icon = QIcon(pixmap)
    
    # Сохраняем иконку
    icon.pixmap(QSize(32, 32)).save("icon.png")

if __name__ == "__main__":
    create_icon() 
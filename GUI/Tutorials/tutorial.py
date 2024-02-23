import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QLabel, QVBoxLayout, QPushButton, \
    QGridLayout, QTableWidget, QTableWidgetItem, QTabWidget
from PyQt6.QtGui import QPalette, QColor


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()

        self.setWindowTitle("My App")

        tabs = QTabWidget()

        tabs.setTabPosition(QTabWidget.TabPosition.North)
        tabs.setMovable(True)

        for n, c in enumerate(['red', 'green', 'blue', 'yellow']):
            tabs.addTab(Colour(c), c)

        self.setCentralWidget(tabs)

class Colour(QWidget):
    def __init__(self, colour):
        super(Colour, self).__init__()
        self.setAutoFillBackground(True)

        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(colour))
        self.setPalette(palette)


app = QApplication(sys.argv)
w = MainWindow()
w.show()
app.exec()


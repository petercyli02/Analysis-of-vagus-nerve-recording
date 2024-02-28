import sys
import time

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QLabel, QVBoxLayout, QPushButton, \
    QGridLayout, QTableWidget, QTableWidgetItem, QTabWidget, QSlider
from PyQt6.QtGui import QPalette, QColor
import pyqtgraph as pg
from pyqtgraph import AxisItem, ImageItem
import numpy as np


sys.path.append('../')
from prototype1_setup import record
from Neurogram_short import Recording


class TimeAxisItem(AxisItem):
    def __init__(self, *args, **kwargs):
        super(TimeAxisItem, self).__init__(*args, **kwargs)

    def tickStrings(self, values, scale, spacing):
        return [time.strftime('%H:%M:%S', time.gmtime(val)) for val in values]

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('PyQtGraph Experimentation')

        self.button = QPushButton('Load Plot')
        self.button.clicked.connect(self.plot_data)

        self.layout = QHBoxLayout()
        self.layout.addWidget(self.button)

        self.centralwidget = QWidget()
        self.centralwidget.setLayout(self.layout)
        self.setCentralWidget(self.centralwidget)


    def plot_data(self):
        self.layout.removeWidget(self.button)
        self.button.deleteLater()
        self.button = None

        self.plot_widget = pg.PlotWidget(axisItems={'bottom': TimeAxisItem(orientation='bottom')})
        channel = record.channels[0]

        x_range = np.array([i for i in range(0, len(record.recording), 100)])  # only taking 1 in 100 datapoints for plotting
        sample_rate = 100

        self.x = np.arange(0, len(x_range)) / sample_rate
        self.y = record.filtered['ch_%s' % channel][x_range]

        self.plot = self.plot_widget.plot(self.x, self.y)

        self.plot_widget.setMouseEnabled(x=True, y=False)

        self.plot_widget.setXRange(0, self.x[-1], padding=0)  # Window range set to first 20 seconds

        self.layout.addWidget(self.plot_widget)

        self.slider = QSlider(Qt.Orientation.Vertical)
        self.slider.setMinimum(1)
        self.slider.setMaximum(100)
        self.slider.setValue(10)
        self.slider.valueChanged.connect(self.update_zoom)

        self.layout.addWidget(self.slider)

    def update_zoom(self):
        zoom_factor = self.slider.value()
        max_zoom = self.x[-1]
        current_zoom = max_zoom / zoom_factor

        center_point = self.plot_widget.plotItem.viewRange()[0][0] + current_zoom / 2

        self.plot_widget.setXRange(center_point - current_zoom / 2, center_point + current_zoom / 2, padding=0)

        self.plot_widget.setYRange(-250, 250)



app = QApplication(sys.argv)
w = MainWindow()
w.show()
app.exec()


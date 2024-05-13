import csv

import sys
import time
import pyqtgraph as pg
import numpy as np
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QWidget, QHBoxLayout
from pyqtgraph import AxisItem


class TimeAxisItem(AxisItem):
    def __init__(self, *args, **kwargs):
        super(TimeAxisItem, self).__init__(*args, **kwargs)

    def tickStrings(self, values, scale, spacing):
        return [time.strftime('%H:%M:%S', time.gmtime(val)) for val in values]



data = []
with open('dummy_glucose_data.csv', 'r', newline='') as file:
    reader = csv.reader(file, delimiter=',')
    for row in reader:
        print(row)
        data.append(row)

data = np.array(data).T
x, y = data[0], data[1]
x = np.asfarray(x)
y = np.asfarray(y)
print(x)
print(y)
print(type(x[0]))
print(type(y[0]))
# Subclass QMainWindow to customize your application's main window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("My App")
        self.layout = QHBoxLayout()
        widget = QWidget()
        widget.setLayout(self.layout)

        plot_widget_zoom = pg.PlotWidget(axisItems={'bottom': TimeAxisItem(orientation='bottom')})
        plot_widget_zoom.plot(x, y)
        # Set the central widget of the Window.
        self.layout.addWidget(plot_widget_zoom)
        self.setCentralWidget(widget)


app = QApplication(sys.argv)

window = MainWindow()
window.show()

app.exec()

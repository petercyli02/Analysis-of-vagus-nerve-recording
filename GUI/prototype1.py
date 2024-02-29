import sys, os

from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QHBoxLayout, QSlider, \
    QGraphicsRectItem
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QUrl, QThread, pyqtSignal, QRectF
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import pyqtgraph as pg
from pyqtgraph import AxisItem, ImageItem, InfiniteLine, PlotDataItem
import numpy as np
import time
from Video_Player_prototype1 import VideoPlayer


# Add the parent directory to sys.path
current_script_path = os.path.dirname(__file__)

parent_dir = os.path.abspath(os.path.join(current_script_path, os.pardir))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)
sys.path.append(parent_dir)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Video and Data Plotter")

        self.setGeometry(100, 100, 400, 800)


        self.top_layout = QVBoxLayout()
        self.middle_layout = QHBoxLayout()
        self.bottom_layout = QHBoxLayout()

        # For sliding horizontal on the adjustable plot
        self.bottom_slider = QSlider(Qt.Orientation.Horizontal)
        self.bottom_slider.setMinimum(0)

        self.video_player = VideoPlayer()
        self.plot_data_button = QPushButton("Plot Data")
        self.plot_data_button.clicked.connect(self.on_plot_data_button_clicked)

        self.loading_label = QLabel("")

        # self.top_layout.addWidget(self.load_video_button)
        self.top_layout.addWidget(self.video_player)
        self.middle_layout.addWidget(self.plot_data_button)
        self.bottom_layout.addWidget(self.loading_label)

        self.main_layout = QVBoxLayout()
        self.main_layout.addLayout(self.top_layout, 2)
        self.main_layout.addLayout(self.middle_layout, 1)
        self.main_layout.addLayout(self.bottom_layout, 1)
        # self.main_layout.addLayout()

        self.central_widget = QWidget()
        self.central_widget.setLayout(self.main_layout)
        self.setCentralWidget(self.central_widget)


    def on_plot_data_button_clicked(self):
        """
        Intermediary method of plotting data, serves as the slot for when data is loaded in startup of the GUI
        For now, manually specifies values for the various parameters passed to the actual plot_data(...) function
        """
        # Indicate that the data is loading
        self.loading_label.setText("Loading Data...")
        self.plot_data_button.setEnabled(False)

        self.data_loader_thread = DataLoaderThread()
        self.data_loader_thread.data_loaded.connect(self.on_data_loaded)
        self.data_loader_thread.start()

        print("on_plot_data_button_clicked finished!")


    def on_data_loaded(self, data):
        print("on_data_loaded triggered!")
        self.plot_data_whole(data, ylim=(-250, 250))
        self.plot_data_adjustable(data, ylim=(-250, 250))

        self.middle_layout.removeWidget(self.plot_data_button)
        self.plot_data_button.deleteLater()
        self.plot_data_button = None

        self.bottom_layout.removeWidget(self.loading_label)
        self.loading_label.deleteLater()
        self.loading_label = None


    def plot_data_whole(self, data, ylim=None):
        self.plotter_whole = Plotter(data, ylim)
        self.video_player.mediaPlayer.positionChanged.connect(self.plotter_whole.update_marker)
        self.plotter_whole.plot_data_whole()
        self.middle_layout.addWidget(self.plotter_whole)

    def plot_data_adjustable(self, data, ylim=None):
        self.plotter_adjustable = Plotter(data, ylim)
        self.video_player.mediaPlayer.positionChanged.connect(self.plotter_adjustable.update_marker)
        self.plotter_adjustable.plot_data_adjustable()
        self.bottom_layout.addWidget(self.plotter_adjustable)



class DataLoaderThread(QThread):
    data_loaded = pyqtSignal(tuple)

    def __init__(self):
        super().__init__()

    def run(self):
        # Import my own functions
        from prototype1_setup import record
        from Neurogram_short import Recording

        channel = record.channels[0]
        start_time = None
        end_time = None

        if start_time is None:
            start_index = 0
        else:
            start_index = 0
            start_index += int(start_time[:3]) * 60 * Recording.window_length
            start_index += int(start_time[3:5]) * Recording.window_length
            if len(start_time) == 9:
                start_index += int(start_time[5:])

        if end_time is None:
            end_index = len(record.recording.index)
        else:
            end_index = 0
            end_index += int(end_time[:3]) * 60 * Recording.window_length
            end_index += int(end_time[3:5]) * Recording.window_length
            if len(end_time) == 9:
                end_index += int(end_time[5:])

        self.x_range = [i for i in range(start_index, end_index, 100)]  # only taking 1 in 100 datapoints for plotting

        self.sample_rate = 100

        self.x = np.arange(0, len(self.x_range)) / self.sample_rate
        self.y = record.filtered['ch_%s' % channel][self.x_range]


        print("\n\n\n")
        print("Emitting data for channel %s" % channel)
        print(self.x)
        print(self.y)
        print("Data emitted.")

        self.data_loaded.emit((self.x, self.y))






class TimeAxisItem(AxisItem):
    def __init__(self, *args, **kwargs):
        super(TimeAxisItem, self).__init__(*args, **kwargs)

    def tickStrings(self, values, scale, spacing):
        return [time.strftime('%H:%M:%S', time.gmtime(val)) for val in values]



class Plotter(QWidget):
    data = None
    viewRect = QGraphicsRectItem()
    viewRect.setBrush(QBrush(QColor(255, 255, 255, 100)))
    sample_rate = 100

    def __init__(self, data, ylim):
        super().__init__()
        Plotter.data = data
        self.layout = QHBoxLayout()
        self.ylim = ylim
        self.x, self.y = data[0], data[1]
        self.marker = InfiniteLine(angle=90, movable=False, pen='r')
        self.setLayout(self.layout)



    def plot_data_whole(self):
        print("plot_data_whole called!")

        Plotter.plot_widget_whole = pg.PlotWidget(axisItems={'bottom': TimeAxisItem(orientation='bottom')})
        self.plot = self.plot_widget_whole.plot(self.x, self.y)

        Plotter.plot_widget_whole.addItem(self.marker)
        width = self.x[-1]
        Plotter.viewRect.setRect(QRectF(0, -250, width, 500)) # Plotter.plot_widget_whole.plotItem.vb.height()))
        Plotter.plot_widget_whole.plotItem.vb.addItem(Plotter.viewRect)

        Plotter.plot_widget_whole.setYRange(-250, 250)

        self.layout.addWidget(Plotter.plot_widget_whole)



    def plot_data_adjustable(self):
        print("plot_data_adjustable called!")
        # self.layout.removeWidget(self.button)
        # self.button.deleteLater()
        # self.button = None

        Plotter.plot_widget_zoom = pg.PlotWidget(axisItems={'bottom': TimeAxisItem(orientation='bottom')})

        self.plot = Plotter.plot_widget_zoom.plot(self.x, self.y)

        Plotter.plot_widget_zoom.addItem(self.marker)

        Plotter.plot_widget_zoom.sigRangeChanged.connect(self.updateViewRect)

        Plotter.plot_widget_zoom.setYRange(-250, 250)

        Plotter.plot_widget_zoom.setMouseEnabled(x=True, y=False)

        Plotter.plot_widget_zoom.setXRange(0, self.x[-1], padding=0)  # Window range set to first 20 seconds

        self.layout.addWidget(Plotter.plot_widget_zoom)

        self.slider = QSlider(Qt.Orientation.Vertical)
        self.slider.setMinimum(1)
        self.slider.setMaximum(100)
        self.slider.setValue(10)
        self.slider.valueChanged.connect(self.update_zoom)

        self.layout.addWidget(self.slider)

    def update_marker(self, position):
        time_in_seconds = position / 1000

        self.marker.setValue(time_in_seconds)


    def updateViewRect(self):
        viewRange = Plotter.plot_widget_zoom.viewRange()
        x_start = viewRange[0][0]
        width = viewRange[0][1] - x_start
        height = 500
        # Update the rectangle's dimensions to match the visible range in the zoom plot
        Plotter.viewRect.setRect(QRectF(x_start, -250, width, height))


    def update_zoom(self):
        zoom_factor = self.slider.value()
        max_zoom = self.x[-1]
        current_zoom = max_zoom / zoom_factor
        center_point = Plotter.plot_widget_zoom.plotItem.viewRange()[0][0] + current_zoom / 2
        Plotter.plot_widget_zoom.setXRange(center_point - current_zoom / 2, center_point + current_zoom / 2, padding=0)





app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec())

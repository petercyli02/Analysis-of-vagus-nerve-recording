import sys, os
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QHBoxLayout, QSlider
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QUrl, QThread, pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import pyqtgraph as pg
from pyqtgraph import AxisItem, ImageItem
import numpy as np
import time



# Add the parent directory to sys.path
current_script_path = os.path.dirname(__file__)

parent_dir = os.path.abspath(os.path.join(current_script_path, os.pardir))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)
sys.path.append(parent_dir)

# # Own functions
# from prototype1_setup import *
# from Neurogram_short import Recording



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
        # x = record.recording.index[x_range]
        # y = record.filtered['ch_%s' % channel][x_range]

        self.sample_rate = 100

        self.x = np.arange(0, len(self.x_range)) / self.sample_rate
        self.y = record.filtered['ch_%s' % channel][self.x_range]


        print("\n\n\n")
        print("Emitting data for channel %s" % channel)
        print(self.x)
        print(self.y)
        print("Data emitted.")

        self.data_loaded.emit((self.x, self.y))




class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Video and Data Plotter")

        self.top_layout = QVBoxLayout()
        self.middle_layout = QHBoxLayout()
        self.bottom_layout = QHBoxLayout()

        # Buttons for loading video and plotting data, and label to indicate loading
        self.load_video_button = QPushButton("Load Video")
        self.load_video_button.clicked.connect(self.load_video)
        self.plot_data_button = QPushButton("Plot Data")
        self.plot_data_button.clicked.connect(self.on_plot_data_button_clicked)

        self.loading_label = QLabel("")

        self.top_layout.addWidget(self.load_video_button)
        self.middle_layout.addWidget(self.plot_data_button)
        self.bottom_layout.addWidget(self.loading_label)

        self.main_layout = QVBoxLayout()
        self.main_layout.addLayout(self.top_layout)
        self.main_layout.addLayout(self.middle_layout)
        self.main_layout.addLayout(self.bottom_layout)

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
        self.plotter_whole.plot_data_whole()
        self.middle_layout.addWidget(self.plotter_whole)

    def plot_data_adjustable(self, data, ylim=None):
        self.plotter_adjustable = Plotter(data, ylim)
        self.plotter_adjustable.plot_data_adjustable()
        self.bottom_layout.addWidget(self.plotter_adjustable)


    # def plot_data(self, data, ylim=None):
    #     print("plot_data called!")
    #
    #     x, y = data[0], data[1]
    #
    #     self.figure = Figure()
    #     self.canvas_1 = FigureCanvas(self.figure)
    #     ax = self.figure.add_subplot(111)
    #     ax.clear()
    #     ax.plot(x, y)
    #     # ax.set_title("Channel %s" % channel)
    #     ax.set_xlabel('Time')
    #     ax.set_ylabel('Voltage [uV]')
    #     if ylim is not None:
    #         ax.set_ylim(ylim[0], ylim[1])
    #     self.canvas_1.draw()
    #
    #     # Remove buttons and add plot to layout
    #     self.middle_layout.removeWidget(self.plot_data_button)
    #     self.plot_data_button.deleteLater()
    #     self.plot_data_button = None
    #
    #     self.bottom_layout.removeWidget(self.loading_label)
    #     self.loading_label.deleteLater()
    #     self.loading_label = None
    #
    #     self.middle_layout.addWidget(self.canvas_1, 1)  # 1/3 of the space for plot
    #
    # def plot_data_adjustable(self, data, ylim=None):
    #     self.zoom_slider = QSlider(Qt.Orientation.Vertical)
    #     self.zoom_slider.setRange(1, 100)
    #     self.zoom_slider.valueChanged.connect(self.on_zoom_changed)
    #
    #     x, y = data[0], data[1]
    #     self.figure = Figure()
    #     self.canvas_2 = FigureCanvas(self.figure)
    #     ax = self.figure.add_subplot(111)
    #     ax.clear()
    #     ax.plot(x, y)
    #     # ax.set_title("Channel %s" % channel)
    #     ax.set_xlabel('Time')
    #     ax.set_ylabel('Voltage [uV]')
    #     if ylim is not None:
    #         ax.set_ylim(ylim[0], ylim[1])
    #
    #     self.canvas_2.draw()
    #
    #     # Remove buttons and add plot to layout
    #     self.bottom_layout.addWidget(self.canvas_2)
    #     self.bottom_layout.addWidget(self.zoom_slider)


    # def on_zoom_changed(self, value):
    #     ax = self.canvas_2.axes[0]
    #     xmin =
    #     ax.set_xlim([record.recording.index[xmin], record.recording.index[xmax]])
    #     self.canvas_2.draw()
    #

    def load_video(self):
        # Video Player
        self.video_player = QMediaPlayer()
        video_widget = QVideoWidget()
        self.video_player.setVideoOutput(video_widget)

        # Remove buttons and add video widget to layout
        self.top_layout.removeWidget(self.load_video_button)
        self.load_video_button.deleteLater()
        self.load_video_button = None


        self.top_layout.addWidget(video_widget, 2)  # 1/3 of the space for video

        # Setup video source (replace with your video file path)
        # video_path = "../../../datasets/rat7&8/day2/rat7&8_Day2_noSound.mp4"
        video_path = r"C:\Users\airbl\OneDrive - University of Cambridge\Documents\Cambridge Work IIB\IIB Project\Code\code_Peter\datasets\Misc_files_for_testing\test.mp4"
        self.video_player.setSource(QUrl.fromLocalFile(video_path))

        # Start the video
        self.video_player.play()



class TimeAxisItem(AxisItem):
    def __init__(self, *args, **kwargs):
        super(TimeAxisItem, self).__init__(*args, **kwargs)

    def tickStrings(self, values, scale, spacing):
        return [time.strftime('%H:%M:%S', time.gmtime(val)) for val in values]



class Plotter(QWidget):
    data = None
    # sample_rate = 100

    def __init__(self, data, ylim):
        super().__init__()
        Plotter.data = data
        self.layout = QHBoxLayout()
        self.ylim = ylim

        # self.channel = record.channels[0]
        #
        # self.x_range = np.array([i for i in range(0, len(record.recording), 100)])  # only taking 1 in 100 datapoints for plotting
        # self.sample_rate = 100
        #
        # self.x = np.arange(0, len(self.x_range)) / self.sample_rate
        # self.y = record.filtered['ch_%s' % self.channel][self.x_range]

        self.x, self.y = data[0], data[1]

        self.setLayout(self.layout)



    def plot_data_whole(self):
        print("plot_data_whole called!")

        self.plot_widget_whole = pg.PlotWidget(axisItems={'bottom': TimeAxisItem(orientation='bottom')})
        self.plot = self.plot_widget_whole.plot(self.x, self.y)

        self.plot_widget_whole.setYRange(-250, 250)

        self.layout.addWidget(self.plot_widget_whole)



    def plot_data_adjustable(self):
        print("plot_data_adjustable called!")
        # self.layout.removeWidget(self.button)
        # self.button.deleteLater()
        # self.button = None

        self.plot_widget_zoom = pg.PlotWidget(axisItems={'bottom': TimeAxisItem(orientation='bottom')})

        self.plot = self.plot_widget_zoom.plot(self.x, self.y)

        self.plot_widget_zoom.setYRange(-250, 250)

        self.plot_widget_zoom.setMouseEnabled(x=True, y=False)

        self.plot_widget_zoom.setXRange(0, self.x[-1], padding=0)  # Window range set to first 20 seconds

        self.layout.addWidget(self.plot_widget_zoom)

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

        center_point = self.plot_widget_zoom.plotItem.viewRange()[0][0] + current_zoom / 2

        self.plot_widget_zoom.setXRange(center_point - current_zoom / 2, center_point + current_zoom / 2, padding=0)





app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec())

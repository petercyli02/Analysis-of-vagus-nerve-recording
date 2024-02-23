import sys, os
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt5.QtMultimedia import QMediaContent
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QUrl
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


# Add the parent directory to sys.path
current_script_path = os.path.dirname(__file__)

parent_dir = os.path.abspath(os.path.join(current_script_path, os.pardir))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)
sys.path.append(parent_dir)

# Own functions
from prototype1_setup import *
from Neurogram_short import Recording


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Video and Data Plotter")

        starting_layout = QVBoxLayout()

        # Create a central widget and layout
        self.central_widget = QWidget(self)
        self.layout = QVBoxLayout(self.central_widget)

        # Buttons for loading video and plotting data
        self.load_video_button = QPushButton("Load Video", self)
        self.load_video_button.clicked.connect(self.load_video)

        self.plot_data_button = QPushButton("Plot Data", self)
        self.plot_data_button.clicked.connect(self.plot_data)

        # Add buttons to layout
        self.layout.addWidget(self.load_video_button)
        self.layout.addWidget(self.plot_data_button)

        self.setCentralWidget(self.central_widget)


        # Data Plot
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.layout.addWidget(self.canvas, 1)  # 1/3 of the space for plot

        # You can plot your data here
        self.plot_data(start_time=None, end_time="02000", ylim=(-250, 250))

    def plot_data(self, channel=record.channels[0], start_time=None, end_time=None, ylim=None):

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

        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        ax = self.figure.add_subplot(111)
        ax.clear()
        # ax.plot([0, 1, 2, 3, 4], [10, 1, 20, 3, 40], 'r-')  # Sample data
        x_range = [i for i in range(start_index, end_index)]
        signal = record.filtered['ch_%s' % channel][x_range]
        ax.plot(record.recording.index[x_range], signal)
        ax.set_title("Channel %s" % channel)
        ax.set_xlabel('Time')
        ax.set_ylabel('Voltage [uV]')
        if ylim is not None:
            ax.set_ylim(ylim[0], ylim[1])
        self.canvas.draw()

        # Remove buttons and add plot to layout
        self.layout.removeWidget(self.load_video_button)
        self.load_video_button.deleteLater()
        self.load_video_button = None

        self.layout.removeWidget(self.plot_data_button)
        self.plot_data_button.deleteLater()
        self.plot_data_button = None

        self.layout.addWidget(self.canvas, 1)  # 1/3 of the space for plot

    def load_video(self):
        # Video Player
        self.video_player = QMediaPlayer()
        video_widget = QVideoWidget()
        self.video_player.setVideoOutput(video_widget)

        # Remove buttons and add video widget to layout
        self.layout.removeWidget(self.load_video_button)
        self.load_video_button.deleteLater()
        self.load_video_button = None

        self.layout.removeWidget(self.plot_data_button)
        self.plot_data_button.deleteLater()
        self.plot_data_button = None

        self.layout.addWidget(video_widget, 2)  # 2/3 of the space for video

        # Setup video source (replace with your video file path)
        video_path = "../../datasets/rat7&8/day2/rat7&8_Day2_noSound.mp4"
        self.video_player.setSource(QUrl.fromLocalFile(video_path))

        # Start the video
        self.video_player.play()


app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec())

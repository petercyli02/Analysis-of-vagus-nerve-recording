import os
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QSlider, QHBoxLayout, \
    QFileDialog, QSizePolicy, QStyle, QLabel
from PyQt6.QtMultimedia import QMediaPlayer, QMediaMetaData
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QUrl, QDir
from PyQt6.QtGui import QIcon, QPalette, QColor


class VideoPlayer(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Simple Media Player")
        self.setGeometry(100, 100, 800, 600)

        # Set up the media player
        self.mediaPlayer = QMediaPlayer()

        # Video widget
        self.videoWidget = QVideoWidget()

        self.videoWidget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Play button
        self.playButton = QPushButton()
        self.playButton.setEnabled(False)
        self.playButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.playButton.clicked.connect(self.play)

        # Open button
        self.openButton = QPushButton("Open Video")
        self.openButton.clicked.connect(self.openFile)

        # Progress slider
        self.progressSlider = QSlider(Qt.Orientation.Horizontal)
        self.progressSlider.setRange(0, 0)
        self.progressSlider.sliderMoved.connect(self.setPosition)

        # Playback speed slider
        self.speedSlider = QSlider(Qt.Orientation.Horizontal)
        self.speedSlider.setRange(25, 200)  # Representing 0.25x to 2x
        self.speedSlider.setValue(100)  # Default speed is 1x
        self.speedSlider.setTickInterval(25)  # Steps of 0.25x
        self.speedSlider.sliderMoved.connect(self.setPlaybackSpeed)
        self.speedLabel = QLabel("1x")  # Label to display the current speed
        self.speedSlider.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        # Labels for current and total time
        self.time_label = QLabel('00:00:00 / 00:00:00')
        self.mediaPlayer.positionChanged.connect(self.update_position_label)
        self.mediaPlayer.durationChanged.connect(self.update_duration_label)


        # Horizontal layout for progress slider, play button, and speed slider
        controlLayout = QHBoxLayout()
        controlLayout.addWidget(self.playButton)
        controlLayout.addWidget(self.time_label)
        controlLayout.addWidget(self.speedSlider)
        controlLayout.addWidget(self.speedLabel)
        # controlLayout.addWidget(self.progressSlider, 8)
        controlLayout.addStretch(1)

        # Main layout
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.openButton, 0)
        self.layout.addWidget(self.videoWidget, 2)
        self.layout.addLayout(controlLayout, 0)
        self.layout.addWidget(self.progressSlider, 0)


        self.setLayout(self.layout)

        self.mediaPlayer.setVideoOutput(self.videoWidget)
        self.mediaPlayer.playbackStateChanged.connect(self.mediaStateChanged)
        self.mediaPlayer.positionChanged.connect(self.positionChanged)
        self.mediaPlayer.durationChanged.connect(self.durationChanged)
        self.mediaPlayer.errorOccurred.connect(self.handleError)

    def handleError(self):
        print("Error occurred: ", self.mediaPlayer.errorString())

    def openFile(self):
        dialog_txt = "Choose Media File"
        filename, _ = QFileDialog.getOpenFileName(self, dialog_txt, os.path.expanduser('~'))
        if filename:
            # self.layout.removeWidget(self.openButton)
            # self.openButton.deleteLater()
            # self.openButton = None
            self.mediaPlayer.setSource(QUrl.fromLocalFile(filename))
            self.playButton.setEnabled(True)
            self.mediaPlayer.play()

    def play(self):
        if self.mediaPlayer.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.mediaPlayer.pause()
        else:
            self.mediaPlayer.play()

    def mediaStateChanged(self, state):
        if self.mediaPlayer.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.playButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
        else:
            self.playButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))

    def positionChanged(self, position):
        self.progressSlider.setValue(position)

    def durationChanged(self, duration):
        self.progressSlider.setRange(0, duration)

    def setPosition(self, position):
        self.mediaPlayer.setPosition(position)

    def setPlaybackSpeed(self, speed):
        # Convert slider value to playback rate (e.g., 100 -> 1.0x speed)
        playbackRate = speed / 100.0
        self.mediaPlayer.setPlaybackRate(playbackRate)
        self.speedLabel.setText(f"{playbackRate}x")

    def update_position_label(self, position):
        # Convert the position from milliseconds to hours, minutes, and seconds
        hours, remainder = divmod(position // 1000, 3600)
        minutes, seconds = divmod(remainder, 60)

        current_time = f"{hours:02}:{minutes:02}:{seconds:02}"
        # Update the current time label
        self.time_label.setText(f"{current_time} / {self.total_time}")

    def update_duration_label(self, duration):
        # Convert the duration from milliseconds to hours, minutes, and seconds
        hours, remainder = divmod(duration // 1000, 3600)
        minutes, seconds = divmod(remainder, 60)

        self.total_time = f"{hours:02}:{minutes:02}:{seconds:02}"
        self.update_position_label(0)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    player = VideoPlayer()
    player.show()
    sys.exit(app.exec())

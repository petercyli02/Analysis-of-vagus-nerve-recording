import copy
import csv
import subprocess
import sys, os
from datetime import datetime, timezone

from IPython.external.qt_for_kernel import QtCore
from PyQt6.QtGui import QBrush, QColor, QAction
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QHBoxLayout, QSlider, \
    QGraphicsRectItem, QStyle, QToolBar, QCheckBox, QFileDialog, QDialog, QDial, QSizePolicy
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QUrl, QThread, pyqtSignal, QRectF, QTimer, QSize, QDateTime, QProcess
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import pyqtgraph as pg
from pyqtgraph import AxisItem, ImageItem, InfiniteLine, PlotDataItem, ViewBox, LinearRegionItem, SignalProxy
import numpy as np
import time
from Video_Player_prototype1 import VideoPlayer

# # Import my own functions
# from prototype2_setup import setup
# from Neurogram_short import Recording


# Add the parent directory to sys.path
current_script_path = os.path.dirname(__file__)

parent_dir = os.path.abspath(os.path.join(current_script_path, os.pardir))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)
sys.path.append(parent_dir)


def restart():
    """Restarts the current program, with file objects and descriptors
       cleanup
    """
    try:
        # Note: sys.executable is the path to the Python interpreter
        #       sys.argv[0] is the script name. It might be necessary to use the full path.
        #       You might also need to add additional arguments depending on your application.
        subprocess.Popen([sys.executable, os.path.abspath(sys.argv[0])] + sys.argv[1:])
    except Exception as e:
        print(f'Failed to restart the application: {e}')
    finally:
        # Exit the current application, 0 means a clean exit without error
        sys.exit(0)

    # QtCore.QCoreApplication.quit()
    # status = QtCore.QProcess.startDetached(sys.executable, sys.argv)
    # print(status)



class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Video and Data Plotter")

        self.setGeometry(100, 100, 400, 800)

        self.top_layout = QVBoxLayout()
        self.middle_layout = QHBoxLayout()
        self.bottom_layout = QHBoxLayout()

        self.plotter_adjustable = None
        self.plotter_whole = None

        # For sliding horizontal on the adjustable plot

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

        self.central_widget = QWidget()
        self.central_widget.setLayout(self.main_layout)
        self.setCentralWidget(self.central_widget)

        # Adding a toolbar and a menu bar
        self.menu_bar = self.menuBar()

        self.file_menu = self.menu_bar.addMenu("&File")
        load_video_action = QAction("Load Video", self)
        load_video_action.triggered.connect(self.video_player.openFile)
        # load_video_action.triggered.connect(self.video_player.)
        self.file_menu.addAction(load_video_action)
        load_data_action = QAction("Load Signal Data", self)
        load_data_action.triggered.connect(self.on_plot_data_button_clicked)
        self.file_menu.addAction(load_data_action)
        open_artifact_file_action = QAction("Load Movement Data", self)
        open_artifact_file_action.triggered.connect(self.load_movement_data)
        self.file_menu.addAction(open_artifact_file_action)
        self.save_action = QAction("Save", self)
        self.save_action.triggered.connect(self.save)
        self.save_action.setEnabled(False)
        self.file_menu.addAction(self.save_action)
        save_as_action = QAction("Save As", self)
        save_as_action.triggered.connect(self.save_as)
        self.file_menu.addAction(save_as_action)
        clear_window_action = QAction("Clear Window", self)
        clear_window_action.triggered.connect(MainWindow.clear_window)
        self.file_menu.addAction(clear_window_action)

        self.settings_menu = self.menu_bar.addMenu("&Settings")

        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setIconSize(QSize(50, 50))
        self.addToolBar(self.toolbar)

        self.show_ma_action = QAction("Show Movement Windows", self)
        self.toolbar.addAction(self.show_ma_action)
        self.show_ma_action.setCheckable(True)
        self.show_ma_action.setChecked(True)
        self.show_ma_action.toggled.connect(self.toggle_show_ma)
        self.change_category_action = QAction("Change category", self)
        self.toolbar.addAction(self.change_category_action)
        self.change_category_action.triggered.connect(Plotter.change_category)
        self.change_category_action.setEnabled(False)
        self.adjust_offset_action = QAction("Adjust Offset", self)
        self.adjust_offset_action.setEnabled(False)
        self.adjust_offset_action.triggered.connect(self.open_offset_adjuster)
        self.toolbar.addAction(self.adjust_offset_action)
        self.reset_action = QAction("Clear Movement Data")
        self.toolbar.addAction(self.adjust_offset_action)
        self.reset_action.setEnabled(True)
        self.reset_action.triggered.connect(Plotter.clear_movement_data)

        # self.adjust_offset_action = QAction("Show Motion Artifacts", self)
        # self.toolbar.addAction(self.adjust_offset_action)
        # self.toolbar.addSeparator()
        # self.toolbar.addWidget(QLabel("Show Motion Artifacts"))
        # self.toolbar.addWidget(QCheckBox())


        # So that the KeyPressEvent and KeyReleaseEvent overrides work fine
        self.plotter_adjustable = None

        # Saving the timestamps:
        self.movement_start, self.movement_end = None, None
        self.current_file = None

        # Focus policy to ensure we can receive key presses
        # self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Creating an indicator for if the spacebar is held down
        self.spacebar_mode = False
        self.rewind_speed = 200  # Each time A is pressed, rewind by ___ milliseconds


    @staticmethod
    def clear_window():
        restart()
        # self.video_player.mediaPlayer.setSource(QUrl())
        #
        # if self.plotter_adjustable or self.plotter_whole:
        #     self.middle_layout.removeWidget(self.plotter_whole)
        #     self.plotter_whole.deleteLater()
        #     self.plot_widget_whole = None
        #     self.bottom_layout.removeWidget(self.plotter_adjustable)
        #     self.plotter_adjustable.deleteLater()
        #     self.plotter_adjustable = None
        #
        #     self.loading_label = QLabel("")
        #     self.bottom_layout.addWidget(self.loading_label)
        #
        #     self.plot_data_button = QPushButton("Plot Data")
        #     self.plot_data_button.clicked.connect(self.on_plot_data_button_clicked)
        #     self.middle_layout.addWidget(self.plot_data_button)
        #
        # Plotter.reset_class_attributes()
    def open_offset_adjuster(self):
        if window.video_player.mediaPlayer.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            window.video_player.mediaPlayer.pause()
        Plotter.plot_widget_whole.getPlotItem().hideAxis('bottom')
        Plotter.plot_widget_zoom.getPlotItem().hideAxis('bottom')
        # layout = QVBoxLayout()
        self.offset_adjuster = OffsetAdjuster(max_offset=60)
        self.offset_adjuster.exec()
        # layout.addWidget(self.offset_adjuster)
        Plotter.plot_widget_whole.getPlotItem().showAxis('bottom')
        Plotter.plot_widget_zoom.getPlotItem().showAxis('bottom')


    def load_movement_data(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Load Movement Intervals", "", "CSV (*.csv)")
        self.current_file = filepath
        with open(filepath, "r") as file:
            reader = csv.reader(file)
            for row in reader:
                region_whole = ClickableLinearRegionItem(values=[float(row[0]), float(row[1])], brush=QBrush(QColor(MovementTypeDialog.colours[row[2]])))
                region_zoom = ClickableLinearRegionItem(values=[float(row[0]), float(row[1])], brush=QBrush(QColor(MovementTypeDialog.colours[row[2]])))
                Plotter.interval_regions[(row[0], row[1], row[2])] = [region_whole, region_zoom]
                if self.show_ma_action.isChecked() and Plotter.plot_widget_whole and Plotter.plot_widget_zoom:
                    Plotter.plot_widget_whole.addItem(region_whole)
                    Plotter.plot_widget_zoom.addItem(region_zoom)


    def save(self):
        with open(self.current_file, 'a' if self.current_file else 'w', newline='') as file:
            writer = csv.writer(file)
            for start, end, category in Plotter.new_timestamps:
                # writer.writerow([start.toString(Qt.ISODateWithMs), end.toString(Qt.ISODateWithMs)])
                writer.writerow([start, end, category])
                # writer.writerow([ms_to_iso8601(start), ms_to_iso8601(end)])
                # Plotter.timestamps.append((start, end))
                # Plotter.interval_regions[(start, end)] = ClickableLinearRegionItem(values=[start, end])
        Plotter.new_timestamps.clear()
        remaining_intervals = []
        with open(self.current_file, 'r', newline='') as file:
            reader = csv.reader(file)
            for row in reader:
                interval = tuple(row)
                if interval not in Plotter.entries_to_delete:
                    remaining_intervals.append(interval)
                if interval in Plotter.entries_to_change:
                    remaining_intervals.append((interval[0], interval[1], Plotter.entries_to_change[interval]))
        with open(self.current_file, 'w', newline='') as file:
            writer = csv.writer(file)
            for interval in remaining_intervals:
                writer.writerow(interval)


    def save_as(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "CSV (*.csv)")
        if file_path:
            self.current_file = file_path
            self.save()
            self.save_action.setEnabled(True)


    def toggle_show_ma(self, checked):
        if not self.plotter_adjustable or not self.plotter_whole:
            pass
        elif checked:
            Plotter.display_intervals()
        else:
            Plotter.clear_intervals()


    def on_plot_data_button_clicked(self):
        """
        Intermediary method of plotting data, serves as the slot for when data is loaded in startup of the GUI v1
        For now, manually specifies values for the various parameters passed to the actual plot_data(...) function
        """
        # Indicate that the data is loading
        if not self.loading_label and not self.plot_data_button:
            self.middle_layout.removeWidget(self.plotter_whole)
            self.plotter_whole.deleteLater()
            self.plotter_whole = None

            self.bottom_layout.removeWidget(self.plotter_adjustable)
            self.plotter_adjustable.deleteLater()
            self.plotter_adjustable = None

            self.slider.setValue(1)

        self.plot_data_button.setEnabled(False)
        self.loading_label.setText("Loading data...")

        self.data_loader_thread = DataLoaderThread()
        self.data_loader_thread.data_loaded.connect(self.on_data_loaded)
        self.data_loader_thread.start()



    def on_data_loaded(self, data):
        self.plot_data_whole(data, ylim=(-250, 250))
        self.plot_data_adjustable(data, ylim=(-250, 250))

        self.middle_layout.removeWidget(self.plot_data_button)
        self.plot_data_button.deleteLater()
        self.plot_data_button = None

        self.bottom_layout.removeWidget(self.loading_label)
        self.loading_label.deleteLater()
        self.loading_label = None

        if self.video_player.mediaPlayer.source is not None:
            self.adjust_offset_action.setEnabled(True)


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


    def keyPressEvent(self, event):
        if self.plotter_adjustable and self.plotter_whole and not event.isAutoRepeat():
            if self.video_player.mediaPlayer.source and event.key() == Qt.Key.Key_Space:
                self.movement_start = self.video_player.mediaPlayer.position() / 1000  # .position() gives the timestamp in milliseconds
                self.set_marker_value(self.movement_start)
                self.set_marker_visibility(True)
                if not self.spacebar_mode:
                    self.spacebar_mode = True
                    self.video_player.mediaPlayer.pause()

            elif self.spacebar_mode and event.key() == Qt.Key.Key_D:
                self.video_player.mediaPlayer.play()
            elif self.spacebar_mode and event.key() == Qt.Key.Key_A:
                # self.video_player.mediaPlayer.setPlaybackRate(-1 * self.video_player.mediaPlayer.playbackRate())
                # self.video_player.mediaPlayer.play()
                self.video_player.mediaPlayer.setPosition(max(0, self.video_player.mediaPlayer.position() - self.rewind_speed))
                if self.video_player.mediaPlayer.position() < 1000 * self.movement_start:
                    # print("Video player position:", self.video_player.mediaPlayer.position())
                    self.movement_start = self.video_player.mediaPlayer.position() / 1000.0
                    self.set_marker_value(self.video_player.mediaPlayer.position() / 1000.0)
                    # print("Start marker position:", self.plotter_adjustable.movement_start_marker.value())

            elif event.key() == Qt.Key.Key_Left:
                self.plotter_adjustable.left_timer.start()
            elif event.key() == Qt.Key.Key_Right:
                self.plotter_adjustable.right_timer.start()
            elif event.key() == Qt.Key.Key_Up:
                self.plotter_adjustable.zoom_in_timer.start()
            elif event.key() == Qt.Key.Key_Down:
                self.plotter_adjustable.zoom_out_timer.start()
            elif Plotter.selected_region and event.key() == Qt.Key.Key_Delete:
                Plotter.delete_selected_interval()

            # elif event.key() == Qt.Key.Key_H:
            #     for i in range(10):
            #         testRegion = ClickableLinearRegionItem(values=(10*i, 10*i + 50))
            #         Plotter.plot_widget_whole.addItem(testRegion)
            else:
                super().keyPressEvent(event)


    def keyReleaseEvent(self, event):
        if self.plotter_adjustable and self.plotter_whole and not event.isAutoRepeat():
            if self.movement_start and event.key() == Qt.Key.Key_Space:
                self.spacebar_mode = False
                self.movement_end = self.video_player.mediaPlayer.position() / 1000  # .position() gives the timestamp in milliseconds
                if self.movement_end > self.movement_start:
                    dialog = MovementTypeDialog()
                    if dialog.exec():
                        category = dialog.get_selected_category()
                        itv = (self.movement_start, self.movement_end, MovementTypeDialog.categories[category])
                    # Plotter.timestamps.append(itv)
                        Plotter.new_timestamps.append(itv)
                        Plotter.add_region(itv)
                    self.video_player.mediaPlayer.play()
                else:
                    self.video_player.mediaPlayer.play()
                self.movement_start, self.movement_end = None, None
                self.set_marker_visibility(False)

            # elif self.spacebar_mode and event.key() == Qt.Key.Key_A:
            #     self.video_player.mediaPlayer.pause()
                # self.video_player.mediaPlayer.setPlaybackRate(-1 * self.video_player.mediaPlayer.playbackRate())
            elif self.spacebar_mode and event.key() == Qt.Key.Key_D:
                self.video_player.mediaPlayer.pause()

            elif event.key() == Qt.Key.Key_Left:
                self.plotter_adjustable.left_timer.stop()
            elif event.key() == Qt.Key.Key_Right:
                self.plotter_adjustable.right_timer.stop()
            elif event.key() == Qt.Key.Key_Up:
                self.plotter_adjustable.zoom_in_timer.stop()
            elif event.key() == Qt.Key.Key_Down:
                self.plotter_adjustable.zoom_out_timer.stop()
            else:
                super().keyReleaseEvent(event)

    def set_marker_visibility(self, visible):
        self.plotter_adjustable.movement_start_marker.setVisible(visible)
        self.plotter_whole.movement_start_marker.setVisible(visible)

    def set_marker_value(self, val):
        self.plotter_adjustable.movement_start_marker.setValue(val)
        self.plotter_whole.movement_start_marker.setValue(val)


# def ms_to_iso8601(ms):
#     """
#     For displaying the timestamps in milliseconds in a readable format
#     """
#     s = ms / 1000.0
#     dt = datetime.fromtimestamp(s, tz=timezone.utc)
#     # return dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
#     return dt.strftime('%H:%M:%S.%f')[:-3]



class DataLoaderThread(QThread):
    data_loaded = pyqtSignal(tuple)

    def __init__(self):
        super().__init__()

    def run(self):
        from prototype2_setup import setup
        from Neurogram_short import Recording

        record = setup()

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

        self.data_loaded.emit((self.x, self.y))



class TimeAxisItem(AxisItem):
    def __init__(self, *args, **kwargs):
        super(TimeAxisItem, self).__init__(*args, **kwargs)

    def tickStrings(self, values, scale, spacing):
        return [time.strftime('%H:%M:%S', time.gmtime(val)) for val in values]



class HoldDownButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)

    def mouse_press_event(self, event):
        self.clicked.emit()
        QPushButton.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        self.released.emit()
        QPushButton.mouseReleaseEvent(self, event)


# class CustomViewBox(ViewBox):
#     def keyPressEvent(self, event):
#         # Check if the key is one you want to handle
#         if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right):
#             # Optionally call your custom handlers here
#             # For now, just ignore to suppress default behavior
#             event.ignore()
#         else:
#             super().keyPressEvent(event)
#
#     def keyReleaseEvent(self, event):
#         if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right):
#             event.ignore()
#         else:
#             super().keyReleaseEvent(event)

class ClickableLinearRegionItem(LinearRegionItem):
    regionSelected = pyqtSignal(object)

    def __init__(self, *args, **kwargs):
        super(ClickableLinearRegionItem, self).__init__(*args, **kwargs)
        self.setAcceptHoverEvents(True)

    def mouseClickEvent(self, event):
        self.regionSelected.emit(self)
        event.accept()

    def hoverEvent(self, event):
        # If this region is not the selected region, process hover events normally.
        if not Plotter.selected_region or Plotter.selected_region[1] is not self:
            super(ClickableLinearRegionItem, self).hoverEvent(event)

    def hoverEnterEvent(self, event):
        # If this region is not the selected region, process hover enter events normally.
        if not Plotter.selected_region or Plotter.selected_region[1] is not self:
            super(ClickableLinearRegionItem, self).hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        # If this region is not the selected region, process hover leave events normally.
        if not Plotter.selected_region or Plotter.selected_region[1] is not self:
            super(ClickableLinearRegionItem, self).hoverLeaveEvent(event)





class Plotter(QWidget):
    plot_widget_whole = None
    plot_widget_zoom = None
    data = None
    viewRect = QGraphicsRectItem()
    viewRect.setBrush(QBrush(QColor(255, 255, 255, 100)))
    sample_rate = 100

    timestamps = []
    new_timestamps = []
    interval_regions = {}
    selected_region = []
    selected_interval = None

    entries_to_delete = set()
    entries_to_change = {}

    x_o, y_o = None, None

    current_marker_whole = InfiniteLine(angle=90, movable=False, pen='r')
    current_marker_zoom = InfiniteLine(angle=90, movable=False, pen='r')

    def __init__(self, data, ylim):
        super().__init__()
        Plotter.data = data
        self.inner_layout = QVBoxLayout()
        self.lower_layout = QHBoxLayout()
        self.layout = QHBoxLayout()
        self.ylim = ylim

        Plotter.x_o, Plotter.y_o = data[0], data[1]
        self.x, self.y = self.x_o.copy(), self.y_o.copy()


        self.movement_start_marker = InfiniteLine(angle=90, movable=False, pen='#FF5C5C')

        self.layout.addLayout(self.inner_layout)
        self.setLayout(self.layout)

        self.movement_start_marker.setVisible(False)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)


    # def adjust_dataset_for_offset(self, offset_seconds):
    #     sample_rate = self.sample_rate
    #     offset_samples = int(offset_seconds * sample_rate)
    #
    #     if offset_samples > len(self.x_o):
    #         self.x = self.o_x[offset_samples:]
    #         self.y = self.o_y[offset_samples:]
    #     else:
    #         print("Offset exceeds the dataset's length")
    #
    #     self.plot_data_whole()
    #     self.plot_data_adjustable()



    def plot_data_whole(self):
        Plotter.plot_widget_whole = pg.PlotWidget(axisItems={'bottom': TimeAxisItem(orientation='bottom')})

        # Attempt to disable default key handling
        # view_box = Plotter.plot_widget_whole.getViewBox()
        # view_box.keyPressEvent = lambda event: None

        self.plot = Plotter.plot_widget_whole.plot(self.x, self.y)

        Plotter.plot_widget_whole.addItem(Plotter.current_marker_whole)
        Plotter.plot_widget_whole.addItem(self.movement_start_marker)
        width = self.x[-1]
        Plotter.viewRect.setRect(QRectF(0, -250, width, 500)) # Plotter.plot_widget_whole.plotItem.vb.height()))
        Plotter.plot_widget_whole.plotItem.vb.addItem(Plotter.viewRect)

        Plotter.plot_widget_whole.setYRange(-250, 250)

        self.inner_layout.addWidget(Plotter.plot_widget_whole)



    def plot_data_adjustable(self):

        Plotter.plot_widget_zoom = pg.PlotWidget(axisItems={'bottom': TimeAxisItem(orientation='bottom')})

        # Attempt to disable default key handling
        # view_box = Plotter.plot_widget_zoom.getViewBox()
        # view_box.keyPressEvent = lambda event: None

        self.plot = Plotter.plot_widget_zoom.plot(self.x, self.y)

        Plotter.plot_widget_zoom.addItem(Plotter.current_marker_zoom)
        Plotter.plot_widget_zoom.addItem(self.movement_start_marker)

        Plotter.plot_widget_zoom.sigRangeChanged.connect(self.update_view_rect_on_zoom)
        Plotter.plot_widget_zoom.scene().sigMouseClicked.connect(self.on_plot_clicked)

        Plotter.plot_widget_zoom.setYRange(-250, 250)

        Plotter.plot_widget_zoom.setMouseEnabled(x=True, y=False)

        Plotter.plot_widget_zoom.setXRange(0, self.x[-1], padding=0)  # Window range set to first 20 seconds

        # Button for moving to the left & right
        # self.left_button.clicked.connect(self.move_left)
        self.left_timer = QTimer()
        self.left_timer.timeout.connect(self.move_left)
        self.left_timer.setInterval(100)

        self.left_button = HoldDownButton()
        self.left_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowLeft))
        self.left_button.pressed.connect(self.left_timer.start)
        self.left_button.released.connect(self.left_timer.stop)



        # self.right_button.clicked.connect(self.move_right)
        self.right_timer = QTimer()
        self.right_timer.timeout.connect(self.move_right)
        self.right_timer.setInterval(100)

        self.right_button = HoldDownButton()
        self.right_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowRight))
        self.right_button.pressed.connect(self.right_timer.start)
        self.right_button.released.connect(self.right_timer.stop)

        self.zoom_in_timer = QTimer()
        self.zoom_in_timer.timeout.connect(self.zoom_in)
        self.zoom_in_timer.setInterval(50)

        self.zoom_out_timer = QTimer()
        self.zoom_out_timer.timeout.connect(self.zoom_out)
        self.zoom_out_timer.setInterval(50)


        self.inner_layout.addWidget(Plotter.plot_widget_zoom)
        self.lower_layout.addWidget(self.left_button)
        self.lower_layout.addWidget(self.right_button)

        self.inner_layout.addLayout(self.lower_layout)

        self.slider = QSlider(Qt.Orientation.Vertical)
        self.slider.setMinimum(1)
        self.slider.setMaximum(100)
        self.slider.setValue(1)


        self.slider.valueChanged.connect(self.update_zoom)

        self.layout.addWidget(self.slider)

        # For selecting regions to delete/edit
        # self.proxy = SignalProxy(Plotter.plot_widget_zoom.scene().sigMouseClicked, rateLimit=60, slot=self.on_plot_clicked)


    def update_view_rect(self, sliderPosition=None):
        viewRange = Plotter.plot_widget_zoom.viewRange()
        if not sliderPosition:
            x_start = viewRange[0][0]
        else:
            x_start = sliderPosition

        width = viewRange[0][1] - viewRange[0][0]
        height = 500
        # Update the rectangle's dimensions to match the visible range in the zoom plot
        Plotter.viewRect.setRect(QRectF(x_start, -250, width, height))


    # def update_zoom(self):
    #     zoom_factor = self.slider.value()
    #     max_zoom = self.x[-1]
    #     current_zoom = max_zoom / zoom_factor
    #     center_point = Plotter.plot_widget_zoom.plotItem.viewRange()[0][0] + current_zoom / 2
    #     Plotter.plot_widget_zoom.setXRange(center_point - current_zoom / 2, center_point + current_zoom / 2, padding=0)

    def update_zoom(self):
        zoom_factor = self.slider.value()
        data_min = self.x[0]  # Assuming self.x is sorted and represents your data range
        data_max = self.x[-1]

        current_view_range = Plotter.plot_widget_zoom.viewRange()[0]
        current_center = sum(current_view_range) / 2

        # Calculate new zoom based on the slider value
        current_zoom_width = (data_max - data_min) / zoom_factor
        new_start = current_center - current_zoom_width / 2
        new_end = current_center + current_zoom_width / 2

        # Check if new range goes beyond data boundaries and adjust if necessary
        if new_start < data_min:
            new_start = data_min
            new_end = new_start + current_zoom_width  # Adjust end to maintain zoom width
            # Ensure we don't exceed the data_max after adjustment
            new_end = min(new_end, data_max)

        if new_end > data_max:
            new_end = data_max
            new_start = new_end - current_zoom_width  # Adjust start to maintain zoom width
            # Ensure we don't go below data_min after adjustment
            new_start = max(new_start, data_min)

        # Update the plot range with the corrected values
        Plotter.plot_widget_zoom.setXRange(new_start, new_end, padding=0)

    def update_view_rect_on_zoom(self):
        self.update_view_rect()

    def calculate_movement(self, direction):
        view_range = Plotter.plot_widget_zoom.viewRange()[0]
        current_width = view_range[1] - view_range[0]
        move_step = current_width * 0.1

        if direction == "left":
            new_start = max(view_range[0] - move_step, self.x[0])
            new_end = new_start + current_width
        elif direction == "right":
            new_end = min(view_range[1] + move_step, self.x[-1])
            new_start = new_end - current_width

        Plotter.plot_widget_zoom.setXRange(new_start, new_end, padding=0)


    def on_plot_clicked(self, event):
        # print(event)
        # print(type(event))
        # print("event.pos():", event.pos())
        pos = event.pos()
        # if not Plotter.selected_interval:
        for itv, reg in Plotter.interval_regions.items():
            if reg[1].getRegion()[0] < pos.x() < reg[1].getRegion()[1]:  # regions can only be selected from the zoomable plot, hence reg[1]
                self.selected_interval = itv
                self.select_region(itv)


    def move_left(self):
        self.calculate_movement('left')

    def move_right(self):
        self.calculate_movement('right')


    def zoom_in(self):
        self.slider.setValue(self.slider.value() + 1)

    def zoom_out(self):
        self.slider.setValue(self.slider.value() - 1)


    @classmethod
    def update_marker(cls, position):
        time_in_seconds = position / 1000
        cls.current_marker_whole.setValue(time_in_seconds)
        cls.current_marker_zoom.setValue(time_in_seconds)


    # @classmethod
    # def adjust_data_offset(cls, offset):
    #     print(f"New offset is {offset} seconds")
    #     cls.current_marker_whole.setValue(cls.current_marker_whole.value() + offset)
    #     cls.current_marker_zoom.setValue(cls.current_marker_zoom.value() + offset)
    #
    #     for itv, reg in cls.interval_regions:
    #         start, end = reg.getRegion()
    #         reg.setRegion((start + offset, end + offset))


    @classmethod
    def select_region(cls, itv):
        if cls.selected_region:
            # colour = MovementTypeDialog.colours[itv[-1]]
            cls.deselect_region()
        else:
            cls.selected_interval = itv
            cls.selected_region = Plotter.interval_regions[itv]
            selected_region_brush = QBrush(QColor(0, 255, 0, 50))
            cls.selected_region[0].setBrush(selected_region_brush)
            cls.selected_region[1].setBrush(selected_region_brush)
            cls.selected_region[0].update()
            cls.selected_region[1].update()
            window.change_category_action.setEnabled(True)

    @classmethod
    def deselect_region(cls):
        # default_brush = QBrush(QColor(0, 0, 255, 50))
        # cls.selected_region[0].setBrush(default_brush)
        # cls.selected_region[1].setBrush(default_brush)
        colour = QBrush(MovementTypeDialog.colours[cls.selected_interval[2]])
        cls.selected_region[0].setBrush(colour)
        cls.selected_region[1].setBrush(colour)
        cls.selected_region[0].update()
        cls.selected_region[1].update()
        cls.selected_region = None
        cls.selected_interval = None

        window.change_category_action.setEnabled(False)

    @classmethod
    def add_region(cls, itv):
        region_whole = ClickableLinearRegionItem(values=itv)
        region_zoom = ClickableLinearRegionItem(values=itv)
        brush = QBrush(QColor(MovementTypeDialog.colours[itv[2]]))
        region_whole.setBrush(brush)
        region_zoom.setBrush(brush)
        region = [region_whole, region_zoom]
        cls.interval_regions[itv] = region

        # region[1].regionSelected.connect(cls.selected_region)

        if window.show_ma_action.isChecked():
            cls.plot_widget_whole.addItem(region[0])
            cls.plot_widget_zoom.addItem(region[1])
            print("Region Added, interval:", itv)

    @classmethod
    def delete_region(cls):
        if cls.selected_region:
            cls.plot_widget_whole.removeItem(cls.selected_region[0])
            cls.plot_widget_zoom.removeItem(cls.selected_region[1])
            cls.entries_to_delete.add(cls.selected_interval)
            del cls.interval_regions[cls.selected_interval]
            cls.selected_region = None
            cls.selected_interval = None


    @classmethod
    def display_intervals(cls):
        for region in cls.interval_regions.values():
            cls.plot_widget_whole.addItem(region[0])
            cls.plot_widget_zoom.addItem(region[1])


    @classmethod
    def clear_intervals(cls):
        for region in cls.interval_regions.values():
            cls.plot_widget_whole.removeItem(region[0])
            cls.plot_widget_zoom.removeItem(region[1])


    @classmethod
    def delete_selected_interval(cls):
        if cls.selected_region:
            Plotter.plot_widget_whole.removeItem(cls.selected_region[0])
            Plotter.plot_widget_zoom.removeItem(cls.selected_region[1])
            interval_to_remove = None
            for itv, region in Plotter.interval_regions.items():
                if region == cls.selected_region:
                    interval_to_remove = itv
                break
            if interval_to_remove:
                del cls.interval_regions[interval_to_remove]
            cls.selected_region = None

    @classmethod
    def keyPressEvent(cls, event):
        if cls.selected_region and event.key() == Qt.Key.Key_Delete:
            cls.delete_selected_interval()

    @classmethod
    def reset_class_attributes(cls):
        cls.plot_widget_whole = None
        cls.plot_widget_zoom = None
        cls.data = None
        cls.viewRect = QGraphicsRectItem()
        cls.viewRect.setBrush(QBrush(QColor(255, 255, 255, 100)))
        cls.sample_rate = 100

        cls.timestamps = []
        cls.new_timestamps = []
        cls.interval_regions = {}
        cls.selected_region = []
        cls.selected_interval = None

        cls.entries_to_delete = set()

    @classmethod
    def change_category(cls):
        if cls.selected_region:
            dialog = MovementTypeDialog()
            if dialog.exec():
                category = dialog.get_selected_category()
                cat = MovementTypeDialog.categories[category]  # Short 1-letter code for categories
                brush = QBrush(QColor(MovementTypeDialog.colours[cat]))

                new_interval = (cls.selected_interval[0], cls.selected_interval[1], cat)

                cls.selected_region[0].setBrush(brush)
                cls.selected_region[1].setBrush(brush)
                new_regions = tuple([cls.selected_region[0], cls.selected_region[1]])
                cls.entries_to_change[cls.selected_interval] = cat
                del cls.interval_regions[cls.selected_interval]
                cls.interval_regions[new_interval] = new_regions
                cls.deselect_region(brush)
            window.change_category_action.setEnabled(True)

    @classmethod
    def adjust_plot_objects(cls, offset):
        print(f"New offset is {offset} seconds")

        cls.current_marker_whole.setValue(window.video_player.mediaPlayer.position() / 1000 + offset)
        cls.current_marker_zoom.setValue(window.video_player.mediaPlayer.position() / 1000 + offset)

        for itv, reg in cls.interval_regions.items():
            start_0, end_0 = window.offset_adjuster.interval_regions_original[itv][0]
            start_1, end_1 = window.offset_adjuster.interval_regions_original[itv][1]
            reg[0].setRegion((start_0 + offset, end_0 + offset))
            reg[1].setRegion((start_1 + offset, end_1 + offset))

    #
    @classmethod
    def redraw_plots_with_offset(cls, offset_to_apply):
        index_offset = int(offset_to_apply * cls.sample_rate)

        print("Offset to apply:", offset_to_apply)
        print("Index offset:", index_offset)
        if index_offset == 0:
            cls.plot_widget_whole.clear()
            cls.plot_widget_whole.plot(cls.x_o, cls.y_o)
            cls.plot_widget_whole.addItem(cls.current_marker_whole)
            cls.plot_widget_whole.addItem(window.plotter_whole.movement_start_marker)

            cls.plot_widget_zoom.clear()
            cls.plot_widget_zoom.plot(cls.x_o, cls.y_o)
            cls.plot_widget_zoom.addItem(cls.current_marker_zoom)
            cls.plot_widget_zoom.addItem(window.plotter_adjustable.movement_start_marker)


        else:
            print("Else statement!")
            cls.plot_widget_whole.clear()
            cls.plot_widget_whole.plot(cls.x_o[:-index_offset], cls.y_o[index_offset:])
            cls.plot_widget_whole.addItem(cls.current_marker_whole)
            cls.plot_widget_whole.addItem(window.plotter_whole.movement_start_marker)

            cls.plot_widget_zoom.clear()
            cls.plot_widget_zoom.plot(cls.x_o[:-index_offset], cls.y_o[index_offset:])
            cls.plot_widget_zoom.addItem(cls.current_marker_zoom)
            cls.plot_widget_zoom.addItem(window.plotter_adjustable.movement_start_marker)

        if window.show_ma_action.isChecked():
            cls.display_intervals()

        for itv, reg in cls.interval_regions.items():
            if reg[0].getRegion()[1] - offset_to_apply < 0:
                cls.select_region(itv)
                cls.delete_selected_interval()
                continue

            start_0, end_0 = reg[0].getRegion()
            start_1, end_1 = reg[1].getRegion()
            start_0, start_1 = max(0, start_0 - index_offset), max(0, start_1 - index_offset)
            end_0, end_1 = end_0 - index_offset, end_1 - index_offset
            reg[0].setRegion((start_0, end_0))
            reg[1].setRegion((start_1, end_1))

    @classmethod
    def redraw_original_plots(cls, offset_to_apply):
        OffsetAdjuster.cancel()
        OffsetAdjuster.offset = 0
        OffsetAdjuster.offset_to_apply = 0
        index_offset = int(offset_to_apply * cls.sample_rate)

        cls.plot_widget_whole.clear()
        cls.plot_widget_whole.plot(cls.x_o, cls.y_o)
        cls.plot_widget_whole.addItem(cls.current_marker_whole)
        cls.plot_widget_whole.addItem(window.plotter_whole.movement_start_marker)

        cls.plot_widget_zoom.clear()
        cls.plot_widget_zoom.plot(cls.x_o, cls.y_o)
        cls.plot_widget_zoom.addItem(cls.current_marker_zoom)
        cls.plot_widget_zoom.addItem(window.plotter_adjustable.movement_start_marker)

        if window.show_ma_action.isChecked():
            cls.display_intervals()

        for itv, reg in cls.interval_regions.items():
            start_0, end_0 = reg[0].getRegion()
            start_1, end_1 = reg[1].getRegion()
            start_0, start_1 = start_0 + index_offset, start_1 + index_offset
            end_0, end_1 = end_0 + index_offset, end_1 + index_offset
            reg[0].setRegion((start_0, end_0))
            reg[1].setRegion((start_1, end_1))

    @classmethod
    def clear_movement_data(cls):
        cls.clear_intervals()
        for itv in cls.interval_regions.keys():
            cls.entries_to_delete.add(itv)
        cls.interval_regions = {}



class MovementTypeDialog(QDialog):

    categories = {
        'Stationary + clean': 's',
        'Moving': 'm',
        'Eating': 'e',
        'Chewing': 'c'
    }

    colours = {
        's': QColor(127, 88, 175, 100),#'#FE218B32',
        'm': QColor(100, 197, 235, 100),#'#FED70032',
        'e': QColor(232, 77, 138, 100),#'#21B0FE32',
        'c': QColor(254, 179, 38, 100)#'#0000FF32'
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Movement Type")
        self.selected_category = None

        layout = QVBoxLayout()

        for cat in self.categories:
            btn = QPushButton(cat, self)
            btn.clicked.connect(lambda checked, category=cat: self.select_category(category))
            layout.addWidget(btn)

        self.setLayout(layout)

    def select_category(self, category):
        self.selected_category = category
        self.accept()

    def get_selected_category(self):
        return self.selected_category




class OffsetAdjuster(QDialog):
    # offset_changed = pyqtSignal(float)
    offset = 0
    offset_to_apply = 0
    offset_dial = QDial()

    def __init__(self, max_offset=60): # in seconds
        super().__init__()
        self.max_offset = max_offset
        # self.current_offset_seconds = 0
        # self.total_offset_degrees = 0

        # self.interval_regions_original = copy.deepcopy(Plotter.interval_regions)
        self.interval_regions_original = {}
        for itv, reg in Plotter.interval_regions.items():
            region_copy = [reg[0].getRegion(), reg[1].getRegion()]
            self.interval_regions_original[itv] = region_copy

        # self.original_offset = 0

        self.init_ui()


    def init_ui(self):
        print(f"\n\n\nInitialising UI\n\n\nOffset:{OffsetAdjuster.offset}\n{OffsetAdjuster.offset_to_apply}")
        Plotter.redraw_original_plots(OffsetAdjuster.offset_to_apply)

        self.layout = QVBoxLayout()
        self.options_layout = QHBoxLayout()

        self.info_label = QLabel(f"Current Offset: {OffsetAdjuster.offset_to_apply} seconds")
        self.layout.addWidget(self.info_label)

        OffsetAdjuster.offset_dial.setWrapping(False)
        OffsetAdjuster.offset_dial.setNotchesVisible(True)
        OffsetAdjuster.offset_dial.valueChanged.connect(self.on_dial_changed)
        OffsetAdjuster.offset_dial.setMinimum(0)
        # self.offset_dial.setValue(0)
        OffsetAdjuster.offset_dial.setValue(int(OffsetAdjuster.offset_to_apply * 1000))
        OffsetAdjuster.offset_dial.setMaximum(self.max_offset * 1000)

        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply)
        self.reset_button = QPushButton("Reset")
        self.reset_button.clicked.connect(Plotter.redraw_original_plots)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel)

        self.options_layout.addWidget(self.apply_button)
        self.options_layout.addWidget(self.reset_button)
        self.options_layout.addWidget(self.cancel_button)

        self.layout.addWidget(OffsetAdjuster.offset_dial)
        self.layout.addLayout(self.options_layout)
        self.setLayout(self.layout)



    def on_dial_changed(self, value):
        OffsetAdjuster.offset = value / 1000.0 #- self.original_offset
        self.info_label.setText(f"Current Offset: {OffsetAdjuster.offset} seconds")
        Plotter.adjust_plot_objects(OffsetAdjuster.offset)

    def apply(self):
        OffsetAdjuster.offset_to_apply = OffsetAdjuster.offset
        Plotter.redraw_plots_with_offset(OffsetAdjuster.offset_to_apply)
        Plotter.adjust_plot_objects(0)
        self.accept()
    # def dial_moved(self, value):
    #     delta_degrees = value - (self.total_offset_degrees % 360)
    #     if delta_degrees > 180:
    #         delta_degrees -= 360
    #     elif delta_degrees < -180:
    #         delta_degrees += 360
    #
    #     self.total_offset_degrees += delta_degrees
    #     new_offset_seconds = round(self.total_offset_degrees / 36, 3)    # 10 seconds per full spin
    #
    #     if new_offset_seconds < 0:
    #         new_offset_seconds = 0
    #     elif new_offset_seconds > self.max_offset:
    #         new_offset_seconds = self.max_offset
    #
    #     if self.current_offset_seconds != new_offset_seconds:
    #         self.current_offset_seconds = new_offset_seconds
    #         self.info_label.setText(f"Current Offset: {self.current_offset_seconds} seconds")
    #         self.offset_changed.emit(self.current_offset_seconds)
    def cancel(self):
        OffsetAdjuster.offset_dial.setValue(int(OffsetAdjuster.offset_to_apply * 1000))
        Plotter.adjust_plot_objects(0)
        self.reject()

    # def reset(self):
    #     self.current_offset_seconds = 0
    #     self.total_offset_seconds = 0
    #     self.info_label.setText(f"Current Offset: {self.current_offset_seconds} seconds")
    #     self.offset_dial.setValue(0)

    def closeEvent(self, event):
        self.cancel()



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
            if window.plotter_adjustable and window.plotter_whole:
                window.adjust_offset_action.setEnabled(True)
            # self.mediaPlayer.play()

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



app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec())

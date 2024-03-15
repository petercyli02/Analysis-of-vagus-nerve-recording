import csv
import sys, os
from datetime import datetime, timezone

from PyQt6.QtGui import QBrush, QColor, QAction
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QHBoxLayout, QSlider, \
    QGraphicsRectItem, QStyle, QToolBar, QCheckBox, QFileDialog
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QUrl, QThread, pyqtSignal, QRectF, QTimer, QSize, QDateTime
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import pyqtgraph as pg
from pyqtgraph import AxisItem, ImageItem, InfiniteLine, PlotDataItem, ViewBox, LinearRegionItem, SignalProxy
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
        self.file_menu.addAction(load_video_action)
        load_data_action = QAction("Load Signal Data", self)
        load_data_action.triggered.connect(self.on_plot_data_button_clicked)
        self.file_menu.addAction(load_data_action)
        open_artifact_file_action = QAction("Load Movement Data")
        open_artifact_file_action.triggered.connect(self.load_movement_data)
        self.file_menu.addAction(open_artifact_file_action)
        self.save_action = QAction("Save", self)
        self.save_action.triggered.connect(self.save)
        self.save_action.setEnabled(False)
        self.file_menu.addAction(self.save_action)
        save_as_action = QAction("Save As", self)
        save_as_action.triggered.connect(self.save_as)
        self.file_menu.addAction(save_as_action)
        new_window

        self.settings_menu = self.menu_bar.addMenu("&Settings")

        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setIconSize(QSize(50, 50))
        self.addToolBar(self.toolbar)

        self.show_ma_action = QAction("Show Movement Windows", self)
        self.toolbar.addAction(self.show_ma_action)
        self.show_ma_action.setCheckable(True)
        self.show_ma_action.setChecked(True)
        self.show_ma_action.toggled.connect(self.toggle_show_ma)
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

    def load_movement_data(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Load Movement Intervals", "", "CSV (*.csv)")
        self.current_file = filepath
        with open(filepath, "r") as file:
            reader = csv.reader(file)
            for row in reader:
                # self.timestamps.append((row[0], row[1]))
                Plotter.interval_regions[(row[0], row[1])] = [ClickableLinearRegionItem(values=[(row[0], row[1])]), ClickableLinearRegionItem(values=[(row[0], row[1])])]

    def save(self):
        with open(self.current_file, 'a' if self.current_file else 'w', newline='') as file:
            writer = csv.writer(file)
            for start, end in Plotter.new_timestamps:
                # writer.writerow([start.toString(Qt.ISODateWithMs), end.toString(Qt.ISODateWithMs)])
                writer.writerow([start, end])
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
        self.loading_label.setText("Loading Data...")
        self.plot_data_button.setEnabled(False)

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
                self.video_player.mediaPlayer.play()
                self.movement_end = self.video_player.mediaPlayer.position() / 1000  # .position() gives the timestamp in milliseconds
                if self.movement_end > self.movement_start:
                    itv = (self.movement_start, self.movement_end)
                    Plotter.timestamps.append(itv)
                    Plotter.new_timestamps.append(itv)
                    Plotter.add_region(itv)
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


def ms_to_iso8601(ms):
    """
    For displaying the timestamps in milliseconds in a readable format
    """
    s = ms / 1000.0
    dt = datetime.fromtimestamp(s, tz=timezone.utc)
    # return dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    return dt.strftime('%H:%M:%S.%f')[:-3]



class DataLoaderThread(QThread):
    data_loaded = pyqtSignal(tuple)

    def __init__(self):
        super().__init__()

    def run(self):
        # Import my own functions
        from prototype2_setup import record
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
        if  not Plotter.selected_region or Plotter.selected_region[1] is not self:
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

    def __init__(self, data, ylim):
        super().__init__()
        Plotter.data = data
        self.inner_layout = QVBoxLayout()
        self.layout = QHBoxLayout()
        self.ylim = ylim
        self.x, self.y = data[0], data[1]

        self.current_marker = InfiniteLine(angle=90, movable=False, pen='r')
        self.movement_start_marker = InfiniteLine(angle=90, movable=False, pen='#FF5C5C')

        self.layout.addLayout(self.inner_layout)
        self.setLayout(self.layout)

        self.movement_start_marker.setVisible(False)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)



    def plot_data_whole(self):
        Plotter.plot_widget_whole = pg.PlotWidget(axisItems={'bottom': TimeAxisItem(orientation='bottom')})

        # Attempt to disable default key handling
        # view_box = Plotter.plot_widget_whole.getViewBox()
        # view_box.keyPressEvent = lambda event: None

        self.plot = Plotter.plot_widget_whole.plot(self.x, self.y)

        Plotter.plot_widget_whole.addItem(self.current_marker)
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

        Plotter.plot_widget_zoom.addItem(self.current_marker)
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
        self.lower_layout = QHBoxLayout()
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

    def update_marker(self, position):
        time_in_seconds = position / 1000

        self.current_marker.setValue(time_in_seconds)


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
        for itv, reg in Plotter.interval_regions.items():
            if reg[1].getRegion()[0] < pos.x() < reg[1].getRegion()[1]:  # regions can only be selected from the zoomable plot, hence reg[1]
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
    def select_region(cls, itv):
        if cls.selected_region:
            cls.deselect_region()

        cls.selected_region = Plotter.interval_regions[itv]
        selected_region_brush = QBrush(QColor(0, 255, 0, 50))
        cls.selected_region[0].setBrush(selected_region_brush)
        cls.selected_region[1].setBrush(selected_region_brush)
        cls.selected_region[0].update()
        cls.selected_region[1].update()

    @classmethod
    def deselect_region(cls):
        default_brush = QBrush(QColor(0, 0, 255, 50))
        cls.selected_region[0].setBrush(default_brush)
        cls.selected_region[1].setBrush(default_brush)
        cls.selected_region[0].update()
        cls.selected_region[1].update()
        cls.selected_region = None
        cls.selected_interval = None



    @classmethod
    def add_region(cls, itv):
        region = [ClickableLinearRegionItem(values=itv), ClickableLinearRegionItem(values=itv)]
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

    # @classmethod
    # def mousePressEvent(self, event):
    #     pos = event[0].scenePos()
    #     #
    #     # for region in Plotter.interval_regions.values():
    #     #     if region[1].getRegion()[0] < pos.x() < region[1].getRegion()[1]:
    #     #         self.select_region(region)
    #     #         return
    #
    #     for itv, reg in Plotter.interval_regions.items():
    #         if reg[0].getRegion()[0] < pos.x() < reg[0].getRegion()[1]:  # regions can only be selected from the zoomable plot, hence reg[1]
    #             self.select_region(itv)


app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec())
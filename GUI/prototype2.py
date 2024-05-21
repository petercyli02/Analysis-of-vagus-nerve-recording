import copy
import csv
import json
import subprocess
import sys, os
from datetime import datetime, timezone

import pandas as pd
import pyqtgraph
from numpy.typing import NDArray

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

from Data_Loading import Recording
from additional_functions import convertDfType


# Add the parent directory to sys.path
current_script_path = os.path.dirname(__file__)

parent_dir = os.path.abspath(os.path.join(current_script_path, os.pardir))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)
sys.path.append(parent_dir)



class MainWindow(QMainWindow):
    signal_filepath = None

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Video and Data Plotter")

        self.setGeometry(100, 100, 400, 800)

        self.top_layout = QVBoxLayout()
        self.bottom_layout = QHBoxLayout()
        self.bottom_left_layout = QVBoxLayout()
        self.bottom_centre_layout = QVBoxLayout()
        self.bottom_right_layout = QVBoxLayout()

        self.bottom_centre_top_layout = QVBoxLayout()
        self.bottom_centre_bottom_layout = QHBoxLayout()

        self.plotter_adjustable = None
        self.plotter_whole = None

        # For sliding horizontal on the adjustable plot

        self.video_player = VideoPlayer()
        self.plot_data_button = QPushButton("Plot Data")
        self.plot_data_button.clicked.connect(self.on_plot_data_button_clicked)

        self.loading_label = QLabel("\n\n\n\n\n\nLoading Data...")
        self.loading_label.setVisible(False)

        self.top_layout.addWidget(self.video_player)
        self.bottom_centre_top_layout.addWidget(self.plot_data_button)
        self.bottom_centre_top_layout.addWidget(self.loading_label)

        self.main_layout = QVBoxLayout()
        self.main_layout.addLayout(self.top_layout, 1)
        self.main_layout.addLayout(self.bottom_layout, 1)
        self.bottom_layout.addLayout(self.bottom_left_layout, 0)
        self.bottom_layout.addLayout(self.bottom_centre_layout, 10)
        self.bottom_layout.addLayout(self.bottom_right_layout, 0)
        self.bottom_centre_layout.addLayout(self.bottom_centre_top_layout, 11)
        self.bottom_centre_layout.addLayout(self.bottom_centre_bottom_layout, 1)

        self.slider = QSlider(Qt.Orientation.Vertical)
        self.slider.setMinimum(1)
        self.slider.setMaximum(100)
        self.slider.setValue(1)

        self.slider.setVisible(False)

        self.bottom_right_layout.addWidget(self.slider)

        self.central_widget = QWidget()
        self.central_widget.setLayout(self.main_layout)
        self.setCentralWidget(self.central_widget)

        # Adding a toolbar and a menu bar
        self.menu_bar = self.menuBar()

        self.file_menu = self.menu_bar.addMenu("&File")
        self.load_video_action = QAction("Load Video", self)
        self.load_video_action.triggered.connect(self.video_player.openFile)
        self.file_menu.addAction(self.load_video_action)
        self.load_data_action = QAction("Load Signal Data", self)
        self.load_data_action.triggered.connect(self.on_plot_data_button_clicked)
        self.file_menu.addAction(self.load_data_action)
        self.open_artifact_file_action = QAction("Load Movement Data", self)
        self.open_artifact_file_action.triggered.connect(self.load_movement_data)
        self.file_menu.addAction(self.open_artifact_file_action)
        self.save_action = QAction("Save", self)
        self.save_action.triggered.connect(self.save)
        self.save_action.setEnabled(False)
        self.file_menu.addAction(self.save_action)
        self.save_as_action = QAction("Save As", self)
        self.save_as_action.triggered.connect(self.save_as)
        self.file_menu.addAction(self.save_as_action)
        self.load_glucose_action = QAction("Load Glucose Data", self)
        self.load_glucose_action.triggered.connect(self.load_glucose_plot)
        self.file_menu.addAction(self.load_glucose_action)
        self.load_glucose_action.setEnabled(False)

        self.settings_menu = self.menu_bar.addMenu("&Settings")
        self.settings_menu.setEnabled(False)
        self.settings_menu.setToolTip("To be developed - will enable editing of movement speed, region colours, default ylims etc")

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
        self.reset_action = QAction("Clear Category Data")
        self.reset_action.setEnabled(False)
        self.reset_action.triggered.connect(Plotter.clear_data)
        self.toolbar.addAction(self.reset_action)
        self.toggle_glucose_action = QAction("Show Glucose Data")
        self.toggle_glucose_action.setEnabled(False)
        self.toggle_glucose_action.triggered.connect(self.toggle_glucose_data)
        self.toolbar.addAction(self.toggle_glucose_action)

        self.glucose_plotter_whole = None

        # So that the KeyPressEvent and KeyReleaseEvent overrides work fine
        self.plotter_adjustable = None

        # Saving the timestamps:
        self.movement_start, self.movement_end = None, None
        self.current_file = None

        # Creating an indicator for if the spacebar is held down
        self.spacebar_mode = False
        self.rewind_speed = 200  # Each time A is pressed, rewind by ___ milliseconds

        self.xlim_vagus = [0, 0]

        self.left_timer = QTimer()
        self.left_timer.timeout.connect(Plotter.move_left)
        self.left_timer.setInterval(100)

        self.left_button = HoldDownButton()
        self.left_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowLeft))
        self.left_button.pressed.connect(self.left_timer.start)
        self.left_button.released.connect(self.left_timer.stop)

        self.right_timer = QTimer()
        self.right_timer.timeout.connect(Plotter.move_right)
        self.right_timer.setInterval(100)

        self.right_button = HoldDownButton()
        self.right_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowRight))
        self.right_button.pressed.connect(self.right_timer.start)
        self.right_button.released.connect(self.right_timer.stop)

        self.bottom_centre_bottom_layout.addWidget(self.left_button)
        self.bottom_centre_bottom_layout.addWidget(self.right_button)
        self.left_button.setVisible(False)
        self.right_button.setVisible(False)

        # Initialising the data loader thread object
        self.data_loader_thread = DataLoaderThread()
        self.data_loader_thread.data_loaded.connect(self.on_data_loaded)

        self.rewind_timer = QTimer()
        self.rewind_timer.timeout.connect(self.rewind)
        self.rewind_timer.setInterval(100)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)


    def open_dialog(self):
        self.offset_adjuster = OffsetAdjuster(max_offset=60)
        self.offset_adjuster.exec()


    def open_offset_adjuster(self):
        if window.video_player.mediaPlayer.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            window.video_player.mediaPlayer.pause()
        self.open_dialog()


    def load_movement_data(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Load Movement Intervals", "", "CSV (*.csv)")
        self.current_file = filepath
        with open(filepath, "r") as file:
            reader = csv.reader(file)
            for row in reader:
                region_whole = ClickableLinearRegionItem(values=[float(row[0]), float(row[1])], brush=QBrush(QColor(MovementTypeDialog.colours[row[2]])))
                region_zoom = ClickableLinearRegionItem(values=[float(row[0]), float(row[1])], brush=QBrush(QColor(MovementTypeDialog.colours[row[2]])))
                Plotter.interval_regions[(row[0], row[1], row[2])] = [region_whole, region_zoom]
                if self.show_ma_action.isChecked(): # and Plotter.plot_widget_whole and Plotter.plot_widget_zoom:
                    Plotter.plot_widget_whole.addItem(region_whole)
                    Plotter.plot_widget_zoom.addItem(region_zoom)


    def save(self):
        intervals_to_write = set()
        try:
            with open(self.current_file, mode='r', newline='') as file:
                reader = csv.reader(file)
                for row in reader:
                    if tuple(row[:2]) in Plotter.entries_to_change:
                        intervals_to_write.add(Plotter.entries_to_change[tuple(row[:2])])
                    else:
                        intervals_to_write.add(tuple(row))
        except FileNotFoundError:
            pass
        for itv in Plotter.unsaved_intervals:
            intervals_to_write.add(itv)
        for itv in Plotter.entries_to_delete:
            if itv in intervals_to_write:
                intervals_to_write.remove(itv)
        with open(self.current_file, mode='w', newline='') as file:
            writer = csv.writer(file)
            for itv in intervals_to_write:
                writer.writerow(itv)
        Plotter.unsaved_intervals.clear()
        Plotter.entries_to_change.clear()
        Plotter.entries_to_delete.clear()


    def save_as(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "CSV (*.csv)")
        if file_path:
            if not file_path.endswith('.csv'):
                file_path += '.csv'
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
        MainWindow.signal_filepath, _ = QFileDialog.getOpenFileName(self, "Select previously stored data file", os.path.expanduser('~'),
                                                  "Pickle files (*.pkl)")

        if self.glucose_plotter_whole is not None:
            self.toggle_glucose_action.setEnabled(False)
            self.bottom_centre_top_layout.removeWidget(self.glucose_plotter_whole)
            self.glucose_plotter_whole.deleteLater()
            self.glucose_plotter_whole = None

        if not self.plotter_whole:
            self.plot_data_button.setEnabled(False)

        else:
            self.bottom_centre_top_layout.removeWidget(self.plotter_whole)
            self.plotter_whole.deleteLater()
            self.plotter_whole = None

            self.bottom_centre_top_layout.removeWidget(self.plotter_adjustable)
            self.plotter_adjustable.deleteLater()
            self.plotter_adjustable = None

            self.left_button.setVisible(False)
            self.right_button.setVisible(False)
            self.slider.setVisible(False)
            self.slider.setValue(1)

        self.data_loader_thread.start()
        self.loading_label.setVisible(True)


    def on_data_loaded(self, data):
        Plotter.reset_class_attributes()
        pg.setConfigOption('background', 'k')
        pg.setConfigOption('foreground', 'w')
        Plotter.x_o, Plotter.y_o = data[0], data[1]

        if self.plot_data_button is not None:
            self.bottom_centre_top_layout.removeWidget(self.plot_data_button)
            self.plot_data_button.deleteLater()
            self.plot_data_button = None

        self.plot_data_whole(data, ylim=(-250, 250))
        self.plot_data_adjustable(data, ylim=(-250, 250))

        self.loading_label.setVisible(False)

        if self.video_player.mediaPlayer.source is not None:
            self.adjust_offset_action.setEnabled(True)

        self.slider.setVisible(True)
        self.reset_action.setEnabled(True)


    def plot_data_whole(self, data, ylim=None):
        if not self.plotter_whole:
            self.plotter_whole = Plotter(data, ylim)
        self.video_player.mediaPlayer.positionChanged.connect(Plotter.update_marker)
        self.plotter_whole.plot_data_whole()
        self.bottom_centre_top_layout.addWidget(self.plotter_whole)
        self.bottom_centre_top_layout.setStretch(0, 1)


    def plot_data_adjustable(self, data, ylim=None):
        if not self.plotter_adjustable:
            self.plotter_adjustable = Plotter(data, ylim)
        self.xlim_vagus = [data[0][0], data[0][-1]]
        self.video_player.mediaPlayer.positionChanged.connect(Plotter.update_marker)
        self.plotter_adjustable.plot_data_adjustable()
        self.bottom_centre_top_layout.addWidget(self.plotter_adjustable)
        self.bottom_centre_top_layout.setStretch(0, 1)
        self.slider.valueChanged.connect(self.plotter_adjustable.update_zoom)
        self.left_button.setVisible(True)
        self.right_button.setVisible(True)
        self.load_glucose_action.setEnabled(True)


    def toggle_glucose_data(self):
        visibility = self.glucose_plotter_whole.isVisible()
        self.glucose_plotter_whole.setVisible(not visibility)


    def load_glucose_plot(self):
        if self.glucose_plotter_whole is not None:
            self.bottom_centre_top_layout.removeWidget(self.glucose_plotter_whole)
            self.glucose_plotter_whole.deleteLater()
            self.glucose_plotter_whole = None
        self.toggle_glucose_action.setEnabled(False)
        dialog_txt = "Select File Containing Glucose Data"
        filepath = QFileDialog.getOpenFileName(self, dialog_txt, os.path.expanduser('~'), "CSV Files (*.csv)")[0]
        data = []
        with open(filepath, 'r') as file:
            reader = csv.reader(file, delimiter=',')
            for row in reader:
                if float(row[0]) > window.xlim_vagus[1]:
                    break
                data.append(row)
        data = np.asfarray(data).T

        self.plot_glucose_whole(data)
        self.toggle_glucose_action.setEnabled(True)

    def plot_glucose_whole(self, data):
        self.glucose_plotter_whole = Plotter(data, ylim=(0, 200))
        self.video_player.mediaPlayer.positionChanged.connect(Plotter.update_marker)
        self.bottom_centre_top_layout.addWidget(self.glucose_plotter_whole)
        self.glucose_plotter_whole.plot_glucose_whole()
        self.glucose_plotter_whole.setVisible(True)

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
                self.rewind_timer.start()
                # self.video_player.mediaPlayer.setPosition(max(0, self.video_player.mediaPlayer.position() - self.rewind_speed))
                # if self.video_player.mediaPlayer.position() < 1000 * self.movement_start:
                #     self.movement_start = self.video_player.mediaPlayer.position() / 1000.0
                #     self.set_marker_value(self.video_player.mediaPlayer.position() / 1000.0)
            elif event.key() == Qt.Key.Key_P:
                self.video_player.play()
            elif event.key() == Qt.Key.Key_Left:
                self.left_timer.start()
            elif event.key() == Qt.Key.Key_Right:
                self.right_timer.start()
            elif event.key() == Qt.Key.Key_Up:
                self.plotter_adjustable.zoom_in_timer.start()
            elif event.key() == Qt.Key.Key_Down:
                self.plotter_adjustable.zoom_out_timer.start()
            elif Plotter.selected_region and event.key() == Qt.Key.Key_Delete:
                Plotter.delete_selected_interval()
            else:
                super().keyPressEvent(event)


    def keyReleaseEvent(self, event):
        if self.plotter_adjustable and self.plotter_whole and not event.isAutoRepeat():
            if self.spacebar_mode and event.key() == Qt.Key.Key_Space:
                self.spacebar_mode = False
                if self.video_player.mediaPlayer.isPlaying():
                    self.video_player.mediaPlayer.pause()
                self.movement_end = self.video_player.mediaPlayer.position() / 1000  # .position() gives the timestamp in milliseconds
                if self.movement_end > self.movement_start:
                    dialog = MovementTypeDialog()
                    if dialog.exec():
                        category = dialog.get_selected_category()
                        itv = (self.movement_start, self.movement_end, MovementTypeDialog.categories[category])
                        Plotter.unsaved_intervals.add(itv)
                        Plotter.add_region(itv)
                    self.video_player.mediaPlayer.play()
                else:
                    self.video_player.mediaPlayer.play()
                self.movement_start, self.movement_end = None, None
                self.set_marker_visibility(False)

            elif self.spacebar_mode and event.key() == Qt.Key.Key_A:
                self.rewind_timer.stop()
            elif self.spacebar_mode and event.key() == Qt.Key.Key_D:
                self.video_player.mediaPlayer.pause()

            elif event.key() == Qt.Key.Key_Left:
                self.left_timer.stop()
            elif event.key() == Qt.Key.Key_Right:
                self.right_timer.stop()
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

    def rewind(self):
        self.video_player.mediaPlayer.setPosition(max(0, self.video_player.mediaPlayer.position() - self.rewind_speed))
        if self.video_player.mediaPlayer.position() < 1000 * self.movement_start:
            self.movement_start = self.video_player.mediaPlayer.position() / 1000.0
            self.set_marker_value(self.video_player.mediaPlayer.position() / 1000.0)




class DataLoaderThread(QThread):
    data_loaded = pyqtSignal(tuple)

    def __init__(self):
        super().__init__()

    def run(self):
        # from prototype2_setup import setup
        # from Neurogram_short import Recording

        record = self.setup(MainWindow.signal_filepath)
        print("record.channels:")
        print(record.column_ch)
        channel = record.column_ch[0]
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

        options_filter = [
            "None",
            "butter",
            "fir"]  # Binomial Weighted Average Filter

        options_detection = [
            "get_spikes_threshCrossing",  # Ojo: get_spikes_threshCrossing needs detects also cardiac
            # spikes, so use cardiac_window. This method is slower
            "get_spikes_method",  # Python implemented get_spikes() method. Faster
            "so_cfar"]  # Smallest of constant false-alarm rate filter

        options_threshold = [
            "positive",
            "negative",
            "both_thresh"]
        # %%
        # Configure
        config_text = []
        record.apply_filter = options_filter[1]
        record.detect_method = options_detection[1]  # leave it to butter (option 1)
        record.thresh_type = options_threshold[0]  # do not use it for now
        # Select channel position/number in intan (not channel number in device)

        # record.channels = [5,8,13]  # Select the channels to use. E.g. 5,8,13 for the recording you have now. Include 'all' to select all the channels available
        # record.channels = channels

        # record.path = path
        # config_text = ['Load_from_file %s' % load_from_file, 'Filter: %s' % record.apply_filter,
        #                'Detection: %s' % record.detect_method, 'Threhold type: %s' % record.thresh_type,
        #                'Channels: %s' % record.channels, 'Downsampling: %s' % downsample]
        # config_text.append('Port %s' % (port))
        # config_text.append('Start %s, Dur: %s' % (start, dur))
        # config_text.append('Channels: %s' % record.channels)
        # Ramarkable timestamps (in sec)

        group = '1'

        print('SELECTED GENERAL CONFIGURATION:')
        print('Filter: %s' % record.apply_filter)
        print('Detection: %s' % record.detect_method)
        print('Threhold type: %s' % record.thresh_type)
        print('Channels: %s' % record.channels)
        print('-------------------------------------')

        record.select_channels(
            record.channels)  # keep_ch_loc=True if we want to display following the map. Otherwise follow the order provided by selected channels.
        print('map_array: %s' % record.map_array)
        print('ch_loc: %s' % record.ch_loc)
        print('filter_ch %s' % record.filter_ch)
        print('column_ch %s' % record.column_ch)
        # %%
        # Configure
        record.num_rows = 2  # int(round(len(record.filter_ch)/2)) # round(n_components/2)
        record.num_columns = 1  # int(len(record.filter_ch)-round(len(record.filter_ch)/2))+1
        # plot_ch = int(record.map_array[int(record.ch_loc[0])])
        plot_ch = int(record.column_ch[0])
        print(plot_ch)
        print(record.num_rows)
        print(record.num_columns)
        save_figure = True
        # %%
        # Gain
        gain = 1
        config_text.append('Gain: %s' % (gain))
        # %%
        # Maximum bpm
        bpm = 300
        record.set_bpm(bpm)  # General max bpm in rat HR. Current neurograms at 180bpm
        config_text.append('BPM: %s' % (bpm))
        # %%
        # Final Initialisations - no change

        # Initialize dataframe for results
        # ----------------------------------------------------
        record.rolling_metrics = pd.DataFrame()
        record.summary = pd.DataFrame(columns=['Max_spike_rate', 'Min_spike_rate',
                                               'Max_amplitude_sum', 'Min_amplitude_sum'])
        record.summary.index.name = 'channel'
        record.sig2noise = []  # To save the snr for each channel

        # Intialize dataframes for wavelet decomposition
        # ---------------------------------------------------
        neural_wvl = pd.DataFrame(columns=record.filter_ch)
        neural_wvl_denoised = pd.DataFrame(columns=record.filter_ch)
        other_wvl = pd.DataFrame(columns=record.filter_ch)
        substraction_wvl = pd.DataFrame(columns=record.filter_ch)
        # %%
        # Config for bandpass filter

        filt_config = {
            'W': [400, 4000],  # (max needs to be <fs/2 per Nyquist)
            'None': {},
            'butter': {
                'N': 9,  # The order of the filter
                'btype': 'bandpass',  # 'bandpass', #'hp'  #'lowpass'     # The type of filter.
            },
            'fir': {
                'n': 4,
            },
            'notch': {
                'quality_factor': 30,
            },
        }

        filt_config['butter']['Wn'] = filt_config['W']
        filt_config['butter']['fs'] = record.fs

        config_text.append('filt_config: %s' % json.dumps(filt_config))
        # %%
        # Apply filter

        # Configure
        time_start = time.time()
        signal2filter = record.recording  # The neural data imported via pkl file
        config_text.append('signal2filter: %s' % signal2filter.name)
        record.filter(signal2filter, record.apply_filter, **filt_config[record.apply_filter])
        # Change from float64 to float 16
        record.filtered = convertDfType(record.filtered, typeFloat='float32')
        # print(record.filtered.dtypes)
        print("Time elapsed: {} seconds".format(time.time() - time_start))

        print("\n\n\n\n\n")
        print("------------------------------------------------------")
        print("Setup Complete!")

        self.x = np.arange(0, len(self.x_range)) / self.sample_rate
        self.y = record.filtered['ch_%s' % channel][self.x_range]

        self.data_loaded.emit((self.x, self.y))

    def setup(self, filepath):
        print("Reading data from", filepath)
        neural = pd.read_pickle(filepath)
        print("Data read!")

        # Various parameters
        start = 0
        dur = None
        length = len(neural)
        map_array = self.get_map_array('../../datasets/map_linear.csv')
        channels = []

        # Check the file is a data file
        if neural.index.name == 'time':
            # Convert neural.index to HH:MM:SS format

            # Set time interval
            print(start)
            if dur is None:
                stop = len(neural)
            else:
                stop = int(start + dur)
            print('stop: %s' % stop)
            start = int(start)

            neural = neural.iloc[start:stop]

            # Get Sampling frequency
            fs = 1 / (neural['seconds'].iloc[2] - neural['seconds'].iloc[1])
            print(fs)

            # Downcast it type float64
            for col in neural.columns:
                if col.startswith('ch_'):
                    neural[col] = neural[col].astype('float32')
                    channels.append(col.replace('ch_', ''))
            print(channels)
            basename_without_ext = os.path.splitext(os.path.basename(filepath))[0]
        else:
            print('ERROR: You have selected a wrong file, try again')

        return Recording(neural=neural, fs=fs, length=length, map_array=map_array, filename=basename_without_ext, column_ch=channels)

    def get_map_array(self, map_path='../../datasets/map_linear.csv'):
        # path = '../../datasets/rat7&8/day2'
        # map_path = '../../datasets/map_linear.csv'

        map_array = pd.read_csv(map_path, header=None)
        map_array = map_array.to_numpy()
        map_array = map_array.flatten()

        try:
            np.shape(map_array)[0]
        except:
            print('If map_array is 1D, it needs to be a row. Transposing...')
            map_array = map_array.transpose()
        else:
            map_array = map_array
        return map_array



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



class ClickableLinearRegionItem(LinearRegionItem):
    regionSelected = pyqtSignal(object)

    def __init__(self, *args, **kwargs):
        super(ClickableLinearRegionItem, self).__init__(*args, **kwargs)
        self.setAcceptHoverEvents(True)
        self.setMovable(False)

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
    plot_widget_glucose = None
    data = None

    viewRect = QGraphicsRectItem()
    viewRect.setBrush(QBrush(QColor(255, 255, 255, 100)))

    @staticmethod
    def init_viewRect():
        Plotter.viewRect = QGraphicsRectItem()
        Plotter.viewRect.setBrush(QBrush(QColor(255, 255, 255, 100)))

    viewRect_glucose = QGraphicsRectItem()
    viewRect_glucose.setBrush(QBrush(QColor(0, 0, 0, 100)))
    sample_rate = 100

    # timestamps = []
    unsaved_intervals = set()
    interval_regions = {}
    selected_region = []
    selected_interval = None

    entries_to_delete = set()
    entries_to_change = {}

    valid_intervals = []   # In case of clicking on overlapping intervals
    prev_pos = None
    repeated_clicks = 0

    x_o, y_o = None, None

    current_marker_whole = InfiniteLine(angle=90, movable=False, pen='r')
    @staticmethod
    def init_current_marker_whole():
        Plotter.current_marker_whole = InfiniteLine(angle=90, movable=False, pen='r')

    current_marker_zoom = InfiniteLine(angle=90, movable=False, pen='r')
    @staticmethod
    def init_current_marker_zoom():
        Plotter.current_marker_zoom = InfiniteLine(angle=90, movable=False, pen='r')


    current_marker_glucose = InfiniteLine(angle=90, movable=False, pen='r')
    @staticmethod
    def init_current_marker_glucose():
        Plotter.current_marker_glucose = InfiniteLine(angle=90, movable=False, pen='r')

    @staticmethod
    def init_viewRect_glucose():
        Plotter.viewRect_glucose = QGraphicsRectItem()
        Plotter.viewRect_glucose.setBrush(QBrush(QColor(0, 0, 0, 100)))

    def __init__(self, data, ylim):
        super().__init__()
        Plotter.data = data
        self.inner_layout = QVBoxLayout()
        self.lower_layout = QHBoxLayout()
        self.layout = QHBoxLayout()
        self.ylim = ylim

        self.x, self.y = data[0], data[1]

        self.movement_start_marker = InfiniteLine(angle=90, movable=False, pen='#FF5C5C')

        self.setLayout(self.layout)

        self.movement_start_marker.setVisible(False)




    def plot_data_whole(self):
        Plotter.plot_widget_whole = pg.PlotWidget(axisItems={'bottom': TimeAxisItem(orientation='bottom')})
        self.plot = Plotter.plot_widget_whole.plot(self.x, self.y)
        # print("Checking Plotter.current_marker_whole:")
        # print(Plotter.current_marker_whole)
        # print(type(Plotter.current_marker_whole))
        # print("Checking plot_widget_whole:")
        # print(Plotter.plot_widget_whole)
        # print(type(Plotter.plot_widget_whole))
        Plotter.init_current_marker_whole()
        Plotter.plot_widget_whole.addItem(Plotter.current_marker_whole)
        Plotter.plot_widget_whole.addItem(self.movement_start_marker)
        width = self.x[-1]
        Plotter.init_viewRect()
        Plotter.viewRect.setRect(QRectF(0, -250, width, 500))
        Plotter.plot_widget_whole.plotItem.vb.addItem(Plotter.viewRect)

        Plotter.plot_widget_whole.setYRange(self.ylim[0],self.ylim[1])

        self.layout.addWidget(Plotter.plot_widget_whole)


    def plot_glucose_whole(self):
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        pen = pg.mkPen(width=5, color='k')
        Plotter.plot_widget_glucose = pg.PlotWidget(axisItems={'bottom': TimeAxisItem(orientation='bottom')})

        Plotter.init_current_marker_glucose()
        self.plot = Plotter.plot_widget_glucose.plot(self.x, self.y, pen=pen)
        Plotter.plot_widget_glucose.addItem(Plotter.current_marker_glucose)
        width = self.x[-1]
        Plotter.init_viewRect_glucose()
        Plotter.viewRect_glucose.setRect(QRectF(0, -250, width, 500))
        Plotter.plot_widget_glucose.plotItem.vb.addItem(Plotter.viewRect_glucose)

        Plotter.plot_widget_glucose.setYRange(self.ylim[0], self.ylim[1])

        self.layout.addWidget(Plotter.plot_widget_glucose)




    def plot_data_adjustable(self):
        Plotter.plot_widget_zoom = pg.PlotWidget(axisItems={'bottom': TimeAxisItem(orientation='bottom')})
        self.plot = Plotter.plot_widget_zoom.plot(self.x, self.y)

        Plotter.init_current_marker_zoom()

        Plotter.plot_widget_zoom.addItem(Plotter.current_marker_zoom)
        Plotter.plot_widget_zoom.addItem(self.movement_start_marker)

        Plotter.plot_widget_zoom.sigRangeChanged.connect(self.update_view_rect_on_zoom)
        Plotter.plot_widget_zoom.scene().sigMouseClicked.connect(self.on_plot_clicked)

        Plotter.plot_widget_zoom.setYRange(self.ylim[0],self.ylim[1])

        Plotter.plot_widget_zoom.setMouseEnabled(x=True, y=False)

        Plotter.plot_widget_zoom.setXRange(0, self.x[-1], padding=0)  # Window range set to first 20 seconds

        self.zoom_in_timer = QTimer()
        self.zoom_in_timer.timeout.connect(self.zoom_in)
        self.zoom_in_timer.setInterval(50)

        self.zoom_out_timer = QTimer()
        self.zoom_out_timer.timeout.connect(self.zoom_out)
        self.zoom_out_timer.setInterval(50)

        self.layout.addWidget(Plotter.plot_widget_zoom)


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
        Plotter.viewRect_glucose.setRect(QRectF(x_start, -250, width, height))


    def update_zoom(self):
        zoom_factor = window.slider.value()
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

    @classmethod
    def calculate_movement(cls, direction):
        view_range = Plotter.plot_widget_zoom.viewRange()[0]
        current_width = view_range[1] - view_range[0]
        move_step = current_width * 0.1

        if direction == "left":
            new_start = max(view_range[0] - move_step, window.xlim_vagus[0])
            new_end = new_start + current_width
        elif direction == "right":
            new_end = min(view_range[1] + move_step, window.xlim_vagus[1])
            new_start = new_end - current_width

        Plotter.plot_widget_zoom.setXRange(new_start, new_end, padding=0)


    def on_plot_clicked(self, event):
        if Plotter.selected_interval:
            Plotter.deselect_region()
        else:
            pos = event.pos()
            if Plotter.valid_intervals and pos == Plotter.prev_pos:
                itv = Plotter.valid_intervals[Plotter.repeated_clicks % len(Plotter.valid_intervals)]
                self.selected_interval = itv
                self.select_region(itv)
                Plotter.repeated_clicks += 1
            else:
                Plotter.prev_pos = pos
                Plotter.repeated_clicks = 0
                Plotter.valid_intervals = []
                for itv, reg in Plotter.interval_regions.items():
                    if reg[1].getRegion()[0] < pos.x() < reg[1].getRegion()[1]:  # regions can only be selected from the zoomable plot, hence reg[1]
                        Plotter.valid_intervals.append(itv)
                if Plotter.valid_intervals:
                    itv = Plotter.valid_intervals[0]
                    self.selected_interval = itv
                    self.select_region(itv)
                    if len(Plotter.valid_intervals) > 1:
                        Plotter.repeated_clicks += 1


    def zoom_in(self):
        window.slider.setValue(window.slider.value() + 1)

    def zoom_out(self):
        window.slider.setValue(window.slider.value() - 1)


    @classmethod
    def move_left(cls):
        cls.calculate_movement('left')

    @classmethod
    def move_right(cls):
        cls.calculate_movement('right')


    @classmethod
    def update_marker(cls, position):
        time_in_seconds = position / 1000
        cls.current_marker_whole.setValue(time_in_seconds)
        cls.current_marker_zoom.setValue(time_in_seconds)
        cls.current_marker_glucose.setValue(time_in_seconds)


    @classmethod
    def select_region(cls, itv):
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
        Plotter.repeated_clicks = 0
        Plotter.valid_intervals = []
        Plotter.prev_pos = None

        region_whole = ClickableLinearRegionItem(values=itv)
        region_zoom = ClickableLinearRegionItem(values=itv)
        brush = QBrush(QColor(MovementTypeDialog.colours[itv[2]]))
        region_whole.setBrush(brush)
        region_zoom.setBrush(brush)
        region = [region_whole, region_zoom]
        cls.interval_regions[itv] = region

        if window.show_ma_action.isChecked():
            cls.plot_widget_whole.addItem(region[0])
            cls.plot_widget_zoom.addItem(region[1])
            print("Region Added, interval:", itv)


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
            Plotter.repeated_clicks = 0
            Plotter.valid_intervals = []
            Plotter.prev_pos = None

            Plotter.plot_widget_whole.removeItem(cls.selected_region[0])
            Plotter.plot_widget_zoom.removeItem(cls.selected_region[1])
            # interval_to_remove = None
            for itv, region in Plotter.interval_regions.items():
                if region == cls.selected_region:
                    del cls.interval_regions[itv]
                    if itv in cls.unsaved_intervals:
                        cls.unsaved_intervals.remove(itv)
                    else:
                        cls.entries_to_delete.add(itv)
                    break
            cls.selected_interval = None
            cls.selected_region = None

    @classmethod
    def keyPressEvent(cls, event):
        if cls.selected_region and event.key() == Qt.Key.Key_Delete:
            cls.delete_selected_interval()

    @classmethod
    def reset_class_attributes(cls):
        cls.plot_widget_whole = None
        cls.plot_widget_zoom = None
        cls.plot_widget_glucose = None
        cls.data = None
        # cls.viewRect = QGraphicsRectItem()
        # cls.viewRect.setBrush(QBrush(QColor(255, 255, 255, 100)))
        # cls.viewRect_glucose = QGraphicsRectItem()
        # cls.viewRect_glucose.setBrush(QBrush(QColor(255, 255, 255, 100)))
        cls.init_current_marker_whole()
        cls.init_current_marker_zoom()
        cls.init_current_marker_glucose()
        cls.sample_rate = 100

        cls.unsaved_intervals = set()
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
                new_regions = [cls.selected_region[0], cls.selected_region[1]]
                cls.entries_to_change[cls.selected_interval[:2]] = new_interval
                del cls.interval_regions[cls.selected_interval]
                cls.interval_regions[new_interval] = new_regions
                cls.deselect_region()
            window.change_category_action.setEnabled(False)

    @classmethod
    def adjust_plot_objects(cls, offset):
        print(f"New offset is {offset} seconds")

        cls.current_marker_whole.setValue(window.video_player.mediaPlayer.position() / 1000 + offset)
        cls.current_marker_zoom.setValue(window.video_player.mediaPlayer.position() / 1000 + offset)
        cls.current_marker_glucose.setValue(window.video_player.mediaPlayer.position() / 1000 + offset)

        for itv, reg in cls.interval_regions.items():
            start_0, end_0 = window.offset_adjuster.interval_regions_original[itv][0]
            start_1, end_1 = window.offset_adjuster.interval_regions_original[itv][1]
            reg[0].setRegion((start_0 + offset, end_0 + offset))
            reg[1].setRegion((start_1 + offset, end_1 + offset))


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
        OffsetAdjuster.offset = 0
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
    def clear_data(cls):
        cls.unsaved_intervals = set()

        cls.clear_intervals()
        for itv in cls.interval_regions.keys():
            cls.entries_to_delete.add(itv)
        cls.interval_regions = {}

        cls.interval_regions = {}
        cls.selected_region = []
        cls.selected_interval = None

        cls.entries_to_change = {}

        cls.valid_intervals = []  # In case of clicking on overlapping intervals
        cls.prev_pos = None
        cls.repeated_clicks = 0



class MovementTypeDialog(QDialog):

    categories = {
        '1: Stationary + clean': 's',
        '2: Stationary + noisy': 'n',
        '3: Moving': 'm',
        '4: Eating': 'e',
    }

    colours = {
        's': QColor(127, 88, 175, 100),     #'#FE218B32'
        'n': QColor(100, 197, 235, 100),    #'#FED70032'
        'm': QColor(232, 77, 138, 100),     #'#21B0FE32'
        'e': QColor(254, 179, 38, 100)      #'#0000FF32'
    }

    colours_hex = {
        's': '#7F58AF',
        'n': '#64C5EB',
        'm': '#e85D8A',
        'e': '#FEB326'
    }

    key_to_category = {
        Qt.Key.Key_1: '1: Stationary + clean',
        Qt.Key.Key_2: '2: Stationary + noisy',
        Qt.Key.Key_3: '3: Moving',
        Qt.Key.Key_4: '4: Eating',
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Movement Type")
        self.selected_category = None

        layout = QVBoxLayout()

        for cat in self.categories:
            btn = QPushButton(cat, self)
            btn.clicked.connect(lambda checked, category=cat: self.select_category(category))
            btn.setStyleSheet(f'background-color: {self.colours_hex[self.categories[cat]]}')
            layout.addWidget(btn)

        self.setLayout(layout)

    def select_category(self, category):
        self.selected_category = category
        self.accept()

    def get_selected_category(self):
        return self.selected_category

    def keyPressEvent(self, event):
        if event.key() in self.key_to_category:
            category = self.key_to_category[event.key()]
            self.select_category(category)
        else:
            super().keyPressEvent(event)



class OffsetAdjuster(QDialog):
    offset = 0
    offset_to_apply = 0

    def __init__(self, max_offset=60): # in seconds
        super().__init__()
        self.max_offset = max_offset
        self.interval_regions_original = {}
        for itv, reg in Plotter.interval_regions.items():
            region_copy = [reg[0].getRegion(), reg[1].getRegion()]
            self.interval_regions_original[itv] = region_copy

        self.init_ui()


    def init_ui(self):
        print(f"\n\n\nInitialising UI\n\n\nOffset:{OffsetAdjuster.offset}\n{OffsetAdjuster.offset_to_apply}")
        Plotter.redraw_original_plots(OffsetAdjuster.offset_to_apply)

        self.layout = QVBoxLayout()
        self.options_layout = QHBoxLayout()

        self.info_label = QLabel(f"Current Offset: {OffsetAdjuster.offset_to_apply} seconds")
        self.layout.addWidget(self.info_label)

        self.offset_dial = QDial()
        self.offset_dial.setWrapping(False)
        self.offset_dial.setNotchesVisible(True)
        self.offset_dial.valueChanged.connect(self.on_dial_changed)
        self.offset_dial.setMinimum(0)
        self.offset_dial.setValue(0)
        self.offset_dial.setValue(int(OffsetAdjuster.offset_to_apply * 1000))
        self.offset_dial.setMaximum(self.max_offset * 1000)

        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel)

        self.options_layout.addWidget(self.apply_button)
        self.options_layout.addWidget(self.cancel_button)

        self.layout.addWidget(self.offset_dial)
        self.layout.addLayout(self.options_layout)
        self.setLayout(self.layout)



    def on_dial_changed(self, value):
        print(f'Dial changed! Now offset is {value / 1000.0}')
        OffsetAdjuster.offset = value / 1000.0 #- self.original_offset
        self.info_label.setText(f"Current Offset: {OffsetAdjuster.offset} seconds")
        Plotter.adjust_plot_objects(OffsetAdjuster.offset)

    def apply(self):
        OffsetAdjuster.offset_to_apply = OffsetAdjuster.offset
        Plotter.redraw_plots_with_offset(OffsetAdjuster.offset_to_apply)
        Plotter.adjust_plot_objects(0)
        self.accept()


    def cancel(self):
        self.offset_dial.setValue(int(OffsetAdjuster.offset_to_apply * 1000))
        Plotter.adjust_plot_objects(0)
        self.reject()

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
            self.mediaPlayer.setSource(QUrl.fromLocalFile(filename))
            self.playButton.setEnabled(True)
            if window.plotter_adjustable and window.plotter_whole:
                window.adjust_offset_action.setEnabled(True)
        self.openButton.setVisible(False)
        self.mediaPlayer.play()
        self.mediaPlayer.pause()

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



app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec())
# Libraries
import os
import sys
import json
import time
import datetime
import pycwt
import numpy as np
import scipy as sp
import pandas as pd
import seaborn as sns
import sklearn as sk
import imageio
import scipy.io
from sklearn.decomposition import PCA, FastICA
from sklearn.manifold import TSNE
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import *
from sklearn.mixture import GaussianMixture
import pylab
# import umap
import umap.umap_ as umap
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import *
# from tkinter import simpledialog
from sklearn import metrics
import statistics
import scipy.stats
from sklearn import preprocessing
# Import listed colormap
from matplotlib.colors import ListedColormap
import matplotlib.dates as md
from matplotlib.ticker import FuncFormatter

import plotly.io as plt_io
import plotly.graph_objects as go

# Scipy
from scipy import signal
from scipy import ndimage

# TKinter for selecting files
from tkinter import Tk  # from tkinter import Tk for Python 3.x
from tkinter.filedialog import askopenfile

from PyQt6.QtWidgets import QApplication, QFileDialog


# Add my module to python path
sys.path.append("../")


# from processing.filter import FIR_smooth


class Recording:
    """Class for pre-processing and extracting spikes and HR from electroneurograms (ENG)"""

    window_length = 10000

    def __init__(self, neural, fs, length, map_array, filename, column_ch):
        """Constructor of neurogram object.
        Takes parameters from classmethod open_record, and also initialises other parameters

        Parameters
        ------------
        neural: dataframe
        fs: scalar
        length: lenth of neural dataframe
        map_array:
        filename:
        column_ch

        Return
        --------
        self: object that contains all the parameters

        """
        # self.recording = neural.neural_b
        self.recording = neural  # Initialise with dataframe
        self.recording.name = 'original'
        self.original = neural  # keep a copy of the original
        self.original.name = 'original'  # keep a copy of the original
        self.column_ch = column_ch
        self.fs = fs
        self.filename = filename
        self.threshold = []
        self.wavelet_results = {}
        self.ch_loc = []  # To save location of channel in array (map) as integer
        self.filter_ch = []  # [col for col in neural if col.startswith('ch')]
        self.map_array = map_array
        self.length = length
        self.signal_coded = []
        self.apply_filter = []
        self.detect_method = []
        self.thresh_type = []
        self.channels = []


    @classmethod
    def open_record(cls, path, start, dur=None, load_from_file=False, load_multiple_files=False, downsample=1,
                    port='Port B', map_path=None, verbose=1):
        """
        Called by constructor method to load neural recordings and electrode map

        Parameters
        ------------
        path : 		[string-like] The path for the corresponding setup
        start: 		[int] sample onset
        dur  : 		[int] duration in samples
        load_from_file: [boolean] By default False loads from mat o rhs files, otherwise loads a previously stored csv or pkl with the dataframe
        load_multiple_files: [boolean] load from multiple rhs files or single file (default: False - load single file)
        downsample: [int] (default: 1) downsampling factor.
        channels: 	[array] channels to be selected. If a single port is used then it's always (0, 32), if two ports then port A (0,32) and port B(32, 64)
        map_path: 	[string] path to csv where electrode map is stored
        verbose:    [int - 0,1] signal to display text information (default 1 - show text, 0 - don't show)

        Return
        --------
        neural: 	[dataframe] Index is the time in DateTime, one column for each channel
        fs:  		[float] Sampling frequency
        length: 	[int] number of samples of neural dataframe (number of rows).
        map_array: 	[numpy array] 1D array with the corresponding intan channels for linear electrode device (1-31 electrodes): map_array[0] is intan channel corresponding to electrode 1
        basename_without_ext: [string] name of the file without the extension. For storing purposes
        column_ch:   [list of ints] Available channels from amplifier data in rhs file

        """
        map_array = {}
        # Load dataframes
        neural, fs, basename_without_ext, column_ch = load_data_multich(path, start=start, dur=dur, port=port,
                                                                        load_from_file=load_from_file,
                                                                        load_multiple_files=load_multiple_files,
                                                                        downsample=downsample,
                                                                        verbose=verbose, window_length=Recording.window_length)

        print(neural)
        length = len(neural)
        print(length)

        # Load electrode map
        if map_path is None:
            Tk().withdraw()  # keep the root window from appearing
            map_filepath = askopenfile(initialdir=path, title="Select electrode map .csv",
                                       filetypes=[("map", ".csv")])
        else:
            map_filepath = map_path
        map_array = pd.read_csv(map_filepath, header=None)
        map_array = map_array.to_numpy()
        map_array = map_array.flatten()

        try:
            np.shape(map_array)[0]
        except:
            print('If map_array is 1D, it needs to be a row. Transposing...')
            map_array = map_array.transpose()
        else:
            map_array = map_array

        print("Data loaded succesfully.")
        print('Sampling frequency: %s' % fs)
        print('Recording length: %s(samples), %s(s): ' % (length, length / fs))
        return cls(neural, fs, length, map_array, basename_without_ext, column_ch)

    def select_channels(self, channels):
        """
        Method to select which channels to analyse

        Parameters
        ------------
        channels: 		['all' or list of numbers] list of intan channels to be analysed
        self.column_ch:	[list] list of intan channels from amplifier stored in rhs file (same as channels in load)
        self.map_array:	[numpy array] 1D array with the corresponding intan channels for linear electrode device (1-31 electrodes): map_array[0] is intan channel corresponding to electrode 1

        Return
        --------
        self: object updated with channels information
            ch_loc: 	[list of int] list with electrodes locations corresponding to the selected intan channels
            filter_ch:	[list of string] list with the selected intan channels in string mode (starting in 'ch_')

        """
        if 'all' in channels:
            nchannels = self.column_ch
        # Commented below 29/03/22 because it will only work if all intan channels are available, otherwise I'll need to change the map
        # self.ch_loc = self.column_ch # np.arange(len(self.recording.columns[:-1]))
        # self.filter_ch = np.asarray(self.recording.columns[:-1]) # ['ch_%s'%int(c) for c in self.map_array if ~np.isnan(c)]
        else:
            nchannels = channels

        self.ch_loc = []
        self.filter_ch = []
        for i, ch in enumerate(nchannels):
            ch = int(ch)
            if ch < 0 or (ch not in self.map_array):
                print("Channel not found")
                sys.exit()
            else:
                self.ch_loc.append(np.where(self.map_array == ch)[0][0])
                self.filter_ch.append('ch_%s' % ch)

    def set_gain(self, gain=1):
        """
        Apply amplitude gain to recording

        Parameters
        ------------
        gain: [float] Ratio for gain

        Return
        ------------
        Recording dataframe updated with gain applied to each of the channels selected
        """
        self.recording = self.recording.apply(lambda x: (x * gain) if x.name in self.filter_ch else x)

    def set_bpm(self, bpm):
        """
        Method to set heart rate (beats per minute)

        Parameters
        ------------
        bpm: [float] beats for minute

        Return
        ------------
        Recording object updated with the bpm parameter
        """
        self.bpm = bpm

    # ---------------------------------------------------------------------------
    # Filtering methods
    # ---------------------------------------------------------------------------
    def filter(self, signal2filt, filtername, **kargs):
        """
        Method to apply filtering to recordings (ENG)
        Note that despite the whole dataframe is passed, the algorithm only applies to the selected channels (filter_ch)

        Parameters
        ------------
        signal2filt: [dataframe] signals to filter (columns in dataframe structure)
        filtername:	 [string] name of the filter to apply {'None', 'butter', 'fir', 'notch'}
        kargs:		 [dict] specific parameters for for the filters

        Returns
        ------------
        self.filtered: [dataframe] updare the recording object with a parameter that is a dataframe with the results of the filtering

        """
        if filtername == 'None':
            self.filtered = self.recording
            pass
        elif filtername == 'butter':
            # Configure butterworth filter
            # https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.sosfilt.html#scipy.signal.sosfilt
            # b, a = signal.butter(**kargs)
            # w, h = signal.freqs(b, a)
            # filt_config['butter']['Wn'] = fnorm(filt_config['W'], fs=record.fs).tolist() # The critical frequency or frequencies.
            # Same as doing (filt_config['W']/(record.fs/2)).tolist()
            # kargs['butter']['Wn'] = kargs['W']
            print(kargs)
            kargs['fs'] = self.fs
            sos = signal.butter(**kargs, output='sos')

            # Filter signal: high pass (cutoff at 100Hz)
            # self.recording[self.filter_ch] = signal.lfilter(b, a, self.recording[self.filter_ch])
            # self.recording[self.filter_ch] = signal.sosfilt(sos, self.recording[self.filter_ch])
            self.filtered = signal2filt.apply(lambda x: signal.sosfilt(sos, x) if x.name in self.filter_ch else x)

        elif filtername == 'notch':
            self.filtered = signal2filt.apply(lambda x: self.iir_notch(x, **kargs) if x.name in self.filter_ch else x)

        """
        elif filtername=='fir':
            print(self.filter_ch)
            self.filtered = signal2filt.apply(lambda x: FIR_smooth(x, **kargs) 
                                                    if x.name in self.filter_ch else x)
        """

    # Change from float64 to float 16
    # self.filtered = convertDfType(self.filtered)

    def iir_notch(self, signal2filt, notch_freq, quality_factor):
        # Design a notch filter using signal.iirnotch
        b_notch, a_notch = signal.iirnotch(notch_freq, quality_factor, self.fs)
        # Apply notch filter to the noisy signal using signal.filtfilt
        notch_filtered = signal.filtfilt(b_notch, a_notch, signal2filt)
        return notch_filtered

    # ------------------------------------------
    # Plots
    # Imported for unification but also implemented in visualization.plots)
    # ----------------------------------------------
    def plot_signal(self, signal, ch, map_array, num_rows, num_columns, channels, text_label, text_title, ylim=None,
                    figsize=(10, 15), dtformat='%M:%S.%f', savefigpath='', show_plot=False):
        fig, axes = plt.subplots(num_rows, num_columns, sharex=True, sharey=True, figsize=figsize)
        if (num_rows * num_columns) == 1:
            axes.plot(signal['ch_%s' % int(ch)], label=text_label, lw=0.5)
            # Format axes
            axes.xaxis.set_major_formatter(md.DateFormatter(dtformat))
        else:
            axes = axes.flatten()
            for i, j in enumerate(channels):
                # print(j)
                try:
                    print('plotting ch %s' % map_array[j])
                    axes[i].plot(signal['ch_%s' % int(map_array[j])], label='ch_%s' % int(map_array[j]), lw=0.5)
                    # axes[i].set_title('ch_%s'%int(map_array[j]))
                    # Hide the right and top spines
                    axes[i].spines['right'].set_visible(False)
                    axes[i].spines['top'].set_visible(False)

                    # Only show ticks on the left and bottom spines
                    axes[i].yaxis.set_ticks_position('left')
                    axes[i].xaxis.set_ticks_position('bottom')
                    axes[i].legend(loc='upper right')
                    # Format axes
                    axes[i].xaxis.set_major_formatter(md.DateFormatter(dtformat))
                except KeyError:
                    print('channel %s not found' % int(map_array[j]))
        fig.suptitle(text_title, fontsize=16, family='serif')
        if ylim is not None:
            plt.ylim(ylim)

        if savefigpath != '':
            plt.savefig(savefigpath, facecolor='w')

        if show_plot == True:
            plt.show()
        else:
            print('Plot will not show')
            plt.close()

    def plot_freq_content(self, signal2plot, ch, nperseg=512, max_freq=10000, ylim=None, dtformat='%M:%S.%f',
                          figsize=(10, 15), savefigpath='', show=False):
        """
        plt.specgram parameters:
        NFFT : int
            The number of data points used in each block for the FFT. A power 2 is most efficient. The default value is 256.
            The benefit of a longer FFT is that you will have more frequency resolution. The number of FFT bins, the discrete
            fequency interval of the transform will be N/2. So the frequency resolution of each bin will be the sample frequency Fs x 2/N.
        mode : {'default', 'psd', 'magnitude', 'angle', 'phase'}
            What sort of spectrum to use. Default is 'psd', which takes the power spectral density.
            'magnitude' returns the magnitude spectrum. 'angle' returns the phase spectrum without unwrapping.
            'phase' returns the phase spectrum with unwrapping.
        scale : {'default', 'linear', 'dB'}
            The scaling of the values in the spec. 'linear' is no scaling. 'dB' returns the values in dB scale. When mode is 'psd',
            this is dB power (10 * log10). Otherwise this is dB amplitude (20 * log10). 'default' is 'dB' if mode is 'psd' or 'magnitude'
            and 'linear' otherwise. This must be 'linear' if mode is 'angle' or 'phase'.
        """
        # Raw signal
        fig, ax = plt.subplots(3, 1, figsize=figsize)
        # ax[0].plot(self.original.index, signal2plot['ch_%s'%ch], linewidth=0.5, zorder=0)
        ax[0].plot(signal2plot.index, signal2plot['ch_%s' % ch], linewidth=0.5, zorder=0)
        ax[0].set_title('Sampling Frequency: {}Hz'.format(self.fs))
        ax[0].set_xlabel('Time [s]')
        ax[0].set_ylabel('Voltage [uV]')
        if ylim is not None:
            ax[0].set_ylim(ylim)

        # PSD (whole dataset ferquency distribution)
        f_data, Pxx_den_data = signal.welch(signal2plot['ch_%s' % ch], self.fs, nperseg=nperseg)
        # ax[1].psd(data[0:sf], NFFT=1024, Fs=sf)
        ax[1].semilogx(f_data, Pxx_den_data)
        ax[1].set_xlabel('Frequency [Hz]')
        ax[1].set_ylabel('PSD [V**2/Hz]')

        # Spectogram (frequency content vs time)
        # plt.specgram plots 10*np.log10(Pxx) instead of Pxx
        plt.subplot(313)
        powerSpectrum, freqenciesFound, time, imageAxis = plt.specgram(signal2plot['ch_%s' % ch], NFFT=nperseg,
                                                                       Fs=self.fs, mode='psd', scale='dB')
        plt.ylabel('Spectogram \n Frequenct [Hz]')
        plt.xlabel('Time [s]')
        plt.ylim([0, max_freq])
        clb = plt.colorbar(imageAxis)
        clb.ax.set_title('10*np.log10 \n [dB/Hz]')

        # Format axes
        for i in range(len(ax)):
            # Hide the right and top spines
            ax[i].spines['right'].set_visible(False)
            ax[i].spines['top'].set_visible(False)
            # Only show ticks on the left and bottom spines
            ax[i].yaxis.set_ticks_position('left')
            ax[i].xaxis.set_ticks_position('bottom')
        ax[0].xaxis.set_major_formatter(md.DateFormatter(dtformat))

        if savefigpath != '':
            plt.savefig(savefigpath, facecolor='w')

        if show == True:
            plt.show()
        else:
            print('Plot will not show')
            plt.close()


    def plot_raw_signals(self, channels=None, start_time=None, end_time=None, figsize=None, ylim=None):
        """
        start_time, end_time : [string] in mmmss format e.g. 2 hr 10 min 30 sec -> 13030(xxxx)
                               ....(xxxx) optional - numbers behind the decimal point to specify fractions of a second
        """
        # if signal2plot is None:
        #     signal2plot = self.recording
        if channels is None:
            channels = []
            for col in self.recording.columns:
                if col.startswith('ch_'):
                    # self.recording[col] = self.recording[col].astype('float32')
                    # channels.append(col.replace('ch_', ''))
                    channels.append(col[3:])

        if start_time is None:
            start_index = 0
        else:
            start_index = 0
            start_index += int(start_time[:3]) * 600000
            start_index += int(start_time[3:5]) * 10000
            if len(start_time) == 9:
                start_index += int(start_time[5:])

        if end_time is None:
            end_index = len(self.recording.index)
        else:
            end_index = 0
            end_index += int(end_time[:3]) * 600000
            end_index += int(end_time[3:5]) * 10000
            if len(end_time) == 9:
                end_index += int(end_time[5:])

        if figsize is None:
            figsize = (10, 10*len(channels))
        if ylim is not None:
            ylim = ylim

        fig, ax = plt.subplots(len(channels), 1, figsize=figsize)

        # def time_formatter(x, pos):
        #     return pd.to_datetime(x ).strftime('%H:%M:%S')

        x_range = [i for i in range(start_index, end_index)]
        # x_index = []
        # for idx in self.recording.index[x_range]:
        #     idx = str(idx)
        #     x_index.append(idx.replace('1970-01-01 ', ''))
        # x_index = self.recording.index[x_range].strftime('%H:%M:%S')

        for i in range(len(channels)):
            signal = self.recording['ch_%s' % channels[i]][x_range]
            ax[i].plot(self.recording.index[x_range], signal, linewidth=0.5, zorder=0)
            # ax[i].xaxis.set_major_formatter(FuncFormatter(time_formatter))
            ax[i].set_title("Channel %s" % channels[i])
            ax[i].set_xlabel('Time')
            ax[i].set_ylabel('Voltage [uV]')
            if ylim is not None:
                ax[i].set_ylim(ylim)
        fig.suptitle('Sampling Frequency: {}Hz'.format(self.fs), fontsize=16)


    def discard_MA_0(self, channels=None, std_coeff=3, figsize=None, ylim=None):
        """
        Method: Intuitive, calculates the standard deviation of each channel after filtering, and then discard anything
                above a certain threshold based on the standard deviation
        Currently plots the data for each channel after discarding the corrupted windows
        """
        if not hasattr(self, 'filtered'):
            return

        if channels is None:
            channels = []
            for col in self.recording.columns:
                if col.startswith('ch_'):
                    # self.recording[col] = self.recording[col].astype('float32')
                    # channels.append(col.replace('ch_', ''))
                    channels.append(col)

        if figsize is None:
            figsize = (10, 10*len(channels))
        if ylim is not None:
            ylim = ylim

        fig, ax = plt.subplots(len(channels), 1, figsize=figsize)

        modified_df = self.filtered.copy()
        for i in range(len(channels)):
            windows_to_keep = []
            std = self.filtered[channels[i]].std()
            mean = self.filtered[channels[i]].mean()
            for idx in range(self.length//Recording.window_length + 1):
                window_mean = self.filtered[self.filtered["window"] == idx][channels[i]].mean()
                if abs(window_mean - mean) < std * std_coeff:
                    windows_to_keep.append(idx)
            values = modified_df[modified_df["window"].isin(windows_to_keep)]
            x_range = [i for i in range(len(values))]
            ax[i].plot(x_range, values, linewidth=0.5, zorder=0)
            ax[i].set_title(f"Channel {channels[i]} after discarding MA corrupted windows")
            ax[i].set_xlabel('Sample Index')
            ax[i].set_ylabel('Voltage [uV]')
            if ylim is not None:
                ax[i].set_ylim(ylim)





    def discard_MA_1(self, channels=None, std_const=2, kts_const=2, skw_const=2, figsize=None, ylim=None):
        """
        Method: calculate the standard deviation, skewness and kurtosis of each channel after filtering,
        and then discard any window where any of the three metrics deviate from the corresponding mean value
        beyond a threshold.
        """

        if not hasattr(self, 'filtered'):
            return

        if channels is None:
            channels = []
            for col in self.recording.columns:
                if col.startswith('ch_'):
                    # self.recording[col] = self.recording[col].astype('float32')
                    # channels.append(col.replace('ch_', ''))
                    channels.append(col)

        if figsize is None:
            figsize = (10, 10*len(channels))
        if ylim is not None:
            ylim = ylim

        fig, ax = plt.subplots(len(channels), 1, figsize=figsize)
        modified_df = self.filtered.copy()
        for i in range(len(channels)):
            windows_to_keep = set()
            kurtosis = self.filtered[channels[i]].kurtosis()
            skewness = self.filtered[channels[i]].skew()
            std = self.filtered[channels[i]].std()
            for idx in range(self.length//Recording.window_length + 1):
                window_std = self.filtered[self.filtered["window"] == idx][channels[i]].std()
                window_kts = self.filtered[self.filtered["window"] == idx][channels[i]].kurtosis()
                window_skw = self.filtered[self.filtered["window"] == idx][channels[i]].skew()
                if window_skw > skewness + skw_const:
                    continue
                if window_kts > kurtosis + kts_const:
                    continue
                if window_std > std + std_const:
                    continue
                windows_to_keep.add(idx)

            windows_to_keep = list(windows_to_keep)
            values = modified_df[modified_df["window"].isin(windows_to_keep)]
            x_range = [i for i in range(len(values))]
            ax[i].plot(x_range, values, linewidth=0.5, zorder=0)
            ax[i].set_title(f"Channel {channels[i]} after discarding MA corrupted windows")
            ax[i].set_xlabel('Sample Index')
            ax[i].set_ylabel('Voltage [uV]')
            if ylim is not None:
                ax[i].set_ylim(ylim)

    def ICA(self):
        """

        """

    # def







def load_data_multich(path, start=0, dur=None, port='Port B', load_from_file=False, load_multiple_files=False,
                      downsample=1, verbose=1, window_length=10000):
    """This method loads...

    .. note: This probably should go into a library that could be
             inside the the datasets folder. Then you could import
             it with something like:

               from datasets import load_setup

    Parameters
    ----------
    path :      [string-like] The path for the corresponding setup
    start:      [int] sample onset
    dur  :      [int] duration in samples
    channels:   [array] channels to be selected. If a single port is used then it's always (0, 32), if two ports then port A (0,32) and port B(32, 64)
    load_from_file: [boolean] By default False loads from mat o rhs files, otherwise loads
                    a previously stored csv or pkl with the dataframe
    downsample: [int] (default: 1) downsampling factor.
    verbose:    [int] signal to display text information (default 1 - show text)
    window_length: [int] The number of samples to have per window of data. Set to 50000 (1 minute long) by default

    Returns
    -------
    neural:     [dataframe] Index is the time in DateTime, one column for each channel
    fs:         [float] Sampling frequency
    basename_without_ext: [string] name of the file without the extension. For storing purposes
    channels:   [array of ints] Available channels from amplifier data in rhs file

    """

    # Extract directory of current path
    # dir_name = os.path.dirname(path)

    # Open GUI v1 for selecting file
    Tk().withdraw()  # keep the root window from appearing
    print(path)
    # If data has been previously stored
    if load_from_file:

        filepath = askopenfile(initialdir=path, title="Select previously stored data file",
                               filetypes=[("recording", ".csv .pkl")])
        filepath = filepath.name
        print("Selecting file...")
        # filepath, _ = QFileDialog.getOpenFileName(None, "Select previously stored data file", path,
        #                                           "Pickle files (*.pkl);;CSV files (*.csv);;All files (*.*)")

        print('Loading from file %s' % filepath)
        channels = []
        # Load from csv: computationally expensive
        if filepath.endswith('.csv'):
            neural = pd.read_csv(filepath)
            # Check the file is a data file
            if 'time' in neural.columns:
                # Remove 'time' column and remake it as index (otherwise it's imported as String and not Dataframe)
                neural = neural.drop(columns=['time'])
                neural.index = pd.DatetimeIndex(neural.seconds * 1e9)
                neural.index.name = 'time'

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

                basename_without_ext = os.path.splitext(os.path.basename(filepath))[0]
            else:
                print('ERROR: You have selected a wrong file, try again')
                sys.exit()
        # Load from pickle: much faster
        elif filepath.endswith('.pkl'):
            neural = pd.read_pickle(filepath)

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
                sys.exit()

    else:
        if load_multiple_files:
            # glob allows to load all files in the folder
            files = glob.glob(path + '/*.rhs', recursive=True)
            # Create arrays to store all the data
            amp_data = []
            time = []
            # Run over all files
            for file in files:
                data = read_data(file, verbose=verbose)
                # Sampling frequency
                fs = data['frequency_parameters']['amplifier_sample_rate']
                # Create dataframe
                # As channels not in columns format then transpose
                if (np.shape(data['amplifier_data'])[1] > np.shape(data['amplifier_data'])[0]):
                    # Downsample
                    print('Downsampling with factor: %s' % downsample)
                    new_amp_data = data['amplifier_data'].transpose()
                    new_amp_data = new_amp_data[::downsample]
                    # Transpose data to have channels as columns
                    amp_data.append(new_amp_data)
                    new_time = data['t'].transpose()
                    new_time = new_time[::downsample]  # start:stop:step
                    time.append(new_time)
                else:
                    new_amp_data = data['amplifier_data']
                    new_amp_data = new_amp_data[::downsample]
                    amp_data.append(new_amp_data)
                    new_time = data['t'].transpose()
                    new_time = new_time[::downsample]  # start:stop:step
                    time.append(new_time)
            amp_data = np.concatenate(amp_data, axis=0)
            time = np.concatenate(time, axis=0)
            filepath_init = files[0]
            basename_init = os.path.splitext(os.path.basename(filepath_init))[0]
            filepath_end = files[-1]
            basename_end = os.path.splitext(os.path.basename(filepath_end))[0]
            basename_without_ext = basename_init + '_' + basename_end[-6:]
        else:
            # Open GUI v1 for selecting file
            filepath_init = askopenfile(initialdir=path, title="Select data file (.mat or .rhs)",
                                        filetypes=[("rhs", ".rhs"), ("matlab", ".mat")])
            filepath_init = filepath_init.name
            # Load data
            if filepath_init.endswith('.mat'):
                # print('Loading mat files from %s' %filepath_init)
                data = scipy.io.loadmat(filepath_init)
                # Sampling frequency
                fs = data['fs']
                # Extract only value from nested array
                fs = fs[0][0]
            elif filepath_init.endswith('.rhs'):
                # print('Loading rhs files from %s' %filepath_init)
                data = read_data(filepath_init, verbose=verbose)
                # Sampling frequency
                print(data['frequency_parameters'])
                fs = data['frequency_parameters']['amplifier_sample_rate']
            elif filepath_init.endswith('.csv'):
                print('ERROR: csv file selected. Please choose a .mat or .rhs file')

            # If channels not in columns then transpose
            if (np.shape(data['amplifier_data'])[1] > np.shape(data['amplifier_data'])[0]):
                # Transpose data to have channels as columns
                amp_data = data['amplifier_data'].transpose()
                amp_data = amp_data[::downsample]
                time = data['t'].transpose()
                time = time[::downsample]  # start:stop:step
            else:
                amp_data = data['amplifier_data']
                amp_data = amp_data[::downsample]
                time = data['t']
                time = time[::downsample]  # start:stop:step
            basename_without_ext = os.path.splitext(os.path.basename(filepath_init))[0]

        # Downsample frequency
        # print('Downsampling with factor: %s' %downsample)
        print('time: %s' % len(time))
        print('data: %s' % len(amp_data))
        # amp_data = amp_data[::downsample]
        fs = fs / downsample

        # General to all raw files loading
        # Set time interval
        if dur is None:
            stop = len(amp_data)
        else:
            stop = int(start + dur)
        start = int(start)

        # Create dataframe
        neural = pd.DataFrame()

        # Add column names
        columns = []
        channels = []
        for i, el in enumerate(data['amplifier_channels']):
            # data['amplifier_channels'] contains info as in this example:
            # {'port_name': 'Port A', 'port_prefix': 'A', 'port_number': 1, 'native_channel_name': 'A-030', 'custom_channel_name': 'A-030',
            # 'native_order': 30, 'custom_order': 30, 'chip_channel': 14, 'board_stream': 1, 'electrode_impedance_magnitude': 6839.2158203125,
            # 'electrode_impedance_phase': -59.66900634765625}
            if el['port_name'] == port:
                columns.append(
                    'ch_%s' % (el['custom_order']))  # Array of strings with available channels in the format 'ch_x'
                channels.append(el['custom_order'])  # Array of ints with the number of the available channels
                neural['ch_%s' % (el['custom_order'])] = amp_data[:, i]
        print(columns)
        print(channels)

        # Create dataframe
        # neural = pd.DataFrame(data=amp_data[, columns=columns) #[:,channels]
        neural['seconds'] = time

        neural = neural.iloc[start:stop]

        # Downcast
        for col in neural.columns:
            if col.startswith('ch_'):
                neural[col] = neural[col].astype('float32')

        # Set datetime index
        neural.index = pd.DatetimeIndex(neural.seconds * 1e9)
        neural.index.name = 'time'

        # To avoid loading the data and creating the dataframe every time save it as csv
        # print('Saving data into: %s/%s.csv' %(path, basename_without_ext))
        # neural.to_csv(r'%s/%s.csv' %(path, basename_without_ext))

        print('Saving data into: %s/%s_%s.pkl' % (path, basename_without_ext, port))
        neural.to_pickle(r'%s/%s_%s.pkl' % (path, basename_without_ext, port))

    # Divide the data into windows depending on window_length
    neural['window'] = [i // window_length for i in range(stop)]


    # Return
    return neural, fs, basename_without_ext, channels


'''
    Functions that extracted the features listed from the signal. 
    All these functions take a pandas series as input and usually output a number as float. 
    Some of these functions also have optional inputs. 

    List of all features: [ Mean , Max , Min , MAV , Var , StD , WL , Energy_from_fft , Kurtosis , Skewness ,\
                            Signal_Power , Signal_Energy , Min_max_difference , Zero_crossing , Slope_sign_changes, \
                           Wilson_Amplitude , Root_Mean_Square , V3  , Log_detector , DABS , Maximum_fractal_length ,\
                          Myopulse_percentage_rate , Mean_Frequency ]

    Some of these features might only work well with reasonably large window. The error is roughly in the order of 1/N percent, due to some common
    approximation (sometimes implicit) such as N-1 ~ N. This shouldn't be a big issue when the window length is bigger then 0.1s, for example.
    '''


# Feature 0 : General description
def signal_description(signal_series):
    print(signal_series.describe())
    return signal_series.describe()


def Mean(signal_series):
    mean = signal_series.mean()
    print(f'mean:{mean}')
    return mean


def Max(signal_series):
    maximum = signal_series.max()
    print(f'Maximum: {maximum}')
    return maximum


def Min(signal_series):
    minimum = signal_series.min()
    print(f'Minimum: {minimum}')
    return minimum


# Feature 1 : MAV (mean absolute value)
def MAV(signal_series):
    signal_series_abs = signal_series.abs()
    MAV = signal_series_abs.mean()
    print(f'Mean absolute value (MAV): {MAV}')
    return MAV


# Feature 2 : Variance of the signal.
# (Feature like variance is often considered as a power-related feature)
def Var(signal_series):
    Var = signal_series.var()
    print(f'Variance (Var): {Var}')
    return Var


# Feature 3 : Standard deviation of the signal.
def StD(signal_series):
    StD = signal_series.std()
    print(f'Standard deviation (StD): {StD}')
    return StD


# Feature 4: Waveform length (WL)
'''
NOT to confused with wavelength.
Documented in article "Control of Multifunctional Prosthetic Hands by Processing the Electromyographic Signal" by M. Zecca in more detail.

Also, "Research On the identification of sensory information from mixed nerves by using single-channel cuff
electrodes" by Raspopovic provides very good information on the feature as well
'''


def WL(signal_series):
    signal_series_diff_abs = signal_series.diff().abs()
    WL = signal_series_diff_abs.sum()
    print(f'Waveform Length (WL): {WL}')
    return WL


# Feature 5: Energy calculated based on Discrete Fourier Transform (DFT). (With fast fourier transform algorithm FFT
def Energy_from_fft(signal_series):
    signal_array = signal_series.to_numpy()
    fft = sp.fft.fft(signal_array)
    fft_modulus = np.abs(fft)
    fft_modulus_square = np.square(fft_modulus)
    Energy_from_fft = fft_modulus_square.mean()
    print(f'Energy_from_fft: {Energy_from_fft}')
    return Energy_from_fft


#  Feature 6: Kurtosis. For control, normal distribution should yield a kurtosis of 0.
def Kurtosis(signal_series):
    signal_array = signal_series.to_numpy()
    Kurtosis = sp.stats.kurtosis(signal_array)
    print(f'Kurtosis: {Kurtosis}')
    return Kurtosis


# Feature 7: Skewness (The sample skewness is computed as the Fisher-Pearson coefficient of skewness)
def Skewness(signal_series):
    signal_array = signal_series.to_numpy()
    Skewness = sp.stats.skew(signal_array)
    print(f'Skewness: {Skewness}')
    return Skewness


'''
The two following features, Power and energy of a signal is cited 
from: https://www.gaussianwaves.com/2013/12/power-and-energy-of-a-signal/

There are various definitions of Power and Energy of the signal. The following approaches use the mean of square and sum of
square to represent signal power and energy. This approach does not take sampling frequency into account (default to 1).

Consequently, we would expect that Signal_energy/Signal power = number of sample data.
'''


# Feature 8: Signal Power (directly calculated from the size of signal), equivalent to Mean Square
def Signal_Power(signal_series):
    signal_series_abs = signal_series.abs()
    signal_array_abs = signal_series_abs.to_numpy()
    signal_array_abs_square = np.square(signal_array_abs)
    Signal_power = signal_array_abs_square.mean()
    print(f'Signal_power(Mean of Square): {Signal_power}')
    return Signal_power


# Feature 9: Signal Energy, calcultated from signal directly, equivalent to Sum of Square
# In theory, the value calculated should be almost equal to the energy derived from FFT (Feature 5), by Parseval's theorem
def Signal_Energy(signal_series):
    signal_series_abs = signal_series.abs()
    signal_array_abs = signal_series_abs.to_numpy()
    signal_array_abs_square = np.square(signal_array_abs)
    signal_energy = signal_array_abs_square.sum()
    print(f'Signal_energy(Sum of Square): {signal_energy}')
    return signal_energy


# Feature 10: Difference between Maximum and Minimum
def Min_max_difference(signal_series):
    minimum = signal_series.min()
    maximum = signal_series.max()
    Min_max_difference = maximum - minimum
    print(f'Min_max_difference: {Min_max_difference}')
    return Min_max_difference


# Feature 11: Zero crossing (with threshold that can be chosen.
def Zero_crossing(signal_series, zc_threshold=0):
    time_start = time.time()
    adjacent_multiplication_list = []
    signal_array = signal_series.to_numpy()
    for i in range(len(signal_array) - 1):
        adjacent_multiplication_list.append(signal_array[i] * signal_array[i + 1])

    zero_crossing = 0
    for i in adjacent_multiplication_list:
        if i < -zc_threshold:
            zero_crossing += 1
    print(f'num of zero_crossing: {zero_crossing}')
    # print("Time taken: {} seconds".format(time.time()-time_start))
    return zero_crossing


'''
 See https://www.frontiersin.org/articles/10.3389/fnins.2021.667907/full  for the next few features
'''


# Feature 12: Slope sign changes (SSC): calculate the number of time that slope changes sign
def Slope_sign_changes(signal_series, ssc_threshold=0):
    signal_series_diff = signal_series.diff()
    Slope_sign_changes = Zero_crossing(signal_series_diff, zc_threshold=ssc_threshold)
    print(f'num of Slope_sign_changes: {Slope_sign_changes}')


# Feature 13: Wilson Amplitude: The number of times the change in the signal amplitudes of two consecutive samples exceeds the standard deviation.
def Wilson_Amplitude(signal_series):
    signal_series_diff_abs = signal_series.diff().abs()
    StD = signal_series.std()

    WA = 0
    for i in signal_series_diff_abs:
        if i > StD:
            WA += 1
    print(f'Wilson Amplitude: {WA}')
    return WA


# Feature 14: Root Mean Square (RMS): The root of mean of square or v-order 2.
def Root_Mean_Square(signal_series):
    mean_square = Signal_Power(signal_series)
    RMS = np.sqrt(mean_square)
    print(f'Root mean square: {RMS}')
    return RMS


# Feature 15: Cubic mean or V-order 3 (V3).
def V3(signal_series):
    signal_array = signal_series.to_numpy()
    mean_of_cube = np.power(signal_array, 3).mean()
    V3 = np.cbrt(mean_of_cube)
    print(f'Cubic mean: {V3}')
    return V3


# Feature 16: Log detector (LD): The exponential of the average of the log data.
# (Mathematically, this is in theory the same as geometric mean)
def Log_detector(signal_series):
    signal_series_abs = signal_series.abs()
    signal_array_abs = signal_series_abs.to_numpy()
    signal_array_abs_log = np.log(signal_array_abs)
    log_detector = exp(signal_array_abs_log.mean())
    print(f'Log detector: {log_detector}')
    return log_detector


# Feature 17: Difference absolute standard deviation (DABS): Standard deviation of the absolute of the differential data.
# 2 mathematical equivalent (almost) implementations are provided below
def DABS(signal_series):
    DABS = signal_series.diff().std()
    print(f'Standard deviation of the absolute of the differential data: {DABS}')
    return DABS


def DABS2(signal_series):
    signal_series_diff_square = np.square(signal_series.diff())
    DABS2 = np.sqrt(signal_series_diff_square.mean())
    print(f'DABS2: {DABS2}')


# Feature 18: Maximum_fractal_length: Equivalent to the log of DABS PLUS an offset that is equal to (1/2)*log(N − 1)
# I suspect https://www.frontiersin.org/articles/10.3389/fnins.2021.667907/full contains typo. It should be 'Plus' the offset.
# 2 mathematical equivalent (almost) implementations are provided below
def Maximum_fractal_length(signal_series):
    DABS = signal_series.diff().std()
    Maximum_fractal_length = np.log(DABS) + 0.5 * np.log(len(signal_series))
    print(f'Maximum_fractal_length: {Maximum_fractal_length}')
    return Maximum_fractal_length


def Maximum_fractal_length2(signal_series):
    signal_series_diff_square = np.square(signal_series.diff())
    Maximum_fractal_length2 = 0.5 * np.log(signal_series_diff_square.sum())
    print(f'Maximum_fractal_length2: {Maximum_fractal_length2}')
    return Maximum_fractal_length2


# Feature 19: Myopulse percentage rate (MPR): the number of times the absolute of the data exceeds the standard deviation.
def Myopulse_percentage_rate(signal_series):
    signal_series_abs = signal_series.abs()
    StD = signal_series.std()
    MPR = 0
    for i in signal_series_abs:
        if i > StD:
            MPR += 1
    print(f'Myopulse_percentage_rate: {MPR}')
    return MPR


# Plotting PSD
def Plot_PSD_welch(signal_series):
    plt.close()
    f, Pxx_den = signal.welch(signal_series, fs=30000, nperseg=512)
    plt.semilogx(f, Pxx_den)
    plt.xlabel('Frequency [Hz]')
    plt.ylabel('PSD [V**2/Hz]')
    plt.show()
    print(len(Pxx_den))
    plt.show()


# Feature 20: Mean Frequency: calculated based on the power sepctral density.
def Mean_Frequency(signal_series):
    f, Pxx_den = signal.welch(signal_series, fs=30000, nperseg=512)
    sum_of_power = Pxx_den.sum()  # the normalization factor
    dot_product = np.dot(f, Pxx_den)  # frequency weighted by power
    mean_freq = dot_product / sum_of_power
    print(f'mean frequency:{mean_freq}Hz')
    return mean_freq


def Feature_extraction_1(signal_df, features_list, channels_list):
    '''
        Function that executes all the feature extractions and save the results in a pandas dataframe

        Parameters
        ------------
        signal_df: all the signal in the form of dataframe
        features_list: the list of features wanted to extract
        channels_list: the list of channels that we want for channel extraction.
                        Use signal_df.columns[:x] for convenience

        Return
        --------------
        features_table: the data stored in a dataframe
    '''

    features_list_string = ['channel'] + features_list
    features_table = pd.DataFrame(columns=features_list_string)
    for ch in channels_list:
        # print(ch)
        result_list = []
        result_list.append(str(ch))
        # print(result_list)
        for function_name in features_list:
            # print(function_name)
            # Use globals() to get the function by name
            if function_name in globals() and callable(globals()[function_name]):
                method = globals()[function_name]
            result_list.append(method(signal_df['%s' % ch]))
        features_table.loc[len(features_table)] = result_list
    features_table.set_index('channel')
    return features_table

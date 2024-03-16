# All imports

import copy

import IPython

import os
import sys
import json
import time
import datetime
import pycwt
import statistics
import random
import pickle
import numpy as np
import scipy as sp
import pandas as pd
import seaborn as sns
import sklearn as sk
import tkinter as tk
import matplotlib.pyplot as plt
from sklearn import metrics
from sklearn import decomposition
from sklearn.decomposition import PCA
from tkinter import *
from tkinter import ttk
from sklearn import preprocessing
from datetime import date
import matplotlib.dates as mdates

from neurodsp.rhythm import sliding_window_matching
from neurodsp.utils.download import load_ndsp_data
from neurodsp.plts.rhythm import plot_swm_pattern
from neurodsp.plts.time_series import plot_time_series
from neurodsp.utils import set_random_seed, create_times
# Import listed chormap
from matplotlib.colors import ListedColormap
import matplotlib.dates as md
from matplotlib import colors as mcolors
# Scipy
from scipy import signal
from scipy import ndimage
# TKinter for selecting files
from tkinter import Tk     # from tkinter import Tk for Python 3.x
from tkinter.filedialog import askdirectory

# Add my module to python path
sys.path.append("../")

# Get the directory of the current script
current_script_path = os.path.dirname(__file__)

# Add the parent directory to sys.path to ensure successful imports
# from Neurogram_short.py and additional_functions.py
parent_dir = os.path.abspath(os.path.join(current_script_path, os.pardir))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)


print("Setup started...")
print("------------------------------------------------------\n\n\n\n\n")

# Own libraries
from Neurogram_short import * # Recording, MyWavelet, MyWaveforms
from additional_functions import *

os.environ['KMP_DUPLICATE_LIB_OK']='True'


def setup():
    """
    All code for setting up the filter - written by Amparo
    """
    # After successful import - now select dataset


    Tk().withdraw()  # keep the root window from appearing
    dir_name = ('../datasets/')


    # The paths that lead to where the needed data is located
    path = '../../datasets/rat7&8/day2'
    map_path = '../../datasets/map_linear.csv'



    # When using port A: channels=range(0,32,1) by default port B:range(32,64,1)
    # Start and dur in samples
    # feinstein: channels=[0]
    time_start = time.time()
    load_from_file = True  # Keep it always to true
    downsample = 2  # Only when loading from raw - no need to use it
    start = 0
    dur = None

    port = 'Port A'  # Select port A or B for different recordings
    record = Recording.open_record(path, start=start, dur=dur,
                                   load_from_file=load_from_file,
                                   load_multiple_files=True,
                                   downsample=downsample,
                                   port=port,  # Select recording port
                                   map_path=map_path,
                                   verbose=0)

    # Create directory to save figures
    if not os.path.exists('%s/figures/' % (path)):
        os.makedirs('%s/figures/' % (path))
    print("Time elapsed: {} seconds".format(time.time() - time_start))

    #sys.exit()





    #%%
    # Prepare channels

    channels = []
    for col in record.recording.columns:
        if col.startswith('ch_'):
            # self.recording[col] = self.recording[col].astype('float32')
            channels.append(col.replace('ch_', ''))
    #%%
    # Get current time for saving (avoid overwriting)
    now = datetime.datetime.now()
    current_time = now.strftime("%d%m%Y_%H%M%S")
    #%%
    ## Configuration
    # Do not change
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
    #%%
    # Configure
    config_text = []
    record.apply_filter = options_filter[1]
    record.detect_method = options_detection[1]   # leave it to butter (option 1)
    record.thresh_type = options_threshold[0]     # do not use it for now
    # Select channel position/number in intan (not channel number in device)

    # record.channels = [5,8,13]  # Select the channels to use. E.g. 5,8,13 for the recording you have now. Include 'all' to select all the channels available
    record.channels = channels

    record.path = path
    config_text = ['Load_from_file %s' %load_from_file, 'Filter: %s'%record.apply_filter, 'Detection: %s'%record.detect_method, 'Threhold type: %s'%record.thresh_type, 'Channels: %s' %record.channels, 'Downsampling: %s' %downsample]
    config_text.append('Port %s' %(port))
    config_text.append('Start %s, Dur: %s' %(start,dur))
    config_text.append('Channels: %s' %record.channels)
    # Ramarkable timestamps (in sec)

    group = '1'

    print('SELECTED GENERAL CONFIGURATION:')
    print('Filter: %s'%record.apply_filter)
    print('Detection: %s'%record.detect_method)
    print('Threhold type: %s'%record.thresh_type)
    print('Channels: %s' %record.channels)
    print('-------------------------------------')

    record.select_channels(record.channels) # keep_ch_loc=True if we want to display following the map. Otherwise follow the order provided by selected channels.
    print('map_array: %s' %record.map_array)
    print('ch_loc: %s' %record.ch_loc)
    print('filter_ch %s' %record.filter_ch)
    print('column_ch %s' %record.column_ch)
    #%%
    # Configure
    record.num_rows = 2 #int(round(len(record.filter_ch)/2)) # round(n_components/2)
    record.num_columns = 1 #int(len(record.filter_ch)-round(len(record.filter_ch)/2))+1
    plot_ch = int(record.map_array[record.ch_loc[0]])
    print(plot_ch)
    print(record.num_rows)
    print(record.num_columns)
    save_figure = True
    #%%
    # Gain
    gain = 1
    config_text.append('Gain: %s' %(gain))
    #%%
    # Maximum bpm
    bpm = 300
    record.set_bpm(bpm) # General max bpm in rat HR. Current neurograms at 180bpm
    config_text.append('BPM: %s' %(bpm))
    #%%
    # Final Initialisations - no change

    # Initialize dataframe for results
    #----------------------------------------------------
    record.rolling_metrics = pd.DataFrame()
    record.summary = pd.DataFrame(columns=['Max_spike_rate', 'Min_spike_rate',
                                    'Max_amplitude_sum', 'Min_amplitude_sum'])
    record.summary.index.name = 'channel'
    record.sig2noise = [] #To save the snr for each channel

    # Intialize dataframes for wavelet decomposition
    #---------------------------------------------------
    neural_wvl = pd.DataFrame(columns=record.filter_ch)
    neural_wvl_denoised = pd.DataFrame(columns=record.filter_ch)
    other_wvl = pd.DataFrame(columns=record.filter_ch)
    substraction_wvl = pd.DataFrame(columns=record.filter_ch)
    #%%
    # Config for bandpass filter

    filt_config = {
        'W': [400, 4000],  # (max needs to be <fs/2 per Nyquist)
        'None': {},
        'butter': {
                'N': 9,                # The order of the filter
                'btype': 'bandpass', #'bandpass', #'hp'  #'lowpass'     # The type of filter.
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

    config_text.append('filt_config: %s' %json.dumps(filt_config))
    #%%
    # Apply filter

    # Configure
    time_start = time.time()
    signal2filter = record.recording    # The neural data imported via pkl file
    config_text.append('signal2filter: %s' %signal2filter.name)
    record.filter(signal2filter, record.apply_filter, **filt_config[record.apply_filter])
    # Change from float64 to float 16
    record.filtered = convertDfType(record.filtered, typeFloat='float32')
    #print(record.filtered.dtypes)
    print("Time elapsed: {} seconds".format(time.time()-time_start))


    print("\n\n\n\n\n")
    print("------------------------------------------------------")
    print("Setup Complete!")

    return record
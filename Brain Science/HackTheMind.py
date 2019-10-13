# -*- coding: utf-8 -*-
"""
Estimate Relaxation from Band Powers

This example shows how to buffer, epoch, and transform EEG data from a single
electrode into values for each of the classic frequencies (e.g. alpha, beta, theta)
Furthermore, it shows how ratios of the band powers can be used to estimate
mental state for neurofeedback.

The neurofeedback protocols described here are inspired by
*Neurofeedback: A Comprehensive Review on System Design, Methodology and Clinical Applications* by Marzbani et. al

Adapted from https://github.com/NeuroTechX/bci-workshop
"""

import numpy as np  # Module that simplifies computations on matrices
import matplotlib.pyplot as plt  # Module used for plotting
from pylsl import StreamInlet, resolve_byprop  # Module to receive EEG data
import utils  # Our own utility functions
import os
import subprocess
from time import sleep
import time 
from playsound import playsound
import requests
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--shout', default=False, required=False, help='True if you want the computer shout when you are conentrated')
args = parser.parse_args()

shout = args.shout

# Handy little enum to make code more readable

RELAX_VALUE = [0]*4
CONCENTRATION_VALUE = [0]*4


class Band:
    Delta = 0
    Theta = 1
    Alpha = 2
    Beta = 3


""" EXPERIMENTAL PARAMETERS """
# Modify these to change aspects of the signal processing

# Length of the EEG data buffer (in seconds)
# This buffer will hold last n seconds of data and be used for calculations
BUFFER_LENGTH = 5

# Length of the epochs used to compute the FFT (in seconds)
EPOCH_LENGTH = 1

# Amount of overlap between two consecutive epochs (in seconds)
OVERLAP_LENGTH = 0.8

# Amount to 'shift' the start of each next consecutive epoch
SHIFT_LENGTH = EPOCH_LENGTH - OVERLAP_LENGTH

# Index of the channel(s) (electrodes) to be used
# 0 = left ear, 1 = left forehead, 2 = right forehead, 3 = right ear
INDEX_CHANNEL = [0]

# Search for active LSL streams
print('Looking for an EEG stream...')
streams = resolve_byprop('type', 'EEG', timeout=2)
if len(streams) == 0:
	raise RuntimeError('Can\'t find EEG stream.')

# Set active EEG stream to inlet and apply time correction
print("Start acquiring data")
inlet = StreamInlet(streams[0], max_chunklen=12)
eeg_time_correction = inlet.time_correction()

# Get the stream info and description
info = inlet.info()
description = info.desc()

# Get the sampling frequency
# This is an important value that represents how many EEG data points are
# collected in a second. This influences our frequency band calculation.
# for the Muse 2016, this should always be 256
fs = int(info.nominal_srate())

""" 2. INITIALIZE BUFFERS """

# Initialize raw EEG data buffer
eeg_buffer = np.zeros((int(fs * BUFFER_LENGTH), 1))
filter_state = None  # for use with the notch filter

# Compute the number of epochs in "buffer_length"
n_win_test = int(np.floor((BUFFER_LENGTH - EPOCH_LENGTH) /
							SHIFT_LENGTH + 1))

# Initialize the band power buffer (for plotting)
# bands will be ordered: [delta, theta, alpha, beta]
band_buffer = np.zeros((n_win_test, 4))


def get_dada():
	""" 3.1 ACQUIRE DATA """
	# Obtain EEG data from the LSL stream
	global eeg_buffer
	global filter_state
	global band_buffer

	global file

	eeg_data, timestamp = inlet.pull_chunk(
		timeout=1, max_samples=int(SHIFT_LENGTH * fs))

	# Only keep the channel we're interested in
	ret = [None]*4
	for i in range(4):
		ch_data = np.array(eeg_data)[:, i]#he tocat aixo

		# Update EEG buffer with the new data
		eeg_buffer, filter_state = utils.update_buffer(
			eeg_buffer, ch_data, notch=True,
			filter_state=filter_state)

		""" 3.2 COMPUTE BAND POWERS """
		# Get newest samples from the buffer
		data_epoch = utils.get_last_data(eeg_buffer,
											EPOCH_LENGTH * fs)

		# Compute band powers
		band_powers = utils.compute_band_powers(data_epoch, fs)
		band_buffer, _ = utils.update_buffer(band_buffer,
												np.asarray([band_powers]))
		# Compute the average band powers for all epochs in buffer
		# This helps to smooth out noise
		smooth_band_powers = np.mean(band_buffer, axis=0)

		# print('Delta: ', band_powers[Band.Delta], ' Theta: ', band_powers[Band.Theta],
		#       ' Alpha: ', band_powers[Band.Alpha], ' Beta: ', band_powers[Band.Beta])
		#file.write("%lf,%lf,%lf,%lf\n" % (band_powers[Band.Alpha],band_powers[Band.Beta],band_powers[Band.Delta],band_powers[Band.Theta]))
		""" 3.3 COMPUTE NEUROFEEDBACK METRICS """
		# These metrics could also be used to drive brain-computer interfaces

		# Alpha Protocol:
		# Simple redout of alpha power, divided by delta waves in order to rule out noise
		#return (10 + (smooth_band_powers[Band.Alpha] / \
		#	smooth_band_powers[Band.Delta]))**5
		ret[i] = (smooth_band_powers[Band.Alpha] / smooth_band_powers[Band.Delta])
		#acum += (smooth_band_powers[Band.Alpha] - smooth_band_powers[Band.Delta])
	return ret

def calibrate():
	global RELAX_VALUE
	global CONCENTRATION_VALUE
	print("RELAX")
	start = time.time()
	ack = start

	i = 0
	while ack - start < 15:
		ack = time.time()
		dada = get_dada()
		#if (dada[0] < 1.0 or dada[1] < 1.0 or dada[2] < 1.0 or dada[3] < 1.0):
		RELAX_VALUE[0] += dada[0]
		RELAX_VALUE[1] += dada[1]
		RELAX_VALUE[2] += dada[2]
		RELAX_VALUE[3] += dada[3]
		print(dada)
		i += 1
	RELAX_VALUE[0] /= i
	RELAX_VALUE[1] /= i
	RELAX_VALUE[2] /= i
	RELAX_VALUE[3] /= i
	subprocess.run(["python", "crida.py"])

	print("CONCENTRATE")
	for i in range (20):
		dada = get_dada()
	start = time.time()
	ack = start

	i = 0
	while ack - start < 15:
		ack = time.time()
		dada = get_dada()
		#if (dada[0] > 0.0 or dada[1] > 0.0 or dada[2] > 0.0 or dada[3] > 0.0):
		CONCENTRATION_VALUE[0] += dada[0]
		CONCENTRATION_VALUE[1] += dada[1]
		CONCENTRATION_VALUE[2] += dada[2]
		CONCENTRATION_VALUE[3] += dada[3]
		print(dada)
		i += 1

	CONCENTRATION_VALUE[0] /= i
	CONCENTRATION_VALUE[1] /= i
	CONCENTRATION_VALUE[2] /= i
	CONCENTRATION_VALUE[3] /= i

	print("Have Fun")
	print(RELAX_VALUE,CONCENTRATION_VALUE)
	#requests.post("http://127.0.0.1:5000/threshold",data={'value':(RELAX_VALUE+(CONCENTRATION_VALUE-RELAX_VALUE)*0.75)})



def crida():
	mult = 0.75
	thresholds = [ RELAX_VALUE[0]+(CONCENTRATION_VALUE[0]-RELAX_VALUE[0])*mult,
				   RELAX_VALUE[1]+(CONCENTRATION_VALUE[1]-RELAX_VALUE[1])*mult,
				   RELAX_VALUE[2]+(CONCENTRATION_VALUE[2]-RELAX_VALUE[2])*mult,
				   RELAX_VALUE[3]+(CONCENTRATION_VALUE[3]-RELAX_VALUE[3])*mult]

	concentrat = True
	while True:
		dada = get_dada()

		comparacio = [x > y for x,y in zip(dada, thresholds)]
		if concentrat:
			if sum(comparacio) < 2:
				concentrat=False
		else:
			if sum(comparacio) > 2:
				concentrat=True
		print(sum(comparacio), "\t", dada, "\t", concentrat)
		
		if shout and not concentrat:
			subprocess.run(["python", "crida.py"])

		#requests.post("http://127.0.0.1:5000/relax",data={'value':dada})
		requests.post("http://127.0.0.1:5000/updown",data={'value':int(concentrat)})


calibrate()
crida()
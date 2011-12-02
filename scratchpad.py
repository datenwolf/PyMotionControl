# -*- coding: utf-8 -*-

import threading
import rpyc
import Phytron
from blinker import Signal

class Constraint:
	pass

class Stage:
	def __init__(self, axes):
		self.axes = axes

	def setTarget(self, target):
		self.target = target

	def startCycle(self):
		for ax in self.axes:
			pass

class Axis(object):
	def __init__(self, inverted = False, scale={}):
		self.inverted = inverted
		self.scale = scale
		self.position = None
		self.running = None
		self.initializing = None
		self.initialized = None
		self.initiator_minus = None
		self.initiator_plus = None
		self.onPosition = Signal()
		self.onStarted = Signal()
		self.onStopped = Signal()
		self.onInitializing = Signal()
		self.onInitialized = Signal()
		self.onInitiatorMinus = Signal()
		self.onInitiatorPlus = Signal()
	
	def update(self):
		last_position = self.position
		last_running = self.running
		last_initializing = self.initializing
		last_initialized = self.initialized
		last_initiator_minus = self.initiator_minus
		last_initiator_plus = self.initiator_plus

		self.do_update()

		if last_position != self.position:
			self.onPosition.send(position = self.position)

		if last_running != self.running:
			if self.running:
				self.onStarted.send()
			else:
				self.onStopped.send()

		if last_initializing != self.initializing:
			self.onInitializing.send(initializing = self.initializing)

		if last_initialized != self.initialized:
			self.onInitialized.send(initialized = self.initialized)

		if last_initiator_minus != self.initiator_minus:
			self.onInitiatorMinus.send(active = self.initiator_minus)

		if last_initiator_plus != self.initiator_plus:
			self.onInitiatorPlus.send(active = self.initiator_plus)

	def wait_for_stop(self):
		self.update()
		while self.running:
			self.update()

	def initialize(self):
		if self.running:
			self.stop()
			self.wait_for_stop()
		self.do_initialize()
		self.wait_for_stop()

class PhytronAxis(Axis):
	INITIATOR_MINUS = 1
	INITIATOR_PLUS  = 2
	def __init__(self, ipcomm_axis, max_run_freq, initiator, scale, inverted = False):
		super(PhytronAxis, self).__init__()
		self.ipcomm_axis = ipcomm_axis
		self.max_run_freq = max_run_freq
		self.initiator = initiator
	
	def do_update(self):
		if self.running:
			self.pos = self.ipcomm_axis.getPosition()

		status = self.ipcomm_axis.getFullStatus()
		self.running = status.running
		self.initializing = status.initializing
		self.initialized = status.initialized
		self.initiator_minus = status.initiator_minus
		self.initator_plus = status.initiator_plus

	def do_initialize(self):
		self.ipcomm_axis.setRunFrequency(self.max_run_freq)
		if self.initiator == PhytronAxis.INITIATOR_MINUS:
			self.ipcomm_axis.initializeMinus()
		if self.initiator == PhytronAxis.INITIATOR_PLUS:
			self.ipcomm_axis.initializePlus()


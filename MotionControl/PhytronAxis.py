# -*- coding: utf8 -*-

from Axis import Axis

class PhytronAxis(Axis):
	INITIATOR_MINUS = 1
	INITIATOR_PLUS  = 2
	def __init__(self, ipcomm_axis, limits=None, max_run_freq=None, initiator=INITIATOR_MINUS, initiator_position = 0, limited = True, scale={}):
		super(PhytronAxis, self).__init__(limits = limits, scale = scale)

		self.ipcomm_axis = ipcomm_axis
		if not max_run_freq:
			max_run_freq = self.ipcomm_axis.getRunFrequency()
		self.max_run_freq = max_run_freq
		self.initialisation = False
		self.initiator = initiator
		self.initiator_position = initiator_position
		self.onInitialized.connect(self.handle_initialized)

		self.ipcomm_axis.limited = limited

	def __del__(self):
		self.ipcomm_axis.stop()
	
	def handle_initialized(self, sender, initialized):
		if self.initialisation and sender == self and initialized:
			self.ipcomm_axis.setPosition(self.initiator_position)
	
	def do_update(self):
		status = self.ipcomm_axis.getFullStatus()
		self.position = self.ipcomm_axis.getPosition()
		self.running = status.running
		self.initializing = status.initializing
		self.initialized = status.initialized
		self.initiator_minus = status.initiator_minus
		self.initator_plus = status.initiator_plus
		self.initiator_error = status.initiator_error
		self.temperature_warning = status.high_temperature

	def emergency_stop(self):
		self.ipcomm_axis.stop()		

	def initiate(self):
		self.ipcomm_axis.stop()
		self.wait_for_stop()
		self.ipcomm_axis.setRunFrequency(self.max_run_freq)
		if self.initiator == PhytronAxis.INITIATOR_MINUS:
			self.ipcomm_axis.initializeMinus()
		if self.initiator == PhytronAxis.INITIATOR_PLUS:
			self.ipcomm_axis.initializePlus()
		self.initialisation = True

	def set_initiator_position(self, sender, initialized):
		if sender == self and initialized:
			self.ipcomm_axis.setPosition(self.initiator_position)
			self.position = self.initator_position

	def goto_absolute(self, target, speed = None):
		self.ipcomm_axis.stop()
		self.wait_for_stop()
		if not speed:
			speed = 1.
		self.ipcomm_axis.setRunFrequency(self.max_run_freq * speed)
		self.ipcomm_axis.gotoAbs(target)

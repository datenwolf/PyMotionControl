# -*- coding: utf8 -*-

class Axis(object):
	def __init__(self, inverted = False, scale={}):
		from blinker import Signal
		self.inverted = inverted
		self.scale = scale
		self.position = None
		self.running = None
		self.initializing = None
		self.initialized = None
		self.initiator_minus = None
		self.initiator_plus = None
		self.initiator_error = None
		self.temperature_warning = None
		self.onPosition = Signal()
		self.onStarted = Signal()
		self.onStopped = Signal()
		self.onInitializing = Signal()
		self.onInitialized = Signal()
		self.onInitiatorMinus = Signal()
		self.onInitiatorPlus = Signal()
		self.onInitiatorError = Signal()
		self.onTemperatureWarning = Signal()
	
	def update(self):
		last_position = self.position
		last_running = self.running
		last_initializing = self.initializing
		last_initialized = self.initialized
		last_initiator_minus = self.initiator_minus
		last_initiator_plus = self.initiator_plus
		last_initiator_error = self.initiator_error
		last_temperature_warning = self.temperature_warning

		self.do_update()

		if last_position != self.position:
			self.onPosition.send(self, position = self.position)

		if last_running != self.running:
			if self.running:
				self.onStarted.send(self)
			else:
				self.onStopped.send(self)

		if last_initializing != self.initializing:
			self.onInitializing.send(self, initializing = self.initializing)

		if last_initialized != self.initialized:
			self.onInitialized.send(self, initialized = self.initialized)

		if last_initiator_minus != self.initiator_minus:
			self.onInitiatorMinus.send(self, active = self.initiator_minus)

		if last_initiator_plus != self.initiator_plus:
			self.onInitiatorPlus.send(self, active = self.initiator_plus)

		if last_initiator_error != self.initiator_error:
			self.onInitiatorError.send(self, error = self.initiator_error)

		if last_temperature_warning != self.temperature_warning:
			self.onTemperatureWarning.send(self, warning = self.temperature_warning)

	def wait_for_stop(self):
		self.update()
		while self.running:
			self.update()

	def initiate(self):
		raise NotImplementedError()

	def goto_absolute(self, target, speed = None):
		raise NotImplementedError()

	def goto_relative(self, offset, speed = None):
		raise NotImplementedError()

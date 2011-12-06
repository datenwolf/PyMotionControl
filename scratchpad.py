# -*- coding: utf-8 -*-

import Queue
import threading

class Action:
	def execute(self):
		self.aborted = False
		self.do_execute()
	
	def ended(self):
		if self.aborted:
			return True
		return do_ended()

	def abort(self):
		self.aborted = True
		self.do_abort()
	
	def do_execute():
		raise NotImplementedError

	def do_ended():
		raise NotImplementedError
	
	def do_abort():
		pass

class NullAction(Action):
	def do_execute(self):
		pass
	
	def do_ended(self):
		return True

class Initiate(Action):
	def __init__(self, axes):
		self.axes = axes
	
	def do_execute(self):
		for a in self.axis:
			a.initiate()
	def do_ended():

		all_stopped = not (True in [axis.running for axis in self.axes])
		if not all_stopped:
			return False
		self.aborted = False in [axis.initialized for axis in self.axes]
		return True
	
	def do_abort():
		for axis in self.axes:
			axis.halt()

class GotoAbsolute(Action):
	def __init__(self, axes, target, speed = None):
		if len(axes) != len(target):
			raise ValueError()
		if speed and len(speed) != len(axes):
			raise ValueError()

		self.axes = axes
		self.target = target
		self.speed = speed

	def do_execute(self):
		for i, axis in enumerate(self.axes):
			speed = None
			if self.speed:
				speed = self.speed[i]
			axis.goto_absolute(self.target[i], speed)

	def do_abort(self):
		for axis in self.axes:
			axis.halt()

	def do_ended(self):
		return not (True in [axis.running for axis in self.axes])
		

class EmergencyStop(Action):
	def __init__(self, axes):
		self.axes = axes
	
	def do_execute(self):
		for a in axes:
			a.emergency_stop()

	def do_ended(self):
		return not (True in [axis.running for axis in self.axes])
	
class CycleAbort(Exception):
	pass

class CycleFinished(Exception):
	pass

class MotionControl(object):
	def __init__(self, axes, constraints):
		self.axes = axes
		self.constraints = constraints

		import weakref, threading
		self.on_cycle_started = Signal()
		self.on_cycle_finished = Signal()
		self.on_cycle_aborted = Signal()

	def __del__(self):
		self.abort()

	def can_cycle_start(self):
		return True # FIXME: 

	def prepare_cycle(self):
		pass

	def start_cycle(self):
		if not self.can_cycle_start()
			return False
		self.prepare_cycle()
		self.active = True
		self.worker_thread = threading.Thread(target = MotionControl.cycle_worker, name = "MotionControl.worker", args=(weakref.proxy(self),))
		self.worker_thread.daemon =True
		self.worker_thread.start()
		self.on_cycle_started.send()

	def abort(self):
		self.active = False
		self.worker_thread.join()

	def __del__(self):
		self.active = False

	def cycle_worker(ref):
		abort_action = ref.abort_action
		try:
			import time
			while ref.active:
				time.sleep(0.01)
			ref.on_cycle_finished.send()

		except CycleAbort:
			ref.abort_action.execute()
			ref.on_cycle_aborted.send()

import threading
import rpyc
import Phytron
from blinker import Signal

class Constraint:
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
			self.onPosition.send(position = self.position)

		if last_running != self.running:
			if self.running:
				self.onStarted.send()
			else:
				self.onStopped.send()

		if last_initializing != self.initializing:
			self.onInitializing.send(self, initializing = self.initializing)

		if last_initialized != self.initialized:
			self.onInitialized.send(self, initialized = self.initialized)

		if last_initiator_minus != self.initiator_minus:
			self.onInitiatorMinus.send(self, active = self.initiator_minus)

		if last_initiator_plus != self.initiator_plus:
			self.onInitiatorPlus.send(self, active = self.initiator_plus)

		if last_initiator_error != self.initiator_error:
			self.onInitiatorError(self, error = self.initiator_error)

		if last_temperature_warning != self.temperature_warning:
			self.onTemperatureWarning(self, warning = self.temperature_warning)

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

class PhytronAxis(Axis):
	INITIATOR_MINUS = 1
	INITIATOR_PLUS  = 2
	def __init__(self, ipcomm_axis, max_run_freq=None, initiator=INITIATOR_MINUS, initiator_position = 0, inverted = False):
		super(PhytronAxis, self).__init__()
		self.ipcomm_axis = ipcomm_axis
		if not max_run_freq:
			max_run_freq = self.ipcomm_axis.getRunFrequency()
		self.max_run_freq = max_run_freq
		self.initiator = initiator
		self.initiator_position = initiator_position
		self.onInitialized.connect(self.set_initator_position)
	
	def set_initator_position(self, sender, initialized):
		if sender == self:
			self.ipcomm_axis.setPosition(self.initiator_position)
	
	def do_update(self):
		if self.running:
			self.pos = self.ipcomm_axis.getPosition()

		status = self.ipcomm_axis.getFullStatus()
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

	def set_initiator_position(self, sender, initialized):
		if sender == self and initialized:
			self.ipcomm_axis.setPosition(self.initiator_position)

	def goto_absolute(self, target, speed = None):
		self.ipcomm_axis.stop()
		self.wait_for_stop()
		if not speed:
			speed = 1.
		self.ipcomm_axis.setRunFrequency(self.max_run_freq * speed)
		self.ipcomm_axis.gotoAbs(target)

if __name__ == '__main__':
	ipcomm = Phytron.IPCOMM('/dev/ttyERDASTEP', axes=5)
	axis = PhytronAxis(ipcomm[0])
	action = MotionAbsolute([axis,], [200000,])
	motctl = MotionControl([axis,])

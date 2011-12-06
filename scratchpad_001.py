# -*- coding: utf-8 -*-

import Queue
import threading

class Action(object):
	def __init__(self):
		self.aborted = False
		self.started = False

	def execute(self):
		self.aborted = False
		self.started = True
		self.do_execute()
	
	def ended(self):
		if not self.started:
			False
		if self.aborted:
			return True
		return self.do_ended()

	def abort(self):
		self.aborted = True
		self.do_abort()
	
	def do_execute(self):
		raise NotImplementedError

	def do_ended(self):
		raise NotImplementedError
	
	def do_abort(self):
		pass

class NullAction(Action):
	def do_execute(self):
		pass
	
	def do_ended(self):
		return True

class Initiate(Action):
	def __init__(self, axes):
		Action.__init__(self)
		self.axes = axes
	
	def do_execute(self):
		for axis in self.axes:
			axis.initiate()

	def do_ended(self):
		all_stopped = not (True in [axis.running for axis in self.axes])
		if all_stopped and False in [axis.initialized for axis in self.axes]:
			raise CycleAbort()
		return all_stopped
	
	def do_abort(self):
		for axis in self.axes:
			axis.halt()

class GotoAbsolute(Action):
	def __init__(self, axes, target, speed = None):
		Action.__init__(self)
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
		Action.__init__(self)
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
	def __init__(self, axes, constraints = None):
		import Queue

		self.axes = axes
		self.constraints = constraints

		self.action_queue = Queue.Queue()
		self.abort_action = NullAction()

		self.onCycleStarted = Signal()
		self.onCycleFinished = Signal()
		self.onCycleAborted = Signal()

		self.active = False
		self.target = None

	def __del__(self):
		self.abort()

	def __getattr__(self, name):
		if name == 'position':
			return [axis.position for axis in self.axes]

	def update(self):
		for axis in self.axes:
			axis.update()

	def set_target(self, target):
		if isinstance(target, list):
			if len(target) != len(self.axes):
				raise ValueError
			self.target = target
		if isinstance(target, dict):
			for k,v in target:
				self.target[k] = v
		if isinstance(target, tuple):
			self.target[target[0]] = target[1]

		speed = None
		current_position = self.position
		if not None in current_position:
			delta = [abs(a-b) for a,b in zip(target, current_position)]
			max_delta = max(delta)
			speed = [float(d)/float(max_delta) for d in delta]
		self.action_queue = Queue.Queue()
		self.action_queue.put(GotoAbsolute(self.axes, self.target, speed))

	def can_cycle_start(self):
		if self.active:
			return False
		return True # FIXME: Add constraint tests here

	def start_cycle(self):
		import threading, weakref

		if not self.can_cycle_start():
			return False

		self.current_action = None
		self.active = True
		self.worker_thread = threading.Thread(target = MotionControl.cycle_worker, name = "MotionControl.worker", args=(weakref.proxy(self),))
		self.worker_thread.daemon =True
		self.worker_thread.start()
		self.onCycleStarted.send()

	def abort(self):
		self.active = False
		self.worker_thread.join()

	def __del__(self):
		self.abort()

	def cycle_worker(ref):
		abort_action = ref.abort_action
		try:
			import time
			while True:
				if not ref.active:
					raise CycleAbort()
				ref.update()
				if not ref.current_action or ref.current_action.ended():
					if ref.action_queue.empty():
						break
					ref.current_action = ref.action_queue.get_nowait()

				ref.current_action.execute()

				while True:
					if not ref.active:
						raise CycleAbort()
					ref.update()
					if ref.current_action.ended():
						break

				ref.action_queue.task_done()

			ref.onCycleFinished.send()
		except CycleAbort:
			ref.abort_action.execute()
			ref.onCycleAborted.send()

		finally:
			try:
				while not ref.action_queue.empty():
					ref.action_queue.get_nowait()
					ref.action_queue.task_done()
			except:
				pass
			ref.active = False

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

class PhytronAxis(Axis):
	INITIATOR_MINUS = 1
	INITIATOR_PLUS  = 2
	def __init__(self, ipcomm_axis, max_run_freq=None, initiator=INITIATOR_MINUS, initiator_position = 0, inverted = False, scale={}):
		super(PhytronAxis, self).__init__(inverted = inverted, scale = scale)

		self.ipcomm_axis = ipcomm_axis
		if not max_run_freq:
			max_run_freq = self.ipcomm_axis.getRunFrequency()
		self.max_run_freq = max_run_freq
		self.initialisation = False
		self.initiator = initiator
		self.initiator_position = initiator_position
		self.onInitialized.connect(self.handle_initialized)
	
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


if __name__ == '__main__':
	import sys
	from PyQt4 import QtGui
	
	app = QtGui.QApplication(sys.argv)
	lcd = QtGui.QLCDNumber()
	lcd.setFrameStyle(QtGui.QFrame.Plain)
	lcd.setSegmentStyle(QtGui.QLCDNumber.Flat)
	lcd.setNumDigits(6)
	lcd.setSmallDecimalPoint(False)
	lcd.setDecMode()
	lcd.show()
	
	def show_position(sender, position):
		lcd.display("%.3f" % (float(position)/8000.,) )

	ipcomm = Phytron.IPCOMM('/dev/ttyERDASTEP', axes=5)
	axes = [PhytronAxis(ipcomm[0], initiator_position = -200000, max_run_freq=1500)]
	axes[0].onPosition.connect(show_position)
	moctl = MotionControl(axes)
	moctl.abort_action = EmergencyStop(axes)
	moctl.action_queue.put(Initiate(axes))
	moctl.start_cycle()
	if 1:
		moctl.action_queue.put(GotoAbsolute(axes, [0], [0.5]))
		moctl.action_queue.put(GotoAbsolute(axes, [200000], [1]))
		moctl.action_queue.put(GotoAbsolute(axes, [-100000], [0.75]))
	
	app.exec_()

# -*- coding: utf-8 -*-

import Queue
import threading

class Action:
	EXECUTING = 0
	FINISHED = 1
	ABORTED = 2
	def execute(self):
		self.aborted = False
		self.do_execute()
	
	def ended(self):
		if self.aborted:
			return True
		return do_ended()

	def abort(self):
		self.do_abort()
		self.aborted = True
	
	def do_execute():
		raise NotImplementedError

	def do_abort():
		raise NotImplementedError

	def do_ended():
		raise NotImplementedError


class ActionMotionAbsolute(Action):
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

class ActionExecuter(object):
	def __init__(self, action):
		self.action = action
	
	def start(self):
		import threading, weakref
		self.running = True
		self.worker_thread = threading.Thread(target=ActionExecuter.run, args=(weakref.proxy(self),))
	
	def abort(self):
		self.running = False
		self.worker_thread.join()

	def run(self):
		action = self.action
		try:
			action.execute()
		except ReferenceError:
			action.abort()
		

class MotionControl(object):
	def __init__(self, name):
		import weakref, threading
		self.name = name
		self.on_cycle_started = Signal()
		self.on_cycle_finished = Signal()
		self.on_cycle_aborted = Signal()

	def __del__(self):

	def start_cycle(self):
		self.active = True
		self.worker_thread = threading.Thread(target = MotionControl.cycle_threadfunction, name = "MotionControl.worker_thread"), args=(weakref.proxy(self),))
		self.worker_thread.daemon =True
		self.worker_thread.start()
		self.on_cycle_started.send()

	def abort(self):
		self.active = False
		self.worker_thread.join()

	def __del__(self):
		self.active = False

	def cycle_threadfunction(ref):
		try:
			import time
			while ref.active:
				print self.name
				time.sleep(1)
			ref.on_cycle_finished.send()
		except:
			ref.on_cycle_aborted.send()

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
		raise NotImplementedError()
		"""
		if self.running:
			self.stop()
			self.wait_for_stop()
		self.do_initialize()
		self.wait_for_stop()
		"""

	def goto_absolute(self, targeti, speed = None):
		raise NotImplementedError()

	def goto_relative(self, offset, speed = None):
		raise NotImplementedError()

class PhytronAxis(Axis):
	INITIATOR_MINUS = 1
	INITIATOR_PLUS  = 2
	def __init__(self, ipcomm_axis, scale=1, max_run_freq=None, initiator=INITIATOR_MINUS, inverted = False):
		super(PhytronAxis, self).__init__()
		self.ipcomm_axis = ipcomm_axis
		if not max_run_freq:
			max_run_freq = self.ipcomm_axis.getRunFrequency()
		self.max_run_freq = max_run_freq
		self.initiator = initiator
		self.scale = scale if not inverted else -scale
	
	def do_update(self):
		if self.running:
			self.pos = self.ipcomm_axis.getPosition()

		status = self.ipcomm_axis.getFullStatus()
		self.running = status.running
		self.initializing = status.initializing
		self.initialized = status.initialized
		self.initiator_minus = status.initiator_minus
		self.initator_plus = status.initiator_plus

	def stop_sync(self):
		self.ipcomm_axis.halt()
		while self.ipcomm_axis.getFullStatus().running:
			pass

	def initialize(self):
		self.stop_sync()
		self.ipcomm_axis.setRunFrequency(self.max_run_freq)
		if self.initiator == PhytronAxis.INITIATOR_MINUS:
			self.ipcomm_axis.initializeMinus()
		if self.initiator == PhytronAxis.INITIATOR_PLUS:
			self.ipcomm_axis.initializePlus()

	def goto_absolute(self, target, speed = None):
		self.stop_sync()
		if not speed:
			speed = 1.
		self.ipcomm_axis.setRunFrequency(self.max_run_freq * speed)
		self.ipcomm_axis.gotoAbs(target * self.scale)

if __name__ == '__main__':
	ipcomm = Phytron.IPCOMM('/dev/ttyERDASTEP', axes=5)
	axis = PhytronAxis(ipcomm[0])
	action = ActionMotionAbsolute([axis,], [200000,])


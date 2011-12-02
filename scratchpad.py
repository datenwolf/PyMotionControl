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


class ActionMotion(Action):
	def __init__(self, axes, target, speed = None):
		if len(axes) != len(target):
			raise ValueError()
		if speed and len(speed) != len(axes):
			raise ValueError()

		self.axes = axes
		self.target_position = target
		self.motion_speed = speed

	def do_execute(self):
		for i, axis enumerate(self.axes):
			if self.speed:
				axis.

class ActionExecuter(threading.Thread)
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
		self.name = name
		self.active = True
		self.worker_thread = threading.Thread(target = self.workerLoop, name = "MotionControl.worker_thread")
		self.worker_thread.setDaemon(True)
		self.worker_thread.start()

	def __del__(self):

	def workerLoop(self):
		import time
		while self.active:
			print self.name
			time.sleep(1)


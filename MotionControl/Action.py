# -*- coding: utf8 -*-

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
		for a in self.axes:
			a.emergency_stop()

	def do_ended(self):
		return not (True in [axis.running for axis in self.axes])

# -*- coding: utf-8 -*-

class CycleAbort(Exception):
	pass

class MotionStage(object):
	def __init__(self, axes, constraints = None):
		from Action import EmergencyStop
		from blinker import Signal

		self.axes_idx = dict()
		for i, axis in enumerate(axes):
			self.axes_idx[axis] = i
		self.axes = [axis for axis in axes]
		self.constraints = constraints
		self.abort_action = EmergencyStop(self.axes)

		self.onCycleStarted = Signal()
		self.onCycleFinished = Signal()
		self.onCycleAborted = Signal()

		self.onDestinationChanged = Signal()
		self.onPositionChanged = Signal()

		for axis in self.axes:
			axis.onPosition.connect(self.forward_onPosition)

		self.worker_thread = None
		self.active = False
		self.destination = None
		self.cycle_clear()

		self.update()

	def __del__(self):
		self.abort()

	def cycle_clear(self):
		import Queue
		self.action_queue = Queue.Queue()
	
	def cycle_add_action(self, action):
		if not self.action_queue:
			self.cycle_clear()
		self.action_queue.put(action)

	@property
	def position(self):
		return tuple([axis.position for axis in self.axes])

	def forward_onPosition(self, sender, position):
		self.onPositionChanged.send(self, axis=self.axes_idx[sender], position=position)

	def update(self):
		old_position = self.position
		for axis in self.axes:
			axis.update()
		if old_position != self.position:
			self.onPositionChanged.send(self, position = self.position)
			
	def set_destination(self, destination):
		current_position = self.position
		if not self.destination:
			self.update()
			self.destination = current_position
		if isinstance(destination, list) or isinstance(destination, tuple):
			if len(destination) != len(self.axes):
				raise ValueError
			self.destination = tuple(destination)
		if isinstance(destination, dict):
			new_destination = list(self.destination)
			for k in destination:
				new_destination[k] = destination[k]
			self.destination = tuple(new_destination)

		for i,dest in enumerate(self.destination):
			self.onDestinationChanged.send(self, axis = i, destination = dest)

		speed = None
		if not None in current_position:
			delta = [abs(a-b) for a,b in zip(self.destination, current_position)]
			max_delta = max(delta)
			if max_delta > 0:
				speed = [float(d)/float(max_delta) for d in delta]

		from Action import GotoAbsolute

		self.cycle_clear()
		self.cycle_add_action(GotoAbsolute(self.axes, self.destination, speed))

	def can_cycle_start(self):
		if self.active:
			return False
		return True # FIXME: Add constraint tests here

	def cycle_start(self):
		import threading, weakref

		if not self.can_cycle_start():
			return False

		self.current_action = None
		self.active = True
		self.worker_thread = threading.Thread(target = MotionStage.cycle_worker, name = "MotionControl.worker", args=(weakref.proxy(self),))
		self.worker_thread.daemon =True
		self.worker_thread.start()
		self.onCycleStarted.send()

	def abort(self):
		import threading
		self.active = False
		if isinstance(self.worker_thread, threading.Thread):
			self.worker_thread.join()

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

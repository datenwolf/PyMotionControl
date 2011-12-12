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

		self.onRunning = Signal()
		self.onInitializing = Signal()
		self.onInitialized = Signal()
		self.onInitiatorMinus = Signal()
		self.onInitiatorPlus = Signal()
		self.onPositionChanged = Signal()
		for axis in self.axes:
			axis.onInitializing.connect(self.onInitializing_repeat)
			axis.onInitialized.connect(self.onInitialized_repeat)
			axis.onInitiatorMinus.connect(self.onInitiatorMinus_repeat)
			axis.onInitiatorPlus.connect(self.onInitiatorPlus_repeat)
			axis.onRunning.connect(self.onRunning_repeat)
			axis.onPosition.connect(self.onPosition_repeat)

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
	def running(self):
		return tuple([axis.running for axis in self.axes])
	@property
	def initializing(self):
		return tuple([axis.initializing for axis in self.axes])
	@property
	def initialized(self):
		return tuple([axis.initialized for axis in self.axes])
	@property
	def initiator_minus(self):
		return tuple([axis.initiator_minus for axis in self.axes])
	@property
	def initiator_plus(self):
		return tuple([axis.initiator_plus for axis in self.axes])
	@property
	def position(self):
		return tuple([axis.position for axis in self.axes])

	def onRunning_repeat(self, sender, running):
		self.onRunning.send(self, axis=self.axes_idx[sender], running=running)
	def onPosition_repeat(self, sender, position):
		self.onPositionChanged.send(self, axis=self.axes_idx[sender], position=position)
	def onInitializing_repeat(self, sender, initializing):
		self.onInitializing.send(self, axis=self.axes_idx[sender], initializing=initializing)
	def onInitialized_repeat(self, sender, initialized):
		self.onInitialized.send(self, axis=self.axes_idx[sender], initialized=initialized)
	def onInitiatorMinus_repeat(self, sender, active):
		self.onInitiatorMinus.send(self, axis=self.axes_idx[sender], active=active)
	def onInitiatorPlus_repeat(self, sender, active):
		self.onInitiatorPlus.send(self, axis=self.axes_idx[sender], active=active)

	def update(self):
		old_position = self.position
		for axis in self.axes:
			axis.update()
			
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
		return True # FIXME: Add constraint tests here

	def cycle_start(self):
		import threading, weakref

		if self.active:
			return False

#		if not self.can_cycle_start():
#			return False

		self.current_action = None
		self.active = True
		self.worker_thread = threading.Thread(target = MotionStage.cycleWorker, name = "MotionControl.cycleWorker", args=(weakref.proxy(self),))
		self.worker_thread.daemon = True
		self.worker_thread.start()
		self.onCycleStarted.send(self)

	def abort(self):
		import threading
		self.active = False
		if isinstance(self.worker_thread, threading.Thread):
			self.worker_thread.join()

	def cycleWorker(ref):
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

			ref.onCycleFinished.send(ref)
		except CycleAbort:
			ref.abort_action.execute()
			ref.onCycleAborted.send(ref)

		finally:
			try:
				while not ref.action_queue.empty():
					ref.action_queue.get_nowait()
					ref.action_queue.task_done()
			except:
				pass
			ref.active = False
	
	def reference(self):
		from Action import Initiate, GotoAbsolute
		self.destination = None
		self.cycle_clear()
		self.cycle_add_action(Initiate([self.axes[0]]))
		self.cycle_add_action(GotoAbsolute([self.axes[0]], [0]))
		self.cycle_start()
	

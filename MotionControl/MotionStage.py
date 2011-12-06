# -*- coding: utf-8 -*-

class CycleAbort(Exception):
	pass

class MotionStage(object):
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

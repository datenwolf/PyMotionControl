# -*- coding: utf-8 -*-

import rpyc

class Service(rpyc.Service):
	stage = None
	def on_connect(self):
		Service.stage.onPositionChanged.connect(self.onPosition)
		
		for i,p in enumerate(Service.stage.position):
			self.onPosition(None, i, p)
	
	def on_disconnect(self):
		Service.stage.onPositionChanged.disconnect(self.onPosition)
	
	def onPosition(self, sender, axis, position):
		rpyc.async(self._conn.root.onPosition)(axis, position)

	def exposed_set_destination(self, destination):
		Service.stage.set_destination(destination)
	def exposed_cycle_start(self):
		Service.stage.cycle_start()
	def exposed_abort(self):
		Service.stage.abort()

	def exposed_reference(self):
		Service.stage.reference()

	def exposed_getAxisLimits(self, axis):
		return Service.stage.axes[axis].limits


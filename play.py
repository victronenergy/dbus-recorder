#!/usr/bin/python -u

import sys
import os
from dbus.mainloop.glib import DBusGMainLoop
import dbus
import dbus.service
import gobject
import pickle
import logging
from collections import defaultdict
from functools import total_ordering
from itertools import izip, repeat
import heapq
from argparse import ArgumentParser

InterfaceBusItem = 'com.victronenergy.BusItem'
InterfaceProperties = 'org.freedesktop.DBus.Properties'

class SystemBus(dbus.bus.BusConnection):
    def __new__(cls):
        return dbus.bus.BusConnection.__new__(cls, dbus.bus.BusConnection.TYPE_SYSTEM)

class SessionBus(dbus.bus.BusConnection):
    def __new__(cls):
        return dbus.bus.BusConnection.__new__(cls, dbus.bus.BusConnection.TYPE_SESSION)

def wrap_dbus_value(v):
	""" Stripped down version, since everything is already dbus wrapped, we
	    just need to handle empty lists. """
	if isinstance(v, list) and len(v) == 0:
		return dbus.Array([], signature=dbus.Signature('u'), variant_level=1)
	return v

class DbusRootObject(dbus.service.Object):
	def __init__(self, busName, values):
		super(DbusRootObject, self).__init__(busName, '/')
		self.values = values

	@dbus.service.method(InterfaceBusItem, out_signature = 'v')
	def GetValue(self):
		values = { k[1:]: wrap_dbus_value(v._properties['Value']) \
			for k, v in self.values.items() \
			if 'Value' in v._properties }
		return dbus.Dictionary(values, signature=dbus.Signature('sv'),
			variant_level=1)

class DbusPathObject(dbus.service.Object):
	## Constructor of MyDbusObject
	#
	# Creates the dbus-object under the given bus-name (dbus-service-name).
	# @param busName Return value from dbus.service.BusName, see run()).
	# @param objectPath The dbus-object-path.
	def __init__(self, busName, objectPath, properties):
		super(DbusPathObject, self).__init__(busName, objectPath)
		self._objectPath = objectPath
		self._properties = properties

	@dbus.service.method(InterfaceBusItem, out_signature = 'v')
	def GetValue(self):
		logging.debug("GetValue %s" % self._objectPath)
		value = dbus.Array([], signature=dbus.Signature('i'), variant_level=1)
		if 'Value' in self._properties:
			if self._properties['Value'] != dbus.Array([]):
				value = self._properties['Value']
		return value

	## Dbus method GetText
	# Returns the value as string of the dbus-object-path.
	# @return text A text-value or '' (error)
	@dbus.service.method(InterfaceBusItem, out_signature = 's')
	def GetText(self):
		logging.debug("GetText %s" % self._objectPath)
		text = '---'
		if 'Text' in self._properties:
			text = self._properties['Text']
		return text

	## Dbus method SetValue
	# Sets the value.
	# @param value The new value.
	# @return completion-code When successful a 0 is return, and when not a -1 is returned.
	@dbus.service.method(InterfaceBusItem, in_signature = 'v', out_signature = 'i')
	def SetValue(self, value):
		logging.debug("SetValue %s" % self._objectPath)
		result = -1
		if 'Value' in self._properties:
			self._properties['Value'] = value
			self._properties['Text'] = str(value)
			self.PropertiesChanged(self._properties)
			result = 0
		return result

	def setProperties(self, properties):
		self._properties = properties
		self.PropertiesChanged(properties)

	@dbus.service.signal(InterfaceBusItem, signature = 'a{sv}')
	def PropertiesChanged(self, properties):
		logging.debug('signal PropertiesChanged %s %s' % (self._object_path, properties))

@total_ordering
class PropertiesChangedData(object):
	def __init__(self, time, dbusObjectPath, changes):
		self._time = time
		self._dbusObjectPath = dbusObjectPath
		self._changes = changes

	def __eq__(self, other):
		return self._time == other._time

	def __lt__(self, other):
		return self._time < other._time

class PickleIterator(object):
	def __init__(self, service, values, fp):
		self.service = service
		self.values = values
		self.fp = fp

	def __iter__(self):
		return self

	def next(self):
		if self.fp.closed:
			raise StopIteration

		try:
			return pickle.load(self.fp)
		except EOFError:
			self.fp.close()
			raise StopIteration

class EventStream(object):
	def __init__(self, *args):
		self.args = args
		self.reset()

	def reset(self):
		self.streams = filter(lambda x: x is not None,
			(open_recording(fn) for fn in self.args))
		self.events = sort_streams(*self.streams)
		self.current = None

	def __iter__(self):
		return self

	def next(self):
		self.current = self.events.next()
		return self.current

class Timer(object):
	def __init__(self, services, events):
		self.services = services
		self.events = events
		self.tickcount = 0
		self.evt = None

	def __call__(self):
		if self.events.current is None:
			evt = self.events.next()
		else:
			evt = self.events.current

		try:
			while evt[0]._time <= self.tickcount:
				servicename = evt[1]
				servicepath = evt[0]._dbusObjectPath
				service = self.services[servicename]
				if servicepath in service:
					changes = evt[0]._changes
					logging.debug('Replaying %s %s %s' % (servicename, servicepath, changes))
					service[servicepath].setProperties(changes)
					self.services[servicename]
				evt = self.events.next()
		except StopIteration:
			self.events.reset()
			self.tickcount = 0
			evt = self.events.next()
		else:
			self.tickcount += 1

		return True

def open_recording(fn):
	fp = open(fn, 'rb')
	try:
		service = pickle.load(fp)
		values = pickle.load(fp)
	except EOFError:
		fp.close()
		return None

	return PickleIterator(service, values, fp)

def sort_streams(*args):
	""" args is a list of iterables, The smallest item is yielded each time.
	"""
	streams = [izip(c, repeat(c.service)) for c in args]
	return heapq.merge(*streams)

def main():
	parser = ArgumentParser(description=sys.argv[0])
	parser.add_argument('--speed',
		help='Speedup factor', type=int, default=1)
	parser.add_argument('datafiles', nargs='+', help='Path to data file')

	args = parser.parse_args()

	DBusGMainLoop(set_as_default=True)

	services = defaultdict(dict)
	roots = []
	logging.info("Opening recordings")
	events = EventStream(*args.datafiles)

	# Register dbus services/paths
	for it in events.streams:
		# Every stream gets its own dbus connection.
		logging.info("Initialising service {}".format(it.service))
		bus = SessionBus() if 'DBUS_SESSION_BUS_ADDRESS' in os.environ else SystemBus()
		busName = dbus.service.BusName(it.service, bus)
		for path, props in it.values.iteritems():
			logging.debug("path %s properties %s" % (path, props))
			services[it.service][path] = DbusPathObject(busName, path, props)

		roots.append(DbusRootObject(busName, services[it.service]))

	logging.info("Stage set, starting simulation")
	gobject.timeout_add(int(1000.0/args.speed), Timer(services, events))
	gobject.MainLoop().run()
			
if __name__ == "__main__":
	logging.basicConfig(level=logging.INFO)
	main()

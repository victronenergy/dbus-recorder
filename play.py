#!/usr/bin/python3 -u

import sys
import os
from dbus.mainloop.glib import DBusGMainLoop
import dbus
import dbus.service
from gi.repository import GLib
import pickle
import logging
from collections import defaultdict
from functools import total_ordering
from itertools import repeat
import heapq
from argparse import ArgumentParser
import json
from csv import reader as csvreader
from csv import excel_tab

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

# Used for CSV to dbus wrapping
def demarshall(typ, v):
	de = {
		"INT32": dbus.types.Int32,
		"UINT32": dbus.types.UInt32,
		"UINT16": dbus.types.UInt16,
		"BYTE": lambda x: dbus.types.Byte(int(x)),
		"DOUBLE": dbus.types.Double,
		"STRING": dbus.types.String,
	}

	if typ.startswith("ARRAY"):
		subtype = typ[6:-1]
		v = json.loads(v)
		return dbus.types.Array([demarshall(subtype, x) for x in v])

	if typ in de:
		return de[typ](v)

	return None

class Unpickler(pickle.Unpickler):
	# Support for older pickles
	_replacements = {
		('dbus', 'UTF8String'): ('dbus', 'String')
	}
	def find_class(self, module, name):
		module, name = self._replacements.get((module, name), (module, name))
		return super().find_class(module, name)

class DbusRootObject(dbus.service.Object):
	_objectPath = '/'

	def __init__(self, busName, values):
		super(DbusRootObject, self).__init__(busName, '/')
		self.values = values

	@dbus.service.method(InterfaceBusItem, out_signature = 'v')
	def GetValue(self):
		values = { k[1:]: wrap_dbus_value(v._properties['Value']) \
			for k, v in list(self.values.items()) \
			if hasattr(v, '_properties') and 'Value' in v._properties }
		return dbus.Dictionary(values, signature=dbus.Signature('sv'),
			variant_level=1)

	def setProperties(self, properties):
		values = properties['Value']
		texts = properties['Text']
		for k, v in values.items():
			if not k:
				continue # safeguard
			p = '/' + k
			changes = {'Value': v }
			try:
				changes['Text'] = texts[k]
			except KeyError:
				pass

			# Pass on to DbusPathObject
			try:
				self.values[p]._setProperties(changes)
			except KeyError:
				pass

		# Send PropertiesChanged. Make sure it has the right signature
		# since python-dbus will guess wrong.
		self.PropertiesChanged({ k: dbus.types.Dictionary(v, signature='sv')
			for k, v in properties.items() })

	@dbus.service.signal(InterfaceBusItem, signature = 'a{sv}')
	def PropertiesChanged(self, properties):
		logging.debug('signal PropertiesChanged %s %s' % ('/', properties))

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

	def _setProperties(self, properties):
		# Make sure it is wrapped. If no Value, substitute invalid.
		properties['Value'] = wrap_dbus_value(properties.get('Value', []))
		self._properties = properties

	def setProperties(self, properties):
		self._setProperties(properties)
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
	def __init__(self, unpickler, service, values):
		self.unpickler = unpickler
		self.service = service
		self.values = values

	def __iter__(self):
		return self

	def __next__(self):
		try:
			return self.unpickler.load()
		except EOFError:
			raise StopIteration

class CsvIterator(object):
	def __init__(self, csvreader, service, values):
		self.csvreader = csvreader
		self.service = service # com.victronenergy.battery.whatever
		self.values = values # /Dc/0/Voltage: {'Value': 53.2, 'Text': '53.2V'}

	def __iter__(self):
		return self

	def __next__(self):
		try:
			t, path, typ, value, text = next(self.csvreader)[:5]
			return PropertiesChangedData(int(t), path, {
				'Value': demarshall(typ, value),
				'Text': text
			})
		except (EOFError, ValueError):
			raise StopIteration

class EventStream(object):
	def __init__(self, *args):
		self.args = args
		self.reset()

	def reset(self):
		self.streams = [x for x in (open_recording(fn) for fn in self.args) if x is not None]
		self.events = sort_streams(*self.streams)
		self.current = None

	def __iter__(self):
		return self

	def __next__(self):
		self.current = next(self.events)
		return self.current

class Timer(object):
	def __init__(self, services, events):
		self.services = services
		self.events = events
		self.tickcount = 0
		self.evt = None

	def __call__(self):
		if self.events.current is None:
			evt = next(self.events)
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
				evt = next(self.events)
		except StopIteration:
			self.events.reset()
			self.tickcount = 0
			evt = next(self.events)
		else:
			self.tickcount += 1

		return True

def open_recording(fn):
	if fn.endswith('.csv'):
		fp = open(fn, 'r', encoding='UTF-8')
		reader = csvreader(fp, dialect=excel_tab, quotechar="'")
		try:
			service = next(reader)[0]
		except IndexError:
			fp.close()
			return None

		try:
			values = {}
			path, typ, value, text = next(reader)[:4]
			while path:
				values[path] = {
					'Value': demarshall(typ, value),
					'Text': text
				}
				path, typ, value, text = next(reader)[:4]
		except EOFError:
			fp.close()
			return None
		except ValueError:
			pass # Not enough values to unpack

		return CsvIterator(reader, service, values)
	else:
		fp = open(fn, 'rb')
		unpickler = Unpickler(fp, encoding='UTF-8')
		try:
			service = unpickler.load()
			values = unpickler.load()
		except EOFError:
			fp.close()
			return None

		return PickleIterator(unpickler, service, values)

def sort_streams(*args):
	""" args is a list of iterables, The smallest item is yielded each time.
	"""
	streams = [zip(c, repeat(c.service)) for c in args]
	return heapq.merge(*streams)

def main():
	parser = ArgumentParser(description=sys.argv[0])
	parser.add_argument('--speed',
		help='Speedup factor', type=int, default=1)
	parser.add_argument('datafiles', nargs='+', help='Path to data file')

	args = parser.parse_args()

	DBusGMainLoop(set_as_default=True)

	services = defaultdict(dict)
	logging.info("Opening recordings")
	events = EventStream(*args.datafiles)

	# Register dbus services/paths
	for it in events.streams:
		# Every stream gets its own dbus connection.
		logging.info("Initialising service {}".format(it.service))
		bus = SessionBus() if 'DBUS_SESSION_BUS_ADDRESS' in os.environ else SystemBus()
		busName = dbus.service.BusName(it.service, bus)
		for path, props in it.values.items():
			logging.debug("path %s properties %s" % (path, props))
			services[it.service][path] = DbusPathObject(busName, path, props)

		services[it.service]['/'] = DbusRootObject(busName, services[it.service])

	logging.info("Stage set, starting simulation")
	GLib.timeout_add(int(1000.0/args.speed), Timer(services, events))
	GLib.MainLoop().run()
			
if __name__ == "__main__":
	logging.basicConfig(level=logging.INFO)
	main()

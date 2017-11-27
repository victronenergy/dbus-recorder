#!/usr/bin/python -u

## @package kwhcounters
# Reads the counters from dbus-vebus-device and calculates derived data

# Python imports
from dbus.mainloop.glib import DBusGMainLoop
import dbus
import dbus.service
from gobject import timeout_add, source_remove, MainLoop
from os import path, getpid, _exit, environ
from time import time
import sys
import signal
import platform
import getopt
import errno
#import cPickle as pickle
import pickle

# Local imports
import tracing
from dbusdevice import DbusDevice

## Major version.
FIRMWARE_VERSION_MAJOR = 0x00
## Minor version.
FIRMWARE_VERSION_MINOR = 0x05
## Localsettings version.
version = (FIRMWARE_VERSION_MAJOR << 8) | FIRMWARE_VERSION_MINOR

## Traces (info / debug) setup
pathTraces = '/log/'
traceFileName = 'dbusrecordertraces'
tracingEnabled = False
traceToConsole = False
traceToFile = False
traceDebugOn = False

## dbusrecorder mode
RECORD = 0
PLAY = 1
STOP = 2
mode = RECORD
duration = 0

timeZero = 0
timerId = None
timeTick = 0

PROTOCOL_ASCII = 0
PROTOCOL_BINARY = 1
PROTOCOL_NEWSTYLE = 2
PicklerProtocol = PROTOCOL_NEWSTYLE

## dbus-service name
service = 'dummy'

## file name
filename = 'recorded.dat'
filehandle = None

## The dbus bus.
bus = None

device = None
names = None

## Dbus interface name(s).
InterfaceBusItem = 'com.victronenergy.BusItem'
InterfaceProperties = 'org.freedesktop.DBus.Properties'

## The dictionary of MyDbusService(s).
myDbusServices = {}

class MyDbusdbusrecorderObject(dbus.service.Object):
	## Constructor of MyDbusObject
	#
	# Creates the dbus-object under the given bus-name (dbus-service-name).
	# @param busName Return value from dbus.service.BusName, see run()).
	# @param objectPath The dbus-object-path.
	def __init__(self, busName, objectPath, properties):
		dbus.service.Object.__init__(self, busName, objectPath)
		self._objectPath = objectPath
		self._properties = properties

	## Dbus method GetDescription
	#
	# Returns the a description. Currently not implemented.
	# Alwayes returns 'no description available'.
	# @param language A language code (e.g. ISO 639-1 en-US).
	# @param length Lenght of the language string. 
	# @return description Always returns 'no description available'
	@dbus.service.method(InterfaceBusItem, in_signature = 'si', out_signature = 's')
	def GetDescription(self, language, length):
		return 'no description available'

	## Dbus method Get
	# Returns the value of the property of the dbus-object-path.
	# @param interface the interface (e.g. 'com.victronenergy.BusItem')
	# @param property the property (e.g. 'Valid' or 'Value')
	# @return value A property-value or -1 (error)
	@dbus.service.method(InterfaceProperties, in_signature = 'ss', out_signature = 'v')
	def Get(self, interface, property):
		tracing.log.debug("Get %s %s %s" % (self._objectPath, interface, property))
		value = dbus.Array([], signature=dbus.Signature('i'), variant_level=1)
		if interface == InterfaceBusItem:
			if property in self._properties:
				value = self._properties[property]
		return value

	## Dbus method GetValue
	# Returns the value of the dbus-object-path.
	# @return value A value or -1 (error)
	@dbus.service.method(InterfaceBusItem, out_signature = 'v')
	def GetValue(self):
		tracing.log.debug("GetValue %s" % self._objectPath)
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
		tracing.log.debug("GetText %s" % self._objectPath)
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
		tracing.log.debug("SetValue %s" % self._objectPath)
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
		tracing.log.debug('signal PropertiesChanged %s %s' % (self._object_path, properties))

class PropertiesChangedData(object):
	def __init__(self, time, dbusObjectPath, changes):
		self._time = time
		self._dbusObjectPath = dbusObjectPath
		self._changes = changes

	def __str__(self):
		return "PropertiesChangedData:\n" + str(self._time) + '\n' + str(self._dbusObjectPath) + '\n' + str(self._changes) + '\n'

def handlerEvents(dbusName, dbusObjectPath, changes):
	tracing.log.debug('handlerEvents - path: %s %s' % (dbusName, dbusObjectPath))
	if mode == RECORD:
		timeNow = int(round(time()))
		timeDelta = timeNow - timeZero
		data = PropertiesChangedData(timeDelta, dbusObjectPath, changes)
		with open(filename, 'ab') as filehandle:
			pickle.dump(data, filehandle, protocol=PicklerProtocol)

## Callback function when a NameOwnerChanged occurs on the dbus.
#
# A new service when the newOwner not empty or else the service
# is disconnected. New service is added and introspected. Disconnected
# service is deleted from the device-list.
# @param name the dbus-service-name.
# @param oldOwner the old owner (dbus-service-unique-name)
# @param newOwner the new owner (dbus-service-unique-name)
def handlerNameOwnerChanged(name, oldOwner, newOwner):
	tracing.log.info('handlerNameOwnerChanged name=%s oldOwner=%s newOwner=%s' % (name, oldOwner, newOwner))

## Handles the system (Linux / Windows) signals such as SIGTERM.
#
# Stops the logscript with an exit-code.
# @param signum the signal-number.
# @param stack the call-stack.
def handlerSignals(signum, stack):
	global filehandle

	tracing.log.warning('handlerSignals received: %d' % signum)
	if mode == PLAY:
		filehandle.close()
		source_remove(timerId)
	exitCode = 0
	if signum == signal.SIGHUP:
		exitCode = 1
	sys.exit(exitCode)

def record():
	global timeZero
	#global filehandle

	tracing.log.info("Recording %s" % device)
	timeZero = int(round(time()))
	dbusName = device.getBusName()
	values = device.getValues()
	with open(filename, 'wb') as filehandle:
		pickle.dump(dbusName, filehandle, protocol=PicklerProtocol)
		pickle.dump(values, filehandle, protocol=PicklerProtocol)
	tracing.log.info('recorded initial values')
	tracing.log.info('recording properties changes')
	if duration:
		timeTick = 0
		timer()
		timerId = timeout_add(1000, timer)

def simulate():
	global myDbusServices
	global timerId
	global filehandle
	global timeTick

	filehandle = open(filename, 'rb')
	dbusName = pickle.load(filehandle)
	for name in names:
		if name.startswith(dbusName):
			print("%s already on dbus" % dbusName)
			sys.exit()
			return
	values = pickle.load(filehandle)
	busName = dbus.service.BusName(dbusName, bus)
	for objectPath, properties in values.iteritems():
		tracing.log.debug("path %s properties %s" % (objectPath, properties))
		myDbusObject = MyDbusdbusrecorderObject(busName, objectPath, properties)
		myDbusServices[objectPath] = myDbusObject
	tracing.log.info('play %s' % dbusName)
	timeTick = 0
	timer()
	timerId = timeout_add(1000, timer)

getNewData = True
data = None
def timer():
	global timeTick
	global filehandle
	global getNewData
	global data
	global mode

	if mode == PLAY:
		tracing.log.debug("time %ss" % timeTick)
		changes = True
		while changes:
			try:
				if getNewData:
					data = pickle.load(filehandle)
			except:
				tracing.log.info("restart")
				filehandle.close()
				filehandle = open(filename, 'rb')
				dbusName = pickle.load(filehandle)
				values = pickle.load(filehandle)
				data = pickle.load(filehandle)
				timeTick = 0
				getNewData = True
			if data._time <= timeTick:
				if data._dbusObjectPath in myDbusServices:
					service = myDbusServices[data._dbusObjectPath]
					#tracing.log.debug("properties changed %s %s" % (data._dbusObjectPath, data._changes))
					service.setProperties(data._changes)
				else:
					tracing.log.info("%s not found in myDbusServices" % data._dbusObjectPath)
				getNewData = True
			else:
				getNewData = False
				changes = False
	else: # Recording
		if timeTick >= duration:
			tracing.log.info("finished recording with duration %ss" % duration)
			mode = STOP
			sys.exit()
			return False
	timeTick = timeTick + 1
	return True

## The main function.
def run():
	global bus
	global device
	global names

	DBusGMainLoop(set_as_default=True)

	# setup debug traces.
	tracing.setupTraces(tracingEnabled, pathTraces, traceFileName, traceToConsole, traceToFile, traceDebugOn)
	tracing.log.debug('tracingPath = %s' % pathTraces)

	# Print the logscript version
	tracing.log.info('dbusrecorder version is: 0x%04x' % version)
	tracing.log.info('dbusrecorder PID is: %d' % getpid())

	# Trace the python version.
	pythonVersion = platform.python_version()
	tracing.log.debug('Current python version: %s' % pythonVersion)

	# setup signal handling.
	signal.signal(signal.SIGHUP, handlerSignals) # 1: Hangup detected
	signal.signal(signal.SIGINT, handlerSignals) # 2: Ctrl-C
	signal.signal(signal.SIGUSR1, handlerSignals) # 10: kill -USR1 <logscript-pid>
	signal.signal(signal.SIGTERM, handlerSignals) # 15: Terminate

	# get on the bus
	bus = dbus.SessionBus() if 'DBUS_SESSION_BUS_ADDRESS' in environ else dbus.SystemBus()

	# subscribe to NameOwnerChange for bus connect / disconnect events.. 
	# org.freedesktop.DBus / NameOwnerChanged
	bus.add_signal_receiver(handlerNameOwnerChanged, signal_name='NameOwnerChanged')

	# get named devices on the bus
	names = bus.list_names()

	if mode == RECORD:
		for name in names:
			if name.startswith(service):
				tracing.log.info("Introspecting: %s" % name)
				device = DbusDevice(bus, name, handlerEvents)
				break
		if device is None:
			print("No dbus-service with name %s found!" % service)
			sys.exit()
		else:
			record()
	else:
		simulate()

	MainLoop().run()

def usage():
	print("Usage: ./dbusrecorder [OPTION]")
	print("-h, --help\tdisplay this help and exit")
	print("-c\t\tenable tracing to console (standard off)")
	print("-t\t\tenable tracing to file (standard off)")
	print("-d\t\tset tracing level to debug (standard info)")
	print("-v, --version\treturns the program version")
	print("--record\trecord specified dbus-service to specified file")
	print("--duration\ttime duration recording in seconds (0 is infinite)")
	print("-p\t\tplay specified file")
	print("--file\t\tfilename to record or simulate from")
	print("--banner\tshows program-name and version at startup")

def main(argv):
	global tracingEnabled
	global traceToConsole
	global traceToFile
	global traceDebugOn
	global mode
	global service
	global filename
	global duration

	try:
		opts, args = getopt.getopt(argv, "vhctdp", ["help", "version", "record=", "file=", "duration=", "banner"])
	except getopt.GetoptError:
		usage()
		sys.exit(errno.EINVAL)
	for opt, arg in opts:
		if opt == '-h' or opt == '--help':
			usage()
			sys.exit()
		elif opt == '-c':
			tracingEnabled = True
			traceToConsole = True
		elif opt == '-t':
			tracingEnabled = True
			traceToFile = True
		elif opt == '-d':
			traceDebugOn = True
		elif opt == '-r' or opt == '--record':
			mode = RECORD
			if arg:
				service = arg
			else:
				usage()
				sys.exit()
		elif opt == '-p':
			mode = PLAY
		elif opt == '--file':
			if arg:
				filename = arg
			else:
				usage()
				sys.exit()
		elif opt == '--duration':
			try:
				duration = int(arg)
			except:
				print("duration is not a valid number")
				sys.exit()
		elif opt == '-v' or opt == '--version':
			print(version)
			sys.exit()
		elif opt == '--banner':
			print("dbusrecorder 0x%04x" % version)

	run()

main(sys.argv[1:])

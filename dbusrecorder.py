#!/usr/bin/python3 -u

## @package kwhcounters
# Reads the counters from dbus-vebus-device and calculates derived data

# Python imports
from dbus.mainloop.glib import DBusGMainLoop
import dbus
import dbus.service
from gi.repository.GLib import timeout_add, MainLoop
from os import getpid, environ
from time import time
import sys
import signal
import platform
import getopt
import errno
import pickle
import logging
from functools import partial

logger = logging.getLogger(__name__)

# Local imports
from dbusdevice import DbusDevice

## Major version.
FIRMWARE_VERSION_MAJOR = 0x01
## Minor version.
FIRMWARE_VERSION_MINOR = 0x00
## Localsettings version.
version = (FIRMWARE_VERSION_MAJOR << 8) | FIRMWARE_VERSION_MINOR

PicklerProtocol = 2 # new style

class PropertiesChangedData(object):
	def __init__(self, time, dbusObjectPath, changes):
		self._time = time
		self._dbusObjectPath = dbusObjectPath
		self._changes = changes

	def __str__(self):
		return "PropertiesChangedData:\n" + str(self._time) + '\n' + str(self._dbusObjectPath) + '\n' + str(self._changes) + '\n'

class Timer(object):
	def __init__(self, duration):
		self._duration = duration
		self._tick = 0

	def __call__(self):
		if self._tick >= self._duration:
			logger.info("finished recording with duration %ss" % self._duration)
			sys.exit()
			return False

		self._tick += 1
		return True

def handlerEvents(filename, timeZero, dbusName, dbusObjectPath, changes):
	logger.debug('handlerEvents - path: %s %s' % (dbusName, dbusObjectPath))

	timeNow = int(round(time()))
	timeDelta = timeNow - timeZero
	data = PropertiesChangedData(timeDelta, dbusObjectPath, changes)
	with open(filename, 'ab') as filehandle:
		pickle.dump(data, filehandle, protocol=PicklerProtocol)

## Handles the system (Linux / Windows) signals such as SIGTERM.
#
# Stops the logscript with an exit-code.
# @param signum the signal-number.
# @param stack the call-stack.
def handlerSignals(signum, stack):
	logger.warning('handlerSignals received: %d' % signum)
	exitCode = 0
	if signum == signal.SIGHUP:
		exitCode = 1
	sys.exit(exitCode)

def record(device, filename, duration):
	logger.info("Recording %s" % device)
	dbusName = device.getBusName()
	values = device.getValues()
	with open(filename, 'wb') as filehandle:
		pickle.dump(dbusName, filehandle, protocol=PicklerProtocol)
		pickle.dump(values, filehandle, protocol=PicklerProtocol)
	logger.info('recorded initial values')
	logger.info('recording properties changes')
	if duration:
		timer = Timer(duration)
		timer()
		timeout_add(1000, timer)

## The main function.
def run(service, filename, duration):
	DBusGMainLoop(set_as_default=True)

	# Print the logscript version
	logger.info('dbusrecorder version is: 0x%04x' % version)
	logger.info('dbusrecorder PID is: %d' % getpid())

	# Trace the python version.
	pythonVersion = platform.python_version()
	logger.debug('Current python version: %s' % pythonVersion)

	# setup signal handling.
	signal.signal(signal.SIGHUP, handlerSignals) # 1: Hangup detected
	signal.signal(signal.SIGINT, handlerSignals) # 2: Ctrl-C
	signal.signal(signal.SIGUSR1, handlerSignals) # 10: kill -USR1 <logscript-pid>
	signal.signal(signal.SIGTERM, handlerSignals) # 15: Terminate

	# get on the bus
	bus = dbus.SessionBus() if 'DBUS_SESSION_BUS_ADDRESS' in environ else dbus.SystemBus()

	# get named devices on the bus
	device = None
	for name in bus.list_names():
		if name.startswith(service):
			logger.info("Introspecting: %s" % name)
			device = DbusDevice(bus, name, partial(handlerEvents, filename, int(round(time()))))
			break
	if device is None:
		print("No dbus-service with name %s found!" % service)
		sys.exit()

	record(device, filename, duration)
	MainLoop().run()

def usage():
	print("Usage: ./dbusrecorder [OPTION]")
	print("-h, --help\tdisplay this help and exit")
	print("-d\t\tset logging level to debug (standard info)")
	print("-v, --version\treturns the program version")
	print("--record\trecord specified dbus-service to specified file")
	print("--duration\ttime duration recording in seconds (0 is infinite)")
	print("--file\t\tfilename to record to")
	print("--banner\tshows program-name and version at startup")

def main(argv):
	# Default logging level
	logging.basicConfig(level=logging.INFO)

	service = None
	filename = 'recorded.dat'
	duration = 0

	try:
		opts, args = getopt.getopt(argv, "vhd", ["help", "version", "record=", "file=", "duration=", "banner"])
	except getopt.GetoptError:
		usage()
		sys.exit(errno.EINVAL)
	for opt, arg in opts:
		if opt == '-h' or opt == '--help':
			usage()
			sys.exit()
		elif opt == '-d':
			logger.setLevel(logging.DEBUG)
		elif opt == '-r' or opt == '--record':
			if arg:
				service = arg
			else:
				usage()
				sys.exit()
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

	if service is None:
		usage()
		sys.exit()

	run(service, filename, duration)

main(sys.argv[1:])

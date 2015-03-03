# Local import
import dbus
from dbusitem import Dbusitem
import tracing

class DbusDevice(object):
	## The constructor processes the tree of dbus-items.
	# @param bus Session/System bus object
	# @param name the dbus-service-name.
	def __init__(self, bus, name, eventCallback):
		self._dbus_name = name
		self._tree = Dbusitem(bus, name, '/')
		self._value = {}
		self._eventCallback = eventCallback
		self._tree.foreach(self.add_item)

	def __del__(self):
		tracing.log.debug('__del__ %s' % self)
		self._dbus_name = None
		self._value = None
		self._eventCallback = None
		self._tree._delete()

	def add_item(self, dbusitem):
		tracing.log.debug(dbusitem.object.object_path)
		self._value[dbusitem.object.object_path] = dbusitem
		dbusitem._add_to_prop_changed()
		dbusitem.SetEventCallback(self._eventCallback)
		
	## Returns the dbus-service-name which represents the Victron-device.
	def __str__(self):
		return "DbusDevice=%s" % self._dbus_name
	
	def getBusName(self):
		return self._dbus_name
	
	def getValues(self):
		values = {}
		for obj_path, dbusitem in self._value.iteritems():
			tracing.log.info("getValues %s" % obj_path)
			properties = {}
			properties['Value'] = dbusitem.value#dbusTypeToPythonType(obj_path, dbusitem.value)
			properties['Valid'] = bool(dbusitem.valid)
			properties['Text'] = str(dbusitem.text)
			values[obj_path] = properties
		return values

# convert to python type.
# pickle doesn't handle dbus-types.
def dbusTypeToPythonType(obj_path, dbusValue):
	pythonValue = dbusValue
	dbusType = type(dbusValue).__name__
	if dbusType == dbus.UInt16 or dbusType == dbus.UInt32 or dbusType == dbus.UInt64:
		pythonValue = int(dbusValue)
	elif dbusType == dbus.Byte or dbusType == dbus.Int16 or dbusType == dbus.Int32 or dbusType == dbus.Int64:
		pythonValue = int(dbusValue)
	elif dbusType == 'Double':
		pythonValue == float(dbusValue)
	elif dbusType == dbus.String:
		pythonValue == str(dbusValue)
	if pythonValue == -1:
		if obj_path == '/Ac/ActiveIn/L1/V':
			tracing.log.info("unknown %s %s %s" % (obj_path, dbusType, dbusValue))
	return pythonValue

import logging
import dbus

logger = logging.getLogger(__name__)

class DbusDevice(object):
	## The constructor processes the tree of dbus-items.
	# @param bus Session/System bus object
	# @param name the dbus-service-name.
	def __init__(self, bus, name, eventCallback):
		self._dbus_name = name
		self._dbus_conn = bus
		self._items = []
		self._eventCallback = eventCallback
		self._getChildren(bus, name)
		self._service_id = self._dbus_conn.get_name_owner(name)

	def __del__(self):
		logger.debug('__del__ %s' % self)
		self._dbus_name = None
		self._value = None
		self._eventCallback = None

	def _getChildren(self, bus, service):
		data = self._dbus_conn.call_blocking(service, '/', None, 'GetValue', '', [])
		for child in data:
			name = "/" + child
			self._items.append(name)
		self._dbus_conn.add_signal_receiver(self._on_dbus_value_changed,
			dbus_interface='com.victronenergy.BusItem', signal_name='PropertiesChanged', path_keyword='path',
			sender_keyword='service_id')

	def _on_dbus_value_changed(self, changes, path=None, service_id=None):
		if service_id == self._service_id:
			self._eventCallback(self._dbus_name, path, changes)

	## Returns the dbus-service-name which represents the Victron-device.
	def __str__(self):
		return "DbusDevice=%s" % self._dbus_name
	
	def getBusName(self):
		return self._dbus_name
	
	def getValues(self):
		values = {}
		for i in self._items:
			properties = {}
			properties['Value'] = self._dbus_conn.call_blocking(self._dbus_name, i, None, 'GetValue', '', [])
			properties['Valid'] = bool(properties['Value'] != dbus.Array([]))
			properties['Text'] = str(self._dbus_conn.call_blocking(self._dbus_name, i, None, 'GetText', '', []))
			values[i] = properties
		return values

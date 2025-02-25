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
		self._eventCallback = eventCallback
		self._service_id = self._dbus_conn.get_name_owner(name)
		self._dbus_conn.add_signal_receiver(self._on_dbus_value_changed,
			dbus_interface='com.victronenergy.BusItem', signal_name='PropertiesChanged', path_keyword='path',
			sender_keyword='service_id')
		self._dbus_conn.add_signal_receiver(self._on_dbus_items_changed,
			dbus_interface='com.victronenergy.BusItem',
			signal_name='ItemsChanged', path='/', sender_keyword='service_id')

	def __del__(self):
		logger.debug('__del__ %s' % self)
		self._dbus_name = None
		self._value = None
		self._eventCallback = None

	def _on_dbus_value_changed(self, changes, path=None, service_id=None):
		if service_id == self._service_id:
			self._eventCallback(self._dbus_name, path, changes)

	def _on_dbus_items_changed(self, items, service_id=None):
		if service_id == self._service_id:
			for path, changes in items.items():
				self._eventCallback(self._dbus_name, path, changes)

	## Returns the dbus-service-name which represents the Victron-device.
	def __str__(self):
		return "DbusDevice=%s" % self._dbus_name
	
	def getBusName(self):
		return self._dbus_name
	
	def getValues(self):
		try:
			values = self._dbus_conn.call_blocking(self._dbus_name, '/', None, 'GetItems', '', [])
			for v in values.values():
				v['Valid'] = bool(v['Value'] != dbus.Array([]))
			return values
		except dbus.exceptions.DBusException:
			data = self._dbus_conn.call_blocking(self._dbus_name, '/', None, 'GetValue', '', [])
			texts = self._dbus_conn.call_blocking(self._dbus_name, '/', None, 'GetText', '', [])

			values = {}
			for p, v in data.items():
				values['/' + p] = {
					'Value': v,
					'Valid': bool(v != dbus.Array([])),
					'Text': texts[p]}
			return values

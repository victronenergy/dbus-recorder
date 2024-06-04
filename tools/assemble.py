import sys
import dbus
from csv import reader as csvreader, excel_tab
import json
import pickle

class PropertiesChangedData(object):
	def __init__(self, time, dbusObjectPath, changes):
		self._time = time
		self._dbusObjectPath = dbusObjectPath
		self._changes = changes

def demarshall(typ, v):
	de = {
		"INT32": dbus.types.Int32,
		"INT16": dbus.types.Int16,
		"UINT32": dbus.types.UInt32,
		"UINT16": dbus.types.UInt16,
		"BYTE": lambda x: dbus.types.Byte(int(x)),
		"DOUBLE": dbus.types.Double,
		"STRING": dbus.types.String,
		"BOOLEAN": dbus.types.Boolean,
	}

	if typ.startswith("ARRAY"):
		subtype = typ[6:-1]
		v = json.loads(v)
		return dbus.types.Array([demarshall(subtype, x) for x in v])

	if typ in de:
		return de[typ](v)

	return None

def main():
	fp = open(sys.argv[1], 'r', encoding='UTF-8')
	fo = open(sys.argv[2], 'wb')
	reader = csvreader(fp, dialect=excel_tab, quotechar="'")

	service = next(reader)[0]
	pickle.dump(service, fo, protocol=2)

	# Initial values
	di = {}
	for row in reader:
		if not (row and row[0]):
			break

		path, typ, value, text = row[:4]
		value = demarshall(typ, value)
		di[path] = {
			'Value': value,
			'Text': text,
			'Valid': value != []
		}

	pickle.dump(di, fo, protocol=2)

	# Changes
	# 324 /Hub4/L1/AcPowerSetpoint    INT32:2773  2773W
	# dbus.Dictionary({dbus.String(u'Text'): dbus.String(u'408W'),
	# dbus.String(u'Value'): dbus.Int32(408)})
	for row in reader:
		time, path, typ, value, text = row[:5]
		changes = dbus.types.Dictionary({
			dbus.types.String('Text'): dbus.types.String(text),
			dbus.types.String('Value'): demarshall(typ, value)
		})
		pickle.dump(PropertiesChangedData(int(time), path, changes),
			fo, protocol=2)

	fo.close(); fp.close()

if __name__ == "__main__":
	main()

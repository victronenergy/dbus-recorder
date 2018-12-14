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

def demarshall(v):
	if v.startswith('INT32:'):
		return dbus.types.Int32(v[6:])
	if v.startswith("UINT32:"):
		return dbus.types.UInt32(v[7:])
	if v.startswith("UINT16:"):
		return dbus.types.UInt16(v[7:])
	if v.startswith("BYTE:"):
		return dbus.types.Byte(int(v[5:]))
	if v.startswith("DOUBLE:"):
		return dbus.types.Double(v[7:])
	if v.startswith("ARRAY:"):
		v = json.loads(v[6:])
		return dbus.types.Array([demarshall(x) for x in v])
	if v.startswith("STRING:"):
		return dbus.types.String(v[7:])
	return None

def main():
	fp = open(sys.argv[1], 'rb')
	fo = open(sys.argv[2], 'wb')
	reader = csvreader(fp, dialect=excel_tab)

	service = reader.next()[0]
	pickle.dump(service, fo, protocol=2)

	# Initial values
	di = {}
	for row in reader:
		if not (row and row[0]):
			break

		path, value, text = row[:3]
		value = demarshall(value)
		di[unicode(path)] = {
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
		time, path, value, text = row[:4]
		changes = dbus.types.Dictionary({
			dbus.types.String('Text'): dbus.types.String(text),
			dbus.types.String('Value'): demarshall(value)
		})
		pickle.dump(PropertiesChangedData(int(time), path, changes),
			fo, protocol=2)

	fo.close(); fp.close()

if __name__ == "__main__":
	main()

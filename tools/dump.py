import sys
import dbus
from csv import writer as csvwriter, excel_tab
import pickle
import json

class PropertiesChangedData(object):
    def __init__(self, time, dbusObjectPath, changes):
        self._time = time
        self._dbusObjectPath = dbusObjectPath
        self._changes = changes

def typeof(v):
    if isinstance(v, dbus.types.Int32):
        return "INT32:{}".format(v)
    if isinstance(v, dbus.types.UInt32):
        return "UINT32:{}".format(v)
    if isinstance(v, dbus.types.UInt16):
        return "UINT16:{}".format(v)
    if isinstance(v, dbus.types.Byte):
        return "BYTE:{}".format(int(v))
    if isinstance(v, dbus.types.Double):
        return "DOUBLE:{}".format(v)
    if isinstance(v, dbus.types.Array):
        return "ARRAY:{}".format(json.dumps([typeof(x) for x in v]))
    if isinstance(v, dbus.types.String):
        return "STRING:{}".format(v)
    return "UNKNOWN:{}".format(v)

writer = csvwriter(sys.stdout, dialect=excel_tab)
with open(sys.argv[1], 'rb') as fp:
    service = pickle.load(fp)
    writer.writerow([service])

    values = pickle.load(fp)
    for k, v in values.iteritems():
        writer.writerow([k, typeof(v['Value']), v['Text']])
    writer.writerow([])

    while True:
        try:
            #position = fp.tell()
            change = pickle.load(fp)
            value = change._changes['Value']

            writer.writerow([change._time, change._dbusObjectPath, typeof(value), change._changes['Text']])

        except EOFError:
            break

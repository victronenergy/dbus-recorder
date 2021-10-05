import sys
import dbus
from csv import writer as csvwriter, excel_tab, QUOTE_NONE
import pickle
import json

class Unpickler(pickle.Unpickler):
    # Support for older pickles
    _replacements = {
        ('dbus', 'UTF8String'): ('dbus', 'String')
    }
    def find_class(self, module, name):
        module, name = self._replacements.get((module, name), (module, name))
        return super().find_class(module, name)

class PropertiesChangedData(object):
    def __init__(self, time, dbusObjectPath, changes):
        self._time = time
        self._dbusObjectPath = dbusObjectPath
        self._changes = changes

def typeof(v):
    if isinstance(v, dbus.types.Int32):
        return "INT32"
    if isinstance(v, dbus.types.UInt32):
        return "UINT32"
    if isinstance(v, dbus.types.UInt16):
        return "UINT16"
    if isinstance(v, dbus.types.Byte):
        return "BYTE"
    if isinstance(v, dbus.types.Double):
        return "DOUBLE"
    if isinstance(v, dbus.types.Array):
        if len(v):
            return "ARRAY[{}]".format(typeof(v[0]))
        else:
            return "ARRAY"
    if isinstance(v, dbus.types.String):
        return "STRING"
    if isinstance(v, dbus.types.Dictionary):
        return "DICT"
    return "UNKNOWN"

def fmt(v):
    if isinstance(v, dbus.types.Array):
        return json.dumps([fmt(x) for x in v])
    if isinstance(v, dbus.types.Dictionary):
        return json.dumps({str(k): (typeof(x), fmt(x)) for k, x in v.items()})
    if isinstance(v, dbus.types.Byte):
        return int(v)
    return str(v)

def fmt_text(t):
    if isinstance(t, dbus.types.Dictionary):
        return json.dumps({str(k): str(v) for k, v in t.items()})
    return t

writer = csvwriter(sys.stdout, dialect=excel_tab, quotechar="'")
with open(sys.argv[1], 'rb') as fp:
    unpickler = Unpickler(fp, encoding='UTF-8')
    service = unpickler.load()
    writer.writerow([service])

    values = unpickler.load()
    for k, v in values.items():
        writer.writerow([k, typeof(v['Value']), fmt(v['Value']), v['Text'].strip()])
    writer.writerow([])

    while True:
        try:
            #position = fp.tell()
            change = unpickler.load()
            value = change._changes['Value']

            writer.writerow([change._time, change._dbusObjectPath, typeof(value), fmt(value), fmt_text(change._changes['Text'])])

        except EOFError:
            break

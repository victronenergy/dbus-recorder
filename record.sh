#!/bin/bash
export PYTHONPATH=/opt/victronenergy/pythonshared/
# ./dbusrecorder.py --help
# Usage: ./dbusrecorder [OPTION]
# -h, --help	display this help and exit
# -c		enable tracing to console (standard off)
# -t		enable tracing to file (standard off)
# -d		set tracing level to debug (standard info)
# -v, --version	returns the program version
# --record	record specified dbus-service to specified file
# --duration	time duration recording in seconds (0 is infinite)
# -p		play specified file
# --file		filename to record or simulate from
/opt/victronenergy/dbusrecorder/dbusrecorder.py --record com.victronenergy.vebus.ttyO1 --file=/opt/victronenergy/dbusrecorder/vebus.dat --duration=60 &
/opt/victronenergy/dbusrecorder/dbusrecorder.py --record com.victronenergy.battery.can0_di0 --file=/opt/victronenergy/dbusrecorder/lynxshunt.dat --duration=60 &
/opt/victronenergy/dbusrecorder/dbusrecorder.py --record com.victronenergy.lynxion.can0_di0 --file=/opt/victronenergy/dbusrecorder/lynxion.dat --duration=60 &

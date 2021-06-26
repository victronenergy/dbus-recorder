#!/bin/bash
export PYTHONPATH=/opt/victronenergy/pythonshared
/opt/victronenergy/dbusrecorder/dbusrecorder.py --record com.victronenergy.gps --file=/opt/victronenergy/dbusrecorder/gps.dat --duration=2700 &
